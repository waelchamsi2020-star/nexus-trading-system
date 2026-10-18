"""Adversarial and deterministic fixtures, never performance evidence."""
import copy
import json
import unittest
from unittest.mock import patch

from nexus import specialists as sp
from nexus import strategies as st

LEGACY_FIXTURES = ("fvg_first_return", "base_first_return", "donchian_20", "failed_range_break",
                   "pin_rejection", "inside_bar_break", "band_reentry", "atr_channel_break",
                   "momentum_acceleration", "utc_opening_range", "regression_reentry", "tick_activity_rejection")


def sample(n=80, step=3600):
    return [{"time": 1728000000+i*step, "open": 100, "close": 100+(.2 if i % 2 else -.2),
                 "high": 100.5, "low": 99.5, "tick_volume": 100, "real_volume": 0, "spread": 1} for i in range(n)]


def bar(b, i, o, h, l, c):
    b[i].update(open=o, high=h, low=l, close=c)


def fixture(id):
    b = sample()
    if id == "fvg_first_return":
        bar(b, -4, 100, 103.2, 99.8, 103)
        bar(b, -3, 102.5, 103, 102, 102.8)
        bar(b, -2, 102.8, 103, 102.5, 102.7)
        bar(b, -1, 101.2, 102.6, 101, 102.4)
    elif id == "base_first_return":
        bar(b, -4, 100, 100.2, 99.8, 100.1)
        bar(b, -3, 100.1, 102.6, 100, 102.5)
        bar(b, -2, 102.5, 102.8, 102, 102.4)
        bar(b, -1, 100.2, 101.2, 100.1, 101)
    elif id == "donchian_20":
        bar(b, -1, 100, 103.2, 99.8, 103)
    elif id == "failed_range_break":
        bar(b, -1, 99.8, 100.3, 99, 100.2)
    elif id == "pin_rejection":
        bar(b, -1, 100.15, 100.3, 99, 100.2)
    elif id == "tick_activity_rejection":
        bar(b, -1, 99.8, 100.3, 99, 100.2)
        b[-1]["tick_volume"]=200
    elif id == "inside_bar_break":
        bar(b, -3, 100, 102, 98, 100)
        bar(b, -2, 100, 101, 99, 100.8)
        bar(b, -1, 100.8, 103.2, 100.7, 103)
    elif id in ("band_reentry", "regression_reentry"):
        bar(b, -2, 99.2, 99.3, 98.8, 99)
        bar(b, -1, 99, 100, 98.9, 99.8)
    elif id == "atr_channel_break":
        for i in range(len(b)-1):
            x = 100+i*.1
            bar(b, i, x-.1, x+.6, x-.6, x)
        bar(b, -1, 108, 111.2, 107.9, 111)
    elif id == "momentum_acceleration":
        bar(b, -2, 100, 100.5, 99.5, 100.3)
        bar(b, -1, 100.3, 103.2, 100.2, 103)
    elif id == "utc_opening_range":
        b = sample(80, 60)
        bar(b, -1, 100.2, 102.2, 100, 102)
    else:
        raise AssertionError(id)
    return b


# Vulture review: unittest/pytest discovers and executes this TestCase by module inspection.
class Specialists(unittest.TestCase):
    def test_tick_proxy_requires_real_input_counts_and_activity_not_just_wick(self):
        b=fixture("tick_activity_rejection")
        b[-1]["tick_volume"]=100
        self.assertFalse(sp.tick_activity_rejection(b,{})["triggered"])
        b=fixture("tick_activity_rejection");b[-10]["tick_volume"]=0
        result=sp.tick_activity_rejection(b,{})
        self.assertEqual(result["status"],"DATA_MISSING")
        self.assertFalse(result["triggered"])
        b=fixture("tick_activity_rejection")
        result=sp.tick_activity_rejection(b,{})
        self.assertIn("not real order flow", " ".join(result["assumptions"]))
        self.assertIn("approximation",st.REGISTRY["order_flow"]["contract"]["definition"]["name_en"])

    def test_common_price_plan_for_each_specialist_after_regime_acceptance(self):
        # Regime selection has separate tests; isolate the real analyzer and
        # common entry/stop/target construction here, not a fabricated card.
        for id in LEGACY_FIXTURES:
            spec = sp.SPECS[id]
            with self.subTest(id=id):
                b = fixture(id)
                tf = "M1" if id == "utc_opening_range" else "H1"
                with patch.object(sp, "regime", return_value={"name": spec["allowed_regimes"][0]}):
                    card = st.analyze_strategy(id, "TEST", tf, b, b[-1]["time"]+st.PERIODS[tf])
                self.assertTrue(card["actionable"], card["conditions_missing"])
                self.assertLess(card["stop"]["price"], card["entry"]["price"])
                self.assertGreater(card["targets"][0]["price"], card["entry"]["price"])
                self.assertTrue(card["execution_plan"]["stop_may_only_tighten"])

    def test_each_specialist_has_real_symmetric_trigger_and_bracketed_plan(self):
        for id in LEGACY_FIXTURES:
            with self.subTest(id=id):
                b = fixture(id)
                tf = "M1" if id == "utc_opening_range" else "H1"
                c = {"timeframe": tf}
                result = st.REGISTRY[id]["analyzer"](b, c)
                self.assertTrue(result["triggered"], result)
                self.assertEqual(result["direction"], "BUY")
                self.assertLess(result["invalidation"], b[-1]["close"])
                mirrored = copy.deepcopy(b)
                for x, original in zip(mirrored, b):
                    x.update(open=200-original["open"], close=200-original["close"],
                             high=200-original["low"], low=200-original["high"])
                opposite = st.REGISTRY[id]["analyzer"](mirrored, c)
                self.assertTrue(opposite["triggered"], opposite)
                self.assertEqual(opposite["direction"], "SELL")
                self.assertGreater(opposite["invalidation"], mirrored[-1]["close"])
                json.dumps(result, allow_nan=False)

    def test_first_return_rejects_consumed_zone_and_far_edge_breach(self):
        for id in ("fvg_first_return", "base_first_return"):
            b = fixture(id)
            b[-2]["low"] = 100.1
            self.assertFalse(st.REGISTRY[id]["analyzer"](b, {})["triggered"])
            b = fixture(id)
            b[-1]["low"] = 90
            self.assertFalse(st.REGISTRY[id]["analyzer"](b, {})["triggered"])

    def test_zone_expiry_and_formation_bar_cannot_trigger(self):
        for id in ("fvg_first_return", "base_first_return"):
            b = fixture(id)
            self.assertFalse(st.REGISTRY[id]["analyzer"](b[:-2], {})["triggered"])
            held = dict(b[-2])
            expanded = b[:-1]+[dict(held) for _ in range(21)]+b[-1:]
            for i, x in enumerate(expanded):
                x["time"] = b[0]["time"]+i*3600
            self.assertFalse(st.REGISTRY[id]["analyzer"](expanded, {})["triggered"])

    def test_opening_range_requires_complete_anchor_and_intraday_timeframe(self):
        b = fixture("utc_opening_range")
        self.assertFalse(sp.utc_opening_range(b[1:], {"timeframe": "M1"})["triggered"])
        self.assertFalse(sp.utc_opening_range(b, {"timeframe": "H1"})["triggered"])

    def test_prior_regime_cannot_be_changed_by_trigger_bar(self):
        b = sample()
        before = sp.regime(b)
        bar(b, -1, 100, 1000, 1, 999)
        self.assertEqual(sp.regime(b), before)
        self.assertEqual(before["name"], "RANGE")

    def test_wrong_regime_blocks_new_trend_signal(self):
        b = fixture("donchian_20")
        c = st.analyze_strategy("donchian_20", "TEST", "H1", b, b[-1]["time"]+3600)
        self.assertFalse(c["actionable"])
        self.assertEqual(c["market_regime"]["name"], "RANGE")
        self.assertIn("market regime", " ".join(c["conditions_missing"]))

    def test_invalid_or_unfinished_data_never_actionable_for_any_new_agent(self):
        for id in LEGACY_FIXTURES:
            b = fixture(id)
            tf = "M1" if id == "utc_opening_range" else "H1"
            bad = copy.deepcopy(b)
            bad[-1]["close"] = float("nan")
            for data, now in ((bad, b[-1]["time"]+st.PERIODS[tf]), (b, b[-1]["time"])):
                card = st.analyze_strategy(id, "TEST", tf, data, now)
                self.assertFalse(card["actionable"], id)

    def test_all_agents_have_serializable_contract_and_no_broker_authority(self):
        for meta in st.registry_manifest():
            c = meta["contract"]
            self.assertEqual(c["rule_id"], meta["id"])
            self.assertEqual(c["coverage"], meta["coverage"])
            self.assertFalse(c["direct_broker_authority"])
            self.assertFalse(c["school_complete"])
            json.dumps(c, allow_nan=False)

    def test_flat_history_does_not_generate_infinite_momentum(self):
        b = sample()
        for i in range(len(b)-1):
            bar(b, i, 100, 100, 100, 100)
        self.assertFalse(sp.momentum_acceleration(b, {})["triggered"])
