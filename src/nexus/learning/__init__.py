"""Versioned knowledge and observational learning. No broker or execution authority.

Closed, attributable trades are labels; waiting/rejected signals are NOT losses.
Outputs are research suggestions only. They cannot modify strategy code or risk.
"""
import hashlib
import json
import math
import re
import statistics
from pathlib import Path

from ..risk import cashflow_records, cost_uncertainties
from ..store import encode

LEARNING_SOURCE_MODULES=('learning/__init__.py','learning/proposals.py','learning/sandbox.py','learning/drift_monitor.py','learning_journal.py','risk.py','store.py')

LEGACY_KNOWLEDGE_DEPENDENCIES=('strategies.py','specialists.py','local_models.py','timeframes.py')
V2_KNOWLEDGE_DEPENDENCIES=LEGACY_KNOWLEDGE_DEPENDENCIES+('confluence.py','confluence_registry.py')
V3_KNOWLEDGE_DEPENDENCIES=V2_KNOWLEDGE_DEPENDENCIES+('indicators.py','extended_models.py')
KNOWLEDGE_DEPENDENCIES=V3_KNOWLEDGE_DEPENDENCIES+('config/models.yaml','config/models.schema.json')


def knowledge_dependencies(schema):
    if schema not in (1, 2, 3, 4):
        raise ValueError('Unknown knowledge dependency schema')
    return {1:LEGACY_KNOWLEDGE_DEPENDENCIES, 2:V2_KNOWLEDGE_DEPENDENCIES, 3:V3_KNOWLEDGE_DEPENDENCIES, 4:KNOWLEDGE_DEPENDENCIES}[schema]
CHART_FEATURE_NAMES=('return_1_atr','return_5_atr','ema_gap_atr','rsi_centered',
                     'close_location','efficiency_20','volatility_ratio_log','tick_activity_log')
CHART_MODEL_POLICY={'model_version':'chart-logistic-v1','feature_version':'ohlc-v1',
                    'evaluation_version':'chart-economic-review-v2','review_probability_threshold':.5,
                    'minimum_selected_holdout_outcomes':30,'calibration_bins':5,
                    'drift_review_version':'feature-location-shadow-v1',
                    'iterations':120,'learning_rate':.1,'l2':.05,'train_fraction':.7,
                    'minimum_samples':60,'minimum_train_samples':40,'holdout_minimum':12,
                    'standardized_clip':10.,'class_weight':'none','target':'net_r > 0 after costs',
                    'execution_context_grouping':['protocol_revision','execution_style','scalp_policy_revision','execution_policy_revision']}


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()).hexdigest()


def feature_drift_review(train_vectors, holdout_vectors, names):
    """Fixed descriptive input-shift alerts; no adaptation or trading authority."""
    if len(train_vectors)<2 or len(holdout_vectors)<2:
        return {'status':'INSUFFICIENT_DATA','execution_authority':False,'features':[]}
    if not names or len(set(names))!=len(names):
        raise ValueError('Unique drift feature names required')
    for vector in list(train_vectors)+list(holdout_vectors):
        if len(vector)!=len(names) or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in vector):
            raise ValueError('Finite aligned drift vectors required')
    features=[];limits=[]
    for index,name in enumerate(names):
        train=[v[index] for v in train_vectors];later=[v[index] for v in holdout_vectors]
        # Common numerical scaling only; never changes the classifier's fitted
        # normalizer. The mean/std ratio is invariant to this scaling.
        common=max(abs(x) for x in train+later) or 1.
        first=[x/common for x in train];last=[x/common for x in later]
        center=statistics.fmean(first);scale=statistics.pstdev(first)
        constant_changed=scale==0 and any(x!=first[0] for x in last)
        shift=(statistics.fmean(last)-center)/scale if scale else 0. if not constant_changed else None
        extreme_fraction=sum(abs((x-center)/scale)>3 for x in last)/len(last) if scale else float(constant_changed)
        numeric_valid=shift is None or math.isfinite(shift)
        if not numeric_valid:
            shift=None
        alert=constant_changed or not numeric_valid or (shift is not None and abs(shift)>=2) or extreme_fraction>=.25
        # Limits are fitted only on the chronological training partition.
        # Keep dimensional values separate from the unit-invariant diagnostics.
        mean=center*common;std=scale*common
        lower=(center-3*scale)*common;upper=(center+3*scale)*common
        bounds_valid=all(math.isfinite(x) for x in (mean,std,lower,upper))
        limits.append({'feature':name,'training_mean':mean if math.isfinite(mean) else None,
                       'training_std':std if math.isfinite(std) else None,
                       'lower':lower if bounds_valid else None,'upper':upper if bounds_valid else None,
                       'sigma_multiplier':3.,'status':'AVAILABLE' if bounds_valid else 'NUMERIC_RANGE_INVALID'})
        features.append({'feature':name,'standardized_mean_shift':shift,
                         'outside_three_training_std_fraction':extreme_fraction,
                         'constant_training_changed':constant_changed,'numeric_valid':numeric_valid,'alert':alert})
    return {'status':'RESEARCH_DRIFT_ALERT' if any(x['alert'] for x in features) else 'NO_ALERT_IN_SAMPLE',
            'version':'feature-location-shadow-v1','train_samples':len(train_vectors),'holdout_samples':len(holdout_vectors),
            'thresholds':{'absolute_mean_shift':2.,'outside_three_std_fraction':.25},
            'thresholds_tuned_on_holdout':False,'features':features,'training_control_limits':limits,'execution_authority':False,
            'automatic_normalizer_changes':False,'profitability_inference':False}


def verified_rule(value):
    """Copy the reference before accepting it: callers cannot rewrite a revision."""
    rule=json.loads(encode(value))
    revision=rule.pop('revision',None)
    if not revision or digest(rule)!=revision:
        raise ValueError('Knowledge rule fingerprint mismatch')
    if not isinstance(rule.get('id'),str) or not rule['id']:
        raise ValueError('Knowledge rule identity is missing')
    return {**rule,'revision':revision}


def load_library(root):
    path=Path(root)/'docs/knowledge/library.json'
    if not path.exists():raise ValueError('Knowledge reference unavailable')
    document=json.loads(path.read_text(encoding='utf-8'))
    dependency_schema=document.get('dependency_schema',1)
    dependencies=set(knowledge_dependencies(dependency_schema))
    if document.get('schema')!=1 or set(document.get('source_hashes',{}))!=dependencies:
        raise ValueError('Incomplete knowledge dependency manifest')
    result={}
    for item in document['rules']:
        rule=verified_rule(item)
        if rule.get('dependency_schema',1)!=dependency_schema:
            raise ValueError('Knowledge dependency schema mismatch')
        if rule.get('source_hashes')!=document['source_hashes']:
            raise ValueError('Knowledge dependency manifest mismatch')
        if rule['id'] in result:raise ValueError('Duplicate knowledge rule')
        result[rule['id']]=rule
    # All shared code participates in the revision, not just the entry function.
    for name,expected in document['source_hashes'].items():
        if name not in dependencies:
            raise ValueError('Unknown knowledge dependency')
        source=Path(root)/'docs/agent-rules/snapshot/nexus'/name
        if hashlib.sha256(source.read_bytes()).hexdigest()!=expected:
            raise ValueError('Knowledge source fingerprint mismatch')
    return result


def knowledge_export_sources(root,references):
    """Resolve immutable reference dependencies as inert, verified ZIP members.

    Earlier installations may have kept a revision without its shared source
    files. Report each gap rather than substituting today's implementation.
    Names and hashes are validated before they are used as filesystem paths.
    The returned bytes are the exact bytes verified, never imported or run.
    """
    archive=Path(root)/'docs/knowledge/sources'
    resolved_archive=archive.resolve()
    rules={}
    for value in references:
        rule=verified_rule(value)
        rules[rule['revision']]=rule
    files={};sources={};missing=[]
    for revision,rule in sorted(rules.items()):
        hashes=rule.get('source_hashes',{})
        if not isinstance(hashes,dict) or set(hashes)-set(KNOWLEDGE_DEPENDENCIES):
            raise ValueError('Unknown knowledge export dependency manifest')
        dependencies=knowledge_dependencies(rule.get('dependency_schema',1))
        for name in dependencies:
            expected=hashes.get(name)
            if name not in hashes:
                missing.append({'revision':revision,'rule_id':rule['id'],'name':name,
                                'sha256':None,'path':None,'reason':'missing_dependency_hash'})
                continue
            if not isinstance(expected,str) or re.fullmatch('[0-9a-f]{64}',expected) is None:
                raise ValueError('Invalid knowledge export dependency fingerprint')
            member=f'docs/knowledge/sources/{expected}-{name}'
            source=archive/f'{expected}-{name}'
            if not source.resolve().is_relative_to(resolved_archive):
                raise ValueError('Unsafe knowledge source archive path')
            if member not in files:
                try:blob=source.read_bytes()
                except FileNotFoundError:
                    missing.append({'revision':revision,'rule_id':rule['id'],'name':name,
                                    'sha256':expected,'path':member,'reason':'missing_source_archive'})
                    continue
                if hashlib.sha256(blob).hexdigest()!=expected:
                    raise ValueError('Knowledge source archive fingerprint mismatch')
                files[member]=blob
                sources[member]={'name':name,'sha256':expected,'path':member,'revisions':[]}
            sources[member]['revisions'].append(revision)
    manifest={'schema':1,'complete':not missing,'reference_revisions':len(rules),
              'completeness_scope':'shared dependency sources for exported rule revisions',
              'sources':[sources[member] for member in sorted(sources)],'missing':missing}
    return manifest,files


def _finite_number(value):
    if not isinstance(value,(int,float)) or isinstance(value,bool):return False
    try:return math.isfinite(value)
    except OverflowError:return False


def _effective_fill_time(deal):
    """Use declared MT5 millisecond precision only when both clocks agree.

    Missing precision retains the supplied seconds value. Invalid supplied
    milliseconds cannot be replaced by a guessed timestamp or a grace period.
    """
    seconds=deal.get('time')
    if not _finite_number(seconds) or seconds<=0:return None
    if 'time_msc' not in deal:return seconds
    milliseconds=deal['time_msc']
    if not _finite_number(milliseconds) or milliseconds<=0 or milliseconds!=math.floor(milliseconds):return None
    if seconds!=math.floor(seconds):return None
    precise=milliseconds/1000
    return precise if math.floor(precise)==seconds else None


def _unlinked_cost_proven_before_intent(record,created_at):
    """An unlinked old cost cannot belong to an intent not yet created.

    Preserve the veto for linked, owned or potentially late-posted costs. With
    seconds-only evidence, the entire timestamp second must precede creation.
    This concerns research labels only; account-wide risk accounting is intact.
    """
    deal=record['deal']
    if not _finite_number(created_at) or created_at<=0:return False
    if record['kind']=='TRADE' or record['owner_id'] or deal.get('magic',0)!=0:return False
    if deal.get('order') not in (None,0) or deal.get('position_id') not in (None,0):return False
    if str(deal.get('comment','')).startswith('NX:'):return False
    timestamp=_effective_fill_time(deal)
    if timestamp is None:return False
    if 'time_msc' not in deal:return math.floor(timestamp)+1<=created_at
    return timestamp<created_at


def _validated_chart_features(feature,symbol,timeframe,data_time,created_at,entry_at):
    """Accept only the original decision snapshot, never a later observation."""
    if feature is None:return None,'missing_entry_features'
    if not isinstance(feature,dict):return None,'invalid_feature_schema'
    if type(feature.get('schema')) is not int or feature['schema']!=1 or feature.get('feature_version')!='ohlc-v1':
        return None,'invalid_feature_schema'
    if feature.get('source')!='completed_mt5_ohlc':return None,'unverified_feature_source'
    if not isinstance(symbol,str) or not symbol or not isinstance(timeframe,str) or not timeframe or feature.get('symbol')!=symbol or feature.get('timeframe')!=timeframe:
        return None,'mismatched_feature_context'
    feature_time=feature.get('data_time')
    if not all(_finite_number(value) and value>0 for value in (feature_time,data_time,created_at,entry_at)) or feature_time!=data_time or not feature_time<=created_at<=entry_at:
        return None,'future_or_missing_entry_time'
    values=feature.get('values')
    if not isinstance(values,dict) or set(values)!=set(CHART_FEATURE_NAMES):return None,'invalid_feature_values'
    if any(not _finite_number(value) or abs(value)>20 for value in values.values()):return None,'invalid_feature_values'
    if any(abs(values[name])>1 for name in ('rsi_centered','close_location')) or not 0<=values['efficiency_20']<=1:
        return None,'invalid_feature_values'
    if not isinstance(feature.get('input_snapshot_hash'),str) or re.fullmatch('[0-9a-f]{64}',feature['input_snapshot_hash']) is None:
        return None,'invalid_input_snapshot_hash'
    try:
        copied=json.loads(encode(feature));claimed=copied.pop('feature_hash',None)
        if digest(copied)!=claimed:return None,'feature_fingerprint_mismatch'
    except (TypeError,ValueError):return None,'invalid_feature_snapshot'
    return {**copied,'feature_hash':claimed},''


def _safe_probability(score):
    score=max(-35.,min(35.,score))
    return max(1e-12,min(1.-1e-12,1./(1.+math.exp(-score))))


def _prediction_metrics(labels,probabilities):
    return {'brier':statistics.fmean((probability-label)**2 for label,probability in zip(labels,probabilities)),
            'log_loss':-statistics.fmean(label*math.log(probability)+(1-label)*math.log1p(-probability)
                                        for label,probability in zip(labels,probabilities))}


def _shadow_outcome_review(rows,probabilities,threshold=.5,bins=5):
    """Fixed, non-tuned observational review; net R already includes attributed costs.

    This is not a portfolio simulation, a deployable selector or a certificate.
    Positions may overlap, so summing R is not an account return or drawdown.
    """
    if len(rows)!=len(probabilities) or not _finite_number(threshold) or not 0<=threshold<=1:
        raise ValueError('Invalid shadow review alignment or threshold')
    if type(bins) is not int or bins<1 or bins>100:
        raise ValueError('Invalid calibration bin count')
    if any(not _finite_number(p) or not 0<=p<=1 for p in probabilities):
        raise ValueError('Invalid shadow probability')
    if any(not _finite_number(row.get('net_r')) for row in rows):
        raise ValueError('Invalid cost-adjusted shadow outcome')
    def summarize(items):
        values=[row['net_r'] for row in items];wins=sum(v>0 for v in values);losses=sum(v<0 for v in values)
        result={'outcomes':len(values),'positive':wins,'negative':losses,'breakeven':len(values)-wins-losses,
                'positive_fraction':wins/len(values) if values else None,'mean_net_r':None,'sum_net_r':None,
                'profit_factor_r':None,'profit_factor_infinite':False,'numeric_valid':True}
        try:
            total=math.fsum(values);gain=math.fsum(v for v in values if v>0);loss=-math.fsum(v for v in values if v<0)
            mean=statistics.fmean(values) if values else None
            factor=gain/loss if loss>0 else None
            if not all(value is None or math.isfinite(value) for value in (total,mean,gain,loss,factor)):
                raise ValueError('Unbounded economic review statistic')
            result.update(mean_net_r=mean,sum_net_r=total,profit_factor_r=factor,
                          profit_factor_infinite=loss==0 and gain>0)
        except (ValueError,OverflowError):
            result['numeric_valid']=False
        return result
    selected=[row for row,p in zip(rows,probabilities) if p>=threshold]
    calibration=[]
    for index in range(bins):
        pairs=[(row,p) for row,p in zip(rows,probabilities) if min(int(p*bins),bins-1)==index]
        calibration.append({'lower':index/bins,'upper':(index+1)/bins,'upper_inclusive':index==bins-1,
                            'observations':len(pairs),'mean_prediction':statistics.fmean(p for _,p in pairs) if pairs else None,
                            'observed_positive_fraction':sum(row['net_r']>0 for row,_ in pairs)/len(pairs) if pairs else None,
                            'outcomes':summarize([row for row,_ in pairs])})
    return {'version':'chart-economic-review-v2','threshold':threshold,'threshold_tuned_on_holdout':False,
            'selected':summarize(selected),'abstained':len(rows)-len(selected),'all_outcomes':summarize(rows),
            'calibration':calibration,'units':'net R, not account currency or portfolio return',
            'mode':'SHADOW_ONLY','execution_authority':False,'automatic_live_changes':False}


def _execution_context(row):
    style=row.get('execution_style','BASE')
    fields=[row.get(name,'') for name in ('protocol_revision','scalp_policy_revision','execution_policy_revision')]
    if style not in ('BASE','SCALP') or any(not isinstance(value,str) or (value and re.fullmatch('[0-9a-f]{64}',value) is None) for value in fields):
        return None
    if style=='SCALP' and (row.get('scalp_variant') not in ('normal','fast') or not all(fields)):
        return None
    return (fields[0],style,fields[1],fields[2])


def _chart_learning(records):
    grouped={};missing=0;invalid=0;ineligible=0
    for row in records:
        if row.get('eligible') is not True:
            ineligible+=1;continue
        feature,error=_validated_chart_features(row.get('chart_features'),row.get('symbol'),row.get('timeframe'),
            row.get('entry_data_time'),row.get('intent_created_at'),row.get('entry_at'))
        if error or not _finite_number(row.get('net_r')) or not _finite_number(row.get('closed_at')):
            if row.get('chart_feature_status')=='missing_entry_features' or (row.get('chart_features') is None and not row.get('chart_feature_status')):missing+=1
            else:invalid+=1
            continue
        context=_execution_context(row)
        if context is None:
            invalid+=1
            continue
        key=(row['strategy_id'],row['revision'],row['symbol'],row['timeframe'],context)
        grouped.setdefault(key,[]).append({**row,'chart_features':feature})
    models=[]
    for key,rows in sorted(grouped.items()):
        rows.sort(key=lambda row:(row['entry_data_time'],row['closed_at'],row.get('outcome_id','')))
        split=int(len(rows)*CHART_MODEL_POLICY['train_fraction']);holdout=rows[split:]
        cutoff=holdout[0]['entry_data_time'] if holdout else None
        # A training outcome must have been available when holdout decisions
        # were made, even when position lifetimes overlap the nominal split.
        train=[row for row in rows[:split] if cutoff is not None and row['closed_at']<cutoff]
        labels=[int(row['net_r']>0) for row in train];held_labels=[int(row['net_r']>0) for row in holdout]
        positives=sum(labels);held_positives=sum(held_labels)
        model={'strategy_id':key[0],'revision':key[1],'symbol':key[2],'timeframe':key[3],
               'protocol_revision':key[4][0],'execution_style':key[4][1],
               'scalp_policy_revision':key[4][2],'execution_policy_revision':key[4][3],
               'samples':len(rows),'train_samples':len(train),'holdout_samples':len(holdout),
               'purged_overlapping_labels':split-len(train),'train_positives':positives,
               'train_negatives':len(train)-positives,'holdout_positives':held_positives,
               'train_positive_fraction':positives/len(train) if train else None,
               'holdout_positive_fraction':held_positives/len(holdout) if holdout else None,
               'status':'INSUFFICIENT','mode':'SHADOW_ONLY','live_weight_changed':False,
               'execution_authority':False,'risk_changed':False,'code_changed':False}
        models.append(model)
        if len(rows)<CHART_MODEL_POLICY['minimum_samples'] or len(train)<CHART_MODEL_POLICY['minimum_train_samples'] or len(holdout)<CHART_MODEL_POLICY['holdout_minimum']:continue
        if not 0<positives<len(train):
            model['status']='ONE_CLASS_TRAINING';continue
        vectors=[[row['chart_features']['values'][name] for name in CHART_FEATURE_NAMES] for row in train]
        means=[statistics.fmean(vector[index] for vector in vectors) for index in range(len(CHART_FEATURE_NAMES))]
        scales=[max(1e-8,math.sqrt(statistics.fmean((vector[index]-means[index])**2 for vector in vectors))) for index in range(len(CHART_FEATURE_NAMES))]
        def normalize(vector, means=means, scales=scales):
            limit=CHART_MODEL_POLICY['standardized_clip']
            return [max(-limit,min(limit,(value-mean)/scale)) for value,mean,scale in zip(vector,means,scales)]
        standardized=[normalize(vector) for vector in vectors]
        baseline=(positives+1)/(len(train)+2);intercept=math.log(baseline/(1-baseline));weights=[0.]*len(CHART_FEATURE_NAMES)
        for _iteration in range(CHART_MODEL_POLICY['iterations']):
            residuals=[_safe_probability(intercept+math.fsum(weight*value for weight,value in zip(weights,vector)))-label for vector,label in zip(standardized,labels)]
            intercept-=CHART_MODEL_POLICY['learning_rate']*statistics.fmean(residuals)
            weights=[weight-CHART_MODEL_POLICY['learning_rate']*(statistics.fmean(residual*vector[index] for residual,vector in zip(residuals,standardized))+CHART_MODEL_POLICY['l2']*weight) for index,weight in enumerate(weights)]
        held_vectors=[normalize([row['chart_features']['values'][name] for name in CHART_FEATURE_NAMES]) for row in holdout]
        probabilities=[_safe_probability(intercept+math.fsum(weight*value for weight,value in zip(weights,vector))) for vector in held_vectors]
        scores=_prediction_metrics(held_labels,probabilities);baseline_scores=_prediction_metrics(held_labels,[baseline]*len(holdout))
        model.update(status='EVALUATED_SHADOW',intercept=intercept,coefficients=dict(zip(CHART_FEATURE_NAMES,weights)),
                     normalizer={'means':dict(zip(CHART_FEATURE_NAMES,means)),'scales':dict(zip(CHART_FEATURE_NAMES,scales))},
                     baseline_probability=baseline,holdout_model=scores,holdout_baseline=baseline_scores,
                     holdout_improved=scores['brier']<baseline_scores['brier'] and scores['log_loss']<baseline_scores['log_loss'],
                     training_closed_through=max(row['closed_at'] for row in train),holdout_started_at=cutoff,
                     training_fingerprint=digest([[row.get('outcome_id'),row['chart_features']['feature_hash'],row['net_r'],row['closed_at']] for row in train]),
                     holdout_probability_min=min(probabilities),holdout_probability_max=max(probabilities))
        economic=_shadow_outcome_review(holdout,probabilities,CHART_MODEL_POLICY['review_probability_threshold'],CHART_MODEL_POLICY['calibration_bins'])
        reference=_shadow_outcome_review(holdout,[baseline]*len(holdout),CHART_MODEL_POLICY['review_probability_threshold'],CHART_MODEL_POLICY['calibration_bins'])
        selected=economic['selected']
        review_status=('NUMERIC_RANGE_INVALID' if not selected['numeric_valid'] else
                       'INSUFFICIENT_SELECTED_OUTCOMES' if selected['outcomes']<CHART_MODEL_POLICY['minimum_selected_holdout_outcomes'] else
                       'NONPOSITIVE_NET_EXPECTANCY' if selected['mean_net_r']<=0 else 'RESEARCH_ONLY_POSITIVE_SAMPLE')
        model.update(economic_review=economic,baseline_economic_review=reference,economic_review_status=review_status,
                     drift_review=feature_drift_review(vectors,[[row['chart_features']['values'][name] for name in CHART_FEATURE_NAMES] for row in holdout],CHART_FEATURE_NAMES),
                     classification_improved=model['holdout_improved'],profitability_proven=False,
                     evaluation_fingerprint=digest([CHART_MODEL_POLICY,
                        [[row.get('outcome_id'),row['chart_features']['feature_hash'],row['net_r'],row['closed_at']] for row in holdout],probabilities]))
    return {'mode':'SHADOW_ONLY','models':models,'eligible_records':sum(len(rows) for rows in grouped.values()),
            'missing_features':missing,'invalid_features':invalid,'excluded_records':ineligible,
            'policy':dict(CHART_MODEL_POLICY),'minimum_samples':CHART_MODEL_POLICY['minimum_samples'],
            'minimum_train_samples':CHART_MODEL_POLICY['minimum_train_samples'],'holdout_minimum':CHART_MODEL_POLICY['holdout_minimum'],
            'auto_changes':False,'execution_authority':False,'live_weight_changed':False,'risk_changed':False,'code_changed':False,
            'limitations':['selection_bias','correlated_trades','costs_subject_to_later_correction','not_causal_proof']}


class LearningMemory:
    def __init__(self,store,library):
        self.store=store;self.library={key:verified_rule(rule) for key,rule in library.items()};self._chart_cache={}
        if any(key!=rule['id'] for key,rule in self.library.items()):
            raise ValueError('Knowledge library identity mismatch')
        with store.lock:
            store.db.executescript('''
            CREATE TABLE IF NOT EXISTS knowledge_versions(revision TEXT PRIMARY KEY,rule_id TEXT NOT NULL,payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS rule_observations(id TEXT PRIMARY KEY,account TEXT NOT NULL,at REAL NOT NULL,revision TEXT NOT NULL,payload TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS observations_account ON rule_observations(account,at);
            CREATE INDEX IF NOT EXISTS observations_time ON rule_observations(at DESC);
            CREATE TABLE IF NOT EXISTS learning_outcomes(id TEXT PRIMARY KEY,account TEXT NOT NULL,at REAL NOT NULL,revision TEXT NOT NULL,payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS learning_outcome_revisions(id TEXT NOT NULL,fingerprint TEXT NOT NULL,at REAL NOT NULL,payload TEXT NOT NULL,PRIMARY KEY(id,fingerprint));
            ''')
            # Earlier preview databases had no account on correction records.
            # Recover ownership only from an existing, explicitly scoped label;
            # never guess the account for orphaned historical corrections.
            if 'account' not in {r['name'] for r in store.db.execute('PRAGMA table_info(learning_outcome_revisions)')}:
                store.db.execute('ALTER TABLE learning_outcome_revisions ADD COLUMN account TEXT')
            store.db.execute('UPDATE learning_outcome_revisions SET account=(SELECT account FROM learning_outcomes WHERE learning_outcomes.id=learning_outcome_revisions.id) WHERE account IS NULL')
            store.db.execute('CREATE INDEX IF NOT EXISTS corrections_account ON learning_outcome_revisions(account,at)')
        with store.transaction() as db:
            for rule in self.library.values():
                stored=db.execute('SELECT payload FROM knowledge_versions WHERE revision=?',(rule['revision'],)).fetchone()
                if stored and verified_rule(json.loads(stored[0]))!=rule:
                    raise ValueError('Stored knowledge revision conflict')
                db.execute('INSERT OR IGNORE INTO knowledge_versions VALUES(?,?,?)',(rule['revision'],rule['id'],encode(rule)))

    def observe(self,account,cards,now):
        """One immutable observation per closed-bar rule/context identity."""
        with self.store.transaction() as db:
            for card in cards:
                rule=self.library.get(card.get('strategy_id'))
                if not rule:continue
                revision=rule['revision']
                card['rule_revision']=revision
                identity=digest([account,revision,card.get('symbol'),card.get('timeframe'),card.get('data_time')])
                row={k:card.get(k) for k in ('strategy_id','symbol','timeframe','data_time','status','direction','conditions_met','conditions_missing','market_regime','score','chart_features')}
                row['observed_at']=now
                db.execute('INSERT OR IGNORE INTO rule_observations VALUES(?,?,?,?,?)',(identity,account,now,revision,encode(row)))
            # Bound raw observations, while keeping every rule version and trade label.
            db.execute('DELETE FROM rule_observations WHERE rowid IN (SELECT rowid FROM rule_observations ORDER BY at DESC LIMIT -1 OFFSET 50000)')

    def ingest(self,account,intents,deals,now,simulation=False):
        """Full supplied history is reconciled again so late fees amend labels.

        Only uniquely owned, broker-confirmed CLOSED entries with entry and exit
        fills count. Pre-library trades remain unversioned, never retrofitted.
        """
        intents=[i for i in intents if i['account_key']==account]
        records=cashflow_records(deals,intents)
        uncertainty=set(cost_uncertainties(records,intents))
        cost_candidates=[r for r in records if 'deal:'+str(r['deal'].get('ticket','unknown')) in uncertainty or
                         (r['kind']!='TRADE' and not r['owner_id'] and not r['foreign'])]
        grouped={}
        for r in records:
            if r['owner_id']:grouped.setdefault(r['owner_id'],[]).append(r)
        with self.store.transaction() as db:
            for intent in intents:
                if intent['kind']!='ENTRY':continue
                iid=digest([account,intent['id']]);payload=intent['payload'];proposal=payload.get('proposal',{})
                data=grouped.get(intent['id'],[])
                entry=[r for r in data if r['kind']=='TRADE' and r['deal'].get('entry')==0]
                exits=[r for r in data if r['kind']=='TRADE' and r['deal'].get('entry') in (1,2,3)]
                fills=entry+exits
                entry_times=[_effective_fill_time(r['deal']) for r in entry]
                exit_times=[_effective_fill_time(r['deal']) for r in exits]
                valid_fills=bool(fills) and all(
                    _finite_number(r['deal'].get(k)) and r['deal'][k]>0
                    for r in fills for k in ('volume','time'))
                valid_fills=valid_fills and all(value is not None and value<=now for value in entry_times+exit_times)
                positions={r['deal'].get('position_id') for r in fills}
                balanced=valid_fills and positions and None not in positions and 0 not in positions and all(
                    math.isclose(sum(r['deal']['volume'] for r in entry if r['deal'].get('position_id')==position),
                                 sum(r['deal']['volume'] for r in exits if r['deal'].get('position_id')==position),
                                 rel_tol=1e-8,abs_tol=1e-8)
                    for position in positions)
                coherent=bool(entry) and len({r['deal'].get('type') for r in entry})==1 and all(
                    r['deal'].get('type')!=entry[0]['deal'].get('type') for r in exits)
                coherent=coherent and bool(proposal.get('symbol')) and all(
                    r['deal'].get('symbol')==proposal['symbol'] for r in fills)
                complete=(intent['state']=='CLOSED' and payload.get('confirmed') and entry and exits and
                          balanced and coherent and not any(r['deal'].get('entry')==2 for r in exits) and
                          max(entry_times)<=max(exit_times))
                if not complete:
                    # A previously complete record must not remain eligible if
                    # broker history later becomes incomplete or unconfirmed.
                    previous=db.execute('SELECT payload FROM learning_outcomes WHERE id=? AND account=?',(iid,account)).fetchone()
                    if previous:
                        revoked=json.loads(previous[0]);revoked.update(eligible=False,revoked=True)
                        revoked['exclusions']=list(dict.fromkeys(revoked['exclusions']+['incomplete_current_broker_history']))
                        self._remember(db,iid,account,revoked,now)
                    db.execute('DELETE FROM learning_outcomes WHERE id=?',(iid,))
                    continue
                revision=proposal.get('rule_revision') or 'LEGACY_UNVERSIONED'
                stored=db.execute('SELECT payload FROM knowledge_versions WHERE revision=?',(revision,)).fetchone()
                rule=verified_rule(json.loads(stored[0])) if stored else {}
                version_matches=rule.get('id')==proposal.get('strategy_id') and rule.get('version')==proposal.get('strategy_version')
                risk=payload.get('original_risk',0)
                valid_risk=_finite_number(risk) and risk>0
                entry_at=min(entry_times)
                created_at=intent.get('created')
                created_at=created_at if _finite_number(created_at) and 0<created_at<=entry_at else None
                blocking_costs=[r for r in cost_candidates if not _unlinked_cost_proven_before_intent(r,created_at)]
                eligible=bool(version_matches and valid_risk and not blocking_costs and not simulation)
                net=math.fsum(r['net'] for r in data)
                net_r=net/risk if valid_risk else None
                if net_r is not None and not math.isfinite(net_r):
                    valid_risk=False;eligible=False;net_r=None
                closed=max(exit_times)
                feature,feature_error=_validated_chart_features(proposal.get('chart_features'),proposal.get('symbol'),proposal.get('timeframe'),
                    proposal.get('data_time'),intent.get('created'),entry_at)
                row={'strategy_id':proposal.get('strategy_id'),'strategy_version':proposal.get('strategy_version'),
                     'decision_protocol':proposal.get('decision_protocol','general'),
                     'protocol_revision':proposal.get('protocol_revision',''),
                     'execution_style':proposal.get('execution_style','BASE'),
                     'scalp_variant':proposal.get('scalp_variant'),
                     'scalp_policy_revision':proposal.get('scalp_policy_revision',''),
                     'execution_policy_revision':proposal.get('execution_policy_revision',''),
                     'symbol':proposal.get('symbol'),'timeframe':proposal.get('timeframe'),
                     'regime':proposal.get('market_regime','UNKNOWN'),'revision':revision,
                     'net':net,'original_risk':risk if _finite_number(risk) else None,'net_r':net_r,
                     'closed_at':closed,'eligible':eligible,'simulation':simulation,
                     'chart_features':feature,'chart_feature_status':feature_error or 'VALID',
                     'entry_at':entry_at,'entry_data_time':proposal.get('data_time') if _finite_number(proposal.get('data_time')) else None,
                     'intent_created_at':intent.get('created') if _finite_number(intent.get('created')) else None,
                     'cost_review':{'scope':'original_entry_intent','unresolved_history_records':len(cost_candidates),
                                    'proven_prior_unlinked_records':len(cost_candidates)-len(blocking_costs),
                                    'blocking_records':len(blocking_costs)},
                     'exclusions':(["legacy_or_mismatched_rule"] if not version_matches else [])+
                                  (["invalid_initial_risk"] if not valid_risk else [])+
                                  (["unresolved_cost_attribution"] if blocking_costs else [])+
                                  (["synthetic_results"] if simulation else []),
                     'cashflow_fingerprint':digest(sorted((r['deal'] for r in data),key=digest))}
                if _execution_context(row) is None:
                    row['eligible']=False
                    row['exclusions'].append('invalid_execution_context')
                blob=encode(row)
                db.execute('INSERT OR REPLACE INTO learning_outcomes VALUES(?,?,?,?,?)',(iid,account,closed,revision,blob))
                self._remember(db,iid,account,row,now)

    @staticmethod
    def _remember(db,identity,account,row,now):
        db.execute('INSERT OR IGNORE INTO learning_outcome_revisions(id,fingerprint,at,payload,account) VALUES(?,?,?,?,?)',
                   (identity,digest(row),now,encode(row),account))

    def snapshot(self,account):
        with self.store.lock:
            records=[{'outcome_id':r['id'],**json.loads(r['payload'])} for r in self.store.db.execute('SELECT id,payload FROM learning_outcomes WHERE account=? ORDER BY at,id',(account,))]
            observations=self.store.db.execute('SELECT COUNT(*) FROM rule_observations WHERE account=?',(account,)).fetchone()[0]
            versions=self.store.db.execute('SELECT COUNT(*) FROM knowledge_versions').fetchone()[0]
        grouped={}
        for row in records:
            if row['eligible']:
                context=_execution_context(row)
                if context is None:continue
                key=(row['strategy_id'],row['revision'],row['symbol'],row['timeframe'],row['regime'],context)
                grouped.setdefault(key,[]).append(row['net_r'])
        models=[]
        for key,values in sorted(grouped.items()):
            n=len(values);wins=sum(v>0 for v in values);losses=sum(v<0 for v in values);zeros=n-wins-losses
            mean=statistics.fmean(values);ewma=values[0]
            for value in values[1:]:ewma=.2*value+.8*ewma
            # Sequential holdout: earlier 70% versus newest 30%; no shuffled data.
            split=int(n*.7);train=values[:split];holdout=values[split:]
            enough=n>=40 and len(holdout)>=12
            status='INSUFFICIENT'
            if enough:
                status='REVIEW_DETERIORATION' if statistics.fmean(holdout)<=0 else 'CANDIDATE_RESEARCH' if statistics.fmean(train)>0 else 'MIXED_EVIDENCE'
            models.append({'strategy_id': key[0],'revision': key[1],'symbol': key[2],'timeframe': key[3],'regime': key[4],
                               'protocol_revision': key[5][0],'execution_style': key[5][1],
                               'scalp_policy_revision': key[5][2],'execution_policy_revision': key[5][3],
                'samples': n,'wins': wins,'losses': losses,'breakeven': zeros,'mean_r': mean,'ewma_r': ewma,
                'smoothed_positive_rate': (wins+1)/(n+2),'holdout_samples': len(holdout),
                'holdout_mean_r': statistics.fmean(holdout) if holdout else None,'status': status,
                'live_weight_changed': False})
        fingerprint=digest([CHART_MODEL_POLICY,records])
        cached=self._chart_cache.get(account)
        if not cached or cached[0]!=fingerprint:
            if len(self._chart_cache)>=8 and account not in self._chart_cache:self._chart_cache.pop(next(iter(self._chart_cache)))
            self._chart_cache[account]=(fingerprint,_chart_learning(records))
        chart_learning=json.loads(encode(self._chart_cache[account][1]))
        return {'mode':'OBSERVATIONAL','library_rules':len(self.library),'stored_versions':versions,
                'observations':observations,'closed_records':len(records),'eligible_records':sum(r['eligible'] for r in records),
                'excluded_records':sum(not r['eligible'] for r in records),'models':models,
                'auto_changes':False,'minimum_samples':40,'holdout_minimum':12,
                'limitations':['selection_bias','correlated_trades','costs_subject_to_later_correction','not_causal_proof'],
                'chart_learning':chart_learning,'error':''}

    def export(self,account):
        with self.store.lock:
            versions=[]
            for saved in self.store.db.execute('SELECT revision,rule_id,payload FROM knowledge_versions ORDER BY rule_id,revision'):
                rule=verified_rule(json.loads(saved['payload']))
                if saved['revision']!=rule['revision'] or saved['rule_id']!=rule['id']:
                    raise ValueError('Stored knowledge revision identity mismatch')
                versions.append(rule)
            outcomes=[{'outcome_id':r['id'],**json.loads(r['payload'])} for r in self.store.db.execute('SELECT id,payload FROM learning_outcomes WHERE account=? ORDER BY at,id',(account,))]
            observations=[{'observation_id':r['id'],'revision':r['revision'],**json.loads(r['payload'])} for r in self.store.db.execute('SELECT id,revision,payload FROM rule_observations WHERE account=? ORDER BY at DESC,id LIMIT 1000',(account,))]
            corrections=[{'outcome_id':r['id'],'fingerprint':r['fingerprint'],'recorded_at':r['at'],**json.loads(r['payload'])} for r in self.store.db.execute('SELECT id,fingerprint,at,payload FROM learning_outcome_revisions WHERE account=? ORDER BY at DESC,id,fingerprint LIMIT 1000',(account,))]
            correction_count=self.store.db.execute('SELECT COUNT(*) FROM learning_outcome_revisions WHERE account=?',(account,)).fetchone()[0]
        evaluation=self.snapshot(account)
        return {'schema':'nexus-knowledge-learning-v1','reference':versions,'outcomes':outcomes,
                'observation_evidence':observations,'outcome_correction_history':corrections,
                'export_window':{'latest_evidence_limit':1000,'observation_total':evaluation['observations'],
                                'correction_total':correction_count,'observations_truncated':evaluation['observations']>len(observations),
                                'corrections_truncated':correction_count>len(corrections)},
                'evaluation':evaluation}
