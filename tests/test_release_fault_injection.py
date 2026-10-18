"""Injected failures use isolated SQLite and synthetic brokers; no MT5 connection."""
import json
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import test_continuous_learning as learning_fixtures
import test_risk_execution as fixtures

from nexus.learning.proposals import ProposalStore
from nexus.store import Store


# Vulture review: unittest/pytest discovers this TestCase class.
class ReleaseFaultInjection(unittest.TestCase):
    def fixture(self):
        f=fixtures.RiskExecutionTests();f.setUp();self.addCleanup(f.tearDown)
        return f

    def test_mt5_disconnect_during_send_retains_unknown_and_blocks_retry(self):
        f=self.fixture();f.activate();send=f.broker.send
        def disconnect_after_fill(request):
            send(request)
            f.broker.connected=False
            raise ConnectionError('Injected disconnect after broker fill before acknowledgment')
        with patch.object(f.broker,'send',side_effect=disconnect_after_fill):
            result=f.executor.execute(f.proposal())
        self.assertEqual('UNKNOWN',result['state'])
        intent=f.store.intent(result['intent_id'])
        self.assertGreater(intent['reserved'],0)
        self.assertEqual('READ_ONLY',f.executor.mode)
        self.assertEqual(1,len(f.broker.sent))
        self.assertFalse(f.executor.execute(f.proposal())['approved'])
        self.assertEqual(1,len(f.broker.sent))
        self.assertEqual(intent['reserved'],f.store.intent(intent['id'])['reserved'])

    def test_reconciliation_timeout_preserves_reservation_and_revokes_authority(self):
        f=self.fixture();result=f.entry();before=f.store.intent(result['intent_id'])
        with patch.object(f.broker,'deals',side_effect=TimeoutError('Injected history timeout')):
            report=f.executor.reconcile()
        self.assertFalse(report['ok']);self.assertIn('timeout',report['reason'])
        self.assertEqual('READ_ONLY',f.executor.mode)
        self.assertEqual(before,f.store.intent(before['id']))
        self.assertEqual(1,len(f.broker.sent))
        self.assertTrue(f.executor.reconcile()['ok'])
        self.assertEqual('READ_ONLY',f.executor.mode)

    def test_concurrent_audit_conflict_rolls_back_both_claims_then_one_retry_wins(self):
        f=self.fixture();f.store.reserve('entry','account',10.,{'symbol':'FIXTURE'},[],100.)
        f.store.db.execute("CREATE TRIGGER audit_conflict BEFORE INSERT ON audit WHEN NEW.event='INTENT_SENDING' BEGIN SELECT RAISE(ABORT,'injected concurrent audit conflict');END")
        barrier=threading.Barrier(2)
        def claim(expect_error):
            store=Store(f.path)
            try:
                barrier.wait(timeout=10)
                if expect_error:
                    try:store.claim_send('entry')
                    except sqlite3.IntegrityError:return 'ROLLED_BACK'
                    return 'UNEXPECTED_COMMIT'
                return store.claim_send('entry')
            finally:store.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(claim,[True,True]))
        self.assertEqual(['ROLLED_BACK']*2,results)
        self.assertEqual('PREPARED',f.store.intent('entry')['state'])
        self.assertEqual(0,sum(x['event']=='INTENT_SENDING' for x in f.store.recent_audit()))
        f.store.db.execute('DROP TRIGGER audit_conflict')
        barrier=threading.Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(claim,[False,False]))
        self.assertEqual([False,True],sorted(results))
        self.assertEqual(1,sum(x['event']=='INTENT_SENDING' for x in f.store.recent_audit()))

    def test_proposals_db_write_failure_commits_neither_proposal_nor_audit(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);evidence=root/'evidence.json';evidence.write_text('{}')
            store=ProposalStore(root/'proposals.db','ACCOUNT-A')
            try:
                store.db.execute("CREATE TRIGGER disk_failure BEFORE INSERT ON proposals BEGIN SELECT RAISE(ABORT,'injected disk write failure');END")
                with self.assertRaisesRegex(sqlite3.IntegrityError,'disk write failure'):
                    store.create_proposal('review',1,2,evidence,'proposal')
                self.assertEqual([],store.list_proposals())
                self.assertEqual(0,store.db.execute('SELECT COUNT(*) FROM proposal_audit').fetchone()[0])
                store.db.execute('DROP TRIGGER disk_failure')
                store.create_proposal('review',1,2,evidence,'proposal')
                self.assertEqual('PENDING',store.list_proposals()[0]['status'])
                self.assertEqual(1,store.db.execute('SELECT COUNT(*) FROM proposal_audit').fetchone()[0])
            finally:store.close()

    def test_sandbox_mid_evaluation_failure_rejects_without_partial_metrics(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);school={'school_id':'ema_cross','revision':'fixture','symbol':'SYNTHETIC',
                'timeframe':'M5','features':['x'],'train':[[-1.],[1.]]*20,'heldout':[[4.]]*12}
            rows=learning_fixtures.pairs()
            document={'account_key':'A','schools':[school],'candidates':[{**{k:school[k] for k in
                ('school_id','revision','symbol','timeframe')},'paired_heldout':rows}]}
            evidence=root/'evidence.json';evidence.write_text(json.dumps(document))
            evaluate=learning_fixtures.loop.evaluate_proposal
            def interrupted_evaluation(proposal, heldout):
                def interrupted_rows():
                    yield from heldout[:20]
                    raise RuntimeError('Injected sandbox interruption after twenty valid rows')
                return evaluate(proposal,interrupted_rows())
            with patch.object(learning_fixtures.loop,'evaluate_proposal',side_effect=interrupted_evaluation):
                report=learning_fixtures.loop.run_cycle(document,root/'proposals.db',evidence,'2026-10-18')
            result=report['proposals'][0]['sandbox']
            self.assertEqual('REJECT_SANDBOX_ERROR',result['status'])
            self.assertEqual('RuntimeError',result['error_type'])
            self.assertNotIn('metrics',result);self.assertFalse(report['execution_authority'])
            self.assertFalse(report['live_mutation'])
            store=ProposalStore(root/'proposals.db','A')
            try:
                self.assertEqual('REJECTED',store.list_proposals()[0]['status'])
                self.assertEqual(['PENDING','REJECTED'],[r[0] for r in store.db.execute('SELECT status FROM proposal_audit ORDER BY id')])
            finally:store.close()
