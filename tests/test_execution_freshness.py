"""Post-read clock checks against an isolated synthetic broker; no MT5 I/O."""
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nexus.broker import SimBroker
from nexus.confluence import PROTOCOL_REVISION
from nexus.execution import Executor
from nexus.risk import RiskManager, protocol_certificate_hash
from nexus.store import Store


class AdvancingBroker(SimBroker):
    def __init__(self, clock):
        super().__init__(clock)
        self.hooks = {}
        self.tick_offset = 0.
        self._prices["STOCK.A"] = 100.

    def before(self, method):
        callback = self.hooks.pop(method, None)
        if callback:
            callback()

    def tick(self, symbol):
        self.before("tick")
        return {**super().tick(symbol), "time": math.floor(self.clock()) + self.tick_offset}

    def session(self, symbol):
        self.before("session")
        return {**super().session(symbol), "as_of": math.floor(self.clock())}

    def calendar(self):
        self.before("calendar")
        return {**super().calendar(), "as_of": math.floor(self.clock())}

    def calc_profit(self, *args):
        self.before("calc_profit")
        return super().calc_profit(*args)

    def calc_margin(self, *args):
        self.before("calc_margin")
        return super().calc_margin(*args)

    def check(self, request):
        self.before("check")
        return super().check(request)


class ExecutionFreshnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.now = 1000.9
        self.clock = lambda: self.now
        self.broker = AdvancingBroker(self.clock)
        self.store = Store(Path(self.temp.name) / "synthetic.sqlite3")
        self.addCleanup(self.store.close)
        self.risk = RiskManager(self.broker, self.store)
        self.executor = Executor(self.broker, self.store, self.risk, self.clock)
        self.settings = {"daily_risk": 1000., "daily_target": 1000.,
                         "commission_per_lot": 0., "slippage_points": 0.}

    def advance(self, seconds):
        self.now += seconds

    def activate(self, strict=False):
        settings = dict(self.settings)
        if strict:
            settings["decision_protocol"] = "four_school_v1"
        self.executor.activate("AUTO_DEMO", settings)

    def proposal(self, strict=False, **changes):
        proposal = {"id": "clock-fixture", "symbol": "STOCK.A", "side": "BUY",
                    "sl": 99., "tp": 103., "qualified": True, "news_ok": True,
                    "data_time": self.now - 1., "expires_at": self.now + 120., **changes}
        if strict:
            proposal.update(protocol_revision=PROTOCOL_REVISION,
                            decision_matrix={"passed": True, "fixture": "synthetic clock test"})
            proposal["decision_matrix"]["certificate_hash"] = protocol_certificate_hash(proposal)
        return proposal

    def prepared(self, proposal=None):
        result = self.risk.prepare(proposal or self.proposal(), clock=self.clock)
        self.assertTrue(result["approved"], result)
        return result

    def assert_unsent(self, result, reason):
        self.assertFalse(result["approved"], result)
        self.assertIn(reason, result["reason"])
        self.assertEqual([], self.broker.sent)
        self.assertEqual(0., self.store.snapshot(self.risk.key, self.now)["reserved"])

    def test_fresh_price_accepts_quote_acquired_across_second_boundary(self):
        self.activate()
        self.broker.hooks["tick"] = lambda: self.advance(.2)
        bid, ask = self.executor._fresh_price({"symbol": "STOCK.A"})
        self.assertEqual((100., 100.01), (bid, ask))
        self.assertAlmostEqual(1001.1, self.now)

    def test_fresh_price_still_refuses_true_future_and_stale_quotes(self):
        self.activate()
        for offset in (2., -16.):
            with self.subTest(offset=offset):
                self.now = 1000.9
                self.broker.tick_offset = offset
                self.broker.hooks["tick"] = lambda: self.advance(.2)
                with self.assertRaisesRegex(ValueError, "Fresh broker price"):
                    self.executor._fresh_price({"symbol": "STOCK.A"})
        self.assertEqual([], self.broker.sent)

    def test_sender_passes_advancing_clock_into_independent_risk_preparation(self):
        self.activate()
        self.broker.hooks["tick"] = lambda: self.advance(.2)
        result = self.executor.execute(self.proposal())
        self.assertTrue(result["approved"], result)
        self.assertTrue(result["confirmed"], result)
        self.assertEqual(1, len(self.broker.sent))

    def test_risk_uses_clock_after_session_and_calendar_reads(self):
        self.activate()
        self.broker.hooks["session"] = lambda: self.advance(.2)
        self.broker.hooks["calendar"] = lambda: self.advance(.2)
        self.prepared()
        self.assertAlmostEqual(1001.3, self.now)
        self.assertEqual([], self.broker.sent)

    def test_risk_still_refuses_true_future_and_stale_quotes(self):
        self.activate()
        for offset in (2., -16.):
            with self.subTest(offset=offset):
                self.now = 1000.9
                self.broker.tick_offset = offset
                self.broker.hooks["tick"] = lambda: self.advance(.2)
                result = self.risk.prepare(self.proposal(), clock=self.clock)
                self.assert_unsent(result, "Tick is stale or from the future")

    def test_risk_refuses_proposal_expired_during_calendar_read(self):
        self.activate()
        proposal = self.proposal(expires_at=self.now + 1.)
        self.broker.hooks["calendar"] = lambda: self.advance(1.1)
        self.assert_unsent(self.risk.prepare(proposal, clock=self.clock), "Proposal is stale")
        self.assertEqual([], self.store.intents())

    def test_risk_refuses_expiry_during_sizing_and_preflight_without_reservation(self):
        self.activate()
        for method in ("calc_profit", "calc_margin", "check"):
            with self.subTest(method=method):
                proposal = self.proposal(expires_at=self.now + 1.)
                self.broker.hooks[method] = lambda: self.advance(1.1)
                self.assert_unsent(self.risk.prepare(proposal, clock=self.clock), "Proposal is stale")
                self.assertEqual([], self.store.intents())

    def test_risk_refuses_quote_that_ages_out_during_sizing(self):
        self.activate()
        self.broker.hooks["calc_profit"] = lambda: self.advance(16.)
        self.assert_unsent(self.risk.prepare(self.proposal(), clock=self.clock), "Tick is stale")
        self.assertEqual([], self.store.intents())

    def test_risk_refuses_day_rollover_during_preflight(self):
        self.now = 86399.9
        self.activate()
        self.broker.hooks["check"] = lambda: self.advance(.2)
        result = self.risk.prepare(self.proposal(), clock=self.clock)
        self.assertFalse(result["approved"], result)
        self.assertIn("UTC day changed", result["reason"])
        self.assertEqual([], self.store.intents())
        self.assertEqual([], self.broker.sent)

    def test_risk_refuses_real_account_switch_during_preflight(self):
        self.activate()
        self.broker.hooks["check"] = lambda: self.broker._account.update(trade_mode=1)
        self.assert_unsent(self.risk.prepare(self.proposal(), clock=self.clock), "authorized Demo")
        self.assertEqual([], self.store.intents())

    def test_sender_accepts_bridge_reads_across_second_boundary(self):
        self.activate()
        prepared = self.prepared()
        self.broker.hooks["session"] = lambda: self.advance(.2)
        self.broker.hooks["calendar"] = lambda: self.advance(.2)
        self.broker.hooks["tick"] = lambda: self.advance(.2)
        result = self.executor._send(prepared["intent_id"], entry=True)
        self.assertTrue(result["approved"], result)
        self.assertEqual(1, len(self.broker.sent))

    def test_sender_refuses_proposal_expired_during_bridge_read(self):
        self.activate()
        prepared = self.prepared(self.proposal(expires_at=self.now + 1.))
        self.broker.hooks["calendar"] = lambda: self.advance(1.1)
        self.assert_unsent(self.executor._send(prepared["intent_id"], entry=True), "Proposal expired")
        self.assertEqual("REJECTED", self.store.intent(prepared["intent_id"])["state"])

    def test_sender_refuses_expiry_during_margin_and_broker_preflight(self):
        self.activate()
        for method in ("calc_profit", "calc_margin", "check"):
            with self.subTest(method=method):
                prepared = self.prepared(self.proposal(id="sender-" + method, expires_at=self.now + 1.))
                self.broker.hooks[method] = lambda: self.advance(1.1)
                self.assert_unsent(self.executor._send(prepared["intent_id"], entry=True), "Proposal expired")
                self.assertEqual("REJECTED", self.store.intent(prepared["intent_id"])["state"])

    def test_sender_refuses_quote_that_ages_out_during_risk_math(self):
        self.activate()
        prepared = self.prepared()
        self.broker.hooks["calc_profit"] = lambda: self.advance(16.)
        self.assert_unsent(self.executor._send(prepared["intent_id"], entry=True), "Fresh broker price")

    def test_sender_refuses_true_future_and_stale_quotes_after_bridge_reads(self):
        self.activate()
        for offset in (2., -16.):
            with self.subTest(offset=offset):
                self.broker.tick_offset = 0.
                prepared = self.prepared(self.proposal(id="quote-" + str(offset)))
                self.broker.tick_offset = offset
                self.broker.hooks["tick"] = lambda: self.advance(.2)
                self.assert_unsent(self.executor._send(prepared["intent_id"], entry=True), "Fresh broker price")

    def test_sender_refuses_quote_that_ages_out_during_preflight(self):
        self.activate()
        prepared = self.prepared()
        self.broker.hooks["check"] = lambda: self.advance(16.)
        self.assert_unsent(self.executor._send(prepared["intent_id"], entry=True), "Fresh broker price")

    def test_strict_sender_refuses_expiry_during_last_reward_risk_calculation(self):
        self.activate(strict=True)
        prepared = self.prepared(self.proposal(strict=True, expires_at=self.now + 1.))
        original = self.risk.minimum_rr_check
        calls = []
        def slow_last_rr(*args):
            calls.append(1)
            result = original(*args)
            if len(calls) == 3:
                self.advance(1.1)
            return result
        with patch.object(self.risk, "minimum_rr_check", side_effect=slow_last_rr):
            self.assert_unsent(self.executor._send(prepared["intent_id"], entry=True), "Proposal expired")
        self.assertEqual(3, len(calls))

    def test_strict_sender_refuses_quote_aged_during_last_reward_risk_calculation(self):
        self.activate(strict=True)
        prepared = self.prepared(self.proposal(strict=True))
        original = self.risk.minimum_rr_check
        calls = []
        def slow_last_rr(*args):
            calls.append(1)
            result = original(*args)
            if len(calls) == 3:
                self.advance(16.)
            return result
        with patch.object(self.risk, "minimum_rr_check", side_effect=slow_last_rr):
            self.assert_unsent(self.executor._send(prepared["intent_id"], entry=True), "Fresh broker price")
        self.assertEqual(3, len(calls))

    def test_sender_keeps_day_authorization_guard_after_slow_preflight(self):
        self.now = 86399.9
        self.activate()
        prepared = self.prepared()
        self.broker.hooks["check"] = lambda: self.advance(.2)
        result = self.executor._send(prepared["intent_id"], entry=True)
        self.assertFalse(result["approved"], result)
        self.assertIn("UTC day changed", result["reason"])
        self.assertEqual("READ_ONLY", self.executor.mode)
        self.assertEqual([], self.broker.sent)
        self.assertEqual("REJECTED", self.store.intent(prepared["intent_id"])["state"])


if __name__ == "__main__":
    unittest.main()
