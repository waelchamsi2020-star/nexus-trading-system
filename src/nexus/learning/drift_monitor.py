"""Training-fitted three-sigma monitoring, separate for every supplied context."""
from . import feature_drift_review


def monitor_schools(schools):
    rows=[];seen=set()
    for school in schools:
        key=(school['school_id'],school['revision'],school['symbol'],school['timeframe'])
        if key in seen:raise ValueError('Duplicate school context')
        seen.add(key)
        report=feature_drift_review(school['train'],school['heldout'],school['features'])
        alert=any(x['outside_three_training_std_fraction']>0 or x['constant_training_changed'] for x in report['features'])
        rows.append({'school_id':key[0],'revision':key[1],'symbol':key[2],'timeframe':key[3],
                     'alert':alert,'three_sigma_limits':report.get('training_control_limits',[]),
                     'status':'INSUFFICIENT' if not report['features'] else 'DRIFT_ALERT' if alert else 'NO_ALERT',
                     'execution_authority':False})
    return rows
