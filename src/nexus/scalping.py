"""Pure scalp-session policy; no broker, orders, persistence or extra budget.

The coordinator supplies a verified account book and persists the returned
latch. Execution still requires the current confluence certificate, fresh
cost-adjusted reward/risk and the shared account-wide daily risk authority.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from collections.abc import Mapping

from .risk import MAGIC, cashflow_records, cost_uncertainties, record_matches
from .store import blocks_send

POLICY_DEFINITION = {
    "schema": 1, "execution_style": "SCALP", "minimum_net_reward_risk": 2,
    "risk_budget": "shared_account_daily_limits_no_additional_budget",
    "risk_request": "positive_percent_of_equity_capped_by_shared_risk_authority",
    "confluence": "versioned_authorized_protocol_and_fresh_sender_checks",
    "target_scope": "original_entry_variant_and_session_only",
    "latch": "persisted_session_latch_never_automatically_reset",
    "stop_may_only_tighten": True, "allow_addition": False,
    "profit_percent": "optional_equity_target_volume_cap_broker_step_floor_no_geometry_change",
    "variants": {
        "normal": {"timeframes": ["M1", "M5"], "max_hold_bars": 3,
                   "monitoring": "local_completed_bar_scalp"},
        "fast": {"timeframes": ["M1"], "max_hold_bars": None,
                 "exit_policy": "broker_SL_TP_completed_bar_invalidation_and_daily_risk_no_fixed_timer",
                 "monitoring": "local_faster_monitoring_not_exchange_HFT"},
    },
}
POLICY_REVISION = hashlib.sha256(json.dumps(POLICY_DEFINITION, sort_keys=True,
                                           separators=(",", ":")).encode("utf-8")).hexdigest()


def policy_definition(variant="normal"):
    if variant not in POLICY_DEFINITION["variants"]:
        raise ValueError("Scalp variant must be normal or fast")
    return {"revision": POLICY_REVISION, "variant": variant,
            **copy.deepcopy(POLICY_DEFINITION["variants"][variant]),
            "minimum_net_reward_risk": 2, "additional_risk_budget": 0.,
            "stop_may_only_tighten": True, "allow_addition": False}


def _amount(value, label, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(label + " must be a finite amount")  # noqa: TRY004 -- Keep ValueError validation contract consumed by API handlers and existing risk tests.
    try:
        valid = math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid or (value <= 0 if positive else False):
        raise ValueError(label + " must be finite" + (" and positive" if positive else ""))
    return float(value)


def _flag(value, label):
    if type(value) is not bool:
        raise ValueError(label + " must be boolean")
    return value


def _session_id(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise ValueError("A nonempty scalp session ID is required")
    return value


def validate_scalp_settings(enabled=False, target_value=None, risk_percent=None, variant="normal", min_reward_risk=2, profit_percent=None):
    """Canonical switch and independent goal, without allocating any risk."""
    enabled = _flag(enabled, "Scalp enabled")
    policy_definition(variant)
    min_reward_risk = _amount(min_reward_risk, "Scalp minimum reward/risk", positive=True)
    if min_reward_risk < 2:
        raise ValueError("Scalp minimum reward/risk must be at least 2")
    if target_value is not None:
        target_value = _amount(target_value, "Scalp target", positive=True)
    if enabled and target_value is None:
        raise ValueError("Enabled scalping requires a positive target amount")
    if risk_percent is not None:
        risk_percent = _amount(risk_percent, "Scalp risk percent", positive=True)
        if risk_percent > 100:
            raise ValueError("Scalp risk percent cannot exceed 100")
    if enabled and risk_percent is None:
        raise ValueError("Enabled scalping requires a positive risk percent")
    extra = {}
    if profit_percent is not None:
        profit_percent = _amount(profit_percent, "Scalp profit percent", positive=True)
        if profit_percent > 100: raise ValueError("Scalp profit percent cannot exceed 100")
        extra["profit_percent"] = profit_percent
    return {**extra, "enabled": enabled, "target_value": target_value,
            "risk_percent": risk_percent, "variant": variant, "min_reward_risk": min_reward_risk}


def adaptation_plan(proposal, scalp_session_id, variant="normal"):
    """Adapt the authorized holding policy; the committee must seal it again.

    Price geometry and evidence remain intact. The stale certificate is removed
    because execution style, session and holding plan belong to its binding.
    This function neither approves a signal nor computes a certificate.
    """
    if not isinstance(proposal, Mapping):
        raise ValueError("A confluence proposal is required")  # noqa: TRY004 -- Keep ValueError validation contract consumed by API handlers and existing risk tests.
    policy = policy_definition(variant)
    timeframe = proposal.get("timeframe")
    if timeframe not in policy["timeframes"]:
        raise ValueError("Scalp timeframe is outside the selected variant")
    matrix = proposal.get("decision_matrix")
    revision = proposal.get("protocol_revision")
    if (not isinstance(matrix, Mapping) or matrix.get("passed") is not True or
            not isinstance(revision, str) or len(revision) != 64 or
            any(character not in "0123456789abcdef" for character in revision)):
        raise ValueError("An evaluated confluence proposal is required for scalp adaptation")
    existing = proposal.get("execution_plan", {})
    if not isinstance(existing, Mapping) or existing.get("timeframe", timeframe) != timeframe:
        raise ValueError("Scalp holding plan timeframe disagrees with the proposal")
    hold = existing.get("max_hold_bars", policy["max_hold_bars"])
    if hold is not None and (type(hold) is not int or hold <= 0):
        raise ValueError("Scalp maximum hold must be a positive integer")
    if hold is None and policy["max_hold_bars"] is not None:
        raise ValueError("Normal scalp requires a bounded holding plan")
    result = copy.deepcopy(dict(proposal))
    result["execution_style"] = "SCALP"
    result["scalp_variant"] = variant
    result["scalp_policy_revision"] = POLICY_REVISION
    result["scalp_session_id"] = _session_id(scalp_session_id)
    result["execution_plan"] = {**copy.deepcopy(dict(existing)),
                                "timeframe": timeframe,
                                "max_hold_bars": None if policy["max_hold_bars"] is None else min(hold, policy["max_hold_bars"]),
                                "allow_addition": False, "stop_may_only_tighten": True}
    result["decision_matrix"] = copy.deepcopy(dict(matrix))
    result["decision_matrix"].pop("certificate_hash", None)
    result["certificate_required"] = True
    return result


def target_guard(progress, target_value, *, enabled=True, latched=False, uncertain=False,
                 risk_percent=None, variant="normal"):
    """Stop new scalp entries only; a persisted latch cannot reset itself."""
    settings = validate_scalp_settings(enabled, target_value, risk_percent, variant)
    latched = _flag(latched, "Scalp target latch")
    uncertain = _flag(uncertain, "Scalp progress uncertainty")
    progress = None if progress is None and uncertain else _amount(progress, "Scalp net progress")
    reached = bool(settings["enabled"] and not uncertain and progress is not None and
                   progress >= settings["target_value"])
    return {"target_reached": reached, "should_latch": reached and not latched,
            "latched": latched or reached,
            "entries_allowed": settings["enabled"] and not (latched or reached or uncertain),
            "stop_scope": "SCALP_SESSION_ONLY"}


def snapshot(account, intents, deals, positions, settings, *, session_id,
             closing_reserve_by_intent=None, latched=False, magic=MAGIC):
    """Calculate one session's attributed progress from supplied evidence.

    Separate fees may have magic=0 but need unique proven entry ownership.
    Unallocated account costs conservatively block the goal rather than become
    scalp profits. Closing reserves are supplied by the independent risk layer;
    missing reserves never become zero for an open scalp position.
    """
    if not isinstance(account, str) or not account or not isinstance(settings, Mapping):
        raise ValueError("Account identity and scalp settings are required")
    settings = validate_scalp_settings(settings.get("enabled", False), settings.get("target_value"),
                                       settings.get("risk_percent"), settings.get("variant", "normal"), settings.get("min_reward_risk", 2))
    if session_id is not None:
        session_id = _session_id(session_id)
    elif settings["enabled"]:
        raise ValueError("Enabled scalping requires a scalp session ID")
    if type(magic) is not int or magic <= 0:
        raise ValueError("A valid risk ownership magic is required")
    if not all(isinstance(values, (list, tuple)) for values in (intents, deals, positions)):
        raise ValueError("Complete supplied intent, deal and position books are required")
    account_intents = [row for row in intents if row.get("account_key") == account]
    entries = [row for row in account_intents if row.get("kind") == "ENTRY"]
    selected = {row["id"]: row for row in entries
                if (row.get("payload", {}).get("proposal", {}).get("execution_style") == "SCALP" and
                    row.get("payload", {}).get("proposal", {}).get("scalp_variant") == settings["variant"] and
                    row.get("payload", {}).get("proposal", {}).get("scalp_session_id") == session_id and
                    session_id is not None)}
    records = cashflow_records(deals, account_intents, magic)
    owned = [row for row in records if row["owner_id"] in selected]
    realized = math.fsum(_amount(row["net"], "Scalp cash flow") for row in owned)
    uncertainty = set(cost_uncertainties(records, account_intents))
    unallocated = [row for row in records if row["kind"] != "TRADE" and
                   not row["owner_id"] and not row["foreign"]]
    uncertainty.update("unallocated_cost:" + str(row["deal"].get("ticket", "unknown")) for row in unallocated)
    unresolved = [row["id"] for row in account_intents if blocks_send(row)]
    uncertainty.update("unresolved_intent:" + identity for identity in unresolved)
    open_positions = []
    for position in positions:
        if position.get("magic") != magic:
            continue
        identifier = position.get("identifier", position.get("ticket"))
        owners = [row for row in entries if
                  record_matches(position, row, magic) or
                  (identifier not in (None, 0) and identifier in row.get("payload", {}).get("position_ids", []))]
        if len(owners) == 1 and owners[0]["id"] in selected:
            open_positions.append((position, owners[0]["id"]))
        elif any(row["id"] in selected for row in owners):
            uncertainty.add("ambiguous_scalp_position:" + str(position.get("ticket", "unknown")))
    floating = math.fsum(_amount(row.get("profit"), "Scalp floating profit") +
                         _amount(row.get("swap", 0), "Scalp floating swap")
                         for row, _identity in open_positions)
    reserves = {} if closing_reserve_by_intent is None else closing_reserve_by_intent
    if not isinstance(reserves, Mapping):
        raise ValueError("Closing reserves must be keyed by original entry intent")  # noqa: TRY004 -- Keep ValueError validation contract consumed by API handlers and existing risk tests.
    reserve_values = []
    for identity in sorted({identity for _row, identity in open_positions}):
        if identity not in reserves:
            uncertainty.add("missing_closing_reserve:" + identity)
            continue
        reserve = _amount(reserves[identity], "Scalp closing reserve")
        if reserve < 0:
            raise ValueError("Scalp closing reserve cannot be negative")
        reserve_values.append(reserve)
    closing = math.fsum(reserve_values)
    progress = _amount(realized + floating - closing, "Scalp total net progress")
    guard = target_guard(progress, settings["target_value"], enabled=settings["enabled"],
                         latched=latched, uncertain=bool(uncertainty),
                         risk_percent=settings["risk_percent"], variant=settings["variant"])
    return {**settings, "session_id": session_id, "realized_net": realized,
            "floating_net": floating, "closing_reserve": closing, "progress_net": progress,
            "progress_valid": not uncertainty, "cost_uncertainty": sorted(uncertainty),
            "unattributed_costs": math.fsum(max(0., -row["net"]) for row in unallocated),
            "intent_ids": sorted(selected), "open_positions": len(open_positions),
            "unresolved_intent_ids": unresolved, **guard,
            "target_confirmed": guard["target_reached"] and not open_positions and all(
                row["state"] in ("CLOSED", "REJECTED", "CANCELLED") for row in selected.values()),
            "policy_revision": POLICY_REVISION, "policy": policy_definition(settings["variant"]),
            "risk_budget_scope": "SHARED_ACCOUNT_DAILY_LIMITS", "additional_risk_budget": 0.}
