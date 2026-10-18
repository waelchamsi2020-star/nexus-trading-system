"""Calendar-period isolation proofs using synthetic engine fixtures only."""
import copy
import hashlib
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_long_walkforward import card

from nexus.strategies import REGISTRY

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('long_temporal_validation_fixture', ROOT / 'tools/long_temporal_validation.py')
temporal = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(temporal)


def cache_and_study():
    count = 24000
    rows = [{'time': 1_600_000_000 + i * 3600, 'open': 100., 'high': 100.5, 'low': 99.5,
             'close': 100., 'tick_volume': 100, 'real_volume': 0, 'spread': 2} for i in range(count)]
    cache = {'bars': rows, 'symbol': 'SYNTHETIC', 'timeframe': 'H1',
             'atr_values': [1.] * count, 'segment_starts': [0] * count,
             'cards': {'engulfing': [{'index': 5024 + i * 8000, 'card': card()} for i in range(3)]},
             'specification': {'point': .01, 'contract_size': 100000., 'profit_currency': 'USD', 'symbol': 'SYNTHETIC'},
             'provenance': {'csv_sha256': 'SYNTHETIC_TEST_FIXTURE', 'lookback_bars': 300}}
    study = {'symbol': 'SYNTHETIC', 'timeframe': 'H1', 'source_data_sha256': 'SYNTHETIC_TEST_FIXTURE',
             'scenarios': [{'commission_usd_round_trip_per_lot': 0., 'top5': ['support_bounce'], 'models': []},
                           {'commission_usd_round_trip_per_lot': 7., 'top5': ['engulfing', 'support_bounce'],
                            'models': [{'model': 'support_bounce', 'trades': 40, 'net_r': 2.},
                                       {'model': 'engulfing', 'trades': 30, 'net_r': 3.}]}]}
    return cache, study


class LongTemporalValidation(unittest.TestCase):
    def test_periods_are_equal_elapsed_calendar_time_not_equal_bar_counts(self):
        bars = [{'time': hour * 3600} for hour in (0, 1, 2, 8, 9)]
        periods = temporal.calendar_slices(bars)
        self.assertEqual([3, 0, 2], [row['bars'] for row in periods])
        self.assertEqual([(0, 3), (3, 3), (3, 5)], [(row['lo'], row['hi']) for row in periods])
        self.assertEqual([12000.] * 3, [row['calendar_end'] - row['calendar_start'] for row in periods])
        self.assertIsNone(periods[1]['first_candle_open'])
        self.assertEqual(36000, periods[-1]['last_candle_close'])

    def test_selection_uses_only_fixed_fee7_netR_minimum30_and_validates_recorded_top5(self):
        _, study = cache_and_study()
        self.assertEqual('engulfing', temporal.select_fixed_fee7_best(study))
        invalid = copy.deepcopy(study)
        invalid['scenarios'][-1]['top5'].reverse()
        with self.assertRaisesRegex(ValueError, 'top5'):
            temporal.select_fixed_fee7_best(invalid)
        invalid = copy.deepcopy(study)
        invalid['scenarios'][-1]['models'][1]['trades'] = 29
        invalid['scenarios'][-1]['top5'] = ['support_bounce']
        self.assertEqual('support_bounce', temporal.select_fixed_fee7_best(invalid))

    def test_exactly_three_fresh_engine_calls_with_period_owned_training_and_no_old_ledger_filtering(self):
        cache, study = cache_and_study()
        calls = []

        def replay(local_cache, train, test, step, embargo, model_ids, lo, hi):
            calls.append((train, test, step, embargo, model_ids, lo, hi))
            return {'folds': [{'train_start': lo, 'train_end': lo + 5000,
                               'test_start': lo + 5024, 'test_end': lo + 6024}],
                    'scenarios': [{'commission_usd_round_trip_per_lot': 7., 'models': [{
                        'model': 'engulfing', 'trades': 31, 'net_r': 1., 'win_rate': .6,
                        'sharpe': .1, 'max_dd': 2., 'censored': 0, 'trade_records': []}]}],
                    'primary_base_books': {'engulfing': {'censored': []}}, 'unused_tail_bars': 0}

        with patch.object(temporal, 'run_study', side_effect=replay):
            report = temporal.evaluate_temporal(cache, study)
        self.assertEqual([(0, 8000), (8000, 16000), (16000, 24000)], [(call[-2], call[-1]) for call in calls])
        self.assertTrue(all(call[:5] == (5000, 1000, 500, 24, ['engulfing']) for call in calls))
        self.assertEqual(3, report['positive_periods_n_ge_30'])
        self.assertTrue(all(row['fresh_replay'] for row in report['periods']))
        self.assertFalse(report['qualified'])
        self.assertTrue(report['selection_reuse'])
        self.assertFalse(report['genuinely_unseen_out_of_sample'])

    def test_earlier_period_prices_cannot_change_later_period_actual_fits_or_trades(self):
        cache, study = cache_and_study()
        before = temporal.evaluate_temporal(cache, study)
        changed = copy.deepcopy(cache)
        for row in changed['bars'][:8000]:
            row.update(open=1000., high=1200., low=800., close=1100.)
        # Recompute causal ATR values from the changed bars, including the
        # trailing effect across the cut. Each new period fit excludes first14.
        import long_signal_cache
        changed['segment_starts'], changed['atr_values'] = long_signal_cache.segment_arrays(changed['bars'], 'H1', 'CONTINUOUS')
        after = temporal.evaluate_temporal(changed, study)
        self.assertEqual(before['periods'][1:], after['periods'][1:])
        self.assertTrue(all(row['folds'] == 4 for row in before['periods']))
        self.assertTrue(all(row['trades'] == 1 for row in before['periods']))
        self.assertEqual(0, before['positive_periods_n_ge_30'])

    def test_inconsistent_source_and_cross_period_fit_fail_closed(self):
        cache, study = cache_and_study()
        wrong = copy.deepcopy(study)
        wrong['source_data_sha256'] = 'CHANGED'
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            temporal.evaluate_temporal(cache, wrong)
        changed = copy.deepcopy(cache)
        changed['provenance']['lookback_bars'] = 5001
        with self.assertRaisesRegex(ValueError, 'lookback'):
            temporal.evaluate_temporal(changed, study)
        with self.assertRaises(ValueError):
            temporal.calendar_slices([{'time': 2}, {'time': 1}])
        invalid_fit = {'folds': [{'train_start': -1, 'train_end': 5000,
                                 'test_start': 5024, 'test_end': 6024}],
                       'scenarios': [{'commission_usd_round_trip_per_lot': 7.,
                                      'models': [{'model': 'engulfing'}]}]}
        with (patch.object(temporal, 'run_study', return_value=invalid_fit),
              self.assertRaisesRegex(ValueError, 'crosses')):
            temporal.evaluate_temporal(cache, study)

    def test_incomplete_existing_cache_rejected_without_triggering_signal_computation(self):
        import long_signal_cache as signals
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / 'SYNTHETIC_FIXTURE.csv'
            csv_path.write_bytes(b'SYNTHETIC_TEST_FIXTURE_NOT_REAL_BARS')
            fingerprint = hashlib.sha256(csv_path.read_bytes()).hexdigest()
            metadata = {'source': 'MT5_NATIVE', 'aggregated': False, 'timeframe': 'H1',
                        'symbol': 'SYNTHETIC', 'point': .01, 'calendar_profile': 'CONTINUOUS',
                        'csv_sha256': fingerprint}
            spec = {'cache_version': signals.CACHE_VERSION, 'csv_sha256': fingerprint,
                    'source_sha256': 'SOURCE', 'symbol': 'SYNTHETIC', 'timeframe': 'H1',
                    'point': .01, 'profile': 'CONTINUOUS', 'model_ids': sorted(REGISTRY),
                    'start_index': 5024, 'lookback_bars': 300, 'python_version': list(sys.version_info[:3])}
            previous = {**spec, 'cache_key': hashlib.sha256(signals._encoded(spec)).hexdigest(),
                        'cache_directory': str(Path(directory) / 'missing-chunks'), 'bar_count': 5025}
            study = {'source_data_sha256': fingerprint, 'cache_provenance': previous}
            with (patch.object(signals, 'source_fingerprint', return_value='SOURCE'),
                  patch.object(signals, 'build_cache') as build,
                  self.assertRaisesRegex(RuntimeError, 'no recomputation')):
                temporal.load_complete_cache(csv_path, metadata, study)
            build.assert_not_called()


if __name__ == '__main__':
    unittest.main()
