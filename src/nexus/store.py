"""Durable daily limits, audit trail and atomic execution intents (stdlib only)."""
from __future__ import annotations

import json
import math
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path

ACTIVE_STATES = ("PREPARED", "SENDING", "ACCEPTED", "PARTIAL", "FILLED", "UNKNOWN")
UNCERTAIN_STATES = ("SENDING", "UNKNOWN")


def utc_day(now=None):
    return time.strftime("%Y-%m-%d", time.gmtime(time.time() if now is None else now))


def account_key(account):
    """An authorization is bound to the broker account AND terminal installation."""
    for field in ("login", "server", "platform_id"):
        if account.get(field) in (None, ""):
            raise ValueError("Account identity is incomplete: " + field)
    return json.dumps([str(account["login"]), str(account["server"]), str(account["platform_id"])], separators=(",", ":"))


def encode(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def blocks_send(intent):
    return (intent["state"] in UNCERTAIN_STATES or
            (intent["state"] in ACTIVE_STATES and intent["state"] != "PREPARED" and
             (intent["kind"] == "MANAGEMENT" or not intent["payload"].get("confirmed", False))))


class Store:
    def __init__(self, path):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.path, timeout=15, check_same_thread=False, isolation_level=None)
        # Vulture review: sqlite3.Connection.row_factory supplies named-row access used throughout Store.
        self.db.row_factory = sqlite3.Row
        try:
            check = self.db.execute("PRAGMA quick_check(1)").fetchone()
            if not check or check[0] != "ok":
                raise sqlite3.DatabaseError("Local ledger integrity check failed; preserve the original database for recovery")
        except BaseException:
            self.db.close()
            raise
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS days(
                account_key TEXT NOT NULL, day TEXT NOT NULL, risk_amount REAL NOT NULL,
                target_amount REAL NOT NULL, equity_start REAL NOT NULL,
                created REAL NOT NULL, PRIMARY KEY(account_key,day));
            CREATE TABLE IF NOT EXISTS intents(
                id TEXT PRIMARY KEY, account_key TEXT NOT NULL, day TEXT NOT NULL,
                kind TEXT NOT NULL, state TEXT NOT NULL, reserved REAL NOT NULL,
                buckets TEXT NOT NULL, payload TEXT NOT NULL, created REAL NOT NULL,
                updated REAL NOT NULL);
            CREATE INDEX IF NOT EXISTS intents_account ON intents(account_key,state);
            CREATE TABLE IF NOT EXISTS audit(
                sequence INTEGER PRIMARY KEY AUTOINCREMENT, at REAL NOT NULL,
                event TEXT NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS day_halts(
                account_key TEXT NOT NULL, day TEXT NOT NULL, reason TEXT NOT NULL,
                at REAL NOT NULL, PRIMARY KEY(account_key,day));
        """)

    @contextmanager
    def transaction(self):
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                yield self.db
            except BaseException:
                self.db.rollback()
                raise
            else:
                self.db.commit()

    def close(self):
        with self.lock:
            self.db.close()

    def audit(self, event, payload):
        with self.lock:
            self.db.execute("INSERT INTO audit(at,event,payload) VALUES(?,?,?)", (time.time(), event, encode(payload)))

    def recent_audit(self, limit=100):
        with self.lock:
            rows = self.db.execute("SELECT * FROM audit ORDER BY sequence DESC LIMIT ?", (max(1, min(int(limit), 1000)),)).fetchall()
        return [{**dict(r), "payload": json.loads(r["payload"])} for r in rows]

    def get_day(self, account_key, now=None):
        with self.lock:
            row = self.db.execute("SELECT * FROM days WHERE account_key=? AND day=?", (account_key, utc_day(now))).fetchone()
        return dict(row) if row else None

    def ensure_day(self, account_key, risk_amount, target_amount, equity, now=None):
        now = time.time() if now is None else now
        if any(not math.isfinite(float(v)) or float(v) <= 0 for v in (risk_amount, target_amount, equity)):
            raise ValueError("Daily risk, target and equity must be positive finite amounts")
        with self.transaction() as db:
            db.execute("INSERT OR IGNORE INTO days VALUES(?,?,?,?,?,?)", (account_key, utc_day(now), risk_amount, target_amount, equity, now))
            row = db.execute("SELECT * FROM days WHERE account_key=? AND day=?", (account_key, utc_day(now))).fetchone()
        # Re-activation cannot reset or expand the stored day's limits.
        return dict(row)

    def halt_day(self, account_key, reason, now=None):
        now = time.time() if now is None else now
        with self.transaction() as db:
            db.execute("INSERT OR IGNORE INTO day_halts VALUES(?,?,?,?)", (account_key, utc_day(now), str(reason), now))

    def amend_day_limits(self, key, risk_amount, target_amount, now=None, *, allow_increase=False):
        """Explicit audited amendment, never resets ledger or a stopped day."""
        now=time.time() if now is None else now
        if any(not math.isfinite(float(v)) or float(v)<=0 for v in (risk_amount,target_amount)):
            raise ValueError("Daily amounts must be positive and finite")
        with self.transaction() as db:
            row=db.execute("SELECT * FROM days WHERE account_key=? AND day=?",(key,utc_day(now))).fetchone()
            if not row:raise ValueError("No daily limits to amend")
            if risk_amount>row["risk_amount"] and allow_increase is not True:raise ValueError("Daily risk may only be tightened without an explicit increase authorization")
            if db.execute("SELECT 1 FROM day_halts WHERE account_key=? AND day=?",(key,utc_day(now))).fetchone():
                raise ValueError("Stopped daily policy cannot be reset by amendment")
            db.execute("UPDATE days SET risk_amount=?,target_amount=? WHERE account_key=? AND day=?",(risk_amount,target_amount,key,utc_day(now)))
            db.execute("INSERT INTO audit(at,event,payload) VALUES(?,?,?)",(now,"DAILY_LIMITS_AMENDED",encode({"account_key":key,"before":dict(row),"risk_amount":risk_amount,"target_amount":target_amount,"explicit_request":True,"increase_authorized":allow_increase is True})))
        return self.get_day(key,now)

    def day_halt(self, account_key, now=None):
        with self.lock:
            row = self.db.execute("SELECT * FROM day_halts WHERE account_key=? AND day=?", (account_key, utc_day(now))).fetchone()
        return dict(row) if row else None

    @staticmethod
    def _intent(row):
        if row is None:
            return None
        result = dict(row)
        result["buckets"] = json.loads(result["buckets"])
        result["payload"] = json.loads(result["payload"])
        return result

    def intent(self, intent_id):
        with self.lock:
            row = self.db.execute("SELECT * FROM intents WHERE id=?", (intent_id,)).fetchone()
        return self._intent(row)

    def intents(self, account_key=None):
        with self.lock:
            if account_key is None:
                rows = self.db.execute("SELECT * FROM intents ORDER BY created").fetchall()
            else:
                rows = self.db.execute("SELECT * FROM intents WHERE account_key=? ORDER BY created", (account_key,)).fetchall()
        return [self._intent(r) for r in rows]

    def reserve(self, intent_id, key, amount, payload, buckets, available, bucket_limits=None, now=None):
        """Serialize budget checks across threads AND independent app processes.

        available excludes broker-book exposure and realized losses, but includes
        funds potentially reserved by other intents; those are deducted here.
        All prior-day live reservations continue to consume today's budget.
        """
        now = time.time() if now is None else now
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("Invalid risk reservation")
        bucket_limits = bucket_limits or {}
        if not math.isfinite(float(available)) or available < 0 or any(not math.isfinite(float(v)) or v < 0 for v in bucket_limits.values()):
            raise ValueError("Invalid available risk or factor cap")
        with self.transaction() as db:
            existing = db.execute("SELECT * FROM intents WHERE id=?", (intent_id,)).fetchone()
            if existing:
                return {"approved": False, "reason": "DUPLICATE_INTENT", "intent": self._intent(existing)}
            if db.execute("SELECT 1 FROM day_halts WHERE account_key=? AND day=?", (key, utc_day(now))).fetchone():
                return {"approved": False, "reason": "DAILY_POLICY_HALTED"}
            # One ambiguous broker response blocks every entry, even through a
            # second independently initialized Store/Executor instance.
            pending = db.execute("SELECT * FROM intents WHERE account_key=? AND state IN (?,?,?,?,?,?)", (key, *ACTIVE_STATES)).fetchall()
            if any(blocks_send(self._intent(r)) for r in pending):
                return {"approved": False, "reason": "UNRESOLVED_BROKER_RESULT"}
            rows = db.execute("SELECT reserved,buckets FROM intents WHERE account_key=? AND state IN (?,?,?,?,?,?)", (key, *ACTIVE_STATES)).fetchall()
            used = sum(float(r["reserved"]) for r in rows)
            if amount + used > available + 1e-8:
                return {"approved": False, "reason": "DAILY_BUDGET_RESERVED"}
            for bucket in buckets:
                used_bucket = sum(float(r["reserved"]) for r in rows if bucket in json.loads(r["buckets"]))
                if used_bucket + amount > bucket_limits.get(bucket, available) + 1e-8:
                    return {"approved": False, "reason": "CORRELATION_BUCKET_CAP:" + bucket}
            db.execute("INSERT INTO intents VALUES(?,?,?,?,?,?,?,?,?,?)", (intent_id, key, utc_day(now), "ENTRY", "PREPARED", amount, encode(buckets), encode(payload), now, now))
            db.execute("INSERT INTO audit(at,event,payload) VALUES(?,?,?)",
                       (now, "RISK_RESERVED", encode({"intent_id": intent_id, "risk": amount})))
        return {"approved": True, "intent_id": intent_id}

    def management_intent(self, intent_id, key, request, reason, now=None):
        now = time.time() if now is None else now
        with self.transaction() as db:
            if db.execute("SELECT 1 FROM intents WHERE id=?", (intent_id,)).fetchone():
                return False
            db.execute("INSERT INTO intents VALUES(?,?,?,?,?,?,?,?,?,?)", (intent_id, key, utc_day(now), "MANAGEMENT", "PREPARED", 0, "[]", encode({"request": request, "reason": reason, "action_reason": reason}), now, now))
            db.execute("INSERT INTO audit(at,event,payload) VALUES(?,?,?)",
                       (now, "MANAGEMENT_PREPARED", encode({"intent_id": intent_id, "reason": reason})))
        return True

    def claim_send(self, intent_id):
        """Persistent compare-and-set: exactly one sender can claim this intent."""
        with self.transaction() as db:
            row = db.execute("SELECT account_key,kind,day FROM intents WHERE id=?", (intent_id,)).fetchone()
            if not row:
                return False
            if row["kind"] == "ENTRY" and db.execute("SELECT 1 FROM day_halts WHERE account_key=? AND day=?", (row["account_key"], row["day"])).fetchone():
                return False
            pending = db.execute("SELECT * FROM intents WHERE account_key=? AND id<>? AND state IN (?,?,?,?,?,?)", (row["account_key"], intent_id, *ACTIVE_STATES)).fetchall()
            if any(blocks_send(self._intent(r)) for r in pending):
                return False
            changed = db.execute("UPDATE intents SET state='SENDING',updated=? WHERE id=? AND state='PREPARED'", (time.time(), intent_id)).rowcount
            if changed:
                db.execute("INSERT INTO audit(at,event,payload) VALUES(?,?,?)",
                           (time.time(), "INTENT_SENDING", encode({"intent_id": intent_id})))
        return bool(changed)

    def set_intent_state(self, intent_id, state, **fields):
        if state not in (*ACTIVE_STATES, "REJECTED", "CANCELLED", "CLOSED"):
            raise ValueError("Unknown execution state")
        with self.transaction() as db:
            row = db.execute("SELECT * FROM intents WHERE id=?", (intent_id,)).fetchone()
            if not row:
                raise KeyError(intent_id)
            if row["state"] in ("REJECTED", "CANCELLED", "CLOSED") and state != row["state"]:
                raise ValueError("Terminal intent cannot be reactivated")
            payload = json.loads(row["payload"])
            payload.update(fields)
            reserved = fields.get("reserved", row["reserved"])
            if state in ("REJECTED", "CANCELLED", "CLOSED"):
                reserved = 0.0
            if not math.isfinite(float(reserved)) or reserved < 0:
                raise ValueError("Invalid reservation")
            if state == row["state"] and reserved == row["reserved"] and payload == json.loads(row["payload"]):
                return self._intent(row)
            db.execute("UPDATE intents SET state=?,reserved=?,payload=?,updated=? WHERE id=?", (state, reserved, encode(payload), time.time(), intent_id))
            db.execute("INSERT INTO audit(at,event,payload) VALUES(?,?,?)",
                       (time.time(), "INTENT_" + state, encode({"intent_id": intent_id, **fields})))
        return self.intent(intent_id)

    def snapshot(self, account_key, now=None):
        intents = self.intents(account_key)
        return {"day": self.get_day(account_key, now), "intents": intents,
                "reserved": sum(i["reserved"] for i in intents if i["state"] in ACTIVE_STATES),
                "unresolved": [i["id"] for i in intents if blocks_send(i)]}

