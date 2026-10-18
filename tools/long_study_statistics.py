"""Bounded-memory uncertainty diagnostics for a unique fee-seven OOS ledger.

All registry models remain in the multiplicity family, including no-trade
models. Ranking and inference never choose the best commission scenario.
Historical post-selection diagnostics never grant execution qualification.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from nexus.strategies import REGISTRY


def _controls(iterations, seed, batch_size):
    if type(iterations) is not int or not 100 <= iterations <= 1_000_000:
        raise ValueError('iterations must be an integer in [100,1000000]')
    if type(seed) is not int or not 0 <= seed < 2**64:
        raise ValueError('seed must be a nonnegative unsigned 64-bit integer')
    if type(batch_size) is not int or not 1 <= batch_size <= 10000:
        raise ValueError('batch_size must be an integer in [1,10000]')


def _finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('Finite numeric ' + label + ' required')
    return float(value)


def stable_seed(model, seed=20261018, purpose='iid'):
    raw = hashlib.sha256((str(model) + ':' + purpose).encode()).digest()
    return (seed ^ int.from_bytes(raw[:8], 'big')) % 2**64


def _resample_summary(values, sampled_means, *, iterations, seed, method):
    observed = float(values.mean())
    centered_null = sampled_means - observed
    p = (int(np.count_nonzero(np.abs(centered_null) >= abs(observed))) + 1) / (iterations + 1)
    ci = np.quantile(sampled_means, [.025, .975])
    return {'n': len(values), 'iterations': iterations, 'seed': seed, 'method': method,
            'status': 'CONDITIONAL_RESAMPLING_APPROXIMATION', 'mean_r': observed,
            'net_r': float(values.sum()), 'bootstrap_mean_r': float(sampled_means.mean()),
            'mean_ci95': ci.tolist(), 'total_ci95': (ci * len(values)).tolist(),
            'p_two_sided_null_centered': p,
            'verdict': 'SIGNIFICANT_AT_95' if observed > 0 and ci[0] > 0 and p <= .05 else 'NOT_SIGNIFICANT'}


def bootstrap_iid(values, *, iterations=10000, seed=20261018, batch_size=256):
    """Exactly n draws per resample; null centered, +1 Monte Carlo correction.

    Maximum index matrix is bounded to approximately one million elements;
    keeping all ten thousand means is cheap. RNG draws do not depend on batch.
    """
    _controls(iterations, seed, batch_size)
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or not np.isfinite(values).all() or len(values) > 1_000_000:
        raise ValueError('Finite one-dimensional returns of length <=1000000 required')
    n = len(values)
    if n < 2 or np.ptp(values) == 0:
        return {'n': n, 'iterations': iterations, 'seed': seed, 'method': 'IID n-of-n percentile bootstrap',
                'status': 'INSUFFICIENT_VARIATION', 'mean_r': float(values.mean()) if n else None,
                'net_r': float(values.sum()), 'bootstrap_mean_r': None,
                'mean_ci95': None, 'total_ci95': None, 'p_two_sided_null_centered': 1.,
                'verdict': 'NOT_SIGNIFICANT'}
    rng = np.random.default_rng(seed)
    sampled = np.empty(iterations)
    chunk = min(batch_size, max(1, 1_000_000 // n))
    for offset in range(0, iterations, chunk):
        count = min(chunk, iterations - offset)
        sampled[offset:offset + count] = values[rng.integers(0, n, size=(count, n))].mean(axis=1)
    return _resample_summary(values, sampled, iterations=iterations, seed=seed,
                             method='IID n-of-n percentile bootstrap; centered two-sided null; +1 correction')


def adjusted_pvalues(values):
    ps = np.asarray(values, dtype=float)
    if ps.ndim != 1 or not len(ps) or not np.isfinite(ps).all() or np.any((ps < 0) | (ps > 1)):
        raise ValueError('A nonempty finite p-value family in [0,1] required')
    count = len(ps)
    order = np.argsort(ps, kind='stable')
    ranked = ps[order] * count / np.arange(1, count + 1)
    corrected = np.minimum.accumulate(ranked[::-1])[::-1]
    bh = np.empty_like(ps)
    bh[order] = np.minimum(corrected, 1.)
    return np.minimum(ps * count, 1.).tolist(), bh.tolist()


def trade_metrics(trades):
    ordered = sorted(trades, key=lambda t: (t['exit_time'], t['entry_time'], t.get('symbol', '')))
    values = [t['r'] for t in ordered]
    net = math.fsum(values)
    mean = net / len(values) if values else None
    variance = math.fsum((v - mean)**2 for v in values) / (len(values) - 1) if len(values) > 1 else None
    equity = peak = drawdown = 0.
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return {'trades': len(values), 'net_r': net, 'mean_r': mean,
            'win_rate': sum(v > 0 for v in values) / len(values) if values else None,
            'trade_sharpe_nonannualized': mean / math.sqrt(variance) if variance and variance > 0 else None,
            'max_drawdown_r': drawdown}


def validate_unique_trades(model, trades):
    if not isinstance(trades, list):
        raise TypeError('trades must be a list: ' + model)
    result, identities, groups = [], set(), defaultdict(list)
    for raw in trades:
        if not isinstance(raw, dict):
            raise TypeError('Trade must be an object: ' + model)
        trade = dict(raw)
        for field in ('r', 'entry_time', 'exit_time'):
            trade[field] = _finite(trade.get(field), field)
        if trade['entry_time'] < 0 or trade['exit_time'] < trade['entry_time']:
            raise ValueError('Invalid chronological trade interval: ' + model)
        if raw.get('model', raw.get('strategy_id', model)) != model:
            raise ValueError('Trade/model ownership mismatch')
        for field in ('symbol', 'timeframe', 'side'):
            if field in trade and not isinstance(trade[field], str):
                raise ValueError('String trade ' + field + ' required')
        identity = (trade.get('symbol', ''), trade.get('timeframe', ''), trade['entry_time'], trade['exit_time'])
        if identity in identities:
            raise ValueError('Duplicate OOS trade in ' + model)
        identities.add(identity)
        groups[(trade.get('symbol', ''), trade.get('timeframe', ''))].append(trade)
        result.append(trade)
    for group in groups.values():
        previous = None
        for trade in sorted(group, key=lambda t: (t['entry_time'], t['exit_time'])):
            if previous is not None and trade['entry_time'] < previous['exit_time']:
                raise ValueError('Overlapping OOS trades in model/instrument/frame: ' + model)
            previous = trade
    return sorted(result, key=lambda t: (t['entry_time'], t.get('symbol', ''), t.get('timeframe', '')))


def cluster_sensitivity(trades, *, iterations=10000, seed=20261019, batch_size=256):
    """Resample whole folds, or UTC calendar months when fold_id is absent.

    Variable-size clusters use a ratio estimate: sum R/sum trades. Total CI
    scales that mean by original n, not a claim of a fixed time horizon.
    """
    _controls(iterations, seed, batch_size)
    groups = defaultdict(list)
    for trade in trades:
        key = ('fold:' + json.dumps(trade['fold_id'], sort_keys=True, allow_nan=False)) if 'fold_id' in trade else (
            'month:' + datetime.fromtimestamp(trade['entry_time'], UTC).strftime('%Y-%m'))
        groups[key].append(trade['r'])
    inventory = {key: len(group) for key, group in sorted(groups.items())}
    if len(groups) < 5:
        return {'method': 'Whole-time-cluster bootstrap sensitivity', 'status': 'INSUFFICIENT_TIME_CLUSTERS',
                'minimum_clusters': 5, 'clusters': inventory, 'p_two_sided_null_centered': 1.,
                'mean_ci95': None, 'total_ci95': None, 'verdict': 'NOT_SIGNIFICANT'}
    grouped = [groups[key] for key in sorted(groups)]
    sums = np.asarray([math.fsum(group) for group in grouped])
    counts = np.asarray([len(group) for group in grouped])
    values = np.asarray([t['r'] for t in trades])
    rng = np.random.default_rng(seed)
    sampled = np.empty(iterations)
    n = len(grouped)
    chunk = min(batch_size, max(1, 1_000_000 // n))
    for offset in range(0, iterations, chunk):
        count = min(chunk, iterations - offset)
        indices = rng.integers(0, n, size=(count, n))
        sampled[offset:offset + count] = sums[indices].sum(axis=1) / counts[indices].sum(axis=1)
    result = _resample_summary(values, sampled, iterations=iterations, seed=seed,
                               method='Whole-time-cluster bootstrap; sum(R)/sum(n), total CI at original n')
    result.update(clusters=inventory, cluster_count=len(groups),
                  independence_proven=False, fixed_horizon_profit_claim=False)
    return result


def descriptive_periods(trades, boundaries):
    result = []
    for index, (start, end) in enumerate(itertools.pairwise(boundaries)):
        selected = [t for t in trades if start <= t['entry_time'] < end or
                    (index == 2 and t['entry_time'] == end)]
        result.append({'period': index + 1, 'start': start, 'end': end,
                       'cross_boundary_exits': sum(t['exit_time'] > end for t in selected),
                       'method': 'Entry-time grouping of same ledger; not fresh independent replay',
                       'fresh_replay': False, **trade_metrics(selected)})
    return result


def analyze_study(document, *, iterations=10000, seed=20261018, batch_size=256):
    _controls(iterations, seed, batch_size)
    if not isinstance(document, dict) or not isinstance(document.get('models'), list):
        raise TypeError('Study object with models list required')
    if _finite(document.get('commission_usd_round_trip_per_lot'), 'commission') != 7.:
        raise ValueError('Primary commission must be fixed at USD7 round-trip per lot')
    if _finite(document.get('slippage_points_per_side'), 'slippage') != 10.:
        raise ValueError('Original 10-point per-side slippage required')
    models = {}
    for row in document['models']:
        model = row.get('model') if isinstance(row, dict) else None
        if model not in REGISTRY or model in models:
            raise ValueError('Unknown or duplicate model identifier')
        models[model] = validate_unique_trades(model, row.get('trades'))
    if set(models) != set(REGISTRY):
        raise ValueError('Multiplicity family must include all ' + str(len(REGISTRY)) + ' registered models')
    all_trades = [trade for trades in models.values() for trade in trades]
    boundaries = document.get('period_boundaries')
    if boundaries is None:
        start = min((t['entry_time'] for t in all_trades), default=0.)
        end = max((t['exit_time'] for t in all_trades), default=3.)
        end = max(end, start + 3.)
        boundaries = [start + (end - start) * i / 3 for i in range(4)]
        boundary_source = 'Derived from same ledger trade interval; descriptive only'
    else:
        if not isinstance(boundaries, list) or len(boundaries) != 4:
            raise ValueError('Exactly four increasing chronological period boundaries required')
        boundaries = [_finite(v, 'period boundary') for v in boundaries]
        if any(b <= a for a, b in itertools.pairwise(boundaries)):
            raise ValueError('Strictly increasing period boundaries required')
        if any(t['entry_time'] < boundaries[0] or t['exit_time'] > boundaries[-1] for t in all_trades):
            raise ValueError('Declared period boundaries exclude observed trades')
        boundary_source = 'Caller-declared; same-ledger grouping remains descriptive'
    rows = []
    for model in sorted(models):
        trades = models[model]
        iid = bootstrap_iid([t['r'] for t in trades], iterations=iterations,
                            seed=stable_seed(model, seed, 'iid'), batch_size=batch_size)
        block = cluster_sensitivity(trades, iterations=iterations,
                                    seed=stable_seed(model, seed, 'clusters'), batch_size=batch_size)
        rows.append({'model': model, **trade_metrics(trades), 'iid': iid,
                     'cluster_sensitivity': block, 'primary_ranking_eligible': len(trades) >= 30,
                     'short_sample': len(trades) < 30,
                     'periods_descriptive': descriptive_periods(trades, boundaries)})
    bonferroni, bh = adjusted_pvalues([r['iid']['p_two_sided_null_centered'] for r in rows])
    for index, row in enumerate(rows):
        row['p_bonferroni_all_models'] = bonferroni[index]
        row['p_bh_all_models'] = bh[index]
    ranked = sorted((r for r in rows if r['primary_ranking_eligible']), key=lambda r: (-r['net_r'], r['model']))
    positive = lambda row: row['trades'] > 0 and row['net_r'] > 0
    significant = [r['model'] for r in rows if positive(r) and r['iid']['verdict'] == 'SIGNIFICANT_AT_95']
    after_bonf = [r['model'] for r in rows if positive(r) and r['iid']['verdict'] == 'SIGNIFICANT_AT_95'
                  and r['p_bonferroni_all_models'] <= .05]
    after_bh = [r['model'] for r in rows if positive(r) and r['iid']['verdict'] == 'SIGNIFICANT_AT_95'
                and r['p_bh_all_models'] <= .05]
    return {'status': 'POST_SELECTION_LONG_HISTORY_DIAGNOSTIC', 'qualified': False,
            'execution_authority': False, 'live_changes': False,
            'primary_commission_usd_round_trip_per_lot': 7., 'slippage_points_per_side': 10.,
            'iterations': iterations, 'seed': seed, 'family_size': len(rows),
            'models_with_trades': sum(r['trades'] > 0 for r in rows),
            'raw_positive_models': [r['model'] for r in rows if positive(r)],
            'positive_significant_before_correction': significant,
            'positive_after_bonferroni': after_bonf, 'positive_after_bh': after_bh,
            'counts': {'positive_net_r': sum(positive(r) for r in rows),
                       'significant_before': len(significant), 'after_bonferroni': len(after_bonf),
                       'after_bh': len(after_bh)},
            'primary_adjustment': 'Bonferroni all registry models; BH dependence assumptions not independently verified',
            'ranking_rule': 'USD7 netR descending, minimum30 unique OOS trades, model-id tie break; fixed before inspecting USD0/USD3',
            'top5': [{k: row[k] for k in ('model', 'trades', 'win_rate', 'net_r', 'trade_sharpe_nonannualized',
                                         'max_drawdown_r', 'p_bonferroni_all_models', 'p_bh_all_models')} for row in ranked[:5]],
            'selected_best_model': ranked[0]['model'] if ranked else None,
            'period_boundaries': boundaries, 'period_boundary_source': boundary_source,
            'models': rows,
            'source_data_sha256': document.get('source_data_sha256'),
            'study_protocol': document.get('protocol'),
            'limitations': ['Unique nonoverlapping trade intervals are validated per model/symbol/frame, not claimed independent.',
                           'IID inference is conditional on fixed observed trades and can understate temporal dependence.',
                           'Whole-fold/month clusters are a sensitivity analysis; at least5 time clusters required.',
                           'All58 models retained including no-trade p=1; original wider historical search is not erased.',
                           'Same-ledger3-period summaries are descriptive, not three fresh causal replays or unseen OOS.',
                           'No rejection or non-significance proves a true zero edge or luck.',
                           'Positive/significant samples do not establish broker-executable or portfolio profitability.',
                           'Historical costs, source gaps and post-selection reuse remain external study-quality gates.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--iterations', type=int, default=10000)
    parser.add_argument('--seed', type=int, default=20261018)
    args = parser.parse_args()
    source = json.loads(args.input.read_text(encoding='utf-8'))
    result = analyze_study(source, iterations=args.iterations, seed=args.seed)
    result['input_ledger_sha256'] = hashlib.sha256(args.input.read_bytes()).hexdigest()
    result['statistics_source_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps({key: result[key] for key in ('status', 'family_size', 'models_with_trades', 'counts',
                                                   'selected_best_model', 'top5', 'qualified')}, indent=2))


if __name__ == '__main__':
    main()
