"""Causal rule fixtures for bounded local models, never profitability evidence."""
import copy
import json
import unittest

from nexus import specialists as sp
from nexus import strategies as st

NEW_MODELS = ("fractal_5_breakout", "obv_divergence_reclaim")


def sample(n=80):
    return [{"time": 1728000000+i*3600, "open": 100, "high": 101, "low": 99,
                 "close": 100, "tick_volume": 100, "real_volume": 0, "spread": 1} for i in range(n)]


def bar(b, i, o, h, l, c, volume=100):
    b[i].update(open=o, high=h, low=l, close=c, tick_volume=volume)


def fractal_fixture():
    b = sample()
    bar(b, -9, 100, 104, 99.7, 103)
    bar(b, -8, 103, 103.2, 99.7, 101)
    bar(b, -7, 101, 101.5, 99.7, 101)
    bar(b, -6, 101, 101.3, 99, 100.5)
    bar(b, -5, 100.5, 101, 97, 98.5)
    bar(b, -4, 98.5, 100, 98, 99.5)
    bar(b, -3, 99.5, 101, 98.5, 100.2)
    bar(b, -2, 100.2, 103.5, 99, 103)
    bar(b, -1, 103, 105, 102, 104.5)
    return b


def obv_fixture():
    b = sample()
    bar(b, -14, 100, 100.2, 98, 99)
    bar(b, -13, 99, 100.5, 98.5, 100, 400)
    bar(b, -12, 100, 101.5, 99.5, 101, 400)
    bar(b, -11, 101, 102.5, 100.5, 102, 400)
    bar(b, -10, 102, 104, 101.5, 103)
    bar(b, -9, 103, 103.5, 101, 102)
    bar(b, -8, 102, 102.2, 99.5, 101)
    bar(b, -7, 101, 101.5, 98, 99)
    bar(b, -6, 99, 99.2, 97, 98)
    bar(b, -5, 98, 100, 97.5, 99)
    bar(b, -4, 99, 101, 98, 100)
    bar(b, -3, 100, 102, 99, 101)
    bar(b, -2, 101, 103.5, 100, 103)
    bar(b, -1, 103, 105.5, 102.5, 105)
    return b


def mirror(b):
    opposite = copy.deepcopy(b)
    for x, original in zip(opposite, b):
        x.update(open=200-original["open"], close=200-original["close"],
                 high=200-original["low"], low=200-original["high"])
    return opposite


def details(result):
    return result["evidence"][0]["value"]


# Vulture review: unittest/pytest discovers and executes this TestCase by module inspection.
class ExtendedTheories(unittest.TestCase):
    def test_bullish_and_mirrored_bearish_triggers_have_structural_price_plans(self):
        for id, fixture in zip(NEW_MODELS, (fractal_fixture, obv_fixture)):
            for b, side in ((fixture(), "BUY"), (mirror(fixture()), "SELL")):
                with self.subTest(id=id, side=side):
                    result = st.REGISTRY[id]["analyzer"](b, {})
                    self.assertTrue(result["triggered"], result)
                    self.assertEqual(result["direction"], side)
                    self.assertEqual(result["invalidation"], 97 if side == "BUY" else 103)
                    card = st.analyze_strategy(id, "TEST", "H1", b, b[-1]["time"]+3600,
                                               {"data_kind": "synthetic"})
                    self.assertTrue(card["actionable"], card["conditions_missing"])
                    self.assertEqual(card["status"], "READY")
                    self.assertLess(card["stop"]["price"], card["entry"]["price"]) if side == "BUY" else self.assertGreater(card["stop"]["price"], card["entry"]["price"])
                    self.assertGreater(card["targets"][0]["price"], card["entry"]["price"]) if side == "BUY" else self.assertLess(card["targets"][0]["price"], card["entry"]["price"])
                    json.dumps(card, allow_nan=False)

    def test_fractal_references_are_confirmed_before_the_trigger(self):
        b = fractal_fixture()
        evidence = details(sp.fractal_5_breakout(b, {}))
        self.assertEqual(evidence["confirmed_high"]["price"], 104)
        self.assertEqual(evidence["confirmed_low"]["price"], 97)
        for key in ("confirmed_high", "confirmed_low"):
            pivot = evidence[key]
            self.assertLess(pivot["confirmation_bar_time"], b[-1]["time"])
            self.assertEqual(pivot["confirmation_bar_time"], b[pivot["index"]+2]["time"])
        changed = copy.deepcopy(b)
        changed[-1].update(high=1000, close=999)
        new = details(sp.fractal_5_breakout(changed, {}))
        self.assertEqual(evidence["confirmed_high"], new["confirmed_high"])
        self.assertEqual(evidence["confirmed_low"], new["confirmed_low"])

    def test_second_right_confirmation_bar_cannot_be_reused_as_breakout_trigger(self):
        b = sample()
        bar(b, 74, 100, 104, 99.5, 102)
        bar(b, 75, 102, 103, 99.5, 101)
        bar(b, 76, 101, 102, 99.5, 101.5)
        before = sp._prior_five_bar_pivots(b[:76])
        at_confirmation = sp._prior_five_bar_pivots(b[:77])
        after_confirmation = sp._prior_five_bar_pivots(b[:78])
        self.assertFalse(any(p["index"] == 74 for p in before))
        self.assertFalse(any(p["index"] == 74 for p in at_confirmation))
        self.assertEqual([p["index"] for p in after_confirmation], [74])

    def test_equal_fractal_extremes_and_dual_pivots_are_excluded(self):
        for b in (fractal_fixture(), mirror(fractal_fixture())):
            key = "high" if b[-9]["high"] == 104 else "low"
            b[-8][key] = b[-9][key]
            self.assertFalse(sp.fractal_5_breakout(b, {})["triggered"])
        b = fractal_fixture()
        b[-9]["low"] = 96
        self.assertFalse(any(p["index"] == len(b)-9 for p in sp._prior_five_bar_pivots(b)))
        self.assertFalse(sp.fractal_5_breakout(b, {})["triggered"])

    def test_fractal_intrabar_cross_already_crossed_close_and_two_edge_bar_abstain(self):
        b = fractal_fixture()
        b[-1]["close"] = 103.9
        self.assertFalse(sp.fractal_5_breakout(b, {})["triggered"])
        b = fractal_fixture()
        bar(b, -2, 100.2, 104.7, 99, 104.5)
        self.assertFalse(sp.fractal_5_breakout(b, {})["triggered"])
        b = fractal_fixture()
        b[-1]["low"] = 96
        result = sp.fractal_5_breakout(b, {})
        self.assertFalse(result["triggered"])
        self.assertTrue(details(result)["dual_boundary_cross"])
        self.assertEqual(result["direction"], "NEUTRAL")

    def test_obv_price_reclaim_requires_divergence_not_just_low_and_breakout(self):
        b = obv_fixture()
        for x in b[-13:-10]:
            x["tick_volume"] = 1
        result = sp.obv_divergence_reclaim(b, {})
        self.assertFalse(result["triggered"])
        self.assertFalse(details(result)["bullish_setup"]["divergence"])
        b = obv_fixture()
        b[-14]["low"] = 97
        self.assertFalse(sp.obv_divergence_reclaim(b, {})["triggered"])

    def test_obv_divergence_uses_prior_pivots_and_intervening_price_reclaim(self):
        b = obv_fixture()
        result = sp.obv_divergence_reclaim(b, {})
        evidence = details(result)
        setup = evidence["bullish_setup"]
        self.assertEqual(setup["first_pivot"]["price"], 98)
        self.assertEqual(setup["second_pivot"]["price"], 97)
        self.assertEqual(setup["second_obv"]-setup["first_obv"], 900)
        self.assertEqual(setup["reclaim_level"], 104)
        self.assertEqual(setup["confirmation_age"], 3)
        self.assertLess(setup["second_pivot"]["confirmation_bar_time"], b[-1]["time"])
        changed = copy.deepcopy(b)
        changed[-1].update(high=1000, close=999, tick_volume=999999)
        self.assertEqual(setup, details(sp.obv_divergence_reclaim(changed, {}))["bullish_setup"])

    def test_obv_unchanged_close_has_zero_contribution(self):
        b = obv_fixture()
        b[-18]["tick_volume"] = 999999
        self.assertEqual(details(sp.obv_divergence_reclaim(b, {}))["bullish_setup"],
                         details(sp.obv_divergence_reclaim(obv_fixture(), {}))["bullish_setup"])

    def test_obv_divergence_without_fresh_price_reclaim_abstains(self):
        b = obv_fixture()
        b[-1]["close"] = 104
        self.assertFalse(sp.obv_divergence_reclaim(b, {})["triggered"])
        b = obv_fixture()
        bar(b, -2, 101, 104.7, 100, 104.5)
        self.assertFalse(sp.obv_divergence_reclaim(b, {})["triggered"])

    def test_obv_broken_pivot_and_expired_divergence_abstain(self):
        b = obv_fixture()
        b[-1]["low"] = 96.9
        result = sp.obv_divergence_reclaim(b, {})
        self.assertFalse(result["triggered"])
        self.assertFalse(details(result)["bullish_setup"]["pivot_intact"])
        b = obv_fixture()
        extra = [dict(b[-2], time=b[-1]["time"]+i*3600) for i in range(6)]
        old_trigger = dict(b[-1], time=b[-1]["time"]+6*3600)
        expired = b[:-1]+extra+[old_trigger]
        result = sp.obv_divergence_reclaim(expired, {})
        self.assertEqual(details(result)["bullish_setup"]["confirmation_age"], 9)
        self.assertFalse(result["triggered"])

    def test_obv_missing_zero_negative_bool_and_nonfinite_volume_abstain(self):
        for index in (-61, -14, -6, -1):
            for value in (None, 0, -1, True, float("nan"), float("inf")):
                with self.subTest(index=index, value=value):
                    b = obv_fixture()
                    if value is None:
                        del b[index]["tick_volume"]
                    else:
                        b[index]["tick_volume"] = value
                    b[index]["real_volume"] = 1000
                    result = sp.obv_divergence_reclaim(b, {})
                    self.assertEqual(result["status"], "DATA_MISSING")
                    self.assertFalse(result["triggered"])
                    self.assertEqual(result["direction"], "NEUTRAL")
                    self.assertIn("not traded-volume OBV", " ".join(result["assumptions"]))

    def test_obv_cumulative_overflow_abstains(self):
        b = obv_fixture()
        for x in b[-13:-10]:
            x["tick_volume"] = 1e308
        result = sp.obv_divergence_reclaim(b, {})
        self.assertEqual(result["status"], "DATA_INVALID")
        self.assertFalse(result["triggered"])
        json.dumps(result, allow_nan=False)

    def test_data_older_than_fixed_window_cannot_change_either_model(self):
        for id, fixture in zip(NEW_MODELS, (fractal_fixture, obv_fixture)):
            b = fixture()
            expected = st.REGISTRY[id]["analyzer"](b, {})
            for x in b[:-61]:
                x.update(open=500, high=1000, low=1, close=900, tick_volume=0)
            self.assertEqual(st.REGISTRY[id]["analyzer"](b, {}), expected)

    def test_analysis_rejects_unfinished_future_and_short_histories(self):
        for id, fixture in zip(NEW_MODELS, (fractal_fixture, obv_fixture)):
            b = fixture()
            for data, now, status in ((b, b[-1]["time"]+3599, "DATA_INVALID"),
                                      (b+[dict(b[-1], time=b[-1]["time"]+3600)], b[-1]["time"]+3600, "DATA_INVALID"),
                                      (b[-60:], b[-1]["time"]+3600, "DATA_MISSING")):
                with self.subTest(id=id, status=status):
                    card = st.analyze_strategy(id, "TEST", "H1", data, now)
                    self.assertEqual(card["status"], status)
                    self.assertFalse(card["actionable"])

    def test_contracts_are_precise_bilingual_versioned_and_have_no_broker_authority(self):
        for id, group in zip(NEW_MODELS, ("structure", "volume")):
            contract = st.REGISTRY[id]["contract"]
            self.assertEqual(contract["rule_id"], id)
            self.assertEqual(contract["rule_version"], "1.0.0")
            self.assertEqual(contract["minimum_bars"], 61)
            self.assertEqual(contract["evidence_group"], group)
            self.assertEqual(contract["definition"]["rules_en"], sp.SPECS[id]["rules"])
            self.assertEqual(len(contract["definition"]["rules_ar"]), len(contract["definition"]["rules_en"]))
            self.assertIn("House", contract["definition"]["scope"])
            self.assertFalse(contract["school_complete"])
            self.assertFalse(contract["direct_broker_authority"])
            self.assertEqual(contract["missing_data_policy"], "abstain")
            json.dumps(contract, allow_nan=False)
        self.assertEqual(st.REGISTRY["obv_divergence_reclaim"]["data_requirements"],
                         ["completed_ohlc", "positive_tick_volume"])
        result = sp.obv_divergence_reclaim(obv_fixture(), {})
        self.assertEqual(details(result)["volume_source"], "tick_volume")
        self.assertEqual(details(result)["volume_units"], "tick_count")
        self.assertIn("not traded-volume OBV", " ".join(result["assumptions"]))
