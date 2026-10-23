"""Candidate opt-in context vetoes, using only an isolated synthetic broker."""
import copy
import json
import sqlite3

import pytest

from nexus import regime_router
from nexus.broker import SimBroker
from nexus.execution import Executor
from nexus.risk import RiskManager
from nexus.store import Store, account_key


class RoutingBroker(SimBroker):
    def __init__(self, clock):
        super().__init__(clock)
        self.rows = []
        self.check_hook = None

    def bars(self, name, timeframe, count):
        return copy.deepcopy(self.rows[-count:])

    def check(self, request):
        if self.check_hook is not None:
            callback, self.check_hook = self.check_hook, None
            callback()
        return super().check(request)


def closed_bars(as_of, *, trend=True):
    rows = []
    for index in range(100):
        opening = 1.07 + index * .0001 if trend else 1.08
        close = opening + .00008 if trend else opening
        rows.append({"time": as_of - (100 - index) * 3600, "open": opening,
                     "high": max(opening, close) + .00002,
                     "low": min(opening, close) - .00002, "close": close,
                     "tick_volume": 100, "spread": 1, "real_volume": 0})
    return rows


@pytest.fixture
def gate(tmp_path):
    now = [1760000000 // 3600 * 3600 + 10]
    signal_time = now[0] - 10
    broker = RoutingBroker(lambda: now[0])
    broker.rows = closed_bars(signal_time)
    config_path = tmp_path / "routing.yaml"
    config = json.loads(regime_router.DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    config["models"]["ema_cross"]["regimes"] = ["ALL"]
    config_path.write_text(json.dumps(config), encoding="utf-8")
    store = Store(tmp_path / "synthetic.sqlite3")
    risk = RiskManager(broker, store)
    executor = Executor(broker, store, risk, lambda: now[0],
                        regime_routing_enabled=True, routing_config_path=config_path)
    settings = {"daily_risk": 1000., "daily_target": 1000., "commission_per_lot": 0.,
                "slippage_points": 0., "max_trade_fraction": .2, "correlation_cap_fraction": .5}
    proposal = {"id": "synthetic-regime-entry", "symbol": "EURUSD.demo", "side": "BUY",
                "strategy_id": "ema_cross", "timeframe": "H1", "sl": 1.075, "tp": 1.09,
                "qualified": True, "news_ok": True, "data_time": signal_time,
                "expires_at": signal_time + 3600}
    yield {"broker": broker, "store": store, "risk": risk, "executor": executor,
           "settings": settings, "proposal": proposal, "now": now,
           "config": config, "config_path": config_path}
    store.close()


def activate(gate, mode="AUTO_DEMO"):
    gate["executor"].activate(mode, gate["settings"])


def last_refusal(gate):
    return next(row["payload"] for row in gate["store"].recent_audit()
                if row["event"] == "REGIME_ROUTING_REJECTED")


def assert_unsent(gate, result):
    assert result["approved"] is False, result
    assert gate["broker"].sent == []
    assert gate["store"].snapshot(gate["risk"].key, gate["now"][0])["reserved"] == 0


def test_candidate_gate_rejects_future_bar_and_audits_account(gate):
    activate(gate)
    future = dict(gate["broker"].rows[-1], time=gate["proposal"]["data_time"])
    gate["broker"].rows.append(future)
    result = gate["executor"].execute(gate["proposal"])
    assert_unsent(gate, result)
    assert "future" in result["reason"]
    audit = last_refusal(gate)
    assert audit["account_key"] == account_key(gate["broker"].account())
    assert audit["model_id"] == "ema_cross"
    assert audit["rule_version"] == gate["config"]["version"]
    assert len(audit["routing_fingerprint"]) == len(audit["snapshot_sha256"]) == 64


def test_candidate_uncertain_blocks_trading_with_no_reservation(gate):
    activate(gate)
    gate["broker"].rows = gate["broker"].rows[-10:]
    result = gate["executor"].execute(gate["proposal"])
    assert_unsent(gate, result)
    assert last_refusal(gate)["regime"] == "UNCERTAIN"
    assert gate["store"].intents() == []


def test_candidate_range_model_cannot_enter_uptrend(gate):
    gate["config"]["models"]["ema_cross"]["regimes"] = ["RANGE"]
    gate["config_path"].write_text(json.dumps(gate["config"]), encoding="utf-8")
    activate(gate)
    result = gate["executor"].execute(gate["proposal"])
    assert_unsent(gate, result)
    assert last_refusal(gate)["regime"] == "TREND_UP"


@pytest.mark.parametrize("side", ["BUY", "SELL"])
def test_allowed_regime_keeps_original_buy_sell_risk_path(gate, side):
    activate(gate)
    proposal = dict(gate["proposal"], side=side)
    if side == "SELL":
        proposal.update(sl=1.09, tp=1.075)
    result = gate["executor"].execute(proposal)
    assert result["approved"] is True, result
    assert result["confirmed"] is True
    assert len(gate["broker"].sent) == 1
    intent = gate["store"].intent(result["intent_id"])
    assert intent["payload"]["proposal"]["regime_routing"]["regime"] == "TREND_UP"
    assert intent["reserved"] > 0


def test_allowed_regime_cannot_override_risk_or_kill_switch(gate):
    activate(gate)
    invalid = dict(gate["proposal"], qualified=False)
    result = gate["executor"].execute(invalid)
    assert_unsent(gate, result)
    assert "gates" in result["reason"]
    gate["executor"].stop_entries()
    assert_unsent(gate, gate["executor"].execute(gate["proposal"]))


def test_routing_config_change_during_preflight_prevents_send(gate):
    activate(gate)
    def change_config():
        gate["config"]["version"] = "1.0.1"
        gate["config_path"].write_text(json.dumps(gate["config"]), encoding="utf-8")
    gate["broker"].check_hook = change_config
    result = gate["executor"].execute(gate["proposal"])
    assert_unsent(gate, result)
    assert "configuration changed" in result["reason"]
    assert last_refusal(gate)["phase"] == "BEFORE_SEND"
    assert gate["store"].intents()[0]["state"] == "REJECTED"


def test_closed_bar_correction_during_preflight_prevents_send(gate):
    activate(gate)
    def correct_bar():
        gate["broker"].rows[-2]["tick_volume"] += 1
    gate["broker"].check_hook = correct_bar
    result = gate["executor"].execute(gate["proposal"])
    assert_unsent(gate, result)
    assert "snapshot changed" in result["reason"]
    assert last_refusal(gate)["phase"] == "BEFORE_SEND"


def test_routing_refuses_stale_or_unaligned_context(gate):
    activate(gate)
    gate["broker"].rows.pop()
    result = gate["executor"].execute(gate["proposal"])
    assert_unsent(gate, result)
    assert "closed-bar time" in result["reason"]
    gate["now"][0] += 3600
    proposal = dict(gate["proposal"], expires_at=gate["now"][0] + 500)
    result = gate["executor"].execute(proposal)
    assert_unsent(gate, result)
    assert "stale" in result["reason"]


def test_no_routing_receipt_cannot_bypass_gate_with_prepared_intent(gate):
    activate(gate)
    prepared = gate["risk"].prepare(gate["proposal"], now=gate["now"][0])
    assert prepared["approved"]
    result = gate["executor"]._send(prepared["intent_id"], entry=True)
    assert_unsent(gate, result)
    assert "no regime routing receipt" in result["reason"]


def test_routing_audit_write_failure_never_reserves_or_sends(gate, monkeypatch):
    activate(gate)
    gate["broker"].rows = []
    original = gate["store"].audit
    def failed_audit(event, payload):
        if event == "REGIME_ROUTING_REJECTED":
            raise sqlite3.OperationalError("synthetic audit write failure")
        return original(event, payload)
    monkeypatch.setattr(gate["store"], "audit", failed_audit)
    result = gate["executor"].execute(gate["proposal"])
    assert_unsent(gate, result)
    assert "audit write failure" in result["reason"]
    assert gate["store"].intents() == []


def test_missing_routing_profile_refuses_activation(gate):
    gate["config_path"].unlink()
    with pytest.raises(ValueError, match="routing profile"):
        activate(gate)
    assert gate["executor"].mode == "READ_ONLY"
    assert gate["broker"].sent == []
    assert last_refusal(gate)["phase"] == "ACTIVATION"


def test_routing_opt_in_does_not_authorize_or_waive_manual_approval(gate):
    assert gate["executor"].execute(gate["proposal"])["approved"] is False
    activate(gate, "MANUAL_DEMO")
    assert gate["executor"].execute(gate["proposal"])["approved"] is False
    assert gate["broker"].sent == []
    assert gate["executor"].execute(gate["proposal"], approved=True)["approved"] is True


def test_missing_route_after_entry_does_not_block_protective_close(gate):
    activate(gate)
    entry = gate["executor"].execute(gate["proposal"])
    assert entry["approved"] is True
    gate["config_path"].unlink()
    result = gate["executor"].flatten_owned_positions()
    assert result["ok"] is True, result
    assert gate["broker"].positions() == []
    assert len(gate["broker"].sent) == 2


def test_default_disabled_filter_keeps_legacy_compatibility(gate):
    executor = Executor(gate["broker"], gate["store"], gate["risk"], lambda: gate["now"][0])
    executor.activate("AUTO_DEMO", gate["settings"])
    proposal = dict(gate["proposal"])
    proposal.pop("strategy_id")
    proposal.pop("timeframe")
    gate["broker"].rows = []
    assert executor.execute(proposal)["approved"] is True
    assert executor.status()["regime_routing"]["enabled"] is False
