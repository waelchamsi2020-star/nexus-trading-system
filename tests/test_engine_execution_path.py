"""End-to-end coordinator tests against a broker-verified Demo fixture.

No real terminal or broker call is made. The fixture deliberately presents the
same Demo/account contract as MT5 while retaining SimBroker's in-memory fills.
"""
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from nexus.engine import PLAN_VERSION, Engine
from nexus.strategies import REGISTRY

ROOT = Path(__file__).resolve().parents[1]


class EngineExecutionPathTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.now = int(time.time() // 86400) * 86400 + 12 * 3600
        self.require_official_feeds = False
        self.engine = Engine(ROOT, Path(self.temp.name), clock=lambda: self.now)
        self.engine._connect(True)
        # This stays an in-memory fixture. Marking its evidence as broker-kind
        # exercises the exact path used by an attached MT5 Demo terminal.
        self.engine.broker.is_simulation = False
        self.addCleanup(self.close)
        self.engine.scanner.step(999)
        self.engine._action({"action": "start", "risk_value": 1000, "target_value": 1000,
                             "unit": "amount", "mode": "AUTO_DEMO",
                             "commission_per_lot": 0, "slippage_points": 10})

    def close(self):
        self.engine.stop_worker()
        if self.engine.store:
            self.engine.store.close()
        self.engine.cache.db.close()
        self.engine.news.db.close()

    def cards(self, symbol, timeframe, bars, as_of, context):
        common = {"symbol": symbol, "quality": "VALIDATED_OHLC", "coverage": "IMPLEMENTED",
                  "data_time": self.now - 1, "expires_at": self.now + 120,
                  "news_requirements": (["calendar", "official_feeds"] if self.require_official_feeds else ["calendar"]),
                  "conditions_missing": [],
                  "invalidation": {"price": 1.074, "evaluation": "completed_bar_close"},
                  "targets": [{"price": 1.09, "method": "fixture", "fraction": 1.0}],
                  "execution_plan": {"take_profit": "FULL", "partial_targets": [],
                                     "max_hold_bars": 12, "timeframe": timeframe,
                                     "allow_addition": False, "stop_may_only_tighten": True}}
        if timeframe == "M5":
            return [{**common, "id": "qualified-demo-signal", "strategy_id": "engulfing",
                     "version": REGISTRY["engulfing"]["version"], "timeframe": timeframe,
                     "direction": "BUY", "status": "READY", "actionable": True,
                     "conditions_met": ["completed bullish fixture"], "score": 90,
                     "evidence_group": "candles", "evidence": [{"kind": "fixture"}],
                     "entry": {"price": 1.08, "zone": [1.079, 1.081], "triggered": True},
                     "stop": {"price": 1.075, "method": "fixture"}}]
        if timeframe == "M15":
            return [{**common, "id": "independent-support", "strategy_id": "ema_cross",
                     "version": REGISTRY["ema_cross"]["version"], "timeframe": timeframe,
                     "direction": "BUY", "status": "WAIT", "actionable": False,
                     "conditions_met": ["completed trend fixture"], "score": 80,
                     "evidence_group": "trend", "evidence": [{"kind": "fixture"}],
                     "entry": None, "stop": None}]
        return []

    def certificate(self):
        symbol, timeframe, strategy = "EURUSD.demo", "M5", "engulfing"
        config = self.engine._quant_config(symbol)
        return {"strategy_id": strategy, "version": REGISTRY[strategy]["version"],
                "plan_version": PLAN_VERSION, "data_kind": "broker",
                "symbol": symbol, "timeframe": timeframe, "qualified": True,
                "status": "QUALIFIED_DEMO_RESEARCH", "data_time": self.now - 1,
                "checked_at": self.now - 5, "certificate_expires_at": self.now + 3600,
                "cost_config_hash": self.engine._cost_hash(config),
                "metrics": {"expectancy_r": 0.25, "profit_factor": 1.4}}

    def analyze_with_qualified_signal(self):
        self.engine.quant_results["EURUSD.demo:M5:engulfing"] = self.certificate()
        with patch("nexus.engine.analyze_all", side_effect=self.cards):
            self.engine._analyze_symbol("EURUSD.demo")

    def test_scan_committee_risk_and_executor_reach_one_demo_order(self):
        self.assertTrue(self.engine.scanner.rows["EURUSD.demo"]["eligible"])
        # There is no matching RSS loaded. A calendar-only strategy must still
        # reach the committee because RSS is optional contextual evidence.
        gate = self.engine.news.gate(self.engine.broker.symbol("EURUSD.demo"),
                                     self.engine.broker.calendar())
        self.assertTrue(gate["ok"])
        self.assertFalse(gate["coverage"]["official_feeds"])
        self.analyze_with_qualified_signal()
        self.assertEqual("BUY", self.engine.decisions["EURUSD.demo"]["decision"])
        self.engine._trade_candidates()
        self.assertEqual(1, len(self.engine.broker.sent))
        self.assertEqual("DEAL", self.engine.broker.sent[0]["action"])
        self.assertEqual("EURUSD.demo", self.engine.broker.sent[0]["symbol"])
        self.assertEqual(1, len(self.engine.broker.positions()))

    def test_explicit_forward_demo_executes_strategy_without_faking_certificate(self):
        self.engine._action({"action":"start","risk_value":1000,"target_value":1000,"unit":"amount","mode":"AUTO_DEMO", "commission_per_lot":0,"slippage_points":10,"validation_policy":"forward_demo"})
        with patch("nexus.engine.analyze_all",side_effect=self.cards):
            self.engine._analyze_symbol("EURUSD.demo")
        proposal=self.engine.decisions["EURUSD.demo"]["proposals"][0]
        self.assertFalse(proposal["qualified"])
        self.assertEqual(proposal["validation_policy"],"forward_demo")
        self.assertEqual(self.engine.quant_results,{})
        self.engine._trade_candidates()
        self.assertEqual(len(self.engine.broker.sent),1)
        self.assertGreater(self.engine.broker.sent[0]["sl"],0)

    def test_forward_label_cannot_bypass_historical_authorization(self):
        self.analyze_with_qualified_signal()
        proposal=self.engine.decisions["EURUSD.demo"]["proposals"][0]
        proposal.update(qualified=False,validation_policy="forward_demo",signal_validated=True)
        result=self.engine.executor.execute(proposal)
        self.assertFalse(result["approved"])
        self.assertEqual(self.engine.broker.sent,[])

    def test_forward_demo_still_requires_news_and_strategy_signal(self):
        self.engine._action({"action":"start","risk_value":1000,"target_value":1000,"unit":"amount","mode":"AUTO_DEMO", "commission_per_lot":0,"slippage_points":10,"validation_policy":"forward_demo"})
        self.require_official_feeds=True
        with patch("nexus.engine.analyze_all",side_effect=self.cards):self.engine._analyze_symbol("EURUSD.demo")
        self.engine._trade_candidates()
        self.assertEqual(self.engine.broker.sent,[])

    def test_high_impact_calendar_blackout_still_blocks_the_same_signal(self):
        original = self.engine.broker.calendar

        def blackout_calendar():
            calendar = original()
            calendar["events"] = [{"currency": "USD", "importance": 3,
                                   "time_utc": self.now, "time_mode": 0}]
            return calendar

        self.engine.broker.calendar = blackout_calendar
        self.analyze_with_qualified_signal()
        self.assertEqual("REJECT", self.engine.decisions["EURUSD.demo"]["decision"])
        self.assertTrue(self.engine.decisions["EURUSD.demo"]["news_gate"]["blackout"])
        self.engine._trade_candidates()
        self.assertEqual([], self.engine.broker.sent)

    def test_auto_quant_is_not_queued_for_news_blocked_signal(self):
        self.require_official_feeds=True
        with patch("nexus.engine.analyze_all",side_effect=self.cards), patch.object(self.engine,"_request_quant") as request:
            self.engine._analyze_symbol("EURUSD.demo")
        request.assert_not_called()

    def test_auto_quant_is_queued_when_it_is_the_only_missing_gate(self):
        with patch("nexus.engine.analyze_all",side_effect=self.cards), patch.object(self.engine,"_request_quant") as request:
            self.engine._analyze_symbol("EURUSD.demo")
        self.assertEqual(request.call_count,1)
        self.assertEqual(request.call_args.args[:3],("EURUSD.demo","M5","engulfing"))

    def test_cached_qualification_reaches_executor_in_same_analysis_cycle(self):
        def cached(*args):
            self.engine.quant_results["EURUSD.demo:M5:engulfing"]=self.certificate()
        with patch("nexus.engine.analyze_all",side_effect=self.cards), patch.object(self.engine,"_request_quant",side_effect=cached):
            self.engine._analyze_symbol("EURUSD.demo")
        self.assertEqual(self.engine.decisions["EURUSD.demo"]["decision"],"BUY")
        self.engine._trade_candidates()
        self.assertEqual(len(self.engine.broker.sent),1)

    def test_expired_qualification_requests_refresh_instead_of_deadlocking(self):
        stale=self.certificate();stale["certificate_expires_at"]=self.now-1
        self.engine.quant_results["EURUSD.demo:M5:engulfing"]=stale
        with patch("nexus.engine.analyze_all",side_effect=self.cards), patch.object(self.engine,"_request_quant") as request:
            self.engine._analyze_symbol("EURUSD.demo")
        request.assert_called_once()
        self.engine._trade_candidates()
        self.assertEqual(self.engine.broker.sent,[])

    def test_strategy_that_explicitly_requires_official_feed_is_still_blocked(self):
        self.require_official_feeds = True
        self.analyze_with_qualified_signal()
        decision = self.engine.decisions["EURUSD.demo"]
        self.assertEqual("REJECT", decision["decision"])
        self.assertIn("required news/calendar coverage missing, stale, or in event blackout",
                      decision["reason_codes"])
        self.engine._trade_candidates()
        self.assertEqual([], self.engine.broker.sent)

    def test_zero_commission_never_needs_contract_profit_conversion(self):
        with patch.object(self.engine.broker, "calc_profit",
                          side_effect=AssertionError("zero commission must not probe profit")):
            config = self.engine._quant_config("EURUSD.demo")
        self.assertEqual(0, config["commission_per_unit"])
        self.assertTrue(config["commission_known"])

    def test_nonzero_commission_uses_stable_multi_tick_conversion_probe(self):
        self.engine.settings["commission_per_lot"] = 5.
        deltas = []

        def rounded_profit(side, symbol, volume, opened, closed):
            deltas.append(closed-opened)
            # A one-tick move rounds to zero; the fixed multi-tick probe does not.
            return round((closed-opened)*0.006, 2)

        with patch.object(self.engine.broker, "calc_profit", side_effect=rounded_profit):
            config = self.engine._quant_config("GOLD#")
        self.assertAlmostEqual(deltas[0], 1.0)
        self.assertGreater(config["commission_per_unit"], 0)


if __name__ == "__main__":
    unittest.main()
