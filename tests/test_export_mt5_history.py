"""Mock SDK proofs: UTC pages, native merge, exclusion and truthful coverage."""
import csv
import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from tools.export_mt5_history import (
    fetch_history,
    five_years_before,
    utc_date,
    write_export,
)


def rate(stamp, close=1.1):
    return {"time": int(stamp.timestamp()), "open": 1.1, "high": 1.3,
            "low": 1., "close": close, "tick_volume": 100, "spread": 2, "real_volume": 0}


class MockSDK:
    TIMEFRAME_H1 = 16385
    TIMEFRAME_M5 = 5

    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def symbol_info(self, symbol):
        return SimpleNamespace(point=.00001, trade_contract_size=100000.,
                               trade_tick_size=.00001, digits=5, currency_base="EUR",
                               currency_profit="USD", currency_margin="EUR")

    def terminal_info(self):
        return SimpleNamespace(connected=True, maxbars=100000, build=6231)

    def account_info(self):
        return SimpleNamespace(login=123, server="MOCK_TEST_ONLY", currency="USD")

    def last_error(self):
        return (1, "Success")

    def copy_rates_range(self, symbol, timeframe, start, end):
        self.calls.append((symbol, timeframe, start, end))
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


class ExportMT5History(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 10, 5, tzinfo=UTC)

    def args(self, days=2):
        end = self.start + timedelta(days=days)
        return {"symbol": "EURUSD", "timeframe": "H1", "start_date": self.start,
                "end_date": end, "as_of": end, "page_days": 1, "retries": 0}

    def test_utc_inclusive_pagination_and_identical_boundary_dedup(self):
        middle = self.start + timedelta(days=1)
        sdk = MockSDK([[rate(self.start), rate(middle)], [rate(middle), rate(middle + timedelta(hours=1))]])
        bars, report = fetch_history(sdk, **self.args())
        self.assertEqual(3, len(bars))
        self.assertEqual(2, len(sdk.calls))
        self.assertTrue(all(call[2].tzinfo is UTC and call[3].tzinfo is UTC for call in sdk.calls))
        self.assertEqual(sdk.calls[0][3], sdk.calls[1][2])
        self.assertEqual(1, report["row_counters"]["duplicate_identical"])
        self.assertEqual(0, report["orders_sent"])
        self.assertFalse(report["coverage"]["five_year_coverage_proven"])

    def test_conflicting_duplicate_timestamp_excluded_and_not_reintroduced(self):
        middle = self.start + timedelta(days=1)
        sdk = MockSDK([[rate(self.start), rate(middle)], [rate(middle, 1.2), rate(middle)]])
        bars, report = fetch_history(sdk, **self.args())
        self.assertEqual([int(self.start.timestamp())], [row["time"] for row in bars])
        self.assertEqual(1, len(report["duplicate_conflicts"]))
        self.assertEqual(1, report["row_counters"]["conflict_timestamp_excluded"])
        self.assertEqual("PARTIAL_DATA_ISSUES", report["status"])

    def test_future_incomplete_out_of_range_and_invalid_native_rows_excluded(self):
        cutoff = self.start + timedelta(hours=2, minutes=30)
        invalid = rate(self.start)
        invalid["high"] = .9
        sdk = MockSDK([[rate(self.start), rate(self.start + timedelta(hours=2)),
                        rate(self.start + timedelta(hours=3)), rate(self.start - timedelta(hours=1)), invalid]])
        bars, report = fetch_history(sdk, **{**self.args(days=1), "end_date": cutoff, "as_of": cutoff})
        self.assertEqual(1, len(bars))
        for reason in ("future", "incomplete", "outside_requested_range", "invalid"):
            self.assertEqual(1, report["row_counters"][reason])

    def test_empty_and_sdk_failure_pages_retained_with_partial_success(self):
        sdk = MockSDK([None, RuntimeError("network interrupted"), [], [], [rate(self.start + timedelta(days=2))]])
        bars, report = fetch_history(sdk, **{**self.args(days=3), "retries": 1})
        self.assertEqual(1, len(bars))
        self.assertEqual(3, len(report["pages"]))
        self.assertEqual(2, report["pages_without_bars"])
        self.assertEqual(1, report["pages_with_sdk_errors"])
        self.assertEqual("network interrupted", report["pages"][0]["attempts"][1]["message"])
        self.assertEqual("EMPTY_SOURCE_RESPONSE", report["pages"][1]["status"])
        self.assertEqual("PARTIAL_DATA_ISSUES", report["status"])

    def test_empty_export_preserves_unknown_fees_and_refuses_overwrite(self):
        bars, report = fetch_history(MockSDK([[]]), **self.args(days=1))
        self.assertEqual("EMPTY", report["status"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "EURUSD_H1.csv"
            evidence = write_export(path, bars, report)
            metadata = json.loads(path.with_suffix(".metadata.json").read_text())
            self.assertIsNone(metadata["commission_per_lot"])
            self.assertFalse(metadata["commission_known"])
            self.assertEqual(0, json.loads(evidence.read_text())["bars"])
            with path.open(newline="") as stream:
                self.assertEqual(1, len(list(csv.reader(stream, delimiter="\t"))))
            with self.assertRaises(FileExistsError):
                write_export(path, bars, report)

    def test_outside_page_fallback_quote_is_not_mistaken_for_historical_coverage(self):
        sdk = MockSDK([[rate(self.start + timedelta(days=1, hours=2))], []])
        bars, report = fetch_history(sdk, **self.args())
        self.assertEqual([], bars)
        self.assertEqual(1, report["row_counters"]["outside_page"])
        self.assertEqual(2, report["pages_without_eligible_bars"])
        self.assertEqual("SOURCE_RESPONSE_WITHOUT_ELIGIBLE_BARS", report["pages"][0]["status"])

    def test_dates_default_five_calendar_years_and_future_request_clamped(self):
        self.assertEqual(UTC, utc_date("2026-10-05").tzinfo)
        self.assertEqual(self.start, utc_date("2026-10-05T04:00:00+04:00"))
        self.assertEqual(28, five_years_before(datetime(2024, 2, 29, tzinfo=UTC)).day)
        actual = self.start + timedelta(hours=2)
        bars, report = fetch_history(MockSDK([[rate(self.start)]]), **{**self.args(), "as_of": actual})
        self.assertEqual(1, len(bars))
        self.assertTrue(report["requested_end_clamped_to_actual_now"])
        self.assertEqual(actual.isoformat(), report["effective_end_utc"])
        with self.assertRaises(ValueError):
            fetch_history(MockSDK([]), **{**self.args(), "page_days": 0})

    def test_account_server_switch_quarantines_mixed_history_without_ids_in_report(self):
        class SwitchedSDK(MockSDK):
            def account_info(self):
                return SimpleNamespace(login=123 if not self.calls else 456,
                                       server="MOCK_TEST_ONLY", currency="USD")
        bars, report = fetch_history(SwitchedSDK([[rate(self.start)]]), **self.args(days=1))
        self.assertEqual([], bars)
        self.assertFalse(report["source_consistency_verified"])
        self.assertEqual(1, report["source_mismatch_quarantined_bars"])
        self.assertIn("QUARANTINED", report["status"])
        self.assertNotIn('"login"', json.dumps(report))
