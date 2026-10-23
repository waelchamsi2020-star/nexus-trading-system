"""Authenticated local controls for the single Demo executor; never sends orders."""
import argparse
import json
import math
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from nexus.server import LocalServer
from tools.demo_limits import amend, read
from tools.demo_performance import summarize


class Controls:
    def __init__(self, directory):
        self.directory = Path(directory)

    def _connect(self, *, writable=False):
        # Viewing a missing installation must never create a new, empty journal.
        mode = 'rw' if writable else 'ro'
        uri = (self.directory / 'trades.db').resolve().as_uri() + '?mode=' + mode
        return sqlite3.connect(uri, uri=True)

    def _snapshot(self, db):
        result = {'limits': read(db), 'status': {}, 'server_time': time.time(),
                  'last_bar': None, 'last_reasons': {}, 'mirror_warning': None,
                  'user_paused': False, 'fresh': False, 'running': False,
                  'status_timestamp': None, 'identity': {}}
        latest = db.execute('SELECT MAX(bar) FROM signals').fetchone()[0]
        result['last_bar'] = latest
        result['last_reasons'] = dict(db.execute(
            'SELECT reason,COUNT(*) FROM signals WHERE bar=? GROUP BY reason',
            (latest,)).fetchall()) if latest is not None else {}
        state = dict(db.execute('SELECT key,value FROM state').fetchall())
        try:
            paused = json.loads(state.get('user_paused', 'false'))
            if not isinstance(paused, bool):
                raise TypeError('INVALID_PAUSE_STATE')
            result['user_paused'] = paused
            published = state.get('published_status')
            status = json.loads(published if published is not None else
                                (self.directory / 'status.json').read_text(encoding='utf-8'))
            config = json.loads((self.directory / 'config.json').read_text(encoding='utf-8'))
            if not isinstance(status, dict) or not isinstance(config, dict):
                raise TypeError('INVALID_EXECUTOR_STATUS')
            # Reject NaN/Infinity before returning JSON or doing risk arithmetic.
            json.dumps(status, allow_nan=False)
            for key in ('balance', 'equity', 'daily_loss_limit', 'daily_loss',
                        'exposure', 'floating_pnl', 'daily_profit', 'daily_profit_target'):
                value = status.get(key)
                if value is not None and (isinstance(value, bool) or
                                          not isinstance(value, (int, float))):
                    raise ValueError('INVALID_STATUS_NUMBER: ' + key)
            positions = status.get('positions', [])
            if not isinstance(positions, list) or any(not isinstance(p, dict) for p in positions):
                raise ValueError('INVALID_STATUS_POSITIONS')
            stamp = datetime.fromisoformat(status['utc'])
            if stamp.tzinfo is None:
                raise ValueError('STATUS_TIMEZONE_REQUIRED')
            timestamp = stamp.timestamp()
            expected = config['account_login']
            if (type(expected) is not int or expected <= 0 or
                    type(status.get('account')) is not int or status['account'] != expected or
                    status.get('trade_mode', 0) != 0):
                raise ValueError('DEMO_ACCOUNT_IDENTITY_MISMATCH')
            expiry = config['expires_at']
            if isinstance(expiry, bool) or not isinstance(expiry, (int, float)) or not math.isfinite(expiry):
                raise ValueError('INVALID_AUTHORIZATION_EXPIRY')
            result.update(status=status, status_timestamp=timestamp,
                          fresh=0 <= result['server_time'] - timestamp < 40,
                          identity={'login': expected, 'server': config.get('account_server')})
            reason = status.get('error')
            if not reason and (self.directory / 'STOP').exists():
                reason = 'USER_KILL_SWITCH'
            halt = json.loads(state.get('halt', 'null'))
            if not reason and halt:
                reason = 'PERSISTENT_HALT: ' + str(halt)
            if not reason and result['server_time'] >= expiry:
                reason = 'AUTHORIZATION_24H_EXPIRED'
            if not reason and not result['fresh']:
                reason = 'EXECUTOR_STATUS_STALE_OR_FUTURE'
            if not reason and status.get('mode') != 'DEMO_LIVE':
                reason = 'EXECUTOR_NOT_RUNNING'
            result['running'] = not bool(reason)
            result['stop_reason'] = reason
            result['mirror_warning'] = json.loads(state.get('status_mirror_warning', 'null'))
            result['performance'] = summarize(db, status, result['fresh'])
        except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
            result.update(error='تعذر التحقق من حالة المنفّذ: ' + str(exc),
                          status={}, identity={}, fresh=False, running=False)
        return result

    def snapshot(self):
        try:
            with self._connect() as db:
                return self._snapshot(db)
        except (OSError, sqlite3.Error, ValueError, TypeError) as exc:
            return {'error': 'تعذر قراءة سجل المنفّذ: ' + str(exc), 'limits': None,
                    'status': {}, 'server_time': time.time(), 'fresh': False,
                    'running': False, 'user_paused': False, 'last_reasons': {}}

    def action(self, payload):
        if payload.get("action") in ("pause", "resume"):
            paused = payload["action"] == "pause"
            with self._connect(writable=True) as db:
                db.execute('BEGIN IMMEDIATE')
                if not paused:
                    snapshot = self._snapshot(db)
                    if not snapshot['running']:
                        raise ValueError('المنفّذ متوقف: ' + str(snapshot.get('error') or
                                         snapshot.get('stop_reason')) + '؛ يلزم معالجة السبب قبل التشغيل')
                db.execute("INSERT OR REPLACE INTO state VALUES ('user_paused',?)",
                           (json.dumps(paused),))
                db.execute("INSERT INTO audit(at,event,payload) VALUES (?,?,?)",
                           (time.time(), "USER_ENTRIES_PAUSED" if paused else "USER_ENTRIES_RESUMED",
                            json.dumps({"positions_unchanged": True})))
            return {"ok": True, "paused": paused}
        if payload.get("action") != "limits":
            raise ValueError("إجراء غير متاح")
        result = amend(self.directory / "trades.db", payload["values"], payload["revision"])
        return {"ok": True, "limits": result}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    server = LocalServer(Controls(args.directory), ROOT / "tools/demo_control_ui")
    url = server.start()
    (args.directory / "control-url.txt").write_text(url, encoding="utf-8")
    print(url, flush=True)
    try:
        while True:
            time.sleep(1)
    finally:
        server.stop()
