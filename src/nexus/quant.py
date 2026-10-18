"""Chronological fixed-rule research; historical evidence never unlocks Real.

OHLC replay is deliberately conservative: signal at completed close, fill at
the next open, stop before target when both are touched in an unknown path.
"""
from __future__ import annotations

import math
import statistics
from concurrent.futures import CancelledError

from .strategies import (
    PERIODS,
    REGISTRY,
    analyze_strategy,
    atr,
    bar_close_time,
    configured_minimum,
    validate_bars,
)

DEFAULTS = {"train_bars": 250, "test_bars": 180, "embargo_bars": 12,
            "max_hold_bars": 12, "min_oos_trades": 30, "min_profit_factor": 1.05,
            "max_drawdown_r": 10.0, "point": 0.0, "slippage_price": 0.0,
            "commission_per_unit": 0.0, "commission_known": False,
            "lookback": 300}

AR_REASONS = {
    "partial/unimplemented strategy cannot qualify": "الاستراتيجية الجزئية أو غير المنفذة لا يمكن تأهيلها",
    "synthetic/simulation/unverified data is never eligible for broker execution": "بيانات اصطناعية أو محاكاة أو غير موثقة لا تؤهل التنفيذ لدى الوسيط",
    "spread scale or actual commission policy unknown": "وحدة السبريد أو سياسة العمولة الفعلية غير معروفة",
    "insufficient chronological training/embargo/test history": "التاريخ غير كافٍ لتقسيم التدريب والحظر والاختبار زمنياً",
    "fewer than required OOS trades": "عدد الصفقات خارج العينة أقل من الحد المطلوب",
    "OOS profit factor unmeasurable or below threshold": "معامل الربح خارج العينة غير قابل للقياس أو دون العتبة",
    "nonpositive or unmeasurable cost-adjusted expectancy": "متوسط العائد بعد التكاليف غير موجب أو غير قابل للقياس",
    "OOS drawdown exceeds fixed threshold": "التراجع خارج العينة يتجاوز الحد الثابت",
    "at least two separate chronological OOS folds required": "يلزم مقطعان منفصلان للاختبار خارج العينة زمنياً",
}


def _translate_result(result):
    result["reason_codes"] = list(result["reasons"])
    result["reasons"] = [f"{AR_REASONS.get(r, r)} ({r})" for r in result["reasons"]]
    return result


def _settings(config):
    settings = {**DEFAULTS, **(config or {})}
    for key in ("train_bars", "test_bars", "embargo_bars", "max_hold_bars", "min_oos_trades", "lookback"):
        if isinstance(settings[key], bool) or not isinstance(settings[key], int) or settings[key] <= 0:
            raise ValueError(f"positive integer required for {key}")
    for key in ("point", "slippage_price", "commission_per_unit", "min_profit_factor", "max_drawdown_r"):
        if not math.isfinite(settings[key]) or settings[key] < 0:
            raise ValueError(f"invalid {key}")
    if "spread_price" in settings and (not math.isfinite(settings["spread_price"]) or settings["spread_price"] < 0):
        raise ValueError("invalid spread_price")
    settings["embargo_bars"] = max(settings["embargo_bars"], settings["max_hold_bars"])
    # Configuration may tighten evidence gates, never reduce these defaults.
    settings["min_oos_trades"] = max(30, settings["min_oos_trades"])
    settings["min_profit_factor"] = max(1.05, settings["min_profit_factor"])
    settings["max_drawdown_r"] = min(10.0, settings["max_drawdown_r"])
    return settings


def _spread(bar, settings):
    return settings["spread_price"] if "spread_price" in settings else bar.get("spread", 0)*settings["point"]


def replay(bars: list[dict], strategy_id: str, symbol: str = "RESEARCH", timeframe: str = "H1",
           start_index: int | None = None, end_index: int | None = None, config: dict | None = None,
           context: dict | None = None, signal_fn=None, cancel_event=None) -> dict:
    """Independent one-position replay; all result prices use the same quote unit.

    signal_fn is a dependency-injection hook for execution-path tests. Such a
    replay cannot issue a quant qualification certificate.
    """
    settings = _settings(config)
    if not bars:
        return {"trades": [], "signals": 0, "skipped": [], "metrics": metrics([])}
    validate_bars(bars, timeframe, bar_close_time(bars[-1]["time"],timeframe))
    minimum = configured_minimum(strategy_id,context)
    start = max(minimum-1, start_index if start_index is not None else minimum-1)
    end = min(len(bars), end_index if end_index is not None else len(bars))
    if start < 0 or end <= start:
        return {"trades": [], "signals": 0, "skipped": [], "metrics": metrics([])}
    trades, skipped, signals = [], [], 0
    signal_index = start
    while signal_index < end-1:
        if cancel_event is not None and cancel_event.is_set():
            raise CancelledError("Research cancelled on application shutdown")
        lookback = max(settings["lookback"],minimum)
        if strategy_id == "vwap_reclaim":
            # Match the live anchored-VWAP context: one complete UTC day plus
            # a small bar-alignment margin, including on M1/M2 charts.
            lookback = max(lookback, math.ceil(86400 / PERIODS[timeframe]) + 3)
        history = bars[max(0, signal_index+1-lookback):signal_index+1]
        decision_time = bar_close_time(history[-1]["time"],timeframe)
        card = signal_fn(history, decision_time) if signal_fn else analyze_strategy(strategy_id, symbol, timeframe, history, decision_time, context)
        if card.get("status") != "READY" or card.get("coverage", "IMPLEMENTED") != "IMPLEMENTED" or not card.get("entry", {}).get("triggered"):
            signal_index += 1
            continue
        baseline = (context or {}).get("train_atr_median")
        current_atr = atr(history)
        if baseline and not .25*baseline <= current_atr <= 4*baseline:
            skipped.append({"signal_time": decision_time, "reason": "outside training volatility envelope"})
            signal_index += 1
            continue
        signals += 1
        fill_index = signal_index+1
        fill_bar = bars[fill_index]
        side = card["direction"]
        spread, slip = _spread(fill_bar, settings), settings["slippage_price"]
        entry = fill_bar["open"]+spread+slip if side == "BUY" else fill_bar["open"]-slip
        stop = card["stop"]["price"]
        target = card["targets"][0]["price"]
        grid = (context or {}).get("tick_size")
        if grid is not None:
            if not isinstance(grid, (int, float)) or not math.isfinite(grid) or grid <= 0:
                raise ValueError("invalid execution price grid")
            stop = round((math.floor(stop/grid) if side == "BUY" else math.ceil(stop/grid))*grid, 10)
            target = round((math.ceil(target/grid) if side == "BUY" else math.floor(target/grid))*grid, 10)
        zone = card["entry"].get("zone", [0, math.inf])
        if not zone[0] <= entry <= zone[1] or (not stop < entry < target if side == "BUY" else not target < entry < stop):
            raw_entry=fill_bar['open']
            raw_zone_ok=zone[0]<=raw_entry<=zone[1]
            raw_bracket_ok=stop<raw_entry<target if side=='BUY' else target<raw_entry<stop
            rejection_class=('GAP_OR_STRUCTURE' if not raw_zone_ok or not raw_bracket_ok else 'COST_ENTRY_ZONE_OR_BRACKET')
            target_exit=target-slip if side=='BUY' else target+slip
            target_net=(target_exit-entry if side=='BUY' else entry-target_exit)-settings['commission_per_unit']
            skipped.append({"signal_time": decision_time, "reason": "next-open gap/cost invalidated entry zone or stop/target",
                            'classification':rejection_class,'side':side,'next_open_bid':raw_entry,
                            'fill_price_after_entry_costs':entry,'spread_price':spread,'slippage_price_per_side':slip,
                            'commission_price_units':settings['commission_per_unit'],'entry_zone':list(zone),
                            'stop':stop,'target':target,'target_quote_basis':'bid' if side=='BUY' else 'ask',
                            'raw_zone_ok':raw_zone_ok,'raw_bracket_ok':raw_bracket_ok,
                            'target_net_price_scenario':target_net,
                            'diagnostic_limit':'Target scenario, not statistically expected profit; gate unchanged'})
            signal_index += 1
            continue
        risk = abs(entry-stop)
        hold = min(settings["max_hold_bars"], card.get("execution_plan", {}).get("max_hold_bars", settings["max_hold_bars"]))
        last_index = min(fill_index+hold-1, end-1)
        exit_price, exit_reason, ambiguous = None, "TIME", False
        exit_index = last_index
        invalidation = (card.get("invalidation") or {}).get("price")
        for j in range(fill_index, last_index+1):
            bar = bars[j]
            bar_spread = _spread(bar, settings)
            stop_hit = bar["low"] <= stop if side == "BUY" else bar["high"]+bar_spread >= stop
            target_hit = bar["high"] >= target if side == "BUY" else bar["low"]+bar_spread <= target
            if stop_hit:
                # A stop crossed in a gap can fill worse. Never award target first.
                exit_price = min(stop, bar["open"])-slip if side == "BUY" else max(stop, bar["open"]+bar_spread)+slip
                exit_reason, exit_index, ambiguous = "STOP", j, bool(target_hit)
                break
            if target_hit:
                exit_price, exit_reason, exit_index = target-slip if side == "BUY" else target+slip, "TARGET", j
                break
            invalidated = invalidation is not None and (bar["close"] < invalidation if side == "BUY" else bar["close"] > invalidation)
            if invalidated:
                if j+1 < end:
                    exit_index = j+1
                    next_bar = bars[exit_index]
                    exit_price = min(next_bar["open"], target)-slip if side == "BUY" else max(next_bar["open"]+_spread(next_bar, settings), target)+slip
                    exit_reason = "INVALIDATION_NEXT_OPEN"
                else:
                    exit_price = bar["close"]-slip if side == "BUY" else bar["close"]+bar_spread+slip
                    exit_reason = "FOLD_BOUNDARY"
                    exit_index = j
                break
        if exit_price is None:
            if last_index+1 < end and last_index == fill_index+hold-1:
                exit_index = last_index+1
                bar = bars[exit_index]
                exit_price = min(bar["open"], target)-slip if side == "BUY" else max(bar["open"]+_spread(bar, settings), target)+slip
                exit_reason = "TIME_NEXT_OPEN"
            else:
                bar = bars[last_index]
                exit_price = bar["close"]-slip if side == "BUY" else bar["close"]+_spread(bar, settings)+slip
                exit_reason = "FOLD_BOUNDARY"
        gross = exit_price-entry if side == "BUY" else entry-exit_price
        commission = settings["commission_per_unit"]
        trades.append({"strategy_id": strategy_id, "symbol": symbol, "timeframe": timeframe,
                       "signal_time": decision_time, "signal_bar_time": history[-1]["time"],
                       "entry_time": fill_bar["time"], "exit_time": (bars[exit_index]["time"] if exit_reason.endswith("NEXT_OPEN") else bar_close_time(bars[exit_index]["time"],timeframe)),
                       "entry_index": fill_index, "exit_index": exit_index, "side": side,
                       "entry": entry, "stop": stop, "target": target, "exit": exit_price,
                       "gross_price_pnl": gross, "commission_price_units": commission,
                       "net_price_pnl": gross-commission, "r": (gross-commission)/risk,
                       "exit_reason": exit_reason, "ambiguous_bar": ambiguous,
                       "fill_model": "next-open; bid OHLC; ask=bid+bar spread; adverse slippage",
                       "plan_model": "fixed full target/stop rounded to declared execution grid; completed-close invalidation and hold expiry exit next open; no trailing/additions"})
        signal_index = exit_index+1
    return {"trades": trades, "signals": signals, "skipped": skipped, "metrics": metrics(trades)}


def metrics(trades: list[dict]) -> dict:
    values = [t["r"] for t in trades]
    positive, negative = sum(max(x, 0) for x in values), sum(max(-x, 0) for x in values)
    equity, peak, drawdown = 0.0, 0.0, 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak-equity)
    return {"trades": len(values), "wins": sum(x > 0 for x in values), "losses": sum(x < 0 for x in values),
            "sample_win_fraction": sum(x > 0 for x in values)/len(values) if values else None,
            "profit_factor": positive/negative if negative else None,
            "profit_factor_infinite": bool(positive > 0 and negative == 0),
            "net_r": sum(values), "expectancy_r": statistics.fmean(values) if values else None,
            "max_drawdown_r": drawdown, "gross_profit_r": positive, "gross_loss_r": negative,
            "ambiguous_stop_first_trades": sum(t.get("ambiguous_bar", False) for t in trades),
            "net_price_units": sum(t.get("net_price_pnl", 0) for t in trades),
            "metric_limit": "R-normalized independent trade replay, not portfolio/account currency or guaranteed profitability"}


def walk_forward(bars: list[dict], strategy_id: str, symbol: str = "RESEARCH", timeframe: str = "H1",
                 config: dict | None = None, data_kind: str = "broker", context: dict | None = None, cancel_event=None) -> dict:
    if cancel_event is not None and cancel_event.is_set():
        raise CancelledError("Research cancelled on application shutdown")
    settings = _settings(config)
    meta = REGISTRY[strategy_id]
    result = {"qualified": False, "status": "INSUFFICIENT", "strategy_id": strategy_id,
              "version": meta["version"], "symbol": symbol, "timeframe": timeframe, "data_kind": data_kind,
              "metrics": metrics([]), "folds": [], "reasons": [], "thresholds": {
                  "minimum_oos_trades": settings["min_oos_trades"], "minimum_profit_factor": settings["min_profit_factor"],
                  "maximum_drawdown_r": settings["max_drawdown_r"]},
              "method": "rolling chronological fixed-rule OOS; training ATR envelope frozen per fold; purge/embargo >= hold",
              "limitations": ["OHLC cannot reconstruct intrabar price paths or broker fills", "No financial return promise",
                              "No multiple-testing adjustment or complete portfolio replay", "Never grants Real/Contest execution"]}
    if meta["coverage"] != "IMPLEMENTED":
        result.update(status="INELIGIBLE", reasons=["partial/unimplemented strategy cannot qualify"])
        return _translate_result(result)
    if bars:
        validate_bars(bars, timeframe, bar_close_time(bars[-1]["time"],timeframe))
        result["data_time"] = bar_close_time(bars[-1]["time"],timeframe)
    if data_kind not in ("broker", "broker_verified"):
        result["reasons"].append("synthetic/simulation/unverified data is never eligible for broker execution")
    costs_known = bool(settings["commission_known"] and (settings["point"] > 0 or "spread_price" in settings))
    if not costs_known:
        result["reasons"].append("spread scale or actual commission policy unknown")
    total = len(bars)
    first_test = settings["train_bars"]+settings["embargo_bars"]
    if total < first_test+settings["test_bars"]:
        result["reasons"].append("insufficient chronological training/embargo/test history")
        return _translate_result(result)
    all_trades = []
    for test_start in range(first_test, total-settings["test_bars"]+1, settings["test_bars"]):
        if cancel_event is not None and cancel_event.is_set():
            raise CancelledError("Research cancelled on application shutdown")
        train_end = test_start-settings["embargo_bars"]
        train_start = train_end-settings["train_bars"]
        train = bars[train_start:train_end]
        train_atrs = [atr(train[max(0, j-14):j+1]) for j in range(14, len(train))]
        baseline = statistics.median(train_atrs) if train_atrs else 0.0
        test_end = test_start+settings["test_bars"]
        c = {**(context or {}), "train_atr_median": baseline, "data_kind": data_kind}
        simulation = replay(bars, strategy_id, symbol, timeframe, test_start, test_end, settings, c, cancel_event=cancel_event)
        fold = {"train_start_index": train_start, "train_end_exclusive": train_end,
                "embargo_start_index": train_end, "test_start_index": test_start, "test_end_exclusive": test_end,
                "train_last_close_time": bar_close_time(train[-1]["time"],timeframe),
                "test_first_signal_close_time": bar_close_time(bars[test_start]["time"],timeframe),
                "frozen_train_atr_median": baseline, "metrics": simulation["metrics"],
                "signals":simulation['signals'],
                "trades": simulation["trades"], "skipped": simulation["skipped"]}
        result["folds"].append(fold)
        all_trades.extend(simulation["trades"])
    result["metrics"] = m = metrics(all_trades)
    if m["trades"] < settings["min_oos_trades"]:
        result["reasons"].append("fewer than required OOS trades")
    if (m["profit_factor"] is None and not m["profit_factor_infinite"]) or (m["profit_factor"] is not None and m["profit_factor"] <= settings["min_profit_factor"]):
        result["reasons"].append("OOS profit factor unmeasurable or below threshold")
    if m["expectancy_r"] is None or m["expectancy_r"] <= 0:
        result["reasons"].append("nonpositive or unmeasurable cost-adjusted expectancy")
    if m["max_drawdown_r"] > settings["max_drawdown_r"]:
        result["reasons"].append("OOS drawdown exceeds fixed threshold")
    if len(result["folds"]) < 2:
        result["reasons"].append("at least two separate chronological OOS folds required")
    result["qualified"] = not result["reasons"]
    result["status"] = "QUALIFIED_DEMO_RESEARCH" if result["qualified"] else "REJECTED"
    return _translate_result(result)
