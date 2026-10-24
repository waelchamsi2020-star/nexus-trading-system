"""Completed higher-frame direction for the explicit cash-protection route."""
import unittest
from unittest.mock import patch

import test_multischool as fixtures


class CashTrendTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.MultiSchoolTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.fixture.start();self.engine=self.fixture.engine;self.now=self.fixture.now
        # MultiSchoolTests.start installs a convenient default context stub;
        # these tests exercise the real causal MT5 context reader.
        del self.engine._cash_trend_context

    def bars(self,tf,up=True):
        seconds={'M15':900,'H1':3600,'H4':14400,'D1':86400}[tf];end=int(self.now//seconds)*seconds
        rows=[]
        for i in range(100):
            close=1.+(i if up else 100-i)*.0001
            rows.append({'time':end-(100-i)*seconds,'open':close,'close':close,'low':close-.00005,'high':close+.00005,'tick_volume':100})
        return rows

    def test_both_completed_trends_and_cache_account_scope(self):
        with patch.object(self.engine.broker,'bars',side_effect=lambda symbol,tf,count:self.bars(tf)) as read:
            trend=self.engine._cash_trend_context(self.fixture.fixture.symbol)
            self.assertEqual({v['direction'] for v in trend.values()},{'BUY'})
            self.engine._cash_trend_context(self.fixture.fixture.symbol);self.assertEqual(read.call_count,4)
            self.engine.risk.key='other-demo-scope'
            self.engine._cash_trend_context(self.fixture.fixture.symbol);self.assertEqual(read.call_count,8)

    def test_stale_cached_history_is_retried_when_broker_recovers_within_bucket(self):
        symbol=self.fixture.fixture.symbol;key=(self.engine.risk.key,symbol,'M15',int(self.now//900))
        self.engine._cash_trend_cache={key:{'data_time':self.now-4000,'direction':'NEUTRAL'}}
        with patch.object(self.engine.broker,'bars',side_effect=lambda symbol,tf,count:self.bars(tf)) as read:
            trend=self.engine._cash_trend_context(symbol)
        self.assertEqual(read.call_count,4)
        self.assertEqual({v['direction'] for v in trend.values()},{'BUY'})
        self.assertGreater(self.engine._cash_trend_cache[key]['data_time'],self.now-900)

    def test_sell_trend_uses_inverse_order_and_slope(self):
        with patch.object(self.engine.broker,'bars',side_effect=lambda symbol,tf,count:self.bars(tf,False)):
            self.assertEqual({v['direction'] for v in self.engine._cash_trend_context(self.fixture.fixture.symbol).values()},{'SELL'})

    def test_missing_stale_or_future_history_does_not_confirm(self):
        for kind in ('missing','stale','future'):
            self.engine._cash_trend_cache={}
            def read(symbol,tf,count,kind=kind):
                rows=self.bars(tf)
                if kind=='missing':return rows[:5]
                for row in rows:row['time']+=(-7200 if kind=='stale' else 7200)
                return rows
            with self.subTest(kind=kind), patch.object(self.engine.broker, 'bars', side_effect=read), self.assertRaises(ValueError):
                self.engine._cash_trend_context(self.fixture.fixture.symbol)

    def test_opposing_larger_trend_blocks_ready_m1_proposal(self):
        self.engine.settings['fast_profit_protection']=True
        opposed={'M15':'BUY','H1':'SELL','H4':'SELL','D1':'BUY'}
        with patch('nexus.multischool.analyze_all',side_effect=self.fixture.fixture_cards), \
             patch.object(self.engine,'_cash_trend_context',return_value={tf:{'direction':side} for tf,side in opposed.items()}):
            result=self.engine._multi_result(self.fixture.fixture.symbol)
        self.assertFalse(result['proposals'])
        self.assertTrue(any('majority' in str(r.get('reasons')) for r in result['ranked']))
        self.assertEqual(self.engine.broker.sent,[])

    def test_aligned_trend_is_bound_into_proposal_certificate(self):
        self.engine.settings['fast_profit_protection']=True
        aligned={tf:{'direction':'BUY'} for tf in fixtures.multischool.CONTEXT_FRAMES}
        with patch('nexus.multischool.analyze_all',side_effect=self.fixture.fixture_cards), \
             patch.object(self.engine,'_cash_trend_context',return_value=aligned):
            result=self.engine._multi_result(self.fixture.fixture.symbol)
        self.assertTrue(result['proposals'],result)
        self.assertEqual(set(result['proposals'][0]['decision_matrix']['higher_timeframe_trend']),set(fixtures.multischool.CONTEXT_FRAMES))

if __name__=='__main__':unittest.main()
