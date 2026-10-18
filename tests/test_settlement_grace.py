"""Bounded confirmation of synthetic sends; no terminal or live service."""
import copy
import time
import unittest
from unittest.mock import patch

from test_risk_execution import SafetyBroker

from nexus.execution import SETTLEMENT_GRACE_SECONDS, SETTLEMENT_MAX_READS, Executor
from nexus.risk import RiskManager
from nexus.store import Store


class SettlementGraceTests(unittest.TestCase):
    def setUp(self):
        self.now=int(time.time()//86400)*86400+43200
        self.elapsed=0.;self.waits=[];self.on_wait=None
        self.broker=SafetyBroker(lambda:self.now)
        self.store=Store(':memory:');self.addCleanup(self.store.close)
        self.risk=RiskManager(self.broker,self.store)
        self.executor=Executor(self.broker,self.store,self.risk,lambda:self.now,
            settlement_clock=lambda:self.elapsed,settlement_sleep=self.wait)
        self.settings={'daily_risk':1000.,'daily_target':1000.,'commission_per_lot':0.,
                       'slippage_points':10,'max_trade_fraction':.2,'correlation_cap_fraction':.5}

    def wait(self,seconds):
        self.waits.append(seconds);self.elapsed+=seconds
        if self.on_wait:self.on_wait()

    def proposal(self,identity='entry'):
        return {'id':identity,'symbol':'EURUSD.demo','side':'BUY','sl':1.075,'tp':1.09,
                'qualified':True,'news_ok':True,'data_time':self.now-1,'expires_at':self.now+120}

    def entry(self):
        self.executor.activate('AUTO_DEMO',self.settings)
        result=self.executor.execute(self.proposal())
        self.assertTrue(result['ok'],result)
        self.assertEqual(self.waits,[])
        return result['intent_id']

    def delayed_exits(self,delay):
        original=self.broker.deals
        def reads(since):
            records=original(since)
            return [row for row in records if row.get('entry')==0] if self.elapsed<delay else records
        return patch.object(self.broker,'deals',side_effect=reads)

    def test_successful_close_waits_for_history_without_replay_risk_release_or_new_authorization(self):
        entry_id=self.entry();authorization=self.executor.authorization
        original_risk=self.store.intent(entry_id)['reserved']
        day_before=self.store.get_day(self.risk.key,self.now)
        def assert_blocked():
            self.assertIs(self.executor.authorization,authorization)
            self.assertEqual(self.store.intent(entry_id)['reserved'],original_risk)
            with self.assertRaisesRegex(ValueError,'Unresolved'):self.executor._guard(entry=True)
            denied=self.store.reserve('blocked',self.risk.key,1.,{},[],10000.,now=self.now)
            self.assertFalse(denied['approved']);self.assertEqual(denied['reason'],'UNRESOLVED_BROKER_RESULT')
            self.assertEqual(len(self.broker.sent),2)
        self.on_wait=assert_blocked
        with self.delayed_exits(1.):result=self.executor.flatten_owned_positions()
        self.assertTrue(result['ok'],result)
        self.assertEqual(self.elapsed,1.)
        self.assertIs(self.executor.authorization,authorization)
        self.assertEqual(self.executor.mode,'AUTO_DEMO')
        self.assertFalse(self.executor.entries_paused)
        self.assertEqual(self.store.intent(entry_id)['state'],'CLOSED')
        self.assertEqual(self.store.intent(entry_id)['reserved'],0.)
        self.assertEqual(self.store.get_day(self.risk.key,self.now),day_before)
        self.assertEqual(len(self.broker.sent),2)
        self.assertEqual(self.executor.status()['unresolved'],[])

    def test_successful_sltp_waits_for_matching_book_and_keeps_existing_authorization(self):
        self.entry();authorization=self.executor.authorization
        stale=copy.deepcopy(self.broker.positions());position=stale[0]
        original=self.broker.positions
        def observed():return copy.deepcopy(stale) if self.elapsed<.5 else original()
        request={'action':'SLTP','symbol':position['symbol'],'position':position['ticket'],'sl':1.077,'tp':1.09}
        with patch.object(self.broker, 'positions', side_effect=observed), self.executor.lock:
            result = self.executor._management_request(request, 'fixture protection', position)
        self.assertTrue(result['ok'],result);self.assertTrue(result['confirmed'])
        self.assertEqual(result['state'],'CLOSED');self.assertEqual(self.elapsed,.5)
        self.assertIs(self.executor.authorization,authorization)
        self.assertEqual(len(self.broker.sent),2)

    def test_grace_expiry_revokes_holds_risk_and_later_confirmation_never_reactivates(self):
        entry_id=self.entry();reserved=self.store.intent(entry_id)['reserved']
        with self.delayed_exits(100.):result=self.executor.flatten_owned_positions()
        self.assertFalse(result['ok'],result)
        attempt=result['results'][0]
        self.assertFalse(attempt['approved']);self.assertFalse(attempt['confirmed'])
        self.assertIn('will not be resent',attempt['reasons'][0])
        self.assertEqual(self.elapsed,SETTLEMENT_GRACE_SECONDS)
        self.assertLessEqual(len(self.waits),SETTLEMENT_MAX_READS)
        self.assertEqual(self.executor.mode,'READ_ONLY');self.assertIsNone(self.executor.authorization)
        self.assertEqual(self.store.intent(entry_id)['reserved'],reserved)
        self.assertTrue(self.executor.reconcile()['ok'])
        self.assertEqual(self.executor.mode,'READ_ONLY')
        self.assertEqual(len(self.broker.sent),2)
        self.executor.activate('AUTO_DEMO',self.settings)
        self.assertEqual(self.executor.mode,'AUTO_DEMO')
        self.assertEqual(self.executor.last_reason,'Demo authorization activated')
        self.assertEqual(len(self.broker.sent),2)

    def test_failed_history_read_revokes_immediately_without_wait_or_resend(self):
        entry_id=self.entry();reserved=self.store.intent(entry_id)['reserved']
        original=self.broker.deals
        def unavailable(since):return None if len(self.broker.sent)>1 else original(since)
        with patch.object(self.broker,'deals',side_effect=unavailable):result=self.executor.flatten_owned_positions()
        self.assertFalse(result['ok'])
        self.assertEqual(self.waits,[]);self.assertEqual(self.executor.mode,'READ_ONLY')
        self.assertIn('Reconciliation failed',self.executor.last_reason)
        self.assertEqual(self.store.intent(entry_id)['reserved'],reserved)
        self.assertEqual(len(self.broker.sent),2)

    def test_unknown_lost_malformed_and_rejected_responses_never_enter_grace(self):
        for special in ('unknown_no_fill','timeout_after_fill','malformed_success_after_fill','reject'):
            with self.subTest(special=special):
                broker=SafetyBroker(lambda:self.now);store=Store(':memory:')
                try:
                    risk=RiskManager(broker,store);waits=[]
                    executor=Executor(broker,store,risk,lambda:self.now,
                        settlement_clock=lambda:0.,settlement_sleep=waits.append)
                    executor.activate('AUTO_DEMO',self.settings);broker.special=special
                    result=executor.execute(self.proposal())
                    self.assertFalse(result['ok']);self.assertEqual(waits,[])
                    self.assertEqual(len(broker.sent),1)
                    self.assertEqual(executor.mode,'AUTO_DEMO' if special=='reject' else 'READ_ONLY')
                finally:store.close()

    def pending_protection(self,identity='pending'):
        position=self.broker.positions()[0]
        request={'action':'SLTP','symbol':position['symbol'],'position':position['ticket'],'sl':1.077,'tp':1.09}
        self.store.management_intent(identity,self.risk.key,request,'fixture delayed protection',self.now)
        self.store.set_intent_state(identity,'FILLED',result={'retcode':10009},confirmed=False)

    def test_periodic_reconciliation_still_revokes_pending_success_immediately(self):
        self.entry();self.pending_protection()
        result=self.executor.reconcile()
        self.assertFalse(result['ok']);self.assertEqual(self.executor.mode,'READ_ONLY')
        self.assertEqual(self.waits,[]);self.assertEqual(len(self.broker.sent),1)

    def native_exit_fixture(self):
        """Synthetic broker TP: no management send was made by Executor."""
        entry_id=self.entry();position=self.broker._positions.pop()
        original=copy.deepcopy(self.broker._deals[-1])
        self.broker._deals.append({**original,'ticket':original['ticket']+1000,
            'order':original['order']+1000,'entry':1,'type':1,
            'profit':1.,'position_id':position['identifier']})
        return entry_id

    def test_native_tp_history_delay_keeps_authorization_blocks_sends_and_does_not_resend(self):
        identity=self.native_exit_fixture();authorization=self.executor.authorization
        reserved=self.store.intent(identity)['reserved']
        def blocked():
            self.assertIs(self.executor.authorization,authorization)
            self.assertEqual(self.store.intent(identity)['reserved'],reserved)
            with self.assertRaisesRegex(ValueError,'Unresolved'):self.executor._guard(entry=True)
            self.assertFalse(self.store.reserve('no-new-entry',self.risk.key,1.,{},[],10000.,now=self.now)['approved'])
        self.on_wait=blocked
        with self.delayed_exits(3.):result=self.executor.reconcile()
        self.assertTrue(result['ok'],result)
        self.assertEqual(self.elapsed,3.)
        self.assertIs(self.executor.authorization,authorization)
        self.assertEqual(self.executor.mode,'AUTO_DEMO')
        self.assertEqual(self.store.intent(identity)['state'],'CLOSED')
        self.assertEqual(self.store.intent(identity)['reserved'],0.)
        self.assertEqual(len(self.broker.sent),1)

    def test_native_exit_missing_past_deadline_revokes_and_later_confirmation_does_not_resume(self):
        identity=self.native_exit_fixture();reserved=self.store.intent(identity)['reserved']
        with self.delayed_exits(100.):result=self.executor.reconcile()
        self.assertFalse(result['ok']);self.assertEqual(self.elapsed,SETTLEMENT_GRACE_SECONDS)
        self.assertEqual(self.executor.mode,'READ_ONLY')
        self.assertEqual(self.store.intent(identity)['reserved'],reserved)
        self.assertTrue(self.executor.reconcile()['ok'])
        self.assertEqual(self.executor.mode,'READ_ONLY')
        self.assertEqual(len(self.broker.sent),1)

    def test_native_exit_grace_never_hides_unrelated_management_uncertainty(self):
        self.entry();self.pending_protection()
        self.broker._positions.pop()
        # A disappeared position does not settle an unconfirmed unrelated
        # protection amendment; no history/receipt may be invented for it.
        with self.delayed_exits(3.):result=self.executor.reconcile()
        self.assertFalse(result['ok']);self.assertEqual(self.waits,[])
        self.assertEqual(self.executor.mode,'READ_ONLY')

    def test_native_exit_grace_never_starts_for_a_preexisting_unknown(self):
        identity=self.native_exit_fixture()
        self.store.set_intent_state(identity,'UNKNOWN',reason='Prior ambiguity')
        with self.delayed_exits(3.):result=self.executor.reconcile()
        self.assertFalse(result['ok']);self.assertEqual(self.waits,[])
        self.assertEqual(self.executor.mode,'READ_ONLY')

    def test_native_exit_grace_revokes_on_account_change(self):
        self.native_exit_fixture()
        self.on_wait=lambda:self.broker._account.update(login=900002)
        with self.delayed_exits(3.):result=self.executor.reconcile()
        self.assertFalse(result['ok']);self.assertEqual(self.executor.mode,'READ_ONLY')
        self.assertIsNone(self.executor.authorization);self.assertEqual(len(self.broker.sent),1)

    def assert_changed_context_revokes(self,change):
        self.entry();self.on_wait=change
        with self.delayed_exits(.5):result=self.executor.flatten_owned_positions()
        self.assertFalse(result['ok'])
        self.assertEqual(self.executor.mode,'READ_ONLY');self.assertIsNone(self.executor.authorization)
        self.assertEqual(len(self.broker.sent),2)

    def test_day_change_during_grace_revokes(self):
        self.assert_changed_context_revokes(lambda:setattr(self,'now',self.now+86400))

    def test_account_change_during_grace_revokes(self):
        self.assert_changed_context_revokes(lambda:self.broker._account.update(login=900002))

    def test_permission_change_during_grace_revokes(self):
        self.assert_changed_context_revokes(lambda:self.broker._account.update(trade_allowed=False))

    def test_settings_change_during_grace_revokes(self):
        self.assert_changed_context_revokes(lambda:self.risk.settings.update(slippage_points=20))

    def test_explicit_revocation_during_grace_is_never_restored(self):
        self.assert_changed_context_revokes(lambda:self.executor.deactivate('fixture explicit revocation'))

    def test_unrelated_unresolved_result_does_not_receive_success_ack_grace(self):
        self.entry();original=self.broker.deals;inserted=[]
        position=copy.deepcopy(self.broker.positions()[0])
        def records(since):
            rows=original(since)
            if len(self.broker.sent)>1:
                if not inserted:
                    request={'action':'SLTP','symbol':position['symbol'],'position':position['ticket'],'sl':1.077,'tp':1.09}
                    self.store.management_intent('unrelated',self.risk.key,request,'unrelated fixture',self.now)
                    self.store.set_intent_state('unrelated','UNKNOWN',reason='unrelated fixture')
                    inserted.append(True)
                return [row for row in rows if row.get('entry')==0]
            return rows
        with patch.object(self.broker,'deals',side_effect=records):result=self.executor.flatten_owned_positions()
        self.assertFalse(result['ok']);self.assertEqual(self.waits,[])
        self.assertEqual(self.executor.mode,'READ_ONLY');self.assertEqual(len(self.broker.sent),2)

    def test_stalled_injected_monotonic_clock_cannot_create_unbounded_retry_loop(self):
        self.entry()
        self.executor._settlement_sleep=lambda seconds:self.waits.append(seconds)
        with self.delayed_exits(100.):result=self.executor.flatten_owned_positions()
        self.assertFalse(result['ok']);self.assertEqual(self.executor.mode,'READ_ONLY')
        self.assertLessEqual(len(self.waits),SETTLEMENT_MAX_READS-1)
        self.assertEqual(len(self.broker.sent),2)

    def test_unexpected_guard_failure_is_not_treated_as_normal_pending_confirmation(self):
        self.entry();original=self.executor._guard
        def guard(*args,**kwargs):
            if len(self.broker.sent)>1:raise ValueError('fixture invalid journal')
            return original(*args,**kwargs)
        with self.delayed_exits(100.),patch.object(self.executor,'_guard',side_effect=guard):
            result=self.executor.flatten_owned_positions()
        self.assertFalse(result['ok']);self.assertEqual(self.waits,[])
        self.assertEqual(self.executor.mode,'READ_ONLY');self.assertEqual(len(self.broker.sent),2)


if __name__=='__main__':unittest.main()
