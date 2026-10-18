"""Independent fail-closed checks at financial and pre-send boundaries."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_risk_execution as fixtures

from nexus.store import Store, account_key


# Vulture review: unittest/pytest discovers and executes this TestCase by module inspection.
class CriticalFailureMatrix(unittest.TestCase):
    def fixture(self):
        f=fixtures.RiskExecutionTests();f.setUp()
        self.addCleanup(f.tearDown)
        return f

    def test_invalid_risk_settings_never_create_authorization_or_send(self):
        cases=[{'validation_policy':'unknown'},{'fast_profit_protection':1},
               {'fast_cash_target_usd':.5},{'risk_unit':'lots'},{'target_unit':'lots'},
               {'max_trade_fraction':1.1},{'correlation_cap_fraction':1.1},
               {'margin_fraction':1.1},{'commission_per_lot':-1},{'slippage_points':-1}]
        for override in cases:
            with self.subTest(override=override):
                f=self.fixture()
                with self.assertRaises(ValueError):f.activate(**override)
                self.assertEqual('READ_ONLY',f.executor.mode)
                self.assertEqual([],f.broker.sent)

    def test_unknown_execution_mode_or_margin_accounting_never_authorizes(self):
        f=self.fixture()
        with self.assertRaises(ValueError):f.executor.activate('UNKNOWN',f.settings)
        f.broker._account['margin_mode']=1
        with self.assertRaises(ValueError):f.activate()
        self.assertEqual([],f.broker.sent)

    def test_pre_send_rejects_changed_bridges_quote_zone_and_contract(self):
        for case in ('session','calendar','expiry','direction','zone','buy_stop','sell_stop',
                     'reservation','negative_margin','free_margin','crossed_quote'):
            with self.subTest(case=case):
                f=self.fixture();f.activate()
                p=f.proposal(side='SELL',sl=1.085,tp=1.065) if case=='sell_stop' else f.proposal()
                prepared=f.risk.prepare(p,clock=lambda fixture=f:fixture.now)
                self.assertTrue(prepared['approved'],prepared)
                intent=copy.deepcopy(f.store.intent(prepared['intent_id']))
                account=f.broker.account();symbol=p['symbol'];info=f.broker.symbol(symbol);tick=f.broker.tick(symbol)
                method=None;value=None
                if case=='session':method='session';value={'known':False}
                elif case=='calendar':method='calendar';value={'ok':False}
                elif case=='expiry':method='symbol';value={**info,'expiration_time':f.now-1}
                elif case=='direction':method='symbol';value={**info,'trade_mode':2}
                elif case=='zone':intent['payload']['proposal']['entry_zone']=[1.,1.01]
                elif case=='buy_stop':intent['payload']['request']['sl']=tick['bid']
                elif case=='sell_stop':intent['payload']['request']['sl']=tick['ask']
                elif case=='reservation':intent['reserved']=0.
                elif case=='negative_margin':method='calc_margin';value=-1.
                elif case=='free_margin':account['margin_free']=0.
                else:method='tick';value={**tick,'ask':tick['bid']-.01}
                if method:
                    with patch.object(f.broker,method,return_value=value),self.assertRaises(ValueError):
                        f.executor._entry_send_check(intent,account)
                else:
                    with self.assertRaises(ValueError):f.executor._entry_send_check(intent,account)
                self.assertEqual([],f.broker.sent)

    def test_absent_management_targets_and_failed_preflight_never_send(self):
        f=self.fixture();f.activate()
        for request in ({'action':'REMOVE','symbol':'EURUSD.demo','order':999},
                        {'action':'DEAL','symbol':'EURUSD.demo','position':999,'side':'SELL','volume':1.}):
            intent={'account_key':f.risk.key,'payload':{'request':request}}
            with self.subTest(request=request),self.assertRaises(ValueError):
                f.executor._management_send_check(intent)
        prepared=f.risk.prepare(f.proposal(),clock=lambda:f.now)
        self.assertTrue(prepared['approved'],prepared)
        with patch.object(f.broker,'check',return_value=None):
            result=f.executor._send(prepared['intent_id'],entry=True)
        self.assertFalse(result['approved'])
        self.assertEqual('REJECTED',f.store.intent(prepared['intent_id'])['state'])
        self.assertEqual(0.,f.store.intent(prepared['intent_id'])['reserved'])
        self.assertEqual([],f.broker.sent)


# Vulture review: unittest/pytest discovers and executes this TestCase by module inspection.
class LedgerFailureMatrix(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.store=Store(Path(self.directory.name)/'ledger.sqlite3')

    def tearDown(self):
        self.store.close();self.directory.cleanup()

    def test_incomplete_account_and_invalid_daily_limits_are_rejected(self):
        for missing in ('login','server','platform_id'):
            data={'login':1,'server':'fixture','platform_id':'fixture'};data[missing]=''
            with self.subTest(missing=missing),self.assertRaises(ValueError):account_key(data)
        for values in ((0,100,1000),(50,float('nan'),1000),(50,100,0)):
            with self.subTest(values=values),self.assertRaises(ValueError):self.store.ensure_day('account',*values)
        self.assertIsNone(self.store.get_day('account'))

    def test_invalid_reservations_caps_and_halted_day_cannot_commit_intent(self):
        for amount,available,caps in ((0,100,{}),(float('nan'),100,{}),(10,-1,{}),(10,100,{'x':-1})):
            with self.subTest(amount=amount,available=available),self.assertRaises(ValueError):
                self.store.reserve('entry','account',amount,{},['x'],available,caps)
        self.assertIsNone(self.store.intent('entry'))
        self.store.halt_day('account','fixture')
        self.assertEqual('DAILY_POLICY_HALTED',self.store.reserve('entry','account',10,{},[],100)['reason'])
        self.assertFalse(self.store.claim_send('absent'))

    def test_halt_between_prepare_and_claim_and_invalid_transitions_are_refused(self):
        self.assertTrue(self.store.reserve('entry','account',10,{},[],100)['approved'])
        self.store.halt_day('account','fixture')
        self.assertFalse(self.store.claim_send('entry'))
        self.assertEqual('PREPARED',self.store.intent('entry')['state'])
        with self.assertRaises(ValueError):self.store.set_intent_state('entry','UNKNOWN_STATE')
        with self.assertRaises(KeyError):self.store.set_intent_state('absent','REJECTED')
        with self.assertRaises(ValueError):self.store.set_intent_state('entry','PREPARED',reserved=-1)

    def test_invalid_and_unapproved_amendments_preserve_the_stored_day(self):
        with self.assertRaises(ValueError):self.store.amend_day_limits('account',-1,100)
        with self.assertRaises(ValueError):self.store.amend_day_limits('absent',50,100)
        before=self.store.ensure_day('account',50,100,1000)
        with self.assertRaises(ValueError):self.store.amend_day_limits('account',51,100)
        self.assertEqual(before,self.store.get_day('account'))
