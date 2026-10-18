"""Strict four-school send invariants with an entirely in-memory broker.

These tests exercise the independent veto, not the school signal detector.
There is no MT5 connection and no live order in this file.
"""
import copy
import tempfile
import time
import unittest
from decimal import Decimal
from pathlib import Path

from nexus.broker import SimBroker
from nexus.confluence import PROTOCOL_REVISION
from nexus.execution import Executor
from nexus.risk import RiskManager, protocol_certificate_hash
from nexus.store import Store


class ExactMoneyBroker(SimBroker):
    def __init__(self, clock):
        super().__init__(clock)
        self.quote = Decimal(100)
        self.quote_side = "BUY"
        self._prices["STOCK.A"] = 100.
        self.check_count = 0
        self.check_callback = None
        self.target_scale = Decimal(1)
        self.invalid_target_profit = None

    def tick(self, name):
        if name != "STOCK.A":
            return super().tick(name)
        point = Decimal(".01")
        bid = self.quote - point if self.quote_side == "BUY" else self.quote
        ask = self.quote if self.quote_side == "BUY" else self.quote + point
        return {"time": self.clock(), "time_msc": int(self.clock() * 1000),
                "bid": float(bid), "ask": float(ask), "last": float(self.quote)}

    def calc_profit(self, side, name, volume, open_price, close_price):
        direction = Decimal(1) if side == "BUY" else Decimal(-1)
        pnl = ((Decimal(str(close_price)) - Decimal(str(open_price))) * direction *
               Decimal(str(volume)) * Decimal(str(self.symbol(name)["trade_contract_size"])))
        if pnl > 0:
            if self.invalid_target_profit is not None:
                return self.invalid_target_profit
            # Deliberately nonlinear at the actual selected volume. A unit-lot
            # check alone cannot prove the final contract reward/risk ratio.
            if Decimal(str(volume)) > 1:
                pnl *= self.target_scale
        return float(pnl)

    def check(self, request):
        self.check_count += 1
        if self.check_callback:
            self.check_callback(self.check_count, request)
        return super().check(request)


class MinimumRewardRiskTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.now = int(time.time() // 86400) * 86400 + 12 * 3600
        self.broker = ExactMoneyBroker(lambda: self.now)
        self.store = Store(Path(self.temp.name) / "fixture.sqlite3")
        self.risk = RiskManager(self.broker, self.store)
        self.executor = Executor(self.broker, self.store, self.risk, lambda: self.now)
        self.settings = {"daily_risk": 1000., "daily_target": 1000.,
                         "commission_per_lot": 0., "slippage_points": 0.,
                         "decision_protocol": "four_school_v1"}

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def activate(self, **changes):
        return self.executor.activate("AUTO_DEMO", {**self.settings, **changes})

    def proposal(self, side="BUY", **changes):
        self.broker.quote_side = side
        proposal = {"id": "strict-fixture", "symbol": "STOCK.A", "side": side,
                    "strategy_id": "fixture", "version": "1", "timeframe": "M5",
                    "sl": 99. if side == "BUY" else 101.,
                    "tp": 102. if side == "BUY" else 98.,
                    "qualified": True, "news_ok": True,
                    "data_time": self.now - 1, "expires_at": self.now + 120,
                    "protocol_revision": PROTOCOL_REVISION,
                    "decision_matrix": {"passed": True, "fixture": "in-memory guard evidence"},
                    **changes}
        proposal["decision_matrix"]["certificate_hash"] = protocol_certificate_hash(proposal)
        return proposal

    def assert_refused_without_send(self, proposal, expected):
        result = self.executor.execute(proposal)
        self.assertFalse(result["approved"], result)
        self.assertIn(expected, result["reason"])
        self.assertEqual([], self.broker.sent)
        self.assertEqual(0., self.store.snapshot(self.risk.key, self.now)["reserved"])
        return result

    def test_exact_two_buy_and_sell_are_accepted(self):
        self.activate()
        for side in ("BUY", "SELL"):
            with self.subTest(side=side):
                result = self.risk.prepare(self.proposal(side, id="fixture-" + side), now=self.now)
                self.assertTrue(result["approved"], result)
                evidence = result["minimum_rr_evidence"]
                self.assertEqual(Decimal(2), Decimal(evidence["price_reward_risk"]))
                self.assertEqual(Decimal(2), Decimal(evidence["net_reward_risk"]))
                self.assertEqual(100., result["volume"])
                self.store.set_intent_state(result["intent_id"], "REJECTED", reason="fixture cleanup")
        self.assertEqual([], self.broker.sent)

    def test_strict_exact_two_reaches_one_confirmed_synthetic_fill(self):
        self.activate()
        result = self.executor.execute(self.proposal())
        self.assertTrue(result["approved"], result)
        self.assertTrue(result["confirmed"], result)
        self.assertEqual(1, len(self.broker.sent))
        evidence = self.store.intent(result["intent_id"])["payload"]["minimum_rr_evidence"]
        self.assertEqual("2", evidence["minimum"])
        self.assertEqual(Decimal(2), Decimal(evidence["net_reward_risk"]))

    def test_below_two_buy_and_sell_have_no_reservation_or_send(self):
        self.activate()
        for side, target in (("BUY", 101.99), ("SELL", 98.01)):
            with self.subTest(side=side):
                self.assert_refused_without_send(self.proposal(side, tp=target), "price reward/risk")

    def test_decimal_geometry_has_no_epsilon_that_accepts_below_two(self):
        self.activate()
        proposal = self.proposal(tp="101.9999999999999999999999999")
        request = {"symbol": "STOCK.A", "side": "BUY", "volume": 1,
                   "price": "100", "sl": "99", "tp": proposal["tp"]}
        with self.assertRaisesRegex(ValueError, "price reward/risk"):
            self.risk.minimum_rr_check(proposal, request, self.broker.symbol("STOCK.A"))

    def test_round_trip_commission_can_turn_nominal_two_into_rejection(self):
        self.activate(commission_per_lot=.01)
        self.assert_refused_without_send(self.proposal(), "net reward/risk after costs")

    def test_user_requested_three_is_bound_and_rejects_an_otherwise_valid_two(self):
        self.activate()
        self.assert_refused_without_send(self.proposal(tp=102.4, requested_min_reward_risk=3), "below 1:3")
        result = self.risk.prepare(self.proposal(tp=103., requested_min_reward_risk=3), now=self.now)
        self.assertTrue(result["approved"], result)
        self.assertEqual("3", result["minimum_rr_evidence"]["minimum"])
        self.store.set_intent_state(result["intent_id"], "REJECTED", reason="fixture cleanup")
        changed = self.proposal(tp=103., requested_min_reward_risk=3)
        changed["requested_min_reward_risk"] = 2
        self.assert_refused_without_send(changed, "certificate")

    def test_requested_minimum_cannot_bypass_two_or_accept_nonfinite(self):
        self.activate()
        for value in (1.99, 0, -1, True, "NaN", "Infinity"):
            with self.subTest(value=value):
                self.assert_refused_without_send(self.proposal(tp=103., requested_min_reward_risk=value), "reward/risk minimum")

    def test_higher_minimum_also_applies_after_costs_without_changing_target(self):
        self.activate(commission_per_lot=.01)
        proposal = self.proposal(tp=103., requested_min_reward_risk=3)
        self.assert_refused_without_send(proposal, "net reward/risk after costs is below 1:3")
        self.assertEqual(103., proposal["tp"])

    def test_exact_net_two_after_commission_is_accepted(self):
        self.activate(commission_per_lot=.01)
        result = self.risk.prepare(self.proposal(tp=102.03), now=self.now)
        self.assertTrue(result["approved"], result)
        self.assertEqual(Decimal(2), Decimal(result["minimum_rr_evidence"]["net_reward_risk"]))

    def test_slippage_reserves_entry_stop_and_target_for_both_sides(self):
        self.activate(slippage_points=1)
        for side, target in (("BUY", 102.06), ("SELL", 97.94)):
            with self.subTest(side=side):
                self.assert_refused_without_send(self.proposal(side), "net reward/risk after costs")
                result = self.risk.prepare(self.proposal(side, tp=target, id="slippage-" + side), now=self.now)
                self.assertTrue(result["approved"], result)
                evidence = result["minimum_rr_evidence"]
                self.assertEqual(Decimal(2), Decimal(evidence["net_reward_risk"]))
                self.assertEqual(Decimal("100.01") if side == "BUY" else Decimal("99.99"),
                                 Decimal(evidence["worst_entry"]))
                self.assertEqual(Decimal("98.99") if side == "BUY" else Decimal("101.01"),
                                 Decimal(evidence["worst_stop"]))
                self.assertEqual(Decimal("102.05") if side == "BUY" else Decimal("97.95"),
                                 Decimal(evidence["worst_target"]))
                self.store.set_intent_state(result["intent_id"], "REJECTED", reason="fixture cleanup")

    def test_nonlinear_profit_is_checked_at_final_selected_volume(self):
        self.activate()
        self.broker.target_scale = Decimal(".99")
        self.assert_refused_without_send(self.proposal(), "net reward/risk after costs")

    def test_nonfinite_broker_reward_is_refused(self):
        self.activate()
        self.broker.invalid_target_profit = float("nan")
        self.assert_refused_without_send(self.proposal(), "Broker reward/risk calculation")

    def test_missing_false_unknown_revision_and_changed_matrix_are_refused(self):
        self.activate()
        missing = self.proposal(); missing.pop("decision_matrix")
        false = self.proposal(); false["decision_matrix"]["passed"] = False
        unknown = self.proposal(); unknown["protocol_revision"] = "f" * 64
        unknown["decision_matrix"]["certificate_hash"] = protocol_certificate_hash(unknown)
        tampered = self.proposal(); tampered["decision_matrix"]["fixture"] = "changed after certification"
        for proposal, expected in ((missing, "confluence certificate"), (false, "confluence certificate"),
                                   (unknown, "protocol revision"), (tampered, "missing or changed")):
            with self.subTest(expected=expected):
                self.assert_refused_without_send(proposal, expected)

    def test_certificate_binds_original_geometry_and_entry_zone(self):
        self.activate()
        for field, change in (("tp", 103.), ("sl", 98.), ("entry_zone", [99., 101.]),
                              ("timeframe", "M1"), ("symbol", "GOLD#"),
                              ("execution_style", "SCALP"), ("scalp_session_id", "session-2"),
                              ("scalp_variant", "fast"), ("requested_risk_percent", .005),
                              ("execution_policy_revision", "changed"), ("scalp_policy_revision", "changed")):
            with self.subTest(field=field):
                proposal = self.proposal(); proposal[field] = change
                self.assert_refused_without_send(proposal, "missing or changed")

    def test_request_cannot_stretch_target_or_widen_certified_stop(self):
        self.activate()
        proposal = self.proposal()
        request = {"symbol": "STOCK.A", "side": "BUY", "volume": 1,
                   "price": 100., "sl": 99., "tp": 102.}
        for field, value in (("sl", 98.), ("tp", 103.)):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'Certified structural stop or TP1 changed'):
                self.risk.minimum_rr_check(proposal, {**request, field: value}, self.broker.symbol('STOCK.A'))

    def test_adverse_quote_change_before_send_fails_rr_without_altering_target(self):
        self.activate()
        self.broker.check_callback = lambda count, request: setattr(self.broker, "quote", Decimal("100.01")) if count == 1 else None
        self.assert_refused_without_send(self.proposal(), "price reward/risk")

    def test_quote_change_during_final_order_check_is_refused_without_repost(self):
        self.activate()
        self.broker.check_callback = lambda count, request: setattr(self.broker, "quote", Decimal("99.99")) if count == 2 else None
        self.assert_refused_without_send(self.proposal(), "Quote changed during broker preflight")
        self.assertEqual(2, self.broker.check_count)

    def test_tick_grid_change_before_send_is_refused(self):
        self.activate()
        def change_grid(count, request):
            if count == 1:
                self.broker._symbols["STOCK.A"]["trade_tick_size"] = .07
        self.broker.check_callback = change_grid
        self.assert_refused_without_send(self.proposal(), "off the broker price grid")

    def test_tampered_durable_certificate_is_rechecked_immediately_before_send(self):
        self.activate()
        result = self.risk.prepare(self.proposal(), now=self.now)
        self.assertTrue(result["approved"], result)
        payload = copy.deepcopy(self.store.intent(result["intent_id"])["payload"])
        payload["proposal"]["decision_matrix"]["fixture"] = "modified in stored proposal"
        self.store.set_intent_state(result["intent_id"], "PREPARED", proposal=payload["proposal"])
        refused = self.executor._send(result["intent_id"], entry=True)
        self.assertFalse(refused["approved"], refused)
        self.assertIn("missing or changed", refused["reason"])
        self.assertEqual([], self.broker.sent)
        self.assertEqual("REJECTED", self.store.intent(result["intent_id"])["state"])

    def test_unknown_setting_is_rejected_and_general_default_is_compatible(self):
        with self.assertRaisesRegex(ValueError, "Unknown decision protocol"):
            self.activate(decision_protocol="not-a-protocol")
        legacy = {k: v for k, v in self.settings.items() if k != "decision_protocol"}
        self.executor.activate("AUTO_DEMO", legacy)
        proposal = self.proposal(tp=101.5)
        proposal.pop("decision_matrix"); proposal.pop("protocol_revision")
        result = self.executor.execute(proposal)
        self.assertTrue(result["approved"], result)
        self.assertEqual("general", self.risk.settings["decision_protocol"])
        self.assertEqual(1, len(self.broker.sent))

    def test_normal_and_fast_scalp_percent_reduce_lots_without_extra_budget(self):
        self.activate()
        for variant in ("normal", "fast"):
            with self.subTest(variant=variant):
                proposal = self.proposal(id="scalp-" + variant, execution_style="SCALP",
                                         scalp_variant=variant, requested_risk_percent=.005)
                result = self.risk.prepare(proposal, now=self.now)
                self.assertTrue(result["approved"], result)
                self.assertEqual(.5, result["volume"])
                self.assertEqual(.5, result["risk"])
                self.assertEqual(.005, result["requested_risk_percent"])
                self.assertEqual(.5, result["requested_risk_amount"])
                self.assertEqual(.5, result["actual_risk_cap"])
                self.assertEqual(10000., result["equity_at_risk_sizing"])
                payload = self.store.intent(result["intent_id"])["payload"]
                self.assertEqual(.5, payload["actual_risk_cap"])
                self.store.set_intent_state(result["intent_id"], "REJECTED", reason="fixture cleanup")
        self.assertEqual([], self.broker.sent)

    def test_large_scalp_percent_cannot_override_shared_daily_or_trade_cap(self):
        self.activate(daily_risk=50., daily_target=100.)
        proposal = self.proposal(execution_style="SCALP", scalp_variant="fast",
                                 requested_risk_percent=100., max_risk_amount=1000000.)
        result = self.risk.prepare(proposal, now=self.now)
        self.assertTrue(result["approved"], result)
        self.assertEqual(10000., result["requested_risk_amount"])
        self.assertEqual(10., result["actual_risk_cap"])
        self.assertEqual(10., result["volume"])
        self.assertEqual(10., result["risk"])
        self.assertEqual(50., self.risk.snapshot(self.now)["risk_amount"])

    def test_scalp_cap_uses_fresh_broker_equity_instead_of_supplied_amount(self):
        self.activate()
        proposal = self.proposal(execution_style="SCALP", requested_risk_percent=.01,
                                 max_risk_amount=999999., equity_at_risk_sizing=999999.)
        self.broker._account["balance"] = 1000.
        result = self.risk.prepare(proposal, now=self.now)
        self.assertTrue(result["approved"], result)
        self.assertEqual(1000., result["equity_at_risk_sizing"])
        self.assertEqual(.1, result["requested_risk_amount"])
        self.assertEqual(.1, result["volume"])

    def test_invalid_scalp_percent_and_variant_are_refused(self):
        self.activate()
        for value in (None, True, 0, -.1, 101., "NaN", "Infinity", "invalid"):
            with self.subTest(value=value):
                proposal = self.proposal(execution_style="SCALP", requested_risk_percent=value)
                self.assert_refused_without_send(proposal, "Scalp risk percent")
        self.assert_refused_without_send(self.proposal(execution_style="SCALP", scalp_variant="unknown",
                                                     requested_risk_percent=.1), "Unknown scalp variant")
        with self.assertRaisesRegex(ValueError, "Scalp risk percent"):
            self.risk.scalp_risk_cap({"execution_style": "SCALP", "requested_risk_percent": float("nan")},
                                    self.broker.account())

    def test_equity_drop_after_sizing_blocks_scalp_send_without_resizing(self):
        self.activate()
        self.broker.check_callback = lambda count, request: self.broker._account.update(balance=1000.) if count == 1 else None
        self.assert_refused_without_send(self.proposal(execution_style="SCALP", requested_risk_percent=.005),
                                         "percentage of current Equity")

    def test_base_keeps_existing_budget_policy(self):
        self.activate()
        result = self.risk.prepare(self.proposal(execution_style="BASE", requested_risk_percent="invalid",
                                                scalp_variant="unknown"), now=self.now)
        self.assertTrue(result["approved"], result)
        self.assertEqual(100., result["volume"])
        self.assertNotIn("actual_risk_cap", result)


if __name__ == "__main__":
    unittest.main()
