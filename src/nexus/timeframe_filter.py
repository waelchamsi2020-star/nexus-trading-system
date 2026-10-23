"""Closed native H4 and D1 confirmation for an H1 signal; no resampling."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .regime_router import classify_regime
from .session_filter import (
    load_context_config,
    observation_time,
    validate_context_config,
)
from .timeframes import PERIODS


def normalize_direction(direction: str) -> str:
    if not isinstance(direction, str) or direction.upper() not in {"BUY", "SELL", "LONG", "SHORT"}:
        raise ValueError("Signal direction must be BUY/SELL or LONG/SHORT")
    return "BUY" if direction.upper() in {"BUY", "LONG"} else "SELL"


def evaluate_timeframes(direction: str, *, h4_bars: list[dict], d1_bars: list[dict],
                        as_of: float, config: Mapping[str, Any] | None = None,
                        routing_config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Both native higher frames must agree with the H1 order direction.

    Callers join only native closed history available at the signal close. If
    a caller passes an unfinished/future candle it raises LookaheadBiasError;
    the function never silently removes it. RANGE and UNCERTAIN both veto.
    """
    profile = load_context_config() if config is None else validate_context_config(config)
    decision = observation_time(as_of)
    side = normalize_direction(direction)
    expected = "TREND_UP" if side == "BUY" else "TREND_DOWN"
    details: dict[str, Any] = {}
    reasons = []
    for timeframe, rows in (("H4", h4_bars), ("D1", d1_bars)):
        context = classify_regime(rows, timeframe, decision, config=routing_config)
        details[timeframe] = context
        if context["last_closed_time"] is None:
            reasons.append(f"MISSING_{timeframe}_HISTORY")
        elif decision - context["last_closed_time"] >= PERIODS[timeframe]:
            reasons.append(f"STALE_{timeframe}_HISTORY")
        if context["regime"] != expected:
            reasons.append(f"{timeframe}_CONTEXT_CONFLICT_OR_UNCERTAIN")
    return {"allowed": not reasons, "direction": side, "expected_regime": expected,
            "details": details, "decision_time": decision,
            "context_version": profile["version"], "context_fingerprint": profile["context_fingerprint"],
            "reasons": reasons or ["NATIVE_H4_D1_DIRECTIONAL_CONFIRMATION"],
            "execution_authority": False}
