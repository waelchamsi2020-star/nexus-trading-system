"""Adversarial four-school protocol fixtures, not performance evidence."""
import copy
import json
import math
import unittest
from unittest.mock import patch

from nexus import confluence as cf

BASE = 1728000000
STEP = 300


def fixture(last=53):
    b = [{"time": BASE+i*STEP, "open": 99.2, "high": 100, "low": 99, "close": 99.5,
              "tick_volume": 100, "real_volume": 0, "spread": 1} for i in range(last+1)]

    def setbar(i, o, h, l, c):
        b[i].update(open=o, high=h, low=l, close=c)
    setbar(20, 99, 145, 99, 99.5)  # known unswept destination, not a fabricated 2R target
    setbar(25, 99, 100, 93, 99.5)
    setbar(35, 99, 103, 99, 99.5)  # pre-sweep protected opposing structure
    setbar(40, 98, 100, 92, 99.5)  # confirmed sell-side liquidity
    setbar(44, 98, 100, 90, 99.5)  # first sweep/reclaim, later confirmed protected pivot
    setbar(45, 99, 101, 98.5, 100)
    setbar(46, 100, 107, 98, 106)  # fresh displacement BOS
    setbar(47, 106, 108, 105, 106.5)  # FVG [101, 105] becomes known only now
    for i in range(48, last):
        setbar(i, 106, 108, 105.5, 106.5)
    setbar(last, 102, 105.2, 101.5, 104)  # first return, completed bullish body inside gap
    return b


def quote(b, bid=103.9, ask=104.):
    return {"bid": bid, "ask": ask, "time": b[-1]["time"]+STEP}


def actual_profile(b, poc=103.5):
    return {"kind": "TRADE_VOLUME_AT_PRICE", "source_type": "EXECUTED_TRANSACTIONS",
            "provenance_verified": True, "source": "fixture exchange trade adapter", "venue": "TEST",
            "symbol": "TEST", "units": "contracts", "complete": True, "coverage": 1.,
            "window_start": b[40]["time"], "window_end": b[-1]["time"]+STEP,
            "bins": [{"price": 100., "volume": 1.}, {"price": poc, "volume": 50.},
                     {"price": 110., "volume": 1.}]}


def run(b=None, profile=None, **kwargs):
    b = fixture() if b is None else b
    return cf.evaluate("TEST", "M5", b, b[-1]["time"]+STEP, .1, profile,
                       quote=kwargs.pop("quote", quote(b)), **kwargs)


# Vulture review: unittest/pytest discovers and executes this TestCase by module inspection.
class FourSchoolConfluence(unittest.TestCase):
    def test_causal_complete_chain_uses_quote_and_known_structural_plan(self):
        result = run()
        self.assertEqual(result["status"], "READY", result)
        self.assertTrue(result["matrix"]["passed"])
        self.assertEqual(result["matrix"]["route"], "ICT_PLUS_HOUSE_TIMING")
        c = result["candidate"]
        self.assertEqual(c["side"], "LONG")
        self.assertEqual(c["entry_reference"], "ACTUAL_ASK")
        self.assertEqual(c["structure_stop"], 89.9)
        self.assertEqual(c["target"], 145)
        self.assertGreaterEqual(c["gross_rr"], 2)
        evidence = c["structural_evidence"]
        self.assertLess(evidence["liquidity_pool"]["confirmed_at"], evidence["sweep_time"])
        self.assertLess(evidence["sweep_time"], evidence["bos_time"])
        self.assertLess(evidence["gap_completed_at"], c["data_time"])
        self.assertFalse(result["matrix"]["volume_profile"]["available"])
        self.assertEqual(result["matrix"]["time"]["evidence"]["matching_cycle"], 8)
        self.assertFalse(c["win_probability_asserted"])
        json.dumps(result, allow_nan=False)

    def test_missing_profile_never_built_from_tick_or_real_bar_volume(self):
        b = fixture(last=56)  # twelve bars since pivot; no 8/16 +/-1 timing
        for bar in b:
            bar.update(tick_volume=999999, real_volume=12345)
        result = run(b)
        self.assertIn("TIMING_NOT_ALIGNED", result["reason_codes"])
        self.assertEqual(result["matrix"]["volume_profile"]["status"], "DATA_MISSING")
        self.assertFalse(result["matrix"]["passed"])
        self.assertIsNone(result["candidate"])

    def test_genuine_poc_route_overrides_only_time_momentum_elliott(self):
        b = fixture(last=56)
        with patch.object(cf, "_momentum", return_value=cf._row("CONFIRMED", direction="SHORT")), \
                patch.object(cf, "_elliott", return_value=cf._row("CONTEXT_CONFIRMED", direction="SHORT")):
            r = run(b, actual_profile(b))
        self.assertEqual(r["status"], "READY", r)
        self.assertEqual(r["matrix"]["route"], "ICT_PLUS_ACTUAL_POC")
        self.assertEqual(set(r["matrix"]["overridden_context"]), {"time", "momentum", "elliott"})
        self.assertEqual(r["candidate"]["target"], 145)
        self.assertFalse(r["matrix"]["volume_profile"]["evidence"]["institutional_identity_asserted"])

    def test_poc_outside_zone_does_not_resolve_timing_or_opposition(self):
        b = fixture(last=56)
        r = run(b, actual_profile(b, 108.))
        self.assertEqual(r["matrix"]["volume_profile"]["reason"]["code"], "POC_OUTSIDE_ZONE")
        self.assertIn("TIMING_NOT_ALIGNED", r["reason_codes"])
        with patch.object(cf, "_momentum", return_value=cf._row("CONFIRMED", direction="SHORT")):
            r = run()
        self.assertIn("MOMENTUM_OPPOSES", r["reason_codes"])
        self.assertFalse(r["matrix"]["passed"])

    def test_profile_provenance_coverage_window_and_volume_types_fail_closed(self):
        b = fixture(last=56)
        variants = [{"source_type": "TICK_ACTIVITY"}, {"kind": "OHLC_VOLUME_REDISTRIBUTION"},
                    {"provenance_verified": False}, {"coverage": .98}, {"complete": False},
                    {"window_end": b[-1]["time"]+STEP+1}, {"window_start": b[45]["time"]},
                    {"venue": ""}, {"symbol": "WRONG"}, {"units": "ticks"}]
        for changes in variants:
            p = actual_profile(b)
            p.update(changes)
            with self.subTest(changes=changes):
                r = run(b, p)
                self.assertEqual(r["matrix"]["volume_profile"]["status"], "DATA_ERROR")
                self.assertFalse(r["matrix"]["passed"])
        for bad in (0, -1, float("nan"), float("inf"), True):
            p = actual_profile(b)
            p["bins"][1]["volume"] = bad
            self.assertEqual(run(b, p)["matrix"]["volume_profile"]["status"], "DATA_ERROR")
        p = actual_profile(b)
        p["bins"][0]["volume"] = 50.  # ambiguous tied POC
        self.assertEqual(run(b, p)["matrix"]["volume_profile"]["status"], "DATA_ERROR")

    def test_future_bar_rejected_rather_than_trimmed(self):
        b = fixture()
        future = copy.deepcopy(b[-1])
        future["time"] += STEP
        original_time = b[-1]["time"]+STEP
        b.append(future)
        r = cf.evaluate("TEST", "M5", b, original_time, .1, quote=quote(fixture()))
        self.assertEqual(r["status"], "DATA_ERROR")
        self.assertFalse(r["matrix"]["passed"])

    def test_broken_or_reused_structure_is_rejected_with_same_primary_profile(self):
        for index, changes in ((50, {"low": 89., "open": 90., "close": 106.5}),
                               (50, {"low": 104.}),  # prior gap touch, no first return
                               (43, {"low": 91.}),  # pool already swept before marked sweep
                               (46, {"open": 105., "low": 104., "close": 106.}),  # non-displacement
                               (46, {"open": 100., "close": 102.})):  # no close BOS
            b = fixture()
            b[index].update(changes)
            with self.subTest(index=index, changes=changes):
                r = run(b, actual_profile(b))
                self.assertFalse(r["matrix"]["passed"])
                self.assertIn("ICT_CHAIN_INCOMPLETE", r["reason_codes"])

    def test_confirmed_pivot_not_created_by_future_confirmation(self):
        # Equal neighbor removes the strict liquidity pivot. Quotes/profile
        # cannot turn an unconfirmed level into a causal structure.
        b = fixture()
        b[42]["low"] = 92.
        r = run(b, actual_profile(b))
        self.assertFalse(r["matrix"]["passed"])
        self.assertIn("ICT_CHAIN_INCOMPLETE", r["reason_codes"])

    def test_rr_uses_actual_ask_and_never_moves_nearest_target(self):
        b = fixture()
        # Place nearer still-unswept liquidity at 130. Risk 14.1, reward 26.
        b[20]["high"] = 130.
        r = run(b, actual_profile(b))
        self.assertIn("RR_BELOW_TWO", r["reason_codes"])
        self.assertIsNone(r["candidate"])
        b[20]["high"] = 132.2  # exactly 2*(104-89.9) above 104
        r = run(b, actual_profile(b))
        self.assertEqual(r["status"], "READY", r)
        self.assertEqual(r["candidate"]["gross_rr"], 2.)
        r = run(b, actual_profile(b), quote=quote(b, bid=104., ask=104.01))
        self.assertIn("RR_BELOW_TWO", r["reason_codes"])

    def test_target_must_predate_sweep_and_remain_unswept(self):
        b = fixture()
        b[20]["high"] = 110.
        b[34]["high"] = 111.  # consumes preexisting target; also removes proper BOS anchor
        r = run(b, actual_profile(b))
        self.assertFalse(r["matrix"]["passed"])
        b = fixture()
        b[20]["high"] = 108.
        # All old high levels consumed by the BOS and gap creation.
        r = run(b, actual_profile(b))
        self.assertIn("NO_UNSWEPT_TARGET", r["reason_codes"])

    def test_nearest_target_cannot_be_skipped_for_more_attractive_rr(self):
        b = fixture()
        b[30]["high"] = 130.  # unswept, known before sweep, nearer than 145
        r = run(b, actual_profile(b))
        self.assertIn("RR_BELOW_TWO", r["reason_codes"])
        b[30]["high"] = 135.
        r = run(b, actual_profile(b))
        self.assertEqual(r["status"], "READY", r)
        self.assertEqual(r["candidate"]["target"], 135.)
        self.assertEqual(r["candidate"]["target_evidence"]["index"], 30)

    def test_a_later_break_cannot_reuse_an_already_broken_bos_level(self):
        b = fixture()
        # First BOS has no displacement/FVG. A later flashy gap cannot make
        # the old structural reference become an intact first break again.
        b[45].update(open=103.5, close=104., high=104.2, low=99.)
        b[46].update(open=104., close=102., high=104.2, low=98.)
        b[47].update(open=102., close=110., high=111., low=101.)
        b[48].update(open=110., close=110.5, high=112., low=109.)
        for i in range(49, 53):
            b[i].update(open=111., close=111.5, high=112., low=110.)
        b[53].update(open=105., close=106., high=109., low=104.5)
        r = run(b, actual_profile(b), quote=quote(b, bid=105.9, ask=106.))
        self.assertIn("ICT_CHAIN_INCOMPLETE", r["reason_codes"])

    def test_actual_divergence_uses_only_confirmed_pivot_rsi_values(self):
        b = fixture()
        # An adverse move into the first lower-low creates weaker RSI, then
        # a shallower final price swing recovers RSI at the next lower low.
        for i in range(26, 41):
            c = 99.5-(i-25)*.25
            b[i].update(open=c+.1, close=c, high=max(100., c+.2), low=min(b[i]["low"], c-.2))
        b[35]["high"] = 103.
        b[41].update(open=96., close=96.2, high=100., low=96.)
        b[42].update(open=96.2, close=97., high=100., low=96.1)
        b[43].update(open=97., close=98., high=100., low=96.5)
        b[44].update(open=98., close=99., high=100., low=90.)
        pivots = cf.causal_pivots(b, as_of=b[-1]["time"]+STEP, timeframe="M5")
        result = cf._momentum(b, pivots, .1)
        self.assertEqual(result["direction"], "LONG", result)
        low_pair = next(p for p in result["evidence"]["pairs"] if p["kind"] == "LOW")
        self.assertTrue(low_pair["divergence"])
        self.assertGreaterEqual(low_pair["second_rsi"]-low_pair["first_rsi"], 2)
        self.assertLess(low_pair["second"]["confirmed_at"], b[-1]["time"]+STEP)

    def test_quote_must_be_live_ordered_and_inside_original_gap(self):
        b = fixture()
        for q in ({"bid": 104, "ask": 103, "time": b[-1]["time"]+STEP},
                  {"bid": 103.9, "ask": 104, "time": b[-1]["time"]+STEP-61},
                  {"bid": 103.9, "ask": 104, "time": b[-1]["time"]+STEP+1},
                  {"bid": float("nan"), "ask": 104, "time": b[-1]["time"]+STEP}):
            r = run(b, quote=q)
            self.assertIn("QUOTE_INVALID", r["reason_codes"])
        r = run(b, quote=quote(b, bid=105., ask=105.1))
        self.assertIn("QUOTE_OUTSIDE_ZONE", r["reason_codes"])
        r = run(b, quote=None)
        self.assertEqual(r["status"], "RESEARCH_READY")
        self.assertFalse(r["matrix"]["passed"])
        self.assertFalse(r["candidate"]["execution_ready"])

    def test_mirror_produces_short_with_bid_and_same_structural_ratio(self):
        b = fixture()
        # Price mirror around 200 reverses all strict inequalities.
        mirrored = []
        for x in b:
            y = {**x, "open": 200-x["open"], "close": 200-x["close"],
                 "high": 200-x["low"], "low": 200-x["high"]}
            mirrored.append(y)
        r = run(mirrored, quote={"bid": 96., "ask": 96.1, "time": mirrored[-1]["time"]+STEP})
        self.assertEqual(r["status"], "READY", r)
        c = r["candidate"]
        self.assertEqual(c["side"], "SHORT")
        self.assertEqual(c["entry_reference"], "ACTUAL_BID")
        self.assertEqual(c["stop"], 110.1)
        self.assertEqual(c["target"], 55.)
        self.assertAlmostEqual(c["gross_rr"], run()["candidate"]["gross_rr"])

    def test_identity_determinism_input_immutability_and_definition_pinning(self):
        b = fixture()
        q = quote(b)
        p = actual_profile(b)
        before = copy.deepcopy((b, q, p))
        a = run(b, p, quote=q)
        c = run(b, p, quote=q)
        self.assertEqual(a, c)
        self.assertEqual((b, q, p), before)
        revision = cf.PROTOCOL_REVISION
        d = cf.definition()
        d["parameters"]["min_reward_risk"] = 0
        public = copy.deepcopy(cf.PROTOCOL)
        try:
            cf.PROTOCOL["parameters"]["min_reward_risk"] = 0
            self.assertEqual(cf.definition()["parameters"]["min_reward_risk"], 2)
            self.assertEqual(cf.PROTOCOL_REVISION, revision)
            self.assertEqual(run(b, p, quote=q), a)
        finally:
            cf.PROTOCOL.clear()
            cf.PROTOCOL.update(public)
        q["ask"] = 104.1
        changed = run(b, p, quote=q)
        self.assertEqual(changed["candidate"]["formation_id"], a["candidate"]["formation_id"])
        self.assertNotEqual(changed["candidate"]["quote_risk_exact"], a["candidate"]["quote_risk_exact"])

    def test_future_price_content_cannot_rewrite_a_past_snapshot(self):
        b = fixture()
        past = run(b)
        future = fixture(last=60)
        future[-1].update(high=150, close=149, open=120, low=119)
        self.assertEqual(run(copy.deepcopy(b)), past)
        self.assertNotEqual(run(future)["status"], "READY")

    def test_malformed_and_extreme_inputs_fail_without_nonfinite_outputs(self):
        for bad_tick in (0, -1, math.inf, math.nan, True, 1e-320):
            b = fixture()
            r = cf.evaluate("TEST", "M5", b, b[-1]["time"]+STEP, bad_tick, quote=quote(b))
            self.assertFalse(r["matrix"]["passed"])
            json.dumps(r, allow_nan=False)
        b = fixture()
        b[-1]["time"] = b[-2]["time"]
        self.assertEqual(run(b)["status"], "DATA_ERROR")
        self.assertEqual(run(fixture()[:39])["status"], "DATA_MISSING")


if __name__ == "__main__":
    unittest.main()
