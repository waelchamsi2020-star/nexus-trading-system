import json
import sqlite3
from types import SimpleNamespace

import pytest

from tools.demo_limits import amend, initialize, read, validate
from tools.demo_live import Service, cash_levels


@pytest.fixture
def journal(tmp_path):
    path = tmp_path / "trades.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE audit(at REAL,event TEXT,payload TEXT)")
        initialize(db, {"daily_profit_amount": 100, "daily_loss_amount": 100,
                            "max_exposure_amount": 100, "max_trade_risk_percent": 2})
    return path


def test_amend_preserves_history_and_audits(journal):
    with sqlite3.connect(journal) as db:
        values = read(db)["values"]
    values.update(daily_loss_amount=418.98, per_trade_profit_amount=1,
                  per_trade_loss_amount=5, kill_drawdown_percent=0)
    assert amend(journal, values, 0)["revision"] == 1
    with sqlite3.connect(journal) as db:
        assert read(db)["values"] == values
        audit = json.loads(db.execute("SELECT payload FROM audit").fetchone()[0])
        assert audit["daily_ledger_reset"] is False


def test_stale_revision_cannot_overwrite(journal):
    with sqlite3.connect(journal) as db:
        values = read(db)["values"]
    amend(journal, values, 0)
    with pytest.raises(ValueError):
        amend(journal, values, 0)


def test_audit_failure_rolls_back_limit_change(journal):
    with sqlite3.connect(journal) as db:
        values = read(db)["values"]
        db.execute("CREATE TRIGGER fail_audit BEFORE INSERT ON audit "
                   "BEGIN SELECT RAISE(ABORT,'disk failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        amend(journal, values, 0)
    with sqlite3.connect(journal) as db:
        assert read(db)["revision"] == 0


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf"), True])
def test_invalid_limits_rejected(journal, value):
    with sqlite3.connect(journal) as db:
        values = read(db)["values"]
    values["daily_loss_amount"] = value
    with pytest.raises((ValueError, TypeError)):
        validate(values)


@pytest.mark.parametrize("side", [0, 1])
def test_cash_targets_reserve_cost_and_round_stop_inward(side):
    price, tick, per_tick, costs = 1.12, .00001, .01, .27
    sl, tp = cash_levels(side, price, tick, per_tick, 5, 1, costs)
    sign = 1 if side == 0 else -1
    assert sign * (price - sl) > 0
    assert abs(sl - price) / tick * per_tick + costs <= 5 + 1e-8
    assert sign * (tp - price) / tick * per_tick - costs >= 1 - 1e-8


def test_executor_reads_live_revision_without_resetting_peak_or_day(journal):
    service = Service.__new__(Service)
    service.db = sqlite3.connect(journal)
    service.db.execute("CREATE TABLE state(key TEXT PRIMARY KEY,value TEXT)")
    service.db.execute("CREATE TABLE deals(ticket INTEGER PRIMARY KEY,payload TEXT)")
    service.db.execute("CREATE TABLE attempts(bar INTEGER,at REAL,model TEXT,status TEXT,request TEXT,result TEXT)")
    service.db.commit()
    service.c = {}
    service.limits_revision = -1
    service.guard = lambda: SimpleNamespace(balance=400, equity=400)
    service.sdk = SimpleNamespace(positions_get=lambda: (), orders_get=lambda: (),
                                 history_deals_get=lambda *_: ())
    service.set("peak_equity", 500)
    values = read(service.db)["values"]
    values.update(kill_drawdown_percent=0, daily_loss_amount=400)
    amend(journal, values, 0)
    snap = service.snapshot()
    assert snap["drawdown_percent"] == 20
    assert service.get("peak_equity") == 500
    assert service.limits_revision == 1 and snap["daily_limit"] == 400
    service.set("daily_halt", [snap["day"], 1])
    assert service.snapshot()["daily_halt"]
    values["daily_loss_amount"] = 450
    amend(journal, values, 1)
    assert not service.snapshot()["daily_halt"]
    assert service.get("peak_equity") == 500
    service.db.close()
