"""Independent extreme-scale percentage checks; no strategy/performance claims."""
import math
import unittest

from nexus import indicators as ind
from nexus import strategies as st


# Vulture review: unittest/pytest discovers and executes this TestCase by module inspection.
class PercentageNumericSafety(unittest.TestCase):
    def test_legacy_simple_rsi_is_finite_even_when_raw_gain_sum_would_overflow(self):
        self.assertEqual(st.rsi([1e307,2e307,3e307]),100.)
        self.assertAlmostEqual(st.rsi([1.,1.7e308,1.,1.7e308]),200/3)
        self.assertEqual(st.rsi([2.,2.,2.]),50.)
    def test_mfi_finite_flows_can_have_a_finite_percentage(self):
        bars=[{'high': float(x),'low': float(x),'close': float(x),'tick_volume': 1e306} for x in (10,11,12,13)]
        self.assertEqual(ind.mfi_tick(bars,3)[-1],100.)

    def test_mfi_mixed_flow_matches_independent_ratio(self):
        bars=[{'high': float(x),'low': float(x),'close': float(x),'tick_volume': 1e306} for x in (10,11,10,12)]
        self.assertAlmostEqual(ind.mfi_tick(bars,3)[-1],100*(23/33))

    def test_mfi_nonfinite_accumulations_are_rejected(self):
        bars=[{'high': float(x),'low': float(x),'close': float(x),'tick_volume': 1e307} for x in (1,2,3,4,5,6,7)]
        with self.assertRaisesRegex(ValueError,'accumulation overflow'):
            ind.mfi_tick(bars,6)

    def test_rsi_percentage_does_not_overflow_on_large_finite_moves(self):
        self.assertEqual(ind.rsi_wilder([1e307,2e307,3e307],2)[-1],100.)
        self.assertAlmostEqual(ind.rsi_wilder([1e307,3e307,2e307],2)[-1],200/3)

    def test_stochastic_and_williams_are_scale_invariant(self):
        bars=[{'high': 3.,'low': 1.,'close': 2.}]*5
        large=[{k:v*1e307 for k,v in x.items()} for x in bars]
        self.assertAlmostEqual(ind.stochastic(large,3,1,1)['d'][-1],50.)
        self.assertAlmostEqual(ind.williams_r(large,3)[-1],-50.)

    def test_adx_does_not_overflow_when_directional_movement_is_large(self):
        bars=[{'high': float(i+2)*1e307,'low': float(i)*1e307,'close': float(i+1)*1e307} for i in range(8)]
        values=ind.adx_wilder(bars,2)
        self.assertTrue(all(x is None or math.isfinite(x) for x in values['plus_di']))
        self.assertAlmostEqual(values['plus_di'][-1],50.)
        self.assertAlmostEqual(values['adx'][-1],100.)


if __name__=='__main__':unittest.main()
