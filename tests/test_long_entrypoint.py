"""Boundary tests for research-only native long-history entrypoint."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location('long_entrypoint_engine', TOOLS / 'long_walkforward.py')
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)


def inputs(tmp_path):
    csv_path = tmp_path / 'native.csv'
    csv_path.write_bytes(b'An isolated unit fixture, never research price data')
    metadata = {'source': 'MT5_NATIVE', 'aggregated': False, 'timeframe': 'H1',
                'symbol': 'EURUSD', 'point': .00001, 'contract_size': 100000.,
                'profit_currency': 'USD', 'calendar_profile': 'FX_UTC22_V1',
                'commission_known': False,
                'csv_sha256': hashlib.sha256(csv_path.read_bytes()).hexdigest()}
    path = tmp_path / 'native.metadata.json'
    path.write_text(json.dumps(metadata), encoding='utf-8')
    return csv_path, path, metadata


@pytest.mark.parametrize('field,value,error', [
    ('timeframe', 'M1', 'native M5/H1'),
    ('source', 'SIMULATION', 'unaggregated MT5'),
    ('aggregated', True, 'unaggregated MT5'),
    ('csv_sha256', 'wrong', 'fingerprint mismatch'),
])
def test_long_entrypoint_rejects_bad_native_provenance(tmp_path, field, value, error):
    csv_path, path, metadata = inputs(tmp_path)
    metadata[field] = value
    path.write_text(json.dumps(metadata), encoding='utf-8')
    with patch('long_signal_cache.build_cache') as cache:
        with pytest.raises(ValueError, match=error):
            engine.run_native(csv_path, path, tmp_path / 'output.json')
        cache.assert_not_called()


def test_long_entrypoint_refuses_short_cache_before_replay(tmp_path):
    csv_path, path, _ = inputs(tmp_path)
    with patch('long_signal_cache.build_cache', return_value={'bars': [None] * 6000}), \
            pytest.raises(ValueError, match='Insufficient original history'):
        engine.run_native(csv_path, path, tmp_path / 'output.json')


def test_long_entrypoint_uses_fixed_protocol_and_separate_unknown_fee(tmp_path):
    csv_path, path, _ = inputs(tmp_path)
    cache = {'bars': [None] * 30860}
    report = {'folds': [None] * 50, 'scenarios': [{'top5': []}]}
    with patch('long_signal_cache.build_cache', return_value=cache) as build, \
            patch.object(engine, 'run_study', return_value=report) as replay, \
            patch.object(engine, 'write_study') as write:
        result, actual_cache = engine.run_native(csv_path, path, tmp_path / 'out.json', workers=3)
        assert build.call_args.kwargs['start_index'] == 5024
        assert build.call_args.kwargs['workers'] == 3
        assert replay.call_args.kwargs == {'train': 5000, 'test': 1000, 'step': 500, 'model_ids': None}
        assert actual_cache['symbol'] == 'EURUSD'
        assert actual_cache['specification']['profit_currency'] == 'USD'
        assert result['actual_commission_known'] is False
        write.assert_called_once()
