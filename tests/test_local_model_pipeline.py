"""Candle-to-plan acceptance without injected pivots or mocked calculators.

These fixtures exercise bounded hypotheses, not entire schools.
Wave/grid fixtures generate their pivots from candles instead of injecting them.
"""
import copy
import itertools
import unittest

import test_local_models as fixtures

from nexus import strategies as st

PIPELINE_MODELS = (
    'interasset_confirmation', 'smt_proxy', 'wyckoff_spring',
    'smc_ict_proxy', 'supply_demand_proxy', 'order_flow', 'seasonality',
    'elliott_candidate', 'gann',
)


def scenario(sid):
    if sid not in ('elliott_candidate', 'gann'):
        return fixtures.data(sid)
    points = ([(0, 105), (45, 105), (50, 100), (60, 110), (70, 104), (78, 109.5), (79, 111)]
              if sid == 'elliott_candidate' else [(0, 103), (60, 103), (70, 99), (78, 100), (79, 105)])
    bars = []
    for i in range(80):
        a, z = next((a, z) for a, z in itertools.pairwise(points) if a[0] <= i <= z[0])
        value = a[1] + (z[1]-a[1]) * (i-a[0]) / (z[0]-a[0])
        bars.append({'time': 1700000000+i*3600, 'open': value, 'close': value,
                         'high': value+.05, 'low': value-.05, 'tick_volume': 100})
    return bars, {'symbol': 'PRIMARY', 'timeframe': 'H1', 'as_of': bars[-1]['time']+3600, 'pivots': []}


# Vulture review: unittest/pytest discovers and executes this TestCase by module inspection.
class LocalModelPipeline(unittest.TestCase):
    def test_buy_sell_candles_to_shared_plan_without_injected_pivots(self):
        for sid in PIPELINE_MODELS:
            bars, context = scenario(sid)
            for side in ('BUY', 'SELL'):
                with self.subTest(model=sid, side=side):
                    before = copy.deepcopy((bars, context))
                    card = st.analyze_strategy(sid, 'PRIMARY', 'H1', bars, context['as_of'], context)
                    self.assertTrue(card['actionable'], card)
                    self.assertEqual(card['direction'], side)
                    stop, entry, target = card['stop']['price'], card['entry']['price'], card['targets'][0]['price']
                    self.assertTrue(stop < entry < target if side == 'BUY' else target < entry < stop)
                    self.assertEqual((bars, context), before, 'analysis must not mutate its inputs')
                fixtures.mirror(bars, context)

    def test_unclosed_trigger_cannot_be_actionable(self):
        for sid in PIPELINE_MODELS:
            bars, context = scenario(sid)
            with self.subTest(model=sid):
                card = st.analyze_strategy(sid, 'PRIMARY', 'H1', bars, bars[-1]['time'], context)
                self.assertFalse(card['actionable'])

    def test_required_external_chart_context_cannot_be_invented(self):
        for sid, fields in (
            ('interasset_confirmation', ('partner_bars', 'partner_symbol')),
            ('smt_proxy', ('partner_bars', 'partner_symbol')),
            ('seasonality', ('daily_bars',)),
        ):
            bars, context = fixtures.data(sid)
            for field in fields:
                context.pop(field, None)
            with self.subTest(model=sid):
                card = st.analyze_strategy(sid, 'PRIMARY', 'H1', bars, context['as_of'], context)
                self.assertFalse(card['actionable'])

    def test_tick_activity_is_required_for_activity_flow(self):
        bars, context = fixtures.data('order_flow')
        for row in bars:
            row['tick_volume'] = 0
        card = st.analyze_strategy('order_flow', 'PRIMARY', 'H1', bars, context['as_of'], context)
        self.assertFalse(card['actionable'])

    def test_wave_grid_need_fresh_cross_and_intact_anchor(self):
        for sid in ('elliott_candidate', 'gann'):
            for side in ('BUY', 'SELL'):
                bars, context = scenario(sid)
                if side == 'SELL':
                    fixtures.mirror(bars, context)
                with self.subTest(model=sid, side=side):
                    prior = bars[:-1]
                    self.assertFalse(st.analyze_strategy(sid, 'PRIMARY', 'H1', prior,
                                                         prior[-1]['time']+3600)['actionable'])
                    broken = copy.deepcopy(bars)
                    broken[-1]['low' if side == 'BUY' else 'high'] = 90 if side == 'BUY' else 150
                    self.assertFalse(st.analyze_strategy(sid, 'PRIMARY', 'H1', broken,
                                                         context['as_of'])['actionable'])
