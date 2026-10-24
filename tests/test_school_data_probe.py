"""Missing MT5 evidence must refuse conditional schools before code promotion."""

import json
from pathlib import Path

from strategies.data_probe import assess_school

ROOT = Path(__file__).resolve().parents[1]
ROWS = {
    row["catalog_id"]: row
    for row in json.loads((ROOT / "config/schools.yaml").read_text(encoding="utf-8"))["schools"]
}


def test_partial_wyckoff_refuses_without_depth_and_signed_flow() -> None:
    result = assess_school(
        ROWS["ta_wyckoff"],
        {"source": "MT5_READ_ONLY", "symbol": "EURUSD", "evidence": {
            "completed_ohlc": True, "tick_volume": True, "real_volume": True,
        }},
    )
    assert result["status"] == "REFUSED_NO_DATA"
    assert {"depth_history", "signed_trades"} <= set(result["missing"])
    assert result["execution_authority"] is False


def test_probe_cannot_activate_even_when_all_requirements_are_reported() -> None:
    school = ROWS["ta_classical"]
    result = assess_school(
        school,
        {"source": "MT5_READ_ONLY", "symbol": "EURUSD", "evidence": {
            key: True for key in school["data_requirement"]["required_keys"]
        }},
    )
    assert result["status"] == "DATA_AVAILABLE_RESEARCH_ONLY"
    assert result["execution_authority"] is False


def test_untrusted_probe_source_is_refused() -> None:
    school = ROWS["ta_classical"]
    result = assess_school(
        school,
        {"source": "UNKNOWN", "symbol": "EURUSD", "evidence": {
            key: True for key in school["data_requirement"]["required_keys"]
        }},
    )
    assert result["status"] == "REFUSED_NO_DATA"
