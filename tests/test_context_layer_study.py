"""Synthetic causal proofs for training-map selection, never market evidence."""
import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path

from test_long_walkforward import fixture_cache

from nexus.regime_router import load_routing_config
from nexus.strategies import REGISTRY
from nexus.walkforward import LookaheadBiasError

_spec = importlib.util.spec_from_file_location(
    'context_study_fixture', Path(__file__).resolve().parents[1] / 'tools/context_layer_study.py')
study = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(study)


def complete_cache():
    cache = fixture_cache(count=260, signals=tuple(range(70, 240, 8)))
    cache['provenance']['csv_sha256'] = 'a' * 64
    for model in REGISTRY:
        cache['cards'].setdefault(model, [])
    return cache


class ContextStudyCausality(unittest.TestCase):
    def test_training_map_is_invariant_to_all_embargo_and_test_prices_cards_and_outcomes(self):
        original = complete_cache()
        folds = study.fit_baselines(original, study.schedule(260, train=150, test=50, step=25))[:1]
        config = load_routing_config()
        contexts = study.classify_cache(original, config)
        before = study.fit_training_maps(original, folds, contexts, config)
        changed = copy.deepcopy(original)
        for row in changed['bars'][folds[0]['train_end']:]:
            row.update(open=900., high=999., low=800., close=950.)
        changed['cards']['engulfing'] = [row for row in changed['cards']['engulfing']
                                         if row['index'] < folds[0]['train_end']]
        after = study.fit_training_maps(changed, folds, study.classify_cache(changed, config), config)
        self.assertEqual(before, after)
        self.assertLess(before[0]['source']['last_outcome_time'],
                        study.bar_close_time(original['bars'][folds[0]['test_start']]['time'], 'H1'))

    def test_context_classifier_does_not_read_future_prices(self):
        cache = complete_cache()
        config = load_routing_config()
        before = study.classify_cache(cache, config)
        changed = copy.deepcopy(cache)
        for row in changed['bars'][121:]:
            row.update(open=1000., high=1200., low=800., close=1100.)
        after = study.classify_cache(changed, config)
        self.assertEqual({key: value for key, value in before.items() if key <= 120},
                         {key: value for key, value in after.items() if key <= 120})

    def test_training_context_injected_future_time_raises_lookahead_bias(self):
        cache = complete_cache()
        config = load_routing_config()
        contexts = study.classify_cache(cache, config)
        for value in contexts.values():
            value['decision_time'] += 10_000_000
        folds = study.fit_baselines(cache, study.schedule(260, train=150, test=50, step=25))[:1]
        with self.assertRaises(LookaheadBiasError):
            study.fit_training_maps(cache, folds, contexts, config)

    def test_selection_only_is_explicit_not_a_hidden_uncertain_bypass_in_routed_book(self):
        cache = complete_cache()
        config = load_routing_config()
        config['models']['engulfing']['regimes'] = ['ALL']
        contexts = study.classify_cache(cache, config)
        gate = study.ContextGate(cache, contexts, {0: config})
        control = study.ContextGate(cache, contexts, {0: config}, selection_only=True)
        row = cache['cards']['engulfing'][0]
        self.assertFalse(gate('engulfing', row['index'], row['card'], {'fold_id': 0})['allowed'])
        self.assertTrue(control('engulfing', row['index'], row['card'], {'fold_id': 0})['allowed'])

    def test_native_join_intersects_only_observed_past_candles_and_rejects_future(self):
        bars = fixture_cache(count=100)['bars']
        histories = {'GBPUSD': bars, 'USDJPY': bars[2:], 'DXY': bars[::2]}
        stamp = study.bar_close_time(bars[-1]['time'], 'H1')
        joined = study.align_native_legs(histories, stamp)
        keys = [[row['time'] for row in rows] for rows in joined.values()]
        self.assertEqual(keys[0], keys[1])
        self.assertEqual(keys[1], keys[2])
        self.assertEqual(49, len(keys[0]))
        self.assertTrue(all(row in histories[symbol] for symbol, rows in joined.items() for row in rows))
        with self.assertRaises(LookaheadBiasError):
            study.align_native_legs(histories, stamp - 1)

    def test_native_asof_join_uses_close_time_not_open_time(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'H4.csv'
            path.write_text('<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>,<TICKVOL>,<SPREAD>\n'
                            '2025.01.02,00:00:00,1,2,0.5,1.5,10,1\n'
                            '2025.01.02,04:00:00,1,2,0.5,1.5,10,1\n', encoding='utf-8')
            digest = study.hashlib.sha256(path.read_bytes()).hexdigest()
            series = study.NativeSeries(path, 'H4', expected_sha256=digest)
            self.assertEqual([], series.asof(series.closes[0] - 1))
            self.assertEqual(1, len(series.asof(series.closes[0])))
            self.assertEqual(2, len(series.asof(series.closes[-1])))
            with self.assertRaises(ValueError):
                study.NativeSeries(path, 'H4', expected_sha256='0' * 64)

    def test_both_net_and_mean_improvement_required_not_just_fewer_losing_models(self):
        def book(n, net):
            return {'scenarios': [{'commission_usd_round_trip_per_lot': 7.,
                                  'models': [{'model': 'engulfing', 'trades': n, 'net_r': net, 'censored': 0}],
                                  'positive_models_n_ge_30': []}]}
        self.assertEqual('NO_CHANGE', study.verdict(book(100, -10), book(30, -5)))
        self.assertEqual('IMPROVED', study.verdict(book(100, -10), book(50, 1)))
        self.assertEqual('WORSE', study.verdict(book(100, -10), book(100, -20)))
        self.assertEqual('NO_CHANGE', study.verdict(book(100, -10), book(0, 0)))
