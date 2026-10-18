"""Temporal and cost-accounting checks independent of strategy profitability."""
import copy
import unittest
from unittest.mock import patch

from nexus.broker import SimBroker
from nexus.quant import analyze_strategy
from nexus.walkforward import LookaheadBiasError, evaluate_history


# Vulture review: unittest/pytest discovers and executes this TestCase by module inspection.
class WalkForwardReview(unittest.TestCase):
    def setUp(self):
        self.now=1800000000.
        self.rows=SimBroker(lambda:self.now).bars('EURUSD.demo','M1',600)
        self.costs={'point':.00001,'slippage_price':.00002,
                    'commission_per_unit':.00003,'commission_known':True}

    def run_review(self,rows=None):
        return evaluate_history(self.rows if rows is None else rows,'ema_cross',symbol='FIXTURE',
                                timeframe='M1',as_of=self.now,costs=self.costs,data_kind='synthetic')

    def test_future_candle_raises_lookahead_bias_error(self):
        rows=self.rows+[dict(self.rows[-1],time=self.now)]
        with self.assertRaises(LookaheadBiasError):self.run_review(rows)

    def test_signals_only_receive_completed_prefix_and_training_precedes_embargo(self):
        seen=[]
        def observe(sid,symbol,tf,history,as_of,context):
            self.assertEqual(history[-1]['time']+60,as_of)
            self.assertTrue(all(row['time']+60<=as_of for row in history))
            seen.append(as_of)
            return analyze_strategy(sid,symbol,tf,history,as_of,context)
        with patch('nexus.quant.analyze_strategy',side_effect=observe):report=self.run_review()
        self.assertTrue(seen)
        self.assertEqual(3,len(report['folds']))
        for fold in report['folds']:
            self.assertEqual(12,fold['test_start_index']-fold['train_end_exclusive'])
            self.assertEqual(250,fold['train_end_exclusive']-fold['train_start_index'])
            self.assertEqual(100,fold['test_end_exclusive']-fold['test_start_index'])
            self.assertTrue(all(t['exit_index']<fold['test_end_exclusive'] for t in fold['trades']))

    def test_later_window_mutation_cannot_change_first_test_fold_or_training(self):
        before=self.run_review()
        rows=copy.deepcopy(self.rows)
        end=before['folds'][0]['test_end_exclusive']
        for row in rows[end:]:
            for key in ('open','high','low','close'):row[key]*=1.01
        after=self.run_review(rows)
        self.assertEqual(before['folds'][0],after['folds'][0])

    def test_net_results_include_declared_commission_and_reject_gaps_short_history(self):
        report=self.run_review()
        trades=[t for fold in report['folds'] for t in fold['trades']]
        self.assertTrue(trades)
        for trade in trades:
            self.assertAlmostEqual(trade['gross_price_pnl']-.00003,trade['net_price_pnl'])
            self.assertEqual(.00003,trade['commission_price_units'])
        for rows in (self.rows[:499],self.rows[:300]+self.rows[301:]):
            with self.assertRaises(ValueError):self.run_review(rows)
        self.assertFalse(report['review']['execution_authority'])
        self.assertFalse(report['qualified'])
