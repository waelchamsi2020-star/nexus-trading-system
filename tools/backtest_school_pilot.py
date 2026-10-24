"""Read-only 30-day M15 pilot using the project's existing chronological replay.

Historical bid OHLC and broker-recorded bar spread are used as provided by MT5.
The ask estimate is bid plus that recorded spread; no live tick is invented.
No order/check/position mutation function is imported or called here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import time
import urllib.request
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

import MetaTrader5 as mt5

from nexus.quant import replay
from nexus.strategies import atr
from strategies.base import Direction
from strategies.schools import REGISTRY

ROOT = Path(__file__).resolve().parents[1]
FRAME = "M15"
FRAME_SECONDS = 900
DAYS = 30
RISK_FRACTION = 0.01
COMMISSION_RESERVE_PER_LOT_USD = 7.0
SLIPPAGE_POINTS = 10
LEGACY_REPLAY_IDS = {"price_action": "engulfing", "market_structure": "dow_structure"}


def eligible_from_running_app(origin: str) -> list[str]:
    for attempt in range(5):
        with urllib.request.urlopen(origin, timeout=6) as response:
            html = response.read().decode("utf-8")
        match = re.search(r'name="nexus-token" content="([^"]+)"', html)
        if not match:
            raise RuntimeError("running app session token unavailable")
        request = urllib.request.Request(
            origin + "/api/state", headers={"X-Nexus-Token": match.group(1)}
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            state = json.load(response)
        account = state.get("account") or {}
        if account.get("login") != 1045864 or account.get("trade_mode") != 0:
            raise RuntimeError("discovery is not Capital demo account 1045864")
        scan = state.get("scan") or {}
        symbols = sorted({row["symbol"] for row in scan.get("rows", []) if row.get("eligible") is True})
        if scan.get("complete") and symbols:
            return symbols
        if attempt < 4:
            time.sleep(2)
    return []


def school_card(name: str, history: list[dict], decision_time: float, point: float) -> dict:
    school = REGISTRY[name]()
    bar = history[-1]
    spread = float(bar["spread"]) * point
    close = float(bar["close"])
    signal = school.evaluate(
        history,
        {"bid": close, "ask": close + spread, "source": "MT5_RECORDED_BAR_SPREAD"},
        {"closed_index": len(history) - 1, "decision_time": decision_time, "session_open": True},
    )
    if signal.direction is Direction.NONE:
        return {"status": "NONE", "reason": signal.reason}
    scale = atr(history)
    return {
        "status": "READY", "coverage": "IMPLEMENTED", "direction": signal.direction.value,
        "entry": {"triggered": True, "zone": [close - 0.5 * scale, close + 0.5 * scale]},
        "stop": {"price": signal.sl_hint}, "targets": [{"price": signal.tp_hint}],
        "invalidation": {"price": signal.sl_hint},
        "execution_plan": {"max_hold_bars": 12},
    }


def stats(trades: list[dict], start: datetime) -> dict:
    values = [float(trade["r"]) for trade in trades]
    wins = sum(value > 0 for value in values)
    profit = sum(max(value, 0) for value in values)
    loss = sum(max(-value, 0) for value in values)
    equity = peak = 1.0
    max_dd = 0.0
    for value in values:
        equity *= max(0, 1 + RISK_FRACTION * value)
        peak = max(peak, equity)
        max_dd = max(max_dd, (peak - equity) / peak)
    by_day = defaultdict(float)
    for trade in trades:
        day = datetime.fromtimestamp(trade["exit_time"], UTC).date()
        by_day[day] += RISK_FRACTION * float(trade["r"])
    daily = [by_day.get((start + timedelta(days=index)).date(), 0.0) for index in range(DAYS)]
    deviation = statistics.stdev(daily) if len(daily) > 1 else 0.0
    sharpe = statistics.fmean(daily) / deviation * math.sqrt(365) if deviation > 0 else None
    holding = [
        (trade["exit_time"] - trade["entry_time"]) / 60 for trade in trades
    ]
    return {
        "trades": len(trades), "winrate": wins / len(trades) if trades else None,
        "rr": profit / loss if loss else None, "maxDD": max_dd if trades else None,
        "sharpe": sharpe, "PF": profit / loss if loss else None,
        "holding_min": statistics.fmean(holding) if holding else None,
        "net_R": sum(values),
    }


def run(origin: str, terminal: str, commission_per_lot: float) -> dict:
    symbols = eligible_from_running_app(origin)
    if not symbols:
        raise RuntimeError("running discovery has no eligible symbols")
    if not mt5.initialize(path=terminal):
        raise RuntimeError(f"MT5 read-only connection failed: {mt5.last_error()}")
    try:
        account = mt5.account_info()
        if account is None or account.login != 1045864 or account.trade_mode != 0:
            raise RuntimeError("broker is not the authorized demo account")
        end = datetime.now(UTC)
        start = end - timedelta(days=DAYS)
        rows = []
        school_trades = {name: [] for name in REGISTRY}
        for symbol in symbols:
            info = mt5.symbol_info(symbol)
            raw = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M15, start, end)
            if info is None or raw is None:
                for name in REGISTRY:
                    rows.append({"school": name, "symbol": symbol, "timeframe": FRAME,
                                 "status": "NO_BROKER_HISTORY", "metrics": stats([], start)})
                continue
            bars = [
                {key: float(bar[key]) if key in {"open", "high", "low", "close"}
                 else int(bar[key]) for key in raw.dtype.names}
                for bar in raw if int(bar["time"]) + FRAME_SECONDS <= end.timestamp()
            ]
            complete = bool(bars and bars[0]["time"] <= start.timestamp() + FRAME_SECONDS * 2
                            and bars[-1]["time"] + FRAME_SECONDS >= end.timestamp() - FRAME_SECONDS * 2)
            for name in REGISTRY:
                if not complete or len(bars) < 100:
                    rows.append({"school": name, "symbol": symbol, "timeframe": FRAME,
                                 "status": "INCOMPLETE_30_DAY_HISTORY", "bars": len(bars),
                                 "metrics": stats([], start)})
                    continue
                point = float(info.point)
                tick_value = float(info.trade_tick_value)
                tick_size = float(info.trade_tick_size)
                volume = float(info.volume_min)
                if min(point, tick_value, tick_size, volume) <= 0:
                    rows.append({"school": name, "symbol": symbol, "timeframe": FRAME,
                                 "status": "INVALID_CONTRACT_METADATA", "metrics": stats([], start)})
                    continue
                fee_money = commission_per_lot * volume
                fee_price = fee_money / (tick_value / tick_size * volume)
                config = {"point": point, "slippage_price": SLIPPAGE_POINTS * point,
                          "commission_per_unit": fee_price, "lookback": 300, "max_hold_bars": 12}
                legacy_id = LEGACY_REPLAY_IDS[name]
                try:
                    result = replay(
                        bars, legacy_id, symbol, FRAME, config=config,
                        context={"tick_size": tick_size},
                        signal_fn=lambda history, time, n=name, p=point: school_card(n, history, time, p),
                    )
                    school_trades[name].extend(result["trades"])
                    rows.append({"school": name, "symbol": symbol, "timeframe": FRAME,
                                 "status": "REPLAYED", "bars": len(bars),
                                 "signals": result["signals"], "skipped": len(result["skipped"]),
                                 "metrics": stats(result["trades"], start)})
                except (ValueError, TypeError, KeyError) as exc:
                    rows.append({"school": name, "symbol": symbol, "timeframe": FRAME,
                                 "status": "REPLAY_ERROR", "reason": type(exc).__name__ + ": " + str(exc)[:180],
                                 "metrics": stats([], start)})
        summaries = {}
        for name, trades in school_trades.items():
            trades.sort(key=lambda trade: (trade["exit_time"], trade["entry_time"], trade["symbol"]))
            measurements = stats(trades, start)
            symbols_with_ten = sum(
                row["metrics"]["trades"] >= 10 for row in rows if row["school"] == name
            )
            pf, sharpe, drawdown = (
                measurements["PF"], measurements["sharpe"], measurements["maxDD"]
            )
            numeric_pass = (
                measurements["trades"] >= 30 and pf is not None and pf >= 1.2
                and drawdown is not None and drawdown <= 0.10
                and sharpe is not None and sharpe >= 0.5 and symbols_with_ten >= 3
            )
            summaries[name] = {**measurements, "symbols_with_10_trades": symbols_with_ten,
                               "numeric_pass": numeric_pass, "costs_verified": False,
                               "verdict": "RESEARCH" if numeric_pass else "DISABLE_PILOT"}
        return {"schema_version": 1, "generated_at_utc": datetime.now(UTC).isoformat(),
                "account": "Capital.ComMena-Demo / 1045864 / mode=0", "period_start_utc": start.isoformat(),
                "period_end_utc": end.isoformat(), "timeframe": FRAME, "discovery_symbols": symbols,
                "model": "nexus.quant.replay; next-open bid OHLC and recorded bar spread; stop-first ambiguity",
                "commission_policy": (
                    f"{commission_per_lot:g} USD/lot scenario; zero-fee scenario matches observed "
                    "deal commission fields but is not verified for every symbol"
                ),
                "slippage_policy": "10 broker points adverse per fill", "risk_fraction_for_maxDD": RISK_FRACTION,
                "sharpe_definition": "daily R returns over 30 calendar days, annualized sqrt(365); indicative only",
                "activation_authority": False, "summary": summaries, "rows": rows}
    finally:
        mt5.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--origin", default="http://127.0.0.1:50083")
    parser.add_argument("--terminal", default=r"C:\Program Files\Capital.com MetaTrader 5\terminal64.exe")
    parser.add_argument("--commission-per-lot", type=float, default=COMMISSION_RESERVE_PER_LOT_USD)
    parser.add_argument("--output", default="pilot-b1-backtest.json")
    args = parser.parse_args()
    if not math.isfinite(args.commission_per_lot) or args.commission_per_lot < 0:
        raise ValueError("commission scenario must be finite and nonnegative")
    result = run(args.origin, args.terminal, args.commission_per_lot)
    destination = ROOT / "outputs" / args.output
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print("rows", len(result["rows"]), "sha256", hashlib.sha256(destination.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
