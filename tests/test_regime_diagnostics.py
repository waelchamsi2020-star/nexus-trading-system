"""Causal regime labels are attribution only, never a new entry strategy."""
import copy
import importlib.util
from pathlib import Path

import pytest

from nexus.segment_research import split_segments

_path = Path(__file__).resolve().parents[1] / 'tools/regime_diagnostics.py'
_spec = importlib.util.spec_from_file_location('regime_diagnostics', _path)
diagnostic = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(diagnostic)


def candles(count=100, slope=.2):
    rows = []
    for index in range(count):
        price = 100 + index * slope
        rows.append({'time': 1_700_000_000 + index * 3600,
                     'open': price, 'close': price, 'high': price + .1,
                     'low': price - .1, 'tick_volume': 100, 'spread': 2})
    return rows


@pytest.mark.parametrize(('slope', 'expected'), [(.2, 'UP'), (-.2, 'DOWN'), (0., 'RANGE')])
def test_regime_up_down_and_range_fixed_non_pnl_fixtures(slope, expected):
    rows = candles(slope=slope)
    result = diagnostic.label_at_entry(rows, rows[80]['time'])
    assert result['regime'] == expected
    assert result['history_bars'] == 60
    assert result['latest_input_close_time'] < rows[80]['time']


def test_regime_label_invariant_to_all_future_and_entry_boundary_prices():
    rows = candles()
    entry = rows[80]['time']
    result = diagnostic.label_at_entry(rows, entry)
    changed = copy.deepcopy(rows)
    for row in changed:
        if row['time'] + 3600 >= entry:
            for key in ('open', 'close', 'high', 'low'):
                row[key] *= 100
    assert diagnostic.label_at_entry(changed, entry) == result


def test_regime_warmup_never_carried_across_unexpected_calendar_gap():
    rows = candles(130)
    for row in rows[100:]:
        row['time'] += 3 * 3600
    segments = split_segments(rows, 'H1', 'CONTINUOUS')
    assert [len(segment) for segment in segments] == [100, 30]
    result = diagnostic.label_at_entry(segments[1], segments[1][20]['time'])
    assert result['regime'] == 'UNKNOWN'
    assert result['history_bars'] == 19
    assert result['reason'] == 'INSUFFICIENT_WITHIN_SEGMENT_HISTORY'
    assert diagnostic.label_at_entry(segments[0], segments[0][90]['time'])['regime'] == 'UP'


def test_regime_zero_atr_is_unknown_and_price_ledger_sha_mismatch_rejected():
    rows = candles()
    for row in rows:
        row.update(open=100., high=100., low=100., close=100.)
    result = diagnostic.label_at_entry(rows, rows[80]['time'])
    assert result['regime'] == 'UNKNOWN'
    assert result['reason'] == 'ZERO_ATR'
    source = {'symbol': 'EURUSD', 'timeframe': 'H1', 'data_sha256': 'saved'}
    with pytest.raises(ValueError, match='fingerprint'):
        diagnostic.validate_ledger(rows, source, 'changed')


def test_ledger_attribution_preserves_records_costs_and_model_count(monkeypatch):
    rows = candles()
    trade = {'segment': 0, 'strategy_id': 'fixture', 'entry_index': 80,
             'exit_index': 81, 'entry_time': rows[80]['time'],
             'exit_time': rows[81]['time'] + 3600, 'exit_reason': 'TARGET',
             'signal_time': rows[80]['time'], 'side': 'BUY', 'entry': 116.,
             'exit': 117., 'stop': 115., 'gross_price_pnl': 1.,
             'commission_price_units': 0., 'net_price_pnl': 1., 'r': 1.}
    source = {'symbol': 'EURUSD', 'timeframe': 'H1', 'data_sha256': 'saved',
              'slippage_points_per_side': 10, 'declared_provenance': {
                  'profit_currency': 'USD', 'contract_size': 100000.},
              'base_trades': {'fixture': [trade]}, 'models': 1,
              'total_bars': len(rows), 'calendar_profile': 'CONTINUOUS',
              'segments': [{'segment': 0, 'bars': len(rows),
                            'first_time': rows[0]['time'], 'last_time': rows[-1]['time']}],
              'scenarios': [{'commission_usd_round_trip_per_lot': 7.,
                             'all_selected_segments': [{'model': 'fixture', 'trades': 1,
                                                        'net_r': .99993}]}],
              'repricing_proof_source_sha256': 'archived_replay'}
    before = copy.deepcopy(source)
    monkeypatch.setattr(diagnostic, 'REGISTRY', {'fixture': {'data_requirements': []}})
    report = diagnostic.diagnose(rows, source, native_sha256='saved', source_report_sha256='ledger')
    assert source == before
    assert report['models'] == report['trade_records'] == 1
    row = report['rows'][0]
    assert row['long_trades'] == row['regimes']['UP']['trades'] == 1
    assert row['short_trades'] == 0
    assert row['net_r'] == pytest.approx(.99993)
    assert not report['qualified']
    assert not report['execution_authority']
    assert not report['live_changes']
    assert 'max_dd' not in report['aggregate_model_trade_regimes']['UP']
    assert report['source_report_sha256'] == 'ledger'
    source['base_trades']['fixture'][0]['r'] = 2.
    with pytest.raises(ValueError, match='arithmetic'):
        diagnostic.diagnose(rows, source, native_sha256='saved', source_report_sha256='ledger')
