"""Audit existing signal prices and exact-data resampling without cost changes."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from nexus.research_resampling import aggregate_m1
from nexus.strategies import REGISTRY
from nexus.walkforward import evaluate_history


def run(input_path, study_path, output_path):
    raw=input_path.read_bytes();capture=json.loads(raw);study=json.loads(study_path.read_text(encoding='utf-8'))
    fingerprint=hashlib.sha256(raw).hexdigest()
    if fingerprint!=study['input_sha256']:raise ValueError('Input/study identity mismatch')
    positive=[]
    for model in study['results']:
        cases=[s for fold in model['folds'] for s in fold['skipped'] if 'target_net_price_scenario' in s]
        before=[];after=[]
        for s in cases:
            entry=s['next_open_bid']+(s['spread_price'] if s['side']=='BUY' else 0.)
            net=(s['target']-entry if s['side']=='BUY' else entry-s['target'])-s['commission_price_units']
            before.append(net);after.append(s['target_net_price_scenario'])
        positive.append({'model':model['strategy_id'],'priced_rejected_signals':len(cases),
                         'positive_before_slippage':sum(x>0 for x in before),
                         'positive_after_slippage':sum(x>0 for x in after),
                         'definition':'Same raw signals; spread and commission unchanged; target scenario, not expected return'})
    frames=[]
    for tf in ('M5','H1'):
        rows=aggregate_m1(capture['bars'],tf,capture['as_of'])
        results=[]
        for sid in sorted(REGISTRY):
            try:
                measured=evaluate_history(rows,sid,symbol=capture['symbol'],timeframe=tf,as_of=capture['as_of'],
                                          costs=capture['costs'],context={'data_kind':'broker','tick_size':capture['costs']['point']})
                results.append({'model':sid,'status':'MEASURED',**measured['review']})
            except ValueError as error:
                if str(error)!='At least 500 completed candles required':raise
                results.append({'model':sid,'status':'NOT_EVALUATED_INSUFFICIENT_HISTORY',
                                'bars':len(rows),'required':500,'trades':None,'win_rate':None,
                                'sharpe':None,'max_drawdown_r':None,'reason':str(error)})
        frames.append({'timeframe':tf,'completed_bars':len(rows),'models':results})
    report={'input_sha256':fingerprint,'entry_order_type':'MARKET_NEXT_OPEN',
            'live_order_type':'TRADE_ACTION_DEAL + ORDER_TYPE_BUY/SELL',
            'limit_order_model':False,'entry_slippage_price':capture['costs']['slippage_price'],
            'costs_changed':False,'zones_changed':False,'positive_target_scenarios':positive,
            'resampled_frames':frames,'orders_sent':0,'profitability_inference':False,
            'scope':'Base registry model replay, not full multi-school fast-router execution plan'}
    output_path.write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps({'entry_order_type':report['entry_order_type'],'priced_signals':sum(x['priced_rejected_signals'] for x in positive),
                      'positive_before_slippage':sum(x['positive_before_slippage'] for x in positive),
                      'positive_after_slippage':sum(x['positive_after_slippage'] for x in positive),
                      'frames':[{'timeframe':x['timeframe'],'bars':x['completed_bars'],
                                 'not_evaluated':sum(y['status'].startswith('NOT_EVALUATED') for y in x['models'])} for x in frames]}))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,default=ROOT/'reports/walkforward-input.json')
    parser.add_argument('--study',type=Path,default=ROOT/'reports/walkforward-review.json')
    parser.add_argument('--output',type=Path,default=ROOT/'reports/execution-assumptions.json')
    args=parser.parse_args();run(args.input,args.study,args.output)
