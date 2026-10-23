"""Closed OHLC fixtures prove routing mechanics, never strategy profitability."""
import copy
import json
import math

import pytest

from nexus.regime_router import (
    CLASSIFIER_DEFAULTS,
    RoutingConfigError,
    classifier_fingerprint,
    classify_regime,
    load_routing_config,
    route_classification,
    route_signal,
    routing_fingerprint,
    validate_routing_config,
)
from nexus.strategies import REGISTRY, DataError
from nexus.walkforward import LookaheadBiasError


def profile():
    source = {"diagnostic_report_sha256": "0" * 64, "native_csv_sha256": "1" * 64}
    diagnostic = {name: {"trades": 0, "net_r": 0.0} for name in ("UP", "DOWN", "RANGE", "UNKNOWN")}
    diagnostic.update(selection_reason="SYNTHETIC_MECHANICS_FIXTURE", prior_sample_adequate=False)
    return {
        "schema_version": 1, "version": "1.0.0", "mode": "RESEARCH_ONLY",
        "execution_authority": False,
        "source": {**source, "selection_rule": "Synthetic mechanics fixture only",
                   "minimum_prior_trades": 5, "limitations": ["No performance evidence"] * 7},
        "classifier": dict(CLASSIFIER_DEFAULTS),
        "models": {model: {"regimes": ["ALL"], "source": dict(source),
                           "diagnostic": copy.deepcopy(diagnostic)} for model in REGISTRY},
    }


def candles(kind="UP", count=100):
    rows = []
    for index in range(count):
        if kind == "UP":
            close = 1.1 + index * 0.001
        elif kind == "DOWN":
            close = 1.3 - index * 0.001
        elif kind == "RANGE":
            close = 1.2 + (0.001 if index % 2 else -0.001)
        else:
            close = 1.2
        rows.append({"time": 1_700_000_000 + 3600 * index, "open": close - 0.0001,
                     "close": close, "high": close + 0.0005, "low": close - 0.0005,
                     "tick_volume": 0, "spread": 2})
    return rows


def observed_at(rows):
    return rows[-1]["time"] + 3600


def test_regime_router_no_lookahead():
    rows = candles()
    decision = observed_at(rows)
    with pytest.raises(LookaheadBiasError, match="future or unfinished"):
        classify_regime(rows + [dict(rows[-1], time=decision)], "H1", decision, config=profile())
    with pytest.raises(LookaheadBiasError):
        route_signal("ema_cross", rows, "H1", decision - 1, config=profile())
    # The latest signal candle is observable exactly at its close.
    assert classify_regime(rows, "H1", decision, config=profile())["regime"] == "TREND_UP"


def test_regime_classification():
    rows = candles("UP")
    result = classify_regime(rows, "H1", observed_at(rows), config=profile())
    assert result["regime"] == "TREND_UP"
    assert result["metrics"]["movement_efficiency"] == pytest.approx(1)
    assert result["metrics"]["ema_gap_atr"] > 0.5
    assert result["metrics"]["ema_slope_atr"] > 0.25
    assert result["last_closed_time"] <= result["decision_time"]
    assert result["execution_authority"] is False


@pytest.mark.parametrize(("kind", "expected"), [("DOWN", "TREND_DOWN"), ("RANGE", "RANGE")])
def test_down_and_range_classification(kind, expected):
    rows = candles(kind)
    result = classify_regime(rows, "H1", observed_at(rows), config=profile())
    assert result["regime"] == expected
    assert 0 <= result["metrics"]["movement_efficiency"] <= 1


def test_routing_respects_regime():
    config = profile()
    config["models"]["ema_cross"]["regimes"] = ["RANGE"]
    rows = candles("UP")
    events = []
    result = route_signal("ema_cross", rows, "H1", observed_at(rows), config=config, audit=events.append)
    assert result["regime"] == "TREND_UP"
    assert result["allowed"] is False
    assert "MODEL_REGIME_NOT_ROUTED" in result["reasons"]
    assert len(events) == 1
    assert events[0]["event"] == "REGIME_ROUTING_REJECTED"
    assert events[0]["routing_fingerprint"] == routing_fingerprint(config)
    rows = candles("RANGE")
    assert route_signal("ema_cross", rows, "H1", observed_at(rows), config=config)["allowed"] is True


def test_uncertain_blocks_trading():
    rows = candles("FLAT")
    results = [route_signal(model, rows, "H1", observed_at(rows), config=profile()) for model in REGISTRY]
    assert len(results) == 58
    assert sum(result["allowed"] for result in results) == 0
    assert all(result["regime"] == "UNCERTAIN" for result in results)
    assert all("UNCERTAIN_CONTEXT_BLOCKED" in result["reasons"] for result in results)


def test_insufficient_history_and_zero_volatility_fail_closed():
    rows = candles(count=59)
    result = route_signal("ema_cross", rows, "H1", observed_at(rows), config=profile())
    assert result["regime"] == "UNCERTAIN"
    assert result["allowed"] is False
    assert "INSUFFICIENT_CLOSED_HISTORY" in result["reasons"]
    assert classify_regime([], "H1", 0, config=profile())["regime"] == "UNCERTAIN"
    flat = [dict(row, open=1, high=1, low=1, close=1) for row in candles("FLAT")]
    assert classify_regime(flat, "H1", observed_at(flat), config=profile())["regime"] == "UNCERTAIN"


def test_threshold_change_changes_context_without_mutating_model_rules():
    rows = candles()
    config = profile()
    assert classify_regime(rows, "H1", observed_at(rows), config=config)["regime"] == "TREND_UP"
    before = copy.deepcopy(REGISTRY)
    config["classifier"]["trend_min_ema_gap_atr"] = 20
    assert classify_regime(rows, "H1", observed_at(rows), config=config)["regime"] == "UNCERTAIN"
    assert REGISTRY == before


def test_all_never_overrides_uncertain_and_empty_profile_never_allows():
    config = profile()
    config["models"]["ema_cross"]["regimes"] = []
    rows = candles()
    assert route_signal("ema_cross", rows, "H1", observed_at(rows), config=config)["allowed"] is False
    rows = candles("RANGE")
    assert route_signal("support_bounce", rows, "H1", observed_at(rows), config=config)["allowed"] is True


@pytest.mark.parametrize("mutation", [
    lambda cfg: cfg.update(version="unversioned"),
    lambda cfg: cfg.update(schema_version=True),
    lambda cfg: cfg.update(execution_authority=True),
    lambda cfg: cfg.update(mode="LIVE"),
    lambda cfg: cfg["models"].pop("ema_cross"),
    lambda cfg: cfg["models"].update(unknown_model={"regimes": ["ALL"]}),
    lambda cfg: cfg["models"]["ema_cross"].update(regimes=["UNCERTAIN"]),
    lambda cfg: cfg["models"]["ema_cross"].update(regimes=["RANGE", "RANGE"]),
    lambda cfg: cfg["models"]["ema_cross"].update(regimes=["ALL", "RANGE"]),
    lambda cfg: cfg["classifier"].update(min_bars=59),
    lambda cfg: cfg["classifier"].update(ema_fast=50),
    lambda cfg: cfg["classifier"].update(slope_bars=0),
    lambda cfg: cfg["classifier"].update(atr_period=math.nan),
    lambda cfg: cfg["classifier"].update(trend_min_efficiency=True),
    lambda cfg: cfg["classifier"].update(range_max_efficiency=0.5),
    lambda cfg: cfg["classifier"].update(extra=1),
    lambda cfg: cfg["source"].update(native_csv_sha256="unknown"),
])
def test_invalid_profile_rejected(mutation):
    config = profile()
    mutation(config)
    with pytest.raises(RoutingConfigError):
        validate_routing_config(config)


@pytest.mark.parametrize("mutation", [
    lambda rows: rows[-1].update(time=rows[-2]["time"]),
    lambda rows: rows[-1].update(time=-1),
    lambda rows: rows[-1].update(time=True),
    lambda rows: rows[-1].update(close=math.nan),
    lambda rows: rows[-1].update(low=-1),
    lambda rows: rows[-1].update(high=rows[-1]["close"] - 1),
    lambda rows: rows[-1].update(tick_volume=-1),
])
def test_invalid_timestamp_geometry_or_activity_is_not_silently_trimmed(mutation):
    rows = candles()
    decision = observed_at(rows)
    mutation(rows)
    with pytest.raises(DataError):
        classify_regime(rows, "H1", decision, config=profile())


def test_profile_snapshot_hash_and_loader(tmp_path):
    config = profile()
    validated = validate_routing_config(config)
    assert validated["routing_fingerprint"] == routing_fingerprint(config)
    assert validated["routing_fingerprint"] == routing_fingerprint(dict(reversed(list(config.items()))))
    config["models"]["ema_cross"]["regimes"] = []
    assert validated["models"]["ema_cross"]["regimes"] == ["ALL"]
    assert validated["routing_fingerprint"] != routing_fingerprint(config)
    target = tmp_path / "routing.yaml"
    target.write_text(json.dumps(validated), encoding="utf-8")
    assert load_routing_config(target) == validated
    target.write_text("not a config", encoding="utf-8")
    with pytest.raises(RoutingConfigError):
        load_routing_config(target)
    with pytest.raises(RoutingConfigError):
        load_routing_config(tmp_path / "missing.yaml")


def test_audit_failure_blocks_caller_and_approval_does_not_fabricate_rejection():
    rows = candles()
    config = profile()
    events = []
    assert route_signal("ema_cross", rows, "H1", observed_at(rows), config=config,
                        audit=events.append)["allowed"] is True
    assert events == []
    config["models"]["ema_cross"]["regimes"] = []

    def unavailable(_event):
        raise OSError("audit unavailable")

    with pytest.raises(OSError, match="audit unavailable"):
        route_signal("ema_cross", rows, "H1", observed_at(rows), config=config, audit=unavailable)
    with pytest.raises(RoutingConfigError, match="Unknown routing model"):
        route_signal("unknown", rows, "H1", observed_at(rows), config=config)


def test_normalized_metrics_use_declared_periods():
    rows = candles()
    result = classify_regime(rows, "H1", observed_at(rows), config=profile())
    metrics = result["metrics"]
    assert metrics["ema_slope_atr"] == pytest.approx(5 * 0.001 / metrics["atr"], rel=0.002)
    assert metrics["movement_efficiency"] == pytest.approx(1)


def test_cached_classification_matches_fresh_routing_and_new_map_only_changes_veto():
    rows = candles()
    config = profile()
    classified = classify_regime(rows, "H1", observed_at(rows), config=config)
    assert route_classification("ema_cross", classified, config=config) == route_signal(
        "ema_cross", rows, "H1", observed_at(rows), config=config)
    updated = copy.deepcopy(config)
    updated["version"] = "1.0.1"
    updated["models"]["ema_cross"]["regimes"] = ["RANGE"]
    events = []
    denied = route_classification("ema_cross", classified, config=updated, audit=events.append)
    assert denied["allowed"] is False
    assert denied["rule_version"] == "1.0.1"
    assert denied["routing_fingerprint"] != classified["routing_fingerprint"]
    assert denied["classifier_fingerprint"] == classified["classifier_fingerprint"]
    assert denied["classifier_fingerprint"] == classifier_fingerprint(updated)
    assert len(events) == 1
    assert classified["reasons"] == ["CLOSED_CANDLE_CONTEXT_CLASSIFIED"]
    assert "allowed" not in classified


def test_cached_context_still_blocks_uncertain_and_audit_failure():
    rows = candles("FLAT")
    config = profile()
    classified = classify_regime(rows, "H1", observed_at(rows), config=config)
    result = route_classification("ema_cross", classified, config=config)
    assert result["regime"] == "UNCERTAIN"
    assert result["allowed"] is False

    def unavailable(_event):
        raise OSError("cached audit unavailable")

    with pytest.raises(OSError, match="cached audit unavailable"):
        route_classification("ema_cross", classified, config=config, audit=unavailable)


def test_cached_context_rejects_changed_classifier():
    rows = candles()
    config = profile()
    classified = classify_regime(rows, "H1", observed_at(rows), config=config)
    config["classifier"]["trend_min_ema_gap_atr"] = 0.6
    with pytest.raises(RoutingConfigError, match="fingerprint"):
        route_classification("ema_cross", classified, config=config)


@pytest.mark.parametrize("mutation", [
    lambda value: value.update(regime="UNKNOWN"),
    lambda value: value.update(regime="TREND_DOWN"),
    lambda value: value.update(classification_source="external_prediction"),
    lambda value: value.update(execution_authority=True),
    lambda value: value.update(decision_time=float("nan")),
    lambda value: value.update(timeframe="UNKNOWN"),
    lambda value: value.update(last_closed_time=value["last_closed_time"] - 1),
    lambda value: value.update(last_bar_open_time=value["last_bar_open_time"] - 3600),
    lambda value: value.update(reasons=[]),
    lambda value: value["metrics"].update(completed_bars=True),
    lambda value: value["metrics"].update(completed_bars=59),
    lambda value: value["metrics"].update(movement_efficiency=2),
    lambda value: value["metrics"].update(atr=0),
    lambda value: value["metrics"].update(ema_gap_atr=float("nan")),
    lambda value: value["metrics"].pop("ema_fast"),
])
def test_cached_context_rejects_malformed_or_unsupported_classification(mutation):
    rows = candles()
    config = profile()
    value = classify_regime(rows, "H1", observed_at(rows), config=config)
    mutation(value)
    with pytest.raises(RoutingConfigError):
        route_classification("ema_cross", value, config=config)


def test_cached_context_rejects_future_and_cannot_forge_history_for_empty_prefix():
    rows = candles()
    config = profile()
    value = classify_regime(rows, "H1", observed_at(rows), config=config)
    value["decision_time"] -= 1
    with pytest.raises(LookaheadBiasError):
        route_classification("ema_cross", value, config=config)
    value = classify_regime([], "H1", 0, config=config)
    assert route_classification("ema_cross", value, config=config)["allowed"] is False
    value["last_bar_open_time"] = 0
    with pytest.raises(RoutingConfigError, match="Empty history"):
        route_classification("ema_cross", value, config=config)


@pytest.mark.parametrize("mutation", [
    lambda cfg: cfg.update(unknown=1),
    lambda cfg: cfg["source"].pop("selection_rule"),
    lambda cfg: cfg["source"].pop("limitations"),
    lambda cfg: cfg["source"].update(minimum_prior_trades=True),
    lambda cfg: cfg["source"].update(limitations=[]),
    lambda cfg: cfg["models"]["ema_cross"].pop("source"),
    lambda cfg: cfg["models"]["ema_cross"].pop("diagnostic"),
    lambda cfg: cfg["models"]["ema_cross"].update(extra=1),
    lambda cfg: cfg["models"]["ema_cross"]["source"].update(native_csv_sha256="2" * 64),
    lambda cfg: cfg["models"]["ema_cross"]["diagnostic"].pop("UP"),
    lambda cfg: cfg["models"]["ema_cross"]["diagnostic"].update(prior_sample_adequate=0),
    lambda cfg: cfg["models"]["ema_cross"]["diagnostic"]["UP"].update(trades=True),
    lambda cfg: cfg["models"]["ema_cross"]["diagnostic"]["UP"].update(trades=-1),
    lambda cfg: cfg["models"]["ema_cross"]["diagnostic"]["UP"].update(net_r=float("inf")),
    lambda cfg: cfg["models"]["ema_cross"]["diagnostic"]["UP"].update(extra=1),
])
def test_required_metadata_matches_strict_schema(mutation):
    config = profile()
    mutation(config)
    with pytest.raises(RoutingConfigError):
        validate_routing_config(config)


@pytest.mark.parametrize("key", ["schema_version", "version", "classifier"])
def test_duplicate_json_keys_are_rejected_even_when_complete_document_is_valid(tmp_path, key):
    config = profile()
    original = json.dumps(config)
    duplicate = original[:-1] + "," + json.dumps(key) + ":" + json.dumps(config[key]) + "}"
    target = tmp_path / "routing.yaml"
    target.write_text(duplicate, encoding="utf-8")
    with pytest.raises(RoutingConfigError, match="Duplicate routing configuration key"):
        load_routing_config(target)


def test_duplicate_nested_model_key_is_rejected_without_overwrite(tmp_path):
    config = profile()
    text = json.dumps(config)
    needle = json.dumps("ema_cross") + ": " + json.dumps(config["models"]["ema_cross"])
    text = text.replace(needle, needle + "," + needle, 1)
    target = tmp_path / "routing.yaml"
    target.write_text(text, encoding="utf-8")
    with pytest.raises(RoutingConfigError, match="Duplicate routing configuration key: ema_cross"):
        load_routing_config(target)

