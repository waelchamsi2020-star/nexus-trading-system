"""Preserve exact ATR arithmetic on gaps, short books and trailing prefixes."""
import itertools
import random
import statistics
import unittest

from nexus.strategies import atr


class ATREquivalenceTests(unittest.TestCase):
    def test_matches_previous_full_history_definition(self):
        rng=random.Random(20261016);rows=[]
        for _ in range(1600):
            close=rng.uniform(1,150);low=close-rng.random();high=close+rng.random()
            rows.append({'close':close,'high':high,'low':low})
        for count in (0,1,2,13,14,15,60,300,1443,1600):
            for period in (1,2,14,40,2000,0,-1,-2):
                with self.subTest(count=count,period=period):
                    book=rows[:count]
                    if len(book)<2:
                        self.assertEqual(atr(book,period),0.0);continue
                    tr=[max(b['high']-b['low'],abs(b['high']-a['close']),abs(b['low']-a['close']))
                        for a,b in itertools.pairwise(book)][-period:]
                    if not tr:
                        with self.assertRaises(statistics.StatisticsError):atr(book,period)
                    else:self.assertEqual(atr(book,period),statistics.fmean(tr))
