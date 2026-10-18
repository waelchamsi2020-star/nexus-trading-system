"""Coordinator boundary tests; no live broker or external data source is used."""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

from test_learning import fills, intent

from nexus.broker import BrokerError
from nexus.engine import Engine
from nexus.learning import digest
from nexus.store import account_key
from nexus.valuation import evaluate

ROOT=Path(__file__).resolve().parents[1]


def financial(model='pv',**changes):
    return {'model':model,'asset':'SCENARIO ONLY','currency':'USD','as_of':2000,
            'published_at':1000,'source':'Manual synthetic unit fixture',
            'cashflows':[100],'discount_rate':.1,**changes}


class LearningEngineBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.now=1_800_000_000
        definition={'id':'fixture_rule','version':'1.0.0','scope':'Synthetic unit fixture'}
        self.reference={**definition,'revision':digest(definition)}
        with patch('nexus.engine.load_library',return_value={'fixture_rule':self.reference}):
            self.engine=Engine(ROOT,self.temporary.name,clock=lambda:self.now)
        self.addCleanup(self.close)
        self.engine._connect(True)
        self.key=account_key(self.engine.broker.account())

    def close(self):
        self.engine.stop_worker()
        if self.engine.store:self.engine.store.close()
        self.engine.cache.db.close();self.engine.news.db.close()

    def observe_a(self):
        card={'strategy_id':'fixture_rule','symbol':'TEST','timeframe':'H1',
              'data_time':self.now-3600,'status':'WAIT','conditions_missing':['trigger']}
        self.engine._observe_rules([card])
        self.engine._update_learning(force=True)
        self.assertEqual(self.engine.learning_state['observations'],1)

    def test_mirror_failure_does_not_break_learning_or_grant_execution(self):
        with patch('nexus.learning_journal.persist',side_effect=OSError('fixture disk failure')):
            self.engine._update_learning(force=True)
        self.assertFalse(self.engine.learning_state['persistence']['ok'])
        self.assertEqual(self.engine.learning_state['mode'],'OBSERVATIONAL')
        self.assertEqual(self.engine.executor.status()['mode'],'READ_ONLY')
        self.assertTrue(any(x['event']=='LEARNING_FILE_ERROR' for x in self.engine.store.recent_audit()))
        self.engine._update_learning(force=True)
        self.assertTrue(self.engine.learning_state['persistence']['ok'])

    def test_learning_mirror_is_exported_and_corruption_does_not_block_diagnostics(self):
        self.engine._update_learning(force=True)
        exported=self.engine._export_knowledge()
        with zipfile.ZipFile(exported['path']) as bundle:
            self.assertIn('learning-state.json',bundle.namelist())
            self.assertFalse(json.loads(bundle.read('learning-state.json'))['automatic_live_changes'])
        target=Path(self.engine.learning_state['persistence']['file'])
        target.write_text('null',encoding='utf-8')
        self.engine._publish()
        report=self.engine._diagnostics()
        with zipfile.ZipFile(report['path']) as bundle:
            self.assertIn('journal.sqlite3',bundle.namelist())
            summary=json.loads(bundle.read('ai-report.json'))
            self.assertTrue(any(x['event']=='CURRENT_LEARNING_FILE_ERROR' for x in summary['active_errors']))

    def test_revoked_executor_cannot_publish_stale_automatic_status(self):
        self.engine.status='AUTO_DEMO'
        self.engine.executor.deactivate('Broker result remains unresolved')
        self.engine._publish()
        state=self.engine.snapshot()
        self.assertEqual(state['mode'],'READ_ONLY')
        self.assertEqual(state['status'],'READ_ONLY')
        self.assertEqual(self.engine.status,'READ_ONLY')
        self.assertEqual(state['error'],'')

    def closed_label(self):
        item=intent(1,self.key,self.reference)
        self.engine.learner.ingest(self.key,[item],fills(item),self.now,simulation=False)
        self.engine.learning_state=self.engine.learner.snapshot(self.key)
        return item

    def test_missing_history_is_an_error_and_does_not_replace_labels_with_empty_history(self):
        self.closed_label()
        before=self.engine.learner.snapshot(self.key)
        for effect in (None,BrokerError('history interrupted')):
            with self.subTest(effect=effect):
                method=Mock(return_value=None) if effect is None else Mock(side_effect=effect)
                with patch.object(self.engine.broker,'deals',method):self.engine._update_learning(force=True)
                self.assertTrue(self.engine.learning_state['error'])
                self.assertEqual(self.engine.learner.snapshot(self.key)['eligible_records'],before['eligible_records'])
        self.assertTrue(any(r['event']=='LEARNING_ERROR' for r in self.engine.store.recent_audit()))
        self.assertEqual(self.engine.executor.status()['mode'],'READ_ONLY')

    def test_export_preserves_failed_refresh_error_with_reference_and_account_evidence(self):
        self.closed_label()
        with patch.object(self.engine.broker,'deals',return_value=None):
            result=self.engine._export_knowledge()
        with zipfile.ZipFile(result['path']) as bundle:
            data=json.loads(bundle.read('knowledge-learning.json'))
        self.assertIn('unavailable',data['evaluation']['error'])
        self.assertEqual(data['evaluation']['eligible_records'],1)
        self.assertIn('observation_evidence',data)
        self.assertIn('outcome_correction_history',data)

    def test_full_history_starts_before_earliest_account_entry_and_ignores_foreign_intents(self):
        own=intent(1,self.key,self.reference)
        for identity,key,created in [(own['id'],self.key,self.now-90000),('foreign','other-account',self.now-300000)]:
            result=self.engine.store.reserve(identity,key,10,own['payload'],[],100,now=created)
            self.assertTrue(result['approved'])
            self.engine.store.set_intent_state(identity,'CLOSED',confirmed=True)
        with patch.object(self.engine.broker,'deals',return_value=fills(own)) as deals:
            self.engine._update_learning(force=True)
        deals.assert_called_once_with(self.now-90000-60)
        self.assertEqual(self.engine.learner.snapshot(self.key)['closed_records'],1)
        self.assertEqual(self.engine.learner.snapshot('other-account')['closed_records'],0)

    def test_account_switch_bypasses_learning_throttle_and_clears_old_scenario(self):
        self.observe_a()
        self.engine._action({'action':'fundamental_analyze','data':financial()})
        self.engine.broker._account['login']+=1
        key_b=account_key(self.engine.broker.account())
        self.engine._update_learning()
        self.assertEqual(self.engine.learning_state['observations'],0)
        self.assertEqual(self.engine.learning_state['closed_records'],0)
        self.assertEqual(self.engine.valuation,{})
        self.assertEqual(self.engine.learner.snapshot(self.key)['observations'],1)
        self.assertEqual(self.engine.learner.snapshot(key_b)['observations'],0)

    def test_account_switch_with_history_failure_does_not_show_previous_account_models(self):
        self.observe_a()
        self.engine.broker._account['login']+=1
        with patch.object(self.engine.broker,'deals',return_value=None):self.engine._update_learning(force=True)
        self.assertTrue(self.engine.learning_state['error'])
        self.assertEqual(self.engine.learning_state['observations'],0)

    def test_recovered_connection_to_new_account_resets_learning_and_saved_valuation(self):
        self.observe_a()
        self.engine._action({'action':'fundamental_analyze','data':financial()})
        self.engine.broker._account['login']+=1
        self.engine.broker.is_simulation=False
        self.engine.broker.reconnect=Mock(side_effect=self.engine.broker.terminal)
        self.assertTrue(self.engine._recover_mt5_connection(BrokerError('fixture IPC interruption')))
        self.assertEqual(self.engine.learning_state['observations'],0)
        self.assertEqual(self.engine.valuation,{})
        self.assertEqual(self.engine.executor.status()['mode'],'READ_ONLY')

    def test_account_identity_is_rechecked_after_history_before_committing_learning(self):
        def switch_during_history(_since):
            self.engine.broker._account['login']+=1
            return []
        with patch.object(self.engine.broker, 'deals', side_effect=switch_during_history), patch.object(self.engine.learner, 'ingest', wraps=self.engine.learner.ingest) as ingest:
            self.engine._update_learning(force=True)
        ingest.assert_not_called()
        self.assertTrue(self.engine.learning_state['error'])

    def test_publish_on_new_account_clears_old_learning_scenario_context_and_authorization(self):
        self.engine._action({'action':'start','mode':'AUTO_DEMO','unit':'amount',
                             'risk_value':50,'target_value':100,'commission_per_lot':0,'slippage_points':10})
        self.observe_a()
        self.engine._action({'action':'fundamental_analyze','data':financial()})
        self.engine.context_cache={'old account context':{}}
        self.engine.partner_catalog=[{'name':'old broker symbol'}]
        self.engine.broker._account['login']+=1
        changed_login=self.engine.broker._account['login']
        self.engine._publish()
        state=self.engine.snapshot()
        self.assertEqual(state['account']['login'],changed_login)
        self.assertEqual(state['learning']['observations'],0)
        self.assertEqual(state['valuation'],{})
        self.assertEqual(state['mode'],'READ_ONLY')
        self.assertEqual(self.engine.context_cache,{})
        self.assertIsNone(self.engine.partner_catalog)
        self.assertEqual(self.engine.store.get_day(self.key,self.now)['risk_amount'],50)

    def test_financial_scenarios_are_local_account_scoped_deduplicated_and_do_not_authorize_execution(self):
        original=self.engine.executor.status()
        request={'action':'fundamental_analyze','data':financial()}
        first=self.engine._action(request);self.engine._action(request)
        self.assertEqual(first['valuation']['data_kind'],'USER_SUPPLIED_FINANCIAL_SCENARIO')
        self.assertFalse(first['valuation']['execution_authority'])
        self.assertIn('not_independently_verified',first['valuation']['limitations'])
        self.assertEqual(self.engine.executor.status(),original)
        self.assertIsNone(self.engine.risk.settings)
        self.assertEqual(self.engine.store.db.execute('SELECT COUNT(*) FROM financial_scenarios').fetchone()[0],1)
        self.engine.broker._account['login']+=1
        self.engine._action(request)
        self.assertEqual(self.engine.store.db.execute('SELECT COUNT(*) FROM financial_scenarios').fetchone()[0],2)
        with self.engine.store.lock:
            scopes={r[0] for r in self.engine.store.db.execute('SELECT account FROM financial_scenarios')}
        self.assertEqual(len(scopes),2)

    def test_invalid_financial_inputs_cannot_persist_partial_scenario(self):
        with self.assertRaises(ValueError):
            self.engine._action({'action':'fundamental_analyze','data':financial(published_at=2001)})
        self.assertEqual(self.engine.store.db.execute('SELECT COUNT(*) FROM financial_scenarios').fetchone()[0],0)
        self.assertEqual(self.engine.valuation,{})

    def test_observation_failure_is_reported_without_changing_execution_state(self):
        status=self.engine.executor.status()
        with patch.object(self.engine.learner,'observe',side_effect=ValueError('fixture learning write failure')):
            self.engine._observe_rules([])
        self.assertIn('write failure',self.engine.learning_state['error'])
        self.assertEqual(self.engine.executor.status(),status)


class ValuationNumericalBoundaryTests(unittest.TestCase):
    def test_scenario_currency_uses_ascii_currency_code(self):
        for currency in ('دول','美元元','ÜSD'):
            with self.subTest(currency=currency), self.assertRaises(ValueError):
                evaluate(financial(currency=currency))

    def test_extreme_dcf_and_bond_inputs_return_controlled_value_error(self):
        cases=[financial('dcf',cashflows=[1,1],discount_rate=1e308,terminal_growth=0,debt=0,cash=0,shares=1),
               financial('bond',par=100,coupon_rate=.1,yield_rate=-.999999,payments_per_year=1,periods=600),
               financial('bond',par=100,coupon_rate=.1,yield_rate=1e308,payments_per_year=1,periods=600)]
        for scenario in cases:
            with self.subTest(model=scenario['model'], rate=scenario.get('yield_rate', scenario['discount_rate'])), self.assertRaises(ValueError):
                evaluate(scenario)


if __name__=='__main__':unittest.main()
