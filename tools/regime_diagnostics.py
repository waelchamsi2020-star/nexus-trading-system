"""Causal, retrospective regime annotations of an unchanged archived trade ledger.

Labels use completed candles strictly before entry, with a one-candle boundary
lag when the preceding candle closes exactly at entry. Thresholds are fixed for
this diagnostic and never selected from trade outcomes. This is exploratory
post-selection attribution, not a regime strategy or evidence of an edge.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from bisect import bisect_left
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from nexus.indicators import ema
from nexus.segment_research import reprice, split_segments, summarize
from nexus.specialists import SPECS
from nexus.strategies import REGISTRY, validate_bars
from nexus.timeframes import bar_close_time

REGIMES = ('UP', 'DOWN', 'RANGE', 'UNKNOWN')
REGIME_CONFIG = {
    'version': 'causal-regime-diagnostic-1.0.0',
    'history_bars': 60,
    'fast_ema': 20,
    'slow_ema': 50,
    'slope_bars': 5,
    'atr_period': 14,
    'minimum_ema_gap_atr': .5,
    'minimum_fast_ema_slope_atr': .25,
    'threshold_selection': 'Fixed before this diagnostic run; no outcome optimization. Retrospective exploratory thresholds, not preregistered evidence.',
}


def label_at_entry(segment, entry_time):
    """Annotate only from this segment; neither future prices nor PnL is read."""
    closes = [bar_close_time(row['time'], 'H1') for row in segment]
    cutoff = bisect_left(closes, entry_time)
    history = segment[max(0, cutoff - REGIME_CONFIG['history_bars']):cutoff]
    if len(history) < REGIME_CONFIG['history_bars']:
        return {'regime': 'UNKNOWN', 'reason': 'INSUFFICIENT_WITHIN_SEGMENT_HISTORY',
                'history_bars': len(history),
                'latest_input_close_time': closes[cutoff - 1] if cutoff else None}
    prices = [row['close'] for row in history]
    fast = ema(prices, REGIME_CONFIG['fast_ema'])
    slow = ema(prices, REGIME_CONFIG['slow_ema'])
    # Simple arithmetic ATR of the final 14 true ranges, with previous closes.
    ranges = [max(row['high'] - row['low'], abs(row['high'] - previous['close']),
                  abs(row['low'] - previous['close']))
              for previous, row in zip(history[-15:-1], history[-14:])]
    atr = math.fsum(ranges) / REGIME_CONFIG['atr_period']
    if atr <= 0:
        return {'regime': 'UNKNOWN', 'reason': 'ZERO_ATR', 'history_bars': len(history),
                'latest_input_close_time': closes[cutoff - 1]}
    gap = (fast[-1] - slow[-1]) / atr
    slope = (fast[-1] - fast[-1 - REGIME_CONFIG['slope_bars']]) / atr
    regime = ('UP' if gap >= REGIME_CONFIG['minimum_ema_gap_atr'] and
              slope >= REGIME_CONFIG['minimum_fast_ema_slope_atr'] else
              'DOWN' if gap <= -REGIME_CONFIG['minimum_ema_gap_atr'] and
              slope <= -REGIME_CONFIG['minimum_fast_ema_slope_atr'] else 'RANGE')
    return {'regime': regime, 'reason': 'FIXED_EMA_GAP_AND_SLOPE_THRESHOLDS',
            'history_bars': len(history), 'latest_input_close_time': closes[cutoff - 1],
            'atr': atr, 'ema_gap_atr': gap, 'fast_ema_slope_atr': slope}


def validate_ledger(bars, source, native_sha256):
    if source.get('symbol') != 'EURUSD' or source.get('timeframe') != 'H1':
        raise ValueError('Archived EURUSD H1 ledger required')
    if native_sha256 != source.get('data_sha256'):
        raise ValueError('Native CSV fingerprint does not match archived ledger')
    if source.get('slippage_points_per_side') != 10:
        raise ValueError('Archived ten-point slippage must remain unchanged')
    meta = source['declared_provenance']
    if meta.get('profit_currency') != 'USD' or meta.get('contract_size', 0) <= 0:
        raise ValueError('Explicit USD profit currency and contract scale required')
    if set(source['base_trades']) != set(REGISTRY) or source['models'] != len(REGISTRY):
        raise ValueError('Archived ledger must retain every current registered model')
    if len(bars) != source['total_bars']:
        raise ValueError('Native bar count differs from archived ledger')
    validate_bars(bars, 'H1', bar_close_time(bars[-1]['time'], 'H1'))
    segments = split_segments(bars, 'H1', source['calendar_profile'])
    inventory = source['segments']
    if len(segments) != len(inventory):
        raise ValueError('Archived calendar segmentation differs from native candles')
    for index, (segment, saved) in enumerate(zip(segments, inventory)):
        if (saved['segment'], saved['bars'], saved['first_time'], saved['last_time']) != (
                index, len(segment), segment[0]['time'], segment[-1]['time']):
            raise ValueError('Archived segment boundaries do not match native candles')
    for model, trades in source['base_trades'].items():
        previous_exit = None
        seen = set()
        for trade in trades:
            segment = segments[trade['segment']]
            entry_index, exit_index = trade['entry_index'], trade['exit_index']
            if not (0 <= entry_index <= exit_index < len(segment)):
                raise ValueError('Archived trade index outside its native segment')
            if segment[entry_index]['time'] != trade['entry_time']:
                raise ValueError('Archived entry time does not match native candle')
            exit_time = (segment[exit_index]['time'] if trade['exit_reason'].endswith('NEXT_OPEN')
                         else bar_close_time(segment[exit_index]['time'], 'H1'))
            if trade['exit_time'] != exit_time or trade['strategy_id'] != model:
                raise ValueError('Archived exit time or model identity mismatch')
            if trade['side'] not in ('BUY', 'SELL') or trade['signal_time'] > trade['entry_time']:
                raise ValueError('Invalid archived side or signal chronology')
            if previous_exit is not None and trade['entry_time'] < previous_exit:
                raise ValueError('Overlapping or unordered trades within one model')
            previous_exit = trade['exit_time']
            key = (trade['segment'], trade['entry_time'])
            if key in seen:
                raise ValueError('Duplicate archived trade')
            seen.add(key)
            values = [trade[key] for key in ('entry', 'exit', 'stop', 'gross_price_pnl',
                                             'commission_price_units', 'net_price_pnl', 'r')]
            if not all(math.isfinite(value) for value in values):
                raise ValueError('Nonfinite archived trade arithmetic')
            risk = abs(trade['entry'] - trade['stop'])
            gross = (trade['exit'] - trade['entry'] if trade['side'] == 'BUY'
                     else trade['entry'] - trade['exit'])
            if (risk <= 0 or trade['commission_price_units'] != 0 or
                    not math.isclose(gross, trade['gross_price_pnl'], abs_tol=1e-12) or
                    not math.isclose(gross, trade['net_price_pnl'], abs_tol=1e-12) or
                    not math.isclose(gross / risk, trade['r'], rel_tol=1e-10, abs_tol=1e-10)):
                raise ValueError('Archived base-trade arithmetic mismatch')
    return segments


def diagnose(bars, source, *, native_sha256, source_report_sha256):
    segments = validate_ledger(bars, source, native_sha256)
    scenario = next(row for row in source['scenarios']
                    if row['commission_usd_round_trip_per_lot'] == 7.)
    archived_metrics = {row['model']: row for row in scenario['all_selected_segments']}
    rows, records = [], []
    fee = 7. / source['declared_provenance']['contract_size']
    for model, base in sorted(source['base_trades'].items()):
        trades = reprice(base, fee)
        totals = summarize(trades)
        expected = archived_metrics[model]
        if totals['trades'] != expected['trades'] or not math.isclose(
                totals['net_r'], expected['net_r'], rel_tol=1e-10, abs_tol=1e-10):
            raise ValueError('Fee-seven repricing differs from archived model metrics')
        groups = {name: [] for name in REGIMES}
        for trade in trades:
            annotation = label_at_entry(segments[trade['segment']], trade['entry_time'])
            if annotation['latest_input_close_time'] is not None and not (
                    annotation['latest_input_close_time'] < trade['entry_time']):
                raise ValueError('Regime annotation read a non-prior candle')
            groups[annotation['regime']].append(trade)
            records.append({'model': model, 'segment': trade['segment'], 'side': trade['side'],
                            'entry_time': trade['entry_time'], 'exit_time': trade['exit_time'],
                            'net_r': trade['r'], **annotation})
        rows.append({'model': model, **totals,
                     'long_trades': sum(t['side'] == 'BUY' for t in trades),
                     'short_trades': sum(t['side'] == 'SELL' for t in trades),
                     'regimes': {name: summarize(group) for name, group in groups.items()}})
    first, last = bars[0]['time'], bar_close_time(bars[-1]['time'], 'H1')
    def pooled(selected):
        # Cross-model entries overlap. Never attach a portfolio Sharpe/drawdown
        # to an arbitrary concatenation of different models' trade records.
        count = len(selected)
        return {'model_trades': count,
                'win_rate': sum(t['net_r'] > 0 for t in selected) / count if count else None,
                'net_r_sum_nonportfolio': math.fsum(t['net_r'] for t in selected)}

    aggregate = {name: pooled([row for row in records if row['regime'] == name])
                 for name in REGIMES}
    direction_groups = {name: {side: pooled([row for row in records
                                            if row['regime'] == name and row['side'] == side])
                               for side in ('BUY', 'SELL')} for name in REGIMES}
    first_trade = min((row['entry_time'] for row in records), default=None)
    last_trade = max((row['exit_time'] for row in records), default=None)
    auxiliary = []
    for model, trades in source['base_trades'].items():
        requirements = REGISTRY[model].get('data_requirements', [])
        external = [name for name in requirements if 'daily' in name or 'partner' in name]
        if not trades and external:
            auxiliary.append({'model': model, 'declared_external_requirements': external,
                              'coverage': REGISTRY[model].get('coverage'),
                              'note': 'No matching daily/partner history was supplied by this single-series research context; not a demonstrated economic failure.'})
    return {'type': 'RETROSPECTIVE_CAUSAL_REGIME_ATTRIBUTION', 'qualified': False,
            'execution_authority': False, 'live_changes': False, 'orders_sent': 0,
            'symbol': 'EURUSD', 'timeframe': 'H1', 'models': len(rows),
            'trade_records': len(records), 'commission_usd_round_trip_per_lot': 7.,
            'slippage_points_per_side': 10, 'spread_policy': 'Unchanged archived native-row spread',
            'data_sha256': native_sha256, 'source_report_sha256': source_report_sha256,
            'source_replay_sha256': source['repricing_proof_source_sha256'],
            'regime_config': REGIME_CONFIG,
            'native_span': {'first_open_utc': datetime.fromtimestamp(first, UTC).isoformat(),
                            'last_close_utc': datetime.fromtimestamp(last, UTC).isoformat(),
                            'elapsed_calendar_days': (last - first) / 86400,
                            'approximate_calendar_months': (last - first) / 86400 / 30.436875,
                            'bars': len(bars), 'calendar_segments': len(segments),
                            'segments_with_archived_trades': sorted({t['segment'] for t in records})},
            'archived_trade_span': {
                'first_entry_utc': datetime.fromtimestamp(first_trade, UTC).isoformat() if first_trade else None,
                'last_exit_utc': datetime.fromtimestamp(last_trade, UTC).isoformat() if last_trade else None,
                'elapsed_calendar_days': (last_trade - first_trade) / 86400 if first_trade else None},
            'aggregate_model_trade_regimes': aggregate,
            'aggregate_model_trade_direction_regimes': direction_groups,
            'existing_context_not_replaced': {
                'specialist_models_with_declared_regime_scope': len(SPECS),
                'specialist_models_with_archived_trades': sum(bool(source['base_trades'].get(model)) for model in SPECS),
                'original_classifier': 'specialists.regime: prior-only efficiency20; TREND>=.45, RANGE<=.25, else MIXED; ATR ratio>=2 HIGH_VOLATILITY; UNKNOWN before41 prior bars.',
                'original_gate': 'strategies.analyze_strategy enforces SPECS.allowed_regimes for specialist models.',
                'training_filter': 'quant.replay already requires current ATR between0.25 and4 times the frozen training ATR median.',
                'this_classifier': 'Independent EMA-gap/slope diagnostic; its RANGE is a residual NON_DIRECTIONAL bucket and is not equivalent to specialists RANGE; it includes mixed/high-volatility states.',
                'nontraded_models_requiring_external_context': auxiliary},
            'rows': rows, 'annotations': records,
            'limitations': [
                'Exploratory attribution after model selection; no regime edge or significance inference.',
                'Fixed diagnostic thresholds are not a trained predictor or a preregistered investment rule.',
                'Only complete candles closing strictly before entry are used; exact entry-boundary close excluded.',
                'EMA20/EMA50 use an SMA seed in the final 60 within-segment candles; ATR14 is a simple mean.',
                'RANGE is a residual NON_DIRECTIONAL bucket: it includes mixed/high-volatility states; it is not the original specialists RANGE and not proof of a tradable price range.',
                'Archived trades already used a training ATR envelope; models are not uniformly context-free.',
                'No prices, trades, side, entry rules, exit rules, costs or live weights are changed.',
                'Model trades across different models overlap and do not form an independent portfolio.',
                'Native source and fixed research calendar are not independently broker-session authenticated.',
                'Ledger fingerprints and arithmetic checked; historical fills are not independently regenerated.',
            ]}


def markdown(report):
    lines = ['# Retrospective causal regime diagnostics', '',
             'Qualified: false. USD7/lot round trip, ten-point per-side slippage and archived row spreads unchanged.',
             '', json.dumps(report['native_span'], indent=2), '',
             json.dumps(report['archived_trade_span'], indent=2), '',
             '| model | trades | long | short | UP n | UP win% | UP net R | DOWN n | DOWN win% | DOWN net R | RANGE n | RANGE win% | RANGE net R | UNKNOWN n | UNKNOWN net R | total net R |',
             '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for row in report['rows']:
        cells = [row['model'], row['trades'], row['long_trades'], row['short_trades']]
        for name in ('UP', 'DOWN', 'RANGE'):
            group = row['regimes'][name]
            cells.extend([group['trades'], '-' if group['win_rate'] is None else f"{100 * group['win_rate']:.2f}", f"{group['net_r']:.6f}"])
        cells.extend([row['regimes']['UNKNOWN']['trades'],
                      f"{row['regimes']['UNKNOWN']['net_r']:.6f}", f"{row['net_r']:.6f}"])
        lines.append('| ' + ' | '.join(map(str, cells)) + ' |')
    lines.extend(['', '## Existing strategy context is retained', '',
                  json.dumps(report['existing_context_not_replaced'], indent=2), '',
                  '## Fixed independent regime rule', '', json.dumps(report['regime_config'], indent=2), '',
                  '## Limitations', '', *('- ' + row for row in report['limitations'])])
    return '\n'.join(lines) + '\n'


def main():
    from edge_test import load_native

    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=ROOT / 'reports/preliminary-H1.json')
    parser.add_argument('--csv', type=Path, default=ROOT / 'data/real/H1/EURUSD_H1.csv')
    parser.add_argument('--output', type=Path, default=ROOT / 'reports/regime-diagnostics.json')
    args = parser.parse_args()
    raw = args.source.read_bytes()
    source = json.loads(raw.decode('utf-8'))
    bars, _, digest = load_native(args.csv, source['declared_provenance'], time.time(), preliminary=True)
    report = diagnose(bars, source, native_sha256=digest,
                      source_report_sha256=hashlib.sha256(raw).hexdigest())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    args.output.with_suffix('.md').write_text(markdown(report), encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items()
                      if key not in ('rows', 'annotations', 'limitations')}, indent=2))


if __name__ == '__main__':
    main()
