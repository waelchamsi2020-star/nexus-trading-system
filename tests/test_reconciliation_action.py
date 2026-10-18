"""User-triggered ledger matching never authorizes a new broker send."""
import tempfile
import unittest
from pathlib import Path

from nexus.engine import Engine

ROOT = Path(__file__).resolve().parents[1]


# Vulture review: unittest/pytest discovers and executes this TestCase by module inspection.
class ReconciliationAction(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.engine = Engine(ROOT, Path(self.directory.name))
        self.engine._connect(True)

    def tearDown(self):
        self.engine.stop_worker()
        self.engine.store.close()
        self.engine.cache.db.close()
        self.engine.news.db.close()
        self.directory.cleanup()

    def test_action_runs_matching_and_records_result_without_reactivation(self):
        result = self.engine.action({'action':'reconcile'})
        self.assertTrue(result['ok'])
        self.assertIn('changes', result['result'])
        audit = self.engine.store.recent_audit()[0]
        self.assertEqual('RECONCILIATION', audit['event'])
        self.assertEqual(result['result'], audit['payload'])
        self.assertEqual('READ_ONLY', self.engine.executor.status()['mode'])
        self.assertEqual([], self.engine.broker.sent)

    def test_connection_failure_is_audited_and_never_sends(self):
        self.engine.broker.connected = False
        result = self.engine.action({'action':'reconcile'})
        self.assertFalse(result['ok'])
        self.assertFalse(self.engine.store.recent_audit()[0]['payload']['ok'])
        self.assertEqual('READ_ONLY', self.engine.executor.status()['mode'])
        self.assertEqual([], self.engine.broker.sent)
