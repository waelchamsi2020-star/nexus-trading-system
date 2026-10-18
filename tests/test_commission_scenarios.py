"""Independent count/boundary checks for gap reports; synthetic timestamps only."""
import importlib.util
import unittest
from datetime import UTC, datetime
from pathlib import Path

spec=importlib.util.spec_from_file_location('commission_scenarios',Path(__file__).resolve().parents[1]/'tools/commission_scenarios.py')
scenarios=importlib.util.module_from_spec(spec);spec.loader.exec_module(scenarios)


# Vulture review: unittest/pytest discovers this TestCase class.
class CommissionGapInventory(unittest.TestCase):
    def test_expected_weekend_preserves_length_but_tuesday_missing_bar_splits(self):
        friday=int(datetime(2026,1,9,21,50,tzinfo=UTC).timestamp())
        sunday=int(datetime(2026,1,11,22,tzinfo=UTC).timestamp())
        bars=[{'time':x} for x in (friday,friday+300,sunday,sunday+300,sunday+600)]
        result=scenarios.inventory(bars,300)
        self.assertEqual(5,result['largest_approved_segment_bars'])
        self.assertEqual(4995,result['shortfall_to_5000'])
        self.assertEqual(1,len(result['gaps']));self.assertTrue(result['gaps'][0]['calendar_gate_approved'])
        tuesday=int(datetime(2026,1,6,12,tzinfo=UTC).timestamp())
        result=scenarios.inventory([{'time':tuesday+i*300} for i in (0,1,3,4,5)],300)
        self.assertEqual(3,result['largest_approved_segment_bars'])
        self.assertEqual(1,result['gaps'][0]['missing_bars'])
        self.assertEqual('فجوة غير مبررة',result['gaps'][0]['classification'])

    def test_empty_exact_5000_and_invalid_timestamp_boundaries(self):
        self.assertEqual(0,scenarios.inventory([],300)['largest_approved_segment_bars'])
        bars=[{'time':1_700_000_000+i*300} for i in range(5000)]
        result=scenarios.inventory(bars,300)
        self.assertEqual(5000,result['largest_approved_segment_bars']);self.assertTrue(result['enough_for_edge_gate'])
        self.assertEqual([],result['gaps'])
        for times in ((300,300),(300,200),(300,601)):
            with self.subTest(times=times),self.assertRaises(ValueError):
                scenarios.inventory([{'time':x} for x in times],300)
