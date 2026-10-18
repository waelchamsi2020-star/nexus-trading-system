"""Read-only native cross-symbol support_bounce research; no execution authority.

Uses the exact segment/window policy of segment_research. USD round-trip fee
scenarios are converted into the profit currency at the observed historical
exit quote when the traded pair is USDJPY. No current FX rate is substituted.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nexus.quant import walk_forward
from nexus.segment_research import split_segments, summarize
from nexus.strategies import REGISTRY, validate_bars
from nexus.timeframes import bar_close_time
from nexus.walkforward import LookaheadBiasError

MODEL = "support_bounce"
PROFILE = "FX_UTC22_V1"


def quote_fee(usd_fee, *, symbol, profit_currency, contract_size, exit_quote):
    """USD scenario to quote-price units per lot, with a historical conversion."""
    if (not math.isfinite(usd_fee) or usd_fee < 0 or
            not math.isfinite(contract_size) or contract_size <= 0):
        raise ValueError("Invalid explicit commission or contract size")
    if profit_currency == "USD":
        conversion = 1.
    elif symbol == "USDJPY" and profit_currency == "JPY":
        if not math.isfinite(exit_quote) or exit_quote <= 0:
            raise ValueError("Positive historical USDJPY exit quote required")
        conversion = exit_quote
    else:
        raise ValueError("Historical USD/profit conversion unsupported; never invent a rate")
    return usd_fee * conversion / contract_size


def reprice_usd(trades, *, symbol, profit_currency, contract_size, commission):
    result = []
    for trade in trades:
        risk = abs(trade["entry"] - trade["stop"])
        if not math.isfinite(risk) or risk <= 0:
            raise ValueError("Positive structural risk required")
        fee = quote_fee(commission, symbol=symbol, profit_currency=profit_currency,
                        contract_size=contract_size, exit_quote=trade["exit"])
        net = trade["gross_price_pnl"] - fee
        result.append({**trade, "commission_usd_round_trip_per_lot": commission,
                       "commission_price_units": fee, "net_price_pnl": net,
                       "r": net / risk})
    return result


def evaluate(bars, *, symbol, specification, as_of, commission=7.):
    if not bars:
        raise ValueError("No native historical bars")
    if any(bar_close_time(row["time"], "H1") > as_of for row in bars):
        raise LookaheadBiasError("Future or incomplete native candle")
    validate_bars(bars, "H1", as_of)
    point = specification["point"]
    contract_size = specification["contract_size"]
    if not math.isfinite(point) or point <= 0:
        raise ValueError("Positive observed point required")
    # Validate currency even if replay happens to produce no trades.
    quote_fee(commission, symbol=symbol, profit_currency=specification["profit_currency"],
              contract_size=contract_size, exit_quote=bars[-1]["close"])
    segments = split_segments(bars, "H1", PROFILE)
    selected = [i for i, rows in enumerate(segments) if len(rows) >= 200]
    fallback = not selected
    if fallback:
        selected = [max(range(len(segments)), key=lambda i: len(segments[i]))]
    inventory = [{"segment": i, "bars": len(rows), "selected": i in selected,
                  "first_time": rows[0]["time"], "last_time": rows[-1]["time"]}
                 for i, rows in enumerate(segments)]
    all_trades, folds = [], []
    for index in selected:
        rows = segments[index]
        n = len(rows)
        train = min(250, max(1, n // 2))
        test = min(100, max(1, (n - train - 12) // 2))
        review = walk_forward(rows, MODEL, symbol, "H1", config={
            "point": point, "slippage_price": 10 * point,
            "commission_per_unit": 0., "commission_known": True,
            "train_bars": train, "test_bars": test, "embargo_bars": 12,
        }, data_kind="broker", context={"tick_size": point, "calendar_profile": PROFILE})
        for fold in review["folds"]:
            trades = reprice_usd(fold["trades"], symbol=symbol,
                profit_currency=specification["profit_currency"],
                contract_size=contract_size, commission=commission)
            all_trades.extend({"segment": index, **trade} for trade in trades)
            folds.append({"segment": index, "train_bars": train, "test_bars": test,
                          **{key: fold[key] for key in (
                              "train_start_index", "train_end_exclusive", "test_start_index",
                              "test_end_exclusive", "signals", "skipped")},
                          "trades": len(trades)})
    return {"symbol": symbol, "model": MODEL, "model_version": REGISTRY[MODEL]["version"],
            "bars": len(bars), "specification": specification,
            "commission_usd_round_trip_per_lot": commission,
            "commission_policy": "Hypothetical USD 7/lot round trip; actual broker fee unverified",
            "slippage_points_per_side": 10, "spread_policy": "Each native bar spread times observed point",
            "calendar_profile": PROFILE, "segments": inventory,
            "selected_segments": len(selected), "fallback_largest_below_200": fallback,
            "folds": folds, "trade_records": all_trades, **summarize(all_trades),
            "qualified": False, "execution_authority": False, "orders_sent": 0,
            "limitations": [
                "Frozen support_bounce v1.1.0 and identical segment/window policy; no optimization",
                "FX_UTC22_V1 is an unverified fixed research calendar, including for gold",
                "No candles or positions carried across unexplained gaps; short segments excluded",
                "USDJPY fee uses historical replay exit quote as a conversion approximation; no historical conversion bid/ask execution reconstructed",
                "R divides net profit-currency price PnL by structural quote-price risk; not portfolio or fixed USD risk return",
                "Trade Sharpe is nonannualized; positive net R does not prove significance or cross-market edge",
                "Native broker source is locally observed, not independently authenticated",
            ]}


def export_native(mt5, symbol, count, as_of, data_dir):
    info = mt5.symbol_info(symbol)
    if info is None:
        raise ValueError(f"MT5 symbol unavailable: {symbol}; {mt5.last_error()}")
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, count + 1)
    if rates is None:
        raise ValueError(f"MT5 history unavailable: {symbol}; {mt5.last_error()}")
    bars = [{"time": int(row["time"]), "open": float(row["open"]),
             "high": float(row["high"]), "low": float(row["low"]),
             "close": float(row["close"]), "tick_volume": int(row["tick_volume"]),
             "spread": int(row["spread"]), "real_volume": int(row["real_volume"])}
            for row in rates if bar_close_time(int(row["time"]), "H1") <= as_of][-count:]
    validate_bars(bars, "H1", as_of)
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / f"{symbol}_H1.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(["<DATE>", "<TIME>", "<OPEN>", "<HIGH>", "<LOW>", "<CLOSE>", "<TICKVOL>", "<VOL>", "<SPREAD>"])
        for row in bars:
            stamp = datetime.fromtimestamp(row["time"], UTC)
            writer.writerow([stamp.strftime("%Y.%m.%d"), stamp.strftime("%H:%M:%S"),
                             *(repr(row[key]) for key in ("open", "high", "low", "close")),
                             row["tick_volume"], row["real_volume"], row["spread"]])
    specification = {"point": info.point, "contract_size": info.trade_contract_size,
                     "profit_currency": info.currency_profit, "base_currency": info.currency_base,
                     "trade_tick_size": info.trade_tick_size}
    metadata = {"source": "MT5_NATIVE", "symbol": symbol, "timeframe": "H1",
                "timezone": "UTC", "aggregated": False, "completed_only": True,
                "as_of": as_of, "requested": count, "returned": len(bars),
                "specification": specification,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    path.with_suffix(".metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return bars, specification, metadata, path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="+", default=["GBPUSD", "USDJPY", "XAUUSD"])
    parser.add_argument("--count", type=int, default=10000)
    parser.add_argument("--output", type=Path, default=ROOT / "reports/statistical-validation/symbol-generalization.json")
    args = parser.parse_args()
    if args.count < 10000:
        parser.error("At least 10000 native completed bars must be requested")
    import MetaTrader5 as mt5
    if not mt5.initialize():
        raise RuntimeError(f"Read-only MT5 initialize failed: {mt5.last_error()}")
    as_of = time.time()
    rows = []
    try:
        for symbol in args.symbols:
            try:
                bars, specification, metadata, path = export_native(
                    mt5, symbol, args.count, as_of, ROOT / "data/real/H1")
                result = evaluate(bars, symbol=symbol, specification=specification, as_of=as_of)
                result.update(data_file=str(path.relative_to(ROOT)), data_sha256=metadata["sha256"],
                              requested_bars=args.count, at_least_10000=len(bars) >= 10000)
                print(json.dumps({"symbol": symbol, "bars": len(bars), "trades": result["trades"],
                                  "net_r": result["net_r"], "selected_segments": result["selected_segments"]}), flush=True)
            except (ValueError, RuntimeError) as error:
                result = {"symbol": symbol, "status": "UNAVAILABLE", "error": str(error),
                          "qualified": False, "execution_authority": False, "orders_sent": 0}
                print(json.dumps(result), flush=True)
            rows.append(result)
    finally:
        mt5.shutdown()
    positive = [r["symbol"] for r in rows if r.get("trades", 0) > 0 and r.get("net_r", 0) > 0]
    report = {"type": "READ_ONLY_CROSS_SYMBOL_PRELIMINARY", "created_utc": datetime.now(UTC).isoformat(),
              "as_of": as_of, "rows": rows, "positive_symbols": positive,
              "three_symbols_positive": len(positive) >= 3,
              "at_least_30_trades_each": all(r.get("trades", 0) >= 30 for r in rows),
              "qualified": False, "execution_authority": False, "orders_sent": 0,
              "model_source_sha256": hashlib.sha256((ROOT / "src/nexus/strategies.py").read_bytes()).hexdigest(),
              "config_sha256": hashlib.sha256((ROOT / "src/nexus/config/models.yaml").read_bytes()).hexdigest(),
              "replay_source_sha256": hashlib.sha256((ROOT / "src/nexus/quant.py").read_bytes()).hexdigest()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    lines = ["# Native cross-symbol support_bounce H1; USD7/lot round trip", "",
             "| symbol | native bars | segments selected | trades | win rate | net R | trade Sharpe | max DD R |",
             "|---|---|---|---|---|---|---|---|"]
    for row in rows:
        if "trades" in row:
            lines.append("| " + " | ".join(str(row[key]) for key in (
                "symbol", "bars", "selected_segments", "trades", "win_rate", "net_r", "sharpe", "max_dd")) + " |")
        else:
            lines.append(f"| {row['symbol']} | UNAVAILABLE: {row['error']} | | | | | | |")
    lines.extend(["", "Three symbols positive: " + str(report["three_symbols_positive"]),
                  "Thirty trades each: " + str(report["at_least_30_trades_each"]),
                  "Qualified: false. No live changes or broker orders.", "",
                  "Same fixed model/config and >=200 segment selection, largest fallback, training=min(250,N//2),",
                  "test=min(100,(N-training-12)//2), embargo12; commission USD7 and slippage10points/side, native row spread.",
                  "USDJPY fee converted at each historical replay exit quote; profit-currency price-risk R, not account USD portfolio return.",
                  "Calendar fixed FX UTC22 is not broker-verified; gold daily maintenance gaps may leave insufficient eligible history."])
    args.output.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
