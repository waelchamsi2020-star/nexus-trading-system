"""Frozen routing provenance, configurable bounds and fail-closed validation."""
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from nexus.regime_router import (
    load_routing_config,
    routing_fingerprint,
    validate_routing_config,
)
from nexus.strategies import REGISTRY

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / 'src/nexus/config/routing.yaml'
BUILDER_PATH = ROOT / 'tools/build_routing_config.py'
_spec = importlib.util.spec_from_file_location('routing_builder_test_fixture', BUILDER_PATH)
builder = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(builder)

EXPECTED_SOURCE = '1c6c356f19a497a61350c7a7ea41303035e96504299bc36b1d11d2b534beb246'
EXPECTED_NATIVE = '59e9577af8216b1a138911a69fd051288c62c0750abd77cce365d73aea372fa3'
EXPECTED_ROUTES = {
    'band_reentry': ['TREND_UP', 'RANGE'],
    'breakout_retest': ['TREND_UP'],
    'donchian_20': ['RANGE'],
    'inside_bar_break': ['TREND_UP'],
    'pin_rejection': ['RANGE'],
    'regression_reentry': ['RANGE'],
    'support_bounce': ['TREND_DOWN', 'RANGE'],
    'tick_activity_rejection': ['RANGE'],
    'volatility_breakout': ['TREND_UP'],
}


def raw_config():
    return json.loads(CONFIG_PATH.read_text(encoding='utf-8'))


def synthetic_report():
    return {
        'commission_usd_round_trip_per_lot': 7,
        'slippage_points_per_side': 10,
        'data_sha256': '0' * 64,
        'rows': [
            {'model': model, 'regimes': {
                name: {'trades': 0, 'net_r': 0.} for name in ('UP', 'DOWN', 'RANGE', 'UNKNOWN')}}
            for model in sorted(REGISTRY)
        ],
    }


class RoutingConfiguration(unittest.TestCase):
    def test_all_58_preserve_exact_registry_ids_and_prior_source_fingerprints(self):
        config = raw_config()
        self.assertEqual(58, len(config['models']))
        self.assertEqual(set(REGISTRY), set(config['models']))
        self.assertEqual(EXPECTED_SOURCE, config['source']['diagnostic_report_sha256'])
        self.assertEqual(EXPECTED_NATIVE, config['source']['native_csv_sha256'])
        self.assertEqual(10000, config['source']['native_span']['bars'])
        for model, row in config['models'].items():
            with self.subTest(model=model):
                self.assertEqual(EXPECTED_SOURCE, row['source']['diagnostic_report_sha256'])
                self.assertEqual(EXPECTED_NATIVE, row['source']['native_csv_sha256'])
                self.assertEqual({'UP', 'DOWN', 'RANGE', 'UNKNOWN'},
                                 set(row['diagnostic']) - {'selection_reason', 'prior_sample_adequate'})

    def test_frozen_nine_exploratory_routes_and_49_disabled_are_not_relaxed(self):
        config = raw_config()
        active = {key: row['regimes'] for key, row in config['models'].items() if row['regimes']}
        self.assertEqual(EXPECTED_ROUTES, active)
        self.assertEqual(49, sum(not row['regimes'] for row in config['models'].values()))
        self.assertTrue(all(not row['diagnostic']['prior_sample_adequate'] for row in config['models'].values()))
        self.assertEqual('RESEARCH_ONLY', config['mode'])
        self.assertIs(False, config['execution_authority'])
        limitations = ' '.join(config['source']['limitations'])
        self.assertIn('overlaps', limitations)
        self.assertIn('not unseen holdout', limitations)
        self.assertIn('residual non-directional', limitations)

    def test_each_route_matches_positive_net_return_and_five_prior_trades(self):
        config = raw_config()
        for model, row in config['models'].items():
            expected = [target for old, target in builder.REGIME_TRANSLATION.items()
                        if row['diagnostic'][old]['net_r'] > 0 and row['diagnostic'][old]['trades'] >= 5]
            with self.subTest(model=model):
                self.assertEqual(expected, row['regimes'])
                self.assertNotIn('UNKNOWN', row['regimes'])
                self.assertNotIn('UNCERTAIN', row['regimes'])
                self.assertNotIn('ALL', row['regimes'])

    def test_schema_covers_all_models_and_versioned_threshold_bounds(self):
        config = raw_config()
        schema = json.loads(CONFIG_PATH.with_name('routing.schema.json').read_text(encoding='utf-8'))
        self.assertEqual(schema, builder.build_schema(config))
        self.assertEqual(set(REGISTRY), set(schema['properties']['models']['required']))
        self.assertEqual(set(REGISTRY), set(schema['properties']['models']['properties']))
        self.assertEqual(1, schema['properties']['schema_version']['const'])
        self.assertIs(False, schema['properties']['execution_authority']['const'])
        for key, value in config['classifier'].items():
            bounds = schema['properties']['classifier']['properties'][key]
            with self.subTest(classifier_key=key):
                self.assertEqual(value, bounds['default'])
                self.assertLessEqual(bounds['minimum'], value)
                self.assertGreaterEqual(bounds['maximum'], value)

    def test_builder_is_deterministic_and_uses_only_explicit_prior_regime_evidence(self):
        report = synthetic_report()
        rows = report['rows']
        rows[0]['regimes']['UP'] = {'trades': 5, 'net_r': .01}
        rows[1]['regimes']['UP'] = {'trades': 4, 'net_r': 100.}
        rows[2]['regimes']['DOWN'] = {'trades': 30, 'net_r': -1.}
        rows[3]['regimes']['UNKNOWN'] = {'trades': 100, 'net_r': 100.}
        snapshot = copy.deepcopy(report)
        first = builder.build_config(report, '1' * 64)
        shuffled = copy.deepcopy(report)
        shuffled['rows'].reverse()
        shuffled['five_year_test_net_r'] = 1000000
        second = builder.build_config(shuffled, '1' * 64)
        self.assertEqual(first, second)
        self.assertEqual(['TREND_UP'], first['models'][rows[0]['model']]['regimes'])
        self.assertEqual(1, sum(bool(row['regimes']) for row in first['models'].values()))
        self.assertEqual(snapshot, report)

    def test_builder_rejects_changed_costs_missing_models_and_invalid_arithmetic(self):
        for mutation in ('fee', 'slippage', 'missing', 'duplicate', 'count', 'net', 'sha'):
            report = synthetic_report()
            digest = '1' * 64
            if mutation == 'fee':
                report['commission_usd_round_trip_per_lot'] = 0
            elif mutation == 'slippage':
                report['slippage_points_per_side'] = 0
            elif mutation == 'missing':
                report['rows'].pop()
            elif mutation == 'duplicate':
                report['rows'][-1] = copy.deepcopy(report['rows'][0])
            elif mutation == 'count':
                report['rows'][0]['regimes']['UP']['trades'] = True
            elif mutation == 'net':
                report['rows'][0]['regimes']['UP']['net_r'] = float('nan')
            else:
                digest = 'invalid'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                builder.build_config(report, digest)

    def test_loader_rejects_unknown_models_regimes_versions_and_bad_provenance(self):
        model = next(iter(REGISTRY))
        for mutation in ('missing', 'extra', 'unknown_regime', 'uncertain', 'duplicate_regime',
                         'all_mixed', 'version', 'source', 'authority', 'mode', 'schema'):
            config = raw_config()
            if mutation == 'missing':
                config['models'].pop(model)
            elif mutation == 'extra':
                config['models']['not_model_59'] = copy.deepcopy(config['models'][model])
            elif mutation == 'unknown_regime':
                config['models'][model]['regimes'] = ['UP']
            elif mutation == 'uncertain':
                config['models'][model]['regimes'] = ['UNCERTAIN']
            elif mutation == 'duplicate_regime':
                config['models'][model]['regimes'] = ['RANGE', 'RANGE']
            elif mutation == 'all_mixed':
                config['models'][model]['regimes'] = ['ALL', 'RANGE']
            elif mutation == 'version':
                config['version'] = 'latest'
            elif mutation == 'source':
                config['source']['diagnostic_report_sha256'] = 'unknown'
            elif mutation == 'authority':
                config['execution_authority'] = True
            elif mutation == 'mode':
                config['mode'] = 'LIVE'
            else:
                config['schema_version'] = True
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validate_routing_config(config)

    def test_classifier_rejects_out_of_bounds_or_inconsistent_thresholds(self):
        for key, value in (('min_bars', 0), ('ema_fast', True), ('ema_slow', 1000000),
                           ('slope_bars', 0), ('atr_period', 1), ('efficiency_bars', 0),
                           ('trend_min_ema_gap_atr', float('nan')), ('trend_min_slope_atr', -1.),
                           ('trend_min_efficiency', 1.1), ('range_max_efficiency', -.1)):
            config = raw_config()
            config['classifier'][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                validate_routing_config(config)
        for mutation in ('ema_order', 'history', 'efficiency_order'):
            config = raw_config()
            if mutation == 'ema_order':
                config['classifier']['ema_fast'] = config['classifier']['ema_slow']
            elif mutation == 'history':
                config['classifier']['ema_slow'] = config['classifier']['min_bars'] + 1
            else:
                config['classifier']['range_max_efficiency'] = config['classifier']['trend_min_efficiency'] + .1
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validate_routing_config(config)

    def test_loader_rejects_duplicate_keys_and_fingerprint_tracks_threshold_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'routing.yaml'
            path.write_text('{"schema_version":1,"schema_version":1}', encoding='utf-8')
            with self.assertRaises(ValueError):
                load_routing_config(path)
        config = raw_config()
        snapshot = copy.deepcopy(config)
        original = routing_fingerprint(config)
        validated = validate_routing_config(config)
        self.assertEqual(snapshot, config)
        self.assertEqual(original, routing_fingerprint(validated))
        reordered = {key: config[key] for key in reversed(config)}
        self.assertEqual(original, routing_fingerprint(reordered))
        config['classifier']['trend_min_ema_gap_atr'] = .6
        self.assertNotEqual(original, routing_fingerprint(config))
