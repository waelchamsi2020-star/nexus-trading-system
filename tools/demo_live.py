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
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
from nexus.strategies import REGISTRY, analyze_all, atr
from tools.demo_limits import initialize as initialize_limits
from tools.demo_limits import read as read_limits


class MarketDataUnavailable(RuntimeError):
    """Transient observation failure; blocks entries without renewing authority."""


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
    """A broker quote must be finite, executable and neither future nor stale."""
    if quote is None:
        return False
    try:
        age = finite(as_of) - finite(quote.time)
        bid, ask = finite(quote.bid), finite(quote.ask)
    except (AttributeError, TypeError, ValueError):
        return False
    return 0 <= age <= max_age and 0 < bid <= ask


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


def repeated_opportunity(positions, requests, side, symbol='EURUSD', magic=20261019):
    """Different models do not make same-direction exposure an independent opportunity."""
    return (any(p.symbol == symbol and p.magic == magic and p.type == side for p in positions)
            or any(r.get('symbol') == symbol and r.get('type') == side for r in requests))


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
                    'slippage_points': 10, 'commission_reserve_per_lot': 7.}
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
        initialize_limits(self.db, self.c)
        self.limits_revision = -1
        self.account = self.guard()
        old = self.get('identity')
        identity = [self.account.login, self.account.server, self.sdk.terminal_info().path]
        if old is not None and old != identity:
            raise RuntimeError('JOURNAL_ACCOUNT_MISMATCH')
        self.set('identity', identity)
        if self.get('halt'):
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
        if not terminal.trade_allowed or terminal.tradeapi_disabled:
            raise RuntimeError('TERMINAL_ALGORITHMIC_TRADING_DISABLED')
        if not account.trade_allowed or not account.trade_expert:
            raise RuntimeError('DEMO_ACCOUNT_TRADING_PERMISSION_DISABLED')
        if account.currency != 'USD':
            raise RuntimeError('USD_ACCOUNT_REQUIRED_FOR_COST_RESERVE')
        if (self.directory / 'STOP').exists():
            raise RuntimeError('USER_KILL_SWITCH')
        if time.time() >= self.c['expires_at']:
            raise RuntimeError('AUTHORIZATION_24H_EXPIRED')
        if finite(account.equity) <= 0:
            raise RuntimeError('NONPOSITIVE_EQUITY')
        # Wait only after verifying identity, permissions and authorization.
        # Each later cycle repeats all checks before any send.
        if not terminal.connected:
            raise MarketDataUnavailable('MT5_CONNECTION_UNAVAILABLE')
        return account

    def desktop_guard(self):
        # Desktop authorizes only AFTER its durable audit commit. Read that source
        # directly: the large /api/state snapshot can time out during analysis.
        path = Path(self.c['desktop_audit_db']).resolve()
        with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=2) as db:
            authorization = db.execute("SELECT event FROM audit WHERE event IN "
                "('AUTHORIZATION_ACTIVATED','AUTHORIZATION_REVOKED') ORDER BY sequence DESC LIMIT 1").fetchone()
            stop = db.execute("SELECT MAX(at) FROM audit WHERE event='ENTRIES_STOPPED'").fetchone()[0]
        if stop is not None and stop >= self.c['authorized_at']:
            raise RuntimeError('USER_DESKTOP_STOP_ENTRIES')
        if authorization is None or authorization[0] != 'AUTHORIZATION_REVOKED':
            raise RuntimeError('SECOND_EXECUTION_AUTHORITY_DETECTED')

    def snapshot(self):
        current = read_limits(self.db)
        if current['revision'] != self.limits_revision:
            self.c.update(current['values'])
            self.limits_revision = current['revision']
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
        return {'account': account, 'positions': positions, 'equity': finite(account.equity),
                'daily_loss': loss, 'daily_limit': daily_limit, 'day': day, 'exposure': exposure,
                'drawdown_percent': drawdown, 'daily_halt': self.get('daily_halt') in (day, halt_key),
                'daily_profit': daily_profit, 'target_halt': self.get('daily_target_halt') in (day, halt_key)}

    def reject(self, bar, model, reason):
        with self.db:
            self.db.execute('UPDATE signals SET reason=? WHERE bar=? AND model=?', (reason, bar, model))
            self.db.execute('INSERT INTO audit(at,event,payload) VALUES (?,?,?)',
                            (time.time(), 'SIGNAL_REJECTED', encoded({'bar': bar, 'model': model, 'reason': reason})))

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
            sent_this_bar = [json.loads(row[0]) for row in self.db.execute(
                "SELECT request FROM attempts WHERE bar=? AND status IN ('FILLED','SENDING','AMBIGUOUS')",
                (bar,))]
            if repeated_opportunity(snap['positions'], sent_this_bar, side):
                self.reject(bar, model, 'OVERLAPPING_OPPORTUNITY'); continue
            price = finite(tick.ask if side == 0 else tick.bid)
            zone = card['entry']['zone']
            if not finite(zone[0]) <= price <= finite(zone[1]):
                self.reject(bar, model, 'QUOTE_OUTSIDE_MODEL_ENTRY_ZONE'); continue
            distance = finite(atr(bars))
            if distance <= 0:
                raise RuntimeError('INVALID_ATR')
            sign = 1 if side == 0 else -1
            sl = round(price - sign * 1.5 * distance, info.digits)
            tp = round(price + sign * 3 * distance, info.digits)
            if self.c.get('per_trade_profit_amount', 0) > 0:
                unit = info.trade_tick_size or info.point
                one_tick = self.sdk.order_calc_profit(side, 'EURUSD', .01, price, price + sign * unit)
                reserve = self.sdk.order_calc_profit(side, 'EURUSD', .01, price, price - sign * 20 * info.point)
                if one_tick is None or reserve is None:
                    raise RuntimeError('CASH_TARGET_CALCULATION_UNAVAILABLE')
                costs = abs(finite(reserve)) + .01 * 7.
                try:
                    sl, tp = cash_levels(side, price, unit, abs(finite(one_tick)),
                                         self.c['per_trade_loss_amount'],
                                         self.c['per_trade_profit_amount'], costs)
                    sl, tp = round(sl, info.digits), round(tp, info.digits)
                except ValueError:
                    self.reject(bar, model, 'CASH_TARGET_BELOW_COST_RESERVE'); continue
            close_quote = tick.bid if side == 0 else tick.ask
            if min(abs(close_quote - sl), abs(close_quote - tp)) < info.trade_stops_level * info.point:
                self.reject(bar, model, 'BROKER_MIN_STOP_DISTANCE'); continue
            cash = self.sdk.order_calc_profit(side, 'EURUSD', .01, price, sl)
            slip = self.sdk.order_calc_profit(side, 'EURUSD', .01, price, price - sign * 20 * info.point)
            if cash is None or slip is None:
                raise RuntimeError('NEW_POSITION_RISK_UNKNOWN')
            risk = abs(finite(cash)) + abs(finite(slip)) + .01 * 7.
            if self.c.get('per_trade_loss_amount', 0) > 0 and risk > self.c['per_trade_loss_amount'] + 1e-8:
                self.reject(bar, model, 'TRADE_CASH_RISK_LIMIT'); continue
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
            checked = self.sdk.order_check(request)
            if checked is None or checked.retcode != 0:
                self.reject(bar, model, 'ORDER_CHECK: ' + str(checked)); continue
            with self.db:
                self.db.execute('INSERT INTO attempts VALUES (?,?,?,?,?,?)',
                                (bar, time.time(), model, 'SENDING', encoded(request), None,))
                self.db.execute('INSERT INTO audit(at,event,payload) VALUES (?,?,?)',
                                (time.time(), 'SEND_INTENT_RESERVED', encoded({'bar': bar, 'model': model, 'request': request})))
            # No RPC has occurred. Guard/preflight failures must not be recorded
            # as an ambiguous broker send. Never include order_send in this block.
            try:
                self.desktop_guard()
                self.guard()
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
            self.audit('BROKER_ENTRY_CONFIRMED', {'model': model, 'risk_reserved': risk, 'result': value})

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
                  'volume_cap': self.c['volume'], 'expires_at': self.c['expires_at'],
                  'limits_revision': self.limits_revision,
                  'per_trade_profit_amount': self.c.get('per_trade_profit_amount', 0),
                  'per_trade_loss_amount': self.c.get('per_trade_loss_amount', 0),
                  'kill_drawdown_percent': self.c['kill_drawdown_percent'],
                  'entries_paused': bool(self.get('user_paused')),
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
    except MarketDataUnavailable as exc:
        reason = str(exc)
        service.set('data_status', 'WAITING_FOR_MARKET_DATA')
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
    config = json.loads(args.config.read_bytes())
    if not mt5.initialize(config['terminal_executable']):
        raise RuntimeError('MT5_INITIALIZE_FAILED: ' + str(mt5.last_error()))
    service = None
    try:
        service = Service(mt5, args.config)
        (args.config.parent / 'pid').write_text(str(os.getpid()), encoding='ascii')
        while True:
            print(encoded(run_cycle(service)), flush=True)
            time.sleep(10)
    except Exception as exc:
        if service is not None:
            service.set('halt', str(exc)); service.audit('EXECUTION_HALTED', {'reason': str(exc)})
            print(encoded(service.publish(error=str(exc))), flush=True)
        else:
            print(encoded({'mode': 'READ_ONLY', 'error': str(exc)}), flush=True)
        raise
    finally:
        mt5.shutdown()
        lock.close()


if __name__ == '__main__':
    main()
