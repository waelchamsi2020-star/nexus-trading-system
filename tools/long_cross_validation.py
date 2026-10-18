"""Frozen EURUSD winner evaluated on native long GBPUSD/USDJPY/XAUUSD H1.

The winner is selected once from the completed EURUSD USD7 ranking before any
cross-symbol replay. Every evaluation delegates to the unchanged long-window
research engine. Unknown/censored outcomes retain unknown R, never zero loss.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
SYMBOLS = ("GBPUSD", "USDJPY", "XAUUSD")
MINIMUM_BARS = 30860


def fingerprint(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fee_scenario(report, fee=7.):
    rows = [row for row in report.get("scenarios", [])
            if row.get("commission_usd_round_trip_per_lot") == fee]
    if len(rows) != 1:
        raise ValueError("Exactly one declared commission scenario is required")
    return rows[0]


def select_frozen_winner(study):
    if study.get("symbol") != "EURUSD" or study.get("timeframe") != "H1":
        raise ValueError("Completed native EURUSD H1 selection report required")
    scenario = fee_scenario(study)
    top = scenario.get("top5")
    if not isinstance(top, list) or not top:
        raise ValueError("No frozen fee7 winner with at least30 observable closed trades")
    rows = [row for row in scenario.get("models", []) if row.get("model") == top[0]]
    if len(rows) != 1 or rows[0].get("trades", 0) < 30:
        raise ValueError("Frozen winner does not have at least30 observable closed trades")
    ranked = sorted([row for row in scenario["models"] if row.get("trades", 0) >= 30],
                    key=lambda row: (-row["net_r"], row["model"]))
    if ranked[0]["model"] != top[0] or not math.isfinite(rows[0]["net_r"]):
        raise ValueError("Fee7 top5 conflicts with the declared deterministic netR ranking")
    return top[0], rows[0]


def load_manifest(path):
    entries = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(entries, list) or len(entries) != len(SYMBOLS):
        raise ValueError("Exactly three native cross-symbol exports required")
    by_symbol = {}
    for item in entries:
        symbol = item.get("symbol")
        if symbol not in SYMBOLS or symbol in by_symbol or item.get("exit_code") != 0:
            raise ValueError("Unique successful GBPUSD/USDJPY/XAUUSD exports required")
        csv_path = Path(item["csv"])
        metadata_path = csv_path.with_suffix(".metadata.json")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        export_path = csv_path.with_suffix(".report.json")
        export = json.loads(export_path.read_text(encoding="utf-8"))
        digest = fingerprint(csv_path)
        if (metadata.get("symbol") != symbol or metadata.get("timeframe") != "H1" or
                metadata.get("source") != "MT5_NATIVE" or metadata.get("aggregated") is not False or
                metadata.get("csv_sha256") != digest or export.get("csv_sha256") != digest or
                export.get("source_consistency_verified") is not True or
                export.get("symbol") != symbol or export.get("timeframe") != "H1"):
            raise ValueError("Native export identity, source consistency or fingerprint mismatch")
        by_symbol[symbol] = {"csv": csv_path, "metadata_path": metadata_path,
                             "metadata": metadata, "export_path": export_path,
                             "export": export, "sha256": digest}
    return by_symbol


def cross_status(rows):
    symbols_complete = len(rows) == len(SYMBOLS) and {row["symbol"] for row in rows} == set(SYMBOLS)
    observations_pass = symbols_complete and all(
        row["trades"] >= 30 and row["net_r"] > 0 for row in rows)
    native_minimum = symbols_complete and all(row["bars"] >= MINIMUM_BARS for row in rows)
    return {"all_three_positive_n_ge30": observations_pass,
            "all_three_native_minimum_30860": native_minimum,
            "strict_cross_pass": observations_pass and native_minimum,
            "censored_exposures_present": any(row["censored"] > 0 for row in rows),
            "qualified": False, "execution_authority": False}


def run_cross(study_path, manifest_path, output, *, workers=4, runner=None):
    if type(workers) is not int or not 1 <= workers <= 64:
        raise ValueError("workers must be an integer between1and64")
    study_path, manifest_path, output = map(Path, (study_path, manifest_path, output))
    # No cross-model computation starts before a complete selection artifact exists.
    if not study_path.is_file():
        raise FileNotFoundError("Completed EURUSD H1 study is not available: " + str(study_path))
    study_digest = fingerprint(study_path)
    study = json.loads(study_path.read_text(encoding="utf-8"))
    winner, selection = select_frozen_winner(study)
    exports = load_manifest(manifest_path)
    manifest_digest = fingerprint(manifest_path)
    if runner is None:
        from long_walkforward import run_native
        runner = run_native
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for symbol in SYMBOLS:
        source = exports[symbol]
        full_output = output.with_name(output.stem + "-" + symbol + ".json")
        review, cache = runner(source["csv"], source["metadata_path"], full_output,
                               workers=workers, model_ids=[winner])
        del cache
        if review.get("symbol") != symbol or review.get("timeframe") != "H1":
            raise ValueError("Cross-symbol engine result identity mismatch")
        if review.get("bars") != source["metadata"].get("bars"):
            raise ValueError("Native completed-bar count differs from exported metadata")
        if review.get("native_csv_sha256") != source["sha256"]:
            raise ValueError("Cross-symbol result uses a different native source")
        if sorted(row.get("commission_usd_round_trip_per_lot") for row in review.get("scenarios", [])) != [0., 3., 7.]:
            raise ValueError("All three unchanged USD0/3/7 scenarios required")
        expected_replay = study.get("replay_source_sha256")
        if expected_replay and review.get("replay_source_sha256") != expected_replay:
            raise ValueError("Replay engine changed after EURUSD winner selection")
        scenario = fee_scenario(review)
        models = scenario.get("models", [])
        if len(models) != 1 or models[0].get("model") != winner:
            raise ValueError("Cross-symbol replay changed the frozen selected model")
        metric = models[0]
        row = {"symbol": symbol, "model": winner, "bars": review["bars"],
               **{key: metric[key] for key in ("trades", "win_rate", "net_r", "sharpe", "max_dd", "censored",
                                                "entered_observed", "unobserved_entries", "profitable_windows", "total_windows")},
               "minimum_bars_required": MINIMUM_BARS,
               "native_count_requirement_met": review["bars"] >= MINIMUM_BARS,
               "shortfall_to_30860": max(0, MINIMUM_BARS - review["bars"]),
               "native_csv": str(source["csv"]), "native_csv_sha256": source["sha256"],
               "metadata_file": str(source["metadata_path"]),
               "export_report": str(source["export_path"]),
               "export_report_sha256": fingerprint(source["export_path"]),
               "first_open_utc": source["export"].get("first_open_utc"),
               "last_close_utc": source["export"].get("last_close_utc"),
               "source_consistency_verified": True, "coverage": source["export"].get("coverage"),
               "full_study_file": str(full_output), "full_study_sha256": fingerprint(full_output),
               "costs": {"commission_usd_round_trip_per_lot": 7., "slippage_points_per_side": 10,
                         "spread": "native row spread", "actual_broker_commission_known": False,
                         "historical_fee_conversion": "USDJPY exit quote for JPY; identity for USD profit currency"},
               "qualified": False, "execution_authority": False}
        rows.append(row)
        print(json.dumps({"type": "CROSS_RESULT", **{key: row[key] for key in (
            "symbol", "model", "bars", "trades", "net_r", "censored", "shortfall_to_30860")}}), flush=True)
    if fingerprint(study_path) != study_digest or fingerprint(manifest_path) != manifest_digest:
        raise RuntimeError("Frozen study or native manifest changed during cross evaluation")
    if any(fingerprint(source["csv"]) != source["sha256"] for source in exports.values()):
        raise RuntimeError("Native cross-symbol CSV changed during evaluation")
    report = {"type": "FROZEN_WINNER_LONG_H1_CROSS_SYMBOL_RESEARCH", "created_utc": datetime.now(UTC).isoformat(),
              "selection_study": str(study_path), "selection_study_sha256": study_digest,
              "manifest": str(manifest_path), "manifest_sha256": manifest_digest,
              "selected_model": winner, "selection_fee7_metrics": selection,
              "selection_rule": "Completed EURUSD H1 fee7 top5[0]; fixed before cross-symbol outcomes, >=30 closed trades",
              "rows": rows, **cross_status(rows), "live_changes": False, "orders_sent": 0,
              "fees_evaluated_usd_round_trip_per_lot": [0., 3., 7.],
              "reported_fee_usd_round_trip_per_lot": 7.,
              "limitations": [
                  "Every full source study preserves all three hypothetical fee scenarios; table uses USD7 only",
                  "Gold actual29553bars is1307short of30860; strict completeness remains false even if observed netR is positive",
                  "No future data or fabricated candles; source UTC/session schedule remains unverified",
                  "Observable closed conditional episodes only; censored exposures have unknown R, not zero loss",
                  "Winner chosen on EURUSD archive is post-selection, not independently preregistered future holdout",
                  "Positive cross-symbol observations do not establish statistical significance or executable/live edge",
                  "Quote-price-risk R; USDJPY fee conversion approximates historical exit quote, not conversion bid/ask fills",
                  "Fixed settings and unchanged strategy cards; no model rules, risk limits or learning weights updated",
              ]}
    temporary = output.with_suffix(output.suffix + ".pending")
    temporary.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(output)
    lines = ["# Frozen EURUSD fee7 winner: " + winner, "",
             "| symbol | native H1bars | closed | win% | netR | trade Sharpe | maxDD R | censored | shortfall30860 |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in rows:
        win = "-" if row["win_rate"] is None else f"{100 * row['win_rate']:.2f}"
        sharpe = "-" if row["sharpe"] is None else f"{row['sharpe']:.6f}"
        lines.append(f"|{row['symbol']}|{row['bars']}|{row['trades']}|{win}|{row['net_r']:.6f}|{sharpe}|{row['max_dd']:.6f}|{row['censored']}|{row['shortfall_to_30860']}|")
    lines.extend(["", "Strict cross pass: " + str(report["strict_cross_pass"]),
                  "Censored exposure present: " + str(report["censored_exposures_present"]),
                  "qualified=false; execution_authority=false; no broker orders or live changes.",
                  "USD7/lot round trip, 10points/side, row spread. Censored outcomes are unknown.",
                  "Gold data remain29553bars; no invented completion of the1307bar count shortfall."])
    output.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", type=Path, default=ROOT / "reports/long-study/H1.json")
    parser.add_argument("--manifest", type=Path, default=ROOT / "reports/five-year-cross-history/export-manifest.json")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/long-study/cross.json")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    report = run_cross(args.study, args.manifest, args.output, workers=args.workers)
    print(json.dumps({key: report[key] for key in (
        "selected_model", "all_three_positive_n_ge30", "all_three_native_minimum_30860",
        "strict_cross_pass", "censored_exposures_present", "qualified")}, indent=2), flush=True)


if __name__ == "__main__":
    main()
