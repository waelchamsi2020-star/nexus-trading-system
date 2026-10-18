"""Synthetic journal fixtures only; no broker calls or financial edge claim."""
import copy
import importlib.util
import json
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from nexus.risk import MAGIC, comment_for

_file = Path(__file__).resolve().parents[1] / 'tools/demo_runner.py'
_spec = importlib.util.spec_from_file_location('demo_runner_fixture', _file)
runner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(runner)


class FakeReadOnlyBroker:
    def __init__(self):
        self.info = {'login': 123, 'server': 'Fixture-Demo', 'currency': 'USD', 'trade_mode': 0}
        self.term = {'path': str(Path.cwd()), 'connected': True}
        self.iid = 'a' * 64
        common = {'position_id': 200, 'symbol': 'EURUSD', 'magic': MAGIC,
                  'comment': comment_for(self.iid), 'commission': -1., 'swap': 0., 'fee': 0.}
        self.rows = [{**common, 'ticket': 1, 'order': 100, 'entry': 0, 'type': 0,
                      'price': 1.1000, 'volume': .1, 'time': 1000, 'profit': 0.},
                     {**common, 'ticket': 2, 'order': 101, 'entry': 1, 'type': 1,
                      'price': 1.1020, 'volume': .1, 'time': 1100, 'profit': 20.}]
        self.book = []
        self.order_rows = [{'ticket': 100, 'position_id': 200, 'symbol': 'EURUSD', 'sl': 1.0990}]
        self.calc_calls = []
        self.account_reads = 0
        self.switch_on_read = None

    def account(self):
        self.account_reads += 1
        result = copy.deepcopy(self.info)
        if self.switch_on_read == self.account_reads:
            result['trade_mode'] = 2
        return result

    def terminal(self):
        return copy.deepcopy(self.term)

    def positions(self):
        return copy.deepcopy(self.book)

    def deals(self, since, until):
        return copy.deepcopy(self.rows)

    def orders(self, since, until):
        return copy.deepcopy(self.order_rows)

    def symbol_info(self, symbol):
        return {'currency_profit': 'USD', 'trade_contract_size': 100000, 'trade_calc_mode': 0}

    def calc_profit(self, side, symbol, volume, entry, stop):
        self.calc_calls.append((side, symbol, volume, entry, stop))
        return (stop - entry) * volume * 100000 * (1 if side == 'BUY' else -1)


class DemoRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / 'demo' / 'trades.db'
        self.broker = FakeReadOnlyBroker()
        self.key = runner.require_demo(self.broker.info, self.broker.term)
        self.intent = {'id': self.broker.iid, 'account_key': self.key, 'kind': 'ENTRY',
                       'payload': {'position_ids': [200], 'result': {'order': 100, 'deal': 1},
                                   'request': {'symbol': 'EURUSD', 'sl': 1.0990},
                                   'original_risk': 13.,
                                   'proposal': {'id': 'actual-proposal-fixture', 'side': 'BUY',
                                                'strategy_id': 'support_bounce', 'market_regime': 'RANGE'}}}
        self.ledger = Path(self.temp.name) / 'nexus-live.sqlite3'
        with closing(sqlite3.connect(self.ledger)) as db, db:
            db.execute('CREATE TABLE intents(id TEXT,account_key TEXT,kind TEXT,payload TEXT)')
            db.execute('INSERT INTO intents VALUES(?,?,?,?)',
                       (self.intent['id'], self.key, 'ENTRY', json.dumps(self.intent['payload'])))

    def poll(self):
        return runner.observe_once(self.broker, self.db, ledger=self.ledger, since=0, now=1200.)

    def trade(self, key=None):
        with closing(sqlite3.connect(self.db)) as db, db:
            row = db.execute('SELECT payload FROM trades WHERE account_key=?', (key or self.key,)).fetchone()
        return json.loads(row[0])

    def test_closed_fixture_has_actual_signal_entry_exit_regime_cash_and_known_R(self):
        result = self.poll()
        trade = self.trade()
        self.assertEqual(0, result['orders_sent'])
        self.assertEqual('CLOSED', trade['status'])
        self.assertEqual(self.intent['payload']['proposal'], trade['signal'])
        self.assertEqual('RANGE', trade['regime'])
        self.assertEqual(1.1, trade['entry']['price'])
        self.assertEqual(1.102, trade['exit']['price'])
        self.assertEqual(18., trade['net_cash'])
        self.assertAlmostEqual(10., trade['initial_risk']['initial_risk_cash'])
        self.assertAlmostEqual(1.8, trade['R'])
        self.assertEqual(13., trade['planned_risk_cash'])
        self.assertTrue(trade['ownership_confirmed'])
        self.assertTrue(trade['eligible_for_strategy_evaluation'])
        self.assertFalse(trade['qualified'])
        self.assertFalse(trade['execution_authority'])

    def test_unique_owner_does_not_make_open_unknown_risk_or_incomplete_costs_evaluable(self):
        self.broker.rows = self.broker.rows[:1]
        self.broker.book = [{'identifier': 200, 'ticket': 200, 'symbol': 'EURUSD', 'sl': 1.0990}]
        self.poll()
        self.assertTrue(self.trade()['ownership_confirmed'])
        self.assertFalse(self.trade()['eligible_for_strategy_evaluation'])
        self.broker.rows.append({'position_id': 200, 'symbol': 'EURUSD', 'magic': MAGIC,
                                'ticket': 2, 'order': 101, 'entry': 1, 'type': 1,
                                'price': 1.1020, 'volume': .1, 'time': 1100, 'profit': 20.,
                                'commission': -1., 'swap': 0.})
        self.broker.book = []
        self.poll()
        self.assertEqual('CLOSED', self.trade()['status'])
        self.assertTrue(self.trade()['ownership_confirmed'])
        self.assertFalse(self.trade()['cost_fields_complete'])
        self.assertFalse(self.trade()['eligible_for_strategy_evaluation'])
        self.assertIsNone(self.trade()['R'])

    def test_real_contest_unknown_disconnected_accounts_create_no_database(self):
        for mode in (1, 2, None, True, '0'):
            with self.subTest(mode=mode):
                self.broker.info['trade_mode'] = mode
                with self.assertRaises(runner.DemoOnlyError):
                    self.poll()
                self.assertFalse(self.db.exists())
        self.broker.info['trade_mode'] = 0
        self.broker.term['connected'] = False
        with self.assertRaises(runner.DemoOnlyError):
            self.poll()
        self.assertFalse(self.db.exists())

    def test_account_switch_during_snapshot_or_before_commit_never_writes_records(self):
        self.broker.switch_on_read = 2
        with self.assertRaises(runner.DemoOnlyError):
            self.poll()
        self.assertFalse(self.db.exists())
        self.broker.account_reads = 0
        self.broker.switch_on_read = 3
        with self.assertRaises(runner.DemoOnlyError):
            self.poll()
        with closing(sqlite3.connect(self.db)) as db, db:
            self.assertEqual(0, db.execute('SELECT COUNT(*) FROM observations').fetchone()[0])
            self.assertEqual(0, db.execute('SELECT COUNT(*) FROM initial_risk').fetchone()[0])
            self.assertEqual(0, db.execute('SELECT COUNT(*) FROM audit').fetchone()[0])

    def test_duplicate_poll_is_idempotent_and_every_new_observation_has_audit(self):
        self.poll()
        with closing(sqlite3.connect(self.db)) as db, db:
            before = [db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]
                      for table in ('observations', 'audit', 'initial_risk')]
        self.assertEqual(0, self.poll()['changed_records'])
        with closing(sqlite3.connect(self.db)) as db, db:
            after = [db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]
                     for table in ('observations', 'audit', 'initial_risk')]
        self.assertEqual(before, after)
        self.assertEqual(before[0] + before[2], before[1])

    def test_same_position_ticket_on_another_server_is_separate(self):
        self.poll()
        self.broker.info['server'] = 'Other-Fixture-Demo'
        other_key = runner.require_demo(self.broker.info, self.broker.term)
        self.poll()
        with closing(sqlite3.connect(self.db)) as db, db:
            self.assertEqual(2, db.execute('SELECT COUNT(*) FROM trades').fetchone()[0])
        self.assertEqual('MATCHED_NEXUS', self.trade()['signal_status'])
        self.assertEqual('EXTERNAL_UNMATCHED', self.trade(other_key)['signal_status'])
        self.assertIsNone(self.trade(other_key)['signal'])

    def test_running_session_rejects_a_different_demo_account(self):
        self.broker.info['login'] = 456
        with self.assertRaises(runner.DemoOnlyError):
            runner.observe_once(self.broker, self.db, expected_account_key=self.key)
        self.assertFalse(self.db.exists())

    def test_broker_failure_mid_capture_rolls_back_all_observations_and_audit(self):
        with (patch.object(self.broker, 'calc_profit', side_effect=RuntimeError('injected risk conversion outage')),
              self.assertRaises(RuntimeError)):
            self.poll()
        with closing(sqlite3.connect(self.db)) as db, db:
            for table in ('observations', 'initial_risk', 'audit'):
                self.assertEqual(0, db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0])

    def test_concurrent_duplicate_observers_do_not_duplicate_rows(self):
        self.poll()  # Schema creation is not the transaction under test.
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.poll(), range(2)))
        self.assertEqual([0, 0], [row['changed_records'] for row in results])
        with closing(sqlite3.connect(self.db)) as db, db:
            self.assertEqual(1, db.execute('SELECT COUNT(*) FROM trades').fetchone()[0])
            self.assertEqual(1, db.execute('SELECT COUNT(*) FROM initial_risk').fetchone()[0])

    def test_missing_initial_stop_stays_unknown_when_current_stop_changes(self):
        with closing(sqlite3.connect(self.ledger)) as db, db:
            db.execute('DELETE FROM intents')
        self.broker.order_rows = []
        self.broker.rows = self.broker.rows[:1]
        self.broker.book = [{'identifier': 200, 'ticket': 200, 'symbol': 'EURUSD', 'sl': 1.0995}]
        self.poll()
        self.assertIsNone(self.trade()['R'])
        self.assertIsNone(self.trade()['initial_risk']['initial_sl'])
        self.broker.book[0]['sl'] = 1.1010
        self.broker.order_rows = [{'ticket': 100, 'symbol': 'EURUSD', 'sl': 1.1010}]
        self.poll()
        self.assertIsNone(self.trade()['initial_risk']['initial_risk_cash'])
        self.assertEqual([], self.broker.calc_calls)

    def test_late_cost_correction_and_reversion_append_versions_preserve_original(self):
        self.poll()
        self.broker.rows[-1]['commission'] = -3.
        self.poll()
        self.assertAlmostEqual(1.6, self.trade()['R'])
        self.broker.rows[-1]['commission'] = -1.
        self.poll()
        with closing(sqlite3.connect(self.db)) as db, db:
            deals = db.execute("SELECT version,payload FROM observations WHERE kind='DEAL' AND record_id='2' ORDER BY version").fetchall()
            versions = db.execute("SELECT COUNT(*) FROM observations WHERE kind='TRADE'").fetchone()[0]
        self.assertEqual([1, 2, 3], [row[0] for row in deals])
        self.assertEqual([-1., -3., -1.], [json.loads(row[1])['commission'] for row in deals])
        self.assertEqual(3, versions)
        self.assertAlmostEqual(1.8, self.trade()['R'])

    def test_partial_fills_same_order_are_aggregated_and_later_scale_in_invalidates_R(self):
        original = copy.deepcopy(self.broker.rows)
        self.broker.rows = [{**original[0], 'ticket': 10, 'volume': .04},
                            {**original[0], 'ticket': 11, 'volume': .06}, original[1]]
        self.poll()
        self.assertEqual('CLOSED', self.trade()['status'])
        self.assertAlmostEqual(.1, self.trade()['entry']['volume'])
        self.assertAlmostEqual(1.7, self.trade()['R'])
        self.broker.rows.extend([{**original[0], 'ticket': 12, 'order': 103, 'volume': .1},
                                {**original[1], 'ticket': 13, 'order': 104, 'volume': .1}])
        self.poll()
        self.assertIsNone(self.trade()['R'])
        self.assertAlmostEqual(10., self.trade()['initial_risk']['initial_risk_cash'])

    def test_signal_is_not_fabricated_and_original_proposal_not_replaced(self):
        self.poll()
        changed = copy.deepcopy(self.intent['payload'])
        changed['proposal']['market_regime'] = 'FAKE_LATER_CHANGE'
        with closing(sqlite3.connect(self.ledger)) as db, db:
            db.execute('UPDATE intents SET payload=?', (json.dumps(changed),))
        self.poll()
        self.assertEqual('RANGE', self.trade()['regime'])
        self.assertEqual(self.intent['payload']['proposal'], self.trade()['signal'])

    def test_late_ambiguous_owner_flags_conflict_and_preserves_original_signal(self):
        self.poll()
        self.assertEqual('MATCHED_NEXUS', self.trade()['signal_status'])
        conflicting = copy.deepcopy(self.intent)
        conflicting['id'] = 'b' * 64
        conflicting['payload']['proposal']['id'] = 'second-conflicting-proposal'
        with closing(sqlite3.connect(self.ledger)) as db, db:
            db.execute('INSERT INTO intents VALUES(?,?,?,?)',
                       (conflicting['id'], self.key, 'ENTRY', json.dumps(conflicting['payload'])))
        self.poll()
        trade = self.trade()
        self.assertEqual('AMBIGUOUS', trade['signal_status'])
        self.assertFalse(trade['eligible_for_strategy_evaluation'])
        self.assertEqual(self.intent['payload']['proposal'], trade['signal'])
        self.assertEqual(self.intent['id'], trade['intent_id'])
        self.assertEqual([self.intent['id'], conflicting['id']],
                         trade['current_ownership']['matching_intent_ids'])
        self.assertEqual(2, trade['current_ownership']['matching_count'])
        self.assertTrue(trade['current_ownership']['conflict'])
        self.assertEqual('READ_ONLY_NEXUS_ENTRY_LEDGER', trade['current_ownership']['source'])
        self.assertEqual(0, self.poll()['changed_records'])
        with closing(sqlite3.connect(self.db)) as db, db:
            self.assertEqual(1, db.execute("SELECT COUNT(*) FROM observations WHERE kind='SIGNAL'").fetchone()[0])
            conflicts = db.execute("SELECT payload FROM audit WHERE event='OWNERSHIP_CONFLICT'").fetchall()
        self.assertEqual(1, len(conflicts))
        self.assertEqual(2, json.loads(conflicts[0][0])['matching_count'])


if __name__ == '__main__':
    unittest.main()
