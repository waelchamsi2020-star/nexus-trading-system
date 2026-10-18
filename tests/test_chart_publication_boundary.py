"""Reject malformed/future chart rows before drawing, caching or observation."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nexus.engine import Engine
from nexus.strategies import DataError

ROOT = Path(__file__).resolve().parents[1]


# Vulture review: unittest/pytest discovers and executes this TestCase by module inspection.
class ChartPublicationBoundary(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.engine = Engine(ROOT, Path(self.temp.name))
        self.engine._connect(True)
        self.engine.scanner.step(999)
        self.addCleanup(self.close)

    def close(self):
        self.engine.stop_worker()
        if self.engine.store:
            self.engine.store.close()
        self.engine.cache.db.close()
        self.engine.news.db.close()

    def test_future_and_invalid_chart_never_replace_last_valid_snapshot(self):
        request = {'action':'chart','symbol':'GOLD#','timeframe':'M1'}
        self.engine._action(request)
        previous = copy.deepcopy(self.engine.chart)
        for kind in ('future', 'nan', 'boolean'):
            rows = copy.deepcopy(previous['bars'])
            if kind == 'future':
                rows.append(dict(rows[-1], time=self.engine.clock()))
            elif kind == 'nan':
                rows[-1]['close'] = float('nan')
            else:
                rows[-1]['tick_volume'] = True
            with self.subTest(kind=kind), patch.object(self.engine.broker, 'bars', return_value=rows):
                with self.assertRaises(DataError):
                    self.engine._action(request)
                self.assertEqual(self.engine.chart, previous)

    def test_short_completed_chart_exposes_missing_models_without_actionability(self):
        rows = self.engine.broker.bars('GOLD#','M1',10)
        with patch.object(self.engine.broker, 'bars', return_value=rows):
            self.engine._action({'action':'chart','symbol':'GOLD#','timeframe':'M1'})
        self.assertEqual(len(self.engine.chart['bars']),10)
        self.assertEqual(len(self.engine.chart['cards']),58)
        self.assertTrue(all(c['status']=='DATA_MISSING' and not c['actionable'] for c in self.engine.chart['cards']))
