"""Three fresh equal-calendar H1 replays of the fixed fee-seven selected model.

This reuses a complete authenticated local signal cache. It never creates price
data, repairs missing chunks, chooses another fee, tunes a rule or enables
execution. The historical archive/model selection was already inspected.
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import itertools
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))
from long_walkforward import run_study

from nexus.strategies import REGISTRY
from nexus.timeframes import bar_close_time

TRAIN, TEST, STEP, EMBARGO = 5000, 1000, 500, 24


def select_fixed_fee7_best(study):
    scenarios = [s for s in study.get('scenarios', []) if s.get('commission_usd_round_trip_per_lot') == 7.]
    if len(scenarios) != 1:
        raise ValueError('Exactly one fixed USD7 primary scenario required')
    scenario = scenarios[0]
    rows = scenario.get('models', [])
    if any(not isinstance(row, dict) or row.get('model') not in REGISTRY or
           type(row.get('trades')) is not int or row['trades'] < 0 or
           isinstance(row.get('net_r'), bool) or not isinstance(row.get('net_r'), (int, float)) or
           not math.isfinite(row['net_r']) for row in rows):
        raise ValueError('Finite known-model fee-seven ranking rows required')
    if len({row['model'] for row in rows}) != len(rows):
        raise ValueError('Duplicate models in primary ranking')
    ranked = sorted((row for row in rows if row['trades'] >= 30), key=lambda row: (-row['net_r'], row['model']))
    expected = [row['model'] for row in ranked[:5]]
    if scenario.get('top5') != expected:
        raise ValueError('Recorded top5 disagrees with fixed fee-seven netR/minimum30 ranking')
    return expected[0] if expected else None


def calendar_slices(bars, timeframe='H1'):
    if not bars:
        raise ValueError('Actual chronological candles required')
    times = [row['time'] for row in bars]
    if any(isinstance(stamp, bool) or not isinstance(stamp, (int, float)) or
           not math.isfinite(stamp) for stamp in times) or any(b <= a for a, b in itertools.pairwise(times)):
        raise ValueError('Finite strictly chronological candle timestamps required')
    start, end = times[0], bar_close_time(times[-1], timeframe)
    boundaries = [start + (end - start) * index / 3 for index in range(4)]
    rows = []
    for index in range(3):
        lo = bisect.bisect_left(times, boundaries[index])
        hi = bisect.bisect_left(times, boundaries[index + 1])
        rows.append({'period': index + 1, 'calendar_start': boundaries[index],
                     'calendar_end': boundaries[index + 1], 'lo': lo, 'hi': hi,
                     'bars': hi - lo,
                     'first_candle_open': times[lo] if lo < hi else None,
                     'last_candle_close': bar_close_time(times[hi - 1], timeframe) if lo < hi else None})
    return rows


def evaluate_temporal(cache, study):
    if cache.get('timeframe') != 'H1' or study.get('timeframe') != 'H1':
        raise ValueError('Fixed temporal protocol requires H1')
    if cache.get('symbol') != study.get('symbol'):
        raise ValueError('Study/cache symbol mismatch')
    cache_hash = cache['provenance'].get('csv_sha256')
    if not cache_hash or study.get('source_data_sha256') != cache_hash:
        raise ValueError('Study/cache native data fingerprint mismatch')
    lookback = cache['provenance'].get('lookback_bars')
    if type(lookback) is not int or not 1 <= lookback <= 300:
        raise ValueError('Verified causal lookback at most300 required')
    selected = select_fixed_fee7_best(study)
    periods = calendar_slices(cache['bars'], 'H1')
    results = []
    for period in periods:
        common = {**period, 'model': selected, 'commission_usd_round_trip_per_lot': 7.,
                  'slippage_points_per_side': 10, 'fresh_replay': selected is not None and period['bars'] > 0}
        if selected is None or period['bars'] == 0:
            results.append({**common, 'status': 'NO_ELIGIBLE_SELECTED_MODEL' if selected is None else 'EMPTY_CALENDAR_PERIOD',
                            'folds': 0, 'trades': 0, 'net_r': None, 'win_rate': None,
                            'sharpe': None, 'max_dd': None, 'censored': 0,
                            'positive_observed': False, 'positive_n_ge_30': False})
            continue
        # A separate call creates a new position book and training fits. The
        # first signal is lo+5024, so its <=300-bar feature history cannot read
        # the previous calendar period. No filtering of old trade outcomes.
        replayed = run_study(cache, train=TRAIN, test=TEST, step=STEP, embargo=EMBARGO,
                             model_ids=[selected], lo=period['lo'], hi=period['hi'])
        scenario = next(s for s in replayed['scenarios'] if s['commission_usd_round_trip_per_lot'] == 7.)
        row = next(row for row in scenario['models'] if row['model'] == selected)
        for fold in replayed['folds']:
            if (fold['train_start'] < period['lo'] or fold['test_start'] - lookback + 1 < period['lo'] or
                    fold['train_end'] > fold['test_start'] - EMBARGO or fold['test_end'] > period['hi']):
                raise ValueError('A fitted/replayed fold crosses a calendar-period boundary')
        positive = row['trades'] > 0 and row['net_r'] > 0
        results.append({**common, 'status': 'FRESH_CONDITIONAL_REPLAY' if replayed['folds'] else 'INSUFFICIENT_PERIOD_HISTORY',
                        **{key: row[key] for key in ('trades', 'net_r', 'win_rate', 'sharpe', 'max_dd', 'censored')},
                        'folds': len(replayed['folds']), 'fold_definitions': replayed['folds'],
                        'positive_observed': positive, 'positive_n_ge_30': positive and row['trades'] >= 30,
                        'fee7_trade_records': row['trade_records'],
                        'censored_records': replayed['primary_base_books'][selected]['censored'],
                        'unused_tail_bars': replayed['unused_tail_bars']})
    positive_count = sum(row['positive_n_ge_30'] for row in results)
    missing_exposure = sum(row['censored'] for row in results)
    return {'status': 'THREE_FRESH_CALENDAR_PERIODS_RETROSPECTIVE', 'selected_model': selected,
            'selection': 'Best fixed USD7 netR with minimum30 closed trades from original full-history study; no retuning',
            'symbol': cache['symbol'], 'timeframe': 'H1', 'source_data_sha256': cache_hash,
            'protocol': {'train': TRAIN, 'test': TEST, 'step': STEP, 'embargo': EMBARGO,
                         'periods': 'Three equal UTC elapsed-calendar-time bins, candles assigned by opening timestamp',
                         'book': 'Three separate engine run_study calls; no prior-period open position is carried',
                         'feature_guard': 'First signal >=period lo+5024; cached causal history <=300 bars',
                         'training_guard': 'Training-only ATR windows start at least14 candles after each period lo',
                         'boundary_rounding': 'Calendar cuts need not align to candle opens; adjacent index slices share no candle.'},
            'periods': results, 'positive_periods_n_ge_30': positive_count,
            'positive_at_least_two_of_three_n_ge_30': positive_count >= 2,
            'censored_exposures': missing_exposure,
            'temporal_pattern_gate': 'PASS_DESCRIPTIVE_PATTERN_ONLY' if positive_count >= 2 and not missing_exposure else 'NOT_PASSED',
            'qualified': False, 'execution_authority': False, 'live_changes': False,
            'selection_reuse': True, 'genuinely_unseen_out_of_sample': False,
            'limitations': ['The same historical archive already informed model selection; fresh replay is not unseen future data.',
                           'Positive two-of-three is descriptive stability, not statistical significance or a qualified edge.',
                           'Censored positions have unknown R and can overturn results; no zero-loss substitution.',
                           'Each period needs its own5000 training+24 embargo+1000 test bars; short/empty periods are explicit.',
                           'Native spread and ten-point per-side slippage unchanged; USD7 fee remains a hypothetical sensitivity.',
                           'Calendar profile is an unverified research assumption; no synthetic candles or gap bridging.']}


def load_complete_cache(csv_path, metadata, study):
    """Reject incomplete/stale caches before build_cache can compute any work."""
    import long_signal_cache as signals

    fingerprint = hashlib.sha256(Path(csv_path).read_bytes()).hexdigest()
    if metadata.get('source') != 'MT5_NATIVE' or metadata.get('aggregated') is not False or metadata.get('timeframe') != 'H1':
        raise ValueError('Native, nonaggregated H1 metadata required')
    if metadata.get('csv_sha256') != fingerprint or study.get('source_data_sha256') != fingerprint:
        raise ValueError('Native CSV/study/metadata fingerprint mismatch')
    previous = study['cache_provenance']
    if (previous.get('csv_sha256') != fingerprint or previous.get('source_sha256') != signals.source_fingerprint() or
            previous.get('start_index') != TRAIN + EMBARGO or set(previous.get('model_ids', [])) != set(REGISTRY) or
            previous.get('symbol') != metadata.get('symbol') or previous.get('timeframe') != 'H1' or
            previous.get('point') != metadata.get('point') or
            previous.get('profile') != metadata.get('calendar_profile', 'CONTINUOUS') or
            previous.get('cache_version') != signals.CACHE_VERSION or
            previous.get('python_version') != list(sys.version_info[:3]) or previous.get('lookback_bars') != 300):
        raise ValueError('A complete current-source all-model H1 cache is required')
    spec = {key: previous[key] for key in ('cache_version', 'csv_sha256', 'source_sha256', 'symbol',
            'timeframe', 'point', 'profile', 'model_ids', 'start_index', 'lookback_bars', 'python_version')}
    if hashlib.sha256(signals._encoded(spec)).hexdigest() != previous.get('cache_key'):
        raise ValueError('Cache key/provenance disagree; no signal recomputation performed')
    directory = Path(previous['cache_directory'])
    for start in range(TRAIN + EMBARGO, previous['bar_count'], signals.CHUNK_SIZE):
        end = min(start + signals.CHUNK_SIZE, previous['bar_count'])
        path = directory / f'{start:09d}-{end:09d}.json.gz'
        if signals._read_chunk(path, previous['cache_key'], start, end, sorted(REGISTRY)) is None:
            raise RuntimeError('Signal cache missing/corrupt; no recomputation performed: ' + str(path))
    cache = signals.build_cache(csv_path, symbol=metadata['symbol'], timeframe='H1', point=metadata['point'],
                                 profile=metadata.get('calendar_profile', 'CONTINUOUS'),
                                 cache_dir=directory.parent, workers=1,
                                 start_index=TRAIN + EMBARGO, model_ids=None)
    if cache['provenance']['chunks_computed'] != 0:
        raise RuntimeError('Temporal validation unexpectedly computed signal chunks')
    cache['symbol'], cache['timeframe'] = metadata['symbol'], 'H1'
    cache['specification'] = {'point': metadata['point'], 'contract_size': metadata['contract_size'],
                              'profit_currency': metadata['profit_currency'], 'symbol': metadata['symbol']}
    return cache


def write_report(result, output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    lines = ['# Three fresh retrospective calendar-period replays', '',
             'Fixed selected model: ' + str(result['selected_model']), '',
             '| period | UTC calendar start | UTC calendar end | bars | folds | trades | win rate | net R | Sharpe | max DD R | censored | status |',
             '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for row in result['periods']:
        values = [row['period'], datetime.fromtimestamp(row['calendar_start'], UTC).isoformat(),
                  datetime.fromtimestamp(row['calendar_end'], UTC).isoformat(),
                  *(row[key] for key in ('bars', 'folds', 'trades', 'win_rate', 'net_r', 'sharpe', 'max_dd', 'censored', 'status'))]
        lines.append('| ' + ' | '.join(str(value) for value in values) + ' |')
    lines.extend(['', result['temporal_pattern_gate'], '', 'qualified=false; selection_reuse=true; unseen_OOS=false.', '',
                  *('- ' + limit for limit in result['limitations'])])
    output.with_suffix('.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study', type=Path, default=ROOT / 'reports/long-study/H1.json')
    parser.add_argument('--csv', type=Path, required=True)
    parser.add_argument('--metadata', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'reports/long-study/temporal.json')
    args = parser.parse_args()
    study = json.loads(args.study.read_text(encoding='utf-8'))
    metadata = json.loads(args.metadata.read_text(encoding='utf-8'))
    cache = load_complete_cache(args.csv, metadata, study)
    result = evaluate_temporal(cache, study)
    result.update(study_sha256=hashlib.sha256(args.study.read_bytes()).hexdigest(),
                  temporal_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  replay_source_sha256=hashlib.sha256((ROOT / 'tools/long_walkforward.py').read_bytes()).hexdigest())
    write_report(result, args.output)
    print(json.dumps({key: result[key] for key in ('selected_model', 'positive_periods_n_ge_30',
                                                  'censored_exposures', 'temporal_pattern_gate', 'qualified')}, indent=2))
    for row in result['periods']:
        print(json.dumps({key: row[key] for key in ('period', 'bars', 'folds', 'trades', 'net_r', 'sharpe', 'max_dd', 'censored', 'status')}))


if __name__ == '__main__':
    main()
