"""Read-only native higher-timeframe and dollar-index context acquisition.

The original H1 study cutoff remains fixed. No resampling, basket construction,
symbol selection, terminal setting, chart or broker order is performed here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

import export_mt5_history as native

START = '2021-10-18T00:00:00+00:00'
END = '2026-10-16T21:00:00+00:00'
DOLLAR_INDEX_ALIAS = re.compile(r'^(DXY|USDX|USDINDEX|USDOLLARINDEX|DOLLARINDEX)([.#_-][A-Z0-9]+)?$')
EXPECTED_CROSS_SHA = {
    'GBPUSD': '78aae65abd440858290973be717fbb9eb66d8c838c9cc878c560376728540faf',
    'USDJPY': '652c0092d5360c38d9959ba9ef643e996e64c6eea14d418027a76f47d16f2348',
}


def discover_dollar_index(sdk):
    """Accept only an actual broker-listed dollar-index name, never an FX basket."""
    symbols = sdk.symbols_get()
    if symbols is None:
        return {'status': 'SYMBOL_DISCOVERY_FAILED', 'symbol': None, 'matches': [],
                'sdk_error': native._error(sdk), 'constructed_from_fx': False}
    matches = []
    for info in symbols:
        name = getattr(info, 'name', '')
        if isinstance(name, str) and DOLLAR_INDEX_ALIAS.fullmatch(name.upper()):
            matches.append({'name': name, 'description': getattr(info, 'description', '')})
    matches.sort(key=lambda value: (value['name'].upper() != 'DXY', value['name']))
    return {'status': 'BROKER_NATIVE_SYMBOL_FOUND' if matches else 'BROKER_NATIVE_DOLLAR_INDEX_UNAVAILABLE',
            'symbol': matches[0]['name'] if matches else None, 'matches': matches,
            'broker_symbol_count': len(symbols), 'constructed_from_fx': False,
            'selection': 'Exact DXY preferred, then declared native aliases; never price/performance selected.'}


def verify_reused_history(csv_path, *, symbol, end_date=END):
    """Verify immutable existing native cross-symbol files without rewriting them."""
    csv_path = Path(csv_path).resolve()
    metadata_path, report_path = csv_path.with_suffix('.metadata.json'), csv_path.with_suffix('.report.json')
    metadata = json.loads(metadata_path.read_bytes())
    report = json.loads(report_path.read_bytes())
    digest = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    if (digest != EXPECTED_CROSS_SHA.get(symbol) or
            metadata.get('source') != 'MT5_NATIVE' or metadata.get('aggregated') is not False or
            metadata.get('symbol') != symbol or metadata.get('timeframe') != 'H1' or
            report.get('csv_sha256') != digest or metadata.get('csv_sha256') != digest or
            report.get('source_consistency_verified') is not True or
            metadata.get('bars') != report.get('bars') or
            native.utc_date(report['last_close_utc']) > native.utc_date(end_date)):
        raise ValueError('Existing cross-symbol history failed provenance or frozen-cutoff verification')
    return {'status': 'VERIFIED_REUSED_NATIVE_EXPORT', 'symbol': symbol, 'timeframe': 'H1',
            'bars': metadata['bars'], 'csv': str(csv_path), 'metadata': str(metadata_path),
            'report': str(report_path), 'csv_sha256': digest,
            'report_sha256': hashlib.sha256(report_path.read_bytes()).hexdigest(),
            'first_open_utc': report['first_open_utc'], 'last_close_utc': report['last_close_utc'],
            'commission_known': False, 'aggregated': False, 'qualified': False}


def export_context_history(sdk, *, output_dir, start_date=START, end_date=END,
                            as_of=None, run_id=None, progress=None):
    """Fetch native EURUSD H4/D1 and an available broker dollar index at H1."""
    output_dir = Path(output_dir)
    observed = datetime.now(UTC) if as_of is None else native.utc_date(as_of)
    start, end = native.utc_date(start_date), native.utc_date(end_date)
    if end > native.utc_date(END):
        raise ValueError('Context export cannot exceed the frozen original H1 study cutoff')
    if start >= end or end > observed:
        raise ValueError('Context export requires a completed historical UTC interval')
    identity = sdk.terminal_info()
    if identity is None or not getattr(identity, 'connected', False):
        raise RuntimeError('A connected existing MT5 terminal is required')
    discovery = discover_dollar_index(sdk)
    tasks = [('EURUSD', 'H4', 'FX_UTC22_V1'), ('EURUSD', 'D1', 'FX_UTC22_V1')]
    if discovery['symbol']:
        tasks.append((discovery['symbol'], 'H1', 'CONTINUOUS'))
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = run_id or observed.strftime('%Y%m%dT%H%M%S%fZ')
    if not re.fullmatch(r'[A-Za-z0-9_-]+', stamp):
        raise ValueError('Safe unique context export run_id required')
    results = []
    for symbol, timeframe, profile in tasks:
        safe_symbol = re.sub(r'[^A-Za-z0-9_-]', '_', symbol)
        path = output_dir / f'{safe_symbol}_{timeframe}_{start:%Y%m%d}_{stamp}.csv'
        try:
            bars, report = native.fetch_history(
                sdk, symbol=symbol, timeframe=timeframe, start_date=start, end_date=end,
                as_of=observed, page_days=30, retries=1, calendar_profile=profile,
                progress=(lambda value, s=symbol, tf=timeframe: progress(
                    {'symbol': s, 'timeframe': tf, **value})) if progress is not None else None)
            report['context_export'] = {'frozen_H1_cutoff_utc': end.isoformat(),
                                        'native_only': True, 'constructed_from_fx': False}
            report_path = native.write_export(path, bars, report)
            results.append({'status': report['status'], 'symbol': symbol, 'timeframe': timeframe,
                            'bars': len(bars), 'csv': str(path.resolve()),
                            'metadata': str(path.with_suffix('.metadata.json').resolve()),
                            'report': str(report_path.resolve()), 'csv_sha256': report['csv_sha256'],
                            'first_open_utc': report['first_open_utc'], 'last_close_utc': report['last_close_utc'],
                            'unexplained_gaps': report['coverage']['unexplained_gaps'],
                            'source_consistency_verified': report['source_consistency_verified'],
                            'commission_known': False, 'aggregated': False, 'qualified': False})
        except (ValueError, TypeError, RuntimeError, OSError, KeyError) as exc:
            results.append({'status': 'EXPORT_FAILED', 'symbol': symbol, 'timeframe': timeframe,
                            'bars': 0, 'error': type(exc).__name__, 'message': str(exc), 'qualified': False})
    summary = {
        'type': 'READ_ONLY_NATIVE_CONTEXT_HISTORY', 'requested_start_utc': start.isoformat(),
        'frozen_study_cutoff_utc': end.isoformat(), 'observed_at_utc': observed.isoformat(),
        'dollar_index_discovery': discovery, 'exports': results,
        'qualified': False, 'execution_authority': False, 'orders_sent': 0,
        'aggregated_candles': 0, 'fabricated_candles': 0, 'terminal_setting_changes': 0,
        'limitations': ['Native higher-timeframe data is optional contextual evidence, not a new model.',
                        'Dollar-index sessions are unverified; CONTINUOUS labels every observed clock gap honestly.',
                        'The existing EURUSD H1 test observations overlap the earlier route selection diagnostic.',
                        'Unknown historical commission remains null; no fee was inferred from symbol specifications.'],
    }
    summary_path = output_dir / f'context-history-{stamp}.json'
    with summary_path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports/context-layer/history')
    parser.add_argument('--terminal', default='')
    parser.add_argument('--start-date', default=START)
    parser.add_argument('--end-date', default=END)
    args = parser.parse_args()
    import MetaTrader5 as mt5
    initialized = False
    try:
        initialized = mt5.initialize(args.terminal) if args.terminal else mt5.initialize()
        if not initialized:
            raise RuntimeError('MT5 initialize failed: ' + str(native._error(mt5)))
        summary = export_context_history(
            mt5, output_dir=args.output_dir, start_date=args.start_date, end_date=args.end_date,
            progress=lambda row: print(json.dumps({'type': 'NATIVE_CONTEXT_EXPORT_PAGE', **row}), flush=True))
        # Existing native H1 cross-symbol files are retained and verified, not replaced.
        manifest_path = ROOT / 'reports/five-year-cross-history/export-manifest.json'
        reused = []
        if manifest_path.exists():
            for row in json.loads(manifest_path.read_bytes()):
                if row['symbol'] in ('GBPUSD', 'USDJPY') and row.get('exit_code') == 0:
                    reused.append(verify_reused_history(row['csv'], symbol=row['symbol'], end_date=args.end_date))
        summary['reused_cross_symbol_history'] = reused
        path = args.output_dir / 'latest-summary.json'
        path.write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n', encoding='utf-8')
        print(json.dumps(summary, indent=2), flush=True)
    finally:
        if initialized:
            mt5.shutdown()


if __name__ == '__main__':
    main()
