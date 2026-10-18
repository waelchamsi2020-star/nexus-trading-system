"""Long rolling research with unique chronological OOS book and gap censoring.

Signals are unchanged cards from nexus.strategies. The rolling training median
is fitted only from within-segment, training-only ATR windows. Unknown data
gaps reset features and censor unidentifiable fills/exits, never invent an exit
at the price before a gap. Independent episodes after censoring are explicitly
conditional; no research report grants trading authority.
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from nexus.segment_research import summarize
from nexus.strategies import REGISTRY
from nexus.timeframes import bar_close_time


def schedule(count, *, train, test, step, embargo=24, offset=0):
    if any(type(x) is not int or x <= 0 for x in (count, train, test, step, embargo)):
        raise ValueError('Positive integer window dimensions required')
    if embargo < 24 or step > test:
        raise ValueError('Embargo >=24 and step <= test required')
    return [{'fold_id': index, 'train_start': offset + start - embargo - train,
             'train_end': offset + start - embargo, 'test_start': offset + start,
             'test_end': offset + start + test}
            for index, start in enumerate(range(train + embargo, count - test + 1, step))]


def fit_baselines(cache, folds):
    starts, values = cache['segment_starts'], cache['atr_values']
    result = []
    for fold in folds:
        valid = [values[i] for i in range(fold['train_start'] + 14, fold['train_end'])
                 if i - starts[i] >= 14 and values[i] > 0]
        result.append({**fold, 'training_atr_median': statistics.median(valid) if valid else None,
                       'training_atr_windows': len(valid)})
    return result


def _fee_price(trade, fee, specification):
    if specification['profit_currency'] == 'USD':
        conversion = 1.
    elif specification['profit_currency'] == 'JPY' and specification['symbol'] == 'USDJPY':
        conversion = trade['exit']
    else:
        raise ValueError('No supported historical USD/profit-currency conversion')
    return fee * conversion / specification['contract_size']


def price_trades(trades, fee, specification):
    if not math.isfinite(fee) or fee < 0:
        raise ValueError('Finite nonnegative fee required')
    result = []
    for trade in trades:
        commission = _fee_price(trade, fee, specification)
        net = trade['gross_price_pnl'] - commission
        risk = abs(trade['entry'] - trade['stop'])
        result.append({**trade, 'commission_price_units': commission,
                       'net_price_pnl': net, 'r': net / risk})
    return result


def replay_book(cache, model, folds, *, start, end, fixed_fold=None):
    """Single-position book; a current position survives rolling-fold updates.

    After unknown intrabar history the exposure is unidentifiable, so the
    position has R=None and the following segment begins a conditional episode.
    No claim is made that a broker closed that position at the censor time.
    """
    bars, segment = cache['bars'], cache['segment_starts']
    point = cache['specification']['point']
    slip = 10 * point
    candidates = cache['cards'][model]
    indices = [row['index'] for row in candidates]
    fold_starts = [row['test_start'] for row in folds]
    closed, censored, rejected = [], [], []
    cursor = start
    while cursor < end - 1:
        candidate_pos = bisect.bisect_left(indices, cursor)
        if candidate_pos >= len(indices) or indices[candidate_pos] >= end - 1:
            break
        signal_i = indices[candidate_pos]
        card = candidates[candidate_pos]['card']
        owner = fixed_fold if fixed_fold is not None else bisect.bisect_right(fold_starts, signal_i) - 1
        if owner < 0:
            cursor = signal_i + 1
            continue
        fold = folds[owner]
        baseline = fold['training_atr_median']
        if baseline is None or not .25 * baseline <= cache['atr_values'][signal_i] <= 4 * baseline:
            rejected.append({'signal_index': signal_i, 'fold_id': fold['fold_id'], 'reason': 'TRAINING_ATR_ENVELOPE'})
            cursor = signal_i + 1
            continue
        fill_i = signal_i + 1
        common = {'strategy_id': model, 'symbol': cache['symbol'], 'timeframe': cache['timeframe'],
                  'fold_id': fold['fold_id'], 'signal_index': signal_i,
                  'signal_time': bar_close_time(bars[signal_i]['time'], cache['timeframe']),
                  'entry_index': fill_i, 'entry_time': bars[fill_i]['time'], 'side': card['direction']}
        if segment[fill_i] != segment[signal_i]:
            censored.append({**common, 'state': 'UNOBSERVED_ENTRY', 'r': None,
                             'reason': 'Unexpected source gap between completed signal and next observed open'})
            cursor = fill_i
            continue
        side = card['direction']
        spread = bars[fill_i].get('spread', 0) * point
        entry = bars[fill_i]['open'] + spread + slip if side == 'BUY' else bars[fill_i]['open'] - slip
        stop, target = card['stop']['price'], card['targets'][0]['price']
        stop = round((math.floor(stop / point) if side == 'BUY' else math.ceil(stop / point)) * point, 10)
        target = round((math.ceil(target / point) if side == 'BUY' else math.floor(target / point)) * point, 10)
        zone = card['entry'].get('zone', [0, math.inf])
        bracket = stop < entry < target if side == 'BUY' else target < entry < stop
        if not zone[0] <= entry <= zone[1] or not bracket:
            rejected.append({'signal_index': signal_i, 'fold_id': fold['fold_id'],
                             'reason': 'NEXT_OPEN_GAP_COST_ZONE_OR_BRACKET'})
            cursor = signal_i + 1
            continue
        hold = min(12, (card.get('execution_plan') or {}).get('max_hold_bars', 12))
        if type(hold) is not int or hold < 1:
            raise ValueError('Invalid unchanged hold policy')
        last_i = min(fill_i + hold - 1, end - 1)
        exit_price, exit_reason, exit_i, ambiguous = None, None, last_i, False
        censor_i = None
        invalidation = (card.get('invalidation') or {}).get('price')
        for j in range(fill_i, last_i + 1):
            if j > fill_i and segment[j] != segment[j - 1]:
                censor_i = j
                break
            bar = bars[j]
            bar_spread = bar.get('spread', 0) * point
            stop_hit = bar['low'] <= stop if side == 'BUY' else bar['high'] + bar_spread >= stop
            target_hit = bar['high'] >= target if side == 'BUY' else bar['low'] + bar_spread <= target
            if stop_hit:
                exit_price = min(stop, bar['open']) - slip if side == 'BUY' else max(stop, bar['open'] + bar_spread) + slip
                exit_reason, exit_i, ambiguous = 'STOP', j, bool(target_hit)
                break
            if target_hit:
                exit_price = target - slip if side == 'BUY' else target + slip
                exit_reason, exit_i = 'TARGET', j
                break
            if invalidation is not None and (bar['close'] < invalidation if side == 'BUY' else bar['close'] > invalidation):
                exit_reason, exit_i = 'INVALIDATION_NEXT_OPEN', j + 1
                if exit_i < end:
                    if segment[exit_i] != segment[j]:
                        censor_i = exit_i
                    else:
                        following = bars[exit_i]
                        exit_price = min(following['open'], target) - slip if side == 'BUY' else max(following['open'] + following.get('spread', 0) * point, target) + slip
                else:
                    exit_i, exit_reason = j, 'FOLD_BOUNDARY'
                    exit_price = bar['close'] - slip if side == 'BUY' else bar['close'] + bar_spread + slip
                break
        if censor_i is None and exit_price is None:
            if last_i + 1 < end and last_i == fill_i + hold - 1:
                exit_i, exit_reason = last_i + 1, 'TIME_NEXT_OPEN'
                if segment[exit_i] != segment[last_i]:
                    censor_i = exit_i
                else:
                    bar = bars[exit_i]
                    exit_price = min(bar['open'], target) - slip if side == 'BUY' else max(bar['open'] + bar.get('spread', 0) * point, target) + slip
            else:
                exit_i, exit_reason = last_i, 'FOLD_BOUNDARY'
                bar = bars[exit_i]
                exit_price = bar['close'] - slip if side == 'BUY' else bar['close'] + bar.get('spread', 0) * point + slip
        filled = {**common, 'entry': entry, 'stop': stop, 'target': target}
        if censor_i is not None:
            censored.append({**filled, 'state': 'CENSORED_MISSING_INTRABAR', 'r': None,
                             'censor_time': bars[censor_i]['time'], 'last_observed_index': censor_i - 1,
                             'reason': 'No exit price invented; subsequent data segment is a separate conditional episode'})
            cursor = censor_i
            continue
        gross = exit_price - entry if side == 'BUY' else entry - exit_price
        closed.append({**filled, 'exit_index': exit_i, 'exit': exit_price,
                       'exit_time': bars[exit_i]['time'] if exit_reason.endswith('NEXT_OPEN') else bar_close_time(bars[exit_i]['time'], cache['timeframe']),
                       'gross_price_pnl': gross, 'commission_price_units': 0., 'net_price_pnl': gross,
                       'r': gross / abs(entry - stop), 'exit_reason': exit_reason,
                       'ambiguous_bar': ambiguous})
        cursor = exit_i + 1
    return {'trades': closed, 'censored': censored, 'rejected': rejected}


def run_study(cache, *, train, test, step, embargo=24, model_ids=None, lo=0, hi=None):
    hi = len(cache['bars']) if hi is None else hi
    folds = fit_baselines(cache, schedule(hi - lo, train=train, test=test, step=step, embargo=embargo, offset=lo))
    models = sorted(REGISTRY if model_ids is None else model_ids)
    primary, fold_books = {}, {}
    for model in models:
        primary[model] = replay_book(cache, model, folds, start=folds[0]['test_start'], end=folds[-1]['test_end']) if folds else {'trades': [], 'censored': [], 'rejected': []}
        fold_books[model] = [replay_book(cache, model, folds, start=f['test_start'], end=f['test_end'], fixed_fold=i)
                             for i, f in enumerate(folds)]
        print(f"LONG_WF {cache['timeframe']} {model} closed={len(primary[model]['trades'])} censored={len(primary[model]['censored'])}", flush=True)
    scenarios = []
    for fee in (0., 3., 7.):
        rows = []
        for model in models:
            trades = price_trades(primary[model]['trades'], fee, cache['specification'])
            windows = [summarize(price_trades(book['trades'], fee, cache['specification'])) for book in fold_books[model]]
            rows.append({'model': model, **summarize(trades),
                         'censored': len(primary[model]['censored']),
                         'entered_observed': len(trades) + sum(x['state'] == 'CENSORED_MISSING_INTRABAR' for x in primary[model]['censored']),
                         'unobserved_entries': sum(x['state'] == 'UNOBSERVED_ENTRY' for x in primary[model]['censored']),
                         'profitable_windows': sum(x['trades'] > 0 and x['net_r'] > 0 for x in windows),
                         'total_windows': len(folds), 'window_metrics': windows, 'trade_records': trades})
        ranked = sorted([r for r in rows if r['trades'] >= 30], key=lambda r: (-r['net_r'], r['model']))
        positives = [r['model'] for r in ranked if r['net_r'] > 0]
        scenarios.append({'commission_usd_round_trip_per_lot': fee, 'models': rows,
                          'top5': [r['model'] for r in ranked[:5]], 'positive_models_n_ge_30': positives,
                          'verdict': 'PRELIMINARY_EDGE_FOUND' if positives else 'NO_EDGE_ON_AVAILABLE_HISTORY',
                          'verdict_scope': 'Observed closed conditional episodes only; censored exposures have unknown R and may invalidate inference'})
    return {'symbol': cache['symbol'], 'timeframe': cache['timeframe'], 'bars': hi - lo,
            'protocol': {'train': train, 'test': test, 'step': step, 'embargo': embargo,
                         'overlap': 'Full folds reported separately; never summed. Primary book uses most recently trained fold at each signal and carries its open position across fold updates.',
                         'gap': 'Features reset; training ATR never crosses a gap. Unobserved entry/exit is censored R=None; following segment starts a conditional episode.',
                         'costs': 'USD0/3/7 per lot round trip; adverse10 observed symbol points each side; row spread',
                         'ranking': 'Primary winner fixed before examining results: USD7 net R among models with >=30 observable closed trades.'},
            'folds': folds, 'scenarios': scenarios, 'primary_base_books': primary,
            'unused_tail_bars': hi - folds[-1]['test_end'] if folds else hi - lo,
            'source_data_sha256': cache['provenance']['csv_sha256'], 'cache_provenance': cache['provenance'],
            'qualified': False, 'execution_authority': False, 'live_changes': False,
            'limitations': ['Fixed-rule conditional OHLC replay, not actual broker fills or a portfolio',
                           'Overlap-fold results are dependent and not independent samples',
                           'Unknown intrabar exposures are retained separately and never assigned zero loss',
                           'Calendar is a declared unverified research assumption',
                           'Single-series input has no partner/daily model context',
                           'Original archive period and post-selection history are not a pristine future holdout']}


def write_study(report, output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    for scenario in report['scenarios']:
        fee = scenario['commission_usd_round_trip_per_lot']
        lines = [f"# {report['symbol']} {report['timeframe']}, commission USD{fee}/lot round trip", '',
                 'Observable closed trades only; censored exposures have unknown R. Fold profits are not summed.', '',
                 '| model | closed trades | win% | net R | trade Sharpe | max DD R | profitable windows | censored |',
                 '|---|---:|---:|---:|---:|---:|---:|---:|']
        for row in scenario['models']:
            win = '-' if row['win_rate'] is None else f"{100 * row['win_rate']:.2f}"
            sharpe = '-' if row['sharpe'] is None else f"{row['sharpe']:.6f}"
            lines.append(f"|{row['model']}|{row['trades']}|{win}|{row['net_r']:.6f}|{sharpe}|{row['max_dd']:.6f}|{row['profitable_windows']}/{row['total_windows']}|{row['censored']}|")
        lines += ['', 'TOP_5_MODELS: ' + ', '.join(scenario['top5']), scenario['verdict'], 'qualified=false; execution_authority=false.']
        output.with_name(output.stem + f'-fee-{int(fee)}.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def run_native(csv_path, metadata_path, output, workers=6, model_ids=None):
    from long_signal_cache import build_cache

    metadata = json.loads(Path(metadata_path).read_text(encoding='utf-8'))
    tf = metadata['timeframe']
    if tf not in ('M5', 'H1'):
        raise ValueError('Long-history protocol supports native M5/H1 only')
    if metadata.get('source') != 'MT5_NATIVE' or metadata.get('aggregated') is not False:
        raise ValueError('Native, unaggregated MT5 source required')
    fingerprint = hashlib.sha256(Path(csv_path).read_bytes()).hexdigest()
    if metadata.get('csv_sha256') != fingerprint:
        raise ValueError('Native metadata CSV fingerprint mismatch')
    train, test, step = (5000, 1000, 500) if tf == 'H1' else (20000, 5000, 2500)
    cache = build_cache(csv_path, symbol=metadata['symbol'], timeframe=tf, point=metadata['point'],
                        profile=metadata.get('calendar_profile', 'CONTINUOUS'),
                        cache_dir=ROOT / 'reports/long-study-cache', workers=workers,
                        start_index=train + 24, model_ids=model_ids)
    cache['symbol'], cache['timeframe'] = metadata['symbol'], tf
    cache['specification'] = {'point': metadata['point'], 'contract_size': metadata['contract_size'],
                              'profit_currency': metadata['profit_currency'], 'symbol': metadata['symbol']}
    if not schedule(len(cache['bars']), train=train, test=test, step=step):
        raise ValueError('Insufficient original history for a full declared train/embargo/test fold')
    report = run_study(cache, train=train, test=test, step=step, model_ids=model_ids)
    report.update(native_csv_sha256=fingerprint, declared_native_metadata=metadata,
                  replay_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  actual_commission_known=metadata.get('commission_known') is True)
    write_study(report, output)
    print(json.dumps({'timeframe': tf, 'folds': len(report['folds']), 'output': str(output),
                      'fee7_top5': report['scenarios'][-1]['top5']}, indent=2))
    return report, cache


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', type=Path, required=True)
    parser.add_argument('--metadata', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=6)
    parser.add_argument('--model', nargs='+')
    args = parser.parse_args()
    run_native(args.csv, args.metadata, args.output, args.workers, args.model)


if __name__ == '__main__':
    main()
