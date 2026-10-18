"""Durable human/AI-readable research mirror of the authoritative SQLite ledger.

This module cannot propose/send trades or modify rules/weights/risk. A negative
outcome is a review case, not proof of an implementation mistake. The mirror is
never read as a source of executable policy or used to relabel missing evidence.
"""
import hashlib
import json
import math
import os
import tempfile
from pathlib import Path

from .learning import digest


def review_cases(outcomes, evaluation):
    cases = []; groups = {}
    for row in outcomes:
        identity = row.get('outcome_id')
        if not identity:
            continue
        reference = {k:row.get(k) for k in ('outcome_id', 'strategy_id', 'revision', 'symbol', 'timeframe',
                       'regime', 'closed_at', 'protocol_revision', 'execution_style',
                       'scalp_policy_revision', 'execution_policy_revision')}
        if not row.get('eligible'):
            cases.append(dict(reference, category='EXCLUDED_EVIDENCE',
                              evidence=list(row.get('exclusions') or []), action='REPAIR_OR_VERIFY_DATA_NOT_TRADE_POLICY'))
            continue
        net_r = row.get('net_r')
        if isinstance(net_r, bool) or not isinstance(net_r, (int, float)) or not math.isfinite(net_r):
            continue
        key = tuple(reference[k] for k in ('strategy_id', 'revision', 'symbol', 'timeframe', 'regime',
                    'protocol_revision', 'execution_style', 'scalp_policy_revision', 'execution_policy_revision'))
        groups.setdefault(key, []).append((row.get('closed_at',0), identity, net_r))
        if net_r < 0:
            cases.append(dict(reference, category='LOSING_OUTCOME', net_r=net_r, net=row.get('net'),
                              causal_error_proven=False, action='REVIEW_ENTRY_EXIT_COSTS_AND_CONTEXT'))
    streaks = []
    for key, values in groups.items():
        ordered = sorted(values); count = 0
        for _, _, result in reversed(ordered):
            if result >= 0: break
            count += 1
        if count >= 3:
            streaks.append({'strategy_id': key[0], 'revision': key[1], 'symbol': key[2], 'timeframe': key[3],
                                'regime': key[4], 'protocol_revision': key[5], 'execution_style': key[6],
                                'scalp_policy_revision': key[7], 'execution_policy_revision': key[8],
                                'consecutive_losses': count, 'last_outcome_id': ordered[-1][1],
                                'action': 'RESEARCH_REVIEW_NOT_AUTOMATIC_RULE_CHANGE'})
    return {'cases':sorted(cases,key=lambda x:(x.get('closed_at') or 0,x['outcome_id']))[-200:],
            'case_count':len(cases), 'case_window_limit':200,
            'cases_truncated':len(cases)>200, 'loss_streak_reviews':streaks,
            'deterioration_reviews':[m for m in evaluation.get('models',[]) if m.get('status')=='REVIEW_DETERIORATION'],
            'loss_is_implementation_error':False, 'automatic_live_changes':False,
            'full_case_source':'SQLite learning_outcomes and immutable learning_outcome_revisions'}


def persist(learner, account, directory, now, evaluation=None):
    """Atomic account-scoped mirror; old file survives any pre-replace failure.

    SQLite is the recovery source. This JSON contains no raw account identity,
    credentials or tokens. Rule/outcome identifiers remain local research keys.
    """
    account_digest = hashlib.sha256(account.encode('utf-8')).hexdigest()
    evaluation = evaluation if evaluation is not None else learner.snapshot(account)
    with learner.store.lock:
        outcomes = [{'outcome_id':r['id'], **json.loads(r['payload'])}
                    for r in learner.store.db.execute('SELECT id,payload FROM learning_outcomes WHERE account=? ORDER BY at,id',(account,))]
        corrections = learner.store.db.execute('SELECT COUNT(*) FROM learning_outcome_revisions WHERE account=?',(account,)).fetchone()[0]
        faults = {r['event']:r['count'] for r in learner.store.db.execute(
            "SELECT event,COUNT(*) AS count FROM audit WHERE event IN ('ERROR','ANALYSIS_ERROR','QUANT_ERROR','LEARNING_ERROR','LEARNING_FILE_ERROR','WORKER_ERROR','RECONCILIATION_ERROR') GROUP BY event")}
    review = review_cases(outcomes, evaluation)
    content = {'schema':'quant-learning-memory-v1', 'account_digest':account_digest,
               'authoritative_store':'SQLite ledger; this mirror cannot restore or grant trading authority',
               'rule_revisions':{k:v['revision'] for k,v in sorted(learner.library.items())},
               'evaluation':evaluation, 'review':review, 'outcome_correction_records':corrections,
               'operational_faults':{'scope':'application-wide counts; not attributed to a trade or account',
                                     'counts':faults,'full_evidence_source':'SQLite audit; no causal loss attribution'},
               'automatic_live_changes':False, 'external_upload':False}
    path = Path(directory)/account_digest/'learning-state.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    fingerprint = digest(content)
    try:
        previous = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(previous,dict):raise ValueError('Invalid learning mirror document')  # noqa: TRY004 -- Keep ValueError validation contract consumed by API handlers and existing risk tests.
        prior_digest = previous.pop('revision',None)
        prior_payload = {k:v for k,v in previous.items() if k!='saved_at'}
        if prior_digest == digest(previous) and digest(prior_payload) == fingerprint:
            return {'ok':True,'file':str(path),'content_revision':fingerprint,'written':False,'mode':'SHADOW_ONLY'}
    except (OSError,ValueError,TypeError):
        pass
    payload = {**content, 'saved_at':now}
    payload['revision'] = digest(payload)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,
                                         prefix='.learning-',suffix='.tmp',delete=False) as stream:
            temp_path=Path(stream.name)
            json.dump(payload,stream,ensure_ascii=False,allow_nan=False,indent=2)
            stream.flush();os.fsync(stream.fileno())
        os.replace(temp_path,path)
    finally:
        if temp_path is not None and temp_path.exists():temp_path.unlink()
    return {'ok':True,'file':str(path),'content_revision':fingerprint,'written':True,'mode':'SHADOW_ONLY'}


def read_snapshot(directory, account):
    account_digest=hashlib.sha256(account.encode('utf-8')).hexdigest()
    path=Path(directory)/account_digest/'learning-state.json'
    payload=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(payload,dict):raise ValueError('Learning mirror fingerprint or account mismatch')  # noqa: TRY004 -- Keep ValueError validation contract consumed by API handlers and existing risk tests.
    revision=payload.pop('revision',None)
    if payload.get('schema')!='quant-learning-memory-v1' or payload.get('account_digest')!=account_digest or digest(payload)!=revision:
        raise ValueError('Learning mirror fingerprint or account mismatch')
    return {**payload,'revision':revision}
