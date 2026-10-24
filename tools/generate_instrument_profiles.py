"""Convert a read-only MT5 discovery snapshot into a review-only YAML profile.

The emitted document is JSON-compatible YAML, so the generator needs only the
Python standard library. It never enables an instrument and never writes
broker identity or credentials into the generated configuration.
"""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

POLICY_DISABLED_CRYPTO_FRAMES = {"crypto": {"M1", "M5"}}
TIMEFRAMES = ("M1", "M5", "M15", "M30", "H1", "H4", "D1")


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"Expected an object in {path}")
    return value


def build_profiles(snapshot: dict[str, Any], previous: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create disabled-by-default profiles from measured facts only."""
    if snapshot.get("terminal_connected") is not True or snapshot.get("account_trade_mode") != 0:
        raise ValueError("Discovery evidence must come from a connected Demo account")
    spread_policy = snapshot.get("spread_eligibility_policy", "")
    if not isinstance(spread_policy, str) or "no independent spread rejection" not in spread_policy.lower():
        raise ValueError("Snapshot does not declare the no-independent-spread-gate policy")

    rows = snapshot.get("rows")
    if not isinstance(rows, list):
        raise TypeError("Discovery snapshot has no rows")
    symbols: dict[str, Any] = {}
    for row in rows:
        symbol = row.get("symbol")
        category = row.get("class")
        if not isinstance(symbol, str) or not symbol or symbol in symbols:
            raise ValueError("Instrument names must be unique, non-empty strings")
        if not isinstance(category, str) or not category:
            raise ValueError(f"Instrument {symbol} has no class")
        evaluations = {item.get("frame"): item for item in row.get("frame_eval", [])}
        frames = {}
        for timeframe in TIMEFRAMES:
            item = evaluations.get(timeframe, {})
            policy_disabled = timeframe in POLICY_DISABLED_CRYPTO_FRAMES.get(category, set())
            frames[timeframe] = {
                "atr_median": row.get("atr_median", {}).get(timeframe),
                "bar_age_seconds": row.get("bar_age_s", {}).get(timeframe),
                "minimum_risk_usd": item.get("minimum_risk_usd"),
                "spread_target_ratio_p90": item.get("cost_ratio_informational_only"),
                "data_sufficient": bool(item.get("data_sufficient")) and not policy_disabled,
                "status": "DISABLED_BY_POLICY" if policy_disabled else (
                    "RESEARCH_CANDIDATE" if item.get("candidate") else "NOT_ELIGIBLE"
                ),
                "measurement": "NOT_MEASURED_POLICY_DISABLED" if policy_disabled else None,
            }
        enabled_frames = [frame for frame, details in frames.items()
                          if details["status"] == "RESEARCH_CANDIDATE"]
        symbols[symbol] = {
            "class": category,
            "broker_path": row.get("path"),
            "description": row.get("description"),
            "contract": {
                key: row.get(key) for key in (
                    "trade_mode", "tradeable_mode", "point", "tick_size", "tick_value",
                    "volume_min", "volume_step", "volume_max", "stops_level", "contract_size",
                )
            },
            "observed": {
                "quote_age_seconds_at_scan": row.get("tick_age_s"),
                "spread_median": row.get("spread_median"),
                "spread_p90": row.get("spread_p90"),
                "spread_sample_count": row.get("spread_n"),
                "spread_coverage_seconds": row.get("spread_coverage_s"),
            },
            "frames": frames,
            "routing": {
                "enabled": False,
                "strategy": None,
                "candidate_frames": enabled_frames,
                "status": "RESEARCH_ONLY" if enabled_frames else "DISABLED",
                "reason": row.get("verdict_reason", "Requires separately validated strategy and manual activation"),
            },
        }

    overrides = (previous or {}).get("operator_overrides", {})
    if not isinstance(overrides, dict):
        raise TypeError("Existing operator_overrides must remain a mapping")
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "source_snapshot": "read-only MT5 Market Watch discovery",
        "discovery_completed_at_utc": snapshot.get("collected_end_utc"),
        "spread_policy": {
            "independent_rejection_gate": False,
            "measure_for_visibility": True,
            "include_actual_execution_cost_in_risk": True,
            "risk_veto_remains_mandatory": True,
        },
        "activation_policy": "Generated profiles are research-only; generator never enables order routing.",
        "session_hours_status": snapshot.get("session_hours_status"),
        "crypto_m1_m5_status": "DISABLED_FINAL_NOT_MEASURED",
        "symbols": symbols,
        "operator_overrides": overrides,
    }


def write_profiles(source: Path, output: Path) -> dict[str, Any]:
    existing = _load(output) if output.exists() else None
    value = build_profiles(_load(source), existing)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Read-only discovery JSON")
    parser.add_argument("--output", type=Path, default=Path("config/instruments.yaml"))
    args = parser.parse_args()
    value = write_profiles(args.source, args.output)
    enabled = sum(1 for profile in value["symbols"].values() if profile["routing"]["enabled"])
    print(json.dumps({"symbols": len(value["symbols"]), "enabled": enabled,
                      "research_only": sum(p["routing"]["status"] == "RESEARCH_ONLY" for p in value["symbols"].values()),
                      "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
