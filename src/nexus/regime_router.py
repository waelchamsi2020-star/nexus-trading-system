"""Causal context gate for the existing model registry, without order authority.

EMA, ATR and movement efficiency describe closed OHLC candles.  The thresholds
are declared configuration, not fitted probabilities or a profitability claim.
The signal candle is usable only after its close; any later candle is rejected.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from .strategies import REGISTRY, DataError, atr, ema, validate_bars
from .timeframes import PERIODS, bar_close_time
from .walkforward import LookaheadBiasError

REGIMES = frozenset({"TREND_UP", "TREND_DOWN", "RANGE", "UNCERTAIN"})
KNOWN_REGIMES = REGIMES - {"UNCERTAIN"}
DEFAULT_CONFIG_PATH = Path(__file__).with_name("config") / "routing.yaml"
CLASSIFIER_DEFAULTS: dict[str, int | float] = {
    "min_bars": 60,
    "ema_fast": 20,
    "ema_slow": 50,
    "slope_bars": 5,
    "atr_period": 14,
    "efficiency_bars": 20,
    "trend_min_ema_gap_atr": 0.5,
    "trend_min_slope_atr": 0.25,
    "trend_min_efficiency": 0.45,
    "range_max_efficiency": 0.25,
    "range_max_ema_gap_atr": 0.5,
    "range_max_abs_slope_atr": 0.25,
}


class RoutingConfigError(ValueError):
    """A route configuration is incomplete, unversioned or unsafe."""


def routing_fingerprint(config: Mapping[str, Any]) -> str:
    """Canonical hash of the entire profile, independent of YAML key ordering."""
    payload = {key: value for key, value in config.items()
               if key not in {"routing_fingerprint", "classifier_fingerprint"}}
    try:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                             allow_nan=False, ensure_ascii=False).encode("utf-8")
    except (ValueError, TypeError) as exc:
        raise RoutingConfigError("Routing configuration must contain finite JSON values") from exc
    return hashlib.sha256(encoded).hexdigest()


def classifier_fingerprint(config: Mapping[str, Any]) -> str:
    """Hash only the declared classifier, so routing-map updates can reuse context."""
    params = _classifier_config(config.get("classifier"))
    return hashlib.sha256(json.dumps(params, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode("utf-8")).hexdigest()


def _classifier_config(raw: Any) -> dict[str, int | float]:
    if not isinstance(raw, dict) or set(raw) != set(CLASSIFIER_DEFAULTS):
        raise RoutingConfigError("Classifier requires all declared parameters and no unknown parameters")
    params = dict(raw)
    integer_bounds = {
        "min_bars": (60, 2000), "ema_fast": (2, 200), "ema_slow": (3, 500),
        "slope_bars": (1, 100), "atr_period": (2, 200), "efficiency_bars": (2, 200),
    }
    for name, (low, high) in integer_bounds.items():
        value = params[name]
        if type(value) is not int or not low <= value <= high:
            raise RoutingConfigError(f"Classifier {name} requires an integer in [{low}, {high}]")
    if (params["ema_fast"] >= params["ema_slow"] or
            params["min_bars"] < params["ema_slow"] + params["slope_bars"] or
            params["min_bars"] <= max(params["atr_period"], params["efficiency_bars"])):
        raise RoutingConfigError("Classifier history must cover both EMAs, slope, ATR and efficiency")
    for name in set(params) - set(integer_bounds):
        value = params[name]
        upper = 1 if "efficiency" in name else 20
        if (isinstance(value, bool) or not isinstance(value, (int, float)) or
                not math.isfinite(value) or not 0 <= value <= upper):
            raise RoutingConfigError(f"Classifier {name} requires a finite number in [0, {upper}]")
    if (params["trend_min_ema_gap_atr"] <= 0 or params["trend_min_slope_atr"] <= 0 or
            params["range_max_efficiency"] >= params["trend_min_efficiency"]):
        raise RoutingConfigError("Trend thresholds must be positive and efficiency bands disjoint")
    return params


def validate_routing_config(config: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a complete registry profile and return a detached snapshot.

    RESEARCH_ONLY and execution_authority=False are provenance declarations;
    this module can only veto a signal and never grants broker permission.
    """
    if not isinstance(config, Mapping):
        raise RoutingConfigError("Routing configuration requires an object")
    result = copy.deepcopy(dict(config))
    required = {"schema_version", "version", "mode", "execution_authority", "classifier", "source", "models"}
    if not required <= set(result) or set(result) - required - {"routing_fingerprint", "classifier_fingerprint"}:
        raise RoutingConfigError("Routing configuration has missing or unknown properties")
    if (type(result.get("schema_version")) is not int or result["schema_version"] != 1 or
            not isinstance(result.get("version"), str) or
            not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", result["version"])):
        raise RoutingConfigError("Routing requires schema_version=1 and a semantic version")
    if result.get("mode") != "RESEARCH_ONLY" or result.get("execution_authority") is not False:
        raise RoutingConfigError("Routing profile must remain RESEARCH_ONLY without execution authority")
    result["classifier"] = _classifier_config(result.get("classifier"))
    models = result.get("models")
    if not isinstance(models, dict) or set(models) != set(REGISTRY):
        raise RoutingConfigError("Routing must declare every registry model exactly once")
    source = result.get("source")
    source_required = {"diagnostic_report_sha256", "native_csv_sha256", "selection_rule",
                       "minimum_prior_trades", "limitations"}
    if not isinstance(source, dict) or not source_required <= set(source):
        raise RoutingConfigError("Routing requires source provenance")
    if (type(source["minimum_prior_trades"]) is not int or source["minimum_prior_trades"] != 5 or
            not isinstance(source["selection_rule"], str) or not source["selection_rule"] or
            not isinstance(source["limitations"], list) or len(source["limitations"]) < 7 or
            any(not isinstance(item, str) or not item for item in source["limitations"])):
        raise RoutingConfigError("Routing source requires the declared prior sample rule and limitations")
    for name in ("diagnostic_report_sha256", "native_csv_sha256"):
        if not isinstance(source.get(name), str) or not re.fullmatch(r"[a-f0-9]{64}", source[name]):
            raise RoutingConfigError(f"Routing source {name} requires a SHA256")
    for model_id, model in models.items():
        if not isinstance(model, dict) or set(model) != {"regimes", "source", "diagnostic"}:
            raise RoutingConfigError(f"Routing {model_id} requires an object")
        regimes = model.get("regimes")
        if (not isinstance(regimes, list) or any(not isinstance(item, str) for item in regimes) or
                len(set(regimes)) != len(regimes) or not set(regimes) <= KNOWN_REGIMES | {"ALL"} or
                ("ALL" in regimes and len(regimes) != 1)):
            raise RoutingConfigError(f"Routing {model_id} has invalid or duplicate regimes")
        model_source = model.get("source")
        if (not isinstance(model_source, dict) or set(model_source) !=
                {"diagnostic_report_sha256", "native_csv_sha256"} or
                any(model_source.get(key) != source[key] for key in
                    ("diagnostic_report_sha256", "native_csv_sha256"))):
            raise RoutingConfigError(f"Routing {model_id} provenance must match the profile")
        diagnostic = model["diagnostic"]
        if (not isinstance(diagnostic, dict) or set(diagnostic) !=
                {"UP", "DOWN", "RANGE", "UNKNOWN", "selection_reason", "prior_sample_adequate"} or
                not isinstance(diagnostic["selection_reason"], str) or
                not diagnostic["selection_reason"] or type(diagnostic["prior_sample_adequate"]) is not bool):
            raise RoutingConfigError(f"Routing {model_id} requires complete diagnostic provenance")
        for regime in ("UP", "DOWN", "RANGE", "UNKNOWN"):
            summary = diagnostic[regime]
            if (not isinstance(summary, dict) or set(summary) != {"trades", "net_r"} or
                    type(summary["trades"]) is not int or summary["trades"] < 0 or
                    isinstance(summary["net_r"], bool) or not isinstance(summary["net_r"], (int, float)) or
                    not math.isfinite(summary["net_r"])):
                raise RoutingConfigError(f"Routing {model_id}/{regime} requires finite diagnostic measurements")
    result["routing_fingerprint"] = routing_fingerprint(result)
    result["classifier_fingerprint"] = classifier_fingerprint(result)
    return result


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RoutingConfigError(f"Duplicate routing configuration key: {key}")
        result[key] = value
    return result


def load_routing_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load JSON-compatible YAML, with no optional YAML parser dependency."""
    target = DEFAULT_CONFIG_PATH if path is None else Path(path)
    try:
        raw = json.loads(target.read_text(encoding="utf-8-sig"), object_pairs_hook=_unique_object)
    except RoutingConfigError:
        raise
    except (OSError, ValueError) as exc:
        raise RoutingConfigError(f"Cannot read routing profile: {target}") from exc
    return validate_routing_config(raw)


def classify_regime(bars: list[dict], timeframe: str, as_of: float, *,
                    config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Classify the declared closed prefix, rejecting rather than trimming future data.

    EMA is the existing alpha=2/(period+1) recurrence. ATR is the existing simple
    arithmetic mean of trailing true ranges. Slope is the EMA20 change across
    slope_bars, divided by ATR (not a per-bar slope). Efficiency is absolute
    net movement divided by the sum of absolute movements over efficiency_bars.
    """
    profile = load_routing_config() if config is None else validate_routing_config(config)
    try:
        rows = validate_bars(bars, timeframe, as_of)
    except DataError as exc:
        if str(exc) == "unfinished or future bar":
            raise LookaheadBiasError("Regime input contains a future or unfinished candle") from exc
        raise
    params = profile["classifier"]
    metrics: dict[str, Any] = {"completed_bars": len(rows)}
    result: dict[str, Any] = {
        "regime": "UNCERTAIN", "reasons": [], "metrics": metrics,
        "rule_version": profile["version"], "routing_fingerprint": profile["routing_fingerprint"],
        "classifier_fingerprint": profile["classifier_fingerprint"], "timeframe": timeframe,
        "classification_source": "CLOSED_CANDLE_REGIME_V1",
        "decision_time": as_of,
        "last_bar_open_time": rows[-1]["time"] if rows else None,
        "last_closed_time": bar_close_time(rows[-1]["time"], timeframe) if rows else None,
        "execution_authority": False,
    }
    if len(rows) < params["min_bars"]:
        result["reasons"] = ["INSUFFICIENT_CLOSED_HISTORY"]
        return result
    closes = [row["close"] for row in rows]
    volatility = atr(rows, params["atr_period"])
    fast = ema(closes, params["ema_fast"])
    slow = ema(closes, params["ema_slow"])
    changes = [current - previous for previous, current in zip(
        closes[-params["efficiency_bars"]-1:-1], closes[-params["efficiency_bars"]:], strict=True)]
    path_length = math.fsum(abs(change) for change in changes)
    if volatility <= 0 or not math.isfinite(volatility) or path_length <= 0:
        result["reasons"] = ["ZERO_OR_NONFINITE_VOLATILITY_OR_MOVEMENT"]
        return result
    gap = (fast[-1] - slow[-1]) / volatility
    slope = (fast[-1] - fast[-1-params["slope_bars"]]) / volatility
    efficiency = abs(math.fsum(changes)) / path_length
    metrics.update({"ema_fast": fast[-1], "ema_slow": slow[-1], "atr": volatility,
                    "ema_gap_atr": gap, "ema_slope_atr": slope,
                    "movement_efficiency": efficiency})
    if not all(math.isfinite(value) for value in (gap, slope, efficiency)):
        result["reasons"] = ["NONFINITE_CONTEXT_METRICS"]
        return result
    result["regime"] = _regime_from_metrics(metrics, params)
    if result["regime"] == "UNCERTAIN":
        result["reasons"] = ["AMBIGUOUS_CONTEXT_THRESHOLDS"]
    if result["regime"] != "UNCERTAIN":
        result["reasons"] = ["CLOSED_CANDLE_CONTEXT_CLASSIFIED"]
    return result


def _regime_from_metrics(metrics: Mapping[str, Any], params: Mapping[str, Any]) -> str:
    gap, slope, efficiency = (metrics[name] for name in
                              ("ema_gap_atr", "ema_slope_atr", "movement_efficiency"))
    if (gap >= params["trend_min_ema_gap_atr"] and slope >= params["trend_min_slope_atr"] and
            efficiency >= params["trend_min_efficiency"]):
        return "TREND_UP"
    if (gap <= -params["trend_min_ema_gap_atr"] and slope <= -params["trend_min_slope_atr"] and
            efficiency >= params["trend_min_efficiency"]):
        return "TREND_DOWN"
    if (abs(gap) <= params["range_max_ema_gap_atr"] and abs(slope) <= params["range_max_abs_slope_atr"] and
            efficiency <= params["range_max_efficiency"]):
        return "RANGE"
    return "UNCERTAIN"


def route_classification(model_id: str, classification: Mapping[str, Any], *,
                         config: Mapping[str, Any],
                         audit: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    """Apply a new routing map to a trusted, causal research classification.

    The helper checks metric/label consistency and observation times. It is not
    an authentication mechanism for external classifications. Live execution
    uses route_signal with freshly obtained closed candles instead.
    """
    profile = validate_routing_config(config)
    if model_id not in profile["models"]:
        raise RoutingConfigError(f"Unknown routing model: {model_id}")
    if not isinstance(classification, Mapping):
        raise RoutingConfigError("Routing requires a causal classification object")
    result = copy.deepcopy(dict(classification))
    if (result.get("classifier_fingerprint") != profile["classifier_fingerprint"] or
            result.get("classification_source") != "CLOSED_CANDLE_REGIME_V1" or
            result.get("execution_authority") is not False or result.get("regime") not in REGIMES):
        raise RoutingConfigError("Classification provenance, classifier fingerprint or regime is invalid")
    decision, closing, opening = (result.get(key) for key in
                                  ("decision_time", "last_closed_time", "last_bar_open_time"))
    if (isinstance(decision, bool) or not isinstance(decision, (int, float)) or
            not math.isfinite(decision) or decision < 0 or result.get("timeframe") not in PERIODS):
        raise RoutingConfigError("Classification observation time or timeframe is invalid")
    metrics = result.get("metrics")
    reasons = result.get("reasons")
    if (not isinstance(metrics, dict) or type(metrics.get("completed_bars")) is not int or
            metrics["completed_bars"] < 0 or not isinstance(reasons, list) or not reasons or
            any(not isinstance(reason, str) or not reason for reason in reasons)):
        raise RoutingConfigError("Classification requires finite metrics and reasons")
    count = metrics["completed_bars"]
    if count == 0:
        if opening is not None or closing is not None or result["regime"] != "UNCERTAIN":
            raise RoutingConfigError("Empty history must have no candle times and uncertain context")
    else:
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or
               not math.isfinite(value) or value < 0 for value in (opening, closing)):
            raise RoutingConfigError("Classification candle times are invalid")
        assert opening is not None and closing is not None  # Narrow the already validated numeric times.
        if closing > decision:
            raise LookaheadBiasError("Cached regime classification closes after its observation time")
        if bar_close_time(opening, result["timeframe"]) != closing:
            raise RoutingConfigError("Classification candle open and close times disagree")
    metric_names = {"ema_fast", "ema_slow", "atr", "ema_gap_atr", "ema_slope_atr", "movement_efficiency"}
    available = metric_names & set(metrics)
    if available:
        if (available != metric_names or any(isinstance(metrics[name], bool) or
                not isinstance(metrics[name], (int, float)) or not math.isfinite(metrics[name])
                for name in metric_names) or metrics["atr"] <= 0 or
                min(metrics["ema_fast"], metrics["ema_slow"]) <= 0 or
                not 0 <= metrics["movement_efficiency"] <= 1 or count < profile["classifier"]["min_bars"] or
                _regime_from_metrics(metrics, profile["classifier"]) != result["regime"]):
            raise RoutingConfigError("Classification metrics do not support the declared regime")
    elif result["regime"] != "UNCERTAIN":
        raise RoutingConfigError("Known context requires complete metrics")
    result.update({"rule_version": profile["version"], "routing_fingerprint": profile["routing_fingerprint"],
                   "classifier_fingerprint": profile["classifier_fingerprint"], "execution_authority": False})
    regimes = profile["models"][model_id]["regimes"]
    known = result["regime"] != "UNCERTAIN"
    allowed = known and ("ALL" in regimes or result["regime"] in regimes)
    result.update({"model_id": model_id, "allowed": allowed, "allowed_regimes": list(regimes)})
    if not allowed:
        result["reasons"] = list(result["reasons"]) + [
            "UNCERTAIN_CONTEXT_BLOCKED" if not known else "MODEL_REGIME_NOT_ROUTED"]
        if audit is not None:
            audit({"event": "REGIME_ROUTING_REJECTED", **copy.deepcopy(result)})
    return result


def route_signal(model_id: str, bars: list[dict], timeframe: str, as_of: float, *,
                 config: Mapping[str, Any] | None = None,
                 audit: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    """Veto signals outside their profile, recording every rejection when supplied.

    ALL means all three known contexts; it never overrides UNCERTAIN. A failed
    audit callback propagates, preventing a caller from treating it as approval.
    Passing this gate is not a risk approval or permission to submit an order.
    """
    profile = load_routing_config() if config is None else validate_routing_config(config)
    result = classify_regime(bars, timeframe, as_of, config=profile)
    return route_classification(model_id, result, config=profile, audit=audit)
