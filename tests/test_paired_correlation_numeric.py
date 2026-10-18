import itertools
import math
import statistics
import unittest

from nexus import local_models as lm
from nexus import strategies as st


def pairs(xs, ys):
    return [({'close': x}, {'close': y}) for x, y in zip(xs, ys)]


# Vulture review: unittest/pytest discovers and executes this TestCase by module inspection.
class PairedCorrelationNumeric(unittest.TestCase):
    def test_extreme_positive_prices_do_not_overflow_or_underflow_division(self):
        xs = [1e-300 if i % 2 == 0 else 1e300 for i in range(42)]
        for ys, expected in ((xs, 1), (list(reversed(xs)), -1)):
            self.assertAlmostEqual(st.paired_log_correlation(pairs(xs, ys)), expected)
            self.assertAlmostEqual(lm.correlation(pairs(xs, ys)), expected)

    def test_matches_independent_pearson_and_ignores_trigger_return(self):
        xs = [math.exp(4+i*.001+math.sin(i)*.01) for i in range(42)]
        ys = [math.exp(3+i*.002+math.cos(i)*.007) for i in range(42)]
        rx = [math.log(b/a) for a, b in itertools.pairwise(xs[:41])]
        ry = [math.log(b/a) for a, b in itertools.pairwise(ys[:41])]
        self.assertEqual((len(rx), len(ry)), (40, 40))
        expected = statistics.correlation(rx, ry)
        self.assertAlmostEqual(st.paired_log_correlation(pairs(xs, ys)), expected, places=11)
        xs[-1], ys[-1] = 1e300, 1e-300
        self.assertAlmostEqual(st.paired_log_correlation(pairs(xs, ys)), expected, places=11)

    def test_constant_series_provides_no_correlation_confirmation(self):
        self.assertEqual(st.paired_log_correlation(pairs([100]*42, [200]*42)), 0)

    def test_uniform_price_scaling_preserves_correlation(self):
        xs = [100+i+math.sin(i) for i in range(42)]
        ys = [200+i+math.cos(i) for i in range(42)]
        expected = st.paired_log_correlation(pairs(xs, ys))
        scaled = st.paired_log_correlation(pairs([x*1e200 for x in xs], [y*1e-200 for y in ys]))
        self.assertAlmostEqual(scaled, expected, places=9)
