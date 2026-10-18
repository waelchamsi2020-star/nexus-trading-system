"""Declared native MT5 CSV research gate. EDGE_FOUND is not live authorization."""
import argparse
import csv
import hashlib
import itertools
import json
import math
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from nexus.segment_research import evaluate_segments
from nexus.strategies import REGISTRY, validate_bars
from nexus.timeframes import PERIODS
from nexus.trading_calendar import expected_closure_gap, validate_profile
from nexus.walkforward import evaluate_history


def calendar_profile(metadata):
    default='FX_UTC22_V1' if metadata.get('symbol','').upper().startswith('EURUSD') else 'CONTINUOUS'
    return validate_profile(metadata.get('calendar_profile',default))


def validate_contiguity(bars, timeframe, profile):
    validate_profile(profile)
    seconds=PERIODS[timeframe]
    for a,b in itertools.pairwise(bars):
        close=a['time']+seconds
        if close!=b['time'] and not expected_closure_gap(close,b['time'],seconds,profile):
            raise ValueError('Native history contains an unexpected trading-hours gap')


def load_native(path, metadata, as_of, *, preliminary=False):
    if metadata.get('source')!='MT5_NATIVE' or metadata.get('aggregated') is not False:
        raise ValueError('Declared native non-aggregated MT5 export required')
    tf=metadata.get('timeframe')
    if tf not in ('M5','H1') or metadata.get('timezone')!='UTC':raise ValueError('Explicit M5/H1 and UTC required')
    fee_source=metadata.get('fee_source')
    if not metadata.get('symbol') or not isinstance(fee_source,str) or not fee_source.strip() or 'REPLACE_ME' in fee_source:
        raise ValueError('Symbol and documented commission source required; no REPLACE_ME')
    for key in ('point','contract_size','commission_per_lot'):
        value=metadata.get(key)
        if type(value) not in (float,int) or not math.isfinite(value) or value<0 or (key!='commission_per_lot' and value==0):
            raise ValueError('Invalid explicit cost scale: '+key)
    if metadata.get('account_currency')!=metadata.get('profit_currency') or not metadata.get('account_currency'):
        raise ValueError('Explicit matching account/profit currency required for commission conversion')
    blob=path.read_bytes();text=blob.decode('utf-8-sig')
    dialect=csv.Sniffer().sniff(text[:4096],delimiters=',\t;')
    reader=csv.DictReader(text.splitlines(),dialect=dialect)
    required={'<DATE>','<TIME>','<OPEN>','<HIGH>','<LOW>','<CLOSE>','<TICKVOL>','<SPREAD>'}
    if not required<=set(reader.fieldnames or []):raise ValueError('MT5 export columns missing')
    bars=[]
    for row in reader:
        stamp=datetime.strptime(row['<DATE>']+' '+row['<TIME>'],'%Y.%m.%d %H:%M:%S').replace(tzinfo=UTC).timestamp()
        bars.append({'time':int(stamp),'open':float(row['<OPEN>']),'high':float(row['<HIGH>']),
                     'low':float(row['<LOW>']),'close':float(row['<CLOSE>']),
                     'tick_volume':int(row['<TICKVOL>']),'spread':int(row['<SPREAD>']),
                     'real_volume':int(row.get('<VOL>') or 0)})
    if not preliminary and len(bars)<5000:raise ValueError('At least 5000 original candles required')
    validate_bars(bars,tf,as_of)
    if not preliminary:validate_contiguity(bars,tf,calendar_profile(metadata))
    return bars,{'point':metadata['point'],'commission_per_unit':metadata['commission_per_lot']/metadata['contract_size'],
                 'commission_known':True,'slippage_price':10*metadata['point']},hashlib.sha256(blob).hexdigest()


def edge_status(review):
    return 'EDGE_FOUND' if review['trades']>=30 and review['net_r']>0 else 'NO_EDGE_FOUND'


def run(path, metadata, output, as_of):
    bars,costs,fingerprint=load_native(path,metadata,as_of)
    rows=[]
    for sid in sorted(REGISTRY):
        result=evaluate_history(bars,sid,symbol=metadata['symbol'],timeframe=metadata['timeframe'],as_of=as_of,
                                costs=costs,context={'data_kind':'broker','tick_size':metadata['point'],'calendar_profile':calendar_profile(metadata)})
        row={'model':sid,**result['review']};row['edge_status']=edge_status(row);rows.append(row)
        if row['edge_status']=='EDGE_FOUND':print('EDGE_FOUND: '+sid,flush=True)
    report={'version':1,'data_sha256':fingerprint,'declared_native_provenance':metadata,
            'native_source_independently_authenticated':False,
            'calendar_profile':calendar_profile(metadata),
            'calendar_note':'FX_UTC22_V1: user-requested fixed UTC22 weekend and full UTC Christmas/New Year closure assumptions; not broker-verified; no DST/session inference',
            'costs':costs,'slippage_points_per_side':10,
            'models':rows,'execution_authority':False,'live_changes':False,
            'threshold_note':'Positive sample net R and >=30 trades; not statistical significance or a live certificate',
            'missing_auxiliary_context':'No partner/daily context supplied by this single native CSV'}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    lines=['| model | trades | win rate | net R | trade Sharpe | max DD R | status |','|---|---|---|---|---|---|---|']
    for row in rows:
        lines.append('| '+' | '.join(str(row[k]) for k in ('model','trades','win_rate','net_r','sharpe_trade_nonannualized','max_drawdown_r','edge_status'))+' |')
    output.with_suffix('.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    if not any(x['edge_status']=='EDGE_FOUND' for x in rows):print('NO_EDGE_FOUND')
    return report


def run_directory(data_root, output_dir, as_of):
    # Native files only; each CSV carries its own costs, currency and provenance.
    paths=sorted([*data_root.glob('M5/*.csv'), *data_root.glob('H1/*.csv')])
    if not paths:raise ValueError('No native M5/H1 CSV files found')
    prepared=[]
    for path in paths:
        metadata=json.loads(path.with_suffix('.metadata.json').read_text(encoding='utf-8'))
        if metadata.get('timeframe')!=path.parent.name:
            raise ValueError('CSV folder and metadata timeframe disagree: '+str(path))
        prepared.append((path,metadata))
    return [run(path,metadata,output_dir/path.parent.name/(path.stem+'.json'),as_of)
            for path,metadata in prepared]


def run_preliminary(path, metadata, output, as_of, commissions):
    bars,costs,fingerprint=load_native(path,metadata,as_of,preliminary=True)
    report=evaluate_segments(bars,symbol=metadata['symbol'],timeframe=metadata['timeframe'],as_of=as_of,
                             costs=costs,profile=calendar_profile(metadata),commissions=commissions,
                             contract_size=metadata['contract_size'])
    report.update(data_sha256=fingerprint,declared_provenance=metadata,slippage_points_per_side=10,
                  commission_source='User-requested hypothetical sensitivity, not verified broker fees')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    for scenario in report['scenarios']:
        fee=scenario['commission_usd_round_trip_per_lot']
        lines=['# Preliminary research only', '', f'Commission USD {fee}/lot round-trip', '']
        for key in ('all_selected_segments','largest_segment_only'):
            lines.extend([key,'| model | trades | win rate | net R | Sharpe | max DD R |','|---|---|---|---|---|---|'])
            for row in scenario[key]:
                lines.append('| '+' | '.join(str(row[k]) for k in ('model','trades','win_rate','net_r','sharpe','max_dd'))+' |')
        lines.append(scenario['verdict']+': '+str(scenario['positive_observed_models']))
        output.with_name(output.stem+f'-commission-{fee}.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
        print(json.dumps({'timeframe':metadata['timeframe'],'commission':fee,'verdict':scenario['verdict'],
                          'models':scenario['positive_observed_models'],'models_with_trades':report['models_with_any_trades']},ensure_ascii=False),flush=True)
    return report


def main():
    parser=argparse.ArgumentParser()
    inputs=parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--csv',type=Path)
    inputs.add_argument('--data-root',type=Path,help='Read M5/*.csv and H1/*.csv with .metadata.json sidecars')
    parser.add_argument('--metadata',type=Path)
    parser.add_argument('--preliminary-segments',action='store_true')
    parser.add_argument('--commission-scenarios',type=float,nargs='+',default=[0.,3.,7.])
    parser.add_argument('--output',type=Path,default=ROOT/'reports/edge-test.json')
    parser.add_argument('--output-dir',type=Path,default=ROOT/'reports/edge-native')
    args=parser.parse_args()
    if args.data_root:
        if args.preliminary_segments:parser.error('--preliminary-segments requires an explicit --csv and --metadata')
        if args.metadata:parser.error('--metadata is only valid with --csv')
        run_directory(args.data_root,args.output_dir,time.time())
    else:
        if not args.metadata:parser.error('--csv requires --metadata')
        metadata=json.loads(args.metadata.read_text(encoding='utf-8'))
        if args.preliminary_segments:
            run_preliminary(args.csv,metadata,args.output,time.time(),args.commission_scenarios)
        else:run(args.csv,metadata,args.output,time.time())


if __name__=='__main__':
    main()
