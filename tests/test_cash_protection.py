"""Cash protection on synthetic owned positions; never sends to MT5."""
import unittest
from unittest.mock import patch

import test_risk_execution as fixtures


class CashProtectionTests(unittest.TestCase):
    setUp=fixtures.RiskExecutionTests.setUp
    tearDown=fixtures.RiskExecutionTests.tearDown
    activate=fixtures.RiskExecutionTests.activate
    proposal=fixtures.RiskExecutionTests.proposal
    entry=fixtures.RiskExecutionTests.entry

    def open_cash(self,side='BUY',**settings):
        settings.setdefault('fast_cash_target_usd',2.)
        self.settings.update(fast_profit_protection=True,**settings)
        self.broker._symbols['EURUSD.demo']['trade_stops_level']=0
        overrides={'id':'cash-'+side+'-'+str(len(self.store.intents())),'execution_style':'SCALP','scalp_variant':'fast','requested_risk_percent':1}
        if side=='SELL':overrides.update(side='SELL',sl=1.085,tp=1.07)
        self.entry(**overrides)
        return self.broker.positions()[0]

    def test_one_dollar_policy_closes_without_waiting_for_two_buy_and_sell(self):
        for side in ('BUY','SELL'):
            p=self.open_cash(side,fast_cash_target_usd=1.)
            self.mark_net(p,1.01)
            result=self.executor.manage();self.assertTrue(result['ok'],result)
            self.assertFalse(self.broker.positions())
            self.assertEqual(self.store.intent(result['results'][0]['intent_id'])['payload']['reason'],'FAST_CASH_TARGET')

    def test_one_dollar_native_target_includes_costs(self):
        p=self.open_cash(fast_cash_target_usd=1.,commission_per_lot=4)
        self.mark_net(p,.5)
        result=self.executor.manage();self.assertTrue(result['ok'],result)
        actual=self.broker.positions()[0]
        cash=self.executor._fast_cash_context(actual,self.risk._owned_intent(actual,self.store.intents()),self.store.intents(),self.broker.deals(0),self.broker.account())
        self.assertGreaterEqual(self.executor._fast_cash_net(actual,cash,actual['tp'])+1e-8,1.)
        self.assertLess(self.executor._fast_cash_net(actual,cash,actual['tp']-cash['sign']*cash['info']['trade_tick_size']),1.)
        self.assertEqual(actual['sl'],p['sl'])

    def mark_net(self,position,value):
        account,intents,_positions,_orders,deals,_history=self.executor._history_book(self.risk.key)
        owner=self.risk._owned_intent(position,intents)
        cash=self.executor._fast_cash_context(position,owner,intents,deals,account)
        unit=self.broker.symbol(position['symbol'])['trade_contract_size']*position['volume']
        price=position['price_open']+cash['sign']*((value-cash['paid']-cash['swap']+cash['fee'])/unit+cash['slip'])
        self.broker._prices[position['symbol']]=price if position['type']==0 else price-self.broker.symbol(position['symbol'])['point']

    def test_below_dollar_installs_broker_cash_target_without_changing_stop(self):
        p=self.open_cash();self.mark_net(p,.9)
        self.assertTrue(self.executor.manage()['ok'])
        self.assertEqual(len(self.broker.sent),2)
        self.assertEqual(self.broker.positions()[0]['sl'],p['sl'])
        self.assertEqual(self.broker.sent[-1]['action'],'SLTP')
        self.assertLess(self.broker.positions()[0]['tp'],p['tp'])

    def test_dollar_is_protected_by_broker_stop_for_buy_and_sell(self):
        for side in ('BUY','SELL'):
            with self.subTest(side=side):
                if self.broker.positions():
                    self.executor.flatten_owned_positions('Fixture reset')
                p=self.open_cash(side);self.mark_net(p,1.7)
                result=self.executor.manage();self.assertTrue(result['ok'],result)
                actual=self.broker.positions()[0]
                self.assertEqual(self.broker.sent[-1]['action'],'SLTP')
                owner=self.risk._owned_intent(actual,self.store.intents())
                context=self.executor._fast_cash_context(actual,owner,self.store.intents(),self.broker.deals(0),self.broker.account())
                self.assertGreaterEqual(self.executor._fast_cash_net(actual,context,actual['sl'])+1e-8,1.)
                before=len(self.broker.sent);self.executor.manage()
                self.assertEqual(len(self.broker.sent),before)

    def test_two_dollars_closes_the_owned_position(self):
        p=self.open_cash();self.mark_net(p,2.1)
        result=self.executor.manage();self.assertTrue(result['ok'],result)
        self.assertFalse(self.broker.positions())
        intent=self.store.intent(result['results'][0]['intent_id'])
        self.assertEqual(intent['payload']['reason'],'FAST_CASH_TARGET')
        self.assertTrue(intent['payload']['confirmed'])

    def test_broker_distance_falls_back_to_profit_close(self):
        p=self.open_cash();self.mark_net(p,1.1)
        self.broker._symbols[p['symbol']]['trade_stops_level']=100
        result=self.executor.manage();self.assertTrue(result['ok'],result)
        self.assertFalse(self.broker.positions())
        self.assertEqual(self.store.intent(result['results'][0]['intent_id'])['payload']['reason'],'FAST_CASH_PROTECT_FALLBACK')

    def test_target_is_rechecked_after_preflight_price_drop(self):
        p=self.open_cash();self.mark_net(p,2.1)
        self.broker.check_hook=lambda request:self.mark_net(p,.8)
        result=self.executor.manage()
        self.assertFalse(result['ok'])
        self.assertEqual(len(self.broker.sent),1)
        self.assertTrue(self.broker.positions())

    def test_costs_are_included_before_protecting_profit(self):
        p=self.open_cash(commission_per_lot=4)
        self.mark_net(p,.9)
        self.executor.manage();self.assertEqual(len(self.broker.sent),2)
        self.assertEqual(self.broker.positions()[0]['sl'],p['sl'])
        self.mark_net(p,1.7)
        result=self.executor.manage();self.assertTrue(result['ok'],result)
        self.assertEqual(self.broker.sent[-1]['action'],'SLTP')

    def test_native_cash_target_buy_sell_costs_and_no_repeated_amendment(self):
        for side in ('BUY','SELL'):
            with self.subTest(side=side):
                if self.broker.positions():self.executor.flatten_owned_positions('Fixture reset')
                p=self.open_cash(side,commission_per_lot=4);self.mark_net(p,.5)
                result=self.executor.manage();self.assertTrue(result['ok'],result)
                actual=self.broker.positions()[0];self.assertEqual(actual['sl'],p['sl'])
                cash=self.executor._fast_cash_context(actual,self.risk._owned_intent(actual,self.store.intents()),
                    self.store.intents(),self.broker.deals(0),self.broker.account())
                self.assertGreaterEqual(self.executor._fast_cash_net(actual,cash,actual['tp'])+1e-8,2.)
                grid=cash['info']['trade_tick_size']
                self.assertLess(self.executor._fast_cash_net(actual,cash,actual['tp']-cash['sign']*grid),2.)
                before=len(self.broker.sent);self.executor.manage();self.assertEqual(len(self.broker.sent),before)

    def test_native_target_never_pushes_a_closer_existing_target_away(self):
        p=self.open_cash();self.mark_net(p,.5)
        self.broker._positions[0]['tp']=self.broker._positions[0]['price_open']+.00001
        before=len(self.broker.sent)
        self.executor.manage();self.assertEqual(len(self.broker.sent),before)

    def test_native_target_unavailable_distance_does_not_change_loss_stop(self):
        p=self.open_cash();self.mark_net(p,.5)
        self.broker._symbols[p['symbol']]['trade_stops_level']=100
        before=len(self.broker.sent);self.executor.manage()
        self.assertEqual(len(self.broker.sent),before)
        self.assertEqual(self.broker.positions()[0]['sl'],p['sl'])

    def test_native_target_rechecks_geometry_after_broker_preflight(self):
        p=self.open_cash();self.mark_net(p,.5)
        self.broker.check_hook=lambda request:self.mark_net(p,4.)
        result=self.executor.manage();self.assertTrue(result['ok'],result)
        self.assertEqual(len(self.broker.sent),2)
        self.assertFalse(self.broker.positions())
        self.assertEqual(self.store.intent(result['results'][0]['intent_id'])['payload']['reason'],'FAST_CASH_TARGET')

    def test_known_protection_rejection_falls_back_to_verified_profit_close(self):
        p=self.open_cash();self.mark_net(p,1.7);self.broker.special='reject'
        result=self.executor.manage();self.assertTrue(result['ok'],result)
        self.assertFalse(self.broker.positions())
        self.assertEqual(self.store.intent(result['results'][0]['intent_id'])['payload']['reason'],'FAST_CASH_PROTECT_FALLBACK')

    def test_target_ack_then_immediate_owned_close_is_reconciled(self):
        p=self.open_cash();self.mark_net(p,.5);send=self.broker.send
        def close_after_ack(request):
            result=send(request)
            if request['action']=='SLTP':
                send({'action':'DEAL','symbol':p['symbol'],'position':p['ticket'],'side':'SELL',
                    'volume':p['volume'],'price':request['tp'],'magic':self.risk.magic,
                    'comment':p['comment'],'sl':0,'tp':0,'_authorized_account_key':request['_authorized_account_key']})
            return result
        with patch.object(self.broker,'send',side_effect=close_after_ack):result=self.executor.manage()
        self.assertTrue(result['ok'],result);self.assertFalse(self.broker.positions())
        self.assertTrue(self.store.intent(result['results'][0]['intent_id'])['payload']['confirmed'])

    def test_rejected_cash_target_does_not_suppress_original_invalidation(self):
        p=self.open_cash();self.mark_net(p,.5);self.broker.special='reject'
        with patch.object(self.executor,'_completed_bar_exit',side_effect=[None,'PLAN_COMPLETED_BAR_INVALIDATION']):
            result=self.executor.manage()
        self.assertFalse(result['ok']);self.assertFalse(self.broker.positions())
        self.assertEqual(self.broker.sent[-1]['action'],'DEAL')

    def test_existing_bar_invalidation_precedes_installing_cash_target(self):
        p=self.open_cash();self.mark_net(p,.5)
        with patch.object(self.executor,'_completed_bar_exit',return_value='PLAN_COMPLETED_BAR_INVALIDATION'):
            result=self.executor.manage()
        self.assertTrue(result['ok'],result);self.assertFalse(self.broker.positions())
        self.assertEqual(len(self.broker.sent),2)
        self.assertEqual(self.broker.sent[-1]['action'],'DEAL')

    def test_non_dollar_account_cannot_enable_cash_policy(self):
        self.broker._account['currency']='EUR'
        with self.assertRaisesRegex(ValueError,'USD Demo'):
            self.activate(fast_profit_protection=True)

    def test_legacy_and_external_positions_are_not_closed_for_cash(self):
        self.entry();p=self.broker.positions()[0]
        self.broker._prices[p['symbol']]=p['price_open']+.001
        self.executor.manage();self.assertEqual(len(self.broker.sent),1)

if __name__=='__main__':unittest.main()
