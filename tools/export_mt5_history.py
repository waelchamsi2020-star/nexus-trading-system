"""Read-only paginated native MT5 history export, with explicit coverage evidence.

No terminal settings, symbols, orders or positions are modified. The terminal's
chart-history/maxbars limits remain in force. Five years is a requested span,
never a promise that five years of history were returned. API bounds are UTC
and inclusive; duplicate page-boundary bars are verified before merging.

Official API/UTC/history-limit reference:
https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesrange_py
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nexus.timeframes import PERIODS, bar_close_time
from nexus.trading_calendar import expected_closure_gap, validate_profile

REFERENCE = "https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesrange_py"
RATE_FIELDS = ("time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume")


def utc_date(value):
    """Explicit date-only/naive ISO input is interpreted as UTC, never local."""
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(value)
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def five_years_before(value):
    try:
        return value.replace(year=value.year - 5)
    except ValueError:
        return value.replace(year=value.year - 5, day=28)


def utc_text(timestamp):
    return datetime.fromtimestamp(timestamp, UTC).isoformat()


def _rate(row):
    result = {}
    for key in RATE_FIELDS:
        raw = row[key]
        if isinstance(raw, bool):
            raise TypeError("Boolean native rate value: " + key)
        number = float(raw)
        if not math.isfinite(number):
            raise ValueError("Nonfinite native rate value: " + key)
        if key in ("time", "tick_volume", "spread", "real_volume"):
            if number < 0 or int(number) != number:
                raise ValueError("Invalid native integer field: " + key)
            result[key] = int(number)
        else:
            if number <= 0:
                raise ValueError("Nonpositive native OHLC: " + key)
            result[key] = number
    if (result["low"] > min(result["open"], result["close"]) or
            result["high"] < max(result["open"], result["close"]) or
            result["low"] > result["high"]):
        raise ValueError("Inconsistent native OHLC range")
    return result


def _error(sdk):
    try:
        error = sdk.last_error()
        return list(error) if isinstance(error, tuple) else str(error)
    except (AttributeError, TypeError, ValueError, RuntimeError, OSError) as exc:
        return ["LAST_ERROR_UNAVAILABLE", type(exc).__name__, str(exc)]


def _attribute_snapshot(value, names):
    return {key: getattr(value, key, None) for key in names} if value is not None else None


def _source_identity(sdk, symbol, *, terminal, specification):
    """Privately hash terminal/account/specification identity, never print IDs."""
    account = sdk.account_info()
    values = {
        "terminal": _attribute_snapshot(terminal, ("path", "data_path", "company", "name")),
        "account": _attribute_snapshot(account, ("login", "server", "currency")),
        "symbol": symbol,
        "specification": _attribute_snapshot(specification, (
            "point", "trade_contract_size", "trade_tick_size", "currency_profit")),
    }
    available = (terminal is not None and bool(getattr(terminal, "connected", False)) and
                 account is not None and specification is not None)
    return {"available": available,
            "identity_sha256": hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()}


def _gap_inventory(bars, timeframe, profile):
    gaps = []
    for previous, current in itertools.pairwise(bars):
        close = bar_close_time(previous["time"], timeframe)
        if close != current["time"]:
            expected = expected_closure_gap(close, current["time"], PERIODS[timeframe], profile)
            gaps.append({"previous_open_utc": utc_text(previous["time"]),
                         "missing_from_utc": utc_text(close), "next_open_utc": utc_text(current["time"]),
                         "clock_gap_seconds": current["time"] - close,
                         "classification": "EXPECTED_BY_DECLARED_RESEARCH_CALENDAR" if expected else "UNEXPLAINED_SESSION_OR_SOURCE_GAP",
                         "broker_calendar_verified": False})
    return gaps


def fetch_history(sdk, *, symbol, timeframe, start_date, end_date, as_of,
                  page_days=30, retries=1, calendar_profile="CONTINUOUS", progress=None):
    """Return verified unique bars plus every SDK/page/data-quality limitation.

    Conflicting duplicate timestamps are excluded entirely, rather than choosing
    the more convenient quote. Failed/empty pages remain visible in the report.
    `end_date` is a completed-bar cutoff; a bar closing after it is not exported.
    """
    start, requested_end, now = map(utc_date, (start_date, end_date, as_of))
    if start >= requested_end or start >= now:
        raise ValueError("Start must precede end and the actual observation time")
    if not isinstance(page_days, int) or isinstance(page_days, bool) or not 1 <= page_days <= 366:
        raise ValueError("page_days must be an integer between 1 and 366")
    if not isinstance(retries, int) or isinstance(retries, bool) or not 0 <= retries <= 5:
        raise ValueError("retries must be an integer between 0 and 5")
    if timeframe not in PERIODS:
        raise ValueError("Unsupported timeframe")
    validate_profile(calendar_profile)
    timeframe_value = getattr(sdk, "TIMEFRAME_" + timeframe, None)
    if timeframe_value is None:
        raise ValueError("Installed MT5 SDK does not expose timeframe " + timeframe)
    end = min(requested_end, now)
    pages, rows, conflicts, conflict_times, rejected = [], {}, [], set(), []
    counts = {key: 0 for key in ("received", "duplicate_identical", "duplicate_conflicting",
                                "conflict_timestamp_excluded", "invalid", "outside_page",
                                "outside_requested_range", "future", "incomplete")}
    info = sdk.symbol_info(symbol)
    if info is None:
        raise RuntimeError("MT5 symbol unavailable: " + symbol + "; " + str(_error(sdk)))
    terminal = sdk.terminal_info()
    identity_before = _source_identity(sdk, symbol, terminal=terminal, specification=info)
    specification = _attribute_snapshot(info, ("point", "trade_contract_size", "trade_tick_size",
                                               "digits", "currency_base", "currency_profit", "currency_margin"))
    limits = _attribute_snapshot(terminal, ("connected", "maxbars", "build"))
    cursor = start
    while cursor < end:
        page_end = min(cursor + timedelta(days=page_days), end)
        page = {"index": len(pages), "from_utc": cursor.isoformat(), "to_utc": page_end.isoformat(),
                "inclusive_api_bounds": True, "attempts": [], "returned": 0,
                "eligible_native_rows": 0, "accepted_new": 0}
        rates = None
        for attempt in range(retries + 1):
            try:
                rates = sdk.copy_rates_range(symbol, timeframe_value, cursor, page_end)
                error = _error(sdk)
                page["attempts"].append({"attempt": attempt + 1, "sdk_error": error,
                                         "returned": len(rates) if rates is not None else None})
            except (TypeError, ValueError, RuntimeError, OSError, OverflowError) as exc:
                rates = None
                page["attempts"].append({"attempt": attempt + 1, "exception": type(exc).__name__,
                                         "message": str(exc), "sdk_error": _error(sdk), "returned": None})
            if rates is not None and len(rates):
                break
        if rates is None:
            page["status"] = "SDK_ERROR_NO_BARS"
        elif not len(rates):
            page["status"] = "EMPTY_SOURCE_RESPONSE"
        else:
            page["status"] = "DATA_RETURNED"
            page["returned"] = len(rates)
            counts["received"] += len(rates)
            for raw in rates:
                try:
                    row = _rate(raw)
                except (ValueError, TypeError, KeyError, OverflowError) as exc:
                    counts["invalid"] += 1
                    rejected.append({"page": page["index"], "reason": "INVALID_NATIVE_ROW", "error": str(exc)})
                    continue
                stamp = row["time"]
                reason = None
                if stamp > now.timestamp():
                    reason = "future"
                elif bar_close_time(stamp, timeframe) > end.timestamp():
                    reason = "incomplete"
                elif not start.timestamp() <= stamp <= end.timestamp():
                    reason = "outside_requested_range"
                elif not cursor.timestamp() <= stamp <= page_end.timestamp():
                    reason = "outside_page"
                if reason:
                    counts[reason] += 1
                    rejected.append({"page": page["index"], "time": stamp, "reason": reason})
                    continue
                page["eligible_native_rows"] += 1
                if stamp in conflict_times:
                    counts["conflict_timestamp_excluded"] += 1
                elif stamp in rows:
                    if rows[stamp] == row:
                        counts["duplicate_identical"] += 1
                    else:
                        counts["duplicate_conflicting"] += 1
                        conflicts.append({"time": stamp, "page": page["index"], "first": rows.pop(stamp), "conflicting": row})
                        conflict_times.add(stamp)
                else:
                    rows[stamp] = row
                    page["accepted_new"] += 1
            if not page["eligible_native_rows"]:
                page["status"] = "SOURCE_RESPONSE_WITHOUT_ELIGIBLE_BARS"
        pages.append(page)
        if progress is not None:
            progress({"page": page["index"], "from_utc": page["from_utc"], "to_utc": page["to_utc"],
                      "status": page["status"], "returned": page["returned"], "unique_bars_so_far": len(rows)})
        # Inclusive API pages intentionally overlap at this single boundary.
        cursor = page_end
    bars = [rows[stamp] for stamp in sorted(rows)]
    identity_after = _source_identity(sdk, symbol, terminal=sdk.terminal_info(), specification=sdk.symbol_info(symbol))
    consistent = (identity_before["available"] and identity_after["available"] and
                  identity_before["identity_sha256"] == identity_after["identity_sha256"])
    quarantined = len(bars) if not consistent else 0
    if not consistent:
        # Never export a possibly mixed account/server/symbol history.
        bars = []
    gaps = _gap_inventory(bars, timeframe, calendar_profile)
    no_data = [p for p in pages if p["status"] != "DATA_RETURNED"]
    errors = [p for p in pages if p["status"] == "SDK_ERROR_NO_BARS"]
    first, last = (bars[0]["time"], bars[-1]["time"]) if bars else (None, None)
    last_close = bar_close_time(last, timeframe) if last is not None else None
    report = {"type": "READ_ONLY_PAGINATED_MT5_NATIVE_EXPORT", "source": "MT5_NATIVE", "aggregated": False,
              "timezone": "UTC", "symbol": symbol, "timeframe": timeframe, "completed_only": True,
              "requested_start_utc": start.isoformat(), "requested_end_utc": requested_end.isoformat(),
              "effective_end_utc": end.isoformat(), "as_of_utc": now.isoformat(),
              "requested_end_clamped_to_actual_now": requested_end > now, "page_days": page_days,
              "requested_wall_clock_days": (requested_end - start).total_seconds() / 86400,
              "bars": len(bars), "first_open_utc": utc_text(first) if first is not None else None,
              "last_open_utc": utc_text(last) if last is not None else None,
              "last_close_utc": utc_text(last_close) if last_close is not None else None,
              "observed_span_days": (last_close - first) / 86400 if bars else 0.,
              "status": "SOURCE_CHANGED_OR_UNVERIFIABLE_QUARANTINED" if not consistent else "EMPTY" if not bars else "PARTIAL_DATA_ISSUES" if errors or conflicts or counts["invalid"] or counts["outside_page"] else "OBSERVED_WITH_UNVERIFIED_COVERAGE",
              "source_identity_before": identity_before, "source_identity_after": identity_after,
              "source_consistency_verified": consistent, "source_mismatch_quarantined_bars": quarantined,
              "source_specification": specification, "terminal_limits_observed": limits,
              "commission_per_lot": None, "commission_known": False,
              "fee_source": "UNKNOWN_NOT_AVAILABLE_FROM_SYMBOL_SPECIFICATION",
              "pages": pages, "pages_without_bars": len(no_data), "pages_with_sdk_errors": len(errors),
              "pages_without_eligible_bars": sum(p["eligible_native_rows"] == 0 for p in pages),
              "row_counters": counts, "rejected_rows": rejected, "duplicate_conflicts": conflicts,
              "excluded_conflicting_timestamps": sorted(conflict_times), "gaps": gaps,
              "calendar_profile": calendar_profile, "broker_calendar_verified": False,
              "coverage": {
                  "leading_clock_seconds_not_observed": max(0., first - start.timestamp()) if bars else (end - start).total_seconds(),
                  "trailing_clock_seconds_not_observed": max(0., end.timestamp() - last_close) if bars else (end - start).total_seconds(),
                  "internal_clock_gaps": len(gaps),
                  "unexplained_gaps": sum(g["classification"] == "UNEXPLAINED_SESSION_OR_SOURCE_GAP" for g in gaps),
                  "all_requested_trading_bars_proven": False,
                  "five_year_coverage_proven": False,
              },
              "orders_sent": 0, "fabricated_candles": 0, "live_changes": False,
              "qualified": False, "execution_authority": False, "official_reference": REFERENCE,
              "limitations": [
                  "Requested date span is not returned coverage; see actual first/last/count, empty/error pages and gaps",
                  "MT5 supplies available chart history, bounded by terminal Max bars in chart and broker/server retention; no setting changed",
                  "Empty responses cannot distinguish closed sessions, absent broker history, and unloaded terminal history",
                  "Clock gaps include market closures; the declared research calendar is not a verified broker trading schedule",
                  "Native OHLC and tick volume only; no fabricated candles, forward filling, resampling or real order flow",
                  "Conflicting duplicate timestamps are excluded, not silently resolved",
                  "Historical commissions are unknown; metadata does not substitute an invented fee",
                  "SDK connection is local observed provenance, not independent source authentication",
              ]}
    return bars, report


def write_export(path, bars, report):
    """Exclusive creation keeps existing archives and 10000-bar inputs intact."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path = path.with_suffix(".metadata.json")
    report_path = path.with_suffix(".report.json")
    gaps_path = path.with_suffix(".gaps.csv")
    if any(target.exists() for target in (path, metadata_path, report_path, gaps_path)):
        raise FileExistsError("Refusing to overwrite an existing export or its evidence: " + str(path))
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(["<DATE>", "<TIME>", "<OPEN>", "<HIGH>", "<LOW>", "<CLOSE>", "<TICKVOL>", "<VOL>", "<SPREAD>"])
        for row in bars:
            stamp = datetime.fromtimestamp(row["time"], UTC)
            writer.writerow([stamp.strftime("%Y.%m.%d"), stamp.strftime("%H:%M:%S"),
                             *(repr(row[k]) for k in ("open", "high", "low", "close")),
                             row["tick_volume"], row["real_volume"], row["spread"]])
    fingerprint = hashlib.sha256(path.read_bytes()).hexdigest()
    report.update(csv_file=str(path.resolve()), csv_sha256=fingerprint)
    info = report["source_specification"] or {}
    metadata = {"source": "MT5_NATIVE", "aggregated": False, "timezone": "UTC", "completed_only": True,
                "symbol": report["symbol"], "timeframe": report["timeframe"], "bars": len(bars),
                "point": info.get("point"), "contract_size": info.get("trade_contract_size"),
                "profit_currency": info.get("currency_profit"), "commission_per_lot": None,
                "commission_known": False, "fee_source": report["fee_source"],
                "calendar_profile": report["calendar_profile"], "csv_sha256": fingerprint,
                "coverage_report": report_path.name, "qualified": False}
    with metadata_path.open("x", encoding="utf-8") as stream:
        json.dump(metadata, stream, indent=2, allow_nan=False)
    with gaps_path.open("x", newline="", encoding="utf-8") as stream:
        keys = ["previous_open_utc", "missing_from_utc", "next_open_utc", "clock_gap_seconds", "classification", "broker_calendar_verified"]
        writer = csv.DictWriter(stream, fieldnames=keys, lineterminator="\n")
        writer.writeheader()
        writer.writerows(report["gaps"])
    with report_path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    return report_path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="EURUSD")
    parser.add_argument("--timeframe", choices=tuple(PERIODS), default="H1")
    parser.add_argument("--start-date", type=utc_date, help="ISO date/time; naive input explicitly means UTC; default five calendar years ago")
    parser.add_argument("--end-date", type=utc_date, help="ISO UTC completed-bar cutoff; default actual UTC now")
    parser.add_argument("--page-days", type=int, default=30)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--calendar-profile", choices=("CONTINUOUS", "FX_UTC22_V1"), default="CONTINUOUS")
    parser.add_argument("--terminal", help="Optional installed MT5 executable path; no account credentials accepted")
    parser.add_argument("--output", type=Path, help="New CSV path; default private reports/history-expansion; never overwrites")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", args.symbol):
        parser.error("Symbol must be a simple MT5 symbol name, not a filesystem path")
    now = datetime.now(UTC)
    end = args.end_date or now
    start = args.start_date or five_years_before(end)
    output = args.output or ROOT / "reports/history-expansion" / (
        f"{args.symbol}_{args.timeframe}_{start:%Y%m%d}_{now:%Y%m%dT%H%M%S%fZ}.csv")
    output.parent.mkdir(parents=True, exist_ok=True)
    import MetaTrader5 as mt5
    initialized = False
    try:
        initialized = mt5.initialize(args.terminal) if args.terminal else mt5.initialize()
        if not initialized:
            raise RuntimeError("MT5 initialize failed: " + str(_error(mt5)))
        bars, report = fetch_history(mt5, symbol=args.symbol, timeframe=args.timeframe,
            start_date=start, end_date=end, as_of=now, page_days=args.page_days,
            retries=args.retries, calendar_profile=args.calendar_profile,
            progress=lambda row: print(json.dumps({"type": "PAGE", **row}), flush=True))
        report_path = write_export(output, bars, report)
        print(json.dumps({"type": "SUMMARY", "report": str(report_path.resolve()),
            **{key: report[key] for key in ("symbol", "timeframe", "bars", "first_open_utc", "last_close_utc",
                "requested_start_utc", "requested_end_utc", "pages_without_bars", "pages_with_sdk_errors",
                "status", "coverage", "csv_sha256")}}, indent=2), flush=True)
        return 2 if not bars else 0
    except (ValueError, RuntimeError, OSError) as exc:
        failure = output.with_suffix(".failure.json")
        with failure.open("x", encoding="utf-8") as stream:
            json.dump({"type": "EXPORT_FAILED", "symbol": args.symbol, "timeframe": args.timeframe,
                       "start_utc": start.isoformat(), "end_utc": end.isoformat(),
                       "error": type(exc).__name__, "message": str(exc), "orders_sent": 0}, stream, indent=2)
        print(json.dumps({"status": "FAILED", "error": str(exc), "evidence": str(failure)}), flush=True)
        return 1
    finally:
        if initialized:
            mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
