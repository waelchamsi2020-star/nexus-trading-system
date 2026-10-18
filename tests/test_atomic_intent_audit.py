"""SQLite failure injection proves intent changes and evidence commit together."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from nexus.store import Store


# Vulture review: unittest/pytest discovers and executes this TestCase by module inspection.
class AtomicIntentAudit(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / 'ledger.sqlite3'
        self.store = Store(self.path)

    def tearDown(self):
        self.store.close()
        self.directory.cleanup()

    def reserve(self):
        return self.store.reserve('entry', 'account', 10., {'symbol': 'FIXTURE'}, [], 100.)

    def fail_audit(self):
        self.store.db.execute("""CREATE TRIGGER fail_audit BEFORE INSERT ON audit
            BEGIN SELECT RAISE(ABORT, 'injected audit storage failure'); END""")

    def test_reservation_rolls_back_when_audit_insert_fails(self):
        self.fail_audit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.reserve()
        self.assertIsNone(self.store.intent('entry'))
        self.assertEqual([], self.store.recent_audit())
        self.store.db.execute('DROP TRIGGER fail_audit')
        self.assertTrue(self.reserve()['approved'])

    def test_send_claim_rolls_back_and_retry_is_audited_once(self):
        self.reserve()
        self.fail_audit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.claim_send('entry')
        self.assertEqual('PREPARED', self.store.intent('entry')['state'])
        self.store.db.execute('DROP TRIGGER fail_audit')
        self.assertTrue(self.store.claim_send('entry'))
        self.assertFalse(self.store.claim_send('entry'))
        events = [x['event'] for x in self.store.recent_audit()]
        self.assertEqual(1, events.count('INTENT_SENDING'))

    def test_state_and_reserved_money_roll_back_with_failed_audit(self):
        self.reserve()
        before = self.store.intent('entry')
        self.fail_audit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.set_intent_state('entry', 'REJECTED', reason='fixture')
        self.assertEqual(before, self.store.intent('entry'))
        self.store.db.execute('DROP TRIGGER fail_audit')
        self.store.set_intent_state('entry', 'REJECTED', reason='fixture')
        self.store.set_intent_state('entry', 'REJECTED', reason='fixture')
        self.store.close()
        self.store = Store(self.path)
        self.assertEqual(0., self.store.intent('entry')['reserved'])
        self.assertEqual(1, sum(x['event'] == 'INTENT_REJECTED' for x in self.store.recent_audit()))

    def test_management_intent_and_audit_are_atomic_and_idempotent(self):
        self.fail_audit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.management_intent('manage', 'account', {'action': 'close'}, 'fixture')
        self.assertIsNone(self.store.intent('manage'))
        self.store.db.execute('DROP TRIGGER fail_audit')
        self.assertTrue(self.store.management_intent('manage', 'account', {'action': 'close'}, 'fixture'))
        self.assertFalse(self.store.management_intent('manage', 'account', {'action': 'close'}, 'fixture'))
        self.assertEqual(1, sum(x['event'] == 'MANAGEMENT_PREPARED' for x in self.store.recent_audit()))
