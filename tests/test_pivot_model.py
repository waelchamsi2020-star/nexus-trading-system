import copy
import unittest

from nexus import strategies as st
from nexus.specialists import classic_pivot_reclaim


def fixture():
    start = 1728000000
    b = [{"time": start+i*60, "open": 99.5, "close": 99.6, "high": 100, "low": 99, "tick_volume": 100} for i in range(80)]
    b[-1].update(open=99.6, close=100.8, high=101, low=99.5)
    daily = [{"time": start-86400, "open": 100, "high": 110, "low": 90, "close": 100, "tick_volume": 100}]
    return b, {"timeframe": "M1", "as_of": b[-1]["time"]+60, "daily_bars": daily}


# Vulture review: unittest/pytest discovers and executes this TestCase by module inspection.
class PivotModel(unittest.TestCase):
    def test_formula_reclaim_and_symmetric_plan(self):
        b, c = fixture()
        result = classic_pivot_reclaim(b, c)
        self.assertTrue(result["triggered"])
        self.assertEqual(result["direction"], "BUY")
        levels = result["evidence"][0]["value"]
        self.assertEqual((levels["pivot"], levels["resistance_1"], levels["support_1"]), (100, 110, 90))
        self.assertEqual((levels["resistance_2"], levels["support_2"]), (120, 80))
        self.assertEqual(result["targets"][0]["price"], 110)
        mirrored, opposite = copy.deepcopy(b), copy.deepcopy(c)
        for x in mirrored+opposite["daily_bars"]:
            x.update(open=200-x["open"], close=200-x["close"], high=200-x["low"], low=200-x["high"])
        result = classic_pivot_reclaim(mirrored, opposite)
        self.assertEqual(result["direction"], "SELL")
        self.assertTrue(result["triggered"])
        self.assertGreater(result["invalidation"], mirrored[-1]["close"])
        card = st.analyze_strategy("classic_pivot_reclaim", "TEST", "M1", b, c["as_of"], c)
        self.assertTrue(card["actionable"], card["conditions_missing"])

    def test_missing_future_and_expired_daily_reference_abstain(self):
        b, c = fixture()
        self.assertEqual(classic_pivot_reclaim(b, {**c, "daily_bars": []})["status"], "DATA_MISSING")
        future = copy.deepcopy(c["daily_bars"][0]); future["time"] += 2*86400
        self.assertEqual(classic_pivot_reclaim(b, {**c, "daily_bars": [future]})["status"], "DATA_MISSING")
        self.assertEqual(classic_pivot_reclaim(b, {**c, "daily_bars": c["daily_bars"]+[future]}), classic_pivot_reclaim(b, c))
        old = copy.deepcopy(c["daily_bars"]); old[0]["time"] -= 5*86400
        self.assertFalse(classic_pivot_reclaim(b, {**c, "daily_bars": old})["triggered"])

    def test_level_touch_and_unconfirmed_clock_do_not_trigger(self):
        b, c = fixture()
        b[-1]["close"] = 100
        self.assertFalse(classic_pivot_reclaim(b, c)["triggered"])
        b, c = fixture()
        c["daily_bars"][0]["time"] = b[-2]["time"]-86399
        self.assertEqual(classic_pivot_reclaim(b, c)["status"], "DATA_MISSING")

    def test_extreme_or_negative_projected_levels_abstain_without_invalid_json(self):
        import json
        for high,low,close in ((1.79e308,1,1.79e308),(110,1,2)):
            b,c=fixture();c['daily_bars'][0].update(open=close,high=high,low=low,close=close)
            result=classic_pivot_reclaim(b,c)
            self.assertFalse(result['triggered'])
            self.assertIn('finite and positive',' '.join(result['missing']))
            json.dumps(result,allow_nan=False)
        b, c = fixture()
        b[-1]["time"] = 1728000000+86400
        self.assertFalse(classic_pivot_reclaim(b, c)["triggered"])
        self.assertFalse(classic_pivot_reclaim(b, {**c, "timeframe": "D1"})["triggered"])

    def test_bad_reference_and_fresh_cross_required(self):
        b, c = fixture()
        b[-2].update(close=100.2, high=100.5)
        self.assertFalse(classic_pivot_reclaim(b, c)["triggered"])
        b, c = fixture(); c["daily_bars"][0]["high"] = float("nan")
        self.assertEqual(classic_pivot_reclaim(b, c)["status"], "DATA_MISSING")

