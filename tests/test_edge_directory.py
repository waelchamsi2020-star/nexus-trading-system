"""Directory dispatch tests do not simulate native price history or relax validation."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_edge_gate import edge


# Vulture review: unittest/pytest discovers this TestCase class.
class EdgeDirectory(unittest.TestCase):
    def test_m5_h1_csv_sidecars_dispatch_to_separate_reports(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for tf in ('M5','H1'):
                folder=root/tf;folder.mkdir()
                (folder/'EURUSD.csv').write_text('fixture dispatch only')
                (folder/'EURUSD.metadata.json').write_text(json.dumps({'timeframe':tf}))
            with patch.object(edge,'run',return_value={'execution_authority':False}) as runner:
                results=edge.run_directory(root,root/'out',100.)
            self.assertEqual(2,len(results));self.assertEqual(2,runner.call_count)
            self.assertEqual({'M5','H1'},{c.args[1]['timeframe'] for c in runner.call_args_list})
            self.assertEqual({root/'out/M5/EURUSD.json',root/'out/H1/EURUSD.json'},
                             {c.args[2] for c in runner.call_args_list})
            self.assertTrue(all(c.args[3]==100. for c in runner.call_args_list))

    def test_empty_missing_metadata_and_timeframe_mismatch_fail_before_evaluation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            with patch.object(edge,'run') as runner:
                with self.assertRaisesRegex(ValueError,'No native'):edge.run_directory(root,root/'out',100.)
                (root/'M5').mkdir();(root/'M5/EURUSD.csv').write_text('fixture')
                with self.assertRaises(FileNotFoundError):edge.run_directory(root,root/'out',100.)
                (root/'M5/EURUSD.metadata.json').write_text('{"timeframe":"H1"}')
                with self.assertRaisesRegex(ValueError,'disagree'):edge.run_directory(root,root/'out',100.)
                runner.assert_not_called()
