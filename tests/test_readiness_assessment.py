"""Readiness claims must be bound to current evidence, not an arbitrary score."""
import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

tool=Path(__file__).resolve().parents[1]/'tools/assess_readiness.py'
spec=importlib.util.spec_from_file_location('assess_readiness',tool)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class ReadinessAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'reports').mkdir();(self.root/'src/nexus').mkdir(parents=True)
        source=self.root/'src/nexus/model.py';source.write_text('# fixture only',encoding='utf-8')
        hashes={'model.py':hashlib.sha256(source.read_bytes()).hexdigest()}
        self.invariant={'source_hashes':hashes,'passed':True,'orders_sent':0,'evaluations':2,'future_data_checks':2,
                        'failed_checks':[],'per_model':[{'id':'wait_only','statuses':{'WAIT':2}},{'id':'entry','statuses':{'READY':2}}]}
        self.broker={'source_hashes':hashes,'account_mode':'DEMO','orders_sent':0,'evaluations':2,'data_errors':[]}
        self.save('rule-invariants.json',self.invariant);self.save('mt5-rule-review.json',self.broker)

    def save(self,name,data):
        (self.root/'reports'/name).write_text(json.dumps(data),encoding='utf-8')

    def test_clean_operating_checks_never_certify_profitability(self):
        result=module.assess(self.root)
        self.assertTrue(result['technical_invariants_passed']);self.assertTrue(result['broker_read_audit_passed'])
        self.assertFalse(result['profitability_proven']);self.assertIsNone(result['score'])
        self.assertFalse(result['institutional_readiness_certified'])

    def test_source_change_invalidates_both_audits(self):
        (self.root/'src/nexus/model.py').write_text('# changed after tests',encoding='utf-8')
        result=module.assess(self.root)
        self.assertFalse(result['technical_invariants_passed']);self.assertFalse(result['broker_read_audit_passed'])

    def test_waiting_outputs_are_not_entry_branch_proof(self):
        gate=next(x for x in module.assess(self.root)['checks'] if x['id']=='entry_branch_evidence')
        self.assertEqual(gate['status'],'GAP');self.assertEqual(gate['generated_sample_models_without_ready'],['wait_only'])

    def test_declared_pass_does_not_hide_failed_checks(self):
        self.invariant['failed_checks']=[{'invariant':'invalid_price_plan'}]
        self.save('rule-invariants.json',self.invariant)
        self.assertFalse(module.assess(self.root)['technical_invariants_passed'])

    def test_missing_or_malformed_evidence_is_a_gap(self):
        (self.root/'reports/rule-invariants.json').write_text('{broken',encoding='utf-8')
        (self.root/'reports/mt5-rule-review.json').unlink()
        result=module.assess(self.root)
        self.assertFalse(result['technical_invariants_passed']);self.assertFalse(result['broker_read_audit_passed'])

    def test_outside_source_paths_are_rejected(self):
        self.invariant['source_hashes']={'../../secret.py':'not-a-hash'}
        self.save('rule-invariants.json',self.invariant)
        self.assertFalse(module.assess(self.root)['technical_invariants_passed'])

    def test_incomplete_future_checks_and_broker_errors_are_not_passes(self):
        self.invariant['future_data_checks']=1;self.broker['data_errors']=[{'reason':'missing bars'}]
        self.save('rule-invariants.json',self.invariant);self.save('mt5-rule-review.json',self.broker)
        result=module.assess(self.root)
        self.assertFalse(result['technical_invariants_passed']);self.assertFalse(result['broker_read_audit_passed'])

    def test_malformed_fields_and_boolean_counts_are_not_evidence(self):
        for count in (True,'200',None,-1,{},[]):
            with self.subTest(count=count):
                bad=copy.deepcopy(self.invariant);bad.update(evaluations=count,per_model=None)
                self.save('rule-invariants.json',bad)
                self.assertFalse(module.assess(self.root)['technical_invariants_passed'])
        self.broker.pop('data_errors');self.save('mt5-rule-review.json',self.broker)
        self.assertFalse(module.assess(self.root)['broker_read_audit_passed'])


if __name__=='__main__':unittest.main()
