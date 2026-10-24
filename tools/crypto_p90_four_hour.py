"""Read-only four-hour Crypto p90 spread/target measurement on Capital Demo."""
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
from nexus.strategies import atr

FRAME_SPECS = {
    "M15": ("TIMEFRAME_M15", 900),
    "H1": ("TIMEFRAME_H1", 3600),
}
MIN_DURATION_SECONDS = 4 * 60 * 60
POLL_SECONDS = 0.25
MAX_TICK_AGE_SECONDS = 2.0
P90_TARGET_LIMIT = 0.20
SAMPLE_AUDIT_INTERVAL = 15 * 60


def _median(values):
    clean = [float(v) for v in values if math.isfinite(float(v)) and float(v) >= 0]
    return statistics.median(clean) if clean else None


def _p90(values):
    clean = sorted(float(v) for v in values if math.isfinite(float(v)) and float(v) >= 0)
    if not clean:
        return None
    return clean[max(0, math.ceil(0.90 * len(clean)) - 1)]


def _closed_bars(mt5, symbol: str, timeframe: int, period: int, now: float):
    rows = mt5.copy_rates_from_pos(symbol, timeframe, 0, 80)
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


def _audit(db: sqlite3.Connection, event: str, payload: dict) -> int:
    with db:
        cur = db.execute("INSERT INTO audit(at,event,payload) VALUES (?,?,?)",
                         (time.time(), event, json.dumps(payload, separators=(",", ":"),
                                                         allow_nan=False)))
    return int(cur.lastrowid)


def run(config_path: Path, duration: int = MIN_DURATION_SECONDS):
    import MetaTrader5 as mt5

    if duration < MIN_DURATION_SECONDS:
        raise ValueError("FOUR_CONTIGUOUS_HOURS_REQUIRED")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if (config.get("demo_only") is not True or config.get("account_trade_mode") != 0
            or config.get("account_login") != 1045864
            or config.get("account_server") != "Capital.ComMena-Demo"
            or config.get("api_keys_enabled") is not False
            or config.get("live_endpoint_enabled") is not False):
        raise RuntimeError("DEMO_ONLY_CONFIG_REQUIRED")

    db = sqlite3.connect(config_path.parent / "trades.db", timeout=20)
    db.execute("PRAGMA busy_timeout=20000")
    risk_audit_row = db.execute(
        "SELECT id,payload FROM audit WHERE event='CRYPTO_STAGE2_ACTUAL_CONTRACT_RISK' "
        "ORDER BY id DESC LIMIT 1").fetchone()
    if not risk_audit_row:
        raise RuntimeError("STAGE2_RISK_AUDIT_MISSING")
    risk_audit_id, risk_payload = risk_audit_row
    risk_payload = json.loads(risk_payload)
    accepted_pairs = [r for r in risk_payload["rows"] if r.get("pass_stage_2")]
    pairs = {(r["symbol"], r["frame"]) for r in accepted_pairs}
    symbols = sorted({s for s, _ in pairs})
    expected = {("BTCUSD", "M15"), ("BTCUSD", "H1"),
                ("ETHUSD", "M15"), ("ETHUSD", "H1")}
    if pairs != expected:
        raise RuntimeError("STAGE2_ACCEPTED_PAIR_SET_CHANGED")

    if not mt5.initialize(config["terminal_executable"], timeout=10000):
        raise RuntimeError(f"MT5_INITIALIZE_FAILED:{mt5.last_error()}")
    account, terminal = mt5.account_info(), mt5.terminal_info()
    if (account is None or terminal is None or account.login != 1045864
            or account.server != "Capital.ComMena-Demo" or account.trade_mode != 0
            or not terminal.connected):
        raise RuntimeError("DEMO_1045864_CONNECTION_REQUIRED")

    start_audit_id = _audit(db, "CRYPTO_P90_FOUR_HOUR_MEASUREMENT_STARTED", {
        "started_utc": datetime.now(UTC).isoformat(),
        "required_seconds": duration,
        "symbols": symbols,
        "pairs": sorted([{"symbol": s, "frame": tf} for s, tf in pairs],
                         key=lambda x: (x["symbol"], x["frame"])),
        "stage2_risk_audit_id": risk_audit_id,
        "account": 1045864, "server": "Capital.ComMena-Demo",
        "trade_mode": 0, "demo_only": True,
        "order_check": False, "order_send": False,
    })

    start_wall = time.time()
    start_mono = time.monotonic()
    spreads = {s: deque(maxlen=200_000) for s in symbols}
    atr_samples = {(s, tf): [] for s, tf in pairs}
    last_tick_msc = dict.fromkeys(symbols)
    last_bar_time = {(s, tf): None for s, tf in pairs}
    stale_poll_observations = Counter()
    invalid_spread_observations = Counter()
    valid_tick_minute_buckets = {s: Counter() for s in symbols}
    next_audit = start_mono + SAMPLE_AUDIT_INTERVAL
    failure = None
    try:
        while time.monotonic() - start_mono < duration:
            now = time.time()
            account, terminal = mt5.account_info(), mt5.terminal_info()
            if (account is None or terminal is None or account.login != 1045864
                    or account.server != "Capital.ComMena-Demo" or account.trade_mode != 0
                    or not terminal.connected):
                failure = "DEMO_IDENTITY_OR_CONNECTION_CHANGED"
                break

            for symbol in symbols:
                tick = mt5.symbol_info_tick(symbol)
                if tick is None or not tick.time_msc:
                    stale_poll_observations[symbol] += 1
                    continue
                age = now - tick.time_msc / 1000
                if age < -1 or age > MAX_TICK_AGE_SECONDS:
                    stale_poll_observations[symbol] += 1
                    continue
                msc = int(tick.time_msc)
                if last_tick_msc[symbol] != msc:
                    last_tick_msc[symbol] = msc
                    spread = float(tick.ask - tick.bid)
                    if not math.isfinite(spread) or spread <= 0:
                        invalid_spread_observations[symbol] += 1
                    else:
                        spreads[symbol].append(spread)
                        valid_tick_minute_buckets[symbol][int(now // 60)] += 1

            for symbol, frame in pairs:
                attr, period = FRAME_SPECS[frame]
                bars = _closed_bars(mt5, symbol, getattr(mt5, attr), period, now)
                if len(bars) < 16:
                    continue
                bar_close = int(bars[-1]["time"]) + period
                if bar_close <= now and last_bar_time[(symbol, frame)] != bar_close:
                    last_bar_time[(symbol, frame)] = bar_close
                    value = float(atr(bars[-15:], period=14))
                    if math.isfinite(value) and value > 0:
                        atr_samples[(symbol, frame)].append({
                            "closed_bar_utc": datetime.fromtimestamp(bar_close, UTC).isoformat(),
                            "atr": value,
                        })

            elapsed = time.monotonic() - start_mono
            if time.monotonic() >= next_audit:
                partial = {}
                for symbol in symbols:
                    partial[symbol] = {
                        "fresh_unique_ticks": len(spreads[symbol]),
                        "average_ticks_per_elapsed_minute": round(
                            len(spreads[symbol]) / max(elapsed / 60, 1e-9), 3),
                        "median_spread": _median(spreads[symbol]),
                        "p90_spread": _p90(spreads[symbol]),
                        "stale_tick_poll_observations": stale_poll_observations[symbol],
                        "invalid_spread_observations": invalid_spread_observations[symbol],
                        "frames": {
                            frame: {
                                "median_atr_samples": _median(
                                    [x["atr"] for x in atr_samples[(symbol, frame)]]),
                                "atr_sample_count": len(atr_samples[(symbol, frame)]),
                                "latest_closed_bar_sample": (
                                    atr_samples[(symbol, frame)][-1]
                                    if atr_samples[(symbol, frame)] else None),
                            }
                            for frame in ("M15", "H1") if (symbol, frame) in pairs
                        },
                    }
                _audit(db, "CRYPTO_P90_LIVE_MEASUREMENT_SAMPLE", {
                    "observed_utc": datetime.now(UTC).isoformat(),
                    "elapsed_seconds": round(elapsed, 1), "account": 1045864,
                    "demo_only": True, "order_check": False, "order_send": False,
                    "start_audit_id": start_audit_id,
                    "stage2_audit_id": risk_audit_id, "symbols": partial,
                })
                next_audit += SAMPLE_AUDIT_INTERVAL
            time.sleep(POLL_SECONDS)
    except (ArithmeticError, KeyError, OSError, RuntimeError, sqlite3.Error,
            TypeError, ValueError) as exc:
        failure = f"{type(exc).__name__}:{exc}"

    elapsed = time.monotonic() - start_mono
    rows = []
    for symbol, frame in sorted(pairs):
        spread_median = _median(spreads[symbol])
        spread_p90 = _p90(spreads[symbol])
        atr_values = [x["atr"] for x in atr_samples[(symbol, frame)]]
        atr_median = _median(atr_values)
        target = 1.5 * atr_median if atr_median is not None else None
        ratio = spread_p90 / target if spread_p90 is not None and target and target > 0 else None
        sufficient = elapsed >= MIN_DURATION_SECONDS and len(spreads[symbol]) >= 100 and bool(atr_values)
        passed = bool(failure is None and sufficient and ratio is not None
                      and ratio <= P90_TARGET_LIMIT)
        if passed:
            status, reason = "RESEARCH_CANDIDATE", "NO_M15_H1_EXECUTION_STRATEGY_APPROVED"
        elif failure:
            status, reason = "MEASUREMENT_INCOMPLETE", failure
        elif not sufficient:
            status, reason = "DISABLED", "INSUFFICIENT_LIVE_SAMPLE"
        else:
            status, reason = "DISABLED", "P90_SPREAD_EXCEEDS_20_PERCENT_OF_TARGET"
        risk = next(r for r in accepted_pairs if r["symbol"] == symbol and r["frame"] == frame)
        rows.append({
            "symbol": symbol, "frame": frame, "median_spread": spread_median,
            "p90_spread": spread_p90, "median_atr": atr_median,
            "target_1_5x_median_atr": target, "p90_spread_to_target_ratio": ratio,
            "limit": P90_TARGET_LIMIT, "fresh_unique_ticks": len(spreads[symbol]),
            "average_ticks_per_elapsed_minute": round(len(spreads[symbol]) / max(elapsed / 60, 1e-9), 3),
            "stale_tick_poll_observations": stale_poll_observations[symbol],
            "invalid_spread_observations": invalid_spread_observations[symbol],
            "atr_samples": atr_samples[(symbol, frame)],
            "stage2_risk": risk, "stage3_pass": passed,
            "final_status": status, "reason": reason,
        })

    final_event = "CRYPTO_P90_FOUR_HOUR_MEASUREMENT_COMPLETE" if failure is None and elapsed >= MIN_DURATION_SECONDS else "CRYPTO_P90_FOUR_HOUR_MEASUREMENT_INCOMPLETE"
    final_payload = {
        "recorded_utc": datetime.now(UTC).isoformat(),
        "measurement_started_utc": datetime.fromtimestamp(start_wall, UTC).isoformat(),
        "elapsed_seconds": round(elapsed, 1), "required_seconds": MIN_DURATION_SECONDS,
        "source_risk_audit_id": risk_audit_id, "account": 1045864,
        "start_audit_id": start_audit_id,
        "server": "Capital.ComMena-Demo", "trade_mode": 0,
        "demo_only": True, "terminal_connected": True,
        "order_check": False, "order_send": False, "failure": failure,
        "threshold": "p90_spread <= 0.20 * (1.5 * median ATR measured during this 4-hour window)",
        "rows": rows,
    }
    final_id = _audit(db, final_event, final_payload)
    final_payload["final_audit_id"] = final_id
    with db:
        for row in rows:
            db.execute("INSERT OR REPLACE INTO state(key,value) VALUES(?,?)", (
                f"crypto_pair_status:{row['symbol']}:{row['frame']}",
                json.dumps({"status": row["final_status"], "reason": row["reason"],
                            "audit_id": final_id,
                            "requires_new_explicit_authorization": row["final_status"] == "DISABLED"},
                           separators=(",", ":"))))
    print(json.dumps(final_payload, ensure_ascii=False, separators=(",", ":"),
                    allow_nan=False), flush=True)
    db.close()
    mt5.shutdown()
    return final_payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--duration", type=int, default=MIN_DURATION_SECONDS)
    args = parser.parse_args()
    run(args.config, args.duration)


if __name__ == "__main__":
    main()
