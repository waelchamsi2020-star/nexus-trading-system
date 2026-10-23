"""Explicit USD-leg corroboration from aligned native H1 candles, never fake DXY."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .regime_router import classify_regime, load_routing_config, validate_routing_config
from .session_filter import (
    ContextConfigError,
    load_context_config,
    observation_time,
    validate_context_config,
)
from .timeframe_filter import normalize_direction


def canonical_symbol(symbol: str, *, config: Mapping[str, Any] | None = None) -> str:
    """Resolve an exact configured alias; case-folding canonical names is safe.

    Prefixes, suffixes, CFD names and missing indices are never inferred. A
    broker-specific symbol must be explicitly added to the alias dictionary.
    """
    profile = load_context_config() if config is None else validate_context_config(config)
    if not isinstance(symbol, str) or not symbol.strip() or not symbol.isascii():
        raise ValueError("A declared broker symbol alias is required")
    aliases = profile["cross_asset"]["aliases"]
    name = symbol.strip()
    if name in aliases:
        return aliases[name]
    if name.upper() in aliases and name.upper() in {"EURUSD", "GBPUSD", "USDJPY", "DXY"}:
        return aliases[name.upper()]
    raise ValueError(f"Unknown symbol alias: {symbol}")


def evaluate_cross_assets(symbol: str, direction: str, bars_by_symbol: Mapping[str, list[dict]],
                          as_of: float, *, config: Mapping[str, Any] | None = None,
                          routing_config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Require all declared legs, fresh aligned history and correct USD direction.

    This is a deterministic corroboration filter, not measured correlation,
    actual order flow or a claim that USD relationships are stable over time.
    """
    profile = load_context_config() if config is None else validate_context_config(config)
    router = load_routing_config() if routing_config is None else validate_routing_config(routing_config)
    decision = observation_time(as_of)
    side = normalize_direction(direction)
    canonical = canonical_symbol(symbol, config=profile)
    policy = profile["cross_asset"]["policies"].get(canonical)
    if policy is None:
        return {"allowed": False, "symbol": canonical, "direction": side, "details": {},
                "decision_time": decision, "context_version": profile["version"],
                "context_fingerprint": profile["context_fingerprint"],
                "reasons": ["NO_EXPLICIT_CROSS_ASSET_POLICY"], "execution_authority": False}
    if not isinstance(bars_by_symbol, Mapping):
        raise ContextConfigError("Cross-asset input requires an explicit symbol/history mapping")
    selected: dict[str, list[dict]] = {}
    reasons = []
    for supplied, rows in bars_by_symbol.items():
        try:
            leg = canonical_symbol(supplied, config=profile)
        except ValueError:
            continue
        if leg in policy:
            if leg in selected:
                reasons.append(f"AMBIGUOUS_CROSS_ASSET_ALIAS_{leg}")
            else:
                selected[leg] = rows
    details: dict[str, Any] = {}
    closed_times = []
    aligned_times = []
    minimum = max(profile["cross_asset"]["minimum_aligned_bars"], router["classifier"]["min_bars"])
    signal_sign = 1 if side == "BUY" else -1
    for leg, coefficient in policy.items():
        if leg not in selected or not selected[leg]:
            reasons.append(f"MISSING_CROSS_ASSET_{leg}")
            continue
        rows = selected[leg]
        context = classify_regime(rows, "H1", decision, config=router)
        expected = "TREND_UP" if coefficient * signal_sign == 1 else "TREND_DOWN"
        details[leg] = {**context, "expected_regime": expected, "currency_orientation": coefficient}
        if context["regime"] != expected:
            reasons.append(f"CROSS_ASSET_{leg}_CONFLICT_OR_UNCERTAIN")
        closing = context["last_closed_time"]
        if closing is None or decision - closing >= 3600:
            reasons.append(f"STALE_CROSS_ASSET_{leg}")
        else:
            closed_times.append(closing)
        if len(rows) < minimum:
            reasons.append(f"INSUFFICIENT_ALIGNED_CROSS_ASSET_{leg}")
        else:
            aligned_times.append(tuple(row["time"] for row in rows[-minimum:]))
    if len(closed_times) == len(policy) and len(set(closed_times)) != 1:
        reasons.append("CROSS_ASSET_LAST_CLOSE_NOT_ALIGNED")
    if len(aligned_times) == len(policy) and len(set(aligned_times)) != 1:
        reasons.append("CROSS_ASSET_HISTORY_NOT_ALIGNED")
    return {"allowed": not reasons, "symbol": canonical, "direction": side, "details": details,
            "decision_time": decision, "context_version": profile["version"],
            "context_fingerprint": profile["context_fingerprint"],
            "reasons": reasons or ["ALIGNED_NATIVE_H1_USD_LEGS_CONFIRMED"],
            "execution_authority": False}
