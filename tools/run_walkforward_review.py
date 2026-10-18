"""Read-only MT5 capture and fixed-rule OOS review; never sends orders."""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from nexus.broker import MT5Broker
from nexus.strategies import REGISTRY
from nexus.timeframes import bar_close_time
from nexus.walkforward import evaluate_history


def run(args):
    broker=MT5Broker(args.terminal)
    try:
        if broker.account().get('trade_mode')!=0:raise ValueError('Read-only review requires Demo account')
        info=broker.symbol(args.symbol)
        bars=broker.bars(args.symbol,args.timeframe,max(args.capture_count,args.count*2))
        segments=[];current=[]
        for row in bars:
            if current and row['time']!=bar_close_time(current[-1]['time'],args.timeframe):
                segments.append(current);current=[]
            current.append(row)
        segments.append(current)
        eligible=[segment for segment in segments if len(segment)>=args.count]
        if not eligible:
            diagnostic={'symbol':args.symbol,'timeframe':args.timeframe,'requested':args.count,
                        'returned':len(bars),'largest_contiguous':max(map(len,segments),default=0),
                        'segments':len(segments),'orders_sent':0,'fabricated_candles':0}
            (ROOT/'reports/walkforward-data-gap.json').write_text(json.dumps(diagnostic,indent=2),encoding='utf-8')
            raise ValueError('No real contiguous series long enough; candles are never fabricated')
        rows=eligible[-1][-args.count:]
        if info['currency_profit']!=broker.account()['currency']:
            raise ValueError('Commission conversion requires matching account/profit currency for this review')
        costs={'point':info['point'],'slippage_price':args.slippage_points*info['point'],
               'commission_per_unit':args.commission_per_lot/info['trade_contract_size'],
               'commission_known':True}
        capture={'symbol':args.symbol,'timeframe':args.timeframe,'as_of':time.time(),'bars':rows,
                 'costs':costs,'cost_policy':'explicit scenario; commission is not verified historical broker fee',
                 'data_kind':'broker','orders_sent':0}
        blob=json.dumps(capture,ensure_ascii=False,sort_keys=True,allow_nan=False)
        fingerprint=hashlib.sha256(blob.encode()).hexdigest()
        (ROOT/'reports/walkforward-input.json').write_text(blob,encoding='utf-8')
        results=[]
        for sid in sorted(REGISTRY):
            result=evaluate_history(rows,sid,symbol=args.symbol,timeframe=args.timeframe,as_of=capture['as_of'],
                                    costs=costs,context={'data_kind':'broker','tick_size':info['trade_tick_size']})
            results.append(result)
            print(json.dumps({'model':sid,**result['review']}),flush=True)
        report={'type':'FIXED_RULE_CHRONOLOGICAL_REVIEW','input_sha256':fingerprint,
                'symbol':args.symbol,'completed_bars':len(rows),'costs':costs,
                'cost_policy':capture['cost_policy'],'execution_authority':False,'orders_sent':0,
                'auxiliary_data':'partner/daily/order-book unavailable in this capture; applicable models abstain',
                'results':results}
        (ROOT/'reports/walkforward-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
        lines=['| model | nonoverlapping OOS folds | net R | trades | win rate | max DD R | trade Sharpe (not annualized) |',
               '|---|---|---|---|---|---|---|']
        for item in results:
            m=item['review']
            lines.append(f"| {item['strategy_id']} | {m['nonoverlapping_test_folds']} | {m['net_r']:.6f} | {m['trades']} | {m['win_rate']} | {m['max_drawdown_r']:.6f} | {m['sharpe_trade_nonannualized']} |")
        (ROOT/'reports/walkforward-summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    finally:broker.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--terminal',required=True)
    parser.add_argument('--symbol',default='BTCUSD')
    parser.add_argument('--timeframe',default='M1')
    parser.add_argument('--count',type=int,default=600)
    parser.add_argument('--capture-count',type=int,default=2000)
    parser.add_argument('--commission-per-lot',type=float,required=True)
    parser.add_argument('--slippage-points',type=float,required=True)
    run(parser.parse_args())
