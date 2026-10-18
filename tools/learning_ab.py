"""Paired held-out economic review. No live policy writer or broker authority."""
import argparse
import hashlib
import json
import math
import random
import statistics
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from nexus.learning import (
    CHART_FEATURE_NAMES,
    CHART_MODEL_POLICY,
    _execution_context,
    _safe_probability,
    _validated_chart_features,
)


def finite(value):
    return type(value) in (int,float) and math.isfinite(value)


def summarize(values,selected):
    peak=equity=drawdown=0.
    for value in values:
        equity+=value;peak=max(peak,equity);drawdown=max(drawdown,peak-equity)
    if not math.isfinite(equity) or not math.isfinite(drawdown):raise ValueError('Economic numeric range exceeded')
    return {'net_r':equity,'mean_r_per_opportunity':statistics.fmean(values) if values else None,
            'trades':len(selected),'win_rate':sum(x>0 for x in selected)/len(selected) if selected else None,
            'max_drawdown_r':drawdown}


def paired_review(rows,training_closed_through,*,draws=2000,block_size=5,seed=2026):
    if not finite(training_closed_through):raise ValueError('Finite training cutoff required')
    if type(draws) is not int or draws<100 or type(block_size) is not int or block_size<1:
        raise ValueError('Explicit bootstrap draws and block size required')
    seen=set();previous=-math.inf;before=[];after=[];selected_before=[];selected_after=[]
    for row in rows:
        required=('entry_at','closed_at','predicted_at','net_r','before_probability','after_probability')
        if any(not finite(row.get(key)) for key in required):raise ValueError('Finite aligned held-out economic record required')
        identity=row.get('outcome_id')
        if not isinstance(identity,str) or not identity or identity in seen:raise ValueError('Unique outcome identity required')
        seen.add(identity)
        if not training_closed_through<row['predicted_at']<=row['entry_at']<row['closed_at'] or row['entry_at']<previous:
            raise ValueError('Held-out prediction/label timing violated')
        previous=row['entry_at']
        if any(not 0<=row[key]<=1 for key in ('before_probability','after_probability')):raise ValueError('Invalid probability')
        use_before=row['before_probability']>=.5;use_after=row['after_probability']>=.5
        before.append(row['net_r'] if use_before else 0.);after.append(row['net_r'] if use_after else 0.)
        if use_before:selected_before.append(row['net_r'])
        if use_after:selected_after.append(row['net_r'])
    first=summarize(before,selected_before);last=summarize(after,selected_after)
    delta=[b-a for a,b in zip(before,after,strict=True)]
    randomizer=random.Random(seed);means=[]
    if delta:
        for _ in range(draws):
            sampled=[]
            while len(sampled)<len(delta):
                start=randomizer.randrange(max(1,len(delta)-block_size+1))
                sampled.extend(delta[start:start+block_size])
            means.append(statistics.fmean(sampled[:len(delta)]))
        means.sort();interval=[means[int(.025*(draws-1))],means[int(.975*(draws-1))]]
        difference=statistics.fmean(delta)
    else:interval=[None,None];difference=None
    decision=('REJECT_INSUFFICIENT' if difference is None else 'REJECT_DEGRADATION' if difference<0 else
              'REJECT_INSUFFICIENT' if len(rows)<30 or len(selected_after)<30 else
              'REJECT_UNCERTAIN' if interval[0]<=0 else 'RESEARCH_CANDIDATE')
    return {'before':first,'after':last,'mean_difference_r':difference,'paired_block_bootstrap_95':interval,
            'opportunities':len(rows),'bootstrap_draws':draws,'block_size':block_size,'seed':seed,
            'same_observed_net_outcome_and_costs_for_both':True,'threshold':.5,
            'sandbox_decision':decision,'execution_authority':False,'live_policy_changed':False,
            'limitations':['Conditional block-bootstrap interval, not proof of causality or independence',
                           'Abstention is zero per opportunity; this is not equal exposure or a portfolio simulation',
                           'No threshold tuning on held-out outcomes or automatic promotion']}


def evaluate_snapshot(snapshot):
    results=[]
    for model in snapshot['evaluation']['chart_learning']['models']:
        if model.get('status')!='EVALUATED_SHADOW':
            results.append({'strategy_id':model['strategy_id'],'status':'NOT_EVALUATED','samples':model['samples']})
            continue
        context=tuple(model.get(key) for key in ('protocol_revision','execution_style','scalp_policy_revision','execution_policy_revision'))
        group=[]
        for row in snapshot['outcomes']:
            if row.get('eligible') is not True or (row.get('strategy_id'),row.get('revision'),row.get('symbol'),row.get('timeframe'))!=(model['strategy_id'],model['revision'],model['symbol'],model['timeframe']):continue
            feature,error=_validated_chart_features(row.get('chart_features'),row.get('symbol'),row.get('timeframe'),row.get('entry_data_time'),row.get('intent_created_at'),row.get('entry_at'))
            if error or _execution_context(row)!=context or not finite(row.get('net_r')) or not finite(row.get('closed_at')):continue
            group.append({**row,'chart_features':feature})
        group.sort(key=lambda row:(row['entry_data_time'],row['closed_at'],row.get('outcome_id','')))
        holdout=group[int(len(group)*CHART_MODEL_POLICY['train_fraction']):]
        if len(holdout)!=model['holdout_samples']:raise ValueError('Frozen model/export sample alignment changed')
        pairs=[]
        for row in holdout:
            standardized={name:max(-10.,min(10.,(row['chart_features']['values'][name]-model['normalizer']['means'][name])/model['normalizer']['scales'][name])) for name in CHART_FEATURE_NAMES}
            probability=_safe_probability(model['intercept']+math.fsum(model['coefficients'][name]*standardized[name] for name in CHART_FEATURE_NAMES))
            pairs.append({'outcome_id':row['outcome_id'],'entry_at':row['entry_at'],'closed_at':row['closed_at'],
                          'predicted_at':row['entry_data_time'],'net_r':row['net_r'],
                          'before_probability':model['baseline_probability'],'after_probability':probability})
        results.append({'strategy_id':model['strategy_id'],'revision':model['revision'],
                        'evaluation_fingerprint':model['evaluation_fingerprint'],
                        **paired_review(pairs,model['training_closed_through'])})
    return {'models':results,'execution_authority':False,'profitability_proven':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--input',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();blob=Path(args.input).read_bytes()
    result=evaluate_snapshot(json.loads(blob));result['input_sha256']=hashlib.sha256(blob).hexdigest()
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps({'models':len(result['models']),'execution_authority':False}))
