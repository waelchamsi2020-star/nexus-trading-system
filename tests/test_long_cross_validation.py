"""Frozen selection and truthful cross-symbol evidence, using only mock replays."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.long_cross_validation import (
    cross_status,
    fingerprint,
    run_cross,
    select_frozen_winner,
)


def selection():
    return {"symbol": "EURUSD", "timeframe": "H1", "replay_source_sha256": "FROZEN_MOCK_SOURCE",
            "scenarios": [{"commission_usd_round_trip_per_lot": 7., "top5": ["engulfing", "support_bounce"],
                           "models": [{"model": "engulfing", "trades": 40, "net_r": 3.},
                                      {"model": "support_bounce", "trades": 50, "net_r": 2.},
                                      {"model": "pin_rejection", "trades": 2, "net_r": 100.}]}]}


def fixture(directory):
    study = directory / "H1.json"
    study.write_text(json.dumps(selection()))
    manifest = []
    for symbol, count in (("GBPUSD", 31112), ("USDJPY", 31113), ("XAUUSD", 29553)):
        path = directory / (symbol + ".csv")
        # A fingerprint-only fixture; no synthetic prices are research evidence.
        path.write_text("MOCK_CSV_NOT_REAL_PRICES_" + symbol)
        metadata = {"symbol": symbol, "bars": count, "timeframe": "H1", "source": "MT5_NATIVE",
                    "aggregated": False, "csv_sha256": fingerprint(path), "commission_known": False}
        path.with_suffix(".metadata.json").write_text(json.dumps(metadata))
        path.with_suffix(".report.json").write_text(json.dumps({
            **metadata, "source_consistency_verified": True, "first_open_utc": "MOCK", "last_close_utc": "MOCK"}))
        manifest.append({"symbol": symbol, "csv": str(path), "exit_code": 0})
    manifest_path = directory / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    return study, manifest_path


def replay_fixture(csv_path, metadata_path, output, *, workers, model_ids):
    meta = json.loads(metadata_path.read_text())
    metric = {"model": model_ids[0], "trades": 40, "win_rate": .5,
              "net_r": 1., "sharpe": .1, "max_dd": 2., "censored": 2,
              "entered_observed": 42, "unobserved_entries": 0,
              "profitable_windows": 10, "total_windows": 20}
    review = {"symbol": meta["symbol"], "timeframe": "H1", "bars": meta["bars"],
              "native_csv_sha256": fingerprint(csv_path), "replay_source_sha256": "FROZEN_MOCK_SOURCE",
              "scenarios": [{"commission_usd_round_trip_per_lot": fee, "models": [metric]} for fee in (0., 3., 7.)]}
    output.write_text(json.dumps(review))
    return review, {}


class LongCrossValidation(unittest.TestCase):
    def test_winner_frozen_fee7_with_minimum_closed_count_and_deterministic_rank(self):
        model, _ = select_frozen_winner(selection())
        self.assertEqual("engulfing", model)
        changed = copy.deepcopy(selection())
        changed["scenarios"][0]["top5"] = ["pin_rejection"]
        with self.assertRaisesRegex(ValueError, "at least30"):
            select_frozen_winner(changed)
        changed["scenarios"][0]["top5"] = ["support_bounce"]
        with self.assertRaisesRegex(ValueError, "ranking"):
            select_frozen_winner(changed)

    def test_all_positive_results_do_not_erase_gold_shortfall_or_censoring(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            study, manifest = fixture(directory)
            calls = []
            def runner(*args, **kwargs):
                calls.append(kwargs)
                return replay_fixture(*args, **kwargs)
            result = run_cross(study, manifest, directory / "cross.json", workers=4, runner=runner)
            self.assertTrue(result["all_three_positive_n_ge30"])
            self.assertFalse(result["all_three_native_minimum_30860"])
            self.assertFalse(result["strict_cross_pass"])
            self.assertTrue(result["censored_exposures_present"])
            self.assertEqual(1307, result["rows"][2]["shortfall_to_30860"])
            self.assertTrue(all(call == {"workers": 4, "model_ids": ["engulfing"]} for call in calls))
            self.assertFalse(result["qualified"])
            self.assertFalse(result["execution_authority"])
            self.assertEqual(0, result["orders_sent"])

    def test_missing_or_tampered_native_data_never_starts_replay(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            study, manifest = fixture(directory)
            def forbidden(*args, **kwargs):
                self.fail("Replay must not start with absent selection or tampered source")
            with self.assertRaises(FileNotFoundError):
                run_cross(directory / "missing.json", manifest, directory / "out.json", runner=forbidden)
            source = json.loads(manifest.read_text())[0]["csv"]
            Path(source).write_text("CHANGED_MOCK_CSV")
            with self.assertRaisesRegex(ValueError, "fingerprint"):
                run_cross(study, manifest, directory / "out.json", runner=forbidden)

    def test_source_or_model_mutation_after_selection_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            study, manifest = fixture(directory)
            def changed_engine(*args, **kwargs):
                review, cache = replay_fixture(*args, **kwargs)
                review["replay_source_sha256"] = "DIFFERENT_ENGINE"
                return review, cache
            with self.assertRaisesRegex(ValueError, "engine changed"):
                run_cross(study, manifest, directory / "out.json", runner=changed_engine)

    def test_observable_cross_threshold_requires_all_three_count_and_positive(self):
        rows = [{"symbol": symbol, "bars": 30860, "trades": 30, "net_r": .1, "censored": 0}
                for symbol in ("GBPUSD", "USDJPY", "XAUUSD")]
        self.assertTrue(cross_status(rows)["strict_cross_pass"])
        rows[0]["net_r"] = 0.
        self.assertFalse(cross_status(rows)["strict_cross_pass"])
        rows[0]["net_r"], rows[1]["trades"] = .1, 29
        self.assertFalse(cross_status(rows)["strict_cross_pass"])
