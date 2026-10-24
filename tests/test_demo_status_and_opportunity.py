import json
import sqlite3
import time
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from tools.demo_limits import initialize as initialize_limits
from tools.demo_live import (
    MAX_OPEN_POSITIONS,
    MarketClosed,
    MarketDataUnavailable,
    Service,
    current_quote,
    market_session_closed,
    mirror_status,
    position_capacity_reached,
    repeated_opportunity,
    run_cycle,
)


def test_mirror_retries_sharing_violation(tmp_path, monkeypatch):
    replace = Path.replace
    calls = []

    def locked_twice(path, target):
        calls.append(path)
        if len(calls) < 3:
            raise PermissionError("WinError 5")
        return replace(path, target)

    monkeypatch.setattr(Path, "replace", locked_twice)
    assert mirror_status(tmp_path, {"mode": "DEMO_LIVE"}) is None
    assert len(calls) == 3
    assert json.loads((tmp_path / "status.json").read_text())["mode"] == "DEMO_LIVE"


def test_permanent_mirror_failure_keeps_existing_file_and_cleans_temp(tmp_path, monkeypatch):
    (tmp_path / "status.json").write_text('{"old":true}')
    def denied(*_):
        raise PermissionError("WinError 5")
    monkeypatch.setattr(Path, "replace", denied)
    assert "WinError 5" in mirror_status(tmp_path, {"new": True}, attempts=1)
    assert json.loads((tmp_path / "status.json").read_text()) == {"old": True}
    assert list(tmp_path.glob("*.tmp")) == []


def test_publish_survives_display_failure_with_durable_status(tmp_path, monkeypatch):
    service = Service.__new__(Service)
    service.directory = tmp_path
    service.db = sqlite3.connect(":memory:")
    service.db.executescript("CREATE TABLE state(key TEXT PRIMARY KEY,value TEXT);"
        "CREATE TABLE signals(reason TEXT);CREATE TABLE attempts(status TEXT);"
        "CREATE TABLE audit(at REAL,event TEXT,payload TEXT);"
        "CREATE TABLE hourly(hour INTEGER PRIMARY KEY,payload TEXT);")
    service.c = {"account_login": 1045864, "timeframe": "M1", "profile": "FAST_SCALP",
        "daily_profit_amount": 98, "daily_loss_amount": 418.98, "max_trade_risk_percent": 2,
        "max_exposure_amount": 100, "volume": .01, "expires_at": time.time()+100, "kill_drawdown_percent": 100}
    service.started = time.time()
    service.limits_revision = 4
    monkeypatch.setattr("tools.demo_live.mirror_status", lambda *_: "WinError 5")
    service.publish()
    assert service.get("published_status")["mode"] == "DEMO_LIVE"
    assert service.get("status_mirror_warning") == "WinError 5"
    assert service.get("halt") is None


def test_open_position_older_than_opportunity_window_does_not_block():
    p = SimpleNamespace(symbol="EURUSD", magic=20261019, type=1)
    assert not repeated_opportunity([p], [], 1, now=200,
                                    window_seconds=120)
    assert not repeated_opportunity([p], [], 0)


def test_active_attempt_inside_opportunity_window_blocks():
    attempt = {"opportunity_id": "bar:model", "at": 170, "status": "FILLED",
        "request": {"symbol": "EURUSD", "type": 1}}
    assert repeated_opportunity([], [attempt], 1, now=200, window_seconds=120)
    assert not repeated_opportunity([], [], 1)


def test_different_symbol_or_external_magic_not_conflated():
    assert not repeated_opportunity([], [{"at": 190, "status": "FILLED",
        "request": {"symbol": "GBPUSD", "type": 1}}], 1, now=200)


def test_attempt_outside_opportunity_window_does_not_block():
    attempt = {"at": 79, "status": "FILLED",
        "request": {"symbol": "EURUSD", "type": 1}}
    assert not repeated_opportunity([], [attempt], 1, now=200, window_seconds=120)


def test_position_capacity_counts_pending_and_open_positions():
    assert MAX_OPEN_POSITIONS == 3
    assert position_capacity_reached(tuple(SimpleNamespace(ticket=i) for i in range(3)), (), 3)
    assert position_capacity_reached((), tuple(SimpleNamespace(ticket=i) for i in range(3)), 3)
    assert position_capacity_reached((SimpleNamespace(ticket=1),),
        (SimpleNamespace(ticket=2), SimpleNamespace(ticket=3)), 3)
    assert not position_capacity_reached(tuple(SimpleNamespace(ticket=i) for i in range(2)), (), 3)


@pytest.fixture
def executor(tmp_path, monkeypatch):
    """Exercise the real send pipeline against a fully local SDK double."""
    clock = [1800000010.0]
    monkeypatch.setattr("tools.demo_live.time.time", lambda: clock[0])
    service = Service.__new__(Service)
    service.directory = tmp_path
    service.db = sqlite3.connect(tmp_path / "execution.db")
    service.db.executescript("""
        CREATE TABLE state(key TEXT PRIMARY KEY,value TEXT);
        CREATE TABLE signals(bar INTEGER,model TEXT,direction TEXT,status TEXT,
            reason TEXT,payload TEXT,PRIMARY KEY(bar,model));
        CREATE TABLE attempts(bar INTEGER,at REAL,model TEXT,status TEXT,
            request TEXT,result TEXT,PRIMARY KEY(bar,model));
        CREATE TABLE audit(at REAL,event TEXT,payload TEXT);
        CREATE TABLE deals(ticket INTEGER PRIMARY KEY,payload TEXT);
    """)
    service.c = {"timeframe": "M1", "daily_profit_amount": 100,
        "daily_loss_amount": 100, "max_exposure_amount": 100,
        "max_trade_risk_percent": 2, "kill_drawdown_percent": 10,
        "per_trade_loss_amount": 5, "per_trade_profit_amount": 1}
    initialize_limits(service.db, service.c)
    service.limits_revision = 0
    account = SimpleNamespace(balance=1000, equity=1000)
    service.guard = lambda: account
    service.ensure_market_open = lambda: None
    service.desktop_guard = lambda: None
    snapshot = {"equity": 1000, "positions": (), "orders": (), "daily_halt": False,
        "target_halt": False, "exposure": 0, "daily_loss": 0, "daily_limit": 100}
    service.snapshot = lambda: snapshot
    bar = 1799999940
    rates = np.array([(bar - 60 * (299 - i), 1.1, 1.101, 1.099, 1.1)
                      for i in range(300)],
                     dtype=[("time", "i8"), ("open", "f8"), ("high", "f8"),
                            ("low", "f8"), ("close", "f8")])
    cards = [{"strategy_id": f"model_{i:02}", "status": "WAIT",
              "direction": "BUY"} for i in range(58)]
    cards[0].update(status="READY", coverage="IMPLEMENTED",
        entry={"triggered": True, "zone": [1.09, 1.11]},
        data_time=bar+60, expires_at=bar+120)
    monkeypatch.setattr("tools.demo_live.analyze_all", lambda *_: cards)
    monkeypatch.setattr("tools.demo_live.atr", lambda *_: .0004)
    quote = SimpleNamespace(time=clock[0], bid=1.1, ask=1.1001)
    info = SimpleNamespace(point=.00001, trade_tick_size=.00001, digits=5,
        volume_min=.01, volume_max=10, volume_step=.01, trade_stops_level=0, filling_mode=1)
    sends = []

    def send(request):
        sends.append(request)
        return SimpleNamespace(retcode=10009, _asdict=lambda: {"retcode": 10009, "order": 42})

    service.sdk = SimpleNamespace(TIMEFRAME_M1=1, TRADE_ACTION_DEAL=1,
        ORDER_TIME_GTC=0, ORDER_FILLING_FOK=0, TRADE_RETCODE_DONE=10009,
        copy_rates_from_pos=lambda *_: rates, symbol_info=lambda *_: info,
        symbol_info_tick=lambda *_: quote,
        order_calc_profit=lambda side, symbol, volume, entry, exit_price:
            (1 if side == 0 else -1) * (exit_price-entry) * volume * 100000,
        order_check=lambda *_: SimpleNamespace(retcode=0), order_send=send,
        positions_get=lambda: (), orders_get=lambda: (), history_deals_get=lambda *_: (),
        last_error=lambda: (1, "test timeout"))
    yield service, clock, quote, sends, cards[0]
    service.db.close()


def test_future_quote_cannot_reach_order_send(executor):
    service, clock, quote, sends, _ = executor
    quote.time = clock[0] + 60
    service.analyze_and_send({})
    assert sends == []
    assert service.db.execute("SELECT reason FROM signals WHERE model='model_00'").fetchone()[0] == "INVALID_OR_STALE_QUOTE"


def test_at_position_ceiling_signal_is_rejected(executor):
    service, _, _, sends, _ = executor
    service.snapshot = lambda: {"equity": 1000,
        "positions": tuple(SimpleNamespace(ticket=i) for i in range(3)), "orders": (),
        "daily_halt": False, "target_halt": False, "exposure": 0,
        "daily_loss": 0, "daily_limit": 100}
    service.analyze_and_send({})
    assert sends == []
    assert service.db.execute("SELECT reason FROM signals WHERE model='model_00'").fetchone()[0] == "MAX_OPEN_POSITIONS_REACHED"


def test_two_open_positions_allow_third_and_preserve_12_pip_atr_stop(executor, monkeypatch):
    service, _, _, sends, _ = executor
    service.snapshot = lambda: {"equity": 1000,
        "positions": (SimpleNamespace(ticket=1, symbol="EURUSD", magic=20261019, type=1),
            SimpleNamespace(ticket=2, symbol="GBPUSD", magic=777, type=0)), "orders": (),
        "daily_halt": False, "target_halt": False, "exposure": 0,
        "daily_loss": 0, "daily_limit": 100}
    monkeypatch.setattr("tools.demo_live.atr", lambda *_: .0008)  # 1.5 ATR = 12 pips
    service.analyze_and_send({})
    assert len(sends) == 1
    assert sends[0]["sl"] == pytest.approx(1.0989)  # BUY quote ask=1.1001 minus .0012
    assert sends[0]["sl"] != pytest.approx(1.0996)  # cash-level stop for $5 cap
    payload = json.loads(service.db.execute(
        "SELECT payload FROM audit WHERE event='BROKER_ENTRY_CONFIRMED'").fetchone()[0])
    assert payload["stop_source"] == "ATR"
    assert payload["atr_stop"] == pytest.approx(sends[0]["sl"])
    assert payload["risk_cash"] == pytest.approx(1.47)  # $1.20 stop + $0.20 slip + $0.07 commission


def test_atr_stop_below_broker_minimum_extends_only_one_point_and_rechecks_risk(executor, monkeypatch):
    service, _, _, sends, _ = executor
    service.sdk.symbol_info = lambda *_: SimpleNamespace(point=.00001, trade_tick_size=.00001,
        digits=5, volume_min=.01, volume_max=10, volume_step=.01,
        trade_stops_level=10, filling_mode=1)
    monkeypatch.setattr("tools.demo_live.atr", lambda *_: .00004)  # ATR stop = 6 points
    service.analyze_and_send({})
    assert len(sends) == 1
    # Broker minimum is measured from bid; include spread plus the one-point buffer.
    assert abs(sends[0]["price"] - sends[0]["sl"]) / .00001 == pytest.approx(21)
    assert sends[0]["sl"] == pytest.approx(1.09989)
    payload = json.loads(service.db.execute(
        "SELECT payload FROM audit WHERE event='BROKER_ENTRY_CONFIRMED'").fetchone()[0])
    assert payload["stop_source"] == "ATR"
    assert payload["atr_stop_points"] == pytest.approx(21)
    assert payload["risk_cash"] == pytest.approx(.48)  # $0.21 stop + $0.20 slip + $0.07 commission


def test_broker_minimum_stop_that_exceeds_cash_cap_is_rejected(executor, monkeypatch):
    service, _, _, sends, _ = executor
    service.sdk.symbol_info = lambda *_: SimpleNamespace(point=.00001, trade_tick_size=.00001,
        digits=5, volume_min=.01, volume_max=10, volume_step=.01,
        trade_stops_level=500, filling_mode=1)
    monkeypatch.setattr("tools.demo_live.atr", lambda *_: .00004)
    service.analyze_and_send({})
    assert sends == []
    assert service.db.execute("SELECT reason FROM signals WHERE model='model_00'").fetchone()[0] == "STOP_RISK_EXCEEDS_CAP"


def test_closed_weekend_market_classifies_waiting_without_halt():
    assert market_session_closed(SimpleNamespace(session_deals=0),
        SimpleNamespace(time_msc=1_000, bid=1.1, ask=1.1001),
        now=datetime(2026, 10, 24, 6, 0, tzinfo=UTC))
    service = Service.__new__(Service)
    service.sdk = SimpleNamespace(
        # Closed-session classification takes precedence over stale expert flags.
        account_info=lambda: SimpleNamespace(trade_allowed=True, trade_expert=False),
        terminal_info=lambda: SimpleNamespace(tradeapi_disabled=False, connected=True,
                                             trade_allowed=False),
        symbol_info=lambda *_: SimpleNamespace(session_deals=0, session_buy_orders=0,
                                               session_sell_orders=0),
        symbol_info_tick=lambda *_: SimpleNamespace(time=1, time_msc=1_000, bid=1.1, ask=1.1001),
        last_error=lambda: (0, 'ok'))
    service.c = {"symbol": "EURUSD"}
    service.db = sqlite3.connect(":memory:")
    service.db.execute("CREATE TABLE state(key TEXT PRIMARY KEY,value TEXT)")
    service.get = lambda key: None
    service.set = lambda key, value: None
    service.audit = lambda *_: None
    from collections import deque
    service.guard_snapshots = []
    service._permission_failures = deque(maxlen=3)
    service._open_spreads = deque(maxlen=100)
    service._last_spread_tick_msc = None
    with pytest.raises(MarketClosed, match="MARKET_CLOSED"):
        service.ensure_market_open()
    assert not service.db.execute("SELECT 1 FROM state WHERE key='halt'").fetchone()
    service.db.close()


def test_waiting_market_cycle_does_not_evaluate_or_halt():
    class WaitingService:
        def __init__(self):
            self.values = {}
            self.events = []
            self.evaluated = False

        def desktop_guard(self):
            return None

        def snapshot(self):
            raise MarketClosed("MARKET_CLOSED")

        def analyze_and_send(self, _):
            self.evaluated = True

        def get(self, key):
            return self.values.get(key)

        def set(self, key, value):
            self.values[key] = value

        def audit(self, event, payload):
            self.events.append((event, payload))

        def publish(self, snap=None, error=None):
            return {"data_status": self.values.get("data_status"), "error": error}

    service = WaitingService()
    status = run_cycle(service)
    assert status == {"data_status": "WAITING_MARKET", "error": None}
    assert not service.evaluated
    assert service.values["market_wait_reason"] == "MARKET_CLOSED"
    assert service.events == [("MARKET_CLOSED_WAIT_NO_EVALUATION", {
        "reason": "MARKET_CLOSED", "candidate_evaluation": False, "order_send": False})]


def _guard_service(account_allowed, *, tradeapi_disabled=False, market_open=True,
                   clock=1000., terminal_allowed=True, broken=False):
    from collections import deque
    service = Service.__new__(Service)
    state, events = {}, []
    info = SimpleNamespace(session_deals=3 if market_open else 0,
        session_buy_orders=1, session_sell_orders=1, point=.00001, trade_stops_level=30)
    tick = SimpleNamespace(time=clock, time_msc=clock*1000, bid=1.1, ask=1.1001)
    def symbol_info(*_):
        if broken:
            raise RuntimeError('simulated MT5 retcode 10004')
        return info
    service.sdk = SimpleNamespace(
        account_info=lambda: SimpleNamespace(trade_allowed=account_allowed, trade_expert=True,
             login=1045864, trade_mode=0),
        terminal_info=lambda: SimpleNamespace(tradeapi_disabled=tradeapi_disabled,
             connected=True, trade_allowed=terminal_allowed),
        symbol_info=symbol_info, symbol_info_tick=lambda *_: tick,
        last_error=lambda: (10004, 'simulated call failure'))
    service.c = {'symbol': 'EURUSD', 'account_login': 1045864}
    service.set = lambda key, value: state.__setitem__(key, value)
    service.get = lambda key: state.get(key)
    service.audit = lambda event, payload: events.append((event, payload))
    service.guard_snapshots = []
    service._permission_failures = deque(maxlen=3)
    service._open_spreads = deque([10., 10., 10.], maxlen=100)
    service._last_spread_tick_msc = tick.time_msc
    return service, state, events


def test_closed_market_permission_flapping_never_halts(monkeypatch):
    clock = [1000.]
    monkeypatch.setattr('tools.demo_live.time.time', lambda: clock[0])
    service, _, events = _guard_service(False, market_open=False)
    for flag in (False, True, False, True, False):
        service.sdk.account_info = lambda f=flag: SimpleNamespace(trade_allowed=f,
            trade_expert=True, login=1045864, trade_mode=0)
        with pytest.raises(MarketClosed):
            service.ensure_market_open()
        clock[0] += 10
    assert len(service.guard_snapshots) == 5
    assert all(s['branch'] == 'MARKET_CLOSED' for s in service.guard_snapshots)
    assert not any(event == 'DEMO_PERMISSION_DEBOUNCE_CONFIRMED' for event, _ in events)


def test_open_market_three_spaced_permission_failures_halt(monkeypatch):
    clock = [1000.]
    monkeypatch.setattr('tools.demo_live.time.time', lambda: clock[0])
    service, _, events = _guard_service(False)
    for index in range(3):
        service.sdk.symbol_info_tick = lambda *_, c=clock[0]: SimpleNamespace(
            time=c, time_msc=c*1000, bid=1.1, ask=1.1001)
        if index < 2:
            with pytest.raises(MarketDataUnavailable, match='PERMISSION_CONFIRMATION_PENDING'):
                service.ensure_market_open()
        else:
            with pytest.raises(RuntimeError, match='DEMO_ACCOUNT_TRADING_PERMISSION_DISABLED'):
                service.ensure_market_open()
        clock[0] += 10
    confirmed = [p for e, p in events if e == 'DEMO_PERMISSION_DEBOUNCE_CONFIRMED']
    assert len(confirmed) == 1 and len(confirmed[0]['snapshots']) == 3
    assert all(s['branch'] == 'PERMISSION_FAIL' for s in confirmed[0]['snapshots'])


def test_open_market_one_permission_failure_then_success_does_not_halt(monkeypatch):
    clock = [1000.]
    monkeypatch.setattr('tools.demo_live.time.time', lambda: clock[0])
    service, _, events = _guard_service(False)
    with pytest.raises(MarketDataUnavailable, match='PERMISSION_CONFIRMATION_PENDING'):
        service.ensure_market_open()
    clock[0] += 10
    service.sdk.account_info = lambda: SimpleNamespace(trade_allowed=True, trade_expert=True,
        login=1045864, trade_mode=0)
    service.sdk.symbol_info_tick = lambda *_: SimpleNamespace(time=clock[0],
        time_msc=clock[0]*1000, bid=1.1, ask=1.1001)
    service.ensure_market_open()
    assert not service._permission_failures
    assert not any(e == 'DEMO_PERMISSION_DEBOUNCE_CONFIRMED' for e, _ in events)


def test_mt5_call_failure_is_not_permission_failure(monkeypatch):
    monkeypatch.setattr('tools.demo_live.time.time', lambda: 1000.)
    service, _, events = _guard_service(False, broken=True)
    with pytest.raises(MarketDataUnavailable, match='MT5_CALL_FAILED'):
        service.ensure_market_open()
    snapshots = [p for e, p in events if e == 'EXECUTION_GUARD_SNAPSHOT']
    assert snapshots[-1]['branch'] == 'MT5_CALL_FAILED'
    assert snapshots[-1]['retcode'][0] == 10004
    assert not any(e == 'DEMO_PERMISSION_DEBOUNCE_CONFIRMED' for e, _ in events)


def test_guard_snapshot_is_audited_on_success_and_failure(monkeypatch):
    monkeypatch.setattr('tools.demo_live.time.time', lambda: 1000.)
    service, _, events = _guard_service(True)
    service.ensure_market_open()
    service._open_spreads.clear()
    service._last_spread_tick_msc = None
    service.sdk.account_info = lambda: SimpleNamespace(trade_allowed=False,
        trade_expert=True, login=1045864, trade_mode=0)
    with pytest.raises(MarketDataUnavailable, match='PERMISSION_CONFIRMATION_PENDING'):
        service.ensure_market_open()
    snapshots = [p for e, p in events if e == 'EXECUTION_GUARD_SNAPSHOT']
    assert [s['branch'] for s in snapshots] == ['PERMISSION_OK', 'PERMISSION_FAIL']
    assert snapshots[0]['tradeapi_disabled'] is False
    assert len(service.guard_snapshots) == 2


def test_terminal_trade_allowed_false_is_not_guard_failure(monkeypatch):
    from collections import deque
    service = Service.__new__(Service)
    account = SimpleNamespace(trade_allowed=True, trade_expert=True, login=1045864, trade_mode=0)
    terminal = SimpleNamespace(tradeapi_disabled=False, connected=True, trade_allowed=False)
    service.sdk = SimpleNamespace(account_info=lambda: account,
        terminal_info=lambda: terminal,
        symbol_info=lambda *_: SimpleNamespace(session_deals=5, session_buy_orders=1,
            session_sell_orders=1, point=.00001, trade_stops_level=30),
        symbol_info_tick=lambda *_: SimpleNamespace(time=time.time(), time_msc=time.time()*1000,
            bid=1.1, ask=1.1001))
    service.c = {"symbol": "EURUSD", "account_login": 1045864}
    service.set = lambda *_: None
    service.get = lambda *_: None
    service.audit = lambda *_: None
    service.guard_snapshots = []
    service._permission_failures = deque(maxlen=3)
    service._open_spreads = deque([10., 10., 10.], maxlen=100)
    service._last_spread_tick_msc = None
    service.ensure_market_open()
    assert service.guard_snapshots[-1]['branch'] == 'PERMISSION_OK'


def test_fresh_open_market_quote_with_wide_spread_is_not_rejected_by_spread_gate():
    from collections import deque
    service = Service.__new__(Service)
    service.sdk = SimpleNamespace(
        account_info=lambda: SimpleNamespace(trade_allowed=True, trade_expert=True,
            login=1045864, trade_mode=0),
        terminal_info=lambda: SimpleNamespace(tradeapi_disabled=False, connected=True,
                                             trade_allowed=True),
        symbol_info=lambda *_: SimpleNamespace(session_deals=5, session_buy_orders=1,
            session_sell_orders=1, point=.00001, trade_stops_level=30),
        symbol_info_tick=lambda *_: SimpleNamespace(time=time.time(), time_msc=time.time()*1000,
                                                    bid=1.1, ask=1.1004))
    service.c = {"symbol": "EURUSD", "account_login": 1045864}
    state = {}
    events = []
    service.set = lambda key, value: state.__setitem__(key, value)
    service.get = lambda key: state.get(key)
    service.audit = lambda event, payload: events.append((event, payload))
    service.guard_snapshots = []
    service._permission_failures = deque(maxlen=3)
    service._open_spreads = deque([10., 10., 10.], maxlen=100)
    service._last_spread_tick_msc = None
    service.ensure_market_open()
    assert state["market_state"] == "MARKET_OPEN"
    assert service.guard_snapshots[-1]["branch"] == "PERMISSION_OK"
    assert not any(e == "MARKET_OPEN_SPREAD_NOT_NORMAL_NO_EVALUATION" for e, _ in events)
    assert events[-1] == ("MARKET_OPEN_FIRST_FRESH_QUOTE", {
        "quote_age_seconds": pytest.approx(0, abs=1),
        "spread_filter_enforced": False,
        "candidate_evaluation_follows": True})


def test_demo_authorization_renews_at_most_once_with_demo_scope(tmp_path, monkeypatch):
    clock = [5000.0]
    monkeypatch.setattr("tools.demo_live.time.time", lambda: clock[0])
    path = tmp_path / "config.json"
    config = {"account_login": 1045864, "account_server": "Capital.ComMena-Demo",
        "account_trade_mode": 0, "demo_only": True, "api_keys_enabled": False,
        "live_endpoint_enabled": False, "authorized_at": 5500-86400,
        "expires_at": 5500.0, "authorization_duration_seconds": 86400,
        "authorization_id": "old", "source": "test"}
    path.write_text(json.dumps(config), encoding="utf-8")
    service = Service.__new__(Service)
    service.path = path
    service.c = config
    service.config_bytes = path.read_bytes()
    service.db = sqlite3.connect(":memory:")
    service.db.executescript("CREATE TABLE state(key TEXT PRIMARY KEY,value TEXT);"
        "CREATE TABLE audit(id INTEGER PRIMARY KEY,at REAL,event TEXT,payload TEXT);")
    service.sdk = SimpleNamespace(
        account_info=lambda: SimpleNamespace(trade_mode=0, login=1045864,
            server="Capital.ComMena-Demo", trade_allowed=True),
        terminal_info=lambda: SimpleNamespace(tradeapi_disabled=False, connected=True))
    assert service.renew_demo_authorization_if_due()
    assert service.c["expires_at"] == pytest.approx(5500+86400)
    assert service.c["authorization_id"] != "old"
    assert service.c["authorization_guard_floor"] == pytest.approx(5000)
    desktop_db = tmp_path / "desktop-audit.sqlite3"
    with sqlite3.connect(desktop_db) as desktop:
        desktop.execute("CREATE TABLE audit(sequence INTEGER PRIMARY KEY,at REAL,event TEXT)")
        desktop.execute("INSERT INTO audit VALUES (1,4990,'AUTHORIZATION_REVOKED')")
        desktop.execute("INSERT INTO audit VALUES (2,5001,'ENTRIES_STOPPED')")
    service.c["desktop_audit_db"] = str(desktop_db)
    with pytest.raises(RuntimeError, match="USER_DESKTOP_STOP_ENTRIES"):
        service.desktop_guard()
    clock[0] = service.c["expires_at"] - 500
    with pytest.raises(RuntimeError, match="AUTHORIZATION_RENEWAL_LIMIT_REACHED"):
        service.renew_demo_authorization_if_due()
    assert service.get("demo_authorization_renewals") == 1
    assert service.get("halt") == "AUTHORIZATION_RENEWAL_LIMIT_REACHED"
    assert service.db.execute("SELECT COUNT(*) FROM audit WHERE event='DEMO_AUTHORIZATION_RENEWED'").fetchone()[0] == 1
    assert service.db.execute("SELECT COUNT(*) FROM audit WHERE event='DEMO_AUTO_RENEWAL_LIMIT_REACHED'").fetchone()[0] == 1
    assert json.loads(path.read_text(encoding="utf-8"))["demo_only"] is True
    service.db.close()


def test_atr_stop_over_cash_cap_rejects_without_send(executor, monkeypatch):
    service, _, _, sends, _ = executor
    monkeypatch.setattr("tools.demo_live.atr", lambda *_: .004)  # 600 pip stop
    service.analyze_and_send({})
    assert sends == []
    assert service.db.execute("SELECT reason FROM signals WHERE model='model_00'").fetchone()[0] == "STOP_RISK_EXCEEDS_CAP"


def test_entry_zone_rejection_writes_price_atr_spread_and_trend_measurement(executor, capsys):
    service, _, _, sends, card = executor
    card["entry"]["price"] = 1.205
    card["entry"]["zone"] = [1.2, 1.21]
    service.analyze_and_send({})
    assert sends == []
    assert service.db.execute("SELECT reason FROM signals WHERE model='model_00'").fetchone()[0] == "QUOTE_OUTSIDE_MODEL_ENTRY_ZONE"
    payload = json.loads(service.db.execute(
        "SELECT payload FROM audit WHERE event='ENTRY_ZONE_REJECTION_MEASURED'").fetchone()[0])
    assert payload["direction"] == "BUY"
    assert payload["requested_entry_price"] == 1.205
    assert payload["current_price"] == 1.1001
    assert payload["atr_m1_price"] == pytest.approx(.0004)
    assert payload["spread_points"] == pytest.approx(10)
    assert payload["distance_greater_than_atr_plus_spread"] is True
    assert payload["m1_trend_20bar"] == "FLAT"
    assert "ENTRY_ZONE_REJECTION_MEASURED" in capsys.readouterr().out


def test_overlap_rejection_logs_existing_trade_id_and_age(executor, capsys):
    service, clock, _, sends, _ = executor
    service.db.execute("INSERT INTO attempts VALUES (1,?,?,?,?,?)",
        (clock[0]-35, "prior_model", "FILLED",
         json.dumps({"symbol": "EURUSD", "type": 0}), None))
    service.db.commit()
    service.snapshot = lambda: {"equity": 1000,
        "positions": (SimpleNamespace(ticket=98765, identifier=98765, symbol="EURUSD",
            magic=20261019, type=0, time=clock[0]-35),), "orders": (),
        "daily_halt": False, "target_halt": False, "exposure": 0,
        "daily_loss": 0, "daily_limit": 100}
    service.analyze_and_send({})
    assert sends == []
    payload = json.loads(service.db.execute(
        "SELECT payload FROM audit WHERE event='OPPORTUNITY_OVERLAP_MEASURED'").fetchone()[0])
    assert payload["window_seconds"] == 120
    assert payload["overlaps"] == [{"opportunity_id": "1:prior_model",
        "age_seconds": 35.0, "overlap_type": "ACTIVE_ATTEMPT_IN_WINDOW",
        "outcome": "FILLED"}]
    assert "OPPORTUNITY_OVERLAP_MEASURED" in capsys.readouterr().out


def test_old_open_position_without_active_attempt_does_not_create_overlap(executor):
    service, clock, _, sends, _ = executor
    service.snapshot = lambda: {"equity": 1000,
        "positions": (SimpleNamespace(ticket=98765, identifier=98765, symbol="EURUSD",
            magic=20261019, type=0, time=clock[0]-3600),), "orders": (),
        "daily_halt": False, "target_halt": False, "exposure": 0,
        "daily_loss": 0, "daily_limit": 100}
    service.analyze_and_send({})
    assert len(sends) == 1
    assert service.db.execute("SELECT reason FROM signals WHERE model='model_00'").fetchone()[0] != "OVERLAPPING_OPPORTUNITY"
    assert service.db.execute("SELECT COUNT(*) FROM audit WHERE event='OPPORTUNITY_OVERLAP_MEASURED'").fetchone()[0] == 0


def test_future_quote_cannot_understate_existing_position_exposure(executor):
    service, clock, quote, _, _ = executor
    quote.time = clock[0] + 60
    service.sdk.positions_get = lambda: (SimpleNamespace(symbol="EURUSD", sl=1.09,
        type=0, volume=.01),)
    with pytest.raises(RuntimeError, match="POSITION_QUOTE_UNAVAILABLE"):
        Service.snapshot(service)


def test_signal_expiring_during_order_check_cannot_reach_order_send(executor):
    service, clock, _, sends, card = executor

    def slow_check(_):
        clock[0] = card["expires_at"]
        return SimpleNamespace(retcode=0)

    service.sdk.order_check = slow_check
    service.analyze_and_send({})
    assert sends == []
    assert service.db.execute("SELECT status FROM attempts").fetchone()[0] == "CANCELLED_BEFORE_SEND"
    assert service.db.execute("SELECT reason FROM signals WHERE model='model_00'").fetchone()[0] == "EXPIRED_SIGNAL_BEFORE_SEND"


def test_reservation_and_audit_commit_before_send_or_neither(executor):
    service, _, _, sends, _ = executor
    service.db.execute("CREATE TRIGGER fail_reservation_audit BEFORE INSERT ON audit "
        "WHEN NEW.event='SEND_INTENT_RESERVED' BEGIN SELECT RAISE(ABORT,'audit unavailable'); END")
    with pytest.raises(sqlite3.IntegrityError, match="audit unavailable"):
        service.analyze_and_send({})
    assert sends == []
    assert service.db.execute("SELECT COUNT(*) FROM attempts").fetchone()[0] == 0


@pytest.mark.parametrize("direction", ["BUY", "SELL"])
def test_confirmed_send_is_not_repeated_on_same_bar(executor, direction):
    service, _, _, sends, card = executor
    card["direction"] = direction
    service.analyze_and_send({})
    service.analyze_and_send({})
    assert len(sends) == 1
    assert service.db.execute("SELECT status FROM attempts").fetchone()[0] == "FILLED"


def test_cancelled_reservation_and_rejection_audit_are_atomic(executor):
    service, _, _, sends, _ = executor
    service.db.execute("INSERT INTO attempts VALUES (1,0,'m','SENDING','{}',NULL)")
    service.db.execute("INSERT INTO signals VALUES (1,'m','BUY','READY','CANDIDATE','{}')")
    service.db.commit()
    service.db.execute("CREATE TRIGGER fail_rejection_audit BEFORE INSERT ON audit "
        "WHEN NEW.event='SIGNAL_REJECTED' BEGIN SELECT RAISE(ABORT,'audit unavailable'); END")
    with pytest.raises(sqlite3.IntegrityError, match="audit unavailable"):
        service.cancel_reserved(1, "m", "USER_ENTRIES_PAUSED")
    assert sends == []
    assert service.db.execute("SELECT status FROM attempts").fetchone()[0] == "SENDING"
    assert service.db.execute("SELECT reason FROM signals").fetchone()[0] == "CANDIDATE"


@pytest.mark.parametrize("quote", [None, SimpleNamespace(time=100),
    SimpleNamespace(time=float("nan"), bid=1, ask=2),
    SimpleNamespace(time=100, bid=float("nan"), ask=2),
    SimpleNamespace(time=100, bid=0, ask=2),
    SimpleNamespace(time=100, bid=2, ask=1),
    SimpleNamespace(time=80, bid=1, ask=2)])
def test_invalid_broker_quotes_are_not_executable(quote):
    assert not current_quote(quote, 100, 15)


def test_fresh_millisecond_quote_allows_subsecond_broker_clock_skew():
    quote = SimpleNamespace(time=100, time_msc=100500, bid=1, ask=2)
    assert current_quote(quote, 100, 15)
    too_far_future = SimpleNamespace(time=102, time_msc=102000, bid=1, ask=2)
    assert not current_quote(too_far_future, 100, 15)


def test_quote_expiring_during_preflight_is_cancelled(executor):
    service, clock, _, sends, _ = executor

    def delayed_check(_):
        clock[0] += 16
        return SimpleNamespace(retcode=0)

    service.sdk.order_check = delayed_check
    service.analyze_and_send({})
    assert sends == []
    assert service.db.execute("SELECT status FROM attempts").fetchone()[0] == "CANCELLED_BEFORE_SEND"
    assert service.db.execute("SELECT reason FROM signals WHERE model='model_00'").fetchone()[0] == "QUOTE_EXPIRED_DURING_PREFLIGHT"


@pytest.mark.parametrize("reason", ["USER_ENTRIES_PAUSED", "LIMITS_CHANGED_BEFORE_SEND"])
def test_control_amendment_during_preflight_cancels_before_rpc(executor, reason):
    service, _, _, sends, _ = executor

    def amended_check(_):
        if reason == "USER_ENTRIES_PAUSED":
            service.set("user_paused", True)
        else:
            with service.db:
                service.db.execute("UPDATE user_limits SET revision=revision+1")
        return SimpleNamespace(retcode=0)

    service.sdk.order_check = amended_check
    service.analyze_and_send({})
    assert sends == []
    assert service.db.execute("SELECT status FROM attempts").fetchone()[0] == "CANCELLED_BEFORE_SEND"
    audit = json.loads(service.db.execute("SELECT payload FROM audit WHERE event='SIGNAL_REJECTED'").fetchone()[0])
    assert audit["reason"] == reason and audit["rpc_sent"] is False


def test_guard_failure_before_rpc_preserves_definite_local_cancellation(executor):
    service, _, _, sends, _ = executor
    guards = []

    def guard():
        guards.append(1)
        if len(guards) == 2:
            raise RuntimeError("DEMO_CONNECTION_OR_PERMISSION_LOST")

    service.guard = guard
    with pytest.raises(RuntimeError, match="DEMO_CONNECTION_OR_PERMISSION_LOST"):
        service.analyze_and_send({})
    assert sends == []
    assert service.db.execute("SELECT status FROM attempts").fetchone()[0] == "CANCELLED_BEFORE_SEND"


def test_ambiguous_broker_response_is_never_retried(executor):
    service, _, _, sends, _ = executor

    def ambiguous(request):
        sends.append(request)

    service.sdk.order_send = ambiguous
    with pytest.raises(RuntimeError, match="BROKER_RESULT_NOT_CONFIRMED_NO_RETRY"):
        service.analyze_and_send({})
    service.analyze_and_send({})
    assert len(sends) == 1
    assert service.db.execute("SELECT status FROM attempts").fetchone()[0] == "AMBIGUOUS"


@pytest.mark.parametrize("reason", ["POSITION_QUOTE_UNAVAILABLE", "CLOSED_M1_HISTORY_UNAVAILABLE"])
def test_missing_market_data_waits_without_send_and_recovers(executor, reason):
    service, _, quote, sends, _ = executor
    old_snapshot = service.snapshot
    old_rates = service.sdk.copy_rates_from_pos
    service.publish = lambda snap=None, error=None: {"mode": "READ_ONLY" if error else "DEMO_LIVE",
        "error": error, "data_status": service.get("data_status")}
    if reason == "POSITION_QUOTE_UNAVAILABLE":
        # Exercise the actual existing-position exposure quote guard.
        service.snapshot = lambda: Service.snapshot(service)
        service.sdk.positions_get = lambda: (SimpleNamespace(symbol="EURUSD", sl=1.09,
            type=0, volume=.01),)
        quote.time -= 7604
    else:
        service.sdk.copy_rates_from_pos = lambda *_: None
    waiting = run_cycle(service)
    assert waiting == {"mode": "READ_ONLY", "error": reason, "data_status": "WAITING_FOR_MARKET_DATA"}
    assert sends == [] and service.get("halt") is None
    run_cycle(service)
    assert service.db.execute("SELECT COUNT(*) FROM audit WHERE event='MARKET_DATA_WAIT_NO_SEND'").fetchone()[0] == 1
    service.snapshot = old_snapshot
    service.sdk.copy_rates_from_pos = old_rates
    quote.time = 1800000010.0
    recovered = run_cycle(service)
    assert recovered["mode"] == "DEMO_LIVE" and recovered["error"] is None
    assert len(sends) == 1 and service.get("halt") is None
    assert service.get("market_data_wait_reason") is None


@pytest.mark.parametrize("reason", ["REAL_ACCOUNT_DETECTED", "USER_KILL_SWITCH",
    "AUTHORIZATION_24H_EXPIRED", "KILL_DRAWDOWN_LIMIT",
    "BROKER_RESULT_NOT_CONFIRMED_NO_RETRY", "BROKER_SNAPSHOT_INCOMPLETE"])
def test_safety_halts_are_never_treated_as_market_data_wait(executor, reason):
    service, _, _, sends, _ = executor

    def safety_halt():
        raise RuntimeError(reason)

    service.snapshot = safety_halt
    with pytest.raises(RuntimeError, match=reason):
        run_cycle(service)
    assert sends == [] and service.get("market_data_wait_reason") is None


def test_missing_history_has_only_transient_market_data_type(executor):
    service, _, _, sends, _ = executor
    service.sdk.copy_rates_from_pos = lambda *_: None
    with pytest.raises(MarketDataUnavailable, match="CLOSED_M1_HISTORY_UNAVAILABLE"):
        service.analyze_and_send({})
    assert sends == []


def test_connection_wait_never_masks_identity_permission_or_expiry(tmp_path):
    service = Service.__new__(Service)
    service.directory = tmp_path
    service.path = tmp_path / 'config.json'
    service.config_bytes = b'{}'
    service.path.write_bytes(service.config_bytes)
    service.c = {'account_login': 1045864, 'account_server': 'demo',
                 'terminal_path': 'fixture', 'expires_at': time.time() + 300}
    account = SimpleNamespace(login=1045864, server='demo', trade_mode=0,
                              trade_allowed=True, trade_expert=True, currency='USD', equity=100)
    terminal = SimpleNamespace(path='fixture', connected=False, trade_allowed=True, tradeapi_disabled=False)
    service.sdk = SimpleNamespace(account_info=lambda: account, terminal_info=lambda: terminal)
    with pytest.raises(MarketDataUnavailable, match='MT5_CONNECTION_UNAVAILABLE'):
        service.guard()
    terminal.connected = True
    assert service.guard() is account
    terminal.connected = False
    terminal.trade_allowed = False
    with pytest.raises(MarketDataUnavailable, match='MT5_CONNECTION_UNAVAILABLE'):
        service.guard()
    terminal.trade_allowed = True
    account.trade_mode = 2
    with pytest.raises(RuntimeError, match='REAL_ACCOUNT_DETECTED'):
        service.guard()
    account.trade_mode = 0
    account.login = 99
    with pytest.raises(RuntimeError, match='ACCOUNT_OR_TERMINAL_CHANGED'):
        service.guard()
    account.login = 1045864
    terminal.connected = True
    service.c['expires_at'] = time.time() - 1
    assert service.guard() is account


def test_expired_authorization_waits_after_market_classification(monkeypatch):
    service = Service.__new__(Service)
    service.c = {'expires_at': 10.0}
    service.db = sqlite3.connect(':memory:')
    service.db.execute('CREATE TABLE state(key TEXT PRIMARY KEY,value TEXT)')
    service.limits_revision = 0
    service.ensure_market_open = lambda: None
    service.set = lambda key, value: service.db.execute(
        'INSERT OR REPLACE INTO state VALUES (?,?)', (key, json.dumps(value)))
    monkeypatch.setattr('tools.demo_live.time.time', lambda: 11.0)
    monkeypatch.setattr('tools.demo_live.read_limits', lambda *_: {'revision': 0, 'values': {}})
    with pytest.raises(MarketDataUnavailable, match='WAITING_AUTHORIZATION'):
        service.snapshot()
    assert json.loads(service.db.execute(
        "SELECT value FROM state WHERE key='market_state'").fetchone()[0]) == 'WAITING_AUTHORIZATION'
    service.db.close()
