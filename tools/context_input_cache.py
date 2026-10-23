"""Verify and reuse unchanged five-year model cards for a context-only study.

Archived cards are admitted only after reconstructing their exact source hash
from Git and comparing every current model/helper byte. New context or veto
code cannot silently authorize a changed strategy to reuse the old signals.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))

import long_signal_cache as signals

from nexus.strategies import REGISTRY

BASELINE_COMMIT = 'b608e66d060d60d2774d37d313ea8acb5088c656'
ALLOWED_MODIFIED = frozenset({'src/nexus/engine.py', 'src/nexus/execution.py'})
ALLOWED_NEW = frozenset({'src/nexus/regime_router.py', 'src/nexus/config/routing.yaml',
                         'src/nexus/config/routing.schema.json',
                         'src/nexus/cross_asset_filter.py', 'src/nexus/session_filter.py',
                         'src/nexus/timeframe_filter.py', 'src/nexus/config/context_layers.json',
                         'src/nexus/config/context_layers.schema.json'})
SPEC_KEYS = ('cache_version', 'csv_sha256', 'source_sha256', 'symbol', 'timeframe',
             'point', 'profile', 'model_ids', 'start_index', 'lookback_bars', 'python_version')


def _git_blob(repo_root, commit, name):
    result = subprocess.run(['git', 'show', f'{commit}:{name}'], cwd=repo_root,
                            capture_output=True, check=False)
    if result.returncode:
        raise ValueError(f'Cannot reconstruct archived Git source: {name}')
    return result.stdout


def _tracked_source_names(repo_root, commit):
    result = subprocess.run(['git', 'ls-tree', '-r', '--name-only', commit, '--', 'src/nexus'],
                            cwd=repo_root, capture_output=True, check=False)
    if result.returncode:
        raise ValueError('Archived baseline commit is unavailable')
    return [name for name in result.stdout.decode('utf-8').splitlines()
            if name.endswith('.py') or name.startswith('src/nexus/config/')]


def _fingerprint_blobs(blobs, cache_algorithm):
    hasher = hashlib.sha256()
    for name in sorted(blobs, key=Path):
        hasher.update(name.encode('utf-8'))
        hasher.update(b'\0')
        hasher.update(blobs[name])
        hasher.update(b'\0')
    hasher.update(cache_algorithm)
    return hasher.hexdigest()


def verify_archive_source(expected_sha256, *, repo_root=ROOT, commit=BASELINE_COMMIT):
    """Only the explicit context/veto integration may differ from the archive."""
    repo_root = Path(repo_root).resolve()
    names = _tracked_source_names(repo_root, commit)
    original = {name: _git_blob(repo_root, commit, name) for name in names}
    algorithm = _git_blob(repo_root, commit, 'tools/long_signal_cache.py')
    reconstructed = _fingerprint_blobs(original, algorithm)
    if reconstructed != expected_sha256:
        raise ValueError('Archived source fingerprint does not match reconstructed Git baseline')
    if (repo_root / 'tools/long_signal_cache.py').read_bytes() != algorithm:
        raise ValueError('Signal-cache algorithm changed; archived cards cannot be reused')
    current_paths = [*(repo_root / 'src/nexus').rglob('*.py'),
                     *(path for path in (repo_root / 'src/nexus/config').rglob('*') if path.is_file())]
    current = {path.relative_to(repo_root).as_posix(): path for path in current_paths}
    extras = set(current) - set(original)
    missing = set(original) - set(current)
    if missing or not extras <= ALLOWED_NEW:
        raise ValueError(f'Unexpected source inventory change: missing={sorted(missing)}, new={sorted(extras)}')
    changed = [name for name, blob in original.items() if current[name].read_bytes() != blob]
    if not set(changed) <= ALLOWED_MODIFIED:
        raise ValueError(f'Model/helper source changed; archived cards cannot be reused: {sorted(changed)}')
    return {
        'baseline_commit': commit, 'reconstructed_source_sha256': reconstructed,
        'expected_archive_source_sha256': expected_sha256,
        'protected_files_verified': len(original) - len(changed),
        'protected_paths': sorted(set(original) - set(changed)),
        'changed_context_integration_paths': sorted(changed), 'new_context_paths': sorted(extras),
        'cache_algorithm_sha256': hashlib.sha256(algorithm).hexdigest(),
        'source_policy': 'Every existing strategy/helper/config byte must match; only declared context-veto files may differ.',
    }


def write_training_prefix(csv_path, bars, count, timeframe, output):
    """Copy native rows byte for byte, then independently parse and compare them."""
    if type(count) is not int or not 0 < count <= len(bars):
        raise ValueError('Training prefix must retain a positive actual native-row count')
    csv_path, output = Path(csv_path).resolve(), Path(output).resolve()
    if csv_path == output:
        raise ValueError('Training prefix cannot overwrite the native source')
    original = csv_path.read_bytes()
    lines = original.splitlines(keepends=True)
    if len(lines) != len(bars) + 1:
        raise ValueError('Native CSV must contain one header and one complete physical line per candle')
    prefix = b''.join(lines[:count + 1])
    output.parent.mkdir(parents=True, exist_ok=True)
    if not output.exists() or output.read_bytes() != prefix:
        temporary = output.with_name(output.name + f'.pending.{os.getpid()}')
        try:
            temporary.write_bytes(prefix)
            os.replace(temporary, output)
        finally:
            if temporary.exists():
                temporary.unlink()
    parsed, digest = signals.load_csv(output, timeframe)
    if parsed != bars[:count] or output.read_bytes() != prefix:
        raise ValueError('Native training prefix differs from the full-series prefix')
    if csv_path.read_bytes() != original:
        raise ValueError('Native source changed while preparing the prefix')
    return {'path': str(output), 'bars': count, 'csv_sha256': digest,
            'source_csv_sha256': hashlib.sha256(original).hexdigest(),
            'byte_preserving': True, 'parsed_rows_equal_full_prefix': True,
            'synthetic_candles': 0}


def _read_archive(provenance, bars, *, repo_root=ROOT):
    models = sorted(REGISTRY)
    if provenance['model_ids'] != models or provenance['bar_count'] != len(bars):
        raise ValueError('Archived model inventory or native bar count mismatch')
    spec = {key: provenance[key] for key in SPEC_KEYS}
    key = hashlib.sha256(signals._encoded(spec)).hexdigest()
    if key != provenance['cache_key'] or provenance['cache_version'] != signals.CACHE_VERSION:
        raise ValueError('Archived signal-cache key does not match its immutable specification')
    start = provenance['start_index']
    if type(start) is not int or not 0 <= start <= len(bars):
        raise ValueError('Invalid archived first signal index')
    directory = Path(repo_root).resolve() / 'reports/long-study-cache' / key
    declared = Path(provenance['cache_directory']).resolve()
    if declared != directory:
        raise ValueError('Archived chunk directory must resolve to its original repository cache')
    cards = {model: [] for model in models}
    counts = {model: Counter() for model in models}
    chunk_hashes = []
    for begin in range(start, len(bars), signals.CHUNK_SIZE):
        end = min(begin + signals.CHUNK_SIZE, len(bars))
        path = directory / f'{begin:09d}-{end:09d}.json.gz'
        payload = signals._read_chunk(path, key, begin, end, models)
        if payload is None:
            raise ValueError(f'Archived signal chunk failed integrity: {path.name}')
        chunk_hashes.append({'name': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        for model in models:
            cards[model].extend(payload['cards'][model])
            counts[model].update(payload['status_counts'][model])
    if len(chunk_hashes) != provenance['chunks']:
        raise ValueError('Archived chunk inventory differs from the original study')
    return cards, counts, chunk_hashes


def load_context_cache(study_path, csv_path, metadata_path, *, with_training_prefix=True,
                       workers=4):
    """Load the original cards plus only the previously missing native prefix."""
    study_path, csv_path, metadata_path = map(Path, (study_path, csv_path, metadata_path))
    study_blob = study_path.read_bytes()
    study = json.loads(study_blob)
    metadata = json.loads(metadata_path.read_bytes())
    archive = study['cache_provenance']
    proof = verify_archive_source(archive['source_sha256'])
    bars, digest = signals.load_csv(csv_path, study['timeframe'])
    declared_hashes = (study['source_data_sha256'], study['native_csv_sha256'],
                       archive['csv_sha256'], metadata['csv_sha256'])
    if any(value != digest for value in declared_hashes):
        raise ValueError('Native CSV hash differs from the archived study or its sidecar')
    if (len(bars) != study['bars'] or archive['symbol'] != study['symbol'] or
            archive['timeframe'] != study['timeframe'] or metadata['symbol'] != study['symbol'] or
            metadata['timeframe'] != study['timeframe'] or metadata['point'] != archive['point']):
        raise ValueError('Native study/sidecar identity mismatch')
    cards, counts, chunks = _read_archive(archive, bars)
    starts, atr_values = signals.segment_arrays(bars, study['timeframe'], archive['profile'])
    prefix_proof = None
    if with_training_prefix and archive['start_index']:
        prefix_proof = write_training_prefix(
            csv_path, bars, archive['start_index'], study['timeframe'],
            ROOT / 'reports/context-layer/native-training-prefix.csv')
        prefix = signals.build_cache(
            prefix_proof['path'], symbol=study['symbol'], timeframe=study['timeframe'],
            point=archive['point'], profile=archive['profile'],
            cache_dir=ROOT / 'reports/context-layer/prefix-cache', workers=workers,
            start_index=0, model_ids=None)
        length = archive['start_index']
        if (prefix['bars'] != bars[:length] or prefix['segment_starts'] != starts[:length] or
                prefix['atr_values'] != atr_values[:length]):
            raise ValueError('Training prefix cache differs from the original full-series inputs')
        prefix_proof['cache_provenance'] = prefix['provenance']
        for model in sorted(REGISTRY):
            cards[model] = prefix['cards'][model] + cards[model]
            counts[model].update(prefix['status_counts'][model])
    for model, rows in cards.items():
        indices = [row['index'] for row in rows]
        if indices != sorted(set(indices)):
            raise ValueError(f'Overlapping or unordered merged signal indices: {model}')
    if verify_archive_source(archive['source_sha256']) != proof:
        raise ValueError('Protected model/helper sources changed during archive loading')
    source_proof = {
        **proof, 'archive_study_sha256': hashlib.sha256(study_blob).hexdigest(),
        'archive_csv_sha256': digest, 'archived_cache_key': archive['cache_key'],
        'chunks_verified': len(chunks), 'chunk_files': chunks,
        'chunk_inventory_sha256': hashlib.sha256(signals._encoded(chunks)).hexdigest(),
        'training_prefix': prefix_proof, 'complete_model_count': len(cards),
        'qualification': 'RESEARCH_ONLY_UNCHANGED_CARDS_CONTEXT_LAYER_ABLATION',
    }
    specification = {key: metadata[key] for key in ('point', 'contract_size', 'profit_currency', 'symbol')}
    return {
        'bars': bars, 'segment_starts': starts, 'atr_values': atr_values,
        'cards': cards, 'status_counts': {model: dict(value) for model, value in counts.items()},
        'symbol': study['symbol'], 'timeframe': study['timeframe'],
        'specification': specification,
        'provenance': {
            **archive, 'source_sha256': signals.source_fingerprint(),
            'archive_source_sha256': archive['source_sha256'],
            'start_index': 0 if with_training_prefix else archive['start_index'],
            'card_archive_proof': source_proof, 'qualified': False,
            'execution_authority': False, 'live_changes': False,
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study', type=Path, required=True)
    parser.add_argument('--csv', type=Path, required=True)
    parser.add_argument('--metadata', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--no-prefix', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    cache = load_context_cache(args.study, args.csv, args.metadata,
                               with_training_prefix=not args.no_prefix, workers=args.workers)
    output = {'bars': len(cache['bars']), 'models': len(cache['cards']),
              'ready_cards': {model: len(rows) for model, rows in cache['cards'].items()},
              'provenance': cache['provenance']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'bars': output['bars'], 'models': output['models'],
                      'chunks_verified': output['provenance']['card_archive_proof']['chunks_verified'],
                      'training_prefix': output['provenance']['card_archive_proof']['training_prefix'],
                      'orders_sent': 0, 'qualified': False}, indent=2))


if __name__ == '__main__':
    main()
