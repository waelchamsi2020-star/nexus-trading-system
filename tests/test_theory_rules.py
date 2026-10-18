import copy
import unittest

from nexus import strategies as st


def equal_leg_bars():
    anchors = {0: 110., 45: 110., 52: 120., 60: 100., 66: 112.36, 74: 92.36,
               75: 93., 76: 93.3, 77: 93.4, 78: 93.5, 79: 94.5}
    b = []
    keys = sorted(anchors)
    for i in range(80):
        left = max(k for k in keys if k <= i)
        right = min(k for k in keys if k >= i)
        x = anchors[left] if left == right else anchors[left]+(anchors[right]-anchors[left])*(i-left)/(right-left)
        b.append({"time": 1600000000+i*3600, "open": x, "close": x, "high": x+.2, "low": x-.2, "tick_volume": 100})
    return b


# Vulture review: unittest/pytest discovers and executes this TestCase by module inspection.
class TheoryRules(unittest.TestCase):
    def test_equal_leg_long_and_short_from_real_causal_pivots(self):
        b = equal_leg_bars()
        for side in ("BUY", "SELL"):
            card = st.analyze_strategy("harmonic_abcd", "TEST", "H1", b, b[-1]["time"]+3600)
            self.assertTrue(card["actionable"], card)
            self.assertEqual(card["direction"], side)
            self.assertEqual(card["version"], "2.0.0")
            self.assertTrue(card["entry"]["price"] < card["targets"][0]["price"] if side == "BUY" else card["entry"]["price"] > card["targets"][0]["price"])
            for x in b:
                x.update(open=240-x["open"], close=240-x["close"], high=240-x["low"], low=240-x["high"])

    def test_no_entry_before_confirmation_or_after_invalidation(self):
        b = equal_leg_bars()
        for end in (75, 76, 77, 78, 79):
            prefix = b[:end]
            card = st.analyze_strategy("harmonic_abcd", "TEST", "H1", prefix, prefix[-1]["time"]+3600)
            self.assertFalse(card["actionable"])
        b[-1]["low"] = 90
        self.assertFalse(st.analyze_strategy("harmonic_abcd", "TEST", "H1", b, b[-1]["time"]+3600)["actionable"])

    def test_impulse_checks_each_alternative_without_execution_authority(self):
        b = equal_leg_bars()
        prices = [100, 110, 105, 122, 113, 126]
        pivots = [{"kind": "LOW" if i % 2 == 0 else "HIGH", "price": p, "index": 40+i*5,
                       "time": b[40+i*5]["time"], "confirmed_at": b[42+i*5]["time"]+3600} for i,p in enumerate(prices)]
        result = st.elliott_candidate(b, {"pivots": pivots})
        value = result["evidence"][0]["value"]
        self.assertEqual(value["valid_counts"], 1)
        self.assertFalse(result["triggered"])
        bad = copy.deepcopy(pivots); bad[4]["price"] = 109
        result = st.elliott_candidate(b, {"pivots": bad})
        candidate = result["evidence"][0]["value"]["candidates"][0]
        self.assertFalse(candidate["rules"]["wave4_no_overlap"])
        self.assertFalse(candidate["geometry_valid"])
        bad = copy.deepcopy(pivots); bad[2]["price"] = 99
        result = st.elliott_candidate(b, {"pivots": bad})
        self.assertFalse(result["evidence"][0]["value"]["candidates"][0]["rules"]["wave2_above_origin"])
