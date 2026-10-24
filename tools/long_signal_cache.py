"""Resumable causal signal precomputation; no replay or broker authority.

Only unchanged READY/IMPLEMENTED execution fields are retained. Every decision
uses at most 300 already completed candles from its own calendar-aware segment.
Training ATR envelopes and walk-forward ownership remain the caller's task.
Use the CLI or a protected ``if __name__ == '__main__'`` when workers > 1 on
Windows. Chunk files are gzip JSON, committed by atomic replacement.
"""
from __future__ import annotations

import argparse
import copy
import csv
import gzip
import hashlib
import json
import math
import os
import sys
import time
import uuid
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import UTC, datetime
from multiprocessing import get_context
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from nexus.strategies import REGISTRY, analyze_all, analyze_strategy, atr, validate_bars
from nexus.timeframes import PERIODS, bar_close_time
from nexus.trading_calendar import expected_closure_gap, validate_profile
from nexus.walkforward import LookaheadBiasError

CACHE_VERSION = 'causal-shared-signals-1.0.0'
CHUNK_SIZE = 128
EXECUTION_FIELDS = ('status', 'coverage', 'direction', 'entry', 'stop', 'targets',
                    'invalidation', 'execution_plan')
_WORK = None


def _encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def load_csv(path, timeframe, as_of=None):
    """Parse an actual native MT5 export; no commission metadata is invented."""
    if timeframe not in ('M5', 'H1', 'H4', 'D1'):
        raise ValueError('This 300-bar cache supports native M5/H1/H4/D1 only')
    observation_time = time.time() if as_of is None else as_of
    if (isinstance(observation_time, bool) or not isinstance(observation_time, (int, float)) or
            not math.isfinite(observation_time)):
        raise ValueError('Finite observation time required')
    blob = Path(path).read_bytes()
    text = blob.decode('utf-8-sig')
    dialect = csv.Sniffer().sniff(text[:4096], delimiters=',\t;')
    reader = csv.DictReader(text.splitlines(), dialect=dialect)
    required = {'<DATE>', '<TIME>', '<OPEN>', '<HIGH>', '<LOW>', '<CLOSE>', '<TICKVOL>', '<SPREAD>'}
    if not required <= set(reader.fieldnames or []):
        raise ValueError('Native MT5 CSV columns missing')
    bars = []
    for row in reader:
        stamp = datetime.strptime(row['<DATE>'] + ' ' + row['<TIME>'], '%Y.%m.%d %H:%M:%S').replace(tzinfo=UTC)
        bars.append({'time': int(stamp.timestamp()),
                     **{key: float(row['<' + key.upper() + '>']) for key in ('open', 'high', 'low', 'close')},
                     'tick_volume': int(row['<TICKVOL>']), 'spread': int(row['<SPREAD>']),
                     'real_volume': int(row.get('<VOL>') or 0)})
    if not bars:
        raise ValueError('Native export contains no candles')
    if any(bar_close_time(row['time'], timeframe) > observation_time for row in bars):
        raise LookaheadBiasError('Native CSV contains a future or incomplete candle')
    validate_bars(bars, timeframe, observation_time)
    return bars, hashlib.sha256(blob).hexdigest()


def segment_arrays(bars, timeframe, profile):
    """Causal segment start and arithmetic ATR14, including partial warmup ATR."""
    validate_profile(profile)
    starts, values = [], []
    start = 0
    for index, row in enumerate(bars):
        if index:
            close = bar_close_time(bars[index - 1]['time'], timeframe)
            if (close != row['time'] and not expected_closure_gap(
                    close, row['time'], PERIODS[timeframe], profile)):
                start = index
        starts.append(start)
        values.append(atr(bars[max(start, index - 14):index + 1]))
    return starts, values


def source_fingerprint():
    """Freeze all local engine sources/configuration plus this cache algorithm."""
    files = sorted([*Path(ROOT / 'src/nexus').rglob('*.py'),
                    *(p for p in (ROOT / 'src/nexus/config').rglob('*') if p.is_file())])
    hasher = hashlib.sha256()
    for path in files:
        hasher.update(str(path.relative_to(ROOT)).replace('\\', '/').encode())
        hasher.update(b'\0')
        hasher.update(path.read_bytes())
        hasher.update(b'\0')
    hasher.update(Path(__file__).read_bytes())
    return hasher.hexdigest()


def compact_card(card):
    if (card.get('status') != 'READY' or card.get('coverage') != 'IMPLEMENTED' or
            not (card.get('entry') or {}).get('triggered')):
        return None
    return {key: copy.deepcopy(card.get(key)) for key in EXECUTION_FIELDS}


def _atomic_gzip(path, payload):
    path = Path(path)
    temporary = path.with_name(path.name + f'.pending.{os.getpid()}.{uuid.uuid4().hex}')
    try:
        with temporary.open('xb') as stream:
            with gzip.GzipFile(fileobj=stream, mode='wb', mtime=0) as archive:
                archive.write(_encoded(payload))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _read_chunk(path, cache_key, start, end, model_ids):
    try:
        with gzip.open(path, 'rb') as stream:
            envelope = json.loads(stream.read().decode('utf-8'))
        payload = envelope['payload']
        if (envelope.get('sha256') != hashlib.sha256(_encoded(payload)).hexdigest() or
                payload.get('cache_key') != cache_key or payload.get('start') != start or
                payload.get('end') != end or set(payload['cards']) != set(model_ids) or
                set(payload['status_counts']) != set(model_ids)):
            return None
        for model in model_ids:
            if sum(payload['status_counts'][model].values()) != end - start:
                return None
            indices = [row['index'] for row in payload['cards'][model]]
            if indices != sorted(set(indices)) or any(not start <= i < end for i in indices):
                return None
            if any(compact_card(row['card']) != row['card'] for row in payload['cards'][model]):
                return None
        return payload
    except (OSError, EOFError, ValueError, KeyError, TypeError):
        return None


def _initialize_worker(csv_path, spec):
    global _WORK
    bars, digest = load_csv(csv_path, spec['timeframe'], spec['as_of'])
    if digest != spec['csv_sha256'] or source_fingerprint() != spec['source_sha256']:
        raise RuntimeError('Native data or source changed before signal worker started')
    starts, _ = segment_arrays(bars, spec['timeframe'], spec['profile'])
    _WORK = {'bars': bars, 'starts': starts, 'spec': spec}


def _compute_chunk(job):
    start, end, target, cache_key = job
    bars, starts, spec = _WORK['bars'], _WORK['starts'], _WORK['spec']
    models = spec['model_ids']
    cards = {model: [] for model in models}
    counts = {model: Counter() for model in models}
    context = {'tick_size': spec['point'], 'data_kind': 'broker', 'calendar_profile': spec['profile']}
    all_models = set(models) == set(REGISTRY)
    for index in range(start, end):
        history = bars[max(starts[index], index + 1 - 300):index + 1]
        decision_time = bar_close_time(history[-1]['time'], spec['timeframe'])
        if all_models:
            results = analyze_all(spec['symbol'], spec['timeframe'], history, decision_time, context)
        else:
            results = [analyze_strategy(model, spec['symbol'], spec['timeframe'], history, decision_time, context)
                       for model in models]
        for card in results:
            model = card['strategy_id']
            counts[model][card['status']] += 1
            execution = compact_card(card)
            if execution is not None:
                cards[model].append({'index': index, 'card': execution})
    payload = {'cache_key': cache_key, 'start': start, 'end': end, 'cards': cards,
               'status_counts': {model: dict(counts[model]) for model in models}}
    _atomic_gzip(target, {'payload': payload, 'sha256': hashlib.sha256(_encoded(payload)).hexdigest()})
    return start, end


def build_cache(csv_path, *, symbol, timeframe, point, profile, cache_dir,
                workers=6, start_index=0, model_ids=None):
    """Return native bars, causal arrays, compact cards and resumable provenance."""
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError('Explicit symbol required')
    if isinstance(point, bool) or not isinstance(point, (int, float)) or not math.isfinite(point) or point <= 0:
        raise ValueError('Positive finite observed point required')
    if type(workers) is not int or not 1 <= workers <= 64:
        raise ValueError('workers must be an integer from1to64')
    if type(start_index) is not int or start_index < 0:
        raise ValueError('Nonnegative integer start_index required')
    validate_profile(profile)
    models = sorted(REGISTRY) if model_ids is None else sorted(model_ids)
    if not models or len(models) != len(set(models)) or not set(models) <= set(REGISTRY):
        raise ValueError('Unique known model_ids required')
    as_of = time.time()
    bars, csv_sha = load_csv(csv_path, timeframe, as_of)
    if start_index > len(bars):
        raise ValueError('start_index exceeds native history')
    starts, atr_values = segment_arrays(bars, timeframe, profile)
    spec = {'cache_version': CACHE_VERSION, 'csv_sha256': csv_sha,
            'source_sha256': source_fingerprint(), 'symbol': symbol, 'timeframe': timeframe,
            'point': point, 'profile': profile, 'model_ids': models, 'start_index': start_index,
            'lookback_bars': 300, 'python_version': list(sys.version_info[:3])}
    cache_key = hashlib.sha256(_encoded(spec)).hexdigest()
    spec['as_of'] = as_of
    directory = Path(cache_dir).resolve() / cache_key
    directory.mkdir(parents=True, exist_ok=True)
    jobs, available = [], []
    for start in range(start_index, len(bars), CHUNK_SIZE):
        end = min(start + CHUNK_SIZE, len(bars))
        target = directory / f'{start:09d}-{end:09d}.json.gz'
        if _read_chunk(target, cache_key, start, end, models) is not None:
            available.append((start, end, target))
        else:
            jobs.append((start, end, str(target), cache_key))
    reused = len(available)
    if jobs and workers == 1:
        _initialize_worker(str(Path(csv_path).resolve()), spec)
        for job in jobs:
            start, end = _compute_chunk(job)
            available.append((start, end, Path(job[2])))
    elif jobs:
        with ProcessPoolExecutor(max_workers=workers, mp_context=get_context('spawn'),
                                 initializer=_initialize_worker,
                                 initargs=(str(Path(csv_path).resolve()), spec)) as pool:
            futures = {pool.submit(_compute_chunk, job): job for job in jobs}
            for future in as_completed(futures):
                start, end = future.result()
                available.append((start, end, Path(futures[future][2])))
                print(json.dumps({'type': 'SIGNAL_CACHE_CHUNK', 'timeframe': timeframe,
                                  'start': start, 'end': end,
                                  'completed_chunks': len(available),
                                  'total_chunks': reused + len(jobs)}), flush=True)
    if source_fingerprint() != spec['source_sha256'] or hashlib.sha256(Path(csv_path).read_bytes()).hexdigest() != csv_sha:
        raise RuntimeError('Source or native CSV changed during signal precomputation')
    cards = {model: [] for model in models}
    status_counts = {model: Counter() for model in models}
    for start, end, target in sorted(available):
        payload = _read_chunk(target, cache_key, start, end, models)
        if payload is None:
            raise RuntimeError('Signal chunk failed post-write integrity validation: ' + str(target))
        for model in models:
            cards[model].extend(payload['cards'][model])
            status_counts[model].update(payload['status_counts'][model])
    provenance = {**{key: value for key, value in spec.items() if key != 'as_of'},
                  'cache_key': cache_key, 'cache_directory': str(directory),
                  'bar_count': len(bars), 'decision_bars': len(bars) - start_index,
                  'chunks': len(available), 'chunks_reused': reused,
                  'chunks_computed': len(jobs), 'workers': workers,
                  'qualified': False, 'execution_authority': False, 'live_changes': False,
                  'method': 'Unchanged per-model completed-candle analysis; no execution, training fit or gap crossing',
                  'limitation': 'READY cards are proposals only; caller must apply fold-owned ATR, costs, causal fills and position state.'}
    _atomic_gzip(directory / 'manifest.json.gz', {'provenance': provenance})
    return {'bars': bars, 'segment_starts': starts, 'atr_values': atr_values,
            'cards': cards, 'status_counts': {model: dict(counts) for model, counts in status_counts.items()},
            'provenance': provenance}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, required=True)
    parser.add_argument('--timeframe', choices=('M5', 'H1', 'H4', 'D1'), required=True)
    parser.add_argument('--symbol', required=True)
    parser.add_argument('--point', type=float, required=True)
    parser.add_argument('--profile', default='CONTINUOUS')
    parser.add_argument('--cache-dir', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=6)
    parser.add_argument('--start-index', type=int, default=0)
    parser.add_argument('--models', nargs='+')
    args = parser.parse_args()
    result = build_cache(args.csv, symbol=args.symbol, timeframe=args.timeframe,
                         point=args.point, profile=args.profile, cache_dir=args.cache_dir,
                         workers=args.workers, start_index=args.start_index, model_ids=args.models)
    print(json.dumps({'provenance': result['provenance'],
                      'ready_cards': {model: len(cards) for model, cards in result['cards'].items()},
                      'status_counts': result['status_counts']}, indent=2))


if __name__ == '__main__':
    main()
