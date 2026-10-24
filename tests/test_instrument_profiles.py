"""Read-only discovery profile generation safety tests."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from generate_instrument_profiles import build_profiles


class InstrumentProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / "outputs/phase0_market_watch_20261024_0915_revision2.json"
        cls.snapshot = json.loads(path.read_text(encoding="utf-8"))

    def test_every_profile_stays_non_routable_and_spread_is_observational(self):
        result = build_profiles(self.snapshot)
        self.assertEqual(len(result["symbols"]), self.snapshot["symbols_visible"])
        self.assertFalse(result["spread_policy"]["independent_rejection_gate"])
        self.assertTrue(result["spread_policy"]["include_actual_execution_cost_in_risk"])
        self.assertTrue(all(not row["routing"]["enabled"] for row in result["symbols"].values()))
        self.assertTrue(all(row["routing"]["strategy"] is None for row in result["symbols"].values()))

    def test_crypto_m1_m5_are_disabled_without_measurement(self):
        result = build_profiles(self.snapshot)
        for row in result["symbols"].values():
            if row["class"] == "crypto":
                for timeframe in ("M1", "M5"):
                    self.assertEqual(row["frames"][timeframe]["status"], "DISABLED_BY_POLICY")
                    self.assertIsNone(row["frames"][timeframe]["atr_median"])

    def test_generated_profiles_do_not_export_account_identity(self):
        result = build_profiles(self.snapshot)
        encoded = json.dumps(result)
        self.assertNotIn(str(self.snapshot["account"]), encoded)
        self.assertNotIn("authorization", encoded.lower())
        self.assertNotIn("token", encoded.lower())

    def test_manual_overrides_are_preserved_and_non_demo_snapshot_fails_closed(self):
        previous = {"operator_overrides": {"EXAMPLE": {"enabled": False}}}
        result = build_profiles(self.snapshot, previous)
        self.assertEqual(result["operator_overrides"], previous["operator_overrides"])
        invalid = copy.deepcopy(self.snapshot)
        invalid["account_trade_mode"] = 1
        with self.assertRaisesRegex(ValueError, "Demo"):
            build_profiles(invalid)

    def test_cli_writes_valid_json_yaml_without_enabling_any_symbol(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "instruments.yaml"
            subprocess.run([
                sys.executable, str(ROOT / "tools/generate_instrument_profiles.py"),
                "--source", str(ROOT / "outputs/phase0_market_watch_20261024_0915_revision2.json"),
                "--output", str(output),
            ], check=True, capture_output=True, text=True)
            content = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(len(content["symbols"]), self.snapshot["symbols_visible"])
            self.assertFalse(any(item["routing"]["enabled"] for item in content["symbols"].values()))


if __name__ == "__main__":
    unittest.main()
