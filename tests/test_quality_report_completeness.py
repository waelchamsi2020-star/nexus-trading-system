"""A partially completed run must never publish a successful quality gate."""
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('quality_gate', Path(__file__).resolve().parents[1]/'tools/quality_gate.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


# Vulture review: unittest/pytest discovers and executes this TestCase by module inspection.
class QualityReportCompleteness(unittest.TestCase):
    def test_partial_success_and_duplicate_results_never_pass(self):
        required = ('lint','typecheck','unit','integration')
        for names in ((), required[:2], ('lint','typecheck','unit','unit')):
            with self.subTest(names=names):
                report = gate.report_status([{'check':name,'exit_code':0} for name in names],required)
                self.assertFalse(report['complete'])
                self.assertFalse(report['passed'])

    def test_complete_run_requires_every_exit_code_zero(self):
        required = ('lint','typecheck','unit','integration')
        rows = [{'check':name,'exit_code':0} for name in required]
        self.assertTrue(gate.report_status(rows,required)['passed'])
        rows[-1]['exit_code']=1
        report=gate.report_status(rows,required)
        self.assertTrue(report['complete'])
        self.assertFalse(report['passed'])
