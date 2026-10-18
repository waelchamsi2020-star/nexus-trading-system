"""Synthetic branch acceptance for the 32 previously unmapped models.

Seeds were selected to exercise READY, not to optimize a rule or demonstrate
profitability. All calculators, regime filters and plans run without mocks.
The composite research card remains advisory by design.
"""
import copy
import importlib.util
import json
import unittest
from pathlib import Path

import test_confluence as composite_fixture
import test_pivot_model as pivot_fixture

from nexus import strategies as st

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('entry_fixture_generator', ROOT/'tools/discover_entry_fixtures.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
CASES = json.loads((ROOT/'tests/fixtures/discovered-entry-seeds.json').read_text(encoding='utf-8'))['cases']
PIPELINE_MODELS = tuple(sorted(CASES)) + ('classic_pivot_reclaim', 'four_school_confluence')


def reflect(rows):
    return [dict(x, open=300-x['open'], close=300-x['close'],
                 high=300-x['low'], low=300-x['high']) for x in rows]


def scenario(sid, side):
    if sid == 'classic_pivot_reclaim':
        bars, context = pivot_fixture.fixture()
        if side == 'SELL':
            # Preserve the mathematical pivot reflection about 100.
            for row in bars+context['daily_bars']:
                row.update(open=200-row['open'], close=200-row['close'],
                           high=200-row['low'], low=200-row['high'])
        return bars, 'M1', context
    choices = CASES[sid]
    chosen = choices.get(side) or choices['SELL' if side == 'BUY' else 'BUY']
    bars = generator.scenario(chosen['seed'])
    if side not in choices:
        bars = reflect(bars)
    return bars, 'H1', {'as_of': bars[-1]['time']+3600, 'data_kind': 'synthetic', 'anchor_time': bars[-30]['time']}


# Vulture review: unittest/pytest discovers and executes this TestCase by module inspection.
class RemainingEntryPipeline(unittest.TestCase):
    def test_buy_sell_from_candles_through_real_calculators_and_regime(self):
        for sid in PIPELINE_MODELS:
            if sid == 'four_school_confluence':
                continue
            for side in ('BUY', 'SELL'):
                bars, tf, context = scenario(sid, side)
                original = copy.deepcopy((bars, context))
                with self.subTest(model=sid, side=side):
                    card = st.analyze_strategy(sid, 'FIXTURE', tf, bars, context['as_of'], context)
                    self.assertTrue(card['actionable'], card)
                    self.assertEqual(card['direction'], side)
                    stop, entry = card['stop']['price'], card['entry']['price']
                    self.assertTrue(stop < entry if side == 'BUY' else stop > entry)
                    self.assertTrue(all(t['price'] > entry if side == 'BUY' else t['price'] < entry for t in card['targets']))
                    self.assertEqual(card['version'], st.REGISTRY[sid]['contract']['rule_version'])
                    self.assertEqual((bars, context), original)
                    json.dumps(card, allow_nan=False)

    def test_unfinished_and_future_trigger_never_grant_entry(self):
        for sid in PIPELINE_MODELS:
            if sid == 'four_school_confluence':
                bars = composite_fixture.fixture()
                tf = 'M5'; context = {'as_of': bars[-1]['time']+300}
            else:
                bars, tf, context = scenario(sid, 'BUY')
            for rows, now in ((bars, context['as_of']-1),
                              (bars+[dict(bars[-1], time=context['as_of'])], context['as_of'])):
                with self.subTest(model=sid, now=now):
                    card = st.analyze_strategy(sid, 'FIXTURE', tf, rows, now, context)
                    self.assertEqual(card['status'], 'DATA_INVALID')
                    self.assertFalse(card['actionable'])

    def test_composite_advisory_card_has_no_execution_authority(self):
        bars = composite_fixture.fixture()
        now = bars[-1]['time']+300
        card = st.analyze_strategy('four_school_confluence', 'TEST', 'M5', bars, now,
                                   {'tick_size': .1, 'quote': composite_fixture.quote(bars)})
        self.assertEqual(card['status'], 'WAIT')
        self.assertFalse(card['actionable'])
        self.assertIsNone(card['entry'])
        self.assertIsNone(card['execution_plan'])
        self.assertEqual(card['evidence'][0]['kind'], 'decision_matrix')
        # The separate real-quote evaluator can accept the same geometric data.
        result = composite_fixture.run(bars)
        self.assertEqual(result['status'], 'READY')
        self.assertTrue(result['matrix']['passed'])
        self.assertEqual(result['candidate']['entry_reference'], 'ACTUAL_ASK')

    def test_every_registered_model_rejects_insufficient_history(self):
        bars = generator.scenario(0)[:10]
        for sid in st.REGISTRY:
            with self.subTest(model=sid):
                card = st.analyze_strategy(sid, 'FIXTURE', 'H1', bars, bars[-1]['time']+3600)
                self.assertEqual(card['status'], 'DATA_MISSING')
                self.assertFalse(card['actionable'])
