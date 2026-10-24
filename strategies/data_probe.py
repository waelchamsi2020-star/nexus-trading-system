"""Read-only MT5 evidence probe for Phase A school eligibility.

Historical depth and signed aggressor trades are deliberately unavailable here:
the standard MT5 Python calls used by this project cannot prove either history.
No broker order API is accessed by this module.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _field(row: Any, name: str, default: Any = None) -> Any:
    return row.get(name, default) if isinstance(row, Mapping) else getattr(row, name, default)


def probe_symbol(mt5: Any, symbol: str, *, partner_symbol: str | None = None) -> dict[str, Any]:
    """Measure only observations that this MT5 adapter can verify directly."""
    info = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)
    m1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 1, 64)
    daily = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 1, 30)
    rows = [] if m1 is None else list(m1)
    days = [] if daily is None else list(daily)
    partner_rows = []
    if partner_symbol:
        partner = mt5.copy_rates_from_pos(partner_symbol, mt5.TIMEFRAME_M1, 1, 64)
        partner_rows = [] if partner is None else list(partner)
    evidence = {
        "completed_ohlc": len(rows) >= 2,
        "tick_volume": any((_field(row, "tick_volume", 0) or 0) > 0 for row in rows),
        "session_clock": bool(_field(tick, "time_msc", 0) or _field(tick, "time", 0)),
        "long_history": len(days) >= 30,
        "paired_history": len(rows) >= 2 and len(partner_rows) >= 2,
        "real_volume": any((_field(row, "real_volume", 0) or 0) > 0 for row in rows),
        "depth_history": False,
        "signed_trades": False,
    }
    return {
        "symbol": symbol,
        "source": "MT5_READ_ONLY",
        "symbol_info_available": info is not None,
        "m1_closed_bars": len(rows),
        "daily_closed_bars": len(days),
        "partner_m1_closed_bars": len(partner_rows),
        "evidence": evidence,
    }


def assess_school(school: Mapping[str, Any], probe: Mapping[str, Any]) -> dict[str, Any]:
    """Apply the config's refusal rule; never promote a school to ACTIVE."""
    required = school["data_requirement"]["required_keys"]
    evidence = probe.get("evidence", {})
    missing = [key for key in required if evidence.get(key) is not True]
    if probe.get("source") != "MT5_READ_ONLY":
        missing = sorted(set(missing) | set(required))
    if school["tier"] == "TIER_3_REFERENCE":
        status = school["status"]
    else:
        status = "REFUSED_NO_DATA" if missing else "DATA_AVAILABLE_RESEARCH_ONLY"
    return {
        "catalog_id": school["catalog_id"],
        "symbol": probe.get("symbol"),
        "status": status,
        "required_count": len(required),
        "verified_count": len(required) - len(missing),
        "missing": missing,
        "execution_authority": False,
    }
