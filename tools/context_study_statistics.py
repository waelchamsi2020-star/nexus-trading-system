"""Fixed USD7 uncertainty diagnostics for preregistered context ablations.

Every variant retains all 58 models, including zero-trade rows with p=1. The
existing validated bootstrap engine supplies the uncertainty calculations;
this adapter never filters censored exposures into zero returns or promotes
any result to execution authority. More variants are additional searches.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))

from long_study_statistics import (
    adjusted_pvalues,
    analyze_study,
    validate_unique_trades,
)

from nexus.strategies import REGISTRY

SEED = 20261019
ITERATIONS = 10000
EXPECTED_COSTS = 'USD0/3/7 per lot round trip; adverse10 observed symbol points each side; row spread'


def fee_seven_document(study):
    """Validate and detach the unique primary ledger, excluding fold copies."""
    if not isinstance(study, dict) or study.get('timeframe') != 'H1':
        raise ValueError('An explicit H1 context study is required')
    if study.get('qualified') is not False or study.get('execution_authority') is not False:
        raise ValueError('Context statistics require unqualified research without authority')
    protocol = study.get('protocol')
    if (not isinstance(protocol, dict) or protocol.get('costs') != EXPECTED_COSTS or
            any(type(protocol.get(key)) is not int or protocol[key] != value
                for key, value in {'train': 5000, 'test': 1000, 'step': 500, 'embargo': 24}.items())):
        raise ValueError('Original H1 windows, embargo and ten-point costs must remain fixed')
    source = study.get('source_data_sha256')
    if not isinstance(source, str) or not re.fullmatch('[a-f0-9]{64}', source):
        raise ValueError('Source data SHA256 is required')
    selected = [scenario for scenario in study.get('scenarios', [])
                if isinstance(scenario, dict) and scenario.get('commission_usd_round_trip_per_lot') == 7.]
    if len(selected) != 1:
        raise ValueError('Exactly one USD7 commission scenario is required')
    rows = selected[0].get('models')
    if not isinstance(rows, list):
        raise TypeError('A complete model list is required')
    document_rows, models, censoring = [], set(), {}
    for row in rows:
        if not isinstance(row, dict) or row.get('model') not in REGISTRY or row['model'] in models:
            raise ValueError('Unknown or duplicate model in context ledger')
        model = row['model']
        models.add(model)
        records = validate_unique_trades(model, row.get('trade_records'))
        if type(row.get('trades')) is not int or row['trades'] != len(records):
            raise ValueError('Reported closed count differs from primary records: ' + model)
        net = row.get('net_r')
        if (isinstance(net, bool) or not isinstance(net, (int, float)) or not math.isfinite(net) or
                not math.isclose(math.fsum(trade['r'] for trade in records), net, rel_tol=1e-10, abs_tol=1e-9)):
            raise ValueError('Reported net R differs from primary records: ' + model)
        count = row.get('censored')
        if type(count) is not int or count < 0:
            raise ValueError('Explicit nonnegative censored count required: ' + model)
        censoring[model] = count
        document_rows.append({'model': model, 'trades': records})
    if models != set(REGISTRY):
        raise ValueError('All 58 registry models must remain in the multiplicity family')
    return ({'commission_usd_round_trip_per_lot': 7., 'slippage_points_per_side': 10.,
             'models': document_rows, 'source_data_sha256': source, 'protocol': dict(protocol)}, censoring)


def _winner(row):
    if row is None:
        return None
    return {'model': row['model'], 'trades': row['trades'], 'net_r': row['net_r'],
            'mean_r': row['mean_r'], 'win_rate': row['win_rate'],
            'sharpe_nonannualized': row['trade_sharpe_nonannualized'],
            'max_dd_r': row['max_drawdown_r'], 'mean_ci95': row['iid']['mean_ci95'],
            'total_ci95': row['iid']['total_ci95'],
            'p_value': row['iid']['p_two_sided_null_centered'],
            'p_bonferroni_58': row['p_bonferroni_all_models'], 'p_bh_58': row['p_bh_all_models'],
            'p_bonferroni_provided_variants': row['p_bonferroni_provided_variants'],
            'iid_verdict': row['iid']['verdict'], 'censored_exposures': row['censored_exposures'],
            'minimum_30_trades_satisfied': row['primary_ranking_eligible'],
            'cluster_sensitivity': row['cluster_sensitivity'],
            'qualified': False, 'execution_authority': False}


def analyze_context_studies(studies, *, iterations=ITERATIONS, seed=SEED):
    """Run exactly the existing bootstrap, separately and across supplied searches."""
    if not isinstance(studies, dict) or not studies:
        raise ValueError('At least one named context study is required')
    results = {}
    for name, study in sorted(studies.items()):
        if not isinstance(name, str) or not re.fullmatch('[A-Za-z0-9_-]+', name):
            raise ValueError('A simple explicit variant name is required')
        document, censoring = fee_seven_document(study)
        result = analyze_study(document, iterations=iterations, seed=seed)
        for row in result['models']:
            row['censored_exposures'] = censoring[row['model']]
        result.update(variant=name, unknown_exposures=sum(censoring.values()),
                      censor_warning='Unknown gap exposures retain R=null outside this observable ledger; '
                                     'complete-case bootstrap is conditional and cannot qualify a model.',
                      positive_models_n_ge_30=[row['model'] for row in result['models']
                                              if row['primary_ranking_eligible'] and row['net_r'] > 0])
        results[name] = result
    combined = [(name, row) for name, result in results.items() for row in result['models']]
    bonf, bh = adjusted_pvalues([row['iid']['p_two_sided_null_centered'] for name, row in combined])
    for index, (_name, row) in enumerate(combined):
        row['p_bonferroni_provided_variants'] = bonf[index]
        row['p_bh_provided_variants'] = bh[index]
    for result in results.values():
        chosen = next((row for row in result['models'] if row['model'] == result['selected_best_model']), None)
        available = [row for row in result['models'] if row['trades'] > 0]
        raw = min(available, key=lambda row: (-row['net_r'], row['model'])) if available else None
        result['selected_winner'] = _winner(chosen)
        result['descriptive_best_without_sample_cutoff'] = _winner(raw)
        result['winner_status'] = ('NO_ELIGIBLE_MODEL_WITH_30_TRADES' if chosen is None else
                                  'CONDITIONAL_SIGNIFICANCE_AFTER_58_ONLY' if chosen['net_r'] > 0 and
                                  chosen['iid']['verdict'] == 'SIGNIFICANT_AT_95' and
                                  chosen['p_bonferroni_all_models'] <= .05 else 'NOT_SIGNIFICANT')
    return {'status': 'EXPLORATORY_CONTEXT_ABLATION_UNCERTAINTY',
            'iterations': iterations, 'seed': seed, 'per_variant_family': len(REGISTRY),
            'provided_variant_count': len(results), 'provided_family_size': len(combined),
            'commission_usd_round_trip_per_lot': 7., 'slippage_points_per_side': 10.,
            'qualified': False, 'execution_authority': False, 'orders_sent': 0,
            'variants': results,
            'limitations': ['No best commission scenario is selected; every calculation uses USD7 and original ten-point slippage.',
                           'Bonferroni/BH across all58 is per variant; additional provided-variant corrections are sensitivity only.',
                           'Prior historical model/variant searches not supplied here remain unaccounted; no definitive edge claim.',
                           'IID bootstrap may understate serial dependence; whole-fold cluster sensitivity is included.',
                           'Censored exposures are not zero and can invalidate conditional observed-trade inference.',
                           'All variants use reused history, not independent prospective validation.',
                           'A significance test on returns is not a paired causal-effect test against the baseline.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study', action='append', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    studies, provenance = {}, {}
    for path in args.study:
        if path.stem in studies:
            raise ValueError('Duplicate variant filename stem')
        blob = path.read_bytes()
        studies[path.stem] = json.loads(blob)
        provenance[path.stem] = {'path': str(path.resolve()), 'sha256': hashlib.sha256(blob).hexdigest()}
    result = analyze_context_studies(studies)
    for name, item in provenance.items():
        if hashlib.sha256(Path(item['path']).read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('Study artifact changed during analysis: ' + name)
    result['source_artifacts'] = provenance
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + '.pending')
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    temporary.replace(args.output)
    print(json.dumps({'iterations': result['iterations'], 'seed': result['seed'],
                      'provided_family_size': result['provided_family_size'],
                      'variants': {name: {key: row[key] for key in (
                          'counts', 'selected_winner', 'descriptive_best_without_sample_cutoff',
                          'winner_status', 'unknown_exposures')} for name, row in result['variants'].items()},
                      'qualified': False, 'orders_sent': 0}, indent=2))


if __name__ == '__main__':
    main()
