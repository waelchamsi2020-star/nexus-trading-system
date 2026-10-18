"""An uncertain protection change cannot outlive proven full owned closure."""
import copy

from test_settlement_grace import SettlementGraceTests


class ClosedProtectionReconciliationTests(SettlementGraceTests):
    # Inherit fixtures, not the already separately collected regression tests.
    def uncertain_protection(self):
        entry_id=self.entry();position=copy.deepcopy(self.broker.positions()[0])
        request={'action':'SLTP','symbol':position['symbol'],'position':position['ticket'],'sl':1.077,'tp':1.09}
        self.store.management_intent('uncertain-protection',self.risk.key,request,'fixture',self.now)
        self.store.set_intent_state('uncertain-protection','UNKNOWN',position_id=position['identifier'],
            position_volume_before=position['volume'],result={'retcode':10031},reason='Ambiguous broker result')
        self.executor.deactivate('network interruption')
        return entry_id,position

    def fully_close(self,position):
        original=copy.deepcopy(self.broker._deals[-1]);self.broker._positions.clear()
        self.broker._deals.append({**original,'ticket':original['ticket']+1000,'order':original['order']+1000,
            'entry':1,'type':1,'profit':1.,'position_id':position['identifier']})

    def test_uncertain_amendment_settles_only_after_proven_owned_full_exit(self):
        entry_id,position=self.uncertain_protection();self.fully_close(position)
        result=self.executor.reconcile();self.assertTrue(result['ok'],result)
        record=self.store.intent('uncertain-protection')
        self.assertEqual(record['state'],'CLOSED');self.assertTrue(record['payload']['confirmed'])
        self.assertFalse(record['payload']['amendment_confirmed'])
        self.assertEqual(self.store.intent(entry_id)['reserved'],0.)
        self.assertEqual(self.executor.mode,'READ_ONLY');self.assertEqual(len(self.broker.sent),1)
        self.executor.activate('AUTO_DEMO',self.settings)
        self.assertEqual(self.executor.mode,'AUTO_DEMO');self.assertEqual(len(self.broker.sent),1)

    def test_absence_without_exit_evidence_remains_unknown(self):
        _,_position=self.uncertain_protection();self.broker._positions.clear()
        self.assertFalse(self.executor.reconcile()['ok'])
        self.assertEqual(self.store.intent('uncertain-protection')['state'],'UNKNOWN')

    def test_live_position_with_different_ticket_same_identifier_remains_unknown(self):
        _,_position=self.uncertain_protection();self.broker._positions[0]['ticket']+=500
        self.assertFalse(self.executor.reconcile()['ok'])
        self.assertEqual(self.store.intent('uncertain-protection')['state'],'UNKNOWN')

    def test_insufficient_exit_volume_does_not_settle(self):
        _,position=self.uncertain_protection();self.fully_close(position)
        self.broker._deals[-1]['volume']=position['volume']/2
        self.assertFalse(self.executor.reconcile()['ok'])
        self.assertEqual(self.store.intent('uncertain-protection')['state'],'UNKNOWN')

    def test_unowned_closed_position_does_not_settle(self):
        entry_id,position=self.uncertain_protection();self.fully_close(position)
        self.store.set_intent_state(entry_id,'CANCELLED',confirmed=False)
        self.assertFalse(self.executor.reconcile()['ok'])
        self.assertEqual(self.store.intent('uncertain-protection')['state'],'UNKNOWN')


# Reuse only fixture methods, avoiding duplicate inherited test collection.
for _name in dir(SettlementGraceTests):
    if _name.startswith('test_') and _name not in ClosedProtectionReconciliationTests.__dict__:
        setattr(ClosedProtectionReconciliationTests,_name,None)
del SettlementGraceTests
