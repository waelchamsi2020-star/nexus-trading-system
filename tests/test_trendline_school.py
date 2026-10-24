import copy
import unittest

from nexus.schools.trendline import _boundary, analyze


def fixture():
    step = 3600
    rows = []
    for index in range(80):
        close = 100.0
        rows.append({"time": 1_700_000_000 + index * step, "open": close,
                     "high": 101.0, "low": 99.0, "close": close,
                     "tick_volume": 100})
    for index, high in ((20, 120.0), (35, 115.0), (50, 110.0)):
        rows[index]["high"] = high
        rows[index]["close"] = high - 1.0
        rows[index]["open"] = high - 2.0
    rows[-2]["close"] = rows[-2]["open"] = 100.0
    rows[-1].update(open=100.5, high=103.0, low=99.5, close=102.0)
    return rows, rows[-1]["time"] + step


def mirror(rows):
    return [{**row, "open": 200-row["open"], "close": 200-row["close"],
             "high": 200-row["low"], "low": 200-row["high"]} for row in rows]


class TrendlineSchool(unittest.TestCase):
    def test_three_confirmed_descending_highs_produce_research_only_buy(self):
        rows, now = fixture()
        before = copy.deepcopy(rows)
        result = analyze(rows, "H1", now)
        self.assertEqual("BUY", result["direction"])
        self.assertTrue(result["triggered"])
        self.assertEqual("OBSERVATION", result["status"])
        self.assertFalse(result["actionable"])
        self.assertFalse(result["execution_authority"])
        self.assertEqual(3, result["boundaries"][0]["touch_count"])
        self.assertTrue(all(value <= result["inputs"]["data_time"]
                            for value in result["boundaries"][0]["pivot_times"]))
        self.assertEqual(rows, before)

    def test_mirrored_ascending_support_break_produces_research_only_sell(self):
        rows, now = fixture()
        result = analyze(mirror(rows), "H1", now)
        self.assertEqual("SELL", result["direction"])
        self.assertFalse(result["actionable"])
        self.assertFalse(result["execution_authority"])

    def test_future_or_unclosed_bar_is_rejected(self):
        rows, now = fixture()
        future = rows + [{**rows[-1], "time": now}]
        result = analyze(future, "H1", now)
        self.assertEqual("DATA_INVALID", result["status"])
        self.assertFalse(result["triggered"])

    def test_missing_three_point_structure_abstains(self):
        rows, now = fixture()
        rows[35]["high"] = 101.0
        rows[35]["close"] = rows[35]["open"] = 100.0
        result = analyze(rows, "H1", now)
        self.assertEqual("INSUFFICIENT_STRUCTURE", result["status"])
        self.assertEqual("NEUTRAL", result["direction"])

    def test_previously_broken_line_is_not_reused_as_a_new_breakout(self):
        rows, _now = fixture()
        pivots = [{"kind": "HIGH", "index": index, "price": price,
                   "time": rows[index]["time"], "confirmed_at": rows[index + 2]["time"]}
                  for index, price in ((20, 120.0), (35, 115.0), (50, 110.0))]
        self.assertIsNotNone(_boundary(rows, pivots, "HIGH", 5.0))
        rows[60]["close"] = 110.0
        rows[60]["high"] = 110.0
        self.assertIsNone(_boundary(rows, pivots, "HIGH", 5.0))

    def test_standalone_chart_snapshot_keeps_school_out_of_execution_cards(self):
        from nexus.engine import Engine
        rows, now = fixture()
        chart = Engine._chart_snapshot("TEST", "H1", rows, [], now)
        self.assertEqual([], chart["cards"])
        self.assertEqual("trendline_school", chart["school_analyses"][0]["school_id"])
        self.assertFalse(chart["school_analyses"][0]["execution_authority"])


if __name__ == "__main__":
    unittest.main()
