"""Freeze an exploratory route map from a fingerprinted, older diagnostic.

This builder never reads the five-year test outputs. The positive-return rule
is an attribution heuristic, not a calibrated probability or a proven edge.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from nexus.strategies import REGISTRY

MINIMUM_PRIOR_TRADES = 5
CLASSIFIER = {
    'min_bars': 60, 'ema_fast': 20, 'ema_slow': 50, 'slope_bars': 5,
    'atr_period': 14, 'efficiency_bars': 20, 'trend_min_ema_gap_atr': .5,
    'trend_min_slope_atr': .25, 'trend_min_efficiency': .45, 'range_max_ema_gap_atr': .5,
    'range_max_abs_slope_atr': .25, 'range_max_efficiency': .25,
}
REGIME_TRANSLATION = {'UP': 'TREND_UP', 'DOWN': 'TREND_DOWN', 'RANGE': 'RANGE'}


def build_config(report: dict, report_sha256: str) -> dict:
    if (report.get('commission_usd_round_trip_per_lot') != 7 or
            report.get('slippage_points_per_side') != 10):
        raise ValueError('Frozen source must retain USD7 round-trip and ten-point slippage')
    rows = report['rows']
    if len(rows) != len(REGISTRY) or {row['model'] for row in rows} != set(REGISTRY):
        raise ValueError('Exactly one source diagnostic for every registered model required')
    for digest in (report_sha256, report['data_sha256']):
        if len(digest) != 64 or any(character not in '0123456789abcdef' for character in digest):
            raise ValueError('Canonical SHA256 source provenance required')
    models = {}
    for row in sorted(rows, key=lambda item: item['model']):
        evidence = {}
        for regime in ('UP', 'DOWN', 'RANGE', 'UNKNOWN'):
            group = row['regimes'][regime]
            count, net_r = group['trades'], group['net_r']
            if (type(count) is not int or count < 0 or isinstance(net_r, bool) or
                    not isinstance(net_r, (int, float)) or not math.isfinite(net_r)):
                raise ValueError('Finite return and nonnegative integer count required')
            evidence[regime] = {'trades': count, 'net_r': net_r}
        allowed = [target for old, target in REGIME_TRANSLATION.items()
                   if evidence[old]['trades'] >= MINIMUM_PRIOR_TRADES and evidence[old]['net_r'] > 0]
        models[row['model']] = {
            'regimes': allowed,
            'source': {'diagnostic_report_sha256': report_sha256,
                       'native_csv_sha256': report['data_sha256']},
            'diagnostic': {
                **evidence,
                'selection_reason': ('EXPLORATORY_POSITIVE_NET_R_AND_N_GE_5' if allowed else
                                     'DISABLED_NO_POSITIVE_NET_R_REGIME_WITH_N_GE_5'),
                'prior_sample_adequate': bool(allowed) and all(
                    evidence[old]['trades'] >= 30 for old, target in REGIME_TRANSLATION.items()
                    if target in allowed),
            },
        }
    return {
        'schema_version': 1, 'version': '1.0.0', 'mode': 'RESEARCH_ONLY',
        'execution_authority': False, 'classifier': dict(CLASSIFIER),
        'source': {
            'diagnostic_report_sha256': report_sha256,
            'native_csv_sha256': report['data_sha256'],
            'report_path': 'reports/regime-diagnostics.json',
            'selection_rule': 'Prior USD7 net_r > 0 and prior regime trades >= 5; never UNKNOWN.',
            'minimum_prior_trades': MINIMUM_PRIOR_TRADES,
            'minimum_evidence_trades': 30,
            'native_span': report.get('native_span', {}),
            'archived_trade_span': report.get('archived_trade_span', {}),
            'limitations': [
                'Frozen from the older retrospective diagnostic only; no five-year outcome is read by this builder.',
                'The older diagnostic overlaps the five-year study; this experiment is post-selection, not unseen holdout.',
                'Fewer than 30 prior trades in every enabled regime; all enabled routes remain exploratory.',
                'Older diagnostic RANGE is residual non-directional, not the new strict efficiency-based RANGE.',
                'No route is inferred for absent or nonpositive evidence; an empty list disables the model.',
                'ALL means all known regimes only; UNCERTAIN is always blocked. No side override is introduced.',
                'No live execution authority, model parameters, prices, costs or risk limits are changed.',
            ],
        },
        'models': models,
    }


def build_schema(config: dict) -> dict:
    bounds = {
        'min_bars': (60, 2000), 'ema_fast': (2, 200), 'ema_slow': (3, 500),
        'slope_bars': (1, 100), 'atr_period': (2, 200), 'efficiency_bars': (2, 200),
        'trend_min_ema_gap_atr': (0, 20), 'trend_min_slope_atr': (0, 20),
        'trend_min_efficiency': (0, 1), 'range_max_ema_gap_atr': (0, 20),
        'range_max_abs_slope_atr': (0, 20), 'range_max_efficiency': (0, 1),
    }
    classifier = {
        key: {'type': 'integer' if type(value) is int else 'number',
              'minimum': bounds[key][0], 'maximum': bounds[key][1], 'default': value}
        for key, value in CLASSIFIER.items()
    }
    for key in ('trend_min_ema_gap_atr', 'trend_min_slope_atr'):
        classifier[key]['exclusiveMinimum'] = 0
    digest = {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}
    source = {'type': 'object', 'additionalProperties': False,
              'required': ['diagnostic_report_sha256', 'native_csv_sha256'],
              'properties': {'diagnostic_report_sha256': digest, 'native_csv_sha256': digest}}
    group = {'type': 'object', 'additionalProperties': False, 'required': ['trades', 'net_r'],
             'properties': {'trades': {'type': 'integer', 'minimum': 0}, 'net_r': {'type': 'number'}}}
    diagnostic = {
        'type': 'object', 'additionalProperties': False,
        'required': ['UP', 'DOWN', 'RANGE', 'UNKNOWN', 'selection_reason', 'prior_sample_adequate'],
        'properties': {**{key: group for key in ('UP', 'DOWN', 'RANGE', 'UNKNOWN')},
                       'selection_reason': {'type': 'string'},
                       'prior_sample_adequate': {'type': 'boolean'}},
    }
    model = {
        'type': 'object', 'additionalProperties': False,
        'required': ['regimes', 'source', 'diagnostic'],
        'properties': {
            'regimes': {'type': 'array', 'maxItems': 3, 'uniqueItems': True,
                        'items': {'enum': ['TREND_UP', 'TREND_DOWN', 'RANGE', 'ALL']},
                        'oneOf': [
                            {'maxItems': 0},
                            {'minItems': 1, 'items': {'enum': ['TREND_UP', 'TREND_DOWN', 'RANGE']}},
                            {'const': ['ALL']},
                        ]},
            'source': source, 'diagnostic': diagnostic,
        },
    }
    return {
        '$schema': 'https://json-schema.org/draft/2020-12/schema',
        'title': 'Versioned research-only regime routing for 58 unchanged models',
        '$defs': {'model': model},
        'type': 'object', 'additionalProperties': False,
        'required': list(config),
        'properties': {
            'schema_version': {'const': 1},
            'version': {'type': 'string', 'pattern': '^[0-9]+\\.[0-9]+\\.[0-9]+$'},
            'mode': {'const': 'RESEARCH_ONLY'}, 'execution_authority': {'const': False},
            'classifier': {'type': 'object', 'additionalProperties': False,
                           'required': list(CLASSIFIER), 'properties': classifier},
            'source': {'type': 'object', 'required': ['diagnostic_report_sha256', 'native_csv_sha256',
                                                    'selection_rule', 'minimum_prior_trades', 'limitations'],
                       'properties': {'diagnostic_report_sha256': digest, 'native_csv_sha256': digest,
                                      'minimum_prior_trades': {'const': 5},
                                      'limitations': {'type': 'array', 'minItems': 7}}},
            'models': {'type': 'object', 'additionalProperties': False, 'required': sorted(REGISTRY),
                       'properties': {key: {'$ref': '#/$defs/model'} for key in sorted(REGISTRY)}},
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'reports/regime-diagnostics.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'src/nexus/config/routing.yaml')
    args = parser.parse_args()
    raw = args.input.read_bytes()
    config = build_config(json.loads(raw), hashlib.sha256(raw).hexdigest())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(config, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    args.output.with_name('routing.schema.json').write_text(
        json.dumps(build_schema(config), indent=2) + '\n', encoding='utf-8')
    active = {key: row['regimes'] for key, row in config['models'].items() if row['regimes']}
    print(json.dumps({'models': len(config['models']), 'active': len(active),
                      'disabled': len(config['models']) - len(active), 'routes': active,
                      'source': config['source']['diagnostic_report_sha256'],
                      'qualified': False, 'execution_authority': False}, indent=2))


if __name__ == '__main__':
    main()
