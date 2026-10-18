"""Explicit preliminary segment research. Never grants execution qualification."""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

from .quant import metrics, walk_forward
from .strategies import REGISTRY, validate_bars
from .timeframes import PERIODS, bar_close_time
from .trading_calendar import expected_closure_gap, validate_profile
from .walkforward import LookaheadBiasError


def split_segments(bars, timeframe, profile):
    validate_profile(profile)
    if not bars:return []
    segments=[[bars[0]]];seconds=PERIODS[timeframe]
    for row in bars[1:]:
        previous=segments[-1][-1]
        if row['time']<=previous['time']:raise ValueError('Segment input must be strictly chronological')
        close=bar_close_time(previous['time'],timeframe)
        if close==row['time'] or expected_closure_gap(close,row['time'],seconds,profile):
            segments[-1].append(row)
        else:segments.append([row])
    return segments


def reprice(trades, commission_per_unit):
    if not math.isfinite(commission_per_unit) or commission_per_unit<0:raise ValueError('Invalid commission scenario')
    result=[]
    for trade in trades:
        risk=abs(trade['entry']-trade['stop'])
        if risk<=0:raise ValueError('Positive structural price risk required')
        net=trade['gross_price_pnl']-commission_per_unit
        result.append({**trade,'commission_price_units':commission_per_unit,'net_price_pnl':net,'r':net/risk})
    return result


def summarize(trades):
    result=metrics(trades);values=[row['r'] for row in trades]
    if len(values)>1:
        mean=math.fsum(values)/len(values)
        variance=math.fsum((value-mean)**2 for value in values)/(len(values)-1)
        sharpe=mean/math.sqrt(variance) if variance>0 else None
    else:sharpe=None
    return {'trades':len(trades),'win_rate':result['sample_win_fraction'],'net_r':result['net_r'],
            'sharpe':sharpe,'max_dd':result['max_drawdown_r']}


def evaluate_segments(bars, *, symbol, timeframe, as_of, costs, profile, commissions, contract_size):
    for row in bars:
        if bar_close_time(row['time'],timeframe)>as_of:raise LookaheadBiasError('Future or unfinished segment candle')
    validate_bars(bars,timeframe,as_of)
    if not bars:raise ValueError('No actual candles available')
    if not math.isfinite(contract_size) or contract_size<=0:raise ValueError('Invalid contract size')
    if not commissions or any(not math.isfinite(c) or c<0 for c in commissions):raise ValueError('Explicit commission scenarios required')
    segments=split_segments(bars,timeframe,profile)
    largest=max(range(len(segments)),key=lambda i:len(segments[i]))
    selected=[i for i,s in enumerate(segments) if len(s)>=200]
    fallback=not selected
    if fallback:selected=[largest]
    inventory=[{'segment':i,'bars':len(s),'first_time':s[0]['time'],'last_time':s[-1]['time'],
                'selected':i in selected,'largest':i==largest} for i,s in enumerate(segments)]
    base={sid:[] for sid in REGISTRY};folds=[]
    for sid in sorted(REGISTRY):
        for index in selected:
            segment=segments[index];n=len(segment)
            train=min(250,max(1,n//2));test=min(100,max(1,(n-train-12)//2))
            # Configuration is frozen from segment length before examining outcomes.
            result=walk_forward(segment,sid,symbol,timeframe,
                config={**costs,'commission_per_unit':0.,'train_bars':train,'test_bars':test,'embargo_bars':12},
                data_kind='broker',context={'tick_size':costs['point'],'calendar_profile':profile})
            foldrows=[{'segment':index,**fold} for fold in result['folds']]
            for fold in foldrows:
                base[sid].extend({'segment':index,**trade} for trade in fold['trades'])
            folds.append({'model':sid,'segment':index,'train_bars':train,'test_bars':test,
                          'folds':len(foldrows),'signals':sum(f['signals'] for f in foldrows),
                          'rejections':sum(len(f['skipped']) for f in foldrows),
                          'train_test_windows':[{k:f[k] for k in ('train_end_exclusive','test_start_index','test_end_exclusive')} for f in foldrows]})
        print(f"PRELIMINARY_PROGRESS {timeframe} {sid} trades={len(base[sid])}",flush=True)
    scenarios=[]
    for commission in commissions:
        rows=[];largest_rows=[]
        for sid in sorted(REGISTRY):
            trades=reprice(base[sid],commission/contract_size)
            rows.append({'model':sid,**summarize(trades)})
            largest_rows.append({'model':sid,**summarize([t for t in trades if t['segment']==largest])})
        positives=[r['model'] for r in rows if r['trades']>0 and r['net_r']>0]
        scenarios.append({'commission_usd_round_trip_per_lot':commission,'all_selected_segments':rows,
                          'largest_segment_only':largest_rows,'positive_observed_models':positives,
                          'verdict':'PRELIMINARY_EDGE' if positives else 'PRELIMINARY_NO_EDGE'})
    return {'status':'PRELIMINARY_RESEARCH_ONLY','execution_authority':False,'qualified':False,'live_changes':False,
            'timeframe':timeframe,'symbol':symbol,'total_bars':len(bars),'segments':inventory,
            'selected_segments':len(selected),'fallback_largest_below_200':fallback,'models':len(REGISTRY),
            'models_with_any_trades':sum(bool(t) for t in base.values()),'scenarios':scenarios,'windows':folds,
            'base_trades':base,'costs':costs,'calendar_profile':profile,
            'repricing_proof_source_sha256':hashlib.sha256((Path(__file__).parent/'quant.py').read_bytes()).hexdigest(),
            'limitations':['Small disconnected samples; no statistical independence or portfolio claim',
                           'No positions or input bars carried across unexplained gaps',
                           'Fee repricing preserves entries/exits; quant.replay uses commission only in net PnL/diagnostics',
                           'PRELIMINARY_EDGE means positive observed net R with >=1 trade only; not a qualified edge',
                           'Largest segment is a subset of aggregate, not an independent confirmation',
                           'Per-model insufficient warmup may produce no signals; other-asset/daily context absent']}
