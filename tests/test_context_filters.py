"""Synthetic closed-candle mechanics; no model or economic-performance claims."""
import copy
import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from nexus.cross_asset_filter import canonical_symbol, evaluate_cross_assets
from nexus.regime_router import load_routing_config
from nexus.session_filter import (
    ContextConfigError,
    context_fingerprint,
    evaluate_session,
    load_context_config,
    validate_context_config,
)
from nexus.strategies import REGISTRY, DataError
from nexus.timeframe_filter import evaluate_timeframes
from nexus.timeframes import PERIODS
from nexus.walkforward import LookaheadBiasError

AS_OF = datetime(2026, 1, 9, 16, tzinfo=UTC).timestamp()


def history(timeframe="H1", direction="UP", *, count=100, lag=0):
    period = PERIODS[timeframe]
    rows = []
    for index in range(count):
        if direction == "UP":
            close = 1.1 + index * 0.001
        elif direction == "DOWN":
            close = 1.3 - index * 0.001
        elif direction == "RANGE":
            close = 1.2 + (0.001 if index % 2 else -0.001)
        else:
            close = 1.2
        rows.append({"time": AS_OF - count * period + index * period - lag,
                     "open": close - 0.0001, "high": close + 0.0005,
                     "low": close - 0.0005, "close": close, "tick_volume": 0, "spread": 2})
    return rows


def context_config():
    return load_context_config()


def cross_rows(target="EURUSD", side="BUY", config=None):
    profile = context_config() if config is None else config
    sign = 1 if side == "BUY" else -1
    return {symbol: history(direction="UP" if orientation * sign == 1 else "DOWN")
            for symbol, orientation in profile["cross_asset"]["policies"][target].items()}


def test_timeframe_filter_uses_completed_bars():
    router = load_routing_config()
    result = evaluate_timeframes("BUY", h4_bars=history("H4"), d1_bars=history("D1"),
                                 as_of=AS_OF, routing_config=router)
    assert result["allowed"] is True
    assert set(result["details"]) == {"H4", "D1"}
    assert all(value["last_closed_time"] == AS_OF for value in result["details"].values())
    assert result["execution_authority"] is False
    future = history("H4")
    future.append(dict(future[-1], time=AS_OF))
    with pytest.raises(LookaheadBiasError):
        evaluate_timeframes("BUY", h4_bars=future, d1_bars=history("D1"), as_of=AS_OF)
    with pytest.raises(LookaheadBiasError):
        evaluate_timeframes("BUY", h4_bars=history("H4"), d1_bars=history("D1"), as_of=AS_OF - 1)


def test_timeframe_filter_rejects_conflict():
    result = evaluate_timeframes("BUY", h4_bars=history("H4"),
                                 d1_bars=history("D1", "DOWN"), as_of=AS_OF)
    assert result["allowed"] is False
    assert "D1_CONTEXT_CONFLICT_OR_UNCERTAIN" in result["reasons"]
    result = evaluate_timeframes("SELL", h4_bars=history("H4", "DOWN"),
                                 d1_bars=history("D1", "DOWN"), as_of=AS_OF)
    assert result["allowed"] is True


@pytest.mark.parametrize("kind", ["RANGE", "FLAT"])
def test_timeframe_filter_range_or_uncertain_never_confirms_direction(kind):
    result = evaluate_timeframes("BUY", h4_bars=history("H4", kind),
                                 d1_bars=history("D1", kind), as_of=AS_OF)
    assert result["allowed"] is False


def test_timeframe_filter_missing_stale_or_insufficient_history_blocks():
    missing = evaluate_timeframes("BUY", h4_bars=[], d1_bars=history("D1"), as_of=AS_OF)
    assert missing["allowed"] is False
    assert "MISSING_H4_HISTORY" in missing["reasons"]
    stale = evaluate_timeframes("BUY", h4_bars=history("H4", lag=PERIODS["H4"]),
                                d1_bars=history("D1"), as_of=AS_OF)
    assert stale["allowed"] is False
    assert "STALE_H4_HISTORY" in stale["reasons"]
    short = evaluate_timeframes("BUY", h4_bars=history("H4", count=59),
                                d1_bars=history("D1"), as_of=AS_OF)
    assert short["allowed"] is False


def test_higher_frame_broker_day_offset_is_allowed_without_inventing_candles():
    result = evaluate_timeframes("BUY", h4_bars=history("H4", lag=3600),
                                 d1_bars=history("D1", lag=7200), as_of=AS_OF)
    assert result["allowed"] is True
    assert result["details"]["D1"]["last_closed_time"] == AS_OF - 7200


def test_cross_asset_filter_requires_alignment():
    rows = cross_rows()
    assert evaluate_cross_assets("EURUSD", "BUY", rows, AS_OF)["allowed"] is True
    # A missing historical bar cannot be hidden by an aligned latest close.
    rows["GBPUSD"].pop(-10)
    result = evaluate_cross_assets("EURUSD", "BUY", rows, AS_OF)
    assert result["allowed"] is False
    assert "CROSS_ASSET_HISTORY_NOT_ALIGNED" in result["reasons"]
    rows = cross_rows()
    rows["GBPUSD"] = history(lag=1800)
    result = evaluate_cross_assets("EURUSD", "BUY", rows, AS_OF)
    assert result["allowed"] is False
    assert "CROSS_ASSET_LAST_CLOSE_NOT_ALIGNED" in result["reasons"]


@pytest.mark.parametrize("symbol", ["EURUSD", "GBPUSD", "USDJPY"])
@pytest.mark.parametrize("side", ["BUY", "SELL"])
def test_cross_asset_currency_direction_correct(symbol, side):
    result = evaluate_cross_assets(symbol, side, cross_rows(symbol, side), AS_OF)
    assert result["allowed"] is True
    assert result["execution_authority"] is False
    for leg, value in result["details"].items():
        coefficient = context_config()["cross_asset"]["policies"][symbol][leg]
        expected_sign = coefficient * (1 if side == "BUY" else -1)
        assert value["expected_regime"] == ("TREND_UP" if expected_sign == 1 else "TREND_DOWN")
        assert value["regime"] == value["expected_regime"]


def test_cross_asset_conflict_missing_dxy_and_staleness_fail_closed():
    rows = cross_rows()
    rows["USDJPY"] = history(direction="UP")
    result = evaluate_cross_assets("EURUSD", "BUY", rows, AS_OF)
    assert result["allowed"] is False
    assert "CROSS_ASSET_USDJPY_CONFLICT_OR_UNCERTAIN" in result["reasons"]
    rows = cross_rows()
    del rows["DXY"]
    result = evaluate_cross_assets("EURUSD", "BUY", rows, AS_OF)
    assert result["allowed"] is False
    assert "MISSING_CROSS_ASSET_DXY" in result["reasons"]
    assert "DXY" not in result["details"]
    rows = cross_rows()
    rows["DXY"] = history(direction="DOWN", lag=3600)
    result = evaluate_cross_assets("EURUSD", "BUY", rows, AS_OF)
    assert result["allowed"] is False
    assert "STALE_CROSS_ASSET_DXY" in result["reasons"]


def test_cross_asset_rejects_future_or_invalid_bars_without_trimming():
    rows = cross_rows()
    rows["DXY"].append(dict(rows["DXY"][-1], time=AS_OF))
    with pytest.raises(LookaheadBiasError):
        evaluate_cross_assets("EURUSD", "BUY", rows, AS_OF)
    rows = cross_rows()
    rows["GBPUSD"][-1]["low"] = -1
    with pytest.raises(DataError):
        evaluate_cross_assets("EURUSD", "BUY", rows, AS_OF)


def test_explicit_symbol_aliases_do_not_guess_prefixes_or_suffixes():
    assert canonical_symbol("eurusd") == "EURUSD"
    for symbol in ("mEURUSD", "EURUSD.a", "USDX", "DOLLAR", "ЕURUSD"):
        with pytest.raises(ValueError):
            canonical_symbol(symbol)
    config = context_config()
    config["cross_asset"]["aliases"].update({"EURUSD.a": "EURUSD", "GBPUSD.a": "GBPUSD"})
    assert canonical_symbol("EURUSD.a", config=config) == "EURUSD"
    rows = cross_rows()
    rows["GBPUSD.a"] = rows.pop("GBPUSD")
    assert evaluate_cross_assets("EURUSD.a", "BUY", rows, AS_OF, config=config)["allowed"] is True
    rows["GBPUSD"] = rows["GBPUSD.a"]
    result = evaluate_cross_assets("EURUSD.a", "BUY", rows, AS_OF, config=config)
    assert result["allowed"] is False
    assert "AMBIGUOUS_CROSS_ASSET_ALIAS_GBPUSD" in result["reasons"]


def test_cross_asset_insufficient_or_uncertain_leg_and_no_policy_block():
    rows = cross_rows()
    rows["DXY"] = history("H1", "FLAT")
    assert evaluate_cross_assets("EURUSD", "BUY", rows, AS_OF)["allowed"] is False
    rows["DXY"] = history("H1", "DOWN", count=59)
    result = evaluate_cross_assets("EURUSD", "BUY", rows, AS_OF)
    assert "INSUFFICIENT_ALIGNED_CROSS_ASSET_DXY" in result["reasons"]
    result = evaluate_cross_assets("DXY", "BUY", {}, AS_OF)
    assert result["allowed"] is False
    assert result["reasons"] == ["NO_EXPLICIT_CROSS_ASSET_POLICY"]


def test_session_filter_respects_session_restrictions():
    config = context_config()
    config["sessions"]["models"]["ema_cross"] = ["LONDON"]
    london = datetime(2026, 1, 9, 8, tzinfo=UTC).timestamp()
    night = datetime(2026, 1, 9, 23, tzinfo=UTC).timestamp()
    assert evaluate_session("ema_cross", london, config=config)["allowed"] is True
    assert evaluate_session("ema_cross", night, config=config)["allowed"] is False
    assert evaluate_session("support_bounce", night, config=config)["allowed"] is True
    config["sessions"]["models"]["ema_cross"] = []
    assert evaluate_session("ema_cross", london, config=config)["allowed"] is False


@pytest.mark.parametrize(("hour", "minute", "expected"), [
    (6, 59, {"ASIA"}), (7, 0, {"LONDON"}), (12, 0, {"LONDON", "NEW_YORK"}),
    (15, 59, {"LONDON", "NEW_YORK"}), (16, 0, {"NEW_YORK"}),
    (21, 0, set()), (22, 0, {"ASIA"}), (0, 0, {"ASIA"}),
])
def test_utc_session_boundaries_and_overlap(hour, minute, expected):
    observed = datetime(2026, 1, 9, hour, minute, tzinfo=UTC).timestamp()
    result = evaluate_session("ema_cross", observed)
    assert set(result["sessions"]) == expected
    assert result["allowed"] is True  # ALL is explicit, including the 21:00-22:00 UTC gap.
    assert result["execution_authority"] is False


def test_sessions_are_fixed_utc_across_dst_and_all_58_are_explicit():
    config = context_config()
    assert set(config["sessions"]["models"]) == set(REGISTRY)
    assert len(config["sessions"]["models"]) == 58
    assert all(names == ["ALL"] for names in config["sessions"]["models"].values())
    winter = datetime(2026, 1, 9, 8, tzinfo=UTC).timestamp()
    summer = datetime(2026, 7, 9, 8, tzinfo=UTC).timestamp()
    assert evaluate_session("ema_cross", winter)["sessions"] == evaluate_session("ema_cross", summer)["sessions"]
    with pytest.raises(ContextConfigError):
        evaluate_session("not_model_59", winter)


@pytest.mark.parametrize("mutation", [
    lambda cfg: cfg.update(version="latest"),
    lambda cfg: cfg.update(schema_version=True),
    lambda cfg: cfg.update(execution_authority=True),
    lambda cfg: cfg.update(mode="LIVE"),
    lambda cfg: cfg.update(extra=True),
    lambda cfg: cfg["multi_timeframe"].update(timeframes=["H1"]),
    lambda cfg: cfg["multi_timeframe"].update(maximum_age_periods=2),
    lambda cfg: cfg["cross_asset"].update(timeframe="M5"),
    lambda cfg: cfg["cross_asset"].update(minimum_aligned_bars=59),
    lambda cfg: cfg["cross_asset"].update(maximum_age_bars=2),
    lambda cfg: cfg["cross_asset"]["aliases"].update(EURUSD="USDJPY"),
    lambda cfg: cfg["cross_asset"]["aliases"].update(FAKE=[]),
    lambda cfg: cfg["cross_asset"]["policies"]["EURUSD"].update(USDJPY=1),
    lambda cfg: cfg["sessions"].update(timezone="Europe/London"),
    lambda cfg: cfg["sessions"]["windows"]["LONDON"].update(start_hour=True),
    lambda cfg: cfg["sessions"]["windows"]["LONDON"].update(end_hour=7),
    lambda cfg: cfg["sessions"]["models"].pop("ema_cross"),
    lambda cfg: cfg["sessions"]["models"].update(new_model_59=["ALL"]),
    lambda cfg: cfg["sessions"]["models"].update(ema_cross=["ALL", "ASIA"]),
    lambda cfg: cfg["sessions"]["models"].update(ema_cross=["LONDON", "LONDON"]),
    lambda cfg: cfg.update(notes=[]),
])
def test_context_configuration_is_versioned_validated_and_fail_closed(mutation):
    config = context_config()
    mutation(config)
    with pytest.raises(ContextConfigError):
        validate_context_config(config)


def test_config_loader_hash_detachment_schema_and_duplicate_json_keys(tmp_path):
    config = context_config()
    original = copy.deepcopy(config)
    assert context_fingerprint(config) == config["context_fingerprint"]
    assert validate_context_config(config) == config
    assert config == original
    config["sessions"]["models"]["ema_cross"] = ["LONDON"]
    assert context_fingerprint(config) != original["context_fingerprint"]
    target = tmp_path / "context.json"
    target.write_text(json.dumps(config), encoding="utf-8")
    assert load_context_config(target)["sessions"]["models"]["ema_cross"] == ["LONDON"]
    duplicate = json.dumps(config)[:-1] + ',"version":"1.0.0"}'
    target.write_text(duplicate, encoding="utf-8")
    with pytest.raises(ContextConfigError, match="Duplicate"):
        load_context_config(target)
    with pytest.raises(ContextConfigError):
        load_context_config(tmp_path / "missing")


@pytest.mark.parametrize("as_of", [-1, True, float("nan"), float("inf"), "now"])
def test_all_context_filters_reject_invalid_observation_time(as_of):
    with pytest.raises(ValueError):
        evaluate_session("ema_cross", as_of)
    with pytest.raises(ValueError):
        evaluate_timeframes("BUY", h4_bars=[], d1_bars=[], as_of=as_of)
    with pytest.raises(ValueError):
        evaluate_cross_assets("EURUSD", "BUY", {}, as_of)


def test_direction_validation_does_not_guess_and_long_short_are_explicit_aliases():
    assert evaluate_timeframes("LONG", h4_bars=history("H4"), d1_bars=history("D1"), as_of=AS_OF)["direction"] == "BUY"
    assert evaluate_timeframes("SHORT", h4_bars=history("H4", "DOWN"), d1_bars=history("D1", "DOWN"), as_of=AS_OF)["direction"] == "SELL"
    with pytest.raises(ValueError):
        evaluate_timeframes("WAIT", h4_bars=[], d1_bars=[], as_of=AS_OF)
    with pytest.raises(ValueError):
        evaluate_cross_assets("EURUSD", "WAIT", {}, AS_OF)


def test_shared_join_selects_last_300_native_common_rows_not_300_independent_rows(tmp_path):
    module_path = Path(__file__).resolve().parents[1] / "tools/context_layer_study.py"
    spec = importlib.util.spec_from_file_location("context_join_independent_fixture", module_path)
    study = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(study)
    source = history(count=900)
    fixtures = {"GBPUSD": source, "USDJPY": source,
                "DXY": [row for index, row in enumerate(source) if index % 24 not in {21, 22}]}
    streams = {}
    for symbol, rows in fixtures.items():
        path = tmp_path / f"{symbol}_H1.csv"
        lines = ["<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>,<TICKVOL>,<SPREAD>"]
        for row in rows:
            stamp = datetime.fromtimestamp(row["time"], UTC)
            lines.append(",".join([stamp.strftime("%Y.%m.%d"), stamp.strftime("%H:%M:%S"),
                                   *(str(row[key]) for key in ("open", "high", "low", "close")), "0", "2"]))
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        streams[symbol] = study.NativeSeries(path, "H1", expected_sha256=study.hashlib.sha256(path.read_bytes()).hexdigest())
    for decision in (AS_OF, source[799]["time"] + 3600):
        past = {symbol: stream.asof(decision, count=None) for symbol, stream in streams.items()}
        selected = study.align_native_legs(past, decision)
        common = sorted(set.intersection(*({row["time"] for row in rows} for rows in past.values())))[-300:]
        assert len(common) == 300
        for symbol, rows in selected.items():
            assert [row["time"] for row in rows] == common
            assert all(row in past[symbol] and row["time"] + 3600 <= decision for row in rows)
        prematurely_truncated = study.align_native_legs(
            {symbol: stream.asof(decision) for symbol, stream in streams.items()}, decision)
        assert len(prematurely_truncated["DXY"]) < 300
