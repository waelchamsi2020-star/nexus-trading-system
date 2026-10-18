"""Completed-bar chronological research; no broker or order authority."""
from __future__ import annotations

import itertools
import math
import statistics

from .quant import walk_forward
from .strategies import validate_bars
from .timeframes import PERIODS, bar_close_time
from .trading_calendar import expected_closure_gap, validate_profile


class LookaheadBiasError(ValueError):
    """A sample contains information unavailable at the declared observation time."""


def evaluate_history(bars, strategy_id, *, symbol, timeframe, as_of, costs,
                     train_bars=250, test_bars=100, embargo_bars=12,
                     data_kind='broker', context=None):
    if isinstance(as_of,bool) or not isinstance(as_of,(int,float)) or not math.isfinite(as_of):
        raise ValueError('Finite observation time required')
    for row in bars:
        if bar_close_time(row['time'],timeframe)>as_of:
            raise LookaheadBiasError('Future or unfinished candle in walk-forward input')
    validated=validate_bars(bars,timeframe,as_of)
    if len(validated)<500:
        raise ValueError('At least 500 completed candles required')
    profile=validate_profile((context or {}).get('calendar_profile','CONTINUOUS'))
    for previous,current in itertools.pairwise(validated):
        if (bar_close_time(previous['time'],timeframe)!=current['time'] and
                not expected_closure_gap(bar_close_time(previous['time'],timeframe),current['time'],PERIODS.get(timeframe,0),profile)):
            raise ValueError('Walk-forward series has a time gap')
    required={'point','slippage_price','commission_per_unit','commission_known'}
    if not isinstance(costs,dict) or not required<=set(costs):
        raise ValueError('Explicit spread scale, slippage and commission policy required')
    result=walk_forward(validated,strategy_id,symbol,timeframe,
                        config={**costs,'train_bars':train_bars,'test_bars':test_bars,
                                'embargo_bars':embargo_bars},data_kind=data_kind,context=context)
    trades=[trade for fold in result['folds'] for trade in fold['trades']]
    values=[trade['r'] for trade in trades]
    deviation=statistics.stdev(values) if len(values)>1 else 0.
    result['review']={'completed_bars':len(validated),'nonoverlapping_test_folds':len(result['folds']),
                      'train_bars':train_bars,'test_bars':test_bars,'step_bars':test_bars,
                      'embargo_bars':max(12,embargo_bars),'net_r':result['metrics']['net_r'],
                      'trades':len(values),'win_rate':result['metrics']['sample_win_fraction'],
                      'max_drawdown_r':result['metrics']['max_drawdown_r'],
                      'sharpe_trade_nonannualized':statistics.fmean(values)/deviation if deviation else None,
                      'statistical_independence_established':False,'execution_authority':False,
                      'limitations':['Fixed rules, no parameter optimization in test windows',
                                     'Trade-R ratio is not annualized portfolio Sharpe',
                                     'Historical spread column and explicit commission/slippage scenario; no actual-fill claim']}
    result['legacy_qualification_status']=result['status']
    result['qualified']=False
    result['status']='RESEARCH_ONLY'
    return result
