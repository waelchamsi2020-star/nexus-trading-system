"""Fixed holdout review separates prediction quality from economic evidence."""
import copy
import tempfile
import unittest
from pathlib import Path

import test_chart_learning as chart_fixtures

from nexus.learning import _shadow_outcome_review
from nexus.learning_journal import persist, read_snapshot


class ShadowEconomicReviewTests(unittest.TestCase):
    def test_independent_hand_calculation(self):
        rows=[{'net_r':x} for x in (2.,-3.,1.,0.)]
        result=_shadow_outcome_review(rows,[.8,.6,.4,.2]);selected=result['selected']
        self.assertEqual(selected['outcomes'],2);self.assertEqual(result['abstained'],2)
        self.assertEqual(selected['sum_net_r'],-1.);self.assertEqual(selected['mean_net_r'],-.5)
        self.assertAlmostEqual(selected['profit_factor_r'],2/3)

    def test_high_hit_rate_can_still_have_negative_expectancy(self):
        result=_shadow_outcome_review([{'net_r':x} for x in [1.]*9+[-20.]],[.9]*10)
        self.assertEqual(result['selected']['positive_fraction'],.9)
        self.assertAlmostEqual(result['selected']['mean_net_r'],-1.1)
        self.assertFalse(result['execution_authority']);self.assertFalse(result['automatic_live_changes'])

    def test_calibration_edges_include_zero_and_one_exactly_once(self):
        result=_shadow_outcome_review([{'net_r':1.}]*6,[0.,.2,.4,.6,.8,1.])
        self.assertEqual([x['observations'] for x in result['calibration']],[1,1,1,1,2])
        self.assertEqual(sum(x['observations'] for x in result['calibration']),6)

    def test_malformed_alignment_probabilities_and_outcomes_fail_explicitly(self):
        with self.assertRaises(ValueError):_shadow_outcome_review([{'net_r':1}],[])
        for value in (True,-.1,1.1,float('nan'),float('inf')):
            with self.subTest(value=value),self.assertRaises(ValueError):
                _shadow_outcome_review([{'net_r':1}],[value])
        with self.assertRaises(ValueError):_shadow_outcome_review([{'net_r':float('inf')}],[.5])

    def test_large_finite_outcomes_cannot_publish_infinity(self):
        result=_shadow_outcome_review([{'net_r':1e308}]*2,[.9,.9])
        self.assertFalse(result['selected']['numeric_valid'])
        self.assertIsNone(result['selected']['mean_net_r'])
        self.assertIsNone(result['selected']['sum_net_r'])

    def test_empty_selection_does_not_invent_zero_profit_or_win_rate(self):
        selected=_shadow_outcome_review([{'net_r':1.}],[.1])['selected']
        self.assertEqual(selected['outcomes'],0)
        self.assertIsNone(selected['mean_net_r']);self.assertIsNone(selected['positive_fraction'])
        self.assertFalse(selected['profit_factor_infinite'])

    def test_review_never_retunes_threshold_or_mutates_input(self):
        rows=[{'net_r':2.,'id':'a'},{'net_r':-1.,'id':'b'}];before=copy.deepcopy(rows)
        result=_shadow_outcome_review(rows,[.5,.49])
        rows[0]['net_r']=-100.
        changed=_shadow_outcome_review(rows,[.5,.49])
        self.assertEqual(result['selected']['outcomes'],changed['selected']['outcomes'])
        self.assertEqual(result['threshold'],changed['threshold'])
        self.assertFalse(result['threshold_tuned_on_holdout'])
        self.assertEqual(before[1],rows[1])

    def fixture(self):
        fixture=chart_fixtures.ChartLearningTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        return fixture

    def test_full_learning_snapshot_reports_economic_sample_limits(self):
        fixture=self.fixture();fixture.dataset();model=fixture.model()
        self.assertEqual(model['economic_review_status'],'INSUFFICIENT_SELECTED_OUTCOMES')
        self.assertTrue(model['classification_improved'])
        self.assertFalse(model['profitability_proven']);self.assertFalse(model['execution_authority'])
        self.assertEqual(len(model['evaluation_fingerprint']),64)

    def test_holdout_cost_amendment_changes_economics_not_fitted_weights(self):
        fixture=self.fixture();originals,deals=fixture.dataset();before=fixture.model()
        corrected=copy.deepcopy(deals);corrected[42*2+1]['commission']=-5.
        fixture.memory.ingest('A',originals,corrected,1_000_000);after=fixture.model()
        self.assertEqual(before['coefficients'],after['coefficients'])
        self.assertEqual(before['normalizer'],after['normalizer'])
        self.assertEqual(before['training_fingerprint'],after['training_fingerprint'])
        self.assertEqual(before['holdout_model'],after['holdout_model'])
        self.assertNotEqual(before['evaluation_fingerprint'],after['evaluation_fingerprint'])
        self.assertNotEqual(before['economic_review']['selected']['mean_net_r'],after['economic_review']['selected']['mean_net_r'])

    def test_economic_evidence_survives_account_scoped_atomic_mirror(self):
        fixture=self.fixture();fixture.dataset();evaluation=fixture.memory.snapshot('A')
        with tempfile.TemporaryDirectory() as tmp:
            persist(fixture.memory,'A',Path(tmp),1_000_000,evaluation)
            saved=read_snapshot(Path(tmp),'A')['evaluation']['chart_learning']['models'][0]
        expected=evaluation['chart_learning']['models'][0]
        self.assertEqual(saved['economic_review'],expected['economic_review'])
        self.assertEqual(saved['evaluation_fingerprint'],expected['evaluation_fingerprint'])


if __name__=='__main__':unittest.main()
