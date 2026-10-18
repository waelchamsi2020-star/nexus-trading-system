"""Independent counterexamples found during the 0.6.1 model review."""
import json
import unittest
from datetime import UTC, datetime
from types import SimpleNamespace

from nexus import strategies as st
from nexus.execution import Executor


def sample():
    return [{'time': 1600000000+i*3600, 'open': 101., 'close': 101., 'high': 101.5,
                 'low': 100.5, 'tick_volume': 100, 'real_volume': 0, 'spread': 0} for i in range(60)]


def mirror(b):
    return [dict(x, open=200-x['open'], close=200-x['close'],
                 high=200-x['low'], low=200-x['high']) for x in b]


# Vulture review: unittest/pytest discovers and executes this TestCase by module inspection.
class RuleReview(unittest.TestCase):
    def test_rejection_close_must_be_on_valid_side_of_support_or_resistance(self):
        b=sample();b[50]['low']=100
        b[-2].update(open=100, high=100.1, low=99.89, close=99.91)
        b[-1].update(open=99.92, high=99.99, low=99.90, close=99.97)
        for rows in (b, mirror(b)):
            c=st.analyze_strategy('support_bounce','TEST','H1',rows,rows[-1]['time']+3600)
            self.assertFalse(c['actionable'],c)
            self.assertEqual(c['version'],'1.1.0')

    def test_fibonacci_cannot_infer_high_low_order_inside_one_outside_bar(self):
        b=sample()
        for x in b:x.update(open=100, close=100, high=100.5, low=99.5)
        b[55].update(high=110, low=90)
        b[-2].update(open=100, high=101.2, low=99.5, close=101)
        b[-1].update(open=102, high=103, low=98.5, close=99)
        for rows in (b, mirror(b)):
            c=st.analyze_strategy('fib_retracement','TEST','H1',rows,rows[-1]['time']+3600)
            self.assertFalse(c['actionable'],c)
            self.assertEqual(c['version'],'1.1.0')
            self.assertFalse(any(isinstance(e,dict) and 'index' in e for e in c['evidence']))

    def test_all_models_abstain_on_boolean_prices_volumes_or_time(self):
        for key in ('time','open','high','low','close','tick_volume','real_volume','spread'):
            b=sample();b[-1][key]=True
            for sid in st.REGISTRY:
                with self.subTest(key=key,model=sid):
                    c=st.analyze_strategy(sid,'TEST','H1',b,1600000000+60*3600)
                    self.assertEqual(c['status'],'DATA_INVALID')
                    self.assertFalse(c['actionable'])

    def test_malformed_records_and_analysis_clock_fail_closed_with_json_evidence(self):
        for rows,clock in ((None,1600300000),([None],1600300000),(sample(),True),
                           (sample(),'bad clock'),(sample(),float('inf'))):
            for sid in st.REGISTRY:
                c=st.analyze_strategy(sid,'TEST','H1',rows,clock)
                self.assertEqual(c['status'],'DATA_INVALID')
                json.dumps(c,allow_nan=False)

    def test_monthly_plan_uses_february_calendar_close(self):
        self.assertEqual(self.month_exit('2025-02-01','2025-03-01'),
                         'PLAN_COMPLETED_BAR_TIME_EXIT')
        self.assertEqual(self.month_exit('2024-02-01','2024-03-01'),
                         'PLAN_COMPLETED_BAR_TIME_EXIT')

    def test_large_rejection_candle_cannot_publish_a_negative_buffered_stop(self):
        b=sample()
        for x in b:x.update(open=1.,close=1.,high=1.05,low=.95)
        b[-2].update(open=.02,close=.01,high=.025,low=.005)
        b[-1].update(open=.009,close=100.,high=100.5,low=.005)
        c=st.analyze_strategy('engulfing','TEST','H1',b,b[-1]['time']+3600)
        self.assertEqual(c['status'],'WAIT')
        self.assertFalse(c['actionable'])
        self.assertIsNone(c['entry'])
        self.assertIsNone(c['stop'])
        self.assertIn('execution prices must be finite and positive',' '.join(c['conditions_missing']))
        self.assertEqual(c['score'],50.)
        self.assertEqual(c['gaps'],c['conditions_missing'])

    def test_monthly_plan_refuses_january_before_calendar_close(self):
        with self.assertRaises(ValueError):self.month_exit('2025-01-01','2025-01-31')
        self.assertEqual(self.month_exit('2025-01-01','2025-02-01'),
                         'PLAN_COMPLETED_BAR_TIME_EXIT')

    def month_exit(self,opening,now):
        def ts(s):return datetime.fromisoformat(s).replace(tzinfo=UTC).timestamp()
        executor=Executor.__new__(Executor)
        executor.broker=SimpleNamespace(bars=lambda *a:[{'time':ts(opening),'close':101.}])
        executor.clock=lambda:ts(now)
        return executor._completed_bar_exit({'symbol':'TEST','time':ts(opening),'type':0},
            {'payload':{'proposal':{'timeframe':'MN1'}}},
            {'timeframe':'MN1','max_hold_bars':1,'invalidation':None})
