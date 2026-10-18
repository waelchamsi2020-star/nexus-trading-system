"""Shared boundary acceptance across all registered bounded hypotheses."""
import copy
import unittest

from test_registry_acceptance import REGISTRY_MODELS, scenario

from nexus import strategies as st


# Vulture review: unittest/pytest discovers and executes this TestCase by module inspection.
class RegistryBoundaries(unittest.TestCase):
    def test_each_declared_minimum_rejects_one_less_completed_bar(self):
        for sid in REGISTRY_MODELS:
            rows, tf, context = scenario(sid, 'BUY')
            count = st.REGISTRY[sid]['contract']['minimum_bars'] - 1
            with self.subTest(model=sid, available=count):
                card = st.analyze_strategy(sid, 'FIXTURE', tf, rows[-count:], context['as_of'], context)
                self.assertEqual('DATA_MISSING', card['status'], card)
                self.assertFalse(card['actionable'])

    def test_flat_zero_range_cannot_create_an_executable_price_plan(self):
        for sid in REGISTRY_MODELS:
            rows, tf, context = scenario(sid, 'BUY')
            flat = [dict(x, open=100., high=100., low=100., close=100.) for x in rows]
            with self.subTest(model=sid):
                card = st.analyze_strategy(sid, 'FIXTURE', tf, flat, context['as_of'], context)
                self.assertFalse(card['actionable'], card)
                self.assertNotEqual('READY', card['status'], card)

    def test_malformed_volume_and_spread_refused_before_model_evaluation(self):
        for sid in REGISTRY_MODELS:
            rows, tf, context = scenario(sid, 'BUY')
            for key, value in (('tick_volume', -1), ('real_volume', float('nan')), ('spread', True)):
                bad = copy.deepcopy(rows)
                bad[-1][key] = value
                with self.subTest(model=sid, field=key):
                    card = st.analyze_strategy(sid, 'FIXTURE', tf, bad, context['as_of'], context)
                    self.assertEqual('DATA_INVALID', card['status'], card)
                    self.assertFalse(card['actionable'])
