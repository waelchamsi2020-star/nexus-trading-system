import json
import sqlite3
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from tools.demo_limits import initialize as initialize_limits
from tools.demo_live import (
    MarketDataUnavailable,
    Service,
    current_quote,
    mirror_status,
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
    service.c = {"account_login": 12345678, "timeframe": "M1", "profile": "FAST_SCALP",
        "daily_profit_amount": 98, "daily_loss_amount": 418.98, "max_trade_risk_percent": 2,
        "max_exposure_amount": 100, "volume": .01, "expires_at": time.time()+100, "kill_drawdown_percent": 100}
    service.started = time.time()
    service.limits_revision = 4
    monkeypatch.setattr("tools.demo_live.mirror_status", lambda *_: "WinError 5")
    service.publish()
    assert service.get("published_status")["mode"] == "DEMO_LIVE"
    assert service.get("status_mirror_warning") == "WinError 5"
    assert service.get("halt") is None


def test_existing_position_blocks_other_models_same_direction():
    p = SimpleNamespace(symbol="EURUSD", magic=20261019, type=1)
    assert repeated_opportunity([p], [], 1)
    assert not repeated_opportunity([p], [], 0)


def test_durable_fill_blocks_duplicate_before_broker_snapshot_catches_up():
    assert repeated_opportunity([], [{"symbol": "EURUSD", "type": 1}], 1)
    assert not repeated_opportunity([], [], 1)


def test_different_symbol_or_external_magic_not_conflated():
    assert not repeated_opportunity([
        SimpleNamespace(symbol="EURUSD", magic=741903, type=1),
        SimpleNamespace(symbol="GBPUSD", magic=20261019, type=1)], [], 1)


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
        "max_trade_risk_percent": 2, "kill_drawdown_percent": 10}
    initialize_limits(service.db, service.c)
    service.limits_revision = 0
    account = SimpleNamespace(balance=1000, equity=1000)
    service.guard = lambda: account
    service.desktop_guard = lambda: None
    snapshot = {"equity": 1000, "positions": (), "daily_halt": False,
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
    service.c = {'account_login': 12345678, 'account_server': 'demo',
                 'terminal_path': 'fixture', 'expires_at': time.time() + 300}
    account = SimpleNamespace(login=12345678, server='demo', trade_mode=0,
                              trade_allowed=True, trade_expert=True, currency='USD', equity=100)
    terminal = SimpleNamespace(path='fixture', connected=False, trade_allowed=True, tradeapi_disabled=False)
    service.sdk = SimpleNamespace(account_info=lambda: account, terminal_info=lambda: terminal)
    with pytest.raises(MarketDataUnavailable, match='MT5_CONNECTION_UNAVAILABLE'):
        service.guard()
    terminal.connected = True
    assert service.guard() is account
    terminal.connected = False
    terminal.trade_allowed = False
    with pytest.raises(RuntimeError, match='TERMINAL_ALGORITHMIC_TRADING_DISABLED'):
        service.guard()
    terminal.trade_allowed = True
    account.trade_mode = 2
    with pytest.raises(RuntimeError, match='REAL_ACCOUNT_DETECTED'):
        service.guard()
    account.trade_mode = 0
    account.login = 99
    with pytest.raises(RuntimeError, match='ACCOUNT_OR_TERMINAL_CHANGED'):
        service.guard()
    account.login = 12345678
    service.c['expires_at'] = time.time() - 1
    with pytest.raises(RuntimeError, match='AUTHORIZATION_24H_EXPIRED'):
        service.guard()
