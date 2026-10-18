"""Read-only commission scenarios and complete gap inventory; never bypasses edge gates."""
import argparse
import csv
import hashlib
import itertools
import json
import subprocess
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from nexus.strategies import REGISTRY, validate_bars
from nexus.trading_calendar import expected_closure_gap


def stamp(value):
    return datetime.fromtimestamp(value,UTC).strftime('%Y-%m-%d %H:%M')


def read_bars(path):
    with path.open(encoding='utf-8-sig') as handle:
        reader=csv.DictReader(handle,delimiter='\t')
        return [{'time':int(datetime.strptime(row['<DATE>']+' '+row['<TIME>'],'%Y.%m.%d %H:%M:%S').replace(tzinfo=UTC).timestamp()),
                 **{k:float(row['<'+k.upper()+'>']) for k in ('open','high','low','close')},
                 'tick_volume':int(row['<TICKVOL>']),'spread':int(row['<SPREAD>'])} for row in reader]


def inventory(bars, seconds):
    gaps=[];largest=length=1 if bars else 0
    for a,b in itertools.pairwise(bars):
        start=a['time']+seconds;end=b['time']
        if start==end:length+=1;largest=max(largest,length);continue
        if end<=start or (end-start)%seconds:raise ValueError('Duplicate, reversed or off-grid timestamps')
        allowed=expected_closure_gap(start,end,seconds,'FX_UTC22_V1')
        previous=datetime.fromtimestamp(a['time'],UTC);following=datetime.fromtimestamp(end,UTC)
        slots=[datetime.fromtimestamp(t,UTC) for t in range(start,end,seconds)]
        if any((d.month,d.day) in ((12,25),(1,1)) for d in slots):
            kind='عطلة رسمية'
        elif previous.weekday()==4 and following.weekday() in (6,0) and end-start<=4*86400:
            kind='نهاية أسبوع'
        elif end-start<=max(1200,seconds) and all(20<=d.hour<23 for d in slots):
            kind='صيانة وسيط محتملة'
        else:kind='فجوة غير مبررة'
        gaps.append({'previous_bar_utc':stamp(a['time']),'gap_start_utc':stamp(start),'next_bar_utc':stamp(end),
                     'missing_minutes':(end-start)//60,'missing_bars':(end-start)//seconds,'classification':kind,
                     'calendar_gate_approved':allowed,'previously_flagged':not allowed,
                     'action':'مسموحة بالتقويم المعلن' if allowed else 'تبقى حاجزًا؛يلزم جدول الوسيط أو استعادة الشموع الأصلية',
                     'diagnosis':'Temporal classification only; broker closure not independently verified'})
        length=length+1 if allowed else 1;largest=max(largest,length)
    return {'gaps':gaps,'largest_approved_segment_bars':largest,'shortfall_to_5000':max(0,5000-largest),
            'enough_for_edge_gate':largest>=5000,'total_bars':len(bars)}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',type=Path,default=ROOT/'reports/commission-scenarios')
    args=parser.parse_args();folder=args.output_dir;folder.mkdir(parents=True,exist_ok=True)
    as_of=time.time();reports=[];all_gaps=[]
    observed=json.loads((ROOT/'reports/native-auto-export.json').read_text(encoding='utf-8'))['specification_observed']
    for tf,seconds in (('M5',300),('H1',3600)):
        path=ROOT/'data/real'/tf/f'EURUSD_{tf}.csv';bars=read_bars(path)
        completed=[b for b in bars if b['time']+seconds<=as_of];validate_bars(completed,tf,as_of)
        item=inventory(completed,seconds);item.update(timeframe=tf,total_csv_rows=len(bars),completed_bars=len(completed),
             incomplete_bars=len(bars)-len(completed),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        reports.append(item)
        all_gaps.extend({'timeframe':tf,**gap} for gap in item['gaps'])
    diagnostics={'as_of_utc':stamp(as_of),'calendar_profile':'FX_UTC22_V1','broker_calendar_verified':False,'series':reports}
    (folder/'gap-inventory.json').write_text(json.dumps(diagnostics,indent=2,ensure_ascii=False),encoding='utf-8')
    columns=['timeframe','previous_bar_utc','gap_start_utc','next_bar_utc','missing_minutes','missing_bars',
             'classification','calendar_gate_approved','previously_flagged','action']
    with (folder/'gap-inventory.csv').open('w',encoding='utf-8-sig',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=columns,extrasaction='ignore');writer.writeheader();writer.writerows(all_gaps)
    lines=['| الفريم | بداية الفجوة UTC | الشمعة التالية UTC | دقائق مفقودة | التصنيف | استثناء مثبت بالسياسة؟ | الإجراء |',
           '|---|---|---|---|---|---|---|']
    lines.extend('| '+' | '.join(str(g[k]) for k in ('timeframe','gap_start_utc','next_bar_utc','missing_minutes','classification','calendar_gate_approved','action'))+' |' for g in all_gaps)
    (folder/'gap-inventory.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    results=[]
    for commission in (0,3,7):
        for tf in ('M5','H1'):
            target=folder/tf/f'commission-{commission}';target.mkdir(parents=True,exist_ok=True)
            metadata={'source':'MT5_NATIVE','aggregated':False,'symbol':'EURUSD','timeframe':tf,'timezone':'UTC',
                'account_currency':'USD','profit_currency':observed['profit_currency'],
                'calendar_profile':'FX_UTC22_V1','point':observed['point'],'contract_size':observed['contract_size'],
                'commission_per_lot':commission,'fee_source':f'USER_REQUESTED_HYPOTHETICAL_ROUND_TRIP_SCENARIO_USD_{commission}; NOT_VERIFIED_BROKER_FEE'}
            mp=target/'metadata.json';mp.write_text(json.dumps(metadata,indent=2),encoding='utf-8')
            command=[sys.executable,str(ROOT/'tools/edge_test.py'),'--csv',str(ROOT/'data/real'/tf/f'EURUSD_{tf}.csv'),
                     '--metadata',str(mp),'--output',str(target/'edge.json')]
            result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',check=False)
            output=result.stdout+result.stderr;(target/'run.log').write_text(output,encoding='utf-8')
            if result.returncode:
                status='NOT_EVALUATED_DATA_REJECTED'
                models=[{'model':sid,'trades':None,'win_rate':None,'net_r':None,'sharpe':None,'max_dd':None,'status':status} for sid in sorted(REGISTRY)]
                outcome={'commission':commission,'timeframe':tf,'exit_code':result.returncode,'status':status,
                         'error':output.strip().splitlines()[-1],'models':models,'edge_found':None,'command':command}
            else:
                actual=json.loads((target/'edge.json').read_text(encoding='utf-8'))
                outcome={'commission':commission,'timeframe':tf,'exit_code':0,'status':'EVALUATED','models':actual['models'],
                         'edge_found':[r['model'] for r in actual['models'] if r['edge_status']=='EDGE_FOUND'],'command':command}
            results.append(outcome)
            (target/'scenario-result.json').write_text(json.dumps(outcome,indent=2),encoding='utf-8')
            print(json.dumps({k:v for k,v in outcome.items() if k not in ('models','command')},ensure_ascii=False),flush=True)
    final={'type':'ACTUAL_EDGE_CLI_COMMISSION_SCENARIOS','scenarios':results,'diagnostics':diagnostics,
           'unchanged_slippage_points_per_side':10,'spread':'each historical row','minimum_bars':5000,
           'live_orders':0,'conclusion':'NO ECONOMIC VERDICT IF DATA REJECTED; NULL METRICS ARE NOT ZERO TRADES'}
    (folder/'summary.json').write_text(json.dumps(final,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'series':[{k:v for k,v in r.items() if k!='gaps'} for r in reports],
                      'classifications':dict(Counter(g['classification'] for g in all_gaps)),
                      'total_gaps':len(all_gaps),'prior_flagged_gaps':sum(g['previously_flagged'] for g in all_gaps)},ensure_ascii=False))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
