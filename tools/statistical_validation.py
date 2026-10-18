"""Reproducible post-selection diagnostics; never grants trading authority.

Percentile IID bootstrap estimates mean/total uncertainty. A separate centered
null bootstrap tests mean R=0; the fraction of uncentered positive resamples is
not a p-value. Bonferroni is primary because strategies share market evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from nexus.segment_research import reprice, summarize


def bootstrap(values, *, repetitions=10_000, seed=20261018):
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or not np.isfinite(values).all():
        raise ValueError('Finite one-dimensional trade returns required')
    if type(repetitions) is not int or repetitions < 100:
        raise ValueError('At least 100 resamples required')
    n = len(values)
    if n < 2 or np.ptp(values) == 0:
        return {'n': n, 'status': 'INSUFFICIENT_VARIATION', 'p_two_sided': 1.,
                'p_positive': 1., 'mean_r': float(values.mean()) if n else None,
                'total_r': float(values.sum()), 'mean_ci95': None, 'total_ci95': None,
                'resampled_mean_r': None, 'verdict': 'NOT_SIGNIFICANT'}
    rng = np.random.default_rng(seed)
    resampled = values[rng.integers(0, n, size=(repetitions, n))].mean(axis=1)
    observed = float(values.mean())
    null = resampled - observed
    p_two = (int(np.count_nonzero(np.abs(null) >= abs(observed))) + 1) / (repetitions + 1)
    p_positive = (int(np.count_nonzero(null >= observed)) + 1) / (repetitions + 1)
    ci = np.quantile(resampled, [.025, .975])
    return {'n': n, 'status': 'IID_ASSUMPTION', 'seed': seed, 'repetitions': repetitions,
            'mean_r': observed, 'total_r': float(values.sum()),
            'sample_sd_r': float(values.std(ddof=1)),
            'resampled_mean_r': float(resampled.mean()),
            'resampled_total_mean_r': float(resampled.mean() * n),
            'mean_ci95': ci.tolist(), 'total_ci95': (ci * n).tolist(),
            'p_two_sided': p_two, 'p_positive': p_positive,
            'verdict': 'SIGNIFICANT_AT_95' if observed > 0 and ci[0] > 0 and p_two <= .05 else 'NOT_SIGNIFICANT'}


def adjusted_pvalues(pvalues, *, family_size=None):
    ps = np.asarray(pvalues, dtype=float)
    if ps.ndim != 1 or not np.isfinite(ps).all() or np.any((ps < 0) | (ps > 1)):
        raise ValueError('Finite p-values in [0,1] required')
    m = len(ps) if family_size is None else family_size
    if type(m) is not int or m < len(ps) or m < 1:
        raise ValueError('Family size must include every tested hypothesis')
    order = np.argsort(ps, kind='stable')
    ranked = ps[order] * m / np.arange(1, len(ps) + 1)
    adjusted = np.minimum.accumulate(ranked[::-1])[::-1]
    bh = np.empty_like(ps)
    bh[order] = np.minimum(adjusted, 1.)
    return np.minimum(ps * m, 1.).tolist(), bh.tolist()


def block_sensitivity(trades, *, repetitions=10_000, seed=20261019, block_length=4):
    """Circular blocks within each observed segment, never across its data gap."""
    if not trades:
        raise ValueError('Observed trades required')
    if type(block_length) is not int or block_length < 1:
        raise ValueError('Positive block length required')
    groups = {}
    for trade in trades:
        groups.setdefault(trade['segment'], []).append(float(trade['r']))
    rng = np.random.default_rng(seed)
    totals = np.zeros(repetitions)
    for raw in groups.values():
        values = np.asarray(raw)
        n = len(values)
        length = min(n, block_length)
        starts = rng.integers(0, n, size=(repetitions, math.ceil(n / length)))
        indices = ((starts[:, :, None] + np.arange(length)) % n).reshape(repetitions, -1)[:, :n]
        totals += values[indices].sum(axis=1)
    observed = math.fsum(t['r'] for t in trades)
    null = totals - observed
    return {'method': 'Within-segment circular-block sensitivity, not independent confirmation',
            'block_length': block_length, 'seed': seed, 'repetitions': repetitions,
            'segment_trade_counts': {str(k): len(v) for k, v in groups.items()},
            'total_ci95': np.quantile(totals, [.025, .975]).tolist(),
            'p_two_sided': (int(np.count_nonzero(np.abs(null) >= abs(observed))) + 1) / (repetitions + 1)}


def validate_report(source, *, commission=7., repetitions=10_000):
    if source.get('symbol') != 'EURUSD' or source.get('timeframe') != 'H1':
        raise ValueError('This fixed-scope diagnostic requires EURUSD H1')
    if source.get('slippage_points_per_side') != 10:
        raise ValueError('Original ten-point per-side slippage must be preserved')
    contract = source['declared_provenance']['contract_size']
    if source['declared_provenance'].get('profit_currency') != 'USD' or contract <= 0:
        raise ValueError('Explicit USD quote contract required')
    records = []
    for model, trades in sorted(source['base_trades'].items()):
        if not trades:
            continue
        priced = reprice(trades, commission / contract)
        keys = [(t['segment'], t['entry_time'], t['side']) for t in priced]
        if len(set(keys)) != len(keys):
            raise ValueError('Duplicate model entry in source ledger')
        seed = 20261018 if model == 'support_bounce' else 20261018 + int.from_bytes(hashlib.sha256(model.encode()).digest()[:4])
        stats = bootstrap([t['r'] for t in priced], repetitions=repetitions, seed=seed)
        records.append({'model': model, **summarize(priced), 'bootstrap': stats})
    if len(records) != source['models_with_any_trades']:
        raise ValueError('Reported traded-model count mismatch')
    ps = [r['bootstrap']['p_two_sided'] for r in records]
    bonf, bh = adjusted_pvalues(ps)
    bonf58, bh58 = adjusted_pvalues(ps, family_size=source['models'])
    for index, row in enumerate(records):
        row.update(p_bonferroni=bonf[index], p_bh=bh[index],
                   p_bonferroni_all_registry=bonf58[index], p_bh_all_registry=bh58[index])
    selected = next(r for r in records if r['model'] == 'support_bounce')
    repriced = reprice(source['base_trades']['support_bounce'], commission / contract)
    return {'status': 'POST_SELECTION_STATISTICAL_DIAGNOSTIC', 'qualified': False,
            'execution_authority': False, 'live_changes': False,
            'source_data_sha256': source['data_sha256'], 'commission_usd_per_lot_round_trip': commission,
            'slippage_points_per_side': 10, 'spread_policy': 'Observed spread on each source bar',
            'repetitions': repetitions, 'family_size': len(records), 'all_registry_family_size': source['models'],
            'primary_adjustment': 'Bonferroni two-sided, robust to dependence across models if marginal tests are valid',
            'raw_positive_models': [r['model'] for r in records if r['net_r'] > 0],
            'positive_significant_before_correction': [r['model'] for r in records if r['bootstrap']['verdict'] == 'SIGNIFICANT_AT_95'],
            'positive_after_bonferroni': [r['model'] for r in records if r['net_r'] > 0 and r['p_bonferroni'] <= .05],
            'positive_after_bh': [r['model'] for r in records if r['net_r'] > 0 and r['p_bh'] <= .05],
            'support_bounce': selected, 'block_sensitivity': block_sensitivity(repriced, repetitions=repetitions),
            'models': records,
            'limitations': ['IID bootstrap is a requested conditional approximation, not proof of independent trades',
                           'Selection originally inspected 58 models, two frames and three cost scenarios; family42 alone understates search',
                           'BH reported descriptively; dependence conditions not independently established',
                           'Non-significance cannot prove luck or a true zero edge',
                           'Fixed-length trade-total CI is not annual/portfolio/account profit CI',
                           'No new unseen temporal holdout was created by reusing these source candles']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=ROOT / 'reports/preliminary-H1.json')
    parser.add_argument('--data', type=Path, default=ROOT / 'data/real/H1/EURUSD_H1.csv')
    parser.add_argument('--output', type=Path, default=ROOT / 'reports/statistical-validation/bootstrap-multiple.json')
    args = parser.parse_args()
    source = json.loads(args.source.read_text(encoding='utf-8'))
    if hashlib.sha256(args.data.read_bytes()).hexdigest() != source['data_sha256']:
        raise ValueError('Actual native CSV no longer matches observed trade ledger')
    result = validate_report(source)
    result['source_report_sha256'] = hashlib.sha256(args.source.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'models'}, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
