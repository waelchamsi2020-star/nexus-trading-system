"""Keep the Phase A tiers aligned with the existing 58-entry catalog."""

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_all_catalog_schools_have_one_tier() -> None:
    catalog = json.loads((ROOT / "docs/school-catalog/catalog.json").read_text(encoding="utf-8"))
    plan = json.loads((ROOT / "config/schools.yaml").read_text(encoding="utf-8"))
    catalog_ids = {school["id"] for school in catalog["schools"]}
    plan_ids = [school["catalog_id"] for school in plan["schools"]]
    assert len(plan_ids) == len(set(plan_ids)) == 58
    assert set(plan_ids) == catalog_ids
    assert Counter(school["tier"] for school in plan["schools"]) == {
        "TIER_1_EXECUTABLE": 12,
        "TIER_2_CONDITIONAL": 14,
        "TIER_3_REFERENCE": 32,
    }
    assert all(
        school["status"] in {"REFERENCE_ONLY", "REFUSED_NO_DATA"}
        for school in plan["schools"]
        if school["tier"] == "TIER_3_REFERENCE"
    )
    assert all("data_requirement" in school for school in plan["schools"])


def test_no_school_is_activated_by_classification() -> None:
    plan = json.loads((ROOT / "config/schools.yaml").read_text(encoding="utf-8"))
    assert all(school["status"] != "ACTIVE" for school in plan["schools"])
    assert plan["llm_signal_generation"] is False


def test_partial_and_approx_are_strictly_conditional() -> None:
    plan = json.loads((ROOT / "config/schools.yaml").read_text(encoding="utf-8"))
    for school in plan["schools"]:
        if school["requested_name"].endswith(("_approx", "_partial")):
            requirement = school["data_requirement"]
            assert school["tier"] == "TIER_2_CONDITIONAL"
            assert requirement["probe_before_build"] is True
            assert requirement["strict_depth_and_signed_flow"] is True
            assert {"depth_history", "signed_trades"} <= set(requirement["required_keys"])
            assert requirement["on_missing"] == "REFUSED_NO_DATA"


def test_head_shoulders_is_a_pattern_not_a_school_name() -> None:
    plan = json.loads((ROOT / "config/schools.yaml").read_text(encoding="utf-8"))
    rows = {school["catalog_id"]: school for school in plan["schools"]}
    assert rows["ta_chart_patterns"]["requested_name"] == "chart_patterns"
    assert rows["ta_chart_patterns"]["patterns"][0] == "HEAD_SHOULDERS"
