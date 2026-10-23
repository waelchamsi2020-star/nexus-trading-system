"""Preregistered context veto ablations over unchanged, archived model cards.

No model is trained here. Only a per-fold model/regime permission table is fitted
on training outcomes, with fixed classifier/selection thresholds and costs.
Every primary decision precedes its order; no routed book is a filtered list of
baseline trades. Native cross/HTF observations are joined by their close times.
"""
from __future__ import annotations

import argparse
import bisect
import copy
import csv
import gzip
import hashlib
import json
import math
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))

from context_input_cache import load_context_cache
from long_walkforward import (
    fit_baselines,
    price_trades,
    replay_book,
    run_study,
    schedule,
)

from nexus.cross_asset_filter import evaluate_cross_assets
from nexus.regime_router import (
    classify_regime,
    load_routing_config,
    route_classification,
    validate_routing_config,
)
from nexus.session_filter import evaluate_session, load_context_config
from nexus.strategies import REGISTRY, validate_bars
from nexus.timeframe_filter import evaluate_timeframes
from nexus.timeframes import bar_close_time
from nexus.walkforward import LookaheadBiasError


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.pending')
    temporary.write_bytes(encoded(value))
    temporary.replace(path)


def classify_cache(cache, profile):
    """Current H1 context uses exactly the original causal feature segments."""
    needed = sorted({row['index'] for rows in cache['cards'].values() for row in rows})
    contexts = {}
    for number, index in enumerate(needed):
        start = max(cache['segment_starts'][index], index - 299)
        stamp = bar_close_time(cache['bars'][index]['time'], cache['timeframe'])
        contexts[index] = classify_regime(cache['bars'][start:index + 1], cache['timeframe'],
                                           stamp, config=profile)
        if number % 5000 == 0:
            print(f'CONTEXT_CLASSIFIED {cache["symbol"]} {number}/{len(needed)}', flush=True)
    return contexts


def _summaries(cache, fold, contexts):
    """Closed training trades only; explicit bounds make future use an error."""
    observations = {model: {regime: {'trades': 0, 'net_r': 0.}
                            for regime in ('UP', 'DOWN', 'RANGE', 'UNKNOWN')}
                    for model in sorted(REGISTRY)}
    end_time = bar_close_time(cache['bars'][fold['train_end'] - 1]['time'], cache['timeframe'])
    label = {'TREND_UP': 'UP', 'TREND_DOWN': 'DOWN', 'RANGE': 'RANGE', 'UNCERTAIN': 'UNKNOWN'}
    censored = 0
    # Re-label training bounds as the replay interval. No OOS card can be read.
    training_fold = {**fold, 'test_start': fold['train_start'], 'test_end': fold['train_end']}
    for model in sorted(REGISTRY):
        book = replay_book(cache, model, [training_fold], start=fold['train_start'],
                           end=fold['train_end'], fixed_fold=0)
        censored += len(book['censored'])
        for trade in price_trades(book['trades'], 7., cache['specification']):
            if (trade['signal_index'] < fold['train_start'] or
                    trade['exit_index'] >= fold['train_end'] or trade['exit_time'] > end_time):
                raise LookaheadBiasError('Training routing map consumed an outcome after train_end')
            context = contexts[trade['signal_index']]
            if context['decision_time'] > trade['signal_time']:
                raise LookaheadBiasError('Training context observes a later candle')
            row = observations[model][label[context['regime']]]
            row['trades'] += 1
            row['net_r'] += trade['r']
    return observations, censored, end_time


def fit_training_maps(cache, folds, contexts, profile):
    """Fit only routing membership, not classifier/model or risk parameters."""
    result = {}
    for fold in folds:
        observed, censored, end_time = _summaries(cache, fold, contexts)
        digest = hashlib.sha256(encoded(observed)).hexdigest()
        selected = copy.deepcopy(profile)
        selected['version'] = '1.1.0'
        selected['source'].update({
            'diagnostic_report_sha256': digest,
            'native_csv_sha256': cache['provenance']['csv_sha256'],
            'selection_rule': 'Training-only USD7 closed netR>0 and n>=5 by fixed closed-candle regime',
            'fold_id': fold['fold_id'], 'train_start': fold['train_start'],
            'train_end_exclusive': fold['train_end'], 'last_outcome_time': end_time,
            'censored_training_exposures': censored,
        })
        selected['source']['limitations'] += [
            'Five thousand past observed candles only; classifier fixed; training choices are not test results.',
            'Censored training exposures are unknown, not zero; membership is exploratory and not qualified.',
        ]
        for model in sorted(REGISTRY):
            measurements = observed[model]
            regimes = [new for old, new in (('UP', 'TREND_UP'), ('DOWN', 'TREND_DOWN'), ('RANGE', 'RANGE'))
                       if measurements[old]['trades'] >= 5 and measurements[old]['net_r'] > 0]
            selected['models'][model] = {
                'regimes': regimes,
                'source': {'diagnostic_report_sha256': digest,
                           'native_csv_sha256': cache['provenance']['csv_sha256']},
                'diagnostic': {**measurements,
                               'selection_reason': 'Fixed training-only n>=5/netR>0 rule; empty means disabled.',
                               'prior_sample_adequate': all(measurements[old]['trades'] >= 30
                                                            for old in ('UP', 'DOWN', 'RANGE'))},
            }
        result[fold['fold_id']] = validate_routing_config(selected)
        print(f'ROUTES_FIT {cache["symbol"]} fold={fold["fold_id"]} '
              f'enabled={sum(bool(m["regimes"]) for m in selected["models"].values())}', flush=True)
    return result


class NativeSeries:
    """An immutable native observation stream, joined by known candle close.

    Higher-frame indicators use observed completed bars, not a synthetic regular
    clock. Calendar quality remains a reported source limitation. This class
    does not apply the M5/H1-only calendar algorithm to H4 or D1.
    """
    def __init__(self, path, timeframe, *, expected_sha256):
        self.timeframe = timeframe
        self.path = Path(path)
        blob = self.path.read_bytes()
        if hashlib.sha256(blob).hexdigest() != expected_sha256:
            raise ValueError('Native context SHA256 mismatch: ' + str(path))
        text = blob.decode('utf-8-sig')
        reader = csv.DictReader(text.splitlines(), dialect=csv.Sniffer().sniff(text[:4096], delimiters=',\t;'))
        self.bars = []
        for row in reader:
            stamp = datetime.strptime(row['<DATE>'] + ' ' + row['<TIME>'], '%Y.%m.%d %H:%M:%S').replace(tzinfo=UTC)
            self.bars.append({'time': int(stamp.timestamp()),
                              **{key: float(row['<' + key.upper() + '>'])
                                 for key in ('open', 'high', 'low', 'close')},
                              'tick_volume': int(row['<TICKVOL>']), 'spread': int(row['<SPREAD>']),
                              'real_volume': int(row.get('<VOL>') or 0)})
        self.closes = [bar_close_time(row['time'], timeframe) for row in self.bars]
        validate_bars(self.bars, timeframe, self.closes[-1])

    def asof(self, stamp, count=300):
        end = bisect.bisect_right(self.closes, stamp)
        rows = self.bars[0 if count is None else max(0, end - count):end]
        if rows and bar_close_time(rows[-1]['time'], self.timeframe) > stamp:
            raise LookaheadBiasError('As-of join exposed unfinished native context')
        return rows


class ContextGate:
    """Trusted locally constructed classifications; no external cached input.

    Per-fold/model/regime decisions are evaluated by the core router once and
    memoized. Each actual signal retains its own time and exact causal metrics.
    The production executor independently obtains and validates fresh candles.
    """
    def __init__(self, cache, contexts, maps, *, selection_only=False,
                 native=None, context_config=None):
        self.cache, self.contexts = cache, contexts
        self.maps = {key: validate_routing_config(value) for key, value in maps.items()}
        self.selection_only = selection_only
        self.native = native
        self.context_config = context_config
        self.templates, self.layer_cache = {}, {}

    def __call__(self, model, index, card, fold):
        profile = self.maps[fold['fold_id']]
        if ('last_outcome_time' in profile['source'] and
                profile['source']['last_outcome_time'] >=
                bar_close_time(self.cache['bars'][index]['time'], self.cache['timeframe'])):
            raise LookaheadBiasError('Routing map is not strictly prior to its test signal')
        classification = self.contexts[index]
        if classification['decision_time'] != bar_close_time(
                self.cache['bars'][index]['time'], self.cache['timeframe']):
            raise LookaheadBiasError('Context cache is not aligned with its actual signal')
        if self.selection_only:
            allowed = bool(profile['models'][model]['regimes'])
            decision = {'allowed': allowed, 'regime': classification['regime'],
                        'reasons': ['SELECTION_ONLY_ENABLED_MODEL' if allowed else 'TRAINING_MODEL_DISABLED'],
                        'rule_version': profile['version'],
                        'routing_fingerprint': profile['routing_fingerprint'],
                        'classifier_fingerprint': profile['classifier_fingerprint']}
        else:
            key = fold['fold_id'], model, classification['regime'], tuple(classification['reasons'])
            if key not in self.templates:
                self.templates[key] = route_classification(model, classification, config=profile)
            template = self.templates[key]
            decision = {key: template[key] for key in ('allowed', 'regime', 'reasons', 'rule_version',
                         'routing_fingerprint', 'classifier_fingerprint')}
        decision = {**decision, 'decision_time': classification['decision_time'],
                    'last_closed_time': classification['last_closed_time'],
                    'execution_authority': False}
        if not decision['allowed'] or self.native is None:
            return decision
        stamp = classification['decision_time']
        layer_key = stamp, card['direction']
        if layer_key not in self.layer_cache:
            htf = evaluate_timeframes(card['direction'], as_of=stamp,
                                     h4_bars=self.native['H4'].asof(stamp),
                                     d1_bars=self.native['D1'].asof(stamp),
                                     config=self.context_config, routing_config=profile)
            legs = align_native_legs({symbol: series.asof(stamp, count=None) for symbol, series in self.native.items()
                                      if symbol not in ('H4', 'D1')}, stamp)
            cross = evaluate_cross_assets(self.cache['symbol'], card['direction'], legs, stamp,
                                          config=self.context_config, routing_config=profile)
            self.layer_cache[layer_key] = {'htf': htf, 'cross': cross}
        layers = self.layer_cache[layer_key]
        session = evaluate_session(model, stamp, config=self.context_config)
        failures = [name for name, result in {**layers, 'session': session}.items() if not result['allowed']]
        return {**decision, 'allowed': not failures, 'failed_layers': failures,
                'reasons': [reason for name in failures for reason in
                            ({**layers, 'session': session})[name]['reasons']] or ['FULL_CONTEXT_APPROVED']}


def align_native_legs(histories, as_of):
    """Intersect past actual H1 observations, without filling DXY session gaps.

    The cross filter still requires60 matching observed bars and a current last
    close. This makes compared EMA histories synchronous despite native DXY's
    shorter daily trading session; it does not manufacture missing observations.
    A future bar passed to this adapter is rejected, rather than silently dropped.
    """
    if not histories:
        return {}
    for rows in histories.values():
        if any(bar_close_time(row['time'], 'H1') > as_of for row in rows):
            raise LookaheadBiasError('Cross-asset native alignment received a future candle')
    timestamps = [{row['time'] for row in rows} for rows in histories.values()]
    common = set.intersection(*timestamps)
    return {symbol: [row for row in rows if row['time'] in common][-300:]
            for symbol, rows in histories.items()}


class AuditWriter:
    def __init__(self, path, stream):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = stream
        self.counts = Counter()

    def __call__(self, event):
        self.counts[(event['book'], event['routing']['reasons'][-1])] += 1
        self.stream.write(json.dumps(event, separators=(',', ':'), allow_nan=False) + '\n')

    def summary(self):
        return {'path': str(self.path), 'sha256': hashlib.sha256(self.path.read_bytes()).hexdigest(),
                'counts': [{'book': key[0], 'reason': key[1], 'count': count}
                           for key, count in sorted(self.counts.items())]}


def compact_study(study):
    """Do not lose primary records; omit duplicated base books from public tables."""
    return {key: value for key, value in study.items() if key != 'primary_base_books'}


def compare_rows(old, new, fee):
    previous = next(row for row in old['scenarios'] if row['commission_usd_round_trip_per_lot'] == fee)
    current = next(row for row in new['scenarios'] if row['commission_usd_round_trip_per_lot'] == fee)
    lookup = {row['model']: row for row in previous['models']}
    return [{'model': row['model'],
             'old_trades': lookup[row['model']]['trades'], 'new_trades': row['trades'],
             'old_net_r': lookup[row['model']]['net_r'], 'new_net_r': row['net_r'],
             'old_sharpe': lookup[row['model']]['sharpe'], 'new_sharpe': row['sharpe'],
             'old_censored': lookup[row['model']]['censored'], 'new_censored': row['censored']}
            for row in current['models']]


def totals(study, fee=7.):
    scenario = next(row for row in study['scenarios'] if row['commission_usd_round_trip_per_lot'] == fee)
    trades = sum(row['trades'] for row in scenario['models'])
    net = math.fsum(row['net_r'] for row in scenario['models'])
    return {'model_trade_count': trades, 'sum_model_r_not_portfolio': net,
            'mean_model_trade_r': net / trades if trades else None,
            'raw_positive_models': sum(row['trades'] > 0 and row['net_r'] > 0 for row in scenario['models']),
            'positive_models_n_ge_30': scenario['positive_models_n_ge_30'],
            'unknown_exposures': sum(row['censored'] for row in scenario['models'])}


def verdict(control, routed):
    before, after = totals(control), totals(routed)
    adequate = after['model_trade_count'] >= 30 and before['model_trade_count'] >= 30
    if adequate:
        net_better = after['sum_model_r_not_portfolio'] > before['sum_model_r_not_portfolio']
        mean_better = after['mean_model_trade_r'] > before['mean_model_trade_r']
        if net_better and mean_better:
            return 'IMPROVED'
        if not net_better and not mean_better and (
                after['sum_model_r_not_portfolio'] < before['sum_model_r_not_portfolio'] and
                after['mean_model_trade_r'] < before['mean_model_trade_r']):
            return 'WORSE'
    return 'NO_CHANGE'


def native_inputs(manifest):
    rows = manifest['exports'] + manifest['reused_cross_symbol_history']
    native = {}
    for row in rows:
        key = row['timeframe'] if row['timeframe'] in ('H4', 'D1') else row['symbol']
        native[key] = NativeSeries(row['csv'], row['timeframe'], expected_sha256=row['csv_sha256'])
    return native


def run_pipeline(cache, baseline, profile, output, *, native=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    contexts = classify_cache(cache, profile)
    write_json(output / 'closed-contexts.json', contexts)
    folds = fit_baselines(cache, schedule(len(cache['bars']), train=5000, test=1000, step=500, embargo=24))
    fitted = fit_training_maps(cache, folds, contexts, profile)
    write_json(output / 'training-maps.json', fitted)
    # Prove that adding training-prefix cards cannot alter the baseline OOS book.
    studies = {'baseline': run_study(cache, train=5000, test=1000, step=500, embargo=24)}
    for fee in (0., 3., 7.):
        if any(row['old_trades'] != row['new_trades'] or
               any(row['old_' + field] != row['new_' + field] for field in ('net_r', 'sharpe', 'censored'))
               for row in compare_rows(baseline, studies['baseline'], fee)):
            raise ValueError('Ungated replay no longer exactly reproduces the archived baseline')
    write_json(output / 'baseline-replay-proof.json', {'exact_all_58_all_3_fees': True,
               'comparison_fields': ['trades', 'net_r', 'sharpe', 'censored'], 'orders_sent': 0})
    variants = [('selection_only', fitted, True, None),
                ('causal_regime', fitted, False, None),
                ('frozen_selection_only', {fold['fold_id']: profile for fold in folds}, True, None),
                ('frozen_regime', {fold['fold_id']: profile for fold in folds}, False, None)]
    if native is not None:
        variants.append(('full_stage1', fitted, False, native))
    audits = {}
    for name, maps, selection_only, joined in variants:
        gate = ContextGate(cache, contexts, maps, selection_only=selection_only,
                           native=joined, context_config=load_context_config() if joined else None)
        audit_path = output / (name + '-rejections.jsonl.gz')
        with gzip.open(audit_path, 'wt', encoding='utf-8') as stream:
            audit = AuditWriter(audit_path, stream)
            studies[name] = run_study(cache, train=5000, test=1000, step=500, embargo=24,
                                     signal_gate=gate, gate_audit=audit)
        audits[name] = audit.summary()
        write_json(output / (name + '.json'), compact_study(studies[name]))
    write_json(output / 'baseline.json', compact_study(studies['baseline']))
    comparisons = {name: {str(int(fee)): compare_rows(studies['baseline'], study, fee)
                          for fee in (0., 3., 7.)} for name, study in studies.items() if name != 'baseline'}
    summary = {'symbol': cache['symbol'], 'models': len(REGISTRY), 'bars': len(cache['bars']),
               'folds': len(folds), 'totals_usd7': {name: totals(study) for name, study in studies.items()},
               'causal_regime_vs_selection_only': verdict(studies['selection_only'], studies['causal_regime']),
               'full_stage1_vs_selection_only': verdict(studies['selection_only'], studies['full_stage1'])
               if 'full_stage1' in studies else 'NOT_RUN',
               'comparisons': comparisons, 'audits': audits,
               'classification_counts': dict(Counter(c['regime'] for c in contexts.values())),
               'qualified': False, 'orders_sent': 0, 'execution_authority': False,
               'selection_warning': 'Frozen diagnostic overlaps archive. Only rolling training maps are causal selection.',
               'gap_warning': 'Censored positions have unknown R; sum R across model books is not a portfolio.',
               'source_proof': cache['provenance']['card_archive_proof']}
    write_json(output / 'summary.json', summary)
    print(json.dumps({key: summary[key] for key in ('symbol', 'models', 'bars', 'folds', 'totals_usd7',
                     'causal_regime_vs_selection_only', 'full_stage1_vs_selection_only', 'orders_sent')}, indent=2))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study', type=Path, required=True)
    parser.add_argument('--csv', type=Path, required=True)
    parser.add_argument('--metadata', type=Path, required=True)
    parser.add_argument('--history-manifest', type=Path)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--output', type=Path, default=ROOT / 'reports/context-layer/EURUSD')
    args = parser.parse_args()
    cache = load_context_cache(args.study, args.csv, args.metadata, workers=args.workers)
    native = native_inputs(json.loads(args.history_manifest.read_bytes())) if args.history_manifest else None
    run_pipeline(cache, json.loads(args.study.read_bytes()), load_routing_config(), args.output, native=native)


if __name__ == '__main__':
    main()
