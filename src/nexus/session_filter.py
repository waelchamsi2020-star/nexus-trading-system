"""Explicit UTC research sessions and versioned settings for context vetoes."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .strategies import REGISTRY

DEFAULT_CONTEXT_PATH = Path(__file__).with_name("config") / "context_layers.json"
SESSION_NAMES = frozenset({"LONDON", "NEW_YORK", "ASIA"})
CANONICAL_SYMBOLS = frozenset({"EURUSD", "GBPUSD", "USDJPY", "DXY"})
POLICIES = {
    "EURUSD": {"GBPUSD": 1, "USDJPY": -1, "DXY": -1},
    "GBPUSD": {"EURUSD": 1, "USDJPY": -1, "DXY": -1},
    "USDJPY": {"EURUSD": -1, "GBPUSD": -1, "DXY": 1},
}


class ContextConfigError(ValueError):
    """Context settings are malformed or attempt to grant execution authority."""


def context_fingerprint(config: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in config.items() if key != "context_fingerprint"}
    try:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ContextConfigError("Context configuration requires finite JSON values") from exc
    return hashlib.sha256(encoded).hexdigest()


def validate_context_config(config: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(config, Mapping):
        raise ContextConfigError("Context configuration requires an object")
    result = copy.deepcopy(dict(config))
    required = {"schema_version", "version", "mode", "execution_authority", "multi_timeframe", "cross_asset", "sessions", "notes"}
    if not required <= set(result) or set(result) - required - {"context_fingerprint"}:
        raise ContextConfigError("Context configuration has missing or unknown properties")
    if (type(result["schema_version"]) is not int or result["schema_version"] != 1 or
            not isinstance(result["version"], str) or
            not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", result["version"]) or
            result["mode"] != "RESEARCH_ONLY" or result["execution_authority"] is not False):
        raise ContextConfigError("Context settings must be versioned research-only without authority")
    mtf = result["multi_timeframe"]
    if (not isinstance(mtf, dict) or set(mtf) != {"timeframes", "maximum_age_periods"} or
            mtf["timeframes"] != ["H4", "D1"] or type(mtf["maximum_age_periods"]) is not int or
            mtf["maximum_age_periods"] != 1):
        raise ContextConfigError("MTF confirmation requires H4/D1 and freshness below one period")
    cross = result["cross_asset"]
    if (not isinstance(cross, dict) or set(cross) != {"timeframe", "minimum_aligned_bars", "maximum_age_bars", "aliases", "policies"} or
            cross["timeframe"] != "H1" or type(cross["minimum_aligned_bars"]) is not int or
            not 60 <= cross["minimum_aligned_bars"] <= 2000 or
            type(cross["maximum_age_bars"]) is not int or cross["maximum_age_bars"] != 1):
        raise ContextConfigError("Cross confirmation requires aligned H1 candles and explicit bounds")
    aliases = cross["aliases"]
    if (not isinstance(aliases, dict) or not CANONICAL_SYMBOLS <= set(aliases) or
            any(not isinstance(key, str) or not key or key != key.strip() or not key.isascii() or
                not isinstance(value, str) or value not in CANONICAL_SYMBOLS for key, value in aliases.items()) or
            any(aliases[key] != key for key in CANONICAL_SYMBOLS)):
        raise ContextConfigError("Aliases must explicitly map known canonical symbols")
    if cross["policies"] != POLICIES or any(
            type(coefficient) is not int for policy in cross["policies"].values() for coefficient in policy.values()):
        raise ContextConfigError("Cross policy currency orientations must match the declared USD legs")
    sessions = result["sessions"]
    if (not isinstance(sessions, dict) or set(sessions) != {"timezone", "windows", "models"} or
            sessions["timezone"] != "UTC" or not isinstance(sessions["windows"], dict) or
            set(sessions["windows"]) != SESSION_NAMES):
        raise ContextConfigError("Sessions require explicit UTC windows")
    for name, window in sessions["windows"].items():
        if (not isinstance(window, dict) or set(window) != {"start_hour", "end_hour"} or
                any(type(hour) is not int or not 0 <= hour <= 23 for hour in window.values()) or
                window["start_hour"] == window["end_hour"]):
            raise ContextConfigError(f"Session {name} requires distinct integer UTC hours")
    preferences = sessions["models"]
    if not isinstance(preferences, dict) or set(preferences) != set(REGISTRY):
        raise ContextConfigError("Session preferences must declare all 58 registry models")
    for model, names in preferences.items():
        if (not isinstance(names, list) or any(not isinstance(name, str) for name in names) or
                len(set(names)) != len(names) or not set(names) <= SESSION_NAMES | {"ALL"} or
                ("ALL" in names and len(names) != 1)):
            raise ContextConfigError(f"Session preferences invalid for {model}")
    if not isinstance(result["notes"], list) or not result["notes"] or any(
            not isinstance(note, str) or not note for note in result["notes"]):
        raise ContextConfigError("Context limitations must be explicitly recorded")
    result["context_fingerprint"] = context_fingerprint(result)
    return result


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContextConfigError(f"Duplicate context configuration key: {key}")
        result[key] = value
    return result


def load_context_config(path: str | Path | None = None) -> dict[str, Any]:
    target = DEFAULT_CONTEXT_PATH if path is None else Path(path)
    try:
        config = json.loads(target.read_text(encoding="utf-8-sig"), object_pairs_hook=_unique_object)
    except ContextConfigError:
        raise
    except (ValueError, OSError) as exc:
        raise ContextConfigError(f"Cannot read context profile: {target}") from exc
    return validate_context_config(config)


def observation_time(as_of: float) -> float:
    if (isinstance(as_of, bool) or not isinstance(as_of, (int, float)) or
            not math.isfinite(as_of) or as_of < 0):
        raise ValueError("A finite, nonnegative UTC observation time is required")
    # datetime also rejects unsupported calendar ranges before any policy runs.
    datetime.fromtimestamp(as_of, UTC)
    return float(as_of)


def evaluate_session(model_id: str, as_of: float, *,
                     config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """ALL is unrestricted UTC time, not permission to trade a closed market.

    These are fixed UTC research windows, not DST-adjusted exchange calendars.
    London and New York overlap intentionally. Broker availability is separate.
    No favorite session is inferred from the reused five-year test outcomes.
    """
    profile = load_context_config() if config is None else validate_context_config(config)
    observed = observation_time(as_of)
    if model_id not in profile["sessions"]["models"]:
        raise ContextConfigError(f"Unknown session model: {model_id}")
    utc = datetime.fromtimestamp(observed, UTC)
    hour = utc.hour + utc.minute / 60 + utc.second / 3600 + utc.microsecond / 3_600_000_000
    active = []
    for name, window in profile["sessions"]["windows"].items():
        start, end = window["start_hour"], window["end_hour"]
        if (start <= hour < end if start < end else hour >= start or hour < end):
            active.append(name)
    preferences = profile["sessions"]["models"][model_id]
    allowed = "ALL" in preferences or bool(set(preferences) & set(active))
    return {"allowed": allowed, "model_id": model_id, "sessions": active,
            "preferred_sessions": list(preferences), "decision_time": observed,
            "timezone": "UTC", "context_version": profile["version"],
            "context_fingerprint": profile["context_fingerprint"],
            "reasons": ["UTC_SESSION_ALLOWED" if allowed else "MODEL_SESSION_NOT_ALLOWED"],
            "execution_authority": False}
