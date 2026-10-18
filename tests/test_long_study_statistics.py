"""Resampling mathematics/ledger validation on labeled synthetic fixtures."""
import copy
import importlib.util
import unittest
from pathlib import Path

import numpy as np

from nexus.strategies import REGISTRY

_path = Path(__file__).resolve().parents[1] / 'tools/long_study_statistics.py'
_spec = importlib.util.spec_from_file_location('long_study_statistics_fixture', _path)
stats = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(stats)


def fixture_document():
    rows = [{'model': model, 'trades': []} for model in sorted(REGISTRY)]
    for index, r in enumerate([-1., 2., 1., .2, .5] * 8):
        rows[0]['trades'].append({'r': r, 'entry_time': 1000 + index * 3600,
                                 'exit_time': 1100 + index * 3600,
                                 'symbol': 'SYNTHETIC', 'timeframe': 'H1', 'fold_id': index // 5})
    return {'commission_usd_round_trip_per_lot': 7., 'slippage_points_per_side': 10,
            'models': rows, 'protocol': 'SYNTHETIC TEST FIXTURE ONLY'}


class LongStudyStatistics(unittest.TestCase):
    def test_null_centered_monte_carlo_pvalue_and_ci_match_independent_manual_calculation(self):
        values = np.array([-1., 0., 2.])
        seed, iterations = 71, 10000
        rng = np.random.default_rng(seed)
        sampled = values[rng.integers(0, 3, size=(iterations, 3))].mean(axis=1)
        observed = float(values.mean())
        expected_p = (np.count_nonzero(np.abs(sampled - observed) >= abs(observed)) + 1) / (iterations + 1)
        actual = stats.bootstrap_iid(values, iterations=iterations, seed=seed, batch_size=137)
        self.assertEqual(expected_p, actual['p_two_sided_null_centered'])
        np.testing.assert_array_equal(np.quantile(sampled, [.025, .975]), actual['mean_ci95'])
        np.testing.assert_array_equal(np.quantile(sampled, [.025, .975]) * 3, actual['total_ci95'])
        self.assertEqual(float(sampled.mean()), actual['bootstrap_mean_r'])

    def test_chunk_size_and_model_input_order_do_not_change_random_results(self):
        values = [-2., -.3, .2, 1., 4.] * 7
        first = stats.bootstrap_iid(values, iterations=1031, seed=55, batch_size=1)
        second = stats.bootstrap_iid(values, iterations=1031, seed=55, batch_size=137)
        self.assertEqual(first, second)
        document = fixture_document()
        before = stats.analyze_study(document, iterations=100)
        document['models'].reverse()
        after = stats.analyze_study(document, iterations=100)
        self.assertEqual(before, after)

    def test_multiple_comparisons_include_all_58_with_no_trade_p_one(self):
        document = fixture_document()
        result = stats.analyze_study(document, iterations=1000)
        self.assertEqual(58, result['family_size'])
        self.assertEqual(1, result['models_with_trades'])
        self.assertEqual(57, sum(row['iid']['p_two_sided_null_centered'] == 1. for row in result['models'][1:]))
        first = result['models'][0]
        self.assertEqual(min(1., first['iid']['p_two_sided_null_centered'] * 58), first['p_bonferroni_all_models'])
        self.assertEqual(first['model'], result['selected_best_model'])
        self.assertFalse(result['qualified'])
        self.assertFalse(result['execution_authority'])
        self.assertTrue(all(not period['fresh_replay'] for period in first['periods_descriptive']))

    def test_bh_matches_hand_calculated_family_and_rejects_invalid_pvalues(self):
        bonferroni, bh = stats.adjusted_pvalues([.01, .04, .03, 1.])
        np.testing.assert_allclose([.04, .16, .12, 1.], bonferroni)
        np.testing.assert_allclose([.04, .05333333333333334, .05333333333333334, 1.], bh)
        for bad in ([], [float('nan')], [-.01], [1.1]):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                stats.adjusted_pvalues(bad)

    def test_duplicate_and_overlapping_trades_are_rejected_not_deduplicated_silently(self):
        row = {'r': 1., 'entry_time': 100., 'exit_time': 200., 'symbol': 'TEST', 'timeframe': 'H1'}
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            stats.validate_unique_trades('fixture', [row, {**row, 'r': -2.}])
        with self.assertRaisesRegex(ValueError, 'Overlapping'):
            stats.validate_unique_trades('fixture', [row, {**row, 'entry_time': 150., 'exit_time': 250.}])
        self.assertEqual(2, len(stats.validate_unique_trades('fixture', [row, {**row, 'symbol': 'OTHER'}])))
        self.assertEqual(2, len(stats.validate_unique_trades('fixture', [row, {**row, 'entry_time': 200., 'exit_time': 300.}])))

    def test_short_samples_not_promoted_and_primary_costs_cannot_be_changed(self):
        document = fixture_document()
        document['models'][0]['trades'] = document['models'][0]['trades'][:4]
        result = stats.analyze_study(document, iterations=100)
        self.assertIsNone(result['selected_best_model'])
        self.assertEqual([], result['top5'])
        self.assertTrue(result['models'][0]['short_sample'])
        for commission in (0., 3., True):
            invalid = copy.deepcopy(document)
            invalid['commission_usd_round_trip_per_lot'] = commission
            with self.subTest(commission=commission), self.assertRaises(ValueError):
                stats.analyze_study(invalid, iterations=100)
        invalid = copy.deepcopy(document)
        invalid['models'].pop()
        with self.assertRaisesRegex(ValueError, 'all 58'):
            stats.analyze_study(invalid, iterations=100)

    def test_cluster_sensitivity_uses_whole_time_groups_and_reports_insufficient_groups(self):
        trades = fixture_document()['models'][0]['trades']
        first = stats.cluster_sensitivity(trades, iterations=1000, seed=40, batch_size=1)
        second = stats.cluster_sensitivity(trades, iterations=1000, seed=40, batch_size=256)
        self.assertEqual(first, second)
        self.assertEqual(8, first['cluster_count'])
        self.assertTrue(all(count == 5 for count in first['clusters'].values()))
        fewer = stats.cluster_sensitivity(trades[:15], iterations=1000)
        self.assertEqual('INSUFFICIENT_TIME_CLUSTERS', fewer['status'])
        self.assertEqual(1., fewer['p_two_sided_null_centered'])

    def test_invalid_returns_intervals_periods_and_bootstrap_controls_rejected(self):
        for invalid in ([float('inf')], [[1., 2.]], [float('nan')]):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                stats.bootstrap_iid(invalid)
        for controls in ({'iterations': 99}, {'seed': -1}, {'batch_size': 0}, {'iterations': True}):
            with self.subTest(controls=controls), self.assertRaises(ValueError):
                stats.bootstrap_iid([1., -1.], **controls)
        for row in ({'r': True, 'entry_time': 1, 'exit_time': 2},
                    {'r': 1., 'entry_time': 3, 'exit_time': 2}):
            with self.subTest(row=row), self.assertRaises(ValueError):
                stats.validate_unique_trades('fixture', [row])
        invalid = fixture_document()
        invalid['period_boundaries'] = [0., 1., 1., 2.]
        with self.assertRaises(ValueError):
            stats.analyze_study(invalid, iterations=100)


if __name__ == '__main__':
    unittest.main()
