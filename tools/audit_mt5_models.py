"""Read-only closed-bar model review. Never calls risk or an order method."""
import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from nexus.broker import MT5Broker
from nexus.learning import load_library
from nexus.strategies import analyze_all
from nexus.timeframes import bar_close_time


def run(terminal):
    rules=load_library(ROOT)
    broker=MT5Broker(terminal)
    account=broker.account()
    if account['trade_mode']!=0:raise ValueError('This audit is restricted to a Demo account')
    names={s['name'] for s in broker.symbols()};rows=[];errors=[]
    partners={'EURUSD':'GBPUSD','XAUUSD':'XAGUSD','US500':'US100','BTCUSD':'ETHUSD'}
    for symbol, partner_symbol in partners.items():
        if symbol not in names:continue
        for tf in ('M1','M5','H1','D1'):
            try:
                bars=broker.bars(symbol,tf,1500 if tf=='M1' else 300)
                if not bars:raise ValueError('No completed broker history')
                # Historical observation clock, never a current execution signal.
                now=bar_close_time(bars[-1]['time'],tf)
                info=broker.symbol(symbol)
                context={'data_kind':'broker','symbol_info':info}
                partner=partner_symbol
                if partner in names:
                    context.update(partner_symbol=partner,partner_bars=broker.bars(partner,tf,len(bars)))
                context['daily_bars']=broker.bars(symbol,'D1',2600)
                cards=analyze_all(symbol,tf,bars,now,context)
                rows.append({'symbol':symbol,'timeframe':tf,'bars':len(bars),'historical_as_of':now,
                             'status_counts':dict(Counter(c['status'] for c in cards)),
                             'models':[{**{k:c.get(k) for k in ('strategy_id','version','status','direction','actionable','conditions_missing','assumptions')},
                                        'rule_revision':rules[c['strategy_id']]['revision']} for c in cards]})
            except Exception as exc:
                logging.getLogger(__name__).exception("Handled boundary failure")
                errors.append({'symbol':symbol,'timeframe':tf,'reason':str(exc)})
    report={'type':'HISTORICAL_COMPLETED_MT5_BAR_MODEL_REVIEW','orders_sent':0,
            'profitability_test':False,'account_mode':'DEMO','results':rows,'data_errors':errors,
            'source_hashes':next(iter(rules.values()))['source_hashes'],
            'evaluations':sum(len(r['models']) for r in rows)}
    (ROOT/'reports/mt5-rule-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'samples':len(rows),'evaluations':report['evaluations'],'orders_sent':0,'data_errors':errors}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--terminal',required=True)
    run(parser.parse_args().terminal)
