"""Deterministic model invariants on all MT5 periods; no broker or orders.

Generated bars are test data, not trading performance. The report deliberately
does not qualify a strategy or measure profitability.
"""
import copy
import json
import math
import random
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from nexus.learning import load_library
from nexus.school_catalog import catalog
from nexus.strategies import REGISTRY, analyze_all
from nexus.timeframes import PERIODS, bar_close_time, month_start


def bars(tf,kind):
    rng=random.Random(932+kind)
    start=datetime(2008,1,1,tzinfo=UTC).timestamp()
    value=100.
    rows=[]
    for i in range(160):
        movement=(.12 if kind==0 else -.12 if kind==1 else math.sin(i/5)*.18 if kind==2 else rng.uniform(-.8,.8))
        close=value+movement
        rows.append({'time': month_start(start,i) if tf=='MN1' else start+i*PERIODS[tf],
            'open': value,'close': close,'high': max(value,close)+rng.uniform(.08,.35),
            'low': min(value,close)-rng.uniform(.08,.35),'tick_volume': 100+rng.randrange(80),'real_volume': 0,'spread': 2})
        value=close
    return rows


def run():
    document=catalog(ROOT);rules=load_library(ROOT)
    mapped={m for s in document['schools'] for m in s['strategy_ids']}
    failures=[];counts={sid:Counter() for sid in REGISTRY};evaluations=0
    for sid,meta in REGISTRY.items():
        if sid not in mapped or rules[sid]['version']!=meta['version'] or meta['contract']['rule_version']!=meta['version']:
            failures.append({'model':sid,'invariant':'catalog_contract_version_mapping'})
    for tf in PERIODS:
        for kind in range(4):
            rows=bars(tf,kind)
            for end in (80,120,160):
                sample=rows[:end];now=bar_close_time(sample[-1]['time'],tf)
                partner=copy.deepcopy(sample)
                context={'data_kind':'synthetic','partner_symbol':'PARTNER','partner_bars':partner,
                         'symbol_info':{'currency_base':'EUR','currency_profit':'USD'},
                         'anchor_time':sample[max(0,end-20)]['time']}
                cards=analyze_all('PRIMARY',tf,sample,now,context)
                for card in cards:
                    sid=card['strategy_id'];counts[sid][card['status']]+=1;evaluations+=1
                    json.dumps(card,allow_nan=False)
                    if card['status'] in ('PARTIAL','UNIMPLEMENTED','DATA_INVALID'):
                        failures.append({'model':sid,'timeframe':tf,'kind':kind,'invariant':'valid_data_contract','status':card['status']})
                    if card['actionable']:
                        entry=card['entry']['price'];stop=card['stop']['price'];side=card['direction']
                        targets=[t['price'] for t in card['targets']]
                        valid=all(math.isfinite(p) and p>0 for p in [entry,stop,*targets])
                        valid=valid and (stop<entry<min(targets) if side=='BUY' else max(targets)<entry<stop)
                        invalidation=card.get('invalidation')
                        if invalidation:valid=valid and (entry>=invalidation['price'] if side=='BUY' else entry<=invalidation['price'])
                        if not valid:failures.append({'model':sid,'timeframe':tf,'kind':kind,'invariant':'actionable_price_plan','card':card})
                future=dict(sample[-1],time=now if tf!='MN1' else month_start(sample[-1]['time'],1))
                future_cards=analyze_all('PRIMARY',tf,sample+[future],now,context)
                for c in future_cards:
                    if c['status']!='DATA_INVALID' or c['actionable']:
                        failures.append({'model':c['strategy_id'],'timeframe':tf,'invariant':'future_bar_abstention'})
    report={'report_type':'SYNTHETIC_MODEL_INVARIANTS','orders_sent':0,'profitability_test':False,
            'all_schools_complete':False,'models':len(REGISTRY),'schools':len(document['schools']),
            'school_rules':sum(len(s['rule_records']) for s in document['schools']),
            'timeframes':list(PERIODS),'evaluations':evaluations,'future_data_checks':evaluations,
            'source_hashes':next(iter(rules.values()))['source_hashes'],'failed_checks':failures,
            'per_model':[{'id':sid,'version':REGISTRY[sid]['version'],'revision':rules[sid]['revision'],
                          'inputs':REGISTRY[sid]['data_requirements'],'statuses':dict(counts[sid])} for sid in REGISTRY],
            'passed':not failures}
    # Passing a neutral/waiting output cannot demonstrate that an entry branch
    # is correct. Make the limitation machine-readable instead of awarding
    # complete coverage from a clean aggregate invariant result.
    report['trigger_coverage']={
        'scope':'only the generated samples in this report, not the unit-test suite',
        'models_with_ready_output':[sid for sid in REGISTRY if counts[sid]['READY']>0],
        'models_without_ready_output':[sid for sid in REGISTRY if counts[sid]['READY']==0],
        'complete_entry_branch_coverage':False,
        'profitability_proven':False}
    path=ROOT/'reports'/'rule-invariants.json'
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('models','schools','evaluations','future_data_checks','passed')}))
    for f in failures[:8]:print(json.dumps(f,ensure_ascii=True))
    return 0 if not failures else 1


if __name__=='__main__':sys.exit(run())
