"""Causal trend-line school analysis for the chart view.

This is a separate, research-only module. It reports a bounded house-rule
interpretation of trend lines and is deliberately outside the 58-model
execution registry until later evaluation and an explicit promotion review.
"""
from __future__ import annotations

import math
import statistics
from itertools import pairwise
from typing import Any

from .. import strategies as st

SCHOOL_ID = "trendline_school"
VERSION = "0.1.0"
MINIMUM_BARS = 65
PIVOT_LOOKBACK = 120
PIVOT_COUNT = 3
MAX_RESIDUAL_ATR = 0.25


def _fit_line(points: list[dict]) -> tuple[float, float, float] | None:
    """Return slope, intercept and RMS residual for confirmed pivots."""
    if len(points) < PIVOT_COUNT:
        return None
    xs = [float(point["index"]) for point in points]
    ys = [float(point["price"]) for point in points]
    x_mean = statistics.fmean(xs)
    y_mean = statistics.fmean(ys)
    denominator = math.fsum((x - x_mean) ** 2 for x in xs)
    if denominator <= 0:
        return None
    slope = math.fsum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / denominator
    intercept = y_mean - slope * x_mean
    residual = math.sqrt(statistics.fmean((y - (slope * x + intercept)) ** 2
                                         for x, y in zip(xs, ys)))
    if not all(math.isfinite(value) for value in (slope, intercept, residual)):
        return None
    return slope, intercept, residual


def _boundary(bars: list[dict], pivots: list[dict], kind: str, scale: float) -> dict | None:
    recent = [point for point in pivots
              if point["kind"] == kind and point["index"] >= len(bars) - PIVOT_LOOKBACK]
    points = recent[-PIVOT_COUNT:]
    if len(points) != PIVOT_COUNT or any(
            right["index"] - left["index"] < 3 for left, right in pairwise(points)):
        return None
    fitted = _fit_line(points)
    if fitted is None:
        return None
    slope, intercept, residual = fitted
    if scale <= 0 or residual > MAX_RESIDUAL_ATR * scale:
        return None
    # A breakout is meaningful only if the fitted boundary was still respected
    # by completed closes before the candidate breakout bar. An earlier close
    # through the line makes this a stale line rather than a first break.
    for index in range(points[0]["index"], len(bars) - 1):
        close = bars[index]["close"]
        boundary = slope * index + intercept
        if kind == "HIGH" and close > boundary:
            return None
        if kind == "LOW" and close < boundary:
            return None
    previous_index, last_index = len(bars) - 2, len(bars) - 1
    return {
        "kind": "RESISTANCE" if kind == "HIGH" else "SUPPORT",
        "slope_per_bar": slope,
        "intercept": intercept,
        "previous_price": slope * previous_index + intercept,
        "current_price": slope * last_index + intercept,
        "rms_residual": residual,
        "touch_count": len(points),
        "pivot_times": [point["time"] for point in points],
        "pivot_indices": [point["index"] for point in points],
        "bar_count": len(bars),
        "confirmed_at": max(point["confirmed_at"] for point in points),
    }


def analyze(bars: list[dict], timeframe: str, as_of: float) -> dict:
    """Inspect completed MT5-style OHLC bars and report a non-actionable result."""
    base: dict[str, Any] = {
        "school_id": SCHOOL_ID,
        "school": "خط الاتجاه / Trend Line",
        "version": VERSION,
        "timeframe": timeframe,
        "status": "WAIT",
        "direction": "NEUTRAL",
        "triggered": False,
        "actionable": False,
        "execution_authority": False,
        "analysis_only": True,
        "reason": "لا يوجد كسر مؤكد لخط صالح من ثلاث قمم أو قيعان محورية مكتملة.",
        "inputs": {"completed_bars": 0, "minimum_bars": MINIMUM_BARS,
                   "pivot_confirmation_bars": 2, "pivot_lookback": PIVOT_LOOKBACK},
        "boundaries": [],
    }
    try:
        data = st.validate_bars(bars, timeframe, as_of)
    except (st.DataError, TypeError, ValueError, OverflowError) as exc:
        return {**base, "status": "DATA_INVALID", "reason": st.arabic(str(exc))}
    base["inputs"]["completed_bars"] = len(data)
    if len(data) < MINIMUM_BARS:
        return {**base, "status": "DATA_MISSING",
                "reason": f"يلزم {MINIMUM_BARS} شمعة مكتملة على الأقل؛ المتاح {len(data)}."}

    scale = st.atr(data)
    if not math.isfinite(scale) or scale <= 0:
        return {**base, "status": "DATA_INVALID", "reason": "نطاق التقلب غير صالح."}
    pivots = st.causal_pivots(data, left=2, right=2, as_of=as_of, timeframe=timeframe)
    support: dict[str, Any] | None = _boundary(data, pivots, "LOW", scale)
    resistance: dict[str, Any] | None = _boundary(data, pivots, "HIGH", scale)
    boundaries: list[dict[str, Any]] = [line for line in (support, resistance) if line is not None]
    last, previous = data[-1], data[-2]
    buy = bool(resistance and resistance["slope_per_bar"] < 0
               and previous["close"] <= resistance["previous_price"]
               and last["close"] > resistance["current_price"])
    sell = bool(support and support["slope_per_bar"] > 0
                and previous["close"] >= support["previous_price"]
                and last["close"] < support["current_price"])
    result: dict[str, Any] = {**base, "boundaries": boundaries,
              "inputs": {**base["inputs"], "data_time": st.bar_close_time(last["time"], timeframe),
                         "as_of": as_of, "atr": scale,
                         "confirmed_pivots": len(pivots)},
              "rule": {
                  "name": "3-touch confirmed-pivot regression breakout",
                  "touch_count": PIVOT_COUNT,
                  "maximum_fit_error_atr": MAX_RESIDUAL_ATR,
                  "confirmation": "completed-bar close beyond the fitted boundary",
                  "no_lookahead": True,
              }}
    if buy or sell:
        line = resistance if buy else support
        if line is not None:
            result.update(status="OBSERVATION", direction="BUY" if buy else "SELL",
                          triggered=True, reason=("إغلاق مكتمل فوق مقاومة هابطة؛ إشارة تحليلية فقط."
                                                  if buy else "إغلاق مكتمل تحت دعم صاعد؛ إشارة تحليلية فقط."),
                          trigger_price=line["current_price"], invalidation_reference=(
                              min(row["low"] for row in data[-5:]) if buy else
                              max(row["high"] for row in data[-5:])))
    elif not boundaries:
        result["status"] = "INSUFFICIENT_STRUCTURE"
        result["reason"] = "لم تتوفر ثلاثة محاور مؤكدة متقاربة بما يكفي لبناء خط صالح."
    return result

