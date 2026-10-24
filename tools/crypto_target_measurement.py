"""Read-only, live crypto cost/target measurement for the authorized Demo terminal.

This tool never sends, checks, or modifies an order. It measures the selected
Market Watch crypto symbols for 15 minutes and records the cost/ATR decision
in the existing Demo service audit database.
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
import statistics
import sys
import time
from collections import Counter, deque
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nexus.strategies import analyze_all, atr  # noqa: I001


FRAME_SPECS = (
    ("M1", "TIMEFRAME_M1", 60),
    ("M5", "TIMEFRAME_M5", 300),
    ("M15", "TIMEFRAME_M15", 900),
    ("H1", "TIMEFRAME_H1", 3600),
)
MEASUREMENT_SECONDS = 15 * 60
POLL_SECONDS = 0.25
MAX_AGE_SECONDS = 2.0
SPREAD_TARGET_LIMIT = 0.20


def _median(values: list[float] | deque[float]) -> float | None:
    clean = [float(x) for x in values if math.isfinite(float(x)) and float(x) >= 0]
    return statistics.median(clean) if clean else None


def _closed_bars(sdk, symbol: str, timeframe: int, period: int, now: float):
    rows = sdk.copy_rates_from_pos(symbol, timeframe, 0, 80)
    if rows is None:
        return []
    bars = []
    for row in rows:
        if int(row["time"]) + period > now:
            continue
        bars.append({
            key: int(row[key]) if key in ("time", "tick_volume", "spread", "real_volume")
            else float(row[key])
            for key in row.dtype.names
        })
    return bars


def frame_measurement(sdk, symbol: str, frame_name: str, timeframe: int,
                      period: int, now: float) -> dict:
    bars = _closed_bars(sdk, symbol, timeframe, period, now)
    if len(bars) < 16:
        return {"frame": frame_name, "status": "INSUFFICIENT_CLOSED_BARS",
                "closed_bars": len(bars), "median_atr": None, "median_target": None,
                "latest_closed_bar_age_seconds": None}
    latest_age = now - (bars[-1]["time"] + period)
    atr_values = [atr(bars[max(0, index - 15):index])
                  for index in range(16, len(bars) + 1)]
    median_atr = _median(atr_values)
    return {
        "frame": frame_name,
        "status": "FRESH" if -1 <= latest_age <= period else "STALE_CLOSED_BAR",
        "closed_bars": len(bars),
        "latest_closed_bar_time_utc": datetime.fromtimestamp(
            bars[-1]["time"] + period, UTC).isoformat(),
        "latest_closed_bar_age_seconds": round(latest_age, 3),
        "median_atr": median_atr,
        "median_target_distance": 1.5 * median_atr if median_atr is not None else None,
        "atr_observations": len(atr_values),
    }


def entry_candidate_counts(sdk, symbol: str, tick, info, now: float,
                           rejection_counts: Counter) -> tuple[int, int]:
    """Measure closed-M1 strategy cards only; this function has no execution path."""
    bars = _closed_bars(sdk, symbol, sdk.TIMEFRAME_M1, 60, now)
    if len(bars) < 40 or now - (bars[-1]["time"] + 60) > 60:
        rejection_counts["STALE_OR_INSUFFICIENT_M1"] += 1
        return 0, 0
    cards = analyze_all(symbol, "M1", bars, now, {
        "tick_size": info.point, "data_kind": "broker", "calendar_profile": "CRYPTO",
    })
    candidates = [card for card in cards if card.get("status") == "READY"
                  and card.get("coverage") == "IMPLEMENTED"
                  and card.get("entry", {}).get("triggered") is True
                  and card.get("direction") in ("BUY", "SELL")]
    if not candidates:
        rejection_counts["NO_QUALIFIED_MODEL_SIGNAL"] += 1
        return 0, 0
    inside = 0
    for card in candidates:
        zone = (card.get("entry") or {}).get("zone")
        quote = tick.ask if card["direction"] == "BUY" else tick.bid
        if isinstance(zone, (list, tuple)) and len(zone) == 2 and zone[0] <= quote <= zone[1]:
            inside += 1
        else:
            rejection_counts["QUOTE_OUTSIDE_MODEL_ENTRY_ZONE"] += 1
    if inside:
        rejection_counts["CANDIDATE_INSIDE_ENTRY_ZONE"] += inside
    return len(candidates), inside


def _audit(db: sqlite3.Connection, event: str, payload: dict) -> int:
    with db:
        cur = db.execute("INSERT INTO audit(at,event,payload) VALUES (?,?,?)",
                         (time.time(), event, json.dumps(payload, separators=(",", ":"),
                                                        allow_nan=False)))
    return int(cur.lastrowid)


def run(config_path: Path, duration: int = MEASUREMENT_SECONDS) -> dict:
    import MetaTrader5 as mt5

    config = json.loads(config_path.read_text(encoding="utf-8"))
    if (config.get("demo_only") is not True or config.get("account_trade_mode") != 0
            or config.get("account_login") != 1045864
            or config.get("account_server") != "Capital.ComMena-Demo"
            or config.get("api_keys_enabled") is not False
            or config.get("live_endpoint_enabled") is not False):
        raise RuntimeError("DEMO_ONLY_CONFIG_REQUIRED")
    db_path = config_path.parent / "trades.db"
    db = sqlite3.connect(db_path, timeout=20)
    db.execute("PRAGMA busy_timeout=20000")
    event = db.execute(
        "SELECT payload FROM audit WHERE event='CRYPTO_MARKET_WATCH_INVENTORY' "
        "ORDER BY id DESC LIMIT 1").fetchone()
    if not event:
        raise RuntimeError("CRYPTO_INVENTORY_AUDIT_MISSING")
    inventory = json.loads(event[0])
    symbols = inventory.get("selected_top8", [])
    if len(symbols) != 8 or len(set(symbols)) != 8:
        raise RuntimeError("EXPECTED_EIGHT_AUDITED_CRYPTO_SYMBOLS")
    if not mt5.initialize(config["terminal_executable"], timeout=10000):
        raise RuntimeError("MT5_INITIALIZE_FAILED:" + str(mt5.last_error()))
    account, terminal = mt5.account_info(), mt5.terminal_info()
    if (account is None or terminal is None or account.login != 1045864
            or account.server != "Capital.ComMena-Demo" or account.trade_mode != 0
            or not terminal.connected):
        raise RuntimeError("DEMO_1045864_CONNECTION_REQUIRED")
    start_wall = time.time()
    start_mono = time.monotonic()
    quotes: dict[str, deque[float]] = {symbol: deque(maxlen=100_000) for symbol in symbols}
    tick_buckets: dict[str, Counter] = {symbol: Counter() for symbol in symbols}
    bucket_cutoff: dict[str, int] = {symbol: int(start_wall // 60) for symbol in symbols}
    seen_msc: dict[str, int | None] = dict.fromkeys(symbols)
    last_eval_second: dict[str, int] = {}
    last_bar: dict[str, int] = {}
    candidate_totals: Counter = Counter()
    rejection_totals: dict[str, Counter] = {symbol: Counter() for symbol in symbols}
    gates: dict[str, dict] = {}
    next_sample = start_mono + 60
    first_exception = None
    try:
        while time.monotonic() - start_mono < duration:
            now = time.time()
            account, terminal = mt5.account_info(), mt5.terminal_info()
            if (account is None or terminal is None or account.login != 1045864
                    or account.server != "Capital.ComMena-Demo" or account.trade_mode != 0
                    or not terminal.connected):
                first_exception = "DEMO_IDENTITY_OR_CONNECTION_CHANGED"
                break
            for symbol in symbols:
                info, tick = mt5.symbol_info(symbol), mt5.symbol_info_tick(symbol)
                if info is None or tick is None or not tick.time_msc:
                    rejection_totals[symbol]["MT5_QUOTE_UNAVAILABLE"] += 1
                    gates[symbol] = {"status": "PAUSED", "reason": "MT5_QUOTE_UNAVAILABLE"}
                    continue
                age = now - tick.time_msc / 1000
                fresh = -1 <= age <= MAX_AGE_SECONDS
                tradeable_mode = info.trade_mode in (1, 2, 4)
                if not tradeable_mode:
                    rejection_totals[symbol]["SYMBOL_TRADE_MODE_DISABLED_OR_CLOSE_ONLY"] += 1
                    gates[symbol] = {"status": "DISABLED", "reason": "TRADE_MODE",
                                     "trade_mode": info.trade_mode}
                    continue
                if not fresh:
                    rejection_totals[symbol]["STALE_TICK"] += 1
                    gates[symbol] = {"status": "PAUSED", "reason": "STALE_TICK",
                                     "tick_age_seconds": age}
                    continue
                spread = float(tick.ask - tick.bid)
                if not math.isfinite(spread) or spread <= 0:
                    rejection_totals[symbol]["INVALID_SPREAD"] += 1
                    continue
                msc = int(tick.time_msc)
                is_new_tick = seen_msc[symbol] != msc
                spread_history = quotes[symbol]
                if is_new_tick:
                    seen_msc[symbol] = msc
                    spread_history.append(spread)
                    bucket = int(now // 60)
                    tick_buckets[symbol][bucket] += 1
                    cutoff = bucket - 59
                    if cutoff > bucket_cutoff[symbol]:
                        for old_bucket in tuple(tick_buckets[symbol]):
                            if old_bucket < cutoff:
                                del tick_buckets[symbol][old_bucket]
                        bucket_cutoff[symbol] = cutoff
                median_spread = _median(spread_history)
                absolute_spread_cap = 3 * median_spread if median_spread is not None else None
                spread_ok = bool(median_spread and spread <= 3 * median_spread
                                 and spread <= absolute_spread_cap)
                if not spread_ok:
                    rejection_totals[symbol]["SPREAD_OUTSIDE_ROLLING_LIMIT"] += 1
                if not spread_ok:
                    gates[symbol] = {"status": "PAUSED", "reason": "SPREAD",
                                     "tick_age_seconds": age, "spread": spread,
                                     "median_spread": median_spread}
                    continue
                rates = _closed_bars(mt5, symbol, mt5.TIMEFRAME_M1, 60, now)
                if not rates:
                    rejection_totals[symbol]["STALE_OR_INSUFFICIENT_M1"] += 1
                    continue
                bar_time = int(rates[-1]["time"])
                if last_bar.get(symbol) != bar_time:
                    last_bar[symbol] = bar_time
                    second = int(now)
                    if last_eval_second.get(symbol) != second:
                        last_eval_second[symbol] = second
                        try:
                            n, inside = entry_candidate_counts(mt5, symbol, tick, info, now,
                                                               rejection_totals[symbol])
                        except (ArithmeticError, KeyError, TypeError, ValueError) as exc:
                            rejection_totals[symbol]["STRATEGY_EVALUATION_ERROR"] += 1
                            gates[symbol] = {"status": "PAUSED",
                                "reason": "STRATEGY_EVALUATION_ERROR",
                                "detail": f"{type(exc).__name__}:{exc}"}
                            continue
                        candidate_totals[symbol] += n
                        if n and not inside:
                            rejection_totals[symbol]["ENTRY_ZONE"] += n
                gates[symbol] = {"status": "WAITING_MEASUREMENT", "reason": None,
                                 "tick_age_seconds": round(age, 3), "spread": spread,
                                 "median_spread_live": median_spread,
                                 "trade_mode": info.trade_mode,
                                 "session_deals_observed_only": info.session_deals}
            elapsed = time.monotonic() - start_mono
            if time.monotonic() >= next_sample:
                sample = {"observed_utc": datetime.now(UTC).isoformat(),
                          "elapsed_seconds": round(elapsed, 1),
                          "account": 1045864, "demo_only": True, "order_send": False,
                          "symbols": {s: {"gate": gates.get(s),
                              "ticks_per_minute_current_bucket": tick_buckets[s].get(
                                  int(time.time() // 60), 0),
                              "ticks_observed_last_60_minutes": sum(tick_buckets[s].values()),
                              "candidate_cards": candidate_totals[s],
                              "rejections": dict(rejection_totals[s])} for s in symbols}}
                _audit(db, "CRYPTO_LIVE_MEASUREMENT_SAMPLE", sample)
                next_sample += 60
            time.sleep(POLL_SECONDS)
    except (ArithmeticError, KeyError, OSError, RuntimeError, sqlite3.Error,
            TypeError, ValueError) as exc:  # record observation failure, not a trade guard
        first_exception = f"{type(exc).__name__}:{exc}"
    end_wall = time.time()
    frames = {symbol: {} for symbol in symbols}
    summary_rows = []
    for symbol in symbols:
        info = mt5.symbol_info(symbol)
        spread_med = _median(quotes[symbol])
        for frame, attr, period in FRAME_SPECS:
            frame_data = frame_measurement(mt5, symbol, frame, getattr(mt5, attr), period, end_wall)
            target = frame_data["median_target_distance"]
            ratio = spread_med / target if spread_med is not None and target and target > 0 else None
            acceptable_data = frame_data["status"] == "FRESH" and len(quotes[symbol]) > 0
            accepted = bool(acceptable_data and ratio is not None and ratio <= SPREAD_TARGET_LIMIT)
            row = {"symbol": symbol, "frame": frame, "median_spread": spread_med,
                   **frame_data, "spread_to_target_ratio": ratio,
                   "limit": SPREAD_TARGET_LIMIT, "accepted": accepted,
                   "measurement_elapsed_seconds": round(end_wall - start_wall, 1),
                   "live_tick_count": sum(tick_buckets[symbol].values()),
                   "ticks_per_minute_median": _median(list(tick_buckets[symbol].values())),
                   "candidate_cards": candidate_totals[symbol],
                   "rejections": dict(rejection_totals[symbol])}
            frames[symbol][frame] = row
            summary_rows.append(row)
    best = min((r for r in summary_rows if r["spread_to_target_ratio"] is not None),
               key=lambda r: r["spread_to_target_ratio"], default=None)
    worst = max((r for r in summary_rows if r["spread_to_target_ratio"] is not None),
                key=lambda r: r["spread_to_target_ratio"], default=None)
    any_m1 = any(r["frame"] == "M1" and r["accepted"] for r in summary_rows)
    any_higher = any(r["frame"] != "M1" and r["accepted"] for r in summary_rows)
    if first_exception:
        decision = "MEASUREMENT_INCOMPLETE_NO_DECISION"
        event_name = "CRYPTO_LIVE_MEASUREMENT_INCOMPLETE"
    elif not any(r["accepted"] for r in summary_rows):
        decision = "CRYPTO_DISABLED_COST_EXCEEDS_EDGE"
        event_name = decision
    elif any_m1:
        # No entries are sent by this measurement process; M1 can be enabled only
        # by the separately verified crypto execution service, never this tool.
        decision = "M1_MEASURED_PASS_EXECUTION_SERVICE_NOT_TOUCHED"
        event_name = "CRYPTO_M1_COST_GATE_MEASURED_PASS"
    elif any_higher:
        decision = "HIGHER_TIMEFRAME_RESEARCH_ONLY"
        event_name = "CRYPTO_HIGHER_TIMEFRAME_RESEARCH_CANDIDATES"
    else:
        decision = "MEASUREMENT_COMPLETE_NO_ELIGIBLE_PAIR"
        event_name = "CRYPTO_MEASUREMENT_COMPLETE_NO_ELIGIBLE_PAIR"
    payload = {"observed_utc": datetime.now(UTC).isoformat(),
               "measurement_started_utc": datetime.fromtimestamp(start_wall, UTC).isoformat(),
               "measurement_elapsed_seconds": round(end_wall - start_wall, 1),
               "inventory_audit_id": 1124, "initial_gate_audit_id": 1128,
               "account": {"login": account.login, "server": account.server,
                           "trade_mode": account.trade_mode, "equity": account.equity},
               "terminal_connected": terminal.connected, "trade_allowed": account.trade_allowed,
               "demo_only": True, "order_check": False, "order_send": False,
               "failure": first_exception, "decision": decision,
               "best_pair": best, "worst_pair": worst, "measurement": frames}
    final_id = _audit(db, event_name, payload)
    payload["final_audit_id"] = final_id
    if decision == "CRYPTO_DISABLED_COST_EXCEEDS_EDGE":
        with db:
            db.execute("INSERT OR REPLACE INTO state(key,value) VALUES (?,?)",
                       ("crypto_disabled_for_broker", json.dumps({
                           "disabled": True, "audit_id": final_id,
                           "reason": decision, "best_ratio": best["spread_to_target_ratio"] if best else None,
                           "worst_ratio": worst["spread_to_target_ratio"] if worst else None,
                           "requires_new_explicit_authorization": True}, separators=(",", ":"))))
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False), flush=True)
    db.close()
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--duration", type=int, default=MEASUREMENT_SECONDS)
    args = parser.parse_args()
    run(args.config, max(1, args.duration))


if __name__ == "__main__":
    main()
