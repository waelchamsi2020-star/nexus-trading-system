import json
import unittest

from nexus.learning import feature_drift_review


# Vulture review: unittest/pytest discovers this TestCase class.
class DriftControlLimits(unittest.TestCase):
    def test_training_bounds_are_three_sigma_and_shifted_holdout_alerts(self):
        train=[[-1.],[1.]]*20
        normal=feature_drift_review(train,[[-1.],[1.]]*6,['x'])
        shifted=feature_drift_review(train,[[4.]]*12,['x'])
        self.assertEqual(normal['training_control_limits'],shifted['training_control_limits'])
        self.assertEqual({'feature':'x','training_mean':0.,'training_std':1.,'lower':-3.,'upper':3.,
                          'sigma_multiplier':3.,'status':'AVAILABLE'},shifted['training_control_limits'][0])
        self.assertEqual('NO_ALERT_IN_SAMPLE',normal['status'])
        self.assertEqual('RESEARCH_DRIFT_ALERT',shifted['status'])
        self.assertEqual(1.,shifted['features'][0]['outside_three_training_std_fraction'])
        self.assertFalse(shifted['execution_authority'])

    def test_constant_training_and_unrepresentable_bounds_are_explicit(self):
        constant=feature_drift_review([[2.]]*40,[[3.]]*12,['x'])
        self.assertEqual(2.,constant['training_control_limits'][0]['lower'])
        self.assertEqual(0.,constant['training_control_limits'][0]['training_std'])
        self.assertTrue(constant['features'][0]['constant_training_changed'])
        extreme=feature_drift_review([[-1e308],[1e308]]*20,[[0.]]*12,['x'])
        self.assertEqual('NUMERIC_RANGE_INVALID',extreme['training_control_limits'][0]['status'])
        json.dumps(extreme,allow_nan=False)
