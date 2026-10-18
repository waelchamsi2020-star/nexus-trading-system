"""Chronological research isolation, never a proof of a profitable edge."""
import copy
import importlib.util
import itertools
import unittest
from pathlib import Path
from unittest.mock import patch

from test_strategies import bars

from nexus.walkforward import LookaheadBiasError

_path = Path(__file__).resolve().parents[1] / 'tools/temporal_validation.py'
_spec = importlib.util.spec_from_file_location('temporal_validation_audit', _path)
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)


class TemporalValidationAudit(unittest.TestCase):
    def setUp(self):
        self.rows = bars(1200)
        self.args = {'symbol': 'TEST', 'timeframe': 'H1', 'as_of': 2_000_000_000,
                     'profile': 'CONTINUOUS', 'costs': {'point': .00001,
                     'slippage_price': .0001, 'commission_per_unit': .00007,
                     'commission_known': True}}

    def test_training_fit_is_invariant_to_all_heldout_prices(self):
        changed = copy.deepcopy(self.rows)
        for row in changed[600:]:
            for key in ('open', 'high', 'low', 'close'):
                row[key] *= 10
        with patch.object(audit, 'replay', return_value={'trades': [], 'signals': 0, 'skipped': []}):
            before = audit.validate_temporal_half(self.rows, **self.args)
            after = audit.validate_temporal_half(changed, **self.args)
        self.assertEqual(before['fitted_training_only'], after['fitted_training_only'])
        self.assertEqual(before['model_config_revision'], after['model_config_revision'])
        self.assertLessEqual(before['fitted_training_only']['maximum_input_close_time'],
                             before['heldout_first_time'])
        self.assertFalse(before['validation_pass'])
        self.assertTrue(before['post_selection_reused_data'])

    def test_replay_never_receives_other_half_or_carries_state_across_gap(self):
        rows = copy.deepcopy(self.rows)
        for row in rows[900:]:
            row['time'] += 3600
        calls = []

        def capture(segment, model, symbol, timeframe, start_index, end_index, config, context):
            calls.append((copy.deepcopy(segment), context['train_atr_median']))
            self.assertEqual(39, start_index)
            self.assertEqual(len(segment), end_index)
            self.assertTrue(all(b['time'] - a['time'] == 3600 for a, b in itertools.pairwise(segment)))
            return {'trades': [], 'signals': 0, 'skipped': []}

        with patch.object(audit, 'replay', side_effect=capture):
            report = audit.validate_temporal_half(rows, **self.args)
        self.assertEqual([600, 300, 300], [len(call[0]) for call in calls])
        self.assertEqual([rows[0]['time'], rows[600]['time'], rows[900]['time']],
                         [call[0][0]['time'] for call in calls])
        self.assertEqual(1, len({call[1] for call in calls}))
        self.assertEqual(2, report['heldout']['eligible_segments'])
        self.assertEqual(78, report['heldout']['warmup_bars'])

    def test_future_bar_rejected_and_below_200_heldout_segments_not_relaxed(self):
        invalid = copy.deepcopy(self.rows)
        invalid[-1]['time'] = self.args['as_of']
        with self.assertRaises(LookaheadBiasError):
            audit.validate_temporal_half(invalid, **self.args)
        with patch.object(audit, 'replay', return_value={'trades': [], 'signals': 0, 'skipped': []}):
            result = audit.validate_temporal_half(self.rows[:300], **self.args)
        self.assertEqual(0, result['heldout']['eligible_segments'])
        self.assertEqual(150, result['heldout']['ignored_bars_below_200'])
        self.assertFalse(result['validation_pass'])

    def test_signal_history_is_causal_in_actual_replay(self):
        seen = []

        def inspect(model, symbol, timeframe, history, as_of, context):
            self.assertLessEqual(history[-1]['time'] + 3600, as_of)
            self.assertTrue(all(row['time'] + 3600 <= as_of for row in history))
            seen.append((history[0]['time'], history[-1]['time'], as_of))
            return {'status': 'WAIT'}

        with patch('nexus.quant.analyze_strategy', side_effect=inspect):
            report = audit.validate_temporal_half(self.rows[:500], **self.args)
        self.assertTrue(seen)
        split_time = self.rows[250]['time']
        self.assertTrue(all(end < split_time or start >= split_time for start, end, _ in seen))
        self.assertEqual(1, report['heldout']['eligible_segments'])


if __name__ == '__main__':
    unittest.main()
