"""Selected-model regime-only generalization on existing native GBPUSD/USDJPY.

Only one fixed model is evaluated on each symbol. The 58-row routing schema is
retained, but the other 57 models are explicitly not evaluated. HTF, dollar-index
and session filters are outside this benchmark; no cross-series data is invented.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))

from context_layer_study import (
    AuditWriter,
    ContextGate,
    classify_cache,
    compact_study,
    fit_training_maps,
    write_json,
)
from export_context_history import verify_reused_history
from long_signal_cache import build_cache
from long_walkforward import fit_baselines, run_study, schedule

from nexus.regime_router import load_routing_config
from nexus.strategies import REGISTRY


def choose_model(causal_study):
    """Fix the winner once on EURUSD USD7 results, before cross-symbol results."""
    scenario = next(row for row in causal_study['scenarios']
                    if row['commission_usd_round_trip_per_lot'] == 7.)
    rows = scenario['models']
    if {row['model'] for row in rows} != set(REGISTRY) or len(rows) != len(REGISTRY):
        raise ValueError('EURUSD selection source must retain all 58 evaluated models')
    adequate = [row for row in rows if row['trades'] >= 30]
    if adequate:
        selected = min(adequate, key=lambda row: (-row['net_r'], row['model']))
        basis = 'FIXED_USD7_NET_R_AMONG_N_GE_30'
    else:
        selected = min(rows, key=lambda row: (-row['trades'], -row['net_r'], row['model']))
        basis = 'DESCRIPTIVE_MOST_TRADES_NO_MODEL_REACHED_30'
    return {'model': selected['model'], 'eurusd_trades': selected['trades'],
            'eurusd_net_r': selected['net_r'], 'selection_basis': basis,
            'eurusd_sample_adequate': bool(adequate), 'execution_authority': False}


def pad_schema_inventory(cache, selected):
    """Retain schema IDs without claiming uncomputed cross-model coverage."""
    if selected not in REGISTRY or set(cache['cards']) != {selected}:
        raise ValueError('Cross-model cache must evaluate exactly the selected model')
    result = dict(cache)
    result['cards'] = {model: cache['cards'][selected] if model == selected else [] for model in sorted(REGISTRY)}
    result['status_counts'] = {model: cache['status_counts'].get(model, {}) if model == selected else {}
                               for model in sorted(REGISTRY)}
    result['provenance'] = {**cache['provenance'], 'evaluated_model_ids': [selected],
                            'not_evaluated_model_ids': sorted(set(REGISTRY) - {selected}),
                            'schema_padding_only': True, 'qualified': False}
    return result


def run_symbol(selected, row, output_dir, *, workers=2):
    symbol = row['symbol']
    verified = verify_reused_history(row['csv'], symbol=symbol)
    metadata = json.loads(Path(verified['metadata']).read_bytes())
    original = build_cache(
        row['csv'], symbol=symbol, timeframe='H1', point=metadata['point'],
        profile=metadata['calendar_profile'], cache_dir=ROOT / 'reports/context-layer/cross-signal-cache',
        workers=workers, start_index=0, model_ids=[selected])
    cache = pad_schema_inventory(original, selected)
    cache.update(symbol=symbol, timeframe='H1', specification={
        key: metadata[key] for key in ('point', 'contract_size', 'profit_currency', 'symbol')})
    profile = load_routing_config()
    contexts = classify_cache(cache, profile)
    folds = fit_baselines(cache, schedule(len(cache['bars']), train=5000, test=1000, step=500, embargo=24))
    maps = fit_training_maps(cache, folds, contexts, profile)
    folder = Path(output_dir) / symbol
    folder.mkdir(parents=True, exist_ok=True)
    write_json(folder / 'training-maps.json', maps)
    studies = {}
    audit_summaries = {}
    for name, selection_only in (('selection_only', True), ('causal_regime', False)):
        gate = ContextGate(cache, contexts, maps, selection_only=selection_only)
        audit_path = folder / (name + '-rejections.jsonl.gz')
        with gzip.open(audit_path, 'wt', encoding='utf-8') as stream:
            audit = AuditWriter(audit_path, stream)
            study = run_study(cache, train=5000, test=1000, step=500, embargo=24,
                              model_ids=[selected], signal_gate=gate, gate_audit=audit)
        audit_summaries[name] = audit.summary()
        studies[name] = compact_study(study)
        write_json(folder / (name + '.json'), studies[name])
    measurements = []
    for fee in (0., 3., 7.):
        for name, study in studies.items():
            result = next(s for s in study['scenarios'] if s['commission_usd_round_trip_per_lot'] == fee)['models'][0]
            measurements.append({'symbol': symbol, 'model': selected, 'variant': name,
                                 'commission_usd_round_trip_per_lot': fee,
                                 **{key: result[key] for key in ('trades', 'win_rate', 'net_r', 'sharpe',
                                                                'max_dd', 'censored', 'profitable_windows',
                                                                'total_windows')}})
    summary = {
        'symbol': symbol, 'model': selected, 'bars': len(cache['bars']), 'folds': len(folds),
        'scope': 'REGIME_ONLY_SELECTED_MODEL_CAUSAL_TRAINING_MAP',
        'evaluated_model_ids': [selected], 'not_evaluated_model_count': len(REGISTRY) - 1,
        'native_source': verified, 'signal_cache_provenance': original['provenance'],
        'measurements': measurements, 'audits': audit_summaries,
        'protocol': {'train': 5000, 'test': 1000, 'step': 500, 'embargo': 24,
                     'commission_usd_round_trip_per_lot': [0, 3, 7],
                     'slippage_points_per_side': 10, 'spread': 'native row spread',
                     'training_selection': 'USD7 netR>0 and n>=5 per known regime in training only'},
        'qualified': False, 'execution_authority': False, 'orders_sent': 0,
        'limitations': [
            'The model ID was selected on the EURUSD retrospective test; this is exploratory cross-symbol evaluation.',
            'Only the selected model is evaluated. Other schema rows are disabled placeholders for inventory validation, not model coverage.',
            'The same model/regime training selection is fitted independently on each symbol; EURUSD routing membership is not copied.',
            'No H4/D1, DXY agreement or session veto is included; no corresponding cross-symbol context histories were supplied.',
            'Unknown intrabar gaps remain censored, and the broker calendar remains unverified.',
            'USDJPY commission is converted to JPY price units using each historical exit quote, without lowering USD fees.',
        ],
    }
    write_json(folder / 'summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--causal-study', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'reports/context-layer/cross-regime-only')
    parser.add_argument('--workers-per-symbol', type=int, default=2)
    args = parser.parse_args()
    if args.workers_per_symbol != 2:
        raise ValueError('This two-symbol benchmark fixes exactly two workers per symbol (four maximum)')
    selected = choose_model(json.loads(args.causal_study.read_bytes()))
    manifest = json.loads((ROOT / 'reports/five-year-cross-history/export-manifest.json').read_bytes())
    inputs = [row for row in manifest if row['symbol'] in ('GBPUSD', 'USDJPY') and row['exit_code'] == 0]
    if {row['symbol'] for row in inputs} != {'GBPUSD', 'USDJPY'} or len(inputs) != 2:
        raise ValueError('Verified native GBPUSD and USDJPY sources required')
    args.output.mkdir(parents=True, exist_ok=True)
    write_json(args.output / 'selection.json', selected)
    print('CROSS_SELECTED ' + json.dumps(selected), flush=True)
    results = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(run_symbol, selected['model'], copy.deepcopy(row), args.output,
                                workers=2): row['symbol'] for row in inputs}
        for future in as_completed(futures):
            results.append(future.result())
    summary = {'selection': selected, 'symbols': sorted(results, key=lambda row: row['symbol']),
               'qualified': False, 'execution_authority': False, 'orders_sent': 0}
    write_json(args.output / 'summary.json', summary)
    print(json.dumps({'selection': selected, 'measurements': [row for symbol in summary['symbols']
                      for row in symbol['measurements']], 'orders_sent': 0, 'qualified': False}, indent=2))


if __name__ == '__main__':
    main()
