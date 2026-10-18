"""Deterministic chart ML fixtures use synthetic broker history, never live orders.

The fixtures exercise attribution and chronological evaluation. Their model
scores are unit evidence and do not establish trading performance.
"""
import copy
import math
import unittest
from unittest.mock import patch

from test_learning import fills, intent, rule

from nexus.learning import CHART_FEATURE_NAMES, LearningMemory, _chart_learning, digest
from nexus.store import Store


def feature(data_time,signal=1.,symbol='TEST',timeframe='H1'):
    values={'return_1_atr':signal,'return_5_atr':2*signal,'ema_gap_atr':signal,
            'rsi_centered':.8*signal,'close_location':.6*signal,'efficiency_20':.5,
            'volatility_ratio_log':.2*signal,'tick_activity_log':.1*signal}
    result={'schema':1,'feature_version':'ohlc-v1','source':'completed_mt5_ohlc',
            'symbol':symbol,'timeframe':timeframe,'data_time':data_time,'values':values,
            'input_snapshot_hash':digest(['synthetic historical input fixture',data_time,signal])}
    result['feature_hash']=digest(result)
    return result


def rehash(value):
    value.pop('feature_hash',None);value['feature_hash']=digest(value)
    return value


class ChartLearningTests(unittest.TestCase):
    def setUp(self):
        self.store=Store(':memory:');self.addCleanup(self.store.close)
        self.reference=rule()
        self.memory=LearningMemory(self.store,{self.reference['id']:self.reference})

    def dataset(self,count=60,account='A',start=1,features=True,changes=None,label=None,overlap=False,simulation=False):
        originals=[];deals=[]
        for offset in range(count):
            index=start+offset;data_time=1000+index*100
            positive=(offset%2==0) if label is None else label(offset)
            item=intent(index,account,self.reference)
            item['payload']['proposal']['data_time']=data_time
            if features:
                snapshot=feature(data_time,1. if offset%2==0 else -1.)
                if changes:changes(snapshot,offset)
                item['payload']['proposal']['chart_features']=snapshot
            result=self.store.reserve(item['id'],account,10,item['payload'],[],1000,now=data_time+5)
            self.assertTrue(result['approved'])
            self.store.set_intent_state(item['id'],'CLOSED',confirmed=True)
            originals.append(self.store.intent(item['id']))
            closed=data_time+(10000 if overlap and offset<42 else 20)
            history=fills(item,20 if positive else -10,closed_at=closed)
            history[0]['time']=data_time+10
            deals.extend(history)
        self.memory.ingest(account,originals,deals,1_000_000,simulation=simulation)
        return originals,deals

    def chart(self,account='A'):
        return self.memory.snapshot(account)['chart_learning']

    def model(self):
        models=self.chart()['models'];self.assertEqual(len(models),1)
        return models[0]

    def test_closed_owned_original_chart_snapshots_fit_and_evaluate_shadow_classifier(self):
        self.dataset()
        chart=self.chart();model=chart['models'][0]
        self.assertEqual(chart['mode'],'SHADOW_ONLY');self.assertEqual(chart['eligible_records'],60)
        self.assertEqual(chart['policy']['iterations'],120)
        self.assertEqual((model['samples'],model['train_samples'],model['holdout_samples']),(60,42,18))
        self.assertEqual(model['status'],'EVALUATED_SHADOW')
        self.assertEqual(set(model['coefficients']),set(CHART_FEATURE_NAMES))
        self.assertTrue(any(abs(value)>.01 for value in model['coefficients'].values()))
        self.assertLess(model['holdout_model']['brier'],model['holdout_baseline']['brier'])
        self.assertLess(model['holdout_model']['log_loss'],model['holdout_baseline']['log_loss'])
        self.assertLess(model['training_closed_through'],model['holdout_started_at'])
        exported=self.memory.export('A')
        self.assertTrue(all(row['chart_features']['feature_hash'] for row in exported['outcomes']))
        self.assertEqual(exported['evaluation']['chart_learning'],chart)

    def test_base_and_scalp_execution_contexts_are_never_pooled_to_reach_training_threshold(self):
        originals,deals=self.dataset()
        for item in originals[30:]:
            item['payload']['proposal'].update(decision_protocol='four_school_v1',protocol_revision='a'*64,
                execution_style='SCALP',scalp_variant='normal',scalp_policy_revision='b'*64,execution_policy_revision='c'*64)
        self.memory.ingest('A',originals,deals,1_000_000)
        models=self.chart()['models']
        self.assertEqual(len(models),2)
        self.assertEqual(sorted(model['samples'] for model in models),[30,30])
        self.assertTrue(all(model['status']=='INSUFFICIENT' for model in models))
        self.assertEqual({model['execution_style'] for model in models},{'BASE','SCALP'})
        self.assertEqual(len(self.memory.snapshot('A')['models']),2)

    def test_invalid_execution_context_excludes_outcome_without_breaking_other_groups(self):
        originals,deals=self.dataset()
        originals[0]['payload']['proposal'].update(execution_style='SCALP',protocol_revision={'forged':True})
        self.memory.ingest('A',originals,deals,1_000_000)
        self.assertEqual(self.chart()['eligible_records'],59)
        excluded=[row for row in self.memory.export('A')['outcomes'] if not row['eligible']]
        self.assertEqual(len(excluded),1)
        self.assertIn('invalid_execution_context',excluded[0]['exclusions'])
    def test_holdout_features_and_labels_cannot_change_fitted_weights_or_normalizer(self):
        self.dataset();original=self.model()
        other=Store(':memory:');self.addCleanup(other.close)
        self.store=other;self.memory=LearningMemory(other,{self.reference['id']:self.reference})
        def changed(snapshot,index):
            if index>=42:
                snapshot['values']['return_1_atr']=19.
                snapshot['values']['ema_gap_atr']=-19.
                rehash(snapshot)
        self.dataset(changes=changed,label=lambda index:index%2==0 if index<42 else index%2!=0)
        altered=self.model()
        for field in ('coefficients','intercept','normalizer','training_fingerprint','baseline_probability'):
            self.assertEqual(original[field],altered[field])
        self.assertNotEqual(original['holdout_model'],altered['holdout_model'])

    def test_future_tampered_nonfinite_unknown_and_mismatched_features_are_excluded(self):
        cases=[lambda f:f.update(data_time=f['data_time']+1000),
               lambda f:f['values'].update(return_1_atr=2.),
               lambda f:f.update(schema=2),lambda f:f.update(symbol='OTHER'),
               lambda f:f.update(source='synthetic_completed_ohlc'),
               lambda f:f['values'].update(return_1_atr=float('nan')),
               lambda f:f['values'].update(return_1_atr=21.),
               lambda f:f['values'].update(efficiency_20=-.1),
               lambda f:f['values'].update(return_1_atr=10**400)]
        for index,change in enumerate(cases):
            with self.subTest(index=index):
                store=Store(':memory:')
                try:
                    memory=LearningMemory(store,{self.reference['id']:self.reference})
                    item=intent(index+1,reference=self.reference);item['created']=1005
                    snapshot=feature(1000);change(snapshot)
                    if index in (0,2,3,4,6,7,8):rehash(snapshot)
                    item['payload']['proposal'].update(data_time=1000,chart_features=snapshot)
                    history=fills(item,closed_at=1020)
                    memory.ingest('A',[item],history,10000)
                    result=memory.snapshot('A')['chart_learning']
                    self.assertEqual(result['eligible_records'],0);self.assertEqual(result['invalid_features'],1)
                    self.assertEqual(result['models'],[])
                finally:store.close()

    def precision_fixture(self,created=1000.8):
        item=intent(reference=self.reference);item['created']=created
        item['payload']['proposal'].update(data_time=1000,chart_features=feature(1000))
        history=fills(item,closed_at=1001)
        history[0].update(time=1000,time_msc=1000950)
        history[1].update(time=1001,time_msc=1001250)
        return item,history

    def test_millisecond_entry_fill_accepts_original_fractional_intent_time(self):
        item,history=self.precision_fixture()
        self.memory.ingest('A',[item],history,1002)
        chart=self.chart();self.assertEqual(chart['eligible_records'],1)
        outcome=self.memory.export('A')['outcomes'][0]
        self.assertEqual(outcome['entry_at'],1000.95)
        self.assertEqual(outcome['closed_at'],1001.25)
        self.assertEqual(outcome['chart_feature_status'],'VALID')

    def test_intent_after_precise_fill_is_rejected_without_same_second_grace(self):
        item,history=self.precision_fixture(created=1000.96)
        self.memory.ingest('A',[item],history,1002)
        self.assertEqual(self.chart()['eligible_records'],0)
        self.assertEqual(self.chart()['invalid_features'],1)
        self.assertEqual(self.memory.export('A')['outcomes'][0]['chart_feature_status'],'future_or_missing_entry_time')

    def test_absent_milliseconds_preserve_conservative_seconds(self):
        item,history=self.precision_fixture()
        for deal in history:deal.pop('time_msc')
        self.memory.ingest('A',[item],history,1002)
        self.assertEqual(self.chart()['eligible_records'],0)
        self.assertEqual(self.memory.export('A')['outcomes'][0]['entry_at'],1000)

    def test_invalid_inconsistent_and_future_millisecond_fills_do_not_create_labels(self):
        cases=[('time_msc',1001950,1002),('time_msc','1000950',1002),
               ('time_msc',1000950.5,1002),('time_msc',None,1002),
               ('time_msc',float('inf'),1002),('time_msc',10**400,1002),
               ('time_msc',1000950,1000.9)]
        for field,value,now in cases:
            with self.subTest(value=value,now=now):
                item,history=self.precision_fixture();history[0][field]=value
                # Keep the exit inside the current second in the future-fill
                # case so its seconds field alone cannot explain rejection.
                if now==1000.9:history[1].update(time=1000,time_msc=1000990)
                self.memory.ingest('A',[item],history,now)
                self.assertEqual(self.memory.export('A')['outcomes'],[])
                self.assertEqual(self.chart()['models'],[])

    def test_millisecond_entry_exit_order_cannot_reverse_inside_one_second(self):
        item,history=self.precision_fixture(created=1000.5)
        history[1].update(time=1000,time_msc=1000900)
        self.memory.ingest('A',[item],history,1002)
        self.assertEqual(self.memory.export('A')['outcomes'],[])

    def test_unlinked_cost_before_original_intent_does_not_contaminate_later_labels(self):
        originals,deals=self.dataset()
        prior={'ticket':99999,'type':5,'magic':0,'profit':-.22,'time':800,'time_msc':800500,
               'symbol':'','order':0,'position_id':0,'comment':'Broker correction'}
        self.memory.ingest('A',originals,deals+[prior],1_000_000)
        self.assertEqual(self.chart()['eligible_records'],60)
        self.assertEqual(self.model()['status'],'EVALUATED_SHADOW')
        for row in self.memory.export('A')['outcomes']:
            self.assertEqual(row['cost_review']['proven_prior_unlinked_records'],1)
            self.assertEqual(row['cost_review']['blocking_records'],0)
        self.assertEqual(sum(row['net'] for row in self.memory.export('A')['outcomes']),sum(deal['profit'] for deal in deals))

    def test_cost_after_creation_including_after_close_still_blocks_original_outcome(self):
        item,history=self.precision_fixture()
        for time_ms in (1000850,1002000):
            with self.subTest(time_ms=time_ms):
                cost={'ticket':99,'type':5,'magic':0,'profit':-.22,'time':time_ms//1000,'time_msc':time_ms}
                self.memory.ingest('A',[item],history+[cost],1003)
                outcome=self.memory.export('A')['outcomes'][0]
                self.assertFalse(outcome['eligible'])
                self.assertEqual(outcome['cost_review']['blocking_records'],1)
                self.assertIn('unresolved_cost_attribution',outcome['exclusions'])

    def test_same_second_missing_invalid_or_linked_cost_evidence_stays_conservative(self):
        item,history=self.precision_fixture()
        cases=[{'time':1000}, {'time':1000,'time_msc':0}, {},
               {'time':800,'time_msc':800500,'order':item['payload']['result']['order']},
               {'time':800,'time_msc':800500,'position_id':item['payload']['position_ids'][0]},
               {'time':800,'time_msc':800500,'comment':'NX:unresolved-link'}]
        for values in cases:
            with self.subTest(values=values):
                cost={'ticket':99,'type':5,'magic':0,'profit':-.22,**values}
                self.memory.ingest('A',[item],history+[cost],1003)
                outcome=self.memory.export('A')['outcomes'][0]
                self.assertFalse(outcome['eligible'])
                self.assertEqual(outcome['cost_review']['proven_prior_unlinked_records'],0)

    def test_cost_can_precede_fill_without_preceding_pending_intent_creation(self):
        item,history=self.precision_fixture(created=800.)
        item['payload']['proposal'].update(data_time=700,chart_features=feature(700))
        cost={'ticket':99,'type':5,'magic':0,'profit':-.22,'time':900,'time_msc':900500}
        self.memory.ingest('A',[item],history+[cost],1003)
        outcome=self.memory.export('A')['outcomes'][0]
        self.assertFalse(outcome['eligible'])
        self.assertEqual(outcome['cost_review']['blocking_records'],1)

    def test_later_observations_do_not_retrofit_missing_entry_features(self):
        originals,_deals=self.dataset(features=False)
        cards=[{'strategy_id':self.reference['id'],'symbol':'TEST','timeframe':'H1',
                'data_time':item['payload']['proposal']['data_time'],
                'chart_features':feature(item['payload']['proposal']['data_time'])} for item in originals]
        self.memory.observe('A',cards,100000)
        chart=self.chart()
        self.assertEqual(chart['missing_features'],60);self.assertEqual(chart['eligible_records'],0)
        self.assertEqual(chart['models'],[])

    def test_insufficient_data_and_one_class_training_do_not_fit(self):
        self.dataset(count=59)
        model=self.model();self.assertEqual(model['status'],'INSUFFICIENT')
        self.assertNotIn('coefficients',model)
        other=Store(':memory:');self.addCleanup(other.close)
        self.store=other;self.memory=LearningMemory(other,{self.reference['id']:self.reference})
        self.dataset(label=lambda index:index<42)
        model=self.model();self.assertEqual(model['status'],'ONE_CLASS_TRAINING')
        self.assertEqual(model['holdout_positive_fraction'],0.)
        self.assertNotIn('coefficients',model)

    def test_overlapping_outcomes_are_purged_before_the_holdout_decisions(self):
        self.dataset(overlap=True)
        model=self.model()
        self.assertEqual(model['purged_overlapping_labels'],42)
        self.assertEqual(model['train_samples'],0);self.assertEqual(model['status'],'INSUFFICIENT')
        self.assertNotIn('coefficients',model)

    def test_imbalanced_classes_report_safe_model_and_prevalence_baseline_metrics(self):
        self.dataset(label=lambda index:index not in (10,30) and index<42)
        model=self.model();self.assertEqual(model['status'],'EVALUATED_SHADOW')
        self.assertEqual((model['train_positives'],model['train_negatives']),(40,2))
        self.assertEqual(model['holdout_positive_fraction'],0.)
        self.assertGreater(model['baseline_probability'],.9)
        self.assertGreater(model['holdout_probability_min'],0.)
        self.assertLess(model['holdout_probability_max'],1.)
        self.assertTrue(all(math.isfinite(value) for field in ('holdout_model','holdout_baseline') for value in model[field].values()))

    def test_cached_results_are_defensive_and_cost_corrections_trigger_refit(self):
        originals,deals=self.dataset()
        with patch('nexus.learning._chart_learning',wraps=_chart_learning) as fitting:
            original=self.chart();self.chart();self.assertEqual(fitting.call_count,1)
            original['models'][0]['coefficients']['return_1_atr']=999
            self.assertNotEqual(self.model()['coefficients']['return_1_atr'],999)
            self.assertEqual(fitting.call_count,1)
            amended=copy.deepcopy(deals);amended[1]['commission']=-50.
            self.memory.ingest('A',originals,amended,1_000_000)
            self.chart();self.assertEqual(fitting.call_count,2)

    def test_account_scopes_simulation_exclusions_and_no_execution_authority(self):
        self.dataset();before=copy.deepcopy(self.store.intents())
        chart=self.chart();self.assertEqual(before,self.store.intents())
        for value in (chart,chart['models'][0]):
            for flag in ('execution_authority','live_weight_changed','risk_changed','code_changed'):
                self.assertFalse(value[flag])
        self.assertEqual(self.chart('FOREIGN')['models'],[])
        _originals,_deals=self.dataset(count=60,account='SIM',start=101,simulation=True)
        chart=self.chart('SIM')
        self.assertEqual(chart['models'],[]);self.assertEqual(chart['excluded_records'],60)
        self.assertEqual(chart['eligible_records'],0)


if __name__=='__main__':unittest.main()
