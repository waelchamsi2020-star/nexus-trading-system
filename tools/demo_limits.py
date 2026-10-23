"""User-owned cash limits; atomic revision + audit, without resetting day history."""
import json
import math
import sqlite3
import time

KEYS = ("daily_profit_amount", "daily_loss_amount", "max_exposure_amount",
        "max_trade_risk_percent", "per_trade_profit_amount", "per_trade_loss_amount",
        "kill_drawdown_percent")
OPTIONAL = {"per_trade_profit_amount": 0., "per_trade_loss_amount": 0.,
            "kill_drawdown_percent": 10.}


def validate(values):
    if set(values) != set(KEYS):
        raise ValueError("أدخل جميع الحدود المعروضة فقط")
    result = {}
    for key in KEYS:
        value = values[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("الحدود أرقام وليست نصوصاً")
        if not math.isfinite(value) or value < 0 or (value == 0 and key not in OPTIONAL):
            raise ValueError("كل حد يجب أن يكون رقماً موجباً ومحدداً")
        if key in ("max_trade_risk_percent", "kill_drawdown_percent") and value > 100:
            raise ValueError("نسبة مخاطرة الصفقة لا تتجاوز 100%")
        result[key] = float(value)
    if bool(result["per_trade_profit_amount"]) != bool(result["per_trade_loss_amount"]):
        raise ValueError("حدّد ربح وخسارة الصفقة معاً، أو صفّرهما لاستخدام ATR")
    return result


def initialize(db, config):
    with db:
        db.execute("CREATE TABLE IF NOT EXISTS user_limits "
                   "(id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, "
                   "payload TEXT NOT NULL, updated_at REAL NOT NULL)")
        db.execute("INSERT OR IGNORE INTO user_limits VALUES (1,0,?,?)",
                   (json.dumps(validate({k: config.get(k, OPTIONAL.get(k)) for k in KEYS})), time.time()))


def read(db):
    row = db.execute("SELECT revision,payload,updated_at FROM user_limits WHERE id=1").fetchone()
    if row is None:
        raise ValueError("خدمة التنفيذ لم تهيئ الحدود")
    return {"revision": row[0], "values": validate(json.loads(row[1])), "updated_at": row[2]}


def amend(path, values, expected_revision):
    values = validate(values)
    if type(expected_revision) is not int:
        raise ValueError("إصدار الحدود غير صالح")
    with sqlite3.connect(path, timeout=5) as db:
        db.execute("BEGIN IMMEDIATE")
        old = read(db)
        if old["revision"] != expected_revision:
            raise ValueError("تغيرت الحدود في نافذة أخرى؛ حدّث الصفحة")
        revision = expected_revision + 1
        now = time.time()
        db.execute("UPDATE user_limits SET revision=?,payload=?,updated_at=? WHERE id=1",
                   (revision, json.dumps(values), now))
        db.execute("INSERT INTO audit(at,event,payload) VALUES (?,?,?)",
                   (now, "USER_LIMITS_AMENDED", json.dumps({
                       "revision": revision, "before": old["values"], "after": values,
                       "daily_ledger_reset": False})))
    return {"revision": revision, "values": values, "updated_at": now}
