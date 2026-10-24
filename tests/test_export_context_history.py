"""Native context acquisition is read-only and never invents an index or history."""
import hashlib
import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from test_export_mt5_history import MockSDK, rate

from tools import export_context_history as context


class ContextSDK(MockSDK):
    TIMEFRAME_H4 = 16388
    TIMEFRAME_D1 = 16408

    def __init__(self, responses, symbols=('EURUSD', 'DXY')):
        super().__init__(responses)
        self.symbols = symbols

    def symbols_get(self):
        return ([SimpleNamespace(name=name, description='SYNTHETIC native symbol fixture')
                 for name in self.symbols] if self.symbols is not None else None)

    def order_send(self, *_args, **_kwargs):
        raise AssertionError('Research exporter must never call order_send')

    def symbol_select(self, *_args, **_kwargs):
        raise AssertionError('Research exporter must never mutate symbol selection')


class ExportContextHistory(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 10, 5, tzinfo=UTC)
        self.end = self.start + timedelta(days=2)

    def test_only_broker_listed_dollar_index_aliases_are_discovered(self):
        sdk = ContextSDK([], symbols=('EURUSD', 'US30', 'DXYETF', 'USDX.cash', 'DXY'))
        result = context.discover_dollar_index(sdk)
        self.assertEqual('DXY', result['symbol'])
        self.assertEqual(['DXY', 'USDX.cash'], [row['name'] for row in result['matches']])
        self.assertFalse(result['constructed_from_fx'])
        self.assertEqual([], sdk.calls)

    def test_missing_or_failed_dxy_discovery_is_explicit_and_never_constructed(self):
        for catalog, status in ((('EURUSD', 'GBPUSD'), 'BROKER_NATIVE_DOLLAR_INDEX_UNAVAILABLE'),
                                (None, 'SYMBOL_DISCOVERY_FAILED')):
            with self.subTest(catalog=catalog):
                result = context.discover_dollar_index(ContextSDK([], symbols=catalog))
                self.assertEqual(status, result['status'])
                self.assertIsNone(result['symbol'])
                self.assertFalse(result['constructed_from_fx'])

    def test_h4_d1_and_dxy_are_native_completed_exports_with_unknown_fees(self):
        sdk = ContextSDK([[rate(self.start)], [rate(self.start)], [rate(self.start)]])
        with tempfile.TemporaryDirectory() as directory:
            report = context.export_context_history(
                sdk, output_dir=directory, start_date=self.start, end_date=self.end,
                as_of=self.end, run_id='SYNTHETIC_TEST')
            self.assertEqual(3, len(report['exports']))
            self.assertEqual([('EURUSD', 'H4'), ('EURUSD', 'D1'), ('DXY', 'H1')],
                             [(row['symbol'], row['timeframe']) for row in report['exports']])
            self.assertEqual(0, report['orders_sent'])
            self.assertEqual(0, report['aggregated_candles'])
            self.assertEqual(0, report['fabricated_candles'])
            self.assertEqual(0, report['terminal_setting_changes'])
            for row in report['exports']:
                metadata = json.loads(Path(row['metadata']).read_bytes())
                self.assertEqual(1, metadata['bars'])
                self.assertEqual('MT5_NATIVE', metadata['source'])
                self.assertFalse(metadata['aggregated'])
                self.assertIsNone(metadata['commission_per_lot'])
                self.assertFalse(metadata['commission_known'])
                self.assertEqual(hashlib.sha256(Path(row['csv']).read_bytes()).hexdigest(), row['csv_sha256'])
                self.assertLessEqual(context.native.utc_date(row['last_close_utc']), self.end)
            self.assertTrue(all(call[2].tzinfo is UTC and call[3].tzinfo is UTC for call in sdk.calls))

    def test_without_dxy_only_available_higher_timeframes_are_exported(self):
        sdk = ContextSDK([[rate(self.start)], [rate(self.start)]], symbols=('EURUSD',))
        with tempfile.TemporaryDirectory() as directory:
            report = context.export_context_history(
                sdk, output_dir=directory, start_date=self.start, end_date=self.end,
                as_of=self.end, run_id='SYNTHETIC_MISSING_INDEX')
            self.assertEqual(2, len(report['exports']))
            self.assertIsNone(report['dollar_index_discovery']['symbol'])
            self.assertEqual(2, len(sdk.calls))

    def test_cutoff_expansion_and_future_end_are_rejected_before_sdk_history_call(self):
        sdk = ContextSDK([])
        with tempfile.TemporaryDirectory() as directory:
            for end, observed in (('2026-10-17T00:00:00Z', '2026-10-19T00:00:00Z'),
                                   (self.end, self.start + timedelta(days=1))):
                with self.subTest(end=end), self.assertRaises(ValueError):
                    context.export_context_history(
                        sdk, output_dir=directory, start_date=self.start, end_date=end,
                        as_of=observed, run_id='SYNTHETIC_BAD_END')
        self.assertEqual([], sdk.calls)

    def test_reused_cross_symbol_export_must_match_pinned_native_sha(self):
        sdk = ContextSDK([[rate(self.start)]])
        bars, report = context.native.fetch_history(
            sdk, symbol='GBPUSD', timeframe='H1', start_date=self.start,
            end_date=self.end, as_of=self.end, retries=0)
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / 'GBPUSD_H1.csv'
            context.native.write_export(csv_path, bars, report)
            digest = hashlib.sha256(csv_path.read_bytes()).hexdigest()
            with patch.dict(context.EXPECTED_CROSS_SHA, {'GBPUSD': digest}):
                verified = context.verify_reused_history(csv_path, symbol='GBPUSD', end_date=self.end)
                self.assertEqual('VERIFIED_REUSED_NATIVE_EXPORT', verified['status'])
                self.assertEqual(digest, verified['csv_sha256'])
                csv_path.write_bytes(csv_path.read_bytes() + b'CHANGED SOURCE')
                with self.assertRaisesRegex(ValueError, 'provenance'):
                    context.verify_reused_history(csv_path, symbol='GBPUSD', end_date=self.end)
