"""Deterministic unit evidence; these fixtures are NOT live market results."""
import copy
import json
import math
import unittest
from unittest.mock import patch

from nexus import committee, quant, strategies


def bars(count=100, step=3600):
    out = []
    previous = 100.0
    for i in range(count):
        close = 100+math.sin(i/4)*2+i*.025
        out.append({"time": 1_600_000_000+i*step, "open": previous, "high": max(previous, close)+.4,
                        "low": min(previous, close)-.4, "close": close, "tick_volume": 100+i,
                        "real_volume": 0, "spread": 2})
        previous = close
    return out


def pattern_bars(count=80, step=3600):
    return [{"time": 1_600_000_000+i*step, "open": 104.0, "high": 104.5, "low": 103.5,
                 "close": 104.0, "tick_volume": 100+i, "real_volume": 0, "spread": 2}
            for i in range(count)]


def card(id="primary", strategy_id="engulfing", timeframe="H1", group="candle", status="READY", side="BUY"):
    return {"id": id, "strategy_id": strategy_id, "school": "fixture", "version": strategies.REGISTRY.get(strategy_id,{}).get('version','1.0.0'), "symbol": "EURUSD.demo",
                "timeframe": timeframe, "evidence_group": group, "status": status, "coverage": "IMPLEMENTED", "quality": "VALIDATED_OHLC",
                "direction": side, "conditions_met": ["explicit condition"], "score": 80.0, "data_time": 1000, "expires_at": 2000,
                "entry": {"price": 100.0, "zone": [99.8, 100.2], "triggered": True}, "actionable": True,
                "stop": {"price": 99}, "targets": [{"price": 102}], "invalidation": {"price": 99.3}, "execution_plan": {"max_hold_bars": 12},
                "evidence": [], "news_requirements": ["calendar"]}


def certificate(c):
    return {"qualified": True, "strategy_id": c["strategy_id"], "version": c["version"], "symbol": c["symbol"],
                "timeframe": c["timeframe"], "data_kind": "broker", "data_time": 1000, "metrics": {"expectancy_r": .3}}


class StrategyTests(unittest.TestCase):
    def test_batched_common_evidence_matches_independent_models(self):
        data=bars(100);now=data[-1]['time']+3600;context={'data_kind':'synthetic'}
        original=copy.deepcopy(data)
        expected=[strategies.analyze_strategy(k,'X','H1',data,now,context) for k in strategies.REGISTRY]
        with patch('nexus.strategies.causal_pivots',wraps=strategies.causal_pivots) as pivots:
            actual=strategies.analyze_all('X','H1',data,now,context)
        self.assertEqual(actual,expected)
        self.assertLess(pivots.call_count,len(strategies.REGISTRY))
        self.assertEqual(data,original)
        data[-1]['high']=0
        self.assertTrue(all(c['status']=='DATA_INVALID' for c in strategies.analyze_all('X','H1',data,now,context)))

    def test_batch_snapshot_isolated_from_model_row_and_pivot_mutations(self):
        data=bars(100);original=copy.deepcopy(data);now=data[-1]['time']+3600
        expected=strategies.analyze_all('X','H1',data,now)
        sid=next(iter(strategies.REGISTRY));analyzer=strategies.REGISTRY[sid]['analyzer']
        def mutate_own_copy(book,context):
            result=analyzer(book,context)
            book[0]['close']=0
            context['pivots'].clear()
            return result
        with patch.dict(strategies.REGISTRY[sid],{'analyzer':mutate_own_copy}):
            actual=strategies.analyze_all('X','H1',data,now)
        self.assertEqual(actual[1:],expected[1:])
        self.assertEqual(data,original)

    def test_batch_shares_validation_but_standalone_never_skips_it(self):
        data=bars(100);now=data[-1]['time']+3600
        with patch('nexus.strategies.validate_bars',wraps=strategies.validate_bars) as validate:
            strategies.analyze_all('X','H1',data,now)
            self.assertLess(validate.call_count,len(strategies.REGISTRY))
        with patch('nexus.strategies.validate_bars',wraps=strategies.validate_bars) as validate:
            strategies.analyze_strategy('ema_cross','X','H1',data,now)
            self.assertGreaterEqual(validate.call_count,1)

    def test_future_and_unfinished_bars_rejected(self):
        b = bars()
        now = b[-1]["time"]+3600
        self.assertEqual(strategies.analyze_strategy("ema_cross", "X", "H1", b, now)["quality"], "VALIDATED_OHLC")
        self.assertEqual(strategies.analyze_strategy("ema_cross", "X", "H1", b, now-1)["status"], "DATA_INVALID")
        self.assertEqual(strategies.analyze_strategy("ema_cross", "X", "H1", b, float("nan"))["status"], "DATA_INVALID")
        json.dumps(strategies.analyze_strategy("ema_cross", "X", "H1", b, float("nan")), allow_nan=False)
        future = b+[dict(b[-1], time=now)]
        self.assertEqual(strategies.analyze_strategy("ema_cross", "X", "H1", future, now)["status"], "DATA_INVALID")

    def test_pivot_confirmed_only_after_right_bars_close(self):
        b = bars(5)
        for i, high in enumerate([101, 102, 106, 103, 102]):
            b[i].update(open=100, close=100, high=high, low=99)
        before = strategies.causal_pivots(b[:4], as_of=b[3]["time"]+3600)
        after = strategies.causal_pivots(b, as_of=b[4]["time"]+3600)
        self.assertFalse(any(p["index"] == 2 for p in before))
        pivot = next(p for p in after if p["index"] == 2)
        self.assertEqual(pivot["confirmed_at"], b[4]["time"]+3600)
        with self.assertRaises(strategies.DataError):
            strategies.causal_pivots(b, as_of=b[4]["time"]+3599)

    def test_registry_algorithms_and_declared_coverage(self):
        b = bars()
        now = b[-1]["time"]+3600
        cards = strategies.analyze_all("TEST.synthetic", "H1", b, now)
        self.assertEqual({c["strategy_id"] for c in cards}, set(strategies.REGISTRY))
        self.assertEqual(sum(c["coverage"] == "IMPLEMENTED" for c in cards), len(strategies.REGISTRY))
        self.assertEqual(sum(c["coverage"] == "PARTIAL" for c in cards), 0)
        self.assertEqual(sum(c["coverage"] == "UNIMPLEMENTED" for c in cards), 0)
        by_id = {c["strategy_id"]: c for c in cards}
        self.assertNotEqual(by_id["ema_cross"]["evidence"], by_id["rsi_rebound"]["evidence"])
        self.assertNotEqual(by_id["darvas_box"]["evidence"], by_id["ichimoku_cross"]["evidence"])
        self.assertEqual(by_id["interasset_confirmation"]["status"], "DATA_MISSING")
        self.assertTrue(all(not c["actionable"] for c in cards if c["coverage"] != "IMPLEMENTED"))
        json.dumps(cards, allow_nan=False)

    def test_classic_double_top_waits_for_pivot_confirmation_and_fresh_neckline_break(self):
        b = pattern_bars()
        b[64]["high"] = 110.0
        b[68]["low"] = 100.0
        b[72]["high"] = 109.8
        b[-2].update(open=104.0, high=104.2, low=100.8, close=101.0)
        b[-1].update(open=101.0, high=101.2, low=99.2, close=99.5)

        before_confirmation = strategies.analyze_strategy(
            "classic_reversal_patterns", "TEST", "H1", b[:74], b[73]["time"]+3600)
        self.assertEqual(before_confirmation["status"], "WAIT")
        self.assertFalse(before_confirmation["actionable"])

        result = strategies.analyze_strategy(
            "classic_reversal_patterns", "TEST", "H1", b, b[-1]["time"]+3600)
        self.assertEqual((result["status"], result["direction"]), ("READY", "SELL"))
        self.assertTrue(result["actionable"])
        geometry = result["evidence"][0]["value"]
        self.assertEqual(geometry["name"], "double_top")
        self.assertLessEqual(geometry["last_pivot_confirmed_at"], result["data_time"])
        self.assertEqual(result["invalidation"]["evaluation"], "completed_bar_close")
        self.assertLess(result["targets"][0]["price"], result["entry"]["price"])

        inverse = pattern_bars()
        inverse[64]["low"] = 98.0
        inverse[68]["high"] = 108.0
        inverse[72]["low"] = 98.2
        inverse[-2].update(open=104.0, high=107.2, low=103.8, close=107.0)
        inverse[-1].update(open=107.0, high=108.8, low=106.8, close=108.5)
        bullish = strategies.analyze_strategy(
            "classic_reversal_patterns", "TEST", "H1", inverse, inverse[-1]["time"]+3600)
        self.assertEqual((bullish["status"], bullish["direction"]), ("READY", "BUY"))
        self.assertEqual(bullish["evidence"][0]["value"]["name"], "double_bottom")
        self.assertGreater(bullish["targets"][0]["price"], bullish["entry"]["price"])

    def test_classic_head_shoulders_uses_sloped_neckline_from_confirmed_swings(self):
        b = pattern_bars()
        for index, price in ((58, 108.0), (66, 112.0), (74, 108.2)):
            b[index]["high"] = price
        for index, price in ((62, 102.0), (70, 102.2)):
            b[index]["low"] = price
        b[-2].update(open=104.0, high=104.2, low=102.8, close=103.0)
        b[-1].update(open=103.0, high=103.2, low=101.2, close=101.5)

        result = strategies.analyze_strategy(
            "classic_reversal_patterns", "TEST", "H1", b, b[-1]["time"]+3600)
        self.assertEqual((result["status"], result["direction"]), ("READY", "SELL"))
        geometry = result["evidence"][0]["value"]
        self.assertEqual(geometry["name"], "head_and_shoulders")
        self.assertNotEqual(geometry["neckline_previous"], geometry["neckline_now"])
        self.assertEqual(geometry["invalidation"], 112.0)

    def test_geometric_triangle_needs_six_confirmed_swings_and_latest_close_breakout(self):
        b = pattern_bars()
        for index, price in ((55, 110.0), (63, 109.0), (71, 108.0)):
            b[index]["high"] = price
        for index, price in ((59, 100.0), (67, 101.0), (75, 102.0)):
            b[index]["low"] = price
        b[-2].update(open=105.0, high=107.0, low=104.5, close=106.8)
        b[-1].update(open=106.8, high=107.8, low=106.5, close=107.5)

        waiting = strategies.analyze_strategy(
            "geometric_triangle_breakout", "TEST", "H1", b[:-1], b[-2]["time"]+3600)
        self.assertEqual(waiting["status"], "WAIT")
        self.assertFalse(waiting["actionable"])

        result = strategies.analyze_strategy(
            "geometric_triangle_breakout", "TEST", "H1", b, b[-1]["time"]+3600)
        self.assertEqual((result["status"], result["direction"]), ("READY", "BUY"))
        geometry = result["evidence"][0]["value"]
        self.assertEqual(geometry["pattern"], "symmetrical_triangle")
        self.assertTrue(geometry["prior_closes_inside"])
        self.assertLess(geometry["current_height"], geometry["initial_height"])
        self.assertLessEqual(geometry["latest_pivot_confirmed_at"], result["data_time"])
        self.assertGreater(result["targets"][0]["price"], result["entry"]["price"])

        downside = copy.deepcopy(b)
        downside[-2].update(open=105.0, high=105.5, low=103.1, close=103.2)
        downside[-1].update(open=103.2, high=103.4, low=102.0, close=102.3)
        bearish = strategies.analyze_strategy(
            "geometric_triangle_breakout", "TEST", "H1", downside, downside[-1]["time"]+3600)
        self.assertEqual((bearish["status"], bearish["direction"]), ("READY", "SELL"))
        self.assertLess(bearish["targets"][0]["price"], bearish["entry"]["price"])

    def test_manifest_never_claims_interasset_execution_without_explicit_partner_mapping(self):
        manifest={row["id"]:row for row in strategies.registry_manifest()}
        interasset=manifest["interasset_confirmation"]
        self.assertEqual(interasset["coverage"],"IMPLEMENTED")
        self.assertIn("explicit_partner_symbol",interasset["data_requirements"])
        self.assertIn("aligned_partner_ohlc",interasset["data_requirements"])
        self.assertTrue(all("explicit_partner_symbol" in row["data_requirements"]
                            for row in manifest.values() if "aligned_partner_ohlc" in row["data_requirements"]))

    def test_every_implemented_strategy_has_runtime_inputs_and_committee_family(self):
        runtime_inputs={"completed_ohlc","bar_real_volume_or_labeled_tick_proxy","explicit_anchor","positive_tick_volume","explicit_partner_symbol","aligned_partner_ohlc","broker_daily_history","fresh_executable_quote","actual_volume_profile_or_declared_local_timing"}
        for row in strategies.registry_manifest():
            if row["coverage"]!="IMPLEMENTED":
                continue
            with self.subTest(strategy=row["id"]):
                self.assertLessEqual(set(row["data_requirements"]),runtime_inputs)
                self.assertEqual(row["news_requirements"],["calendar"])
                self.assertIn(row["evidence_group"],committee.GROUPS)
                self.assertLessEqual(row["min_bars"],300)

    def test_interasset_candidate_rejects_missing_or_self_partner_identity(self):
        b=bars(80);now=b[-1]["time"]+3600
        for context in ({"partner_bars":b},{"partner_symbol":"TEST","partner_bars":b}):
            c=strategies.analyze_strategy("interasset_confirmation","TEST","H1",b,now,context)
            self.assertEqual(c["status"],"DATA_MISSING")
            self.assertFalse(c["actionable"])

    def test_candle_entry_and_analysis_invalidation_are_distinct(self):
        b = bars(30)
        b[-2].update(open=101, close=100, low=99.8, high=101.1)
        b[-1].update(open=99.9, close=101.2, low=99.7, high=101.4)
        c = strategies.analyze_strategy("engulfing", "TEST", "H1", b, b[-1]["time"]+3600)
        self.assertEqual(c["status"], "READY")
        self.assertTrue(c["entry"]["triggered"])
        self.assertLess(c["stop"]["price"], c["invalidation"]["price"])
        self.assertGreater(c["targets"][0]["price"], c["entry"]["price"])
        self.assertFalse(c["execution_plan"]["allow_addition"])
        self.assertEqual(c["id"], strategies.analyze_strategy("engulfing", "TEST", "H1", b, b[-1]["time"]+3601)["id"])

    def test_ichimoku_cloud_is_historically_computed(self):
        b = bars()
        c = strategies.analyze_strategy("ichimoku_cross", "TEST", "H1", b, b[-1]["time"]+3600)
        evidence = c["evidence"][0]["value"]
        historical = b[:-26]
        expected_b = (max(x["high"] for x in historical[-52:])+min(x["low"] for x in historical[-52:]))/2
        self.assertEqual(evidence["current_cloud_b"], expected_b)
        self.assertEqual(evidence["cloud_origin_time"], b[-27]["time"])

    def test_tick_weighting_is_explicit_proxy_and_anchor_is_respected(self):
        b = bars(30)
        anchor = b[-8]["time"]
        c = strategies.analyze_strategy("vwap_reclaim", "TEST", "H1", b, b[-1]["time"]+3600, {"anchor_time": anchor})
        self.assertEqual(c["evidence"][0]["weight_source"], "tick_volume")
        self.assertEqual(c["evidence"][0]["anchor_time"], anchor)
        self.assertTrue(any("proxy" in a for a in c["assumptions"]))
        weighted = sum((x["high"]+x["low"]+x["close"])/3*x["tick_volume"] for x in b[-8:])/sum(x["tick_volume"] for x in b[-8:])
        self.assertAlmostEqual(c["evidence"][0]["value"], weighted)

    def test_vwap_requires_history_covering_declared_anchor(self):
        b=bars(40,60);now=b[-1]["time"]+60
        card=strategies.analyze_strategy("vwap_reclaim","TEST","M1",b,now,
                                         {"anchor_time":b[0]["time"]-3600,"data_kind":"broker"})
        self.assertEqual(card["status"],"DATA_MISSING")
        self.assertIn("مرساة", " ".join(card["conditions_missing"]))
        self.assertEqual(card["data_kind"],"broker")
        self.assertIn("الوسيط", " ".join(card["sources"]))

    def test_historical_prefix_not_affected_by_later_data(self):
        b = bars(120)
        now = b[99]["time"]+3600
        first = strategies.analyze_strategy("fib_retracement", "TEST", "H1", b[:100], now)
        later = copy.deepcopy(b)
        for x in later[100:]:
            x.update(open=500, close=500, high=501, low=499)
        second = strategies.analyze_strategy("fib_retracement", "TEST", "H1", later[:100], now)
        self.assertEqual(first, second)


class QuantTests(unittest.TestCase):
    def test_next_bar_fill_and_ambiguous_bar_stop_first_with_costs(self):
        b = bars(35)
        for x in b:
            x.update(open=100, close=100, low=99.8, high=100.2, spread=1)
        b[20].update(low=98, high=103)
        def signal(history, as_of):
            if history[-1]["time"] != b[19]["time"]:
                return {"status": "WAIT"}
            c = card()
            c["entry"]["zone"] = [99, 101]
            return c
        result = quant.replay(b, "engulfing", start_index=19, end_index=22,
                              config={"point": .1, "slippage_price": .05, "commission_per_unit": .03}, signal_fn=signal)
        trade = result["trades"][0]
        self.assertEqual(trade["entry_index"], 20)
        self.assertGreaterEqual(trade["entry_time"], trade["signal_time"])
        self.assertEqual(trade["exit_reason"], "STOP")
        self.assertTrue(trade["ambiguous_bar"])
        self.assertAlmostEqual(trade["entry"], 100.15)
        self.assertAlmostEqual(trade["exit"], 98.95)
        self.assertLess(trade["r"], -1)

    def test_stop_gap_executes_worse_than_stop(self):
        b = bars(35)
        for x in b:
            x.update(open=100, close=100, low=99.8, high=100.2, spread=0)
        b[21].update(open=97, close=97.5, low=96.5, high=98)
        def signal(history, as_of):
            return card() if history[-1]["time"] == b[19]["time"] else {"status": "WAIT"}
        result = quant.replay(b, "engulfing", start_index=19, end_index=25, signal_fn=signal)
        self.assertEqual(result["trades"][0]["exit"], 97)
        self.assertEqual(result["trades"][0]["r"], -3)

    def test_running_replay_cancels_without_returning_partial_certificate(self):
        import threading
        from concurrent.futures import CancelledError
        event=threading.Event()
        calls=[]
        def signal(history, as_of):
            calls.append(as_of);event.set()
            return {"status":"WAIT"}
        with self.assertRaises(CancelledError):
            quant.replay(bars(100),"engulfing",signal_fn=signal,cancel_event=event)
        self.assertEqual(len(calls),1)
        with self.assertRaises(CancelledError):
            quant.walk_forward(bars(600),"ema_cross",cancel_event=event)

    def test_walk_forward_embargo_and_synthetic_ineligible(self):
        b = bars(600)
        cfg = {"train_bars": 100, "test_bars": 100, "embargo_bars": 3, "max_hold_bars": 12,
               "point": .01, "commission_known": True}
        result = quant.walk_forward(b, "ema_cross", config=cfg, data_kind="synthetic")
        self.assertFalse(result["qualified"])
        self.assertTrue(any("synthetic" in r for r in result["reasons"]))
        self.assertGreaterEqual(len(result["folds"]), 2)
        for fold in result["folds"]:
            self.assertGreaterEqual(fold["test_start_index"]-fold["train_end_exclusive"], 12)
            for trade in fold["trades"]:
                self.assertLess(trade["exit_index"], fold["test_end_exclusive"])
                self.assertGreater(trade["entry_index"], fold["test_start_index"])

    def test_invalidation_and_time_exit_follow_completed_close(self):
        b = bars(35)
        for x in b:
            x.update(open=100, close=100, low=99.8, high=100.2, spread=0)
        b[20].update(close=99.2, low=99.1)
        b[21].update(open=99.1, close=99.4, low=99.05)
        def signal(history, as_of):
            return card() if history[-1]["time"] == b[19]["time"] else {"status": "WAIT"}
        trade = quant.replay(b, "engulfing", start_index=19, end_index=25, signal_fn=signal)["trades"][0]
        self.assertEqual(trade["exit_reason"], "INVALIDATION_NEXT_OPEN")
        self.assertEqual(trade["exit_index"], 21)
        self.assertEqual(trade["exit_time"], b[21]["time"])
        self.assertEqual(trade["exit"], 99.1)
        for x in b:
            x.update(open=100, close=100, low=99.8, high=100.2)
        trade = quant.replay(b, "engulfing", start_index=19, end_index=25,
                             config={"max_hold_bars": 2}, signal_fn=signal)["trades"][0]
        self.assertEqual(trade["exit_reason"], "TIME_NEXT_OPEN")
        self.assertEqual(trade["exit_index"], 22)

    def test_sell_spread_and_stop_first_model(self):
        b = bars(35)
        for x in b:
            x.update(open=100, close=100, low=99.8, high=100.2, spread=2)
        b[20].update(high=100.95, low=97)
        def signal(history, as_of):
            if history[-1]["time"] != b[19]["time"]:
                return {"status": "WAIT"}
            c = card(side="SELL")
            c["stop"]["price"] = 101
            c["targets"][0]["price"] = 98
            c["invalidation"]["price"] = 100.7
            return c
        trade = quant.replay(b, "engulfing", start_index=19, end_index=25,
                             config={"point": .1}, signal_fn=signal)["trades"][0]
        self.assertEqual(trade["entry"], 100)
        self.assertEqual(trade["exit_reason"], "STOP")
        self.assertTrue(trade["ambiguous_bar"])

    def test_execution_grid_rounding_matches_broker_plan(self):
        b = bars(35)
        for x in b:
            x.update(open=100, close=100, low=99.8, high=100.2, spread=0)
        b[20].update(low=98, high=103)
        def signal(history, as_of):
            if history[-1]["time"] != b[19]["time"]:
                return {"status": "WAIT"}
            c = card()
            c["stop"]["price"] = 99.13
            c["targets"][0]["price"] = 102.13
            return c
        trade = quant.replay(b, "engulfing", start_index=19, end_index=25, context={"tick_size": .25}, signal_fn=signal)["trades"][0]
        self.assertEqual(trade["stop"], 99)
        self.assertEqual(trade["target"], 102.25)

    def test_oos_fold_unchanged_when_future_bars_change(self):
        b = bars(600)
        cfg = {"train_bars": 100, "test_bars": 100, "point": .01, "commission_known": True}
        before = quant.walk_forward(b, "ema_cross", config=cfg)
        altered = copy.deepcopy(b)
        for x in altered[212:]:
            x.update(open=300, close=300, high=301, low=299)
        after = quant.walk_forward(altered, "ema_cross", config=cfg)
        self.assertEqual(before["folds"][0], after["folds"][0])

    def test_unknown_costs_insufficient_samples_and_partial_never_qualify(self):
        b = bars(100)
        result = quant.walk_forward(b, "ema_cross")
        self.assertFalse(result["qualified"])
        self.assertTrue(any("commission" in r for r in result["reasons"]))
        self.assertTrue(any("insufficient" in r for r in result["reasons"]))
        with patch.dict(strategies.REGISTRY["elliott_candidate"], {"coverage": "PARTIAL"}):
            self.assertEqual(quant.walk_forward(b, "elliott_candidate")["status"], "INELIGIBLE")


class CommitteeTests(unittest.TestCase):
    def setup_cards(self):
        primary = card()
        support = card("support", "ema_cross", "H4", "trend", "WAIT")
        return primary, support

    def evaluate(self, cards, news=None, cert=None):
        return committee.decide(cards, cert if cert is not None else [certificate(cards[0])],
                                news if news is not None else {"ok": True, "coverage": {"calendar": True}, "blackout": False}, as_of=1500)

    def test_eligible_entry_returns_risk_proposal(self):
        c = self.setup_cards()
        result = self.evaluate(c)
        self.assertEqual(result["decision"], "BUY")
        proposal = result["proposals"][0]
        self.assertTrue(proposal["qualified"] and proposal["news_ok"])
        self.assertEqual(proposal["sl"], 99)
        self.assertEqual(proposal["tp"], 102)
        self.assertEqual(proposal["id"], c[0]["id"])

    def test_news_missing_or_blackout_is_rejected(self):
        for news in ({"ok": False, "coverage": {}}, {"ok": True, "coverage": {"calendar": False}},
                     {"ok": True, "coverage": {"calendar": True}, "blackout": True}):
            self.assertEqual(self.evaluate(self.setup_cards(), news)["decision"], "REJECT")

    def test_timeframes_disagreement_and_quant_simulation_rejected(self):
        c = list(self.setup_cards())
        c[1].update(direction="SELL",status="READY",actionable=True)
        self.assertIn("timeframes disagree", self.evaluate(c)["reason_codes"])
        c = self.setup_cards()
        cert = certificate(c[0])
        cert["data_kind"] = "synthetic"
        self.assertEqual(self.evaluate(c, cert=[cert])["decision"], "REJECT")
        cert = certificate(c[0])
        cert["data_time"] = 1501
        self.assertEqual(self.evaluate(c, cert=[cert])["decision"], "REJECT")

    def test_waiting_opposite_context_does_not_veto_two_frame_confirmation(self):
        primary,support=self.setup_cards()
        waiting_opposite=card("context-only","rsi_rebound","M15","momentum","WAIT","SELL")
        result=self.evaluate([primary,support,waiting_opposite])
        self.assertEqual(result["decision"],"BUY")
        self.assertNotIn("timeframes disagree",result.get("reason_codes",[]))
        self.assertIn(waiting_opposite["id"],result["ranked"][0]["opposing"])

    def test_expired_future_and_other_strategy_certificates_rejected(self):
        c = self.setup_cards()
        for changes in ({"certificate_expires_at": 1499}, {"checked_at": 1501}, {"checked_at": -90000},
                        {"certificate_expires_at": float("nan")}):
            cert = certificate(c[0]);cert.update(changes)
            self.assertEqual(self.evaluate(c, cert=[cert])["decision"], "REJECT")
        cert = certificate(c[0]);cert["strategy_id"] = "ema_cross"
        self.assertEqual(self.evaluate(c, cert={"engulfing": cert})["decision"], "REJECT")

    def test_opposing_setup_outside_its_entry_zone_does_not_veto_valid_entry(self):
        primary,support=self.setup_cards()
        opposite=card("opposite","rsi_rebound","M15","momentum","READY","SELL")
        opposite["entry"]["zone"]=[101,101.2]
        market={"eligible":True,"open":True,"stale":False,"spread":.01,"tick":{"bid":100.,"ask":100.01}}
        news={"ok":True,"coverage":{"calendar":True},"blackout":False}
        result=committee.decide([primary,support,opposite],[certificate(primary)],news,1500,market)
        self.assertEqual(result["decision"],"BUY")
        self.assertIn("opposite",result["ranked"][0]["opposing"])
        opposite["entry"]["zone"]=[99.9,100.1]
        result=committee.decide([primary,support,opposite],[certificate(primary)],news,1500,market)
        self.assertIn("triggered schools disagree",result["reason_codes"])
        self.assertFalse(result["proposals"])

    def test_correlated_indicators_not_independent_votes(self):
        c = list(self.setup_cards())
        c[0]["evidence_group"] = "momentum"
        c[1]["evidence_group"] = "trend"
        result = self.evaluate(c)
        # The card may not rewrite the registry-declared dependency family.
        # It fails closed before voting instead of manufacturing independence.
        self.assertEqual(result["decision"], "WAIT")
        self.assertIn("no fresh completed and triggered entry setup", result["reason_codes"])

    def test_registry_is_authoritative_over_forged_partial_version_and_group(self):
        primary,support=self.setup_cards()
        forged=card("forged","elliott_candidate","M15","structure","WAIT")
        forged.update(coverage="IMPLEMENTED",version="1.0.0",conditions_met=["fake"],score=100)
        result=self.evaluate([primary,forged])
        self.assertEqual(result["decision"],"REJECT")
        self.assertIn("fewer than two distinct evidence families after dependency grouping",result["reason_codes"])
        for mutation in ({"version":"999.0"},{"evidence_group":"invented_independent_family"}):
            candidate=copy.deepcopy(primary);candidate.update(mutation)
            self.assertEqual(self.evaluate([candidate,support])["decision"],"WAIT")

    def test_partial_cards_excluded_even_if_mislabeled_ready(self):
        c = list(self.setup_cards())
        c[1]["coverage"] = "PARTIAL"
        self.assertEqual(self.evaluate(c)["decision"], "REJECT")
        c[0]["coverage"] = "PARTIAL"
        self.assertEqual(self.evaluate(c)["decision"], "WAIT")

    def test_direction_and_stale_entries_never_suffice(self):
        c = list(self.setup_cards())
        c[0]["entry"]["triggered"] = False
        self.assertEqual(self.evaluate(c)["decision"], "WAIT")
        c[0]["entry"]["triggered"] = True
        c[0]["expires_at"] = 1499
        self.assertEqual(self.evaluate(c)["decision"], "WAIT")


if __name__ == "__main__":
    unittest.main()
