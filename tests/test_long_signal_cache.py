"""Independent cache equality, causal gap reset, fingerprint and resume proofs."""
import copy
import csv
import gzip
import json
from datetime import UTC, datetime

import pytest
from test_strategies import bars

from nexus.strategies import REGISTRY, analyze_all, atr
from nexus.walkforward import LookaheadBiasError
from tools import long_signal_cache as cache


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream, delimiter='\t', lineterminator='\n')
        writer.writerow(['<DATE>', '<TIME>', '<OPEN>', '<HIGH>', '<LOW>', '<CLOSE>', '<TICKVOL>', '<VOL>', '<SPREAD>'])
        for row in rows:
            stamp = datetime.fromtimestamp(row['time'], UTC)
            writer.writerow([stamp.strftime('%Y.%m.%d'), stamp.strftime('%H:%M:%S'),
                             *(row[key] for key in ('open', 'high', 'low', 'close')),
                             row['tick_volume'], row.get('real_volume', 0), row['spread']])


def arguments(tmp_path, **overrides):
    return {'symbol': 'EURUSD', 'timeframe': 'H1', 'point': .00001,
            'profile': 'CONTINUOUS', 'cache_dir': tmp_path / 'cache',
            'workers': 1, **overrides}


def test_all58_compact_execution_fields_equal_direct_completed_candle_analysis(tmp_path):
    path = tmp_path / 'native.csv'
    rows = bars(315)
    write_csv(path, rows)
    result = cache.build_cache(path, **arguments(tmp_path, start_index=310))
    assert set(result['cards']) == set(REGISTRY)
    expected = {model: [] for model in REGISTRY}
    counts = {model: {} for model in REGISTRY}
    context = {'tick_size': .00001, 'data_kind': 'broker', 'calendar_profile': 'CONTINUOUS'}
    for index in range(310, len(rows)):
        direct = analyze_all('EURUSD', 'H1', rows[index + 1 - 300:index + 1],
                             rows[index]['time'] + 3600, context)
        for card in direct:
            model = card['strategy_id']
            counts[model][card['status']] = counts[model].get(card['status'], 0) + 1
            if card['status'] == 'READY' and card['coverage'] == 'IMPLEMENTED' and card['entry']['triggered']:
                expected[model].append({'index': index,
                                        'card': {key: card.get(key) for key in cache.EXECUTION_FIELDS}})
    assert result['cards'] == expected
    assert result['status_counts'] == counts
    assert result['provenance']['decision_bars'] == 5
    assert result['provenance']['qualified'] is False


def test_cache_future_prices_cannot_change_earlier_cards_or_atr(tmp_path):
    original = bars(100)
    changed = copy.deepcopy(original)
    for row in changed[85:]:
        for key in ('open', 'high', 'low', 'close'):
            row[key] *= 10
    first, second = tmp_path / 'first.csv', tmp_path / 'second.csv'
    write_csv(first, original)
    write_csv(second, changed)
    args = arguments(tmp_path, start_index=60, model_ids=['support_bounce', 'ema_cross'])
    before = cache.build_cache(first, **args)
    after = cache.build_cache(second, **args)
    for model in args['model_ids']:
        assert [r for r in before['cards'][model] if r['index'] < 85] == [
            r for r in after['cards'][model] if r['index'] < 85]
    assert before['atr_values'][:85] == after['atr_values'][:85]
    assert before['provenance']['cache_key'] != after['provenance']['cache_key']


def test_unknown_gap_resets_history_and_atr_without_training_carry(tmp_path):
    rows = bars(150)
    for row in rows[100:]:
        row['time'] += 3600
    path = tmp_path / 'gap.csv'
    write_csv(path, rows)
    result = cache.build_cache(path, **arguments(tmp_path, start_index=100, model_ids=['ema_cross']))
    assert result['segment_starts'][:100] == [0] * 100
    assert result['segment_starts'][100:] == [100] * 50
    assert result['atr_values'][100] == 0.
    assert result['atr_values'][110] == atr(rows[100:111])
    assert result['status_counts']['ema_cross'] == {'DATA_MISSING': 50}
    assert result['cards']['ema_cross'] == []


def test_resume_reuses_verified_chunks_and_corruption_recomputes_only_bad_chunk(tmp_path, monkeypatch):
    path = tmp_path / 'native.csv'
    write_csv(path, bars(150))
    args = arguments(tmp_path, model_ids=['engulfing'])
    first = cache.build_cache(path, **args)
    assert first['provenance']['chunks_computed'] == 2
    compute = cache._compute_chunk
    monkeypatch.setattr(cache, '_compute_chunk', lambda job: pytest.fail('Verified chunk was recomputed'))
    second = cache.build_cache(path, **args)
    assert second['cards'] == first['cards']
    assert second['provenance']['chunks_reused'] == 2
    directory = cache.Path(first['provenance']['cache_directory'])
    chunk = min(directory.glob('[0-9]*.json.gz'))
    chunk.write_bytes(b'corrupt incomplete gzip')
    monkeypatch.setattr(cache, '_compute_chunk', compute)
    third = cache.build_cache(path, **args)
    assert third['provenance']['chunks_computed'] == 1
    assert third['provenance']['chunks_reused'] == 1
    assert third['cards'] == first['cards']


def test_parallel_spawn_matches_serial_chunk_results(tmp_path):
    path = tmp_path / 'native.csv'
    write_csv(path, bars(140))
    first = cache.build_cache(path, **arguments(tmp_path, cache_dir=tmp_path / 'serial', model_ids=['engulfing']))
    second = cache.build_cache(path, **arguments(tmp_path, cache_dir=tmp_path / 'parallel',
                                                workers=2, model_ids=['engulfing']))
    assert first['cards'] == second['cards']
    assert first['status_counts'] == second['status_counts']


def test_native_future_duplicates_unknown_model_and_invalid_point_rejected(tmp_path):
    path = tmp_path / 'native.csv'
    rows = bars(80)
    write_csv(path, rows)
    with pytest.raises(LookaheadBiasError):
        cache.load_csv(path, 'H1', rows[-1]['time'])
    with pytest.raises(ValueError, match='point'):
        cache.build_cache(path, **arguments(tmp_path, point=0))
    with pytest.raises(ValueError, match='model_ids'):
        cache.build_cache(path, **arguments(tmp_path, model_ids=['NOT_A_MODEL']))
    write_csv(path, rows[:2] + [rows[1]])
    with pytest.raises(ValueError):
        cache.load_csv(path, 'H1')


def test_atomic_failure_preserves_existing_chunk_and_drops_pending_file(tmp_path, monkeypatch):
    path = tmp_path / 'chunk.json.gz'
    cache._atomic_gzip(path, {'original': True})
    original = path.read_bytes()

    def reject(source, destination):
        raise OSError('Injected atomic replace failure')

    monkeypatch.setattr(cache.os, 'replace', reject)
    with pytest.raises(OSError, match='Injected'):
        cache._atomic_gzip(path, {'original': False})
    assert path.read_bytes() == original
    assert not list(tmp_path.glob('*.pending.*'))
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        assert json.load(stream) == {'original': True}
