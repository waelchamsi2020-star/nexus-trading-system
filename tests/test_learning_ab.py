import copy
import importlib.util
import unittest
from pathlib import Path

import test_chart_learning as fixtures

spec=importlib.util.spec_from_file_location('learning_ab',Path(__file__).resolve().parents[1]/'tools/learning_ab.py')
ab=importlib.util.module_from_spec(spec);spec.loader.exec_module(ab)


# Vulture review: unittest/pytest discovers and executes this TestCase by module inspection.
class LearningAB(unittest.TestCase):
    def rows(self,degrade=False):
        return [{'outcome_id':str(i),'entry_at':10+i*10,'closed_at':12+i*10,'predicted_at':9+i*10,
                 'net_r':1. if i%2==0 else -2.,'before_probability':.8,
                 'after_probability':.8 if (i%2==1 if degrade else i%2==0) else .2} for i in range(80)]

    def test_paired_hand_calculation_bootstrap_and_no_live_authority(self):
        rows=self.rows();original=copy.deepcopy(rows);result=ab.paired_review(rows,1)
        self.assertEqual(-40.,result['before']['net_r']);self.assertEqual(40.,result['after']['net_r'])
        self.assertEqual(1.,result['mean_difference_r']);self.assertGreater(result['paired_block_bootstrap_95'][0],0)
        self.assertEqual('RESEARCH_CANDIDATE',result['sandbox_decision'])
        self.assertFalse(result['execution_authority']);self.assertFalse(result['live_policy_changed'])
        self.assertEqual(original,rows);self.assertEqual(result,ab.paired_review(rows,1))

    def test_sandbox_rejects_degradation_and_insufficient_data(self):
        self.assertEqual('REJECT_DEGRADATION',ab.paired_review(self.rows(True),1)['sandbox_decision'])
        self.assertEqual('REJECT_INSUFFICIENT',ab.paired_review(self.rows()[:10],1)['sandbox_decision'])
        self.assertEqual('REJECT_INSUFFICIENT',ab.paired_review([],1)['sandbox_decision'])

    def test_future_training_prediction_duplicate_and_nonfinite_are_refused(self):
        with self.assertRaises(ValueError):ab.paired_review(self.rows(),10)
        for field,value in (('predicted_at',1000),('net_r',float('nan')),('after_probability',True)):
            rows=self.rows();rows[0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):ab.paired_review(rows,1)
        rows=self.rows();rows[1]['outcome_id']=rows[0]['outcome_id']
        with self.assertRaises(ValueError):ab.paired_review(rows,1)

    def test_frozen_classifier_export_produces_paired_shadow_review(self):
        fixture=fixtures.ChartLearningTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        fixture.dataset(count=240)
        snapshot=fixture.memory.export('A');report=ab.evaluate_snapshot(snapshot)
        self.assertEqual(1,len(report['models']))
        model=report['models'][0]
        self.assertEqual(72,model['opportunities'])
        self.assertTrue(model['same_observed_net_outcome_and_costs_for_both'])
        self.assertFalse(report['execution_authority']);self.assertFalse(report['profitability_proven'])
