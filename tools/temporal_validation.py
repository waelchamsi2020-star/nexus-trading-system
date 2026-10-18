"""Retrospective chronological half-split audit; never a new unseen holdout.

The existing rule is fixed, not fitted. Only the training ATR envelope is fitted
on the first half. Every replay is confined to a single calendar-aware segment.
The report explicitly discloses prior selection on this same dataset.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from nexus.quant import atr, replay
from nexus.segment_research import split_segments, summarize
from nexus.strategies import (
    REGISTRY,
    configured_minimum,
    load_model_config,
    model_config_revision,
    validate_bars,
)
from nexus.timeframes import bar_close_time
from nexus.walkforward import LookaheadBiasError


def fit_training_envelope(training_bars, timeframe, profile):
    """Fit an ATR median using training-only windows; never span a source gap."""
    segments = split_segments(training_bars, timeframe, profile)
    values = [atr(segment[index - 14:index + 1])
              for segment in segments for index in range(14, len(segment))]
    if not values:
        raise ValueError('Training half has no complete within-segment ATR windows')
    baseline = statistics.median(values)
    if baseline <= 0:
        raise ValueError('Training ATR baseline must be positive')
    return {'atr_median': baseline, 'atr_windows': len(values),
            'maximum_input_close_time': bar_close_time(training_bars[-1]['time'], timeframe),
            'fit_method': 'median of within-segment 15-candle simple ATR windows; training half only'}


def _evaluate_half(bars, *, model, symbol, timeframe, profile, costs, fitted, model_config):
    segments = split_segments(bars, timeframe, profile)
    minimum = configured_minimum(model, {'model_config': model_config})
    trades, inventory = [], []
    for index, segment in enumerate(segments):
        eligible = len(segment) >= 200
        row = {'segment': index, 'bars': len(segment), 'eligible': eligible,
               'first_bar_time': segment[0]['time'], 'last_bar_time': segment[-1]['time'],
               'warmup_bars': min(minimum - 1, len(segment)) if eligible else 0}
        if eligible:
            # Only this half/segment is passed to replay. Its own completed
            # candles supply causal indicator warmup; no state crosses a gap.
            result = replay(segment, model, symbol, timeframe,
                            start_index=minimum - 1, end_index=len(segment), config=costs,
                            context={'tick_size': costs['point'], 'model_config': model_config,
                                     'train_atr_median': fitted['atr_median'], 'data_kind': 'broker'})
            row.update(signals=result['signals'], skipped=len(result['skipped']),
                       replayable_signal_bars=max(0, len(segment) - minimum),
                       trades=len(result['trades']))
            trades.extend({'segment': index, **trade} for trade in result['trades'])
        inventory.append(row)
    return {'metrics': summarize(trades), 'trades': trades, 'segments': inventory,
            'eligible_segments': sum(row['eligible'] for row in inventory),
            'eligible_bars': sum(row['bars'] for row in inventory if row['eligible']),
            'ignored_bars_below_200': sum(row['bars'] for row in inventory if not row['eligible']),
            'minimum_history_bars': minimum,
            'warmup_bars': sum(row['warmup_bars'] for row in inventory),
            'replayable_signal_bars': sum(row.get('replayable_signal_bars', 0) for row in inventory)}


def validate_temporal_half(bars, *, symbol, timeframe, as_of, profile, costs,
                           model='support_bounce', model_config=None):
    if len(bars) < 2:
        raise ValueError('Two chronological halves require at least two candles')
    if any(bar_close_time(row['time'], timeframe) > as_of for row in bars):
        raise LookaheadBiasError('Future or incomplete candle in chronological split')
    validate_bars(bars, timeframe, as_of)
    config_path = ROOT / 'src/nexus/config/models.yaml'
    model_config = model_config if model_config is not None else load_model_config(config_path)
    split_index = len(bars) // 2
    training, heldout = bars[:split_index], bars[split_index:]
    fitted = fit_training_envelope(training, timeframe, profile)
    if fitted['maximum_input_close_time'] > heldout[0]['time']:
        raise LookaheadBiasError('Training boundary overlaps the heldout half')
    common = {'model': model, 'symbol': symbol, 'timeframe': timeframe,
              'profile': profile, 'costs': costs, 'fitted': fitted, 'model_config': model_config}
    train_result = _evaluate_half(training, **common)
    heldout_result = _evaluate_half(heldout, **common)
    observed_positive = (heldout_result['metrics']['trades'] > 0 and
                         heldout_result['metrics']['net_r'] > 0)
    return {'model': model, 'rule_version': REGISTRY[model]['version'],
            'model_config_revision': model_config_revision(model_config),
            'total_bars': len(bars), 'split_index': split_index,
            'training_bars': len(training), 'heldout_bars': len(heldout),
            'training_first_time': training[0]['time'], 'training_last_time': training[-1]['time'],
            'heldout_first_time': heldout[0]['time'], 'heldout_last_time': heldout[-1]['time'],
            'fitted_training_only': fitted, 'training': train_result, 'heldout': heldout_result,
            'costs': costs, 'calendar_profile': profile,
            'parameter_selection': 'Existing support_bounce rule and configuration frozen; no grid search or heldout tuning. Only ATR baseline fitted on first half.',
            'qualification': False, 'qualified': False, 'execution_authority': False, 'live_changes': False,
            'post_selection_reused_data': True, 'genuinely_unseen_out_of_sample': False,
            'observed_heldout_positive_net_r': observed_positive,
            'validation_pass': False,
            'validation_verdict': 'RETROSPECTIVE_POSITIVE_NOT_UNSEEN_OOS' if observed_positive else 'RETROSPECTIVE_NONPOSITIVE_OR_INSUFFICIENT',
            'limitations': ['Model was selected using outcomes from these same 10000 bars; resplitting does not erase selection bias.',
                           'No fabricated bars, fallback below 200, or indicator/position state across unexpected gaps.',
                           'Samples and trades are not asserted statistically independent.',
                           'Training metrics are in-sample diagnostics; fitted ATR uses the complete first half.',
                           'OHLC spread/slippage replay is not actual broker execution; commissions remain hypothetical.',
                           'Sharpe is the nonannualized mean/std of trade R, not time-series or account Sharpe.']}


def main():
    from edge_test import calendar_profile, load_native

    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', type=Path, default=ROOT / 'data/real/H1/EURUSD_H1.csv')
    parser.add_argument('--metadata', type=Path,
                        default=ROOT / 'reports/commission-scenarios/H1/commission-0/metadata.json')
    parser.add_argument('--output', type=Path,
                        default=ROOT / 'reports/statistical-validation/temporal-validation.json')
    args = parser.parse_args()
    metadata = json.loads(args.metadata.read_text(encoding='utf-8'))
    if metadata['symbol'] != 'EURUSD' or metadata['timeframe'] != 'H1':
        raise ValueError('This fixed-scope temporal audit requires EURUSD H1')
    bars, costs, fingerprint = load_native(args.csv, metadata, time.time(), preliminary=True)
    costs['commission_per_unit'] = 7.0 / metadata['contract_size']
    result = validate_temporal_half(bars, symbol='EURUSD', timeframe='H1', as_of=time.time(),
                                    profile=calendar_profile(metadata), costs=costs)
    result.update(data_sha256=fingerprint, commission_usd_round_trip_per_lot=7.0,
                  slippage_points_per_side=10,
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    lines = ['# Retrospective chronological half split', '',
             '**Previously selected on the same dataset; this is not an unseen holdout.**', '',
             '| half | original bars | eligible segments | eligible bars | warmup bars | trades | win rate | net R | Sharpe | max DD R |',
             '|---|---|---|---|---|---|---|---|---|---|']
    for key in ('training', 'heldout'):
        row = result[key]
        m = row['metrics']
        lines.append('| ' + ' | '.join(str(value) for value in
                     (key, result[key + '_bars'], row['eligible_segments'], row['eligible_bars'],
                      row['warmup_bars'], m['trades'], m['win_rate'], m['net_r'], m['sharpe'], m['max_dd'])) + ' |')
    lines.extend(['', result['validation_verdict'], '', result['parameter_selection'], '',
                  json.dumps(result['fitted_training_only'], indent=2), '',
                  *('- ' + limit for limit in result['limitations'])])
    args.output.with_suffix('.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({key: value for key, value in result.items() if key not in ('training', 'heldout')}, indent=2))
    for key in ('training', 'heldout'):
        print(key, json.dumps(result[key]['metrics']))


if __name__ == '__main__':
    main()
