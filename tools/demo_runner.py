"""Read-only DEMO observer and optional launcher of the existing READ_ONLY app.

No order submission, activation, learning promotion or entry-rule modification.
Every broker observation and cost correction is append-only and account-bound.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sqlite3
import subprocess
import sys
import time
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from nexus.broker import plain
from nexus.risk import MAGIC, comment_for
from nexus.store import account_key


class DemoOnlyError(RuntimeError):
    """No real, contest, unknown or switched account can enter the journal."""


def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def digest(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


def finite(value, default=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return default
    return float(value)


def require_demo(account, terminal):
    if type(account.get('trade_mode')) is not int or account['trade_mode'] != 0:
        raise DemoOnlyError('DEMO required: Real, Contest and unknown accounts rejected')
    if terminal.get('connected') is not True:
        raise DemoOnlyError('MT5 terminal disconnected')
    if not account.get('currency'):
        raise DemoOnlyError('Account currency unavailable')
    value = dict(account)
    value['platform_id'] = os.path.normcase(os.path.abspath(terminal.get('path', '')))
    if not terminal.get('path'):
        raise DemoOnlyError('Terminal identity unavailable')
    return account_key(value)


def read_nexus_intents(path, key):
    """Read only; never instantiate Store because its constructor creates tables."""
    if not path or not Path(path).is_file():
        return [], 'NEXUS_LEDGER_NOT_FOUND'
    try:
        with closing(sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True, timeout=2)) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("SELECT * FROM intents WHERE account_key=? AND kind='ENTRY'", (key,)).fetchall()
        result = []
        for row in rows:
            intent = dict(row)
            intent['payload'] = json.loads(intent['payload'])
            result.append(intent)
        return result, 'READ_ONLY_LEDGER_MATCH'
    except (sqlite3.Error, ValueError, TypeError):
        return [], 'NEXUS_LEDGER_UNAVAILABLE_OR_INVALID'


def match_intent(position_id, deals, intents):
    matches = []
    entering = [d for d in deals if d.get('entry') == 0 and d.get('type') in (0, 1)]
    for intent in intents:
        payload = intent.get('payload', {})
        request = payload.get('request', {})
        result = payload.get('result') or {}
        # A position identifier alone is not proof of NEXUS ownership. Require
        # matching symbol and magic plus exact comment or original order/deal.
        proofs = [d for d in entering if d.get('magic') == MAGIC and d.get('symbol') == request.get('symbol')
                  and (d.get('comment') == comment_for(intent['id']) or
                       (result.get('order') not in (None, 0) and d.get('order') == result['order']) or
                       (result.get('deal') not in (None, 0) and d.get('ticket') == result['deal']))]
        if proofs and (position_id in payload.get('position_ids', []) or
                       any(d.get('position_id') == position_id for d in proofs)):
            matches.append(intent)
    return matches[0] if len(matches) == 1 else None, sorted(intent['id'] for intent in matches)


def initial_risk_evidence(position_id, deals, orders, intent, account, adapter):
    """Actual fills + proven original SL; never use a position's current stop.

    Cash reconstruction is limited to matching profit/account currency to avoid
    pretending that today's FX conversion proves historical cash risk.
    """
    entering = [d for d in deals if d.get('entry') == 0 and d.get('type') in (0, 1)]
    unknown = {'initial_risk_cash': None, 'initial_sl': None, 'basis': 'UNKNOWN_INITIAL_RISK',
               'reason': 'Original initial stop/cash-risk evidence unavailable', 'opening_volume': None}
    if not entering or any(d.get('entry') == 2 for d in deals):
        return {**unknown, 'reason': 'Missing entry history or position reversal'}
    order_ids = {d.get('order') for d in entering}
    sides = {d['type'] for d in entering}
    if len(order_ids) != 1 or None in order_ids or 0 in order_ids or len(sides) != 1:
        return {**unknown, 'reason': 'Multiple opening orders/scale-ins have no single initial risk denominator'}
    initial_order = next((o for o in orders if o.get('ticket') in order_ids), None)
    request = (intent or {}).get('payload', {}).get('request', {})
    if (request and initial_order and finite(initial_order.get('sl'), 0) > 0 and
            abs(float(request.get('sl', 0)) - float(initial_order['sl'])) > 1e-9):
        return {**unknown, 'reason': 'Ledger initial stop and historical initial order disagree'}
    stop = finite(request.get('sl')) if request else finite((initial_order or {}).get('sl'))
    if stop is None or stop <= 0:
        return unknown
    symbol = entering[0].get('symbol')
    info = adapter.symbol_info(symbol)
    if not info or info.get('currency_profit') != account.get('currency'):
        return {**unknown, 'reason': 'Historical account-currency conversion not proven'}
    volume = sum(finite(d.get('volume'), 0) for d in entering)
    side = 'BUY' if entering[0]['type'] == 0 else 'SELL'
    if volume <= 0:
        return unknown
    cash = 0.
    for deal in entering:
        entry = finite(deal.get('price'))
        if entry is None or (side == 'BUY' and stop >= entry) or (side == 'SELL' and stop <= entry):
            return {**unknown, 'reason': 'Original stop is not a losing protective bracket'}
        value = finite(adapter.calc_profit(side, symbol, deal['volume'], entry, stop))
        if value is None or value >= 0:
            return {**unknown, 'reason': 'Initial filled-stop cash risk unavailable'}
        cash -= value
    return {'initial_risk_cash': cash, 'initial_sl': stop,
            'basis': 'FILLED_INITIAL_STOP_SAME_CURRENCY_RECONSTRUCTION',
            'reason': 'Actual opening fills + original entry request/order SL; no current position SL',
            'opening_volume': volume, 'opening_order_ids': sorted(order_ids),
            'source': 'NEXUS_INITIAL_ENTRY_REQUEST' if request else 'BROKER_ORIGINAL_ORDER',
            'currency': account['currency'], 'symbol': symbol,
            'contract_observation': {k: info.get(k) for k in ('currency_profit', 'trade_contract_size', 'trade_calc_mode')},
            'limitation': 'Broker calculation reconstructed with observed contract; no historical conversion or guaranteed stop fill'}


class MT5ReadOnlyAdapter:
    """The observer intentionally exposes no send/check/activate method."""
    def __init__(self, terminal_path=''):
        import MetaTrader5 as mt5
        self.mt5 = mt5
        if not mt5.initialize(*([terminal_path] if terminal_path else []), timeout=10000):
            raise RuntimeError('MT5 initialize failed: ' + str(mt5.last_error()))

    def call(self, name, *args):
        value = getattr(self.mt5, name)(*args)
        if value is None:
            raise RuntimeError(name + ': ' + str(self.mt5.last_error()))
        return plain(value)

    def account(self):
        return self.call('account_info')

    def terminal(self):
        return self.call('terminal_info')

    def positions(self):
        return self.call('positions_get')

    def deals(self, since, until):
        return self.call('history_deals_get', datetime.fromtimestamp(since, UTC), datetime.fromtimestamp(until, UTC))

    def orders(self, since, until):
        return self.call('history_orders_get', datetime.fromtimestamp(since, UTC), datetime.fromtimestamp(until, UTC))

    def symbol_info(self, symbol):
        return self.call('symbol_info', symbol)

    def calc_profit(self, side, symbol, volume, entry, stop):
        return self.call('order_calc_profit', 0 if side == 'BUY' else 1, symbol, volume, entry, stop)

    def close(self):
        self.mt5.shutdown()


class DemoJournal:
    def __init__(self, path):
        self.path = Path(path)

    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA synchronous=FULL')
        db.executescript('''
            CREATE TABLE IF NOT EXISTS observations(
                account_key TEXT, kind TEXT, record_id TEXT, version INTEGER,
                at REAL, sha TEXT, payload TEXT,
                PRIMARY KEY(account_key,kind,record_id,version));
            CREATE TABLE IF NOT EXISTS initial_risk(
                account_key TEXT, position_id TEXT, at REAL, payload TEXT,
                PRIMARY KEY(account_key,position_id));
            CREATE TABLE IF NOT EXISTS audit(
                sequence INTEGER PRIMARY KEY AUTOINCREMENT, at REAL, account_key TEXT,
                event TEXT, payload TEXT);
            CREATE VIEW IF NOT EXISTS trades AS
                SELECT o.account_key,o.record_id AS position_id,o.version,o.at,o.payload
                FROM observations o WHERE o.kind='TRADE' AND o.version=(
                    SELECT MAX(p.version) FROM observations p
                    WHERE p.account_key=o.account_key AND p.kind=o.kind AND p.record_id=o.record_id);
        ''')
        return db

    @staticmethod
    def _append(db, key, kind, record_id, payload, at):
        row = db.execute('SELECT version,sha FROM observations WHERE account_key=? AND kind=? AND record_id=? ORDER BY version DESC LIMIT 1',
                         (key, kind, str(record_id))).fetchone()
        if row and row['sha'] == digest(payload):
            return 0
        version = (row['version'] if row else 0) + 1
        changed = db.execute('INSERT INTO observations VALUES(?,?,?,?,?,?,?)',
                             (key, kind, str(record_id), version, at, digest(payload), encode(payload))).rowcount
        if changed:
            db.execute('INSERT INTO audit(at,account_key,event,payload) VALUES(?,?,?,?)',
                       (at, key, kind + '_OBSERVED', encode({'record_id': str(record_id), 'version': version, 'sha': digest(payload)})))
        return changed

    @staticmethod
    def _latest(db, key, kind):
        return [json.loads(row['payload']) for row in db.execute('''
            SELECT o.payload FROM observations o WHERE account_key=? AND kind=?
            AND version=(SELECT MAX(p.version) FROM observations p
              WHERE p.account_key=o.account_key AND p.kind=o.kind AND p.record_id=o.record_id)
        ''', (key, kind))]

    def ingest(self, snapshot, adapter, intents=(), ledger_status='NOT_SUPPLIED'):
        key = require_demo(snapshot['account'], snapshot['terminal'])
        if key != require_demo(snapshot['account_after'], snapshot['terminal_after']):
            raise DemoOnlyError('Account/terminal switched during observation; nothing written')
        at = snapshot['at']
        with closing(self._connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            try:
                changed = 0
                for kind, rows, field in (('DEAL', snapshot['deals'], 'ticket'),
                                          ('ORDER', snapshot['orders'], 'ticket'),
                                          ('POSITION', snapshot['positions'], 'identifier')):
                    for row in rows:
                        identity = row.get(field, row.get('ticket'))
                        if identity in (None, 0):
                            raise ValueError('Broker record has no durable identity')
                        changed += self._append(db, key, kind, identity, row, at)
                deals = self._latest(db, key, 'DEAL')
                orders = self._latest(db, key, 'ORDER')
                position_ids = {str(d['position_id']) for d in deals if d.get('position_id') not in (None, 0)}
                position_ids.update(str(p.get('identifier', p['ticket'])) for p in snapshot['positions'])
                for position_id in sorted(position_ids):
                    related = [d for d in deals if str(d.get('position_id')) == position_id]
                    intent, owner_ids = match_intent(int(position_id), related, intents)
                    owners = len(owner_ids)
                    if intent:
                        changed += self._append(db, key, 'SIGNAL', position_id, intent, at)
                    captured = db.execute('SELECT payload FROM initial_risk WHERE account_key=? AND position_id=?',
                                          (key, position_id)).fetchone()
                    if captured:
                        risk = json.loads(captured['payload'])
                    else:
                        risk = initial_risk_evidence(int(position_id), related, orders, intent, snapshot['account'], adapter)
                        db.execute('INSERT INTO initial_risk VALUES(?,?,?,?)', (key, position_id, at, encode(risk)))
                        db.execute('INSERT INTO audit(at,account_key,event,payload) VALUES(?,?,?,?)',
                                   (at, key, 'INITIAL_RISK_CAPTURED', encode({'position_id': position_id, **risk})))
                    original_signals = db.execute("SELECT payload FROM observations WHERE account_key=? AND kind='SIGNAL' AND record_id=? ORDER BY version LIMIT 1",
                                                  (key, position_id)).fetchone()
                    original_signal = json.loads(original_signals['payload']) if original_signals else None
                    previous_owner = (original_signal or {}).get('id')
                    conflict = owners > 1 or (owners == 1 and previous_owner not in (None, owner_ids[0]))
                    ownership = {'matching_intent_ids': owner_ids, 'matching_count': owners,
                                 'original_intent_id': previous_owner, 'conflict': conflict,
                                 'source': 'READ_ONLY_NEXUS_ENTRY_LEDGER', 'ledger_status': ledger_status}
                    owner_change = self._append(db, key, 'OWNERSHIP', position_id, ownership, at)
                    changed += owner_change
                    if conflict and owner_change:
                        db.execute('INSERT INTO audit(at,account_key,event,payload) VALUES(?,?,?,?)',
                                   (at, key, 'OWNERSHIP_CONFLICT', encode({'position_id': position_id, **ownership})))
                    projection = project_trade(position_id, related, snapshot['positions'], original_signal,
                                               risk, ownership, snapshot['account']['currency'])
                    changed += self._append(db, key, 'TRADE', position_id, projection, at)
                # Validate the broker's identity again immediately before COMMIT,
                # including read-only risk conversion calls performed above.
                if key != require_demo(adapter.account(), adapter.terminal()):
                    raise DemoOnlyError('Account switched before journal commit; transaction rolled back')
                db.commit()
            except BaseException:
                db.rollback()
                raise
            count = db.execute('SELECT COUNT(*) FROM trades WHERE account_key=?', (key,)).fetchone()[0]
        return {'mode': 'DEMO_OBSERVER_READ_ONLY', 'account_fingerprint': hashlib.sha256(key.encode()).hexdigest(),
                'changed_records': changed, 'tracked_positions': count, 'ledger_status': ledger_status,
                'database': str(self.path.resolve()), 'orders_sent': 0, 'execution_authority': False}


def project_trade(position_id, deals, positions, intent, risk, ownership, currency):
    entering = [d for d in deals if d.get('type') in (0, 1) and d.get('entry') == 0]
    exiting = [d for d in deals if d.get('type') in (0, 1) and d.get('entry') in (1, 3)]
    entry_volume = sum(finite(d.get('volume'), 0) for d in entering)
    exit_volume = sum(finite(d.get('volume'), 0) for d in exiting)
    current = [p for p in positions if str(p.get('identifier', p.get('ticket'))) == position_id]
    simple = not any(d.get('entry') == 2 for d in deals)
    closed = bool(not current and entering and exiting and simple and abs(entry_volume - exit_volume) <= 1e-8)
    status = 'CLOSED' if closed else 'OPEN' if current else 'INCOMPLETE_OR_COMPLEX_HISTORY'
    totals = {key: sum(finite(d.get(key), 0) for d in deals) for key in ('profit', 'commission', 'swap', 'fee')}
    net = math.fsum(totals.values())
    costs_complete = all(all(finite(d.get(field)) is not None for field in totals) for d in deals)
    risk_matches = risk.get('opening_volume') is not None and abs(risk['opening_volume'] - entry_volume) < 1e-8
    known_risk = finite(risk.get('initial_risk_cash'))
    r = net / known_risk if closed and costs_complete and risk_matches and known_risk and known_risk > 0 else None
    proposal = (intent or {}).get('payload', {}).get('proposal')
    if ownership['conflict']:
        signal_status = 'AMBIGUOUS'
    elif intent and ownership['matching_count'] == 1:
        signal_status = 'MATCHED_NEXUS'
    elif intent:
        signal_status = 'CAPTURED_NEXUS_CURRENT_UNCONFIRMED'
    else:
        signal_status = 'EXTERNAL_UNMATCHED'
    weighted = lambda rows, volume: sum(d['price'] * d['volume'] for d in rows) / volume if volume > 0 else None
    return {'position_id': position_id, 'symbol': (entering or exiting or current or [{}])[0].get('symbol'),
            'side': 'BUY' if entering and entering[0]['type'] == 0 else 'SELL' if entering else None,
            'status': status, 'signal_status': signal_status, 'current_ownership': ownership,
            'ownership_confirmed': signal_status == 'MATCHED_NEXUS',
            'eligible_for_strategy_evaluation': bool(signal_status == 'MATCHED_NEXUS' and closed and costs_complete and r is not None),
            'evaluation_eligibility_scope': 'ROW_COMPLETENESS_ONLY; not a strategy, learning or execution qualification',
            'qualified': False, 'execution_authority': False,
            'signal': proposal, 'intent_id': (intent or {}).get('id'),
            'regime': (proposal or {}).get('market_regime', 'UNKNOWN'),
            'entry': {'time': min((d['time'] for d in entering), default=None), 'price': weighted(entering, entry_volume), 'volume': entry_volume},
            'exit': {'time': max((d['time'] for d in exiting), default=None), 'price': weighted(exiting, exit_volume), 'volume': exit_volume},
            'profit_costs': totals, 'net_cash': net, 'currency': currency, 'cost_fields_complete': costs_complete,
            'cash_scope': 'POSITION_LINKED_DEALS_ONLY; unallocated account-level fees not assigned',
            'initial_risk': risk, 'R': r,
            'R_unavailable_reason': None if r is not None else 'Not fully closed, incomplete costs/history or initial filled risk unproven/changed volume',
            'planned_risk_cash': (intent or {}).get('payload', {}).get('original_risk'),
            'deal_tickets': sorted(d['ticket'] for d in deals),
            'limitations': ['Closed cash includes observed deal profit/commission/swap/fee; later corrections append a new version.',
                            'Unallocated account-level charges remain separate observations, not guessed per-position costs.',
                            'R uses only immutable initial filled-stop evidence; current trailed SL is never a denominator.']}


def observe_once(adapter, path, *, ledger=None, since=0., now=None, expected_account_key=None):
    now = time.time() if now is None else now
    before, terminal = adapter.account(), adapter.terminal()
    key = require_demo(before, terminal)
    if expected_account_key is not None and key != expected_account_key:
        raise DemoOnlyError('Observed account differs from the pinned DEMO session')
    snapshot = {'at': now, 'account': before, 'terminal': terminal,
                'positions': adapter.positions(), 'deals': adapter.deals(since, now),
                'orders': adapter.orders(since, now), 'account_after': adapter.account(),
                'terminal_after': adapter.terminal()}
    if key != require_demo(snapshot['account_after'], snapshot['terminal_after']):
        raise DemoOnlyError('Account changed during read-only snapshot')
    intents, status = read_nexus_intents(ledger, key)
    return DemoJournal(path).ingest(snapshot, adapter, intents, status)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, default=ROOT / 'data/demo/trades.db')
    parser.add_argument('--ledger', type=Path, default=Path(os.environ.get('LOCALAPPDATA', str(ROOT))) / 'NEXUS/live.sqlite3')
    parser.add_argument('--terminal-path', default='')
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--poll-seconds', type=float, default=5.)
    parser.add_argument('--history-days', type=int, default=90)
    parser.add_argument('--launch-app', action='store_true', help='Launch existing lock-protected app in its default READ_ONLY state; never activates trading')
    args = parser.parse_args()
    if not math.isfinite(args.poll_seconds) or args.poll_seconds < 1 or not 1 <= args.history_days <= 3650:
        parser.error('poll-seconds >=1 and history-days 1..3650 required')
    adapter = MT5ReadOnlyAdapter(args.terminal_path)
    try:
        expected_key = require_demo(adapter.account(), adapter.terminal())
        if args.launch_app:
            # Existing application always launches READ_ONLY and enforces its
            # own single-instance lock. No activation argument exists here.
            environment = dict(os.environ)
            environment['PYTHONPATH'] = str(ROOT / 'src') + os.pathsep + environment.get('PYTHONPATH', '')
            subprocess.Popen([sys.executable, '-m', 'nexus.app'], cwd=ROOT, env=environment,
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        while True:
            result = observe_once(adapter, args.db, ledger=args.ledger,
                                  since=time.time() - args.history_days * 86400,
                                  expected_account_key=expected_key)
            print(json.dumps(result, ensure_ascii=False), flush=True)
            if args.once:
                break
            time.sleep(args.poll_seconds)
    finally:
        adapter.close()


if __name__ == '__main__':
    main()
