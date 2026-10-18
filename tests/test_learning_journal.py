"""Durability/research boundary checks; no broker commands or live policy edits."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_learning import fills, intent, rule

from nexus.learning import LearningMemory
from nexus.learning_journal import persist, read_snapshot, review_cases
from nexus.store import Store


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)
        self.store=Store(self.path/'ledger.sqlite3');self.addCleanup(self.store.close)
        self.reference=rule();self.memory=LearningMemory(self.store,{'fixture_rule':self.reference})

    def closed(self, index=1, net=-10, account='A', reference=None):
        item=intent(index,account,reference or self.reference)
        self.memory.ingest(account,[item],fills(item,result=net,closed_at=100+index),10000)

    def test_state_file_is_account_scoped_deduplicated_and_fingerprinted(self):
        self.closed()
        first=persist(self.memory,'A',self.path,10000)
        second=persist(self.memory,'A',self.path,10001)
        self.assertTrue(first['written']);self.assertFalse(second['written'])
        payload=read_snapshot(self.path,'A')
        self.assertEqual(payload['evaluation']['closed_records'],1)
        self.assertEqual(payload['review']['cases'][0]['category'],'LOSING_OUTCOME')
        self.assertFalse(payload['review']['cases'][0]['causal_error_proven'])
        self.assertFalse(payload['automatic_live_changes'])
        other=persist(self.memory,'B',self.path,10000)
        self.assertNotEqual(first['file'],other['file'])
        self.assertEqual(read_snapshot(self.path,'B')['evaluation']['closed_records'],0)

    def test_cost_correction_replaces_current_case_but_preserves_sqlite_history(self):
        self.closed(net=-10);persist(self.memory,'A',self.path,10000)
        self.closed(net=10);persist(self.memory,'A',self.path,10001)
        payload=read_snapshot(self.path,'A')
        self.assertEqual(payload['review']['cases'],[])
        self.assertEqual(payload['outcome_correction_records'],2)
        self.assertEqual(payload['evaluation']['closed_records'],1)

    def test_atomic_replace_failure_keeps_previous_file_and_cleans_temporary_file(self):
        self.closed();result=persist(self.memory,'A',self.path,10000)
        path=Path(result['file']);before=path.read_bytes();self.closed(net=-20)
        with patch('nexus.learning_journal.os.replace', side_effect=OSError('simulated locked destination')), self.assertRaises(OSError):
            persist(self.memory, 'A', self.path, 10001)
        self.assertEqual(path.read_bytes(),before)
        self.assertEqual(list(path.parent.glob('.learning-*.tmp')),[])

    def test_corrupt_mirror_is_rejected_and_rebuilt_from_ledger(self):
        self.closed();result=persist(self.memory,'A',self.path,10000)
        target=Path(result['file']);data=json.loads(target.read_text(encoding='utf-8'))
        data['automatic_live_changes']=True;target.write_text(json.dumps(data),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'fingerprint'):read_snapshot(self.path,'A')
        self.assertTrue(persist(self.memory,'A',self.path,10001)['written'])
        self.assertFalse(read_snapshot(self.path,'A')['automatic_live_changes'])
        for invalid in ('null','[]','false'):
            target.write_text(invalid,encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'fingerprint'):read_snapshot(self.path,'A')
            self.assertTrue(persist(self.memory,'A',self.path,10002)['written'])

    def test_database_reopen_recovers_results_without_trusting_json(self):
        self.closed();persist(self.memory,'A',self.path,10000)
        reopened=Store(self.path/'ledger.sqlite3')
        try:
            memory=LearningMemory(reopened,{'fixture_rule':self.reference})
            self.assertEqual(memory.snapshot('A')['closed_records'],1)
            persist(memory,'A',self.path,10001)
            self.assertEqual(read_snapshot(self.path,'A')['review']['case_count'],1)
        finally:reopened.close()

    def test_loss_streaks_do_not_mix_revision_symbol_or_execution_context(self):
        rows=[{'outcome_id': str(i),'strategy_id': 'a','revision': 'r','symbol': 'X','timeframe': 'M1','regime': 'TREND',
                   'protocol_revision': 'p','execution_style': 'SCALP','scalp_policy_revision': 's',
                   'execution_policy_revision': 'e','eligible': True,'net_r': -1.,'closed_at': i} for i in range(3)]
        before=copy.deepcopy(rows);review=review_cases(rows,{})
        self.assertEqual(review['loss_streak_reviews'][0]['consecutive_losses'],3)
        self.assertEqual(rows,before)
        for key in ('revision','symbol','timeframe','regime','protocol_revision','execution_style','scalp_policy_revision','execution_policy_revision'):
            changed=copy.deepcopy(rows);changed[-1][key]='different'
            self.assertEqual(review_cases(changed,{})['loss_streak_reviews'],[])
        rows.append(dict(rows[-1],outcome_id='win',closed_at=4,net_r=1.))
        self.assertEqual(review_cases(rows,{})['loss_streak_reviews'],[])

    def test_excluded_evidence_never_becomes_loss_or_training_label(self):
        row={'outcome_id': 'synthetic','eligible': False,'net_r': -100,'closed_at': 1,'exclusions': ['synthetic_results']}
        result=review_cases([row],{})
        self.assertEqual(result['cases'][0]['category'],'EXCLUDED_EVIDENCE')
        self.assertEqual(result['loss_streak_reviews'],[])
        self.assertFalse(result['loss_is_implementation_error'])

    def test_case_window_is_bounded_without_deleting_authoritative_history(self):
        rows=[{'outcome_id': str(i),'eligible': False,'closed_at': i,'exclusions': ['missing']} for i in range(205)]
        result=review_cases(rows,{})
        self.assertEqual(result['case_count'],205)
        self.assertEqual(len(result['cases']),200)
        self.assertTrue(result['cases_truncated'])

    def test_operational_faults_are_declared_unattributed_and_have_no_policy_authority(self):
        self.store.audit('ANALYSIS_ERROR',{'reason':'fixture'})
        self.store.audit('COMMITTEE_DECISION',{'decision':'WAIT'})
        persist(self.memory,'A',self.path,10000)
        result=read_snapshot(self.path,'A')
        self.assertEqual(result['operational_faults']['counts'],{'ANALYSIS_ERROR':1})
        self.assertIn('not attributed',result['operational_faults']['scope'])
        self.assertFalse(result['automatic_live_changes'])


if __name__=='__main__':unittest.main()
