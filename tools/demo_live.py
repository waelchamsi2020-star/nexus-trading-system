"""Explicitly authorized, account-pinned MT5 demo execution service.

One entry per model and closed bar; concurrent entries share a cash exposure cap.
No real account, automatic restart authorization, blind retry or pending orders.
The existing desktop engine must remain READ_ONLY to avoid two send authorities.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import sys
import tempfile
import time
import uuid
from collections import deque
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
from nexus import __version__
from nexus.execution_authority import ExecutionAuthorityLease, authority_lock_path
from nexus.strategies import REGISTRY, analyze_all, atr
from tools.demo_limits import initialize as initialize_limits
from tools.demo_limits import read as read_limits

MAX_OPEN_POSITIONS = 3
OPPORTUNITY_WINDOW_SECONDS = 120
DUBAI = timezone(timedelta(hours=4), name='Asia/Dubai')
GUARD_SNAPSHOTS = deque(maxlen=500)


class MarketDataUnavailable(RuntimeError):
    """Transient observation failure; blocks entries without renewing authority."""


class MarketClosed(RuntimeError):
    """The broker session is closed; wait and recheck without evaluating signals."""


def encoded(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, default=str)


def finite(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError('NONFINITE_BROKER_VALUE')
    return result


def completed_window(rows, as_of, period=60, count=300):
    """Freeze observation time and exclude unfinished candles, including SDK roll races."""
    closed = [row for row in rows if int(row['time']) + period <= as_of]
    if len(closed) < count or as_of - (int(closed[-1]['time']) + period) > period:
        return None
    return closed[-count:]


def current_quote(quote, as_of, max_age):
    """A broker quote must be finite and fresh; allow 1s clock/timestamp skew."""
    if quote is None:
        return False
    try:
        # MT5 exposes second and millisecond timestamps. Prefer the precise field;
        # the second field may round across a second boundary, and the broker and
        # local clocks can differ by a few hundred milliseconds.
        stamp_ms = getattr(quote, 'time_msc', None)
        stamp = finite(stamp_ms) / 1000 if stamp_ms is not None else finite(quote.time)
        age = finite(as_of) - stamp
        bid, ask = finite(quote.bid), finite(quote.ask)
    except (AttributeError, TypeError, ValueError):
        return False
    return -1 <= age <= max_age and 0 < bid <= ask


def market_session_closed(symbol_info, quote, now=None):
    """Market-open truth uses instrument session deals and quote age only."""
    now = time.time() if now is None else now.timestamp()
    if symbol_info is None or quote is None:
        return True
    try:
        stamp = finite(quote.time_msc) / 1000
        age = now - stamp
        return int(getattr(symbol_info, 'session_deals', 0)) <= 0 or age < -1 or age > 60
    except (AttributeError, TypeError, ValueError):
        return True


class PermissionDebouncePending(MarketDataUnavailable):
    """One or two transient permission failures while the instrument is open."""


def risk_for_stop(sdk, side, symbol, volume, entry, stop, point, slippage_points):
    """Include stop loss, slippage reserve, and commission in cash risk."""
    sign = 1 if side == 0 else -1
    cash = sdk.order_calc_profit(side, symbol, volume, entry, stop)
    slip = sdk.order_calc_profit(side, symbol, volume,
                                 entry, entry - sign * slippage_points * point)
    if cash is None or slip is None:
        raise RuntimeError('NEW_POSITION_RISK_UNKNOWN')
    return abs(finite(cash)) + abs(finite(slip)) + volume * 7.


def signal_time_rejection(card, bar, period, as_of):
    """Analysis validity is rechecked after broker preflight, before any RPC."""
    try:
        data_time, expires_at = finite(card['data_time']), finite(card['expires_at'])
    except (KeyError, TypeError, ValueError):
        return 'INVALID_SIGNAL_TIME'
    if data_time != bar + period or data_time > as_of or expires_at <= data_time:
        return 'INVALID_SIGNAL_TIME'
    if as_of >= min(expires_at, bar + 2 * period):
        return 'EXPIRED_SIGNAL_BEFORE_SEND'
    return None


def cash_levels(side, price, tick_size, cash_per_tick, loss, profit, costs):
    """Round stop towards entry and profit away; costs include the configured reserve."""
    if cash_per_tick <= 0 or loss <= costs or profit <= 0:
        raise ValueError('CASH_TARGET_BELOW_COST_RESERVE')
    sign = 1 if side == 0 else -1
    stop = price - sign * (loss - costs) / cash_per_tick * tick_size
    target = price + sign * (profit + costs) / cash_per_tick * tick_size
    rounding = math.ceil if side == 0 else math.floor
    return rounding(stop / tick_size) * tick_size, rounding(target / tick_size) * tick_size


def mirror_status(directory, status, attempts=5):
    """Best-effort display mirror. SQLite remains the durable source of status."""
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=directory,
                                         prefix='status-', suffix='.tmp', delete=False) as stream:
            name = Path(stream.name)
            stream.write(encoded(status))
            stream.flush()
            os.fsync(stream.fileno())
        for retry in range(attempts):
            try:
                name.replace(directory / 'status.json')
                return None
            except PermissionError:
                if retry + 1 == attempts:
                    raise
                time.sleep(.05 * (retry + 1))
    except OSError as exc:
        return str(exc)
    finally:
        if name is not None:
            try:
                name.unlink(missing_ok=True)
            except OSError:
                pass


def active_opportunity_conflicts(requests, side, *, now=None, window_seconds=OPPORTUNITY_WINDOW_SECONDS,
                                 symbol='EURUSD'):
    """Return same-direction attempts still inside the short signal window.

    A broker position is deliberately not an opportunity: it may remain open
    long after the signal that created it has expired.
    """
    now = time.time() if now is None else float(now)
    conflicts = []
    for attempt in requests:
        age = now - float(attempt.get('at', float('-inf')))
        request = attempt.get('request', attempt)
        if (0 <= age <= window_seconds and attempt.get('status') in ('FILLED', 'SENDING', 'AMBIGUOUS')
                and request.get('symbol') == symbol and request.get('type') == side):
            conflicts.append({
                'opportunity_id': attempt.get('opportunity_id'),
                'age_seconds': age,
                'status': attempt.get('status'),
                'request': request,
            })
    return conflicts


def repeated_opportunity(positions, requests, side, symbol='EURUSD', magic=20261019,
                         *, now=None, window_seconds=OPPORTUNITY_WINDOW_SECONDS):
    """Only a recent active attempt overlaps; open positions never do by themselves."""
    del positions, magic  # Preserved in the signature for callers; not an overlap signal.
    return bool(active_opportunity_conflicts(requests, side, now=now,
                                             window_seconds=window_seconds, symbol=symbol))


def position_capacity_reached(positions, pending_orders, limit=MAX_OPEN_POSITIONS):
    """Pending orders reserve a position slot just like an open position."""
    return len(positions) + len(pending_orders) >= limit


class Service:
    def __init__(self, sdk, config_path):
        self.sdk = sdk
        self.path = Path(config_path).resolve()
        self.config_bytes = self.path.read_bytes()
        self.c = json.loads(self.config_bytes)
        expected = {'mode': 'DEMO_LIVE', 'symbol': 'EURUSD', 'timeframe': 'M1',
                    'volume': .01, 'sl_atr': 1.5, 'tp_atr': 3., 'magic': 20261019,
                    'comment': 'NEXUS_0.7.0', 'max_exposure_amount': 100.,
                    'max_trade_risk_percent': 2., 'daily_loss_amount': 100.,
                    'daily_profit_amount': 100., 'profile': 'FAST_SCALP', 'kill_drawdown_percent': 10.,
                    'slippage_points': 10, 'commission_reserve_per_lot': 7.,
                    'max_open_positions': MAX_OPEN_POSITIONS,
                    'demo_only': True, 'account_trade_mode': 0,
                    'api_keys_enabled': False, 'live_endpoint_enabled': False,
                    'authorization_duration_seconds': 86400}
        if any(self.c.get(k) != v for k, v in expected.items()) or len(REGISTRY) != 58:
            raise ValueError('UNAUTHORIZED_CONFIGURATION')
        self.directory = self.path.parent
        self.db = sqlite3.connect(self.directory / 'trades.db', timeout=5)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, at REAL, event TEXT, payload TEXT);
            CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE IF NOT EXISTS signals(bar INTEGER, model TEXT, direction TEXT, status TEXT,
                reason TEXT, payload TEXT, PRIMARY KEY(bar,model));
            CREATE TABLE IF NOT EXISTS attempts(bar INTEGER, at REAL, model TEXT,
                status TEXT, request TEXT, result TEXT, PRIMARY KEY(bar,model));
            CREATE TABLE IF NOT EXISTS deals(ticket INTEGER PRIMARY KEY, payload TEXT);
            CREATE TABLE IF NOT EXISTS hourly(hour INTEGER PRIMARY KEY, payload TEXT);
        ''')
        primary = [row[1] for row in self.db.execute('PRAGMA table_info(attempts)') if row[5]]
        if primary == ['bar']:
            if self.db.execute("SELECT 1 FROM attempts WHERE status IN ('SENDING','AMBIGUOUS')").fetchone():
                raise RuntimeError('UNRESOLVED_SEND_PREVENTS_SCHEMA_CHANGE')
            with self.db:
                self.db.execute('ALTER TABLE attempts RENAME TO attempts_single_entry_archive')
                self.db.execute('CREATE TABLE attempts(bar INTEGER, at REAL, model TEXT, '
                                'status TEXT, request TEXT, result TEXT, PRIMARY KEY(bar,model))')
                self.db.execute('INSERT INTO attempts SELECT * FROM attempts_single_entry_archive')
                self.db.execute('INSERT INTO audit(at,event,payload) VALUES (?,?,?)',
                                (time.time(), 'MULTI_ENTRY_SCHEMA_MIGRATION', encoded({'history_preserved': True})))
        self.started = time.time()
        self.guard_snapshots = GUARD_SNAPSHOTS
        self._permission_failures = deque(maxlen=3)
        initialize_limits(self.db, self.c)
        self.limits_revision = -1
        self.account = self.guard()
        old = self.get('identity')
        identity = [self.account.login, self.account.server, self.sdk.terminal_info().path]
        if old is not None and old != identity:
            raise RuntimeError('JOURNAL_ACCOUNT_MISMATCH')
        self.set('identity', identity)
        if self.get('halt') and not self.halt_was_superseded():
            raise RuntimeError('PERSISTENT_HALT: ' + str(self.get('halt')))
        if self.db.execute("SELECT 1 FROM attempts WHERE status IN ('SENDING','AMBIGUOUS')").fetchone():
            raise RuntimeError('UNRESOLVED_SEND_REQUIRES_RECONCILIATION')
        self.set('peak_equity', max(finite(self.account.equity), self.get('peak_equity') or 0.))
        self.audit('DEMO_LIVE_AUTHORIZED', {'config': self.c, 'identity': identity})

    def get(self, key):
        row = self.db.execute('SELECT value FROM state WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def set(self, key, value):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO state VALUES (?,?)', (key, encoded(value)))

    def audit(self, event, value):
        with self.db:
            self.db.execute('INSERT INTO audit(at,event,payload) VALUES (?,?,?)',
                            (time.time(), event, encoded(value)))

    def halt_was_superseded(self):
        """Keep the old halt evidence, but honor explicit audit supersession 1080."""
        rows = self.db.execute("SELECT id,event,payload FROM audit WHERE event IN "
                               "('EXECUTION_HALTED','EXECUTION_HALT_SUPERSEDED') ORDER BY id DESC LIMIT 2").fetchall()
        if len(rows) < 2 or rows[0][1] != 'EXECUTION_HALT_SUPERSEDED':
            return False
        try:
            payload = json.loads(rows[0][2])
        except (TypeError, ValueError):
            return False
        return (payload.get('supersedes_halt_audit_id') == 1078 and
                payload.get('superseded_reason') == 'DEMO_ACCOUNT_TRADING_PERMISSION_DISABLED' and
                rows[1][0] == 1078)

    def renew_demo_authorization_if_due(self, renewal_limit=1, renewal_window=600,
                                        horizon_seconds=72 * 3600):
        """Honor the user's bounded auto-renewal mandate without changing account scope."""
        now = time.time()
        old_expiry = finite(self.c['expires_at'])
        if old_expiry - now > renewal_window:
            return False
        count = int(self.get('demo_authorization_renewals') or 0)
        if count >= renewal_limit:
            self.audit('DEMO_AUTO_RENEWAL_LIMIT_REACHED', {
                'renewals': count, 'limit': renewal_limit, 'account': self.c['account_login'],
                'server': self.c['account_server'], 'demo_only': True,
            'code_version': __version__,
                'user_command': 'Allow at most two automatic 24-hour Demo renewals; then stop.'})
            self.set('halt', 'AUTHORIZATION_RENEWAL_LIMIT_REACHED')
            raise RuntimeError('AUTHORIZATION_RENEWAL_LIMIT_REACHED')
        account, terminal = self.sdk.account_info(), self.sdk.terminal_info()
        if (account is None or terminal is None or account.trade_mode != 0 or
                account.login != 1045864 or account.server != 'Capital.ComMena-Demo' or
                not terminal.connected):
            raise RuntimeError('DEMO_RENEWAL_IDENTITY_OR_PERMISSION_CHECK_FAILED')
        start = old_expiry
        expiry = start + 86400
        if expiry > now + horizon_seconds:
            raise RuntimeError('DEMO_RENEWAL_72H_HORIZON_REACHED')
        new_id = str(uuid.uuid4())
        updated = dict(self.c)
        updated.update(authorized_at=start, expires_at=expiry,
                       authorization_guard_floor=now, authorization_id=new_id,
                       authorization=(
                           f'User-authorized Demo-only renewal {count + 1}/{renewal_limit}; '
                           'account 1045864; server Capital.ComMena-Demo; trade_mode=0; '
                           'no API keys; no real endpoint.'),
                       source=f"{self.c.get('source', '')}")
        self.audit('DEMO_AUTHORIZATION_RENEWAL_INTENT', {
            'renewal': count + 1, 'authorization_id': new_id,
            'starts_at': start, 'expires_at': expiry,
            'account': 1045864, 'server': 'Capital.ComMena-Demo', 'trade_mode': 0,
            'demo_only': True, 'api_keys_enabled': False, 'live_endpoint_enabled': False,
            'code_version': __version__,
            'user_command': 'Bounded automatic Demo-only renewal; maximum one additional renewal, 72-hour horizon.'})
        encoded_config = json.dumps(updated, ensure_ascii=False, indent=2).encode('utf-8')
        name = None
        try:
            with tempfile.NamedTemporaryFile(mode='wb', dir=self.path.parent,
                                             prefix='config-renewal-', suffix='.tmp',
                                             delete=False) as stream:
                name = Path(stream.name)
                stream.write(encoded_config)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.path)
        except Exception:
            if name is not None:
                name.unlink(missing_ok=True)
            raise
        self.c = updated
        self.config_bytes = encoded_config
        self.set('demo_authorization_renewals', count + 1)
        self.audit('DEMO_AUTHORIZATION_RENEWED', {
            'renewal': count + 1, 'authorization_id': new_id,
            'starts_at': start, 'expires_at': expiry,
            'account': 1045864, 'server': 'Capital.ComMena-Demo', 'trade_mode': 0,
            'demo_only': True, 'api_keys_enabled': False, 'live_endpoint_enabled': False,
            'code_version': __version__})
        return True

    def guard(self):
        if self.path.read_bytes() != self.config_bytes:
            raise RuntimeError('CONFIG_CHANGED_REAUTHORIZATION_REQUIRED')
        account, terminal = self.sdk.account_info(), self.sdk.terminal_info()
        if account is None or terminal is None:
            raise RuntimeError('DEMO_ACCOUNT_REQUIRED')
        if account.trade_mode != 0:
            raise RuntimeError('REAL_ACCOUNT_DETECTED')
        if (account.login != self.c['account_login'] or account.server != self.c['account_server'] or
                terminal.path != self.c['terminal_path']):
            raise RuntimeError('ACCOUNT_OR_TERMINAL_CHANGED')
        if account.currency != 'USD':
            raise RuntimeError('USD_ACCOUNT_REQUIRED_FOR_COST_RESERVE')
        if (self.directory / 'STOP').exists():
            raise RuntimeError('USER_KILL_SWITCH')
        duration = self.c.get('authorization_duration_seconds', 86400)
        authorized_at = self.c.get('authorized_at', self.c['expires_at'] - duration)
        if abs((self.c['expires_at'] - authorized_at) - duration) > 1:
            raise RuntimeError('INVALID_AUTHORIZATION_WINDOW')
        if finite(account.equity) <= 0:
            raise RuntimeError('NONPOSITIVE_EQUITY')
        # Wait only after verifying identity, permissions and authorization.
        # Each later cycle repeats all checks before any send.
        if not terminal.connected:
            raise MarketDataUnavailable('MT5_CONNECTION_UNAVAILABLE')
        return account

    def ensure_market_open(self):
        """Instrument/session first; permissions are consulted only in open session."""
        now = time.time()
        info = tick = account = terminal = None
        retcode = None
        tick_msc = tick_age = session_deals = None
        try:
            info = self.sdk.symbol_info(self.c['symbol'])
            tick = self.sdk.symbol_info_tick(self.c['symbol'])
            if info is None or tick is None:
                try:
                    retcode = self.sdk.last_error()
                except Exception as exc:  # noqa: BLE001 - preserve arbitrary MT5 retcode failure
                    retcode = str(exc)
                account = self.sdk.account_info()
                terminal = self.sdk.terminal_info()
                raise MarketDataUnavailable('MT5_CALL_FAILED: ' + str(retcode))
            tick_msc = tick.time_msc if tick is not None and hasattr(tick, 'time_msc') else None
            tick_age = now - finite(tick_msc) / 1000 if tick_msc is not None else None
            session_deals = info.session_deals if info is not None and hasattr(info, 'session_deals') else None
            market_open = (session_deals is not None and int(session_deals) > 0 and
                           tick_age is not None and -1 <= tick_age <= 60)
            # Read all fields for the requested immutable evidence snapshot; these
            # flags never determine the market branch while the session is closed.
            terminal = self.sdk.terminal_info()
            account = self.sdk.account_info()
        except Exception:  # noqa: BLE001 - MT5 SDK failures must never become permission failures
            try:
                retcode = self.sdk.last_error()
            except Exception as exc:  # noqa: BLE001 - preserve arbitrary MT5 retcode failure
                retcode = str(exc)
            market_open = False
            try:
                tick_age = now - finite(tick_msc) / 1000 if tick_msc is not None else None
            except (TypeError, ValueError):
                tick_age = None
            if session_deals is None and info is not None and hasattr(info, 'session_deals'):
                session_deals = info.session_deals
            self._record_guard_snapshot(now, terminal, account, info, tick, tick_age,
                                        'MT5_CALL_FAILED', retcode)
            self.set('market_state', 'WAITING_MARKET')
            raise MarketDataUnavailable('MT5_CALL_FAILED: ' + str(retcode))

        if account is None or terminal is None:
            retcode = self.sdk.last_error()
            self._record_guard_snapshot(now, terminal, account, info, tick, tick_age,
                                        'MT5_CALL_FAILED', retcode)
            self.set('market_state', 'WAITING_MARKET')
            raise MarketDataUnavailable('MT5_CALL_FAILED: ' + str(retcode))
        if not market_open:
            self._permission_failures.clear()
            self._record_guard_snapshot(now, terminal, account, info, tick, tick_age,
                                        'MARKET_CLOSED', None)
            self.set('market_state', 'WAITING_MARKET')
            raise MarketClosed('MARKET_CLOSED')

        failed = not bool(account.trade_allowed) or bool(terminal.tradeapi_disabled)
        if failed:
            last = self._permission_failures[-1] if self._permission_failures else None
            if last is None or now - last['at'] >= 10:
                snap = self._record_guard_snapshot(now, terminal, account, info, tick, tick_age,
                                                   'PERMISSION_FAIL', None)
                self._permission_failures.append({'at': now, 'snapshot': snap})
            else:
                snap = self._record_guard_snapshot(now, terminal, account, info, tick, tick_age,
                                                   'PERMISSION_FAIL', None)
            if len(self._permission_failures) < 3:
                self.set('market_state', 'WAITING_PERMISSION_CONFIRMATION')
                raise PermissionDebouncePending('PERMISSION_CONFIRMATION_PENDING')
            failures = list(self._permission_failures)[-3:]
            intervals = [failures[i]['at'] - failures[i-1]['at'] for i in (1, 2)]
            if all(gap >= 10 for gap in intervals):
                self.audit('DEMO_PERMISSION_DEBOUNCE_CONFIRMED', {
                    'snapshots': [item['snapshot'] for item in failures],
                    'intervals_seconds': intervals, 'market_open': True})
                raise RuntimeError('DEMO_ACCOUNT_TRADING_PERMISSION_DISABLED')
            self.set('market_state', 'WAITING_PERMISSION_CONFIRMATION')
            raise PermissionDebouncePending('PERMISSION_CONFIRMATION_PENDING')
        self._permission_failures.clear()
        self._record_guard_snapshot(now, terminal, account, info, tick, tick_age,
                                    'PERMISSION_OK', None)
        if not terminal.connected:
            raise MarketDataUnavailable('MT5_CONNECTION_UNAVAILABLE')
        if not current_quote(tick, now, 5):
            self.set('market_state', 'WAITING_MARKET')
            raise MarketDataUnavailable('MARKET_QUOTE_STALE')
        if self.c.get('account_login') != account.login or account.trade_mode != 0:
            raise RuntimeError('DEMO_IDENTITY_CHANGED')
        if not account.trade_expert:
            raise MarketDataUnavailable('DEMO_EXPERT_PERMISSION_UNAVAILABLE')

        if self.get('market_open_first_quote_at') is None:
            self.set('market_open_first_quote_at', now)
            self.audit('MARKET_OPEN_FIRST_FRESH_QUOTE', {
                'quote_age_seconds': tick_age, 'spread_filter_enforced': False,
                'candidate_evaluation_follows': True})
        self.set('market_state', 'MARKET_OPEN')

    def _record_guard_snapshot(self, now, terminal, account, info, tick, tick_age, branch, retcode):
        def field(obj, key):
            return getattr(obj, key, None) if obj is not None else None
        snapshot = {
            'at': now, 'time': datetime.fromtimestamp(now, UTC).isoformat(),
            'terminal.connected': field(terminal, 'connected'),
            'terminal.trade_allowed': field(terminal, 'trade_allowed'),
            'tradeapi_disabled': field(terminal, 'tradeapi_disabled'),
            'account.trade_allowed': field(account, 'trade_allowed'),
            'account.trade_expert': field(account, 'trade_expert'),
            'session_deals': field(info, 'session_deals'),
            'session_buy_orders': field(info, 'session_buy_orders'),
            'session_sell_orders': field(info, 'session_sell_orders'),
            'tick.time_msc': field(tick, 'time_msc'), 'tick_age_seconds': tick_age,
            'server_time': field(tick, 'time'), 'branch': branch, 'retcode': retcode}
        if not hasattr(self, 'guard_snapshots'):
            self.guard_snapshots = GUARD_SNAPSHOTS
        self.guard_snapshots.append(snapshot)
        self.audit('EXECUTION_GUARD_SNAPSHOT', snapshot)
        return snapshot

    def desktop_guard(self):
        # Desktop authorizes only AFTER its durable audit commit. Read that source
        # directly: the large /api/state snapshot can time out during analysis.
        path = Path(self.c['desktop_audit_db']).resolve()
        with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=2) as db:
            authorization = db.execute("SELECT event FROM audit WHERE event IN "
                "('AUTHORIZATION_ACTIVATED','AUTHORIZATION_REVOKED') ORDER BY sequence DESC LIMIT 1").fetchone()
            stop = db.execute("SELECT MAX(at) FROM audit WHERE event='ENTRIES_STOPPED'").fetchone()[0]
        stop_floor = self.c.get('authorization_guard_floor', self.c['authorized_at'])
        if stop is not None and stop >= stop_floor:
            raise RuntimeError('USER_DESKTOP_STOP_ENTRIES')
        if authorization is None or authorization[0] != 'AUTHORIZATION_REVOKED':
            raise RuntimeError('SECOND_EXECUTION_AUTHORITY_DETECTED')

    def snapshot(self):
        current = read_limits(self.db)
        if current['revision'] != self.limits_revision:
            self.c.update(current['values'])
            self.limits_revision = current['revision']
        self.ensure_market_open()
        if self.c.get('expires_at') is not None and time.time() >= self.c['expires_at']:
            self.set('market_state', 'WAITING_AUTHORIZATION')
            raise MarketDataUnavailable('WAITING_AUTHORIZATION')
        account = self.guard()
        positions, orders = self.sdk.positions_get(), self.sdk.orders_get()
        now = datetime.now(UTC)
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        deals = self.sdk.history_deals_get(midnight, now)
        if positions is None or orders is None or deals is None:
            raise RuntimeError('BROKER_SNAPSHOT_INCOMPLETE')
        # Non-trading cash movements during the day need independent reconciliation.
        if any(d.type not in (0, 1, 4, 7, 8, 9, 10, 11, 12, 17) for d in deals):
            raise RuntimeError('INTRADAY_CASHFLOW_REQUIRES_RECONCILIATION')
        realized = sum(finite(d.profit) + finite(d.commission) + finite(d.swap) + finite(d.fee) for d in deals)
        baseline = finite(account.balance) - realized
        if baseline <= 0:
            raise RuntimeError('INVALID_DAILY_BASELINE')
        peak = max(self.get('peak_equity') or account.equity, finite(account.equity))
        self.set('peak_equity', peak)
        drawdown = 100 * (peak - account.equity) / peak
        loss = max(0., baseline - finite(account.equity))
        daily_limit = self.c['daily_loss_amount']
        daily_profit = finite(account.equity) - baseline
        if self.c['kill_drawdown_percent'] > 0 and drawdown >= self.c['kill_drawdown_percent']:
            raise RuntimeError('KILL_DRAWDOWN_LIMIT')
        day = midnight.isoformat()
        # A user amendment re-evaluates against the same day's actual P&L.
        # It never resets cash flows, equity peak, or broker positions.
        halt_key = [day, self.limits_revision]
        if loss >= daily_limit:
            self.set('daily_halt', halt_key)
        if daily_profit >= self.c['daily_profit_amount']:
            self.set('daily_target_halt', halt_key)
        exposure = 0.
        for p in positions:
            if not p.sl:
                raise RuntimeError('UNBOUNDED_ACCOUNT_POSITION')
            quote, info = self.sdk.symbol_info_tick(p.symbol), self.sdk.symbol_info(p.symbol)
            if info is None or not current_quote(quote, time.time(), 30):
                raise MarketDataUnavailable('POSITION_QUOTE_UNAVAILABLE')
            current = quote.bid if p.type == 0 else quote.ask
            pnl = self.sdk.order_calc_profit(p.type, p.symbol, p.volume, current, p.sl)
            reserve = self.sdk.order_calc_profit(p.type, p.symbol, p.volume, current,
                                                 current + (-1 if p.type == 0 else 1) * 10 * info.point)
            if pnl is None or reserve is None:
                raise RuntimeError('POSITION_RISK_UNKNOWN')
            exposure += max(0., -finite(pnl)) + abs(finite(reserve)) + p.volume * 7.
        if orders and position_capacity_reached(positions, orders):
            raise RuntimeError('MAX_OPEN_POSITIONS_REACHED_PENDING_EXPOSURE')
        if orders:
            raise RuntimeError('PENDING_ORDER_EXPOSURE_REQUIRES_RECONCILIATION')
        for d in deals:
            with self.db:
                self.db.execute('INSERT OR REPLACE INTO deals VALUES (?,?)', (d.ticket, encoded(d._asdict())))
        # Daily risk uses today's cash flows above. Performance needs exits from
        # the entire observed service period, including while this process was off.
        if time.time() - (self.get('history_reconciled_at') or 0) >= 60:
            first = self.db.execute('SELECT MIN(at) FROM attempts').fetchone()[0]
            history = self.sdk.history_deals_get(
                datetime.fromtimestamp(first - 60, UTC) if first is not None else midnight, now)
            if history is not None:
                with self.db:
                    self.db.executemany('INSERT OR REPLACE INTO deals VALUES (?,?)',
                                        [(d.ticket, encoded(d._asdict())) for d in history])
                self.set('history_reconciled_at', time.time())
        return {'account': account, 'positions': positions, 'orders': orders,
                'equity': finite(account.equity),
                'daily_loss': loss, 'daily_limit': daily_limit, 'day': day, 'exposure': exposure,
                'drawdown_percent': drawdown, 'daily_halt': self.get('daily_halt') in (day, halt_key),
                'daily_profit': daily_profit, 'target_halt': self.get('daily_target_halt') in (day, halt_key)}

    def reject(self, bar, model, reason):
        with self.db:
            self.db.execute('UPDATE signals SET reason=? WHERE bar=? AND model=?', (reason, bar, model))
            self.db.execute('INSERT INTO audit(at,event,payload) VALUES (?,?,?)',
                            (time.time(), 'SIGNAL_REJECTED', encoded({'bar': bar, 'model': model, 'reason': reason})))

    def log_measurement(self, event, details):
        now = time.time()
        payload = {'event': event, 'time_utc': datetime.fromtimestamp(now, UTC).isoformat(),
                   'time_dubai': datetime.fromtimestamp(now, DUBAI).isoformat(), **details}
        self.audit(event, payload)
        print(encoded(payload), flush=True)

    def cancel_reserved(self, bar, model, reason):
        """No RPC occurred: cancellation and its rejection audit commit together."""
        with self.db:
            changed = self.db.execute("UPDATE attempts SET status='CANCELLED_BEFORE_SEND' "
                                      "WHERE bar=? AND model=? AND status='SENDING'",
                                      (bar, model)).rowcount
            if changed != 1:
                raise RuntimeError('SEND_RESERVATION_NOT_CANCELLABLE')
            self.db.execute('UPDATE signals SET reason=? WHERE bar=? AND model=?', (reason, bar, model))
            self.db.execute('INSERT INTO audit(at,event,payload) VALUES (?,?,?)',
                            (time.time(), 'SIGNAL_REJECTED', encoded({'bar': bar, 'model': model,
                             'reason': reason, 'rpc_sent': False})))

    def analyze_and_send(self, snap):
        if self.get('user_paused'):
            return
        frame = self.c['timeframe']
        period = 60
        observed_at = time.time()
        rates = self.sdk.copy_rates_from_pos('EURUSD', self.sdk.TIMEFRAME_M1, 0, 302)
        if rates is None:
            raise MarketDataUnavailable('CLOSED_M1_HISTORY_UNAVAILABLE')
        rates = completed_window(rates, observed_at, period=period)
        if rates is None:
            self.set('data_status', 'WAITING_FOR_FRESH_CLOSED_BAR')
            self.audit('INCOMPLETE_OR_STALE_HISTORY_NO_SEND', {'observed_at': observed_at})
            return
        bars = [{k: int(r[k]) if k in ('time', 'tick_volume', 'spread', 'real_volume') else float(r[k])
                 for k in r.dtype.names} for r in rates]
        bar = bars[-1]['time']
        if bar + period > time.time():
            raise RuntimeError('UNFINISHED_SIGNAL_BAR')
        if time.time() - (bar + period) > period:
            self.set('data_status', 'WAITING_FOR_FRESH_CLOSED_BAR')
            self.audit('STALE_BAR_NO_SEND', {'bar': bar, 'observed_at': time.time()})
            return
        self.set('data_status', 'FRESH')
        if self.db.execute('SELECT 1 FROM signals WHERE bar=?', (bar,)).fetchone():
            return
        cards = analyze_all('EURUSD', frame, bars, time.time(),
                            {'tick_size': self.sdk.symbol_info('EURUSD').point,
                             'data_kind': 'broker', 'calendar_profile': 'FX_UTC22_V1'})
        if len(cards) != 58:
            raise RuntimeError('REGISTRY_COUNT_MISMATCH')
        ready = []
        with self.db:
            for card in cards:
                valid = (card['status'] == 'READY' and card.get('coverage') == 'IMPLEMENTED' and
                         card.get('entry', {}).get('triggered') is True and card.get('direction') in ('BUY', 'SELL'))
                self.db.execute('INSERT INTO signals VALUES (?,?,?,?,?,?)',
                                (bar, card['strategy_id'], card.get('direction'), card['status'],
                                 'CANDIDATE' if valid else 'NO_TRIGGER', encoded(card)))
                if valid:
                    ready.append(card)
            self.db.execute('INSERT INTO audit(at,event,payload) VALUES (?,?,?)',
                            (time.time(), 'ALL_58_MODELS_EVALUATED', encoded({'bar': bar, 'ready': len(ready)})))
        for card in sorted(ready, key=lambda c: c['strategy_id']):
            model = card['strategy_id']
            if self.db.execute('SELECT 1 FROM attempts WHERE bar=? AND model=?', (bar, model)).fetchone():
                self.reject(bar, model, 'DUPLICATE_MODEL_BAR'); continue
            snap = self.snapshot()
            if position_capacity_reached(snap['positions'], snap.get('orders', ())):
                self.reject(bar, model, 'MAX_OPEN_POSITIONS_REACHED'); continue
            if snap['daily_halt']:
                self.reject(bar, model, 'DAILY_LOSS_LIMIT'); continue
            if snap['target_halt']:
                self.reject(bar, model, 'DAILY_PROFIT_TARGET'); continue
            tick, info = self.sdk.symbol_info_tick('EURUSD'), self.sdk.symbol_info('EURUSD')
            if info is None or not current_quote(tick, time.time(), 15):
                self.reject(bar, model, 'INVALID_OR_STALE_QUOTE'); continue
            if info.volume_min > .01 or info.volume_max < .01 or abs(.01 / info.volume_step - round(.01 / info.volume_step)) > 1e-8:
                self.reject(bar, model, 'BROKER_VOLUME_INCOMPATIBLE'); continue
            side = 0 if card['direction'] == 'BUY' else 1
            now = time.time()
            active_attempts = [{
                'opportunity_id': f'{prior_bar}:{prior_model}', 'at': prior_at,
                'status': prior_status, 'request': json.loads(prior_request),
            } for prior_bar, prior_at, prior_model, prior_request, prior_status in self.db.execute(
                "SELECT bar,at,model,request,status FROM attempts WHERE at>=? "
                "AND status IN ('FILLED','SENDING','AMBIGUOUS')",
                (now - OPPORTUNITY_WINDOW_SECONDS,))]
            overlaps = active_opportunity_conflicts(active_attempts, side, now=now)
            if overlaps:
                for overlap in overlaps:
                    overlap['overlap_type'] = 'ACTIVE_ATTEMPT_IN_WINDOW'
                    overlap['outcome'] = overlap.pop('status')
                    overlap.pop('request', None)
                self.log_measurement('OPPORTUNITY_OVERLAP_MEASURED', {
                    'candidate_id': f'{bar}:{model}', 'candidate_direction': card['direction'],
                    'window_seconds': OPPORTUNITY_WINDOW_SECONDS,
                    'overlaps': overlaps})
                self.reject(bar, model, 'OVERLAPPING_OPPORTUNITY'); continue
            price = finite(tick.ask if side == 0 else tick.bid)
            entry = card['entry']
            zone = entry['zone']
            if not finite(zone[0]) <= price <= finite(zone[1]):
                diagnostic_atr = finite(atr(bars))
                point = finite(info.point)
                requested = finite(entry.get('price', (finite(zone[0]) + finite(zone[1])) / 2))
                spread_price = finite(tick.ask) - finite(tick.bid)
                reference_close = finite(bars[-20]['close'])
                latest_close = finite(bars[-1]['close'])
                trend = 'RISING' if latest_close > reference_close else (
                    'FALLING' if latest_close < reference_close else 'FLAT')
                gap_to_zone = finite(zone[0]) - price if price < finite(zone[0]) else (
                    price - finite(zone[1]) if price > finite(zone[1]) else 0.)
                self.log_measurement('ENTRY_ZONE_REJECTION_MEASURED', {
                    'candidate_id': f'{bar}:{model}', 'direction': card['direction'],
                    'requested_entry_price': requested, 'current_price': price,
                    'difference_points': abs(price - requested) / point,
                    'signed_difference_points': (price - requested) / point,
                    'entry_zone_low': finite(zone[0]), 'entry_zone_high': finite(zone[1]),
                    'distance_to_zone_points': gap_to_zone / point,
                    'atr_m1_price': diagnostic_atr, 'atr_m1_points': diagnostic_atr / point,
                    'spread_price': spread_price, 'spread_points': spread_price / point,
                    'm1_trend_20bar': trend,
                    'distance_greater_than_atr_plus_spread': abs(price - requested) > diagnostic_atr + spread_price})
                self.reject(bar, model, 'QUOTE_OUTSIDE_MODEL_ENTRY_ZONE'); continue
            distance = finite(atr(bars))
            if distance <= 0:
                raise RuntimeError('INVALID_ATR')
            sign = 1 if side == 0 else -1
            raw_sl = price - sign * 1.5 * distance
            tick_size = finite(info.trade_tick_size or info.point)
            if tick_size <= 0:
                raise RuntimeError('INVALID_TRADE_TICK_SIZE')
            # Round the protective stop toward entry: never increase ATR risk
            # because of broker precision rounding.
            sl = (math.ceil(raw_sl / tick_size) if side == 0 else math.floor(raw_sl / tick_size)) * tick_size
            sl = round(sl, info.digits)
            tp = round(price + sign * 3 * distance, info.digits)
            close_quote = tick.bid if side == 0 else tick.ask
            point = finite(info.point)
            minimum_points = max(0, int(info.trade_stops_level))
            broker_stop_points = abs(close_quote - sl) / point
            if broker_stop_points + 1e-8 < minimum_points:
                # One point beyond the broker minimum is the absolute extension
                # limit, measured from the executable close-side quote. This
                # correctly includes spread; risk is recomputed before sending.
                minimum_distance = (minimum_points + 1) * point
                raw_minimum_sl = close_quote - sign * minimum_distance
                sl = (math.ceil(raw_minimum_sl / tick_size) if side == 0 else
                      math.floor(raw_minimum_sl / tick_size)) * tick_size
                sl = round(sl, info.digits)
            actual_stop_points = abs(price - sl) / point
            risk = risk_for_stop(self.sdk, side, 'EURUSD', .01, price, sl, point, 20)
            if self.c.get('per_trade_loss_amount', 0) > 0 and risk > self.c['per_trade_loss_amount'] + 1e-8:
                self.reject(bar, model, 'STOP_RISK_EXCEEDS_CAP'); continue
            if min(abs(close_quote - sl), abs(close_quote - tp)) + 1e-8 < minimum_points * point:
                self.reject(bar, model, 'BROKER_MIN_STOP_DISTANCE'); continue
            if risk > self.c['max_trade_risk_percent'] / 100 * snap['equity']:
                self.reject(bar, model, 'TRADE_RISK_LIMIT'); continue
            if snap['exposure'] + risk >= self.c['max_exposure_amount']:
                self.reject(bar, model, 'PORTFOLIO_EXPOSURE_LIMIT'); continue
            if snap['daily_loss'] + snap['exposure'] + risk >= snap['daily_limit']:
                self.reject(bar, model, 'DAILY_LOSS_RESERVE'); continue
            if not info.filling_mode & 1:
                self.reject(bar, model, 'FOK_FILLING_UNAVAILABLE'); continue
            request = {'action': self.sdk.TRADE_ACTION_DEAL, 'symbol': 'EURUSD', 'volume': .01,
                       'type': side, 'price': price, 'sl': sl, 'tp': tp, 'deviation': 10,
                       'magic': 20261019, 'comment': 'NEXUS_0.7.0',
                       'type_time': self.sdk.ORDER_TIME_GTC, 'type_filling': self.sdk.ORDER_FILLING_FOK}
            self.desktop_guard()
            self.guard()
            self.ensure_market_open()
            self.audit('ORDER_CHECK_CALLED', {'bar': bar, 'model': model})
            checked = self.sdk.order_check(request)
            if checked is None or checked.retcode != 0:
                self.reject(bar, model, 'ORDER_CHECK: ' + str(checked)); continue
            with self.db:
                self.db.execute('INSERT INTO attempts VALUES (?,?,?,?,?,?)',
                                (bar, time.time(), model, 'SENDING', encoded(request), None,))
                self.db.execute('INSERT INTO audit(at,event,payload) VALUES (?,?,?)',
                                (time.time(), 'SEND_INTENT_RESERVED', encoded({'bar': bar, 'model': model,
                                 'request': request, 'stop_source': 'ATR', 'atr_stop': sl,
                                  'atr_distance': distance, 'atr_stop_points': actual_stop_points,
                                  'broker_min_stop_points': minimum_points, 'risk_cash': risk})))
            # No RPC has occurred. Guard/preflight failures must not be recorded
            # as an ambiguous broker send. Never include order_send in this block.
            try:
                self.desktop_guard()
                self.guard()
                self.ensure_market_open()
                rejection = signal_time_rejection(card, bar, period, time.time())
                if self.get('user_paused'):
                    rejection = 'USER_ENTRIES_PAUSED'
                elif read_limits(self.db)['revision'] != self.limits_revision:
                    rejection = 'LIMITS_CHANGED_BEFORE_SEND'
                elif rejection is None and not current_quote(tick, time.time(), 15):
                    rejection = 'QUOTE_EXPIRED_DURING_PREFLIGHT'
            except Exception as exc:
                self.cancel_reserved(bar, model, 'PRE_SEND_GUARD: ' + str(exc))
                raise
            if rejection is not None:
                self.cancel_reserved(bar, model, rejection)
                continue
            self.audit('ORDER_SEND_CALLED', {'bar': bar, 'model': model, 'stop_source': 'ATR',
                        'atr_stop': sl, 'atr_distance': distance,
                        'atr_stop_points': actual_stop_points,
                        'broker_min_stop_points': minimum_points, 'risk_cash': risk})
            result = self.sdk.order_send(request)
            value = result._asdict() if result is not None else {'last_error': self.sdk.last_error()}
            status = 'FILLED' if result is not None and result.retcode == self.sdk.TRADE_RETCODE_DONE else 'AMBIGUOUS'
            with self.db:
                self.db.execute('UPDATE attempts SET status=?,result=? WHERE bar=? AND model=?',
                                (status, encoded(value), bar, model))
                self.db.execute('INSERT INTO audit(at,event,payload) VALUES (?,?,?)',
                                (time.time(), 'ORDER_RESULT', encoded({'bar': bar, 'status': status, 'result': value})))
            if status != 'FILLED':
                raise RuntimeError('BROKER_RESULT_NOT_CONFIRMED_NO_RETRY')
            self.audit('BROKER_ENTRY_CONFIRMED', {'model': model, 'risk_reserved': risk,
                        'stop_source': 'ATR', 'atr_stop': sl, 'atr_distance': distance,
                        'atr_stop_points': actual_stop_points, 'risk_cash': risk,
                        'entry': price, 'request': request, 'result': value})

    def publish(self, snap=None, error=None):
        rows = self.db.execute('SELECT reason,COUNT(*) FROM signals GROUP BY reason').fetchall()
        status = {'utc': datetime.now(UTC).isoformat(), 'mode': 'READ_ONLY' if error else 'DEMO_LIVE',
                  'error': error, 'account': self.c['account_login'], 'models': 58, 'symbol': 'EURUSD',
                  'timeframe': self.c['timeframe'], 'profile': self.c['profile'],
                  'daily_profit_target': self.c['daily_profit_amount'],
                  'daily_loss_limit': self.c['daily_loss_amount'],
                  'max_trade_risk_percent': self.c['max_trade_risk_percent'],
                  'max_exposure_amount': self.c['max_exposure_amount'],
                  'multiple_entries': True, 'data_status': self.get('data_status'),
                  'max_open_positions': MAX_OPEN_POSITIONS,
                  'volume_cap': self.c['volume'], 'expires_at': self.c['expires_at'],
                  'limits_revision': self.limits_revision,
                  'per_trade_profit_amount': self.c.get('per_trade_profit_amount', 0),
                  'per_trade_loss_amount': self.c.get('per_trade_loss_amount', 0),
                  'kill_drawdown_percent': self.c['kill_drawdown_percent'],
                  'entries_paused': bool(self.get('user_paused')),
                  'market_state': self.get('market_state'),
                  'signals_by_reason': dict(rows), 'closed_observation_hours': (time.time()-self.started)/3600,
                  'submitted': self.db.execute('SELECT COUNT(*) FROM attempts').fetchone()[0],
                  'filled': self.db.execute("SELECT COUNT(*) FROM attempts WHERE status='FILLED'").fetchone()[0]}
        if snap:
            status.update(balance=snap['account'].balance, equity=snap['equity'],
                          open_positions=len(snap['positions']), floating_pnl=snap['account'].profit,
                          daily_loss=snap['daily_loss'], daily_profit=snap['daily_profit'],
                          target_halt=snap['target_halt'], daily_halt=snap['daily_halt'],
                          exposure=snap['exposure'], drawdown_percent=snap['drawdown_percent'])
            status['positions'] = [dict(p._asdict()) for p in snap['positions']]
            status['pending_orders'] = len(snap.get('orders', ()))
        hour = int(time.time()//3600)
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO state VALUES ('published_status',?)", (encoded(status),))
            self.db.execute('INSERT OR REPLACE INTO hourly VALUES (?,?)', (hour, encoded(status)))
        warning = mirror_status(self.directory, status)
        if warning != self.get('status_mirror_warning'):
            self.set('status_mirror_warning', warning)
            self.audit('STATUS_MIRROR_WARNING' if warning else 'STATUS_MIRROR_RECOVERED',
                       {'error': warning, 'authoritative_status': 'SQLite state.published_status'})
        return status


def run_cycle(service):
    """Wait for missing market data, while all authorization/safety errors remain fatal."""
    service.desktop_guard()
    try:
        snapshot = service.snapshot()
        service.analyze_and_send(snapshot)
        snapshot = service.snapshot()
    except MarketClosed as exc:
        reason = str(exc)
        service.set('data_status', 'WAITING_MARKET')
        if service.get('market_wait_reason') != reason:
            service.set('market_wait_reason', reason)
            service.audit('MARKET_CLOSED_WAIT_NO_EVALUATION', {
                'reason': reason, 'candidate_evaluation': False, 'order_send': False})
        return service.publish()
    except MarketDataUnavailable as exc:
        reason = str(exc)
        if reason == 'WAITING_AUTHORIZATION':
            status = 'WAITING_AUTHORIZATION'
        elif reason == 'PERMISSION_CONFIRMATION_PENDING':
            status = 'WAITING_PERMISSION_CONFIRMATION'
        elif reason.startswith('MT5_CALL_FAILED:'):
            status = 'WAITING_MARKET'
        else:
            status = 'WAITING_FOR_MARKET_DATA'
        service.set('data_status', status)
        if service.get('market_data_wait_reason') != reason:
            service.set('market_data_wait_reason', reason)
            service.audit('MARKET_DATA_WAIT_NO_SEND', {'reason': reason})
        return service.publish(error=reason)
    if service.get('market_data_wait_reason') is not None:
        service.set('market_data_wait_reason', None)
        service.audit('MARKET_DATA_RECOVERED', {'authorization_renewed': False})
    return service.publish(snapshot)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    args = parser.parse_args()
    import msvcrt

    import MetaTrader5 as mt5
    args.config.parent.mkdir(parents=True, exist_ok=True)
    lock = (args.config.parent / 'service.lock').open('a+b')
    lock.seek(0); lock.write(b'1'); lock.flush(); lock.seek(0)
    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    authority_lease = ExecutionAuthorityLease(
        authority_lock_path(args.config.parent.parent), owner='demo_live')
    authority_lease.acquire()
    config = json.loads(args.config.read_bytes())
    if not mt5.initialize(config['terminal_executable']):
        raise RuntimeError('MT5_INITIALIZE_FAILED: ' + str(mt5.last_error()))
    service = None
    try:
        service = Service(mt5, args.config)
        (args.config.parent / 'pid').write_text(str(os.getpid()), encoding='ascii')
        while True:
            try:
                service.renew_demo_authorization_if_due()
            except RuntimeError as exc:
                if str(exc) == 'AUTHORIZATION_RENEWAL_LIMIT_REACHED':
                    raise
                if (str(exc).startswith('DEMO_RENEWAL_') and
                        (time.time() >= service.c['expires_at'] - 600 or
                         service.get('data_status') == 'WAITING_MARKET')):
                    service.set('data_status', 'WAITING_AUTHORIZATION')
                    if service.get('authorization_wait_reason') != str(exc):
                        service.set('authorization_wait_reason', str(exc))
                        service.audit('DEMO_AUTHORIZATION_WAITING_FOR_ALLOWED_RENEWAL', {
                            'reason': str(exc), 'authorization_id': service.c['authorization_id'],
                            'expires_at': service.c['expires_at'], 'demo_only': True})
                    status = service.publish(error=str(exc))
                    print(encoded(status), flush=True)
                    time.sleep(60)
                    continue
                raise
            status = run_cycle(service)
            print(encoded(status), flush=True)
            time.sleep(60 if status.get('data_status') == 'WAITING_MARKET' else 10)
    except Exception as exc:
        if service is not None:
            service.set('halt', str(exc)); service.audit('EXECUTION_HALTED', {'reason': str(exc)})
            print(encoded(service.publish(error=str(exc))), flush=True)
        else:
            print(encoded({'mode': 'READ_ONLY', 'error': str(exc)}), flush=True)
        raise
    finally:
        authority_lease.release()
        mt5.shutdown()
        lock.close()


if __name__ == '__main__':
    main()
