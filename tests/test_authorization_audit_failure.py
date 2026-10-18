import sqlite3
import unittest
from unittest.mock import patch

import test_risk_execution as fixtures


# Vulture review: unittest/pytest discovers this TestCase class.
class AuthorizationAuditFailure(unittest.TestCase):
    def fixture(self):
        fixture=fixtures.RiskExecutionTests();fixture.setUp();self.addCleanup(fixture.tearDown)
        return fixture

    def test_authorization_and_daily_settings_audit_failure_never_grant_send_authority(self):
        for event in ('AUTHORIZATION_ACTIVATED','DAILY_SETTINGS'):
            with self.subTest(event=event):
                f=self.fixture();original=f.store.audit
                def failing(name,payload,event=event,original=original):
                    if name==event:raise sqlite3.OperationalError('Injected audit disk failure')
                    return original(name,payload)
                with patch.object(f.store,'audit',side_effect=failing),self.assertRaises(sqlite3.OperationalError):f.activate()
                self.assertEqual('READ_ONLY',f.executor.mode);self.assertIsNone(f.executor.authorization)
                self.assertEqual([],f.broker.sent)
                if event=='DAILY_SETTINGS':self.assertIsNone(f.risk.settings)

    def test_kill_switch_remains_effective_even_if_audit_write_fails(self):
        f=self.fixture();f.activate()
        with patch.object(f.store,'audit',side_effect=sqlite3.OperationalError('disk')), self.assertRaises(sqlite3.OperationalError):
            f.executor.deactivate('injected kill')
        self.assertEqual('READ_ONLY',f.executor.mode);self.assertIsNone(f.executor.authorization)
        self.assertFalse(f.executor.execute(f.proposal())['approved']);self.assertEqual([],f.broker.sent)

    def test_reservation_buy_sell_settings_and_rejection_have_correlated_audit(self):
        for side in ('BUY','SELL'):
            with self.subTest(side=side):
                f=self.fixture();f.activate()
                proposal=f.proposal(side=side)
                if side=='SELL':proposal.update(sl=1.09,tp=1.06)
                result=f.executor.execute(proposal)
                self.assertTrue(result['approved'])
                events=f.store.recent_audit(100)
                for name in ('DAILY_SETTINGS','AUTHORIZATION_ACTIVATED','RISK_RESERVED','INTENT_SENDING','INTENT_FILLED'):
                    self.assertTrue(any(x['event']==name for x in events),name)
                intent=f.store.intent(result['intent_id'])
                self.assertEqual(side,intent['payload']['request']['side'])
