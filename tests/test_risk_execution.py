"""Safety invariants against explicitly synthetic broker fixtures; no live sends."""
import copy
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from nexus.broker import BrokerError, SimBroker
from nexus.execution import Executor
from nexus.risk import RiskManager
from nexus.store import Store


class SafetyBroker(SimBroker):
    def __init__(self, clock):
        super().__init__(clock)
        self.actual_commission = 0.
        self.special = None
        self.check_hook = None
        self.history_missing = False
        self.tick_age = 0.
        self.calendar_known = True

    def calendar(self):
        return {**super().calendar(), "known": self.calendar_known, "coverage_known": self.calendar_known}

    def tick(self, symbol):
        return {**super().tick(symbol), "time": self.clock() - self.tick_age}

    def check(self, request):
        if self.check_hook:
            callback, self.check_hook = self.check_hook, None
            callback(request)
        return super().check(request)

    def history_orders(self, since):
        if self.history_missing:
            return []
        return super().history_orders(since)

    def send(self, request):
        special, self.special = self.special, None
        if special == "reject":
            self.sent.append(copy.deepcopy(request))
            return {"retcode": 10006, "comment": "explicit fixture rejection"}
        if special == "unknown_no_fill":
            self.sent.append(copy.deepcopy(request))
            raise BrokerError("fixture network result unknown")
        before = len(self._deals)
        try:
            result = super().send(request)
        except Exception:
            for deal in self._deals[before:]:
                deal["commission"] = -self.actual_commission * deal["volume"] / 2
                self._account["balance"] += deal["commission"]
            raise
        for deal in self._deals[before:]:
            deal["commission"] = -self.actual_commission * deal["volume"] / 2
            self._account["balance"] += deal["commission"]
        if special == "none_after_fill":
            return None
        if special == "timeout_after_fill":
            return {"retcode": 10012}
        if special == "processing_error_after_fill":
            return {"retcode": 10011}
        if special == "malformed_success_after_fill":
            return {"retcode": "10009"}
        if type(special) is int:
            return {"retcode": special}
        return result


class RiskExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "synthetic.sqlite3"
        self.now = int(time.time() // 86400) * 86400 + 12 * 3600
        self.broker = SafetyBroker(lambda: self.now)
        self.store = Store(self.path)
        self.risk = RiskManager(self.broker, self.store)
        self.executor = Executor(self.broker, self.store, self.risk, lambda: self.now)
        self.settings = {"daily_risk": 1000., "daily_target": 1000., "commission_per_lot": 0.,
                         "slippage_points": 10, "max_trade_fraction": .2, "correlation_cap_fraction": .5}

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def activate(self, **overrides):
        return self.executor.activate("AUTO_DEMO", {**self.settings, **overrides})

    def proposal(self, identity="signal-1", **overrides):
        return {"id": identity, "symbol": "EURUSD.demo", "side": "BUY", "sl": 1.075,
                "tp": 1.09, "qualified": True, "news_ok": True,
                "data_time": self.now - 1, "expires_at": self.now + 120, **overrides}

    def entry(self, **overrides):
        self.activate()
        result = self.executor.execute(self.proposal(**overrides))
        self.assertTrue(result["approved"], result)
        return result

    def test_initial_read_only_and_manual_approval(self):
        denied = self.executor.execute(self.proposal())
        self.assertFalse(denied["approved"])
        self.assertEqual([], self.broker.sent)
        self.executor.activate("MANUAL_DEMO", self.settings)
        self.assertFalse(self.executor.execute(self.proposal())["approved"])
        self.assertTrue(self.executor.execute(self.proposal(), approved=True)["approved"])
        self.assertEqual(1, len(self.broker.sent))

    def test_activation_rejects_real_contest_unknown_and_boolean(self):
        for mode in (1, 2, None, False):
            with self.subTest(mode=mode):
                self.broker._account["trade_mode"] = mode
                with self.assertRaises(ValueError):
                    self.activate()
                self.assertEqual("READ_ONLY", self.executor.mode)
        self.assertEqual([], self.broker.sent)

    def test_demo_to_demo_account_switch_before_send_is_rejected(self):
        self.activate()
        self.broker.check_hook = lambda request: self.broker._account.update(login=900002)
        result = self.executor.execute(self.proposal())
        self.assertFalse(result["approved"])
        self.assertEqual([], self.broker.sent)
        self.assertEqual("READ_ONLY", self.executor.mode)
        self.assertEqual(0., self.store.snapshot(self.risk.key, self.now)["reserved"])

    def test_switch_to_real_blocks_close_cancel_and_protection(self):
        result = self.entry()
        self.broker._account["trade_mode"] = 2
        self.assertFalse(self.executor.flatten_owned_positions()["ok"])
        self.assertFalse(self.executor.cancel_owned_orders()["ok"])
        self.assertFalse(self.executor.manage()["ok"])
        self.assertEqual(1, len(self.broker.sent))
        self.assertEqual("READ_ONLY", self.executor.mode)
        self.assertGreater(self.store.intent(result["intent_id"])["reserved"], 0)

    def test_terminal_permission_failure_blocks_all_sends(self):
        self.activate()
        self.broker._account["trade_allowed"] = False
        self.assertFalse(self.executor.execute(self.proposal())["approved"])
        self.assertEqual("READ_ONLY", self.executor.mode)
        self.assertEqual([], self.broker.sent)

    def test_disconnect_invalidates_and_reconnect_needs_activation(self):
        self.activate()
        self.broker.connected = False
        self.assertFalse(self.executor.execute(self.proposal())["approved"])
        self.broker.connected = True
        self.assertFalse(self.executor.execute(self.proposal())["approved"])
        self.assertEqual("READ_ONLY", self.executor.mode)
        self.activate()
        self.assertTrue(self.executor.execute(self.proposal())["approved"])

    def test_known_commission_required_and_nonfinite_settings_rejected(self):
        settings = dict(self.settings)
        settings.pop("commission_per_lot")
        with self.assertRaises(ValueError):
            self.executor.activate("AUTO_DEMO", settings)
        for field, value in (("daily_risk", float("nan")), ("daily_target", -1), ("commission_per_lot", -1), ("slippage_points", float("inf"))):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.activate(**{field: value})

    def test_percent_conversion_and_day_limits_survive_reactivation_deposit_restart(self):
        self.activate(daily_risk=1, daily_target=2, risk_unit="percent", target_unit="percent")
        day = self.store.get_day(self.risk.key, self.now)
        self.assertEqual(100., day["risk_amount"])
        self.assertEqual(200., day["target_amount"])
        self.broker._account["balance"] += 5000
        self.activate(daily_risk=5000, daily_target=5000)
        self.assertEqual(100., self.risk.settings["risk_amount"])
        self.store.close()
        self.store = Store(self.path)
        self.risk = RiskManager(self.broker, self.store)
        self.executor = Executor(self.broker, self.store, self.risk, lambda: self.now)
        self.assertEqual("READ_ONLY", self.executor.mode)
        self.activate(daily_risk=9000, daily_target=9000)
        self.assertEqual(100., self.risk.settings["risk_amount"])

    def test_day_rollover_requires_activation_and_old_reservations_carry(self):
        result = self.entry()
        reservation = self.store.intent(result["intent_id"])["reserved"]
        self.now = (int(self.now // 86400) + 1) * 86400 + 1
        self.assertFalse(self.executor.execute(self.proposal("next-day"))["approved"])
        self.assertEqual("READ_ONLY", self.executor.mode)
        self.activate(daily_risk=800)
        self.assertEqual(800, self.risk.snapshot(self.now)["risk_amount"])
        self.assertAlmostEqual(reservation, self.risk.snapshot(self.now)["reserved"])

    def test_contract_specific_risk_and_lot_rounding(self):
        self.activate()
        for name, sl, tp in (("EURUSD.demo", 1.075, 1.09), ("GOLD#", 2430, 2490), ("US500.cash", 5170, 5270), ("OIL-FUT", 71, 77), ("STOCK.A", 205, 220)):
            with self.subTest(symbol=name):
                proposal = self.proposal(name, symbol=name, sl=sl, tp=tp)
                result = self.risk.prepare(proposal, now=self.now)
                self.assertTrue(result["approved"], result)
                request = result["request"]
                info = self.broker.symbol(name)
                expected = -self.broker.calc_profit("BUY", name, request["volume"], request["price"] + 10 * info["point"], sl - 10 * info["point"])
                self.assertAlmostEqual(expected, result["risk"])
                self.assertLessEqual(result["risk"], 200 + 1e-8)
                self.assertAlmostEqual(request["volume"] / info["volume_step"], round(request["volume"] / info["volume_step"]))
                self.store.set_intent_state(result["intent_id"], "REJECTED", reason="fixture reservation cleanup")

    def test_minimum_lot_over_budget_and_margin_exhaustion_rejected(self):
        self.activate(daily_risk=1)
        result = self.executor.execute(self.proposal())
        self.assertFalse(result["approved"])
        self.assertIn("Minimum", result["reason"])
        self.broker.calc_margin = lambda *args: 1e9
        result = self.executor.execute(self.proposal("margin"))
        self.assertFalse(result["approved"])
        self.assertEqual([], self.broker.sent)

    def test_direction_price_grid_stop_session_and_news_gates(self):
        self.activate()
        cases = ({"qualified": False}, {"news_ok": False}, {"expires_at": self.now - 1},
                 {"data_time": self.now + 1}, {"sl": 1.085}, {"tp": 1.07},
                 {"sl": 1.0750001}, {"symbol": "CLOSED.asset", "sl": 49, "tp": 52},
                 {"allow_additions": True})
        for i, changes in enumerate(cases):
            with self.subTest(changes=changes):
                self.assertFalse(self.executor.execute(self.proposal(str(i), **changes))["approved"])
        self.broker._symbols["EURUSD.demo"]["trade_mode"] = 2
        self.assertFalse(self.executor.execute(self.proposal("short-only"))["approved"])
        self.assertEqual([], self.broker.sent)

    def test_unknown_calendar_and_stale_quote_refuse(self):
        self.activate()
        self.broker.calendar_known = False
        self.assertFalse(self.executor.execute(self.proposal())["approved"])
        self.broker.calendar_known = True
        self.broker.tick_age = 60
        self.assertFalse(self.executor.execute(self.proposal())["approved"])
        self.assertEqual([], self.broker.sent)

    def test_stale_symbol_quote_does_not_latch_account_wide_entry_pause(self):
        self.activate();self.broker.tick_age=60
        with self.assertRaises(ValueError):self.executor._fresh_price({"symbol":"EURUSD.demo"})
        self.assertFalse(self.executor.entries_paused)
        self.broker.tick_age=0
        self.assertTrue(self.executor.execute(self.proposal())["approved"])

    def test_external_positions_and_pending_orders_consume_whole_account_budget(self):
        result = self.entry()
        self.broker._positions.append({**self.broker._positions[0], "ticket": 9999, "identifier": 9999,
                                       "magic": 123, "comment": "external", "sl": 0.})
        book = self.risk.snapshot(self.now)
        self.assertTrue(book["unbounded"])
        self.assertEqual(0., book["remaining"])
        self.assertFalse(self.executor.execute(self.proposal("other"))["approved"])
        self.broker._positions.pop()
        self.broker._orders.append({"ticket": 7777, "symbol": "EURUSD.demo", "magic": 123, "comment": "external"})
        self.assertFalse(self.executor.execute(self.proposal("pending"))["approved"])
        self.assertGreater(self.store.intent(result["intent_id"])["reserved"], 0)

    def test_realized_trading_gains_offset_losses_but_deposits_do_not_expand_limit(self):
        self.activate()
        self.broker._deals.extend([
            {"type": 0, "entry": 1, "time": self.now, "profit": -100, "commission": -5, "swap": -2, "fee": -1, "magic": 123},
            {"type": 1, "entry": 1, "time": self.now, "profit": 500, "commission": 0, "magic": 123},
            {"type": 2, "time": self.now, "profit": -5000, "magic": 0},
        ])
        book = self.risk.snapshot(self.now)
        self.assertEqual(108, book["realized_losses"])
        self.assertEqual(392, book["account_realized_net"])
        self.assertEqual(0, book["realized_net_loss"])
        self.assertEqual(1000, book["remaining"])
        self.assertEqual(0, book["realized_net"])

    def test_net_daily_loss_regression_and_existing_reservation(self):
        self.activate(daily_risk=50)
        self.broker._deals.extend([
            {"type":0,"entry":1,"time":self.now,"profit":-45.05,"magic":123},
            {"type":1,"entry":1,"time":self.now,"profit":34.46,"magic":123}])
        book=self.risk.snapshot(self.now)
        self.assertAlmostEqual(book['realized_net_loss'],10.59)
        self.assertAlmostEqual(book['remaining'],39.41)
        self.assertFalse(book['loss_limit_reached'])
        result=self.executor.execute(self.proposal())
        self.assertTrue(result['approved'],result)
        book=self.risk.snapshot(self.now)
        self.assertGreater(book['reserved'],0)
        self.assertAlmostEqual(book['remaining'],39.41-book['reserved']-book['exposure'])
        self.assertAlmostEqual(book['used'],10.59+book['reserved']+book['exposure'])

    def test_gross_losses_do_not_halt_until_net_loss_reaches_limit(self):
        self.activate(daily_risk=50)
        self.broker._deals.extend([
            {"type":0,"entry":1,"time":self.now,"profit":-60,"magic":123},
            {"type":1,"entry":1,"time":self.now,"profit":49,"magic":123}])
        self.assertFalse(self.risk.snapshot(self.now)['loss_limit_reached'])
        self.broker._deals.append({"type":0,"entry":1,"time":self.now,"profit":-39,"magic":123})
        self.assertTrue(self.risk.snapshot(self.now)['loss_limit_reached'])
        self.assertFalse(self.executor.execute(self.proposal())['approved'])
        self.assertEqual([],self.broker.sent)

    def test_deposit_never_offsets_net_trading_loss(self):
        self.activate(daily_risk=50)
        self.broker._deals.extend([
            {"type":0,"entry":1,"time":self.now,"profit":-11,"magic":123},
            {"type":2,"time":self.now,"profit":5000,"magic":0}])
        book=self.risk.snapshot(self.now)
        self.assertEqual(book['account_realized_net'],-11)
        self.assertEqual(book['remaining'],39)

    def test_paid_commission_replaces_reserved_cost_once(self):
        self.broker.actual_commission = 6
        self.activate(commission_per_lot=6)
        result = self.executor.execute(self.proposal())
        self.assertTrue(result["approved"], result)
        book = self.risk.snapshot(self.now)
        entry_cost = result["request"]["volume"] * 3
        original = self.store.intent(result["intent_id"])["payload"]["original_risk"]
        self.assertAlmostEqual(entry_cost, book["realized_losses"])
        self.assertAlmostEqual(original - entry_cost, book["reserved"])
        self.assertAlmostEqual(original, book["used"])

    def test_separate_negative_broker_cost_types_consume_budget_and_target(self):
        self.activate()
        types=(4,7,8,9,10,11,12,17)
        self.broker._deals.extend({"ticket":10000+typ,"type":typ,"time":self.now,"profit":-5.,"magic":0} for typ in types)
        self.broker._deals.extend({"ticket":20000+typ,"type":typ,"time":self.now,"profit":-5000.,"magic":0} for typ in (2,3,6))
        self.broker._deals.append({"ticket":30000,"type":12,"time":self.now,"profit":5000.,"magic":0})
        book=self.risk.snapshot(self.now)
        self.assertEqual(book["realized_losses"],40.)
        self.assertEqual(book["remaining"],960.)
        self.assertEqual(book["unattributed_costs"],40.)
        self.assertEqual(book["net_target"],-40.)
        self.assertEqual(book["realized_net"],0.)
        self.assertEqual(book["cost_uncertainty"],[])

    def test_standalone_opening_commission_offsets_planned_cost_only_once(self):
        self.activate(commission_per_lot=6)
        result=self.executor.execute(self.proposal());self.assertTrue(result["approved"],result)
        intent=self.store.intent(result["intent_id"]);cost=result["request"]["volume"]*3
        fee={"ticket":90001,"type":7,"time":self.now,"profit":-cost,"magic":0,
             "order":intent["payload"]["result"]["order"],"position_id":intent["payload"]["position_ids"][0]}
        self.broker._deals.extend([fee,copy.deepcopy(fee)])  # Exact repeat is one deal.
        self.assertTrue(self.executor.reconcile()["ok"])
        book=self.risk.snapshot(self.now);original=intent["payload"]["original_risk"]
        self.assertAlmostEqual(book["realized_net"],-cost)
        self.assertAlmostEqual(book["commission_fee"],-cost)
        self.assertAlmostEqual(book["realized_losses"],cost)
        self.assertAlmostEqual(book["reserved"],original-cost)
        self.assertAlmostEqual(book["used"],original)
        self.assertEqual(book["unattributed_costs"],0.)
        self.assertEqual(book["cost_uncertainty"],[])
        self.executor.reconcile()
        self.assertAlmostEqual(self.risk.snapshot(self.now)["used"],original)

    def test_position_only_commission_is_owned_but_phase_uncertainty_blocks_entry(self):
        self.activate(commission_per_lot=6)
        result=self.executor.execute(self.proposal());intent=self.store.intent(result["intent_id"])
        self.broker._deals.append({"ticket":90002,"type":8,"time":self.now,"profit":-3.,"magic":0,
                                   "position_id":intent["payload"]["position_ids"][0]})
        self.executor.reconcile();book=self.risk.snapshot(self.now)
        self.assertEqual(book["realized_net"],-3.)
        self.assertEqual(book["unattributed_costs"],0.)
        self.assertAlmostEqual(book["reserved"],intent["payload"]["original_risk"])
        self.assertTrue(book["cost_uncertainty"])
        before=len(self.broker.sent)
        self.assertFalse(self.executor.execute(self.proposal("cost-phase"))["approved"])
        self.assertEqual(len(self.broker.sent),before)
        # Entry uncertainty does not remove explicit Demo risk reduction authority.
        self.assertTrue(self.executor.flatten_owned_positions()["ok"])

    def test_unlinked_cost_overlap_retains_reserve_and_requires_attribution(self):
        self.activate(commission_per_lot=6)
        result=self.executor.execute(self.proposal());intent=self.store.intent(result["intent_id"])
        self.broker._deals.append({"ticket":90003,"type":7,"time":self.now,"profit":-3.,"magic":0})
        self.executor.reconcile();book=self.risk.snapshot(self.now)
        self.assertEqual(book["unattributed_costs"],3.)
        self.assertTrue(book["cost_uncertainty"])
        self.assertAlmostEqual(book["reserved"],intent["payload"]["original_risk"])
        self.assertFalse(self.executor.execute(self.proposal("unlinked"))["approved"])
        # Actual opening order evidence resolves ambiguity, without retrying an order.
        self.broker._deals[-1]["order"]=intent["payload"]["result"]["order"]
        self.executor.reconcile();book=self.risk.snapshot(self.now)
        self.assertEqual(book["cost_uncertainty"],[])
        self.assertEqual(book["unattributed_costs"],0.)
        self.assertAlmostEqual(book["used"],intent["payload"]["original_risk"]+max(0.,3-intent["payload"]["planned_cost"]))

    def test_periodic_commission_link_does_not_prove_opening_fee_phase(self):
        self.activate(commission_per_lot=6)
        result=self.executor.execute(self.proposal());intent=self.store.intent(result["intent_id"])
        for typ in (8,9,10,11):
            self.broker._deals.append({"ticket":90100+typ,"type":typ,"time":self.now,"profit":-1.,"magic":0,
                                      "order":intent["payload"]["result"]["order"]})
        self.executor.reconcile();book=self.risk.snapshot(self.now)
        self.assertEqual(book["realized_net"],-4.)
        self.assertEqual(book["unattributed_costs"],0.)
        self.assertEqual(len(book["cost_uncertainty"]),4)
        self.assertAlmostEqual(book["reserved"],intent["payload"]["original_risk"])
        self.assertFalse(self.executor.execute(self.proposal("periodic"))["approved"])

    def test_unknown_negative_financial_type_fails_closed_without_ignoring_loss(self):
        self.activate()
        self.broker._deals.append({"ticket":90004,"type":5,"time":self.now,"profit":-9.,"magic":0})
        book=self.risk.snapshot(self.now)
        self.assertEqual(book["realized_losses"],9.)
        self.assertEqual(book["unattributed_costs"],9.)
        self.assertTrue(book["cost_uncertainty"])
        self.assertFalse(self.executor.execute(self.proposal())["approved"])
        self.assertEqual(self.broker.sent,[])

    def test_foreign_fee_does_not_offset_our_reservation_or_fake_ownership(self):
        self.activate(commission_per_lot=6)
        result=self.executor.execute(self.proposal());intent=self.store.intent(result["intent_id"])
        self.broker._deals.append({"ticket":90005,"type":7,"time":self.now,"profit":-3.,"magic":123})
        self.executor.reconcile();book=self.risk.snapshot(self.now)
        self.assertEqual(book["realized_net"],0.)
        self.assertEqual(book["unattributed_costs"],3.)
        self.assertEqual(book["cost_uncertainty"],[])
        self.assertAlmostEqual(book["reserved"],intent["payload"]["original_risk"])

    def test_confirmed_partial_exit_separate_fee_is_not_an_opening_offset(self):
        self.activate(commission_per_lot=6)
        result=self.executor.execute(self.proposal());self.assertTrue(result["ok"]);self.broker.next_result="partial"
        close=self.executor.flatten_owned_positions();self.assertTrue(close["ok"],close)
        action=self.store.intent(close["results"][0]["intent_id"])
        self.executor.reconcile();before=self.risk.snapshot(self.now)
        self.broker._deals.append({"ticket":90006,"type":7,"time":self.now,"profit":-3.,"magic":0,
                                   "order":action["payload"]["result"]["order"],"position_id":action["payload"]["position_id"]})
        self.executor.reconcile();book=self.risk.snapshot(self.now)
        self.assertEqual(book["cost_uncertainty"],[])
        self.assertEqual(book["unattributed_costs"],0.)
        self.assertAlmostEqual(book["reserved"],before["reserved"])
        self.assertAlmostEqual(book["realized_net"],before["realized_net"]-3)
        self.assertAlmostEqual(book["used"],before["used"]+3)

    def test_conflicting_duplicate_cashflow_ticket_cannot_be_silently_counted(self):
        self.activate()
        self.broker._deals.extend([{"ticket":90007,"type":7,"time":self.now,"profit":-3.,"magic":0},
                                  {"ticket":90007,"type":7,"time":self.now,"profit":-5.,"magic":0}])
        self.assertFalse(self.executor.execute(self.proposal())["approved"])
        self.assertEqual(self.broker.sent,[])

    def test_full_risk_allocation_is_budget_exhaustion_not_loss_breach(self):
        self.activate(max_trade_fraction=1, correlation_cap_fraction=1)
        result = self.executor.execute(self.proposal())
        self.assertTrue(result["approved"], result)
        book = self.risk.snapshot(self.now)
        self.assertFalse(book["loss_limit_reached"])
        self.assertEqual("STRATEGY_PLANS", self.executor.manage()["policy"])
        self.assertEqual(1, len(self.broker.sent))

    def test_same_signal_never_sends_twice_even_after_restart(self):
        result = self.entry()
        self.assertFalse(self.executor.execute(self.proposal())["approved"])
        replacement = Executor(self.broker, self.store, self.risk, lambda: self.now)
        replacement.activate("AUTO_DEMO", self.settings)
        self.assertFalse(replacement.execute(self.proposal())["approved"])
        self.assertEqual(1, len(self.broker.sent))
        self.assertEqual("FILLED", self.store.intent(result["intent_id"])["state"])

    def test_lost_response_retains_risk_until_positive_history_then_reactivate(self):
        self.activate()
        self.broker.next_result = "lost_response"
        result = self.executor.execute(self.proposal())
        self.assertEqual("UNKNOWN", result["state"])
        self.assertGreater(self.store.intent(result["intent_id"])["reserved"], 0)
        self.assertEqual("READ_ONLY", self.executor.mode)
        self.assertFalse(self.executor.execute(self.proposal())["approved"])
        matched = self.executor.reconcile()
        self.assertTrue(matched["ok"], matched)
        self.assertEqual("FILLED", self.store.intent(result["intent_id"])["state"])
        self.assertEqual("READ_ONLY", self.executor.mode)
        self.activate()
        self.assertFalse(self.executor.execute(self.proposal())["approved"])
        self.assertEqual(1, len(self.broker.sent))

    def test_none_and_timeout_after_fill_are_unknown_without_retry(self):
        for special in ("none_after_fill", "timeout_after_fill"):
            with self.subTest(special=special):
                self.activate()
                self.broker.special = special
                result = self.executor.execute(self.proposal(special))
                self.assertEqual("UNKNOWN", result["state"])
                self.assertTrue(self.executor.reconcile()["ok"])
                self.assertEqual("READ_ONLY", self.executor.mode)
        self.assertEqual(2, len(self.broker.sent))

    def test_unknown_absence_never_releases_or_permits_activation(self):
        self.activate()
        self.broker.special = "unknown_no_fill"
        result = self.executor.execute(self.proposal())
        before = self.store.intent(result["intent_id"])["reserved"]
        for _ in range(3):
            self.assertFalse(self.executor.reconcile()["ok"])
            with self.assertRaises(ValueError):
                self.activate()
        self.assertEqual(before, self.store.intent(result["intent_id"])["reserved"])
        self.assertEqual(1, len(self.broker.sent))

    def test_restart_sending_is_unknown_and_prepared_is_provably_unsent(self):
        self.activate()
        prepared = self.risk.prepare(self.proposal(), now=self.now)
        self.assertTrue(prepared["approved"])
        Executor(self.broker, self.store, self.risk, lambda: self.now)
        self.assertEqual("REJECTED", self.store.intent(prepared["intent_id"])["state"])
        next_intent = self.risk.prepare(self.proposal("inflight"), now=self.now)
        self.assertTrue(self.store.claim_send(next_intent["intent_id"]))
        restarted = Executor(self.broker, self.store, self.risk, lambda: self.now)
        self.assertEqual("UNKNOWN", self.store.intent(next_intent["intent_id"])["state"])
        with self.assertRaises(ValueError):
            restarted.activate("AUTO_DEMO", self.settings)
        self.assertEqual([], self.broker.sent)

    def test_explicit_rejection_releases_but_identity_stays_terminal(self):
        self.activate()
        self.broker.special = "reject"
        result = self.executor.execute(self.proposal())
        self.assertEqual("REJECTED", result["state"])
        self.assertEqual(0., self.store.intent(result["intent_id"])["reserved"])
        self.assertFalse(self.executor.execute(self.proposal())["approved"])
        with self.assertRaises(ValueError):
            self.store.set_intent_state(result["intent_id"], "PREPARED")
        self.assertEqual(1, len(self.broker.sent))

    def test_partial_release_waits_for_terminal_history(self):
        self.activate()
        self.broker.next_result = "partial"
        self.broker.history_missing = True
        result = self.executor.execute(self.proposal())
        intent = self.store.intent(result["intent_id"])
        self.assertEqual("PARTIAL", intent["state"])
        self.assertAlmostEqual(intent["payload"]["original_risk"], intent["reserved"])
        self.broker.history_missing = False
        self.assertTrue(self.executor.reconcile()["ok"])
        intent = self.store.intent(result["intent_id"])
        self.assertAlmostEqual(intent["payload"]["original_risk"] * self.broker.positions()[0]["volume"] / result["request"]["volume"], intent["reserved"])
        self.assertEqual(1, len(self.broker.sent))

    def test_confirmed_partial_close_then_only_remaining_volume_can_retry(self):
        entry = self.entry()
        self.broker.next_result = "partial"
        first = self.executor.flatten_owned_positions()
        self.assertTrue(first["ok"], first)
        self.assertTrue(first["results"][0]["confirmed"])
        remainder = self.broker.positions()[0]["volume"]
        self.assertAlmostEqual(entry["request"]["volume"] - first["results"][0]["result"]["volume"], remainder)
        second = self.executor.flatten_owned_positions()
        self.assertTrue(second["ok"], second)
        self.assertAlmostEqual(remainder, self.broker.sent[-1]["volume"])
        self.assertEqual([], self.broker.positions())
        self.assertEqual("CLOSED", self.store.intent(entry["intent_id"])["state"])
        self.assertEqual(0., self.store.intent(entry["intent_id"])["reserved"])

    def test_unknown_close_blocks_other_management_and_does_not_release_entry(self):
        entry = self.entry()
        self.broker.special = "unknown_no_fill"
        close = self.executor.flatten_owned_positions()
        self.assertFalse(close["ok"])
        self.assertFalse(self.executor.cancel_owned_orders()["ok"])
        self.assertFalse(self.executor.flatten_owned_positions()["ok"])
        self.assertGreater(self.store.intent(entry["intent_id"])["reserved"], 0)
        self.assertEqual(2, len(self.broker.sent))

    def test_stop_entries_preserves_separate_explicit_flatten_authority(self):
        self.entry()
        self.executor.stop_entries()
        self.assertFalse(self.executor.execute(self.proposal("new"))["approved"])
        self.assertEqual(1, len(self.broker.positions()))
        self.assertTrue(self.executor.flatten_owned_positions()["ok"])
        self.assertEqual([], self.broker.positions())

    def test_netting_entry_over_existing_external_position_and_mixed_management_rejected(self):
        entry = self.entry()
        self.broker._account["margin_mode"] = 0
        self.assertFalse(self.executor.execute(self.proposal("second"))["approved"])
        position = self.broker._positions[0]
        self.broker._deals.append({"ticket": 8888, "order": 8888, "position_id": position["identifier"], "time": self.now,
                                  "symbol": position["symbol"], "type": 0, "entry": 0, "volume": .1,
                                  "magic": 456, "comment": "external", "profit": 0, "commission": 0})
        position["volume"] += .1
        flattened = self.executor.flatten_owned_positions()
        self.assertFalse(flattened["ok"], flattened)
        self.assertIn("mixed", flattened["results"][0]["reason"])
        self.assertEqual(1, len(self.broker.sent))
        self.assertGreater(self.store.intent(entry["intent_id"])["reserved"], 0)

    def test_magic_alone_cannot_authorize_external_hedging_position(self):
        entry = self.entry()
        external = {**self.broker._positions[0], "ticket": 8888, "identifier": 8888, "comment": "not-NEXUS"}
        self.broker._positions.append(external)
        flattened = self.executor.flatten_owned_positions()
        self.assertTrue(flattened["ok"], flattened)
        self.assertEqual([8888], [p["ticket"] for p in self.broker.positions()])
        self.assertEqual("CLOSED", self.store.intent(entry["intent_id"])["state"])

    def test_daily_target_latches_stops_and_flattens_with_broker_confirmation(self):
        self.activate(daily_target=10)
        result = self.executor.execute(self.proposal())
        self.assertTrue(result["approved"], result)
        self.broker._prices["EURUSD.demo"] = 1.082
        management = self.executor.manage()
        self.assertEqual("DAILY_TARGET", management["policy"], management)
        self.assertTrue(management["target_confirmed"])
        self.assertEqual([], self.broker.positions())
        self.assertTrue(self.executor.entries_paused)
        self.activate(daily_target=9999)
        self.assertTrue(self.executor.entries_paused)
        self.assertFalse(self.executor.execute(self.proposal("after-target"))["approved"])

    def test_daily_loss_policy_flattens_only_owned_and_is_persistent(self):
        self.entry()
        self.broker._deals.append({"ticket": 9999, "type": 0, "entry": 1, "time": self.now,
                                  "profit": -1100, "commission": 0., "magic": 111, "comment": "external"})
        management = self.executor.manage()
        self.assertEqual("DAILY_LOSS", management["policy"], management)
        self.assertTrue(self.executor.entries_paused)
        self.assertEqual([], self.broker.positions())
        self.assertEqual("DAILY_LOSS", self.store.day_halt(self.risk.key, self.now)["reason"])

    def test_plan_time_exit_protection_and_partial_are_broker_observed(self):
        self.entry(management={"protect_at_r": .2, "partial_at_r": .5, "partial_fraction": .5})
        self.broker._prices["EURUSD.demo"] = 1.082
        protected = self.executor.manage()
        self.assertTrue(protected["ok"], protected)
        self.assertEqual("SLTP", self.broker.sent[-1]["action"])
        self.assertAlmostEqual(self.broker.positions()[0]["price_open"], self.broker.positions()[0]["sl"])
        self.broker._prices["EURUSD.demo"] = 1.083
        partial = self.executor.manage()
        self.assertTrue(partial["ok"], partial)
        self.assertEqual("DEAL", self.broker.sent[-1]["action"])
        self.assertGreater(len(self.broker.positions()), 0)
        self.executor.flatten_owned_positions()
        entry = self.executor.execute(self.proposal("timed", management={"max_hold_seconds": 30}, sl=1.078, tp=1.092))
        self.assertTrue(entry["approved"], entry)
        self.now += 31
        timed = self.executor.manage()
        self.assertTrue(timed["ok"], timed)
        self.assertEqual([], self.broker.positions())

    def test_mutating_activated_settings_revokes_authorization(self):
        self.activate()
        self.risk.settings["risk_amount"] = 99999
        self.assertFalse(self.executor.execute(self.proposal())["approved"])
        self.assertEqual("READ_ONLY", self.executor.mode)
        self.assertEqual([], self.broker.sent)

    def test_execution_plan_invalidation_uses_observed_closed_bar_then_next_quote(self):
        seconds = 3600
        opening = int(self.now // seconds) * seconds
        self.now = opening + 120
        plan = {"max_hold_bars": 12, "timeframe": "H1", "allow_addition": False,
                "invalidation": {"price": 1.079, "evaluation": "completed_bar_close"}}
        self.entry(execution_plan=plan)
        rows = [{"time": opening - seconds, "close": 1.078},
                {"time": opening, "close": 1.082},
                {"time": opening + seconds, "close": 1.078}]
        self.broker.bars = lambda symbol, timeframe, count: [r for r in rows if r["time"] + seconds <= self.now]
        self.broker._prices["EURUSD.demo"] = 1.078
        before_close = self.executor.manage()
        self.assertTrue(before_close["ok"], before_close)
        self.assertEqual(1, len(self.broker.sent))  # Intrabar tick is not confirmation.
        self.now = opening + seconds + 1
        self.assertTrue(self.executor.manage()["ok"])
        self.assertEqual(1, len(self.broker.sent))  # Completed entry bar closes above invalidation.
        self.now = opening + 2 * seconds + 1
        invalidated = self.executor.manage()
        self.assertTrue(invalidated["ok"], invalidated)
        self.assertEqual([], self.broker.positions())
        self.assertEqual(2, len(self.broker.sent))
        close_intent = self.store.intent(invalidated["results"][0]["intent_id"])
        self.assertEqual("PLAN_COMPLETED_BAR_INVALIDATION", close_intent["payload"]["reason"])

    def test_fast_no_time_limit_preserves_invalidation_after_many_bars(self):
        opening=int(self.now//60)*60-600
        position={'symbol':'EURUSD.demo','time':opening,'type':0}
        intent={'payload':{'proposal':{'timeframe':'M1'}}}
        plan={'max_hold_bars':None,'timeframe':'M1','invalidation':None}
        with patch.object(self.broker,'bars',side_effect=AssertionError('No fixed timer history needed')):
            self.assertIsNone(self.executor._completed_bar_exit(position,intent,plan))
        plan['invalidation']={'price':1.079,'evaluation':'completed_bar_close'}
        with patch.object(self.broker,'bars',return_value=[{'time':opening+300,'close':1.078}]):
            self.assertEqual(self.executor._completed_bar_exit(position,intent,plan),'PLAN_COMPLETED_BAR_INVALIDATION')

    def test_execution_plan_counts_actual_completed_bars_not_elapsed_hours(self):
        seconds = 3600
        opening = int(self.now // seconds) * seconds
        self.now = opening + 120
        self.entry(execution_plan={"max_hold_bars": 2, "timeframe": "H1", "invalidation": None})
        rows = [{"time": opening, "close": 1.082}, {"time": opening + 3 * seconds, "close": 1.082}]
        self.broker.bars = lambda symbol, timeframe, count: [r for r in rows if r["time"] + seconds <= self.now] or [{"time": opening - seconds, "close": 1.082}]
        self.now = opening + 3 * seconds + 1
        self.assertTrue(self.executor.manage()["ok"])
        self.assertEqual(1, len(self.broker.sent))  # Two missing bars are not invented.
        self.now = opening + 4 * seconds + 1
        timed = self.executor.manage()
        self.assertTrue(timed["ok"], timed)
        self.assertEqual([], self.broker.positions())
        self.assertEqual("PLAN_COMPLETED_BAR_TIME_EXIT", self.store.intent(timed["results"][0]["intent_id"])["payload"]["reason"])

    def test_execution_plan_supports_all_short_decision_timeframes(self):
        for timeframe, seconds in (("M1", 60), ("M5", 300)):
            with self.subTest(timeframe=timeframe):
                opening = int(self.now // seconds) * seconds - seconds
                position = {"symbol": "EURUSD.demo", "time": opening, "type": 0}
                intent = {"payload": {"proposal": {"timeframe": timeframe}}}
                rows = [{"time": opening, "close": 1.08}]
                with patch.object(self.broker, "bars", return_value=rows):
                    reason = self.executor._completed_bar_exit(
                        position, intent,
                        {"max_hold_bars": 1, "timeframe": timeframe, "invalidation": None})
                self.assertEqual("PLAN_COMPLETED_BAR_TIME_EXIT", reason)

    def test_execution_plan_refuses_future_and_duplicate_bars(self):
        self.entry(execution_plan={"max_hold_bars": 2, "timeframe": "H1", "invalidation": None})
        self.broker.bars = lambda *args: [{"time": self.now - 100, "close": 1.08}]
        self.assertFalse(self.executor.manage()["ok"])
        self.broker.bars = lambda *args: [{"time": self.now - 4000, "close": 1.08}] * 2
        self.assertFalse(self.executor.manage()["ok"])
        self.assertEqual(1, len(self.broker.sent))

    def test_confirmed_cancel_releases_entry_without_assuming_absence_is_proof(self):
        self.activate()
        prepared = self.risk.prepare(self.proposal(), now=self.now)
        request = prepared["request"]
        self.assertTrue(self.store.claim_send(prepared["intent_id"]))
        self.store.set_intent_state(prepared["intent_id"], "ACCEPTED", result={"retcode": 10008, "order": 4567})
        self.broker._orders.append({"ticket": 4567, "symbol": request["symbol"], "magic": request["magic"],
                                    "comment": request["comment"], "volume_current": request["volume"], "type": 2})
        self.assertTrue(self.executor.reconcile()["ok"])
        cancelled = self.executor.cancel_owned_orders()
        self.assertTrue(cancelled["ok"], cancelled)
        self.assertTrue(cancelled["results"][0]["confirmed"])
        self.assertTrue(self.executor.reconcile()["ok"])
        self.assertEqual("CANCELLED", self.store.intent(prepared["intent_id"])["state"])
        self.assertEqual(0., self.store.intent(prepared["intent_id"])["reserved"])

    def test_lost_close_fill_reconciles_before_any_retry(self):
        entry = self.entry()
        self.broker.next_result = "lost_response"
        closed = self.executor.flatten_owned_positions()
        self.assertFalse(closed["ok"])
        self.assertEqual("READ_ONLY", self.executor.mode)
        self.assertEqual([], self.broker.positions())
        self.assertTrue(self.executor.reconcile()["ok"])
        self.assertEqual("CLOSED", self.store.intent(entry["intent_id"])["state"])
        self.activate()
        self.assertTrue(self.executor.flatten_owned_positions()["ok"])
        self.assertEqual(2, len(self.broker.sent))

    def test_high_impact_event_and_missing_currency_coverage_defense(self):
        self.activate()
        base = self.broker.calendar()
        self.broker.calendar = lambda: {**base, "events": [{"currency": "USD", "importance": 3, "time_utc": self.now + 60, "time_mode": 0}]}
        self.assertFalse(self.executor.execute(self.proposal())["approved"])
        self.broker.calendar = lambda: {**base, "currencies": ["USD"]}
        self.assertFalse(self.executor.execute(self.proposal())["approved"])
        self.assertEqual([], self.broker.sent)

    def test_preflight_price_move_cannot_spend_more_than_reservation(self):
        self.activate()
        self.broker.check_hook = lambda request: self.broker._prices.update({"EURUSD.demo": 1.081})
        result = self.executor.execute(self.proposal())
        self.assertFalse(result["approved"])
        self.assertIn("reserved", result["reason"])
        self.assertEqual([], self.broker.sent)
        self.assertEqual(0., self.store.snapshot(self.risk.key, self.now)["reserved"])

    def test_account_changed_after_final_check_still_cannot_send(self):
        self.activate()
        original = self.broker.check
        calls = []
        def checking(request):
            calls.append(request)
            if len(calls) == 2:
                self.broker._account["trade_mode"] = 2
            return original(request)
        self.broker.check = checking
        self.assertFalse(self.executor.execute(self.proposal())["approved"])
        self.assertEqual(2, len(calls))
        self.assertEqual([], self.broker.sent)
        self.assertEqual("READ_ONLY", self.executor.mode)

    def test_generic_error_and_malformed_code_preserve_reservation(self):
        for special in ("processing_error_after_fill", "malformed_success_after_fill"):
            with self.subTest(special=special):
                self.activate()
                self.broker.special = special
                result = self.executor.execute(self.proposal(special))
                self.assertEqual("UNKNOWN", result["state"])
                self.assertGreater(self.store.intent(result["intent_id"])["reserved"], 0)
                self.assertTrue(self.executor.reconcile()["ok"])
        self.assertEqual(2, len(self.broker.sent))

    def test_undefined_trade_return_codes_never_release_risk(self):
        for code in (10037, 10047):
            with self.subTest(code=code):
                self.activate()
                self.broker.special = code
                result = self.executor.execute(self.proposal(str(code)))
                self.assertEqual("UNKNOWN", result["state"])
                self.assertGreater(self.store.intent(result["intent_id"])["reserved"], 0)
                self.assertEqual("READ_ONLY", self.executor.mode)
                self.assertTrue(self.executor.reconcile()["ok"])
                self.assertEqual("FILLED", self.store.intent(result["intent_id"])["state"])
        self.assertEqual(2, len(self.broker.sent))

    def test_changed_locked_and_existing_close_results_require_matching(self):
        for code in (10023, 10028, 10039):
            with self.subTest(code=code):
                self.activate()
                self.broker.special = code
                result = self.executor.execute(self.proposal(str(code)))
                self.assertEqual("UNKNOWN", result["state"])
                self.assertGreater(self.store.intent(result["intent_id"])["reserved"], 0)
                self.assertFalse(self.executor.execute(self.proposal(str(code)))["approved"])
                self.assertTrue(self.executor.reconcile()["ok"])
                self.activate()
                self.assertTrue(self.executor.flatten_owned_positions()["ok"])
        self.assertEqual(6, len(self.broker.sent))

    def test_official_hedge_prohibited_is_explicit_rejection(self):
        self.activate()
        with patch.object(self.broker, "send", return_value={"retcode": 10046}):
            result = self.executor.execute(self.proposal())
        self.assertEqual("REJECTED", result["state"])
        self.assertEqual(0., self.store.intent(result["intent_id"])["reserved"])
        self.assertEqual([], self.broker.positions())


class AtomicLedgerTests(unittest.TestCase):
    def test_independent_connections_cannot_double_spend_shared_budget_or_factor(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "ledger.sqlite3"
            a, b = Store(path), Store(path)
            barrier = threading.Barrier(2)
            results = []
            def reserve(store, identity):
                barrier.wait()
                results.append(store.reserve(identity, "account", 60., {}, ["USD"], 100., {"USD": 100.}))
            one = threading.Thread(target=reserve, args=(a, "one"))
            two = threading.Thread(target=reserve, args=(b, "two"))
            one.start(); two.start(); one.join(); two.join()
            self.assertEqual(1, sum(r["approved"] for r in results))
            self.assertEqual(60., a.snapshot("account")["reserved"])
            self.assertFalse(a.reserve("three", "account", 10., {}, ["USD"], 100., {"USD": 65.})["approved"])
            a.close(); b.close()

    def test_atomic_send_claim_blocks_other_sender_and_duplicate_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "ledger.sqlite3"
            a, b = Store(path), Store(path)
            self.assertTrue(a.reserve("one", "account", 20, {}, [], 100)["approved"])
            self.assertTrue(b.reserve("two", "account", 20, {}, [], 100)["approved"])
            self.assertTrue(a.claim_send("one"))
            self.assertFalse(b.claim_send("one"))
            self.assertFalse(b.claim_send("two"))
            self.assertFalse(b.reserve("three", "account", 20, {}, [], 100)["approved"])
            a.set_intent_state("one", "UNKNOWN")
            self.assertFalse(b.claim_send("two"))
            a.set_intent_state("one", "REJECTED")
            self.assertTrue(b.claim_send("two"))
            a.close(); b.close()


if __name__ == "__main__":
    unittest.main()
