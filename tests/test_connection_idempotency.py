"""Repeat connection verification cannot silently revoke or create authority.

All terminals/accounts are isolated SimBroker fixtures. No native MT5 import,
network request, live database access or broker order is used by these tests.
"""
import copy
from pathlib import Path
from unittest.mock import patch

import pytest

from nexus.broker import BrokerError
from nexus.engine import Engine

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def connected(tmp_path):
    now = [1792368000 + 12 * 3600]
    engine = Engine(ROOT, tmp_path, clock=lambda: now[0])
    engine._connect(True)
    yield engine, now
    engine.stop_worker()
    if engine.store:
        engine.store.close()
    engine.cache.db.close()
    engine.news.db.close()


def authorize(engine, mode="AUTO_DEMO"):
    settings = {"daily_risk": 1000., "daily_target": 2000., "commission_per_lot": 0.,
                "slippage_points": 10., "max_trade_fraction": .2, "correlation_cap_fraction": .5}
    engine.executor.activate(mode, settings)
    engine.settings = copy.deepcopy(engine.risk.settings)
    engine.status = mode


@pytest.mark.parametrize("mode", ["AUTO_DEMO", "MANUAL_DEMO"])
def test_same_source_preserves_original_authorization_and_objects(connected, mode):
    engine, _now = connected
    authorize(engine, mode)
    previous = engine.broker, engine.store, engine.risk, engine.executor, engine.scanner
    authorization = copy.deepcopy(engine.executor.authorization)
    settings = copy.deepcopy(engine.settings)
    engine.quant_results["retained-evidence"] = {"qualified": False}
    with patch("nexus.engine.SimBroker", side_effect=AssertionError("Must not reinitialize")):
        result = engine._connect(True)
    assert result["connection_reused"] is True
    assert result["authorization_preserved"] is True
    assert previous == (engine.broker, engine.store, engine.risk, engine.executor, engine.scanner)
    assert engine.executor.authorization == authorization
    assert engine.settings == settings
    assert engine.status == mode
    assert engine.quant_results == {"retained-evidence": {"qualified": False}}
    assert engine.broker.sent == []
    event = engine.store.recent_audit()[0]
    assert event["event"] == "CONNECTION_VERIFIED_UNCHANGED"
    assert event["payload"]["authorization_preserved"] is True


def test_same_source_read_only_never_creates_authority(connected):
    engine, _now = connected
    original = engine.executor
    result = engine._connect(True)
    assert result["connection_reused"] is True
    assert result["authorization_preserved"] is False
    assert engine.executor is original
    assert engine.executor.mode == engine.status == "READ_ONLY"
    assert engine.executor.authorization is None
    assert engine.executor.entries_paused is True
    assert engine.broker.sent == []


def test_same_source_does_not_resume_explicitly_stopped_entries(connected):
    engine, _now = connected
    authorize(engine)
    engine.executor.stop_entries("Synthetic explicit stop")
    engine.status = "ENTRIES_STOPPED"
    engine._connect(True)
    assert engine.status == "ENTRIES_STOPPED"
    assert engine.executor.entries_paused is True
    assert engine.executor.authorization is not None
    assert engine.broker.sent == []


@pytest.mark.parametrize("field,value", [("login", 900002), ("server", "OTHER-SYNTHETIC"),
                                         ("platform_id", "OTHER-SYNTHETIC-TERMINAL")])
def test_changed_full_account_identity_revokes_instead_of_preserving(connected, field, value):
    engine, _now = connected
    authorize(engine)
    old = engine.executor
    engine.broker._account[field] = value
    result = engine._connect(True)
    assert result["ok"] is True
    assert old.authorization is None
    assert old.mode == "READ_ONLY"
    assert engine.executor is not old
    assert engine.executor.authorization is None
    assert engine.executor.mode == "READ_ONLY"
    assert engine.broker.sent == []


@pytest.mark.parametrize("property_name,value", [("trade_allowed", False), ("trade_allowed", None),
                                                ("trade_expert", False), ("trade_expert", None),
                                                ("trade_mode", 2), ("trade_mode", None)])
def test_changed_or_unknown_account_permission_revokes(connected, property_name, value):
    engine, _now = connected
    authorize(engine)
    old = engine.executor
    engine.broker._account[property_name] = value
    engine._connect(True)
    assert old.authorization is None
    assert engine.executor.mode == "READ_ONLY"
    assert engine.executor.authorization is None
    assert engine.broker.sent == []


@pytest.mark.parametrize("change", [{"connected": False}, {"trade_allowed": None},
                                   {"tradeapi_disabled": None}, {"tradeapi_disabled": True}])
def test_disconnected_or_unknown_terminal_permission_revokes(connected, change):
    engine, _now = connected
    authorize(engine)
    old = engine.executor
    terminal = engine.broker.terminal()
    with patch.object(engine.broker, "terminal", return_value={**terminal, **change}):
        engine._connect(True)
    assert old.authorization is None
    assert engine.executor.mode == "READ_ONLY"
    assert engine.broker.sent == []


def test_partial_read_failure_and_failed_reinitialize_leave_no_authority(connected):
    engine, _now = connected
    authorize(engine)
    old_executor = engine.executor
    with (patch.object(engine.broker, "terminal", side_effect=BrokerError("Synthetic terminal timeout")),
          patch("nexus.engine.SimBroker", side_effect=BrokerError("Synthetic reconnect failure")),
          pytest.raises(BrokerError, match="reconnect failure")):
        engine._connect(True)
    assert old_executor.mode == "READ_ONLY"
    assert old_executor.authorization is None
    assert engine.executor is None
    assert engine.status == "DISCONNECTED"


@pytest.mark.parametrize("new_paths", [("different-terminal", ""), ("", "different-bridge")])
def test_different_connection_source_revokes_even_same_account(connected, new_paths):
    engine, _now = connected
    authorize(engine)
    old = engine.executor
    engine._connect(True, *new_paths)
    assert old.authorization is None
    assert engine.executor is not old
    assert engine.executor.mode == "READ_ONLY"
    assert engine.broker.sent == []


def test_identity_switch_during_health_check_cannot_preserve_authority(connected):
    engine, _now = connected
    authorize(engine)
    old = engine.executor
    original = engine.broker.account
    reads = [0]
    def switching_account():
        reads[0] += 1
        if reads[0] == 3:
            engine.broker._account["login"] += 1
        return original()
    with patch.object(engine.broker, "account", side_effect=switching_account):
        engine._connect(True)
    assert old.authorization is None
    assert engine.executor.mode == "READ_ONLY"
    assert engine.executor.authorization is None
    assert engine.broker.sent == []


def test_utc_day_change_revokes_instead_of_renewing(connected):
    engine, now = connected
    authorize(engine)
    old = engine.executor
    now[0] += 86400
    engine._connect(True)
    assert old.authorization is None
    assert engine.executor.mode == "READ_ONLY"
    assert engine.executor.authorization is None


def test_unknown_permission_on_final_authorization_read_revokes(connected):
    engine, _now = connected
    authorize(engine)
    old = engine.executor
    original = engine.broker.account
    reads = [0]
    def uncertain_on_final_read():
        reads[0] += 1
        if reads[0] == 4:
            engine.broker._account["trade_expert"] = None
        return original()
    with patch.object(engine.broker, "account", side_effect=uncertain_on_final_read):
        engine._connect(True)
    assert old.authorization is None
    assert engine.executor.mode == "READ_ONLY"
    assert engine.broker.sent == []


@pytest.mark.parametrize("final_change", ["unknown_permission", "utc_day", "settings"])
def test_last_terminal_read_cannot_extend_authority(connected, final_change):
    engine, now = connected
    authorize(engine)
    old = engine.executor
    original = engine.broker.terminal
    reads = [0]
    def changed_on_final_terminal():
        reads[0] += 1
        terminal = original()
        if reads[0] == 5:
            if final_change == "unknown_permission":
                terminal["trade_allowed"] = None
            elif final_change == "utc_day":
                now[0] += 86400
            else:
                engine.risk.settings["slippage_points"] += 1
        return terminal
    with patch.object(engine.broker, "terminal", side_effect=changed_on_final_terminal):
        engine._connect(True)
    assert old.authorization is None
    assert engine.executor.mode == "READ_ONLY"
    assert engine.executor.authorization is None
    assert engine.broker.sent == []


def test_same_source_audit_failure_leaves_memory_fail_closed(connected):
    engine, _now = connected
    authorize(engine)
    old = engine.executor
    def failing_audit(_event, _payload):
        raise OSError("Synthetic audit disk write failure")
    with (patch.object(engine.store, "audit", side_effect=failing_audit),
          pytest.raises(OSError, match="audit disk write failure")):
        engine._connect(True)
    assert old.mode == "READ_ONLY"
    assert old.authorization is None
    assert engine.broker.sent == []
