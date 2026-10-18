import json
import tempfile
import unittest
from pathlib import Path

import test_chart_learning as fixtures

from nexus.learning import feature_drift_review
from nexus.learning_journal import persist, read_snapshot


# Vulture review: unittest/pytest discovers and executes this TestCase by module inspection.
class ShadowDriftReview(unittest.TestCase):
    def test_independent_shift_in_training_standard_deviations(self):
        result=feature_drift_review([[-1.],[1.]]*20,[[3.]]*12,['x'])
        self.assertEqual(result['status'],'RESEARCH_DRIFT_ALERT')
        self.assertEqual(result['features'][0]['standardized_mean_shift'],3.)
        self.assertEqual(result['features'][0]['outside_three_training_std_fraction'],0.)
        self.assertFalse(result['execution_authority'])

    def test_identical_distribution_and_unit_scaling(self):
        baseline=[[-1.],[1.]]*20;later=[[-1.],[1.]]*6
        result=feature_drift_review(baseline,later,['x'])
        self.assertEqual(result['status'],'NO_ALERT_IN_SAMPLE')
        self.assertEqual(result['features'],feature_drift_review([[x[0]*1e300] for x in baseline],[[x[0]*1e300] for x in later],['x'])['features'])

    def test_constant_feature_change_is_explicit_and_never_infinite(self):
        result=feature_drift_review([[1.]]*40,[[2.]]*12,['x'])
        self.assertTrue(result['features'][0]['constant_training_changed'])
        self.assertIsNone(result['features'][0]['standardized_mean_shift'])
        self.assertEqual(result['status'],'RESEARCH_DRIFT_ALERT')
        json.dumps(result,allow_nan=False)
        self.assertEqual(feature_drift_review([[1.]],[[2.]],['x'])['status'],'INSUFFICIENT_DATA')

    def test_nonfinite_boolean_or_misaligned_features_are_rejected(self):
        for later in ([[float('nan')]]*2,[[True]]*2,[[1.,2.]]*2):
            with self.assertRaises(ValueError):
                feature_drift_review([[1.],[2.]],later,['x'])

    def test_feedback_snapshot_and_account_mirror_preserve_observational_drift(self):
        fixture=fixtures.ChartLearningTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        fixture.dataset();snapshot=fixture.memory.snapshot('A');model=snapshot['chart_learning']['models'][0]
        review=model['drift_review']
        self.assertEqual(review['train_samples'],model['train_samples'])
        self.assertEqual(review['holdout_samples'],model['holdout_samples'])
        self.assertFalse(review['automatic_normalizer_changes'])
        self.assertFalse(review['profitability_inference'])
        with tempfile.TemporaryDirectory() as directory:
            persist(fixture.memory,'A',Path(directory),1_000_000,snapshot)
            saved=read_snapshot(Path(directory),'A')['evaluation']['chart_learning']['models'][0]
        self.assertEqual(saved['drift_review'],review)
