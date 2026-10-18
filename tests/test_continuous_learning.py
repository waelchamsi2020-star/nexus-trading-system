import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from nexus.learning.drift_monitor import monitor_schools
from nexus.learning.proposals import ProposalStore
from nexus.learning.sandbox import evaluate_proposal

spec=importlib.util.spec_from_file_location('learning_loop',Path(__file__).resolve().parents[1]/'tools/learning_loop.py')
loop=importlib.util.module_from_spec(spec);spec.loader.exec_module(loop)


def pairs(degrade=False):
    return [{'outcome_id':str(i),'before_net_r':1. if i%2 else -1.,
             'after_net_r':(-2. if i%2 else -1.) if degrade else (2. if i%2 else -1.),
             'training_closed_at':1.,'predicted_at':10.+i*10,'entry_at':11.+i*10,'closed_at':12.+i*10,
             'before_costs':{'commission':1.,'slippage_points':10,'spread_points':7},
             'after_costs':{'commission':1.,'slippage_points':10,'spread_points':7}} for i in range(40)]


# Vulture review: unittest/pytest discovers this TestCase class.
class ContinuousLearning(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        self.evidence=self.root/'evidence.json';self.evidence.write_text('{"data_kind":"SYNTHETIC"}')
        self.store=ProposalStore(self.root/'proposals.db','A');self.addCleanup(self.store.close)

    def test_proposals_isolation_idempotency_decisions_and_immutable_evidence(self):
        pid=self.store.create_proposal('threshold',1,2,self.evidence,'x')
        self.assertEqual(pid,self.store.create_proposal('threshold',1,2,self.evidence,'x'))
        with self.assertRaisesRegex(ValueError,'conflict'):self.store.create_proposal('threshold',1,3,self.evidence,'x')
        second=ProposalStore(self.root/'proposals.db','B');self.addCleanup(second.close)
        self.assertEqual([],second.list_proposals())
        with self.assertRaises(KeyError):second.approve_proposal(pid,'reviewed')
        self.store.approve_proposal(pid,'reviewed');self.store.approve_proposal(pid,'reviewed')
        with self.assertRaises(ValueError):self.store.reject_proposal(pid,'terminal')
        self.assertEqual('APPROVED_RESEARCH_ONLY',self.store.list_proposals()[0]['status'])
        other=self.store.create_proposal('threshold',1,2,self.evidence)
        self.evidence.write_text('{"changed":true}')
        with self.assertRaisesRegex(ValueError,'changed'):self.store.reject_proposal(other,'review')

    def test_atomic_audit_failure_rolls_back_create_and_decision(self):
        self.store.db.execute("CREATE TRIGGER audit_fail BEFORE INSERT ON proposal_audit BEGIN SELECT RAISE(ABORT,'injected');END")
        with self.assertRaises(sqlite3.IntegrityError):self.store.create_proposal('x',1,2,self.evidence)
        self.assertEqual([],self.store.list_proposals());self.store.db.execute('DROP TRIGGER audit_fail')
        pid=self.store.create_proposal('x',1,2,self.evidence)
        self.store.db.execute("CREATE TRIGGER audit_fail BEFORE INSERT ON proposal_audit BEGIN SELECT RAISE(ABORT,'injected');END")
        with self.assertRaises(sqlite3.IntegrityError):self.store.reject_proposal(pid,'test')
        self.assertEqual('PENDING',self.store.list_proposals()[0]['status'])

    def test_validation_and_sandbox_fail_closed(self):
        with self.assertRaises(ValueError):ProposalStore(':memory:','')
        for kind,identity in (('',None),('x','')):
            with self.assertRaises(ValueError):self.store.create_proposal(kind,1,2,self.evidence,identity)
        blank=self.root/'blank';blank.write_bytes(b'')
        with self.assertRaises(ValueError):self.store.create_proposal('x',1,2,blank)
        with self.assertRaises(ValueError):self.store._decide('x','REJECTED','')
        with self.assertRaises(ValueError):evaluate_proposal({},[])
        self.assertEqual('REJECT_INSUFFICIENT',evaluate_proposal({'id':'x'},[])['status'])
        good=evaluate_proposal({'id':'x'},pairs());self.assertEqual('READY_FOR_RESEARCH_REVIEW',good['status'])
        self.assertFalse(good['live_mutation']);self.assertFalse(good['execution_authority'])
        self.assertEqual('REJECT_DEGRADATION',evaluate_proposal({'id':'x'},pairs(True))['status'])
        for key,value in (('after_costs',{}),('entry_at',0.),('after_net_r',float('nan')),('outcome_id','')):
            data=pairs();data[0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):evaluate_proposal({'id':'x'},data)
        data=pairs();data[1]['outcome_id']=data[0]['outcome_id']
        with self.assertRaises(ValueError):evaluate_proposal({'id':'x'},data)

    def test_monitor_contexts_and_daily_loop_are_shadow_and_idempotent(self):
        school={'school_id':'ema_cross','revision':'fixture','symbol':'SYNTHETIC','timeframe':'M5',
                'features':['x'],'train':[[-1.],[1.]]*20,'heldout':[[4.]]*12}
        document={'account_key':'A','schools':[school],'candidates':[{**{k:school[k] for k in ('school_id','revision','symbol','timeframe')},'paired_heldout':pairs()}]}
        self.evidence.write_text(json.dumps(document))
        report=loop.run_cycle(document,self.root/'cycle.db',self.evidence,'2026-10-18')
        self.assertTrue(report['monitors'][0]['alert']);self.assertEqual(-3.,report['monitors'][0]['three_sigma_limits'][0]['lower'])
        again=loop.run_cycle(document,self.root/'cycle.db',self.evidence,'2026-10-18')
        self.assertEqual(report['proposals'][0]['id'],again['proposals'][0]['id'])
        self.assertFalse(report['execution_authority']);self.assertFalse(report['live_mutation'])
        with self.assertRaises(ValueError):monitor_schools([school,school])
        school['heldout']=[[-1.],[1.]]*6
        self.assertFalse(monitor_schools([school])[0]['alert'])
        self.evidence.write_text(json.dumps(document));quiet=loop.run_cycle(document,self.root/'quiet.db',self.evidence,'2026-10-18')
        self.assertEqual([],quiet['proposals'])
        school['heldout']=[[4.]]*12;document['candidates']=[];self.evidence.write_text(json.dumps(document))
        rejected=loop.run_cycle(document,self.root/'missing.db',self.evidence,'2026-10-18')
        self.assertEqual('REJECT_INSUFFICIENT',rejected['proposals'][0]['sandbox']['status'])
