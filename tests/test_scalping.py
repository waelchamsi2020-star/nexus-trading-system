"""Pure scalp policy fixtures: no broker, database, service or orders."""
import copy
import math
import unittest

from nexus.risk import MAGIC, comment_for
from nexus.scalping import (
    POLICY_REVISION,
    adaptation_plan,
    policy_definition,
    snapshot,
    target_guard,
    validate_scalp_settings,
)


def intent(identity, style="BASE", session=None, account="A", variant="normal"):
    return {"id": identity * 64, "account_key": account, "kind": "ENTRY", "state": "CLOSED", "reserved": 0,
            "payload": {"confirmed": True, "position_ids": [ord(identity)], "result": {"order": ord(identity) * 10},
                        "request": {"symbol": "TEST"},
                        "proposal": {"symbol": "TEST", "execution_style": style, "scalp_session_id": session,
                                     "scalp_variant": variant}}}


def deal(owner, ticket, profit, **extra):
    return {"ticket": ticket, "type": 1, "entry": 1, "symbol": "TEST", "magic": MAGIC,
            "order": ticket, "position_id": owner["payload"]["position_ids"][0],
            "comment": comment_for(owner["id"]), "profit": profit,
            "commission": 0., "fee": 0., "swap": 0., "volume": 1., "time": 1000, **extra}


class ScalpPolicyTests(unittest.TestCase):
    def calculate(self, intents, deals, positions=(), **kwargs):
        return snapshot("A", intents, deals, positions, {"enabled": True, "target_value": 10, "risk_percent": 1},
                        session_id="session-1", **kwargs)

    def test_default_disabled_and_enabled_target_validation(self):
        self.assertEqual(validate_scalp_settings(), {"enabled": False, "target_value": None, "risk_percent": None, "variant": "normal", "min_reward_risk": 2.})
        self.assertEqual(validate_scalp_settings(True, 5, 1), {"enabled": True, "target_value": 5., "risk_percent": 1., "variant": "normal", "min_reward_risk": 2.})
        for value in (None, 0, -1, True, "5", math.nan, math.inf, 10**400):
            with self.subTest(value=str(value)[:20]), self.assertRaises(ValueError):
                validate_scalp_settings(True, value, 1)
        with self.assertRaises(ValueError):
            validate_scalp_settings(1, 5, 1)
        for risk in (None, 0, -1, 101, True, math.nan, math.inf):
            with self.subTest(risk=risk), self.assertRaises(ValueError):
                validate_scalp_settings(True, 5, risk)

    def test_user_profile_survives_disabled_switch_and_ratio_is_validated(self):
        profile = validate_scalp_settings(False, 7, .5, "fast", min_reward_risk=3)
        self.assertEqual((profile["target_value"], profile["risk_percent"], profile["min_reward_risk"]), (7., .5, 3.))
        for value in (1.99, 0, True, math.nan, math.inf):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_scalp_settings(True, 5, 1, min_reward_risk=value)

    def test_original_style_session_and_account_separate_base_and_scalp(self):
        scalp = intent("a", "SCALP", "session-1")
        base = intent("b")
        old_session = intent("c", "SCALP", "older")
        other_account = intent("d", "SCALP", "session-1", "B")
        legacy = intent("e"); legacy["payload"]["proposal"].pop("execution_style")
        rows = [scalp, base, old_session, other_account, legacy]
        flows = [deal(row, index + 1, 12 if row is scalp else 100) for index, row in enumerate(rows)]
        result = self.calculate(rows, flows)
        self.assertEqual(result["realized_net"], 12.)
        self.assertEqual(result["intent_ids"], [scalp["id"]])
        self.assertTrue(result["should_latch"])
        self.assertEqual(result["additional_risk_budget"], 0)
        self.assertEqual(result["stop_scope"], "SCALP_SESSION_ONLY")

    def test_paid_fees_swap_and_uniquely_linked_magic_zero_cost_reduce_net(self):
        scalp = intent("a", "SCALP", "session-1")
        trade = deal(scalp, 1, 15, commission=-2., fee=-1., swap=-1.)
        fee = {"ticket": 2, "type": 7, "magic": 0, "order": 1, "position_id": ord("a"),
               "comment": "", "profit": -2., "time": 1001}
        result = self.calculate([scalp], [trade, fee])
        self.assertEqual(result["realized_net"], 9.)
        self.assertFalse(result["target_reached"])
        self.assertEqual(result["cost_uncertainty"], [])

    def test_external_windfall_does_not_count_and_unallocated_cost_blocks_goal(self):
        scalp = intent("a", "SCALP", "session-1")
        external = {"ticket": 2, "type": 0, "magic": 999, "profit": 1000., "time": 1000}
        fee = {"ticket": 3, "type": 7, "magic": 0, "profit": -1., "time": 1000}
        result = self.calculate([scalp], [deal(scalp, 1, 12), external, fee])
        self.assertEqual(result["realized_net"], 12.)
        self.assertEqual(result["unattributed_costs"], 1.)
        self.assertFalse(result["progress_valid"])
        self.assertFalse(result["target_reached"])
        self.assertFalse(result["entries_allowed"])

    def test_owned_position_floating_swap_and_closing_reserve_only_for_scalp(self):
        scalp = intent("a", "SCALP", "session-1"); base = intent("b")
        position = {"ticket": 90, "identifier": ord("a"), "magic": MAGIC,
                    "comment": comment_for(scalp["id"]), "profit": 8., "swap": -1.}
        external = {"ticket": 91, "identifier": ord("b"), "magic": MAGIC,
                    "comment": comment_for(base["id"]), "profit": 1000., "swap": 0.}
        result = self.calculate([scalp, base], [deal(scalp, 1, 5)], [position, external],
                                closing_reserve_by_intent={scalp["id"]: 3, base["id"]: 99})
        self.assertEqual((result["floating_net"], result["closing_reserve"], result["progress_net"]), (7., 3., 9.))
        self.assertEqual(result["open_positions"], 1)
        self.assertFalse(result["target_confirmed"])

    def test_open_position_never_assumes_missing_closing_reserve_is_zero(self):
        scalp = intent("a", "SCALP", "session-1")
        position = {"ticket": 90, "identifier": ord("a"), "magic": MAGIC,
                    "comment": comment_for(scalp["id"]), "profit": 20.}
        result = self.calculate([scalp], [], [position])
        self.assertFalse(result["progress_valid"])
        self.assertFalse(result["target_reached"])
        with self.assertRaises(ValueError):
            self.calculate([scalp], [], [position], closing_reserve_by_intent={scalp["id"]: -1})

    def test_ambiguous_position_ownership_blocks_progress_instead_of_double_count(self):
        scalp = intent("a", "SCALP", "session-1"); base = intent("b")
        base["payload"]["position_ids"] = scalp["payload"]["position_ids"][:]
        position = {"ticket": 90, "identifier": ord("a"), "magic": MAGIC, "profit": 20.}
        result = self.calculate([scalp, base], [], [position])
        self.assertEqual(result["floating_net"], 0.)
        self.assertFalse(result["progress_valid"])
        self.assertFalse(result["target_reached"])

    def test_unresolved_base_book_also_blocks_scalp_and_does_not_release_risk(self):
        scalp = intent("a", "SCALP", "session-1"); base = intent("b")
        base.update(state="UNKNOWN", reserved=7.)
        before = copy.deepcopy([scalp, base])
        result = self.calculate([scalp, base], [deal(scalp, 1, 12)])
        self.assertFalse(result["entries_allowed"])
        self.assertFalse(result["target_reached"])
        self.assertEqual([scalp, base], before)

    def test_persisted_latch_cannot_reset_after_profit_falls_or_switch_off(self):
        reached = target_guard(12, 10, risk_percent=1)
        self.assertTrue(reached["should_latch"])
        later = target_guard(-2, 10, latched=True, risk_percent=1)
        self.assertTrue(later["latched"])
        self.assertFalse(later["entries_allowed"])
        self.assertFalse(later["should_latch"])
        self.assertTrue(target_guard(0, None, enabled=False, latched=True)["latched"])

    def test_adaptation_is_detached_shortens_holding_and_requires_new_certificate(self):
        proposal = {"timeframe": "M1", "sl": 100., "tp": 130., "protocol_revision": "f" * 64,
                    "decision_matrix": {"passed": True, "certificate_hash": "old", "evidence": [1]},
                    "execution_plan": {"timeframe": "M1", "max_hold_bars": 12, "invalidation": {"price": 100.}}}
        before = copy.deepcopy(proposal)
        adapted = adaptation_plan(proposal, "session-1")
        self.assertEqual(proposal, before)
        self.assertEqual((adapted["sl"], adapted["tp"]), (100., 130.))
        self.assertEqual(adapted["execution_plan"]["max_hold_bars"], 3)
        self.assertTrue(adapted["execution_plan"]["stop_may_only_tighten"])
        self.assertFalse(adapted["execution_plan"]["allow_addition"])
        self.assertNotIn("certificate_hash", adapted["decision_matrix"])
        self.assertTrue(adapted["certificate_required"])
        adapted["execution_plan"]["invalidation"]["price"] = 99
        self.assertEqual(proposal["execution_plan"]["invalidation"]["price"], 100)
        for timeframe in ("M5",):
            proposal["timeframe"] = timeframe; proposal["execution_plan"]["timeframe"] = timeframe
            proposal["execution_plan"]["max_hold_bars"] = 2
            self.assertEqual(adaptation_plan(proposal, "session-1")["execution_plan"]["max_hold_bars"], 2)

    def test_m15_and_unvalidated_arbitrary_entry_cannot_be_adapted(self):
        proposal = {"timeframe": "M15", "protocol_revision": "f" * 64, "decision_matrix": {"passed": True}}
        with self.assertRaises(ValueError):
            adaptation_plan(proposal, "session-1")
        proposal["timeframe"] = "M1"; proposal["decision_matrix"]["passed"] = False
        with self.assertRaises(ValueError):
            adaptation_plan(proposal, "session-1")
        with self.assertRaises(ValueError):
            adaptation_plan({}, "session-1")

    def test_fast_variant_is_m1_without_forced_time_exit_and_needs_recertification(self):
        proposal = {"timeframe": "M1", "protocol_revision": "f" * 64,
                    "decision_matrix": {"passed": True}, "execution_plan": {"max_hold_bars": 12}}
        adapted = adaptation_plan(proposal, "fast-session", "fast")
        self.assertIsNone(adapted["execution_plan"]["max_hold_bars"])
        self.assertEqual(adapted["scalp_variant"], "fast")
        self.assertEqual(adapted["scalp_policy_revision"], POLICY_REVISION)
        self.assertIn("not_exchange_HFT", policy_definition("fast")["monitoring"])
        proposal["timeframe"] = "M5"
        with self.assertRaises(ValueError):
            adaptation_plan(proposal, "fast-session", "fast")
        with self.assertRaises(ValueError):
            validate_scalp_settings(True, 5, 1, "exchange_hft")

    def test_variants_are_separate_even_if_coordinator_supplies_same_session_id(self):
        normal = intent("a", "SCALP", "session-1", variant="normal")
        fast = intent("b", "SCALP", "session-1", variant="fast")
        flows = [deal(normal, 1, 4), deal(fast, 2, 20)]
        result = self.calculate([normal, fast], flows)
        self.assertEqual(result["realized_net"], 4.)
        self.assertFalse(result["target_reached"])
        fast_result = snapshot("A", [normal, fast], flows, [],
                               {"enabled": True, "target_value": 10, "risk_percent": 1, "variant": "fast"},
                               session_id="session-1", latched=True)
        self.assertEqual(fast_result["realized_net"], 20.)
        self.assertTrue(fast_result["latched"])
        self.assertFalse(fast_result["should_latch"])

    def test_policy_definition_returns_detached_evidence(self):
        policy = policy_definition("normal")
        policy["timeframes"].append("M15")
        self.assertEqual(policy_definition("normal")["timeframes"], ["M1", "M5"])
        self.assertRegex(POLICY_REVISION, r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
