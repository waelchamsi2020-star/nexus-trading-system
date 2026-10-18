"""Precomputed paired held-out outcomes; not a strategy generator or live writer."""
import math
import statistics


def evaluate_proposal(proposal, held_out_data):
    if not isinstance(proposal,dict) or not proposal.get('id'):raise ValueError('Saved research proposal required')
    before=[];after=[];seen=set()
    for row in held_out_data:
        identity=row.get('outcome_id')
        if not identity or identity in seen:raise ValueError('Unique paired outcome required')
        seen.add(identity)
        fields=('before_net_r','after_net_r','training_closed_at','predicted_at','entry_at','closed_at')
        if any(type(row.get(k)) not in (int,float) or not math.isfinite(row[k]) for k in fields):raise ValueError('Finite paired data required')
        if not row['training_closed_at']<row['predicted_at']<=row['entry_at']<row['closed_at']:raise ValueError('Held-out timing violated')
        if row.get('before_costs')!=row.get('after_costs') or not isinstance(row.get('before_costs'),dict):raise ValueError('Same explicit cost policy required')
        costs=row['before_costs']
        if set(costs)!={'commission','slippage_points','spread_points'} or costs.get('slippage_points')!=10 or any(type(x) not in (int,float) or not math.isfinite(x) or x<0 for x in costs.values()):raise ValueError('Explicit unchanged 10-point slippage policy required')
        before.append(row['before_net_r']);after.append(row['after_net_r'])
    def metric(values):
        std=statistics.stdev(values) if len(values)>1 else 0.
        return {'net_r':math.fsum(values),'trade_r_sharpe':statistics.fmean(values)/std if std else None}
    first,last=metric(before),metric(after)
    measured=len(before)>=30 and first['trade_r_sharpe'] is not None and last['trade_r_sharpe'] is not None
    degraded=last['net_r']<first['net_r'] or (measured and last['trade_r_sharpe']<first['trade_r_sharpe'])
    return {'status':'REJECT_DEGRADATION' if degraded else 'READY_FOR_RESEARCH_REVIEW' if measured else 'REJECT_INSUFFICIENT',
            'before':first,'after':last,'opportunities':len(before),'execution_authority':False,
            'live_mutation':False,'input_kind':'PRECOMPUTED_PAIRED_HELDOUT_RESEARCH'}
