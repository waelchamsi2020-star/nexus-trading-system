"""Scoped cross-symbol mechanics on synthetic data, never edge evidence."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_long_walkforward import card, causal_cache, fixture_cache

from nexus.regime_router import load_routing_config
from nexus.strategies import REGISTRY
from tools import context_cross_study as cross


def selection_document():
    return {'scenarios': [{'commission_usd_round_trip_per_lot': 7.,
                           'models': [{'model': model, 'trades': 0, 'net_r': 0.}
                                      for model in sorted(REGISTRY)]}]}


class ContextCrossStudy(unittest.TestCase):
    def test_winner_fixed_by_usd7_net_return_and_minimum_30_not_tiny_positive_sample(self):
        document = selection_document()
        rows = document['scenarios'][0]['models']
        rows[0].update(trades=40, net_r=-5.)
        rows[1].update(trades=30, net_r=-2.)
        rows[2].update(trades=2, net_r=100.)
        chosen = cross.choose_model(document)
        self.assertEqual(rows[1]['model'], chosen['model'])
        self.assertEqual(-2., chosen['eurusd_net_r'])
        self.assertTrue(chosen['eurusd_sample_adequate'])
        self.assertEqual('FIXED_USD7_NET_R_AMONG_N_GE_30', chosen['selection_basis'])
        self.assertFalse(chosen['execution_authority'])

    def test_no_adequate_winner_fallback_is_explicitly_descriptive_and_stable(self):
        document = selection_document()
        rows = document['scenarios'][0]['models']
        rows[0].update(trades=20, net_r=-5.)
        rows[1].update(trades=19, net_r=100.)
        chosen = cross.choose_model(document)
        self.assertEqual(rows[0]['model'], chosen['model'])
        self.assertFalse(chosen['eurusd_sample_adequate'])
        self.assertEqual('DESCRIPTIVE_MOST_TRADES_NO_MODEL_REACHED_30', chosen['selection_basis'])
        rows.reverse()
        self.assertEqual(chosen, cross.choose_model(document))

    def test_selection_requires_exact_all_58_model_inventory(self):
        for mutation in ('missing', 'duplicate'):
            document = selection_document()
            rows = document['scenarios'][0]['models']
            if mutation == 'missing':
                rows.pop()
            else:
                rows[-1] = copy.deepcopy(rows[0])
            with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, '58'):
                cross.choose_model(document)

    def test_schema_padding_preserves_only_evaluated_cards_and_records_57_not_evaluated(self):
        cache = fixture_cache(signals=(20,))
        cache['status_counts'] = {'engulfing': {'READY': 1}}
        padded = cross.pad_schema_inventory(cache, 'engulfing')
        self.assertEqual(set(REGISTRY), set(padded['cards']))
        self.assertIs(cache['cards']['engulfing'], padded['cards']['engulfing'])
        self.assertEqual(57, len(padded['provenance']['not_evaluated_model_ids']))
        self.assertEqual(['engulfing'], padded['provenance']['evaluated_model_ids'])
        self.assertTrue(all(not rows for model, rows in padded['cards'].items() if model != 'engulfing'))
        self.assertEqual({'engulfing'}, set(cache['cards']))
        self.assertNotIn('schema_padding_only', cache['provenance'])
        with self.assertRaises(ValueError):
            cross.pad_schema_inventory(padded, 'engulfing')

    def test_selected_training_membership_is_identical_when_other_57_models_are_not_computed(self):
        selected = 'fractal_5_breakout'
        cache = fixture_cache(count=500, signals=())
        for index, bar in enumerate(cache['bars']):
            close = 100. + .5 * index
            bar.update(open=close - .1, close=close, high=close + .2, low=close - .2)
        cache['segment_starts'], cache['atr_values'] = causal_cache.segment_arrays(cache['bars'], 'H1', 'CONTINUOUS')
        cache['provenance']['csv_sha256'] = '2' * 64
        signals = []
        for index in range(60, 291, 10):
            price = cache['bars'][index]['close']
            signal = card(hold=1, stop=price - 1., target=price + 10.)
            signal['entry']['zone'] = [price - 2., price + 2.]
            signals.append({'index': index, 'card': signal})
        cache['cards'] = {selected: signals}
        cache['status_counts'] = {selected: {'READY': len(signals)}}
        scoped = cross.pad_schema_inventory(cache, selected)
        full = copy.deepcopy(scoped)
        full['cards']['ema_cross'] = copy.deepcopy(signals)
        profile = load_routing_config()
        contexts = cross.classify_cache(scoped, profile)
        folds = cross.fit_baselines(scoped, cross.schedule(500, train=300, test=100, step=50, embargo=24))
        scoped_maps = cross.fit_training_maps(scoped, folds, contexts, profile)
        full_maps = cross.fit_training_maps(full, folds, contexts, profile)
        self.assertTrue(folds)
        for fold in folds:
            index = fold['fold_id']
            self.assertEqual(['TREND_UP'], scoped_maps[index]['models'][selected]['regimes'])
            self.assertEqual(full_maps[index]['models'][selected], scoped_maps[index]['models'][selected]
                             | {'source': full_maps[index]['models'][selected]['source']})
            self.assertEqual([], scoped_maps[index]['models']['ema_cross']['regimes'])
            self.assertEqual(['TREND_UP'], full_maps[index]['models']['ema_cross']['regimes'])

    def test_symbol_runner_always_requests_selected_model_only_and_labels_regime_only_scope(self):
        selected = 'engulfing'
        cache = fixture_cache(count=130, signals=())
        cache['status_counts'] = {selected: {}}
        cache['provenance']['csv_sha256'] = '2' * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            metadata = path / 'source.metadata.json'
            metadata.write_text(json.dumps({'point': .01, 'contract_size': 100000., 'profit_currency': 'USD',
                                             'symbol': 'GBPUSD', 'calendar_profile': 'CONTINUOUS'}), encoding='utf-8')
            verified = {'metadata': str(metadata), 'csv_sha256': '2' * 64}
            with patch.object(cross, 'verify_reused_history', return_value=verified), \
                    patch.object(cross, 'build_cache', return_value=cache) as build, \
                    patch.object(cross, 'run_study', wraps=cross.run_study) as replay:
                summary = cross.run_symbol(selected, {'symbol': 'GBPUSD', 'csv': 'SYNTHETIC_TEST_ONLY.csv'}, path)
            self.assertEqual([selected], build.call_args.kwargs['model_ids'])
            self.assertEqual(2, build.call_args.kwargs['workers'])
            self.assertEqual(2, replay.call_count)
            self.assertTrue(all(call.kwargs['model_ids'] == [selected] for call in replay.call_args_list))
            self.assertEqual([selected], summary['evaluated_model_ids'])
            self.assertEqual(57, summary['not_evaluated_model_count'])
            self.assertEqual('REGIME_ONLY_SELECTED_MODEL_CAUSAL_TRAINING_MAP', summary['scope'])
            self.assertEqual(0, summary['orders_sent'])
