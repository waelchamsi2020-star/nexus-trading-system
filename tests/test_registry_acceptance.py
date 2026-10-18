"""Every registered bounded model has a concrete acceptance contract.

57 executable chart models receive real-calculator BUY/SELL branch fixtures.
The 58th is an advisory composite; actual quote evaluation stays separate.
Synthetic branch coverage is not whole-school or profitability coverage.
"""
import copy
import json
import unittest

import test_confluence as composite
import test_extended_theories as theories
import test_harmonic_end_to_end as harmonic
import test_local_model_pipeline as local
import test_local_models as local_fixtures
import test_remaining_entry_pipeline as remaining
import test_specialists as specialist

from nexus import strategies as st

REGISTRY_MODELS = tuple(sorted(st.REGISTRY))
ADVISORY_MODEL = 'four_school_confluence'


def scenario(sid, side):
    if sid == ADVISORY_MODEL:
        rows = composite.fixture()
        if side == 'SELL':
            rows = [dict(x, open=200-x['open'], close=200-x['close'],
                         high=200-x['low'], low=200-x['high']) for x in rows]
        return rows, 'M5', {'as_of': rows[-1]['time']+300}
    if sid in remaining.PIPELINE_MODELS:
        return remaining.scenario(sid, side)
    if sid in local.PIPELINE_MODELS:
        rows, context = local.scenario(sid)
        if side == 'SELL':
            local_fixtures.mirror(rows, context)
        return rows, 'H1', context
    if sid in ('harmonic_gartley', 'harmonic_bat', 'harmonic_butterfly'):
        rows = harmonic.scenario(sid.removeprefix('harmonic_'), side)
        return rows, 'H1', {'as_of': rows[-1]['time']+3600}
    if sid in theories.NEW_MODELS:
        rows = (theories.fractal_fixture if sid == 'fractal_5_breakout' else theories.obv_fixture)()
        if side == 'SELL':
            rows = theories.mirror(rows)
        return rows, 'H1', {'as_of': rows[-1]['time']+3600}
    if sid in specialist.LEGACY_FIXTURES:
        tf = 'M1' if sid == 'utc_opening_range' else 'H1'
        if sid in ('donchian_20', 'momentum_acceleration'):
            rows = remaining.generator.scenario(20 if side == 'BUY' else 8)
        else:
            rows = specialist.fixture(sid)
            if side == 'SELL':
                rows = remaining.reflect(rows)
        return rows, tf, {'as_of': rows[-1]['time']+(60 if tf == 'M1' else 3600)}
    raise AssertionError('No explicit entry fixture: '+sid)


# Vulture review: unittest/pytest discovers and executes this TestCase by module inspection.
class RegistryAcceptance(unittest.TestCase):
    def test_exact_registry_has_no_unmapped_or_placeholder_contract(self):
        self.assertEqual(len(REGISTRY_MODELS), 58)
        for sid in REGISTRY_MODELS:
            meta = st.REGISTRY[sid]
            with self.subTest(model=sid):
                self.assertEqual(meta['coverage'], 'IMPLEMENTED')
                self.assertEqual(meta['version'], meta['contract']['rule_version'])
                self.assertFalse(meta['contract']['direct_broker_authority'])
                self.assertFalse(meta['contract']['school_complete'])
                for side in ('BUY', 'SELL'):
                    scenario(sid, side)

    def test_executable_models_both_directions_with_real_candle_pipeline(self):
        for sid in REGISTRY_MODELS:
            if sid == ADVISORY_MODEL:
                continue
            for side in ('BUY', 'SELL'):
                rows, tf, context = scenario(sid, side)
                before = copy.deepcopy((rows, context))
                with self.subTest(model=sid, side=side):
                    card = st.analyze_strategy(sid, 'FIXTURE', tf, rows, context['as_of'], context)
                    self.assertTrue(card['actionable'], card)
                    self.assertEqual(card['direction'], side)
                    entry, stop = card['entry']['price'], card['stop']['price']
                    self.assertTrue(stop < entry if side == 'BUY' else stop > entry)
                    self.assertTrue(all(t['price'] > entry if side == 'BUY' else t['price'] < entry for t in card['targets']))
                    self.assertEqual(card['invalidation']['evaluation'], 'completed_bar_close')
                    self.assertTrue(card['execution_plan']['stop_may_only_tighten'])
                    self.assertEqual((rows, context), before)
                    json.dumps(card, allow_nan=False)

    def test_all_models_refuse_unclosed_future_stale_and_short_history(self):
        for sid in REGISTRY_MODELS:
            rows, tf, context = scenario(sid, 'BUY')
            step = 60 if tf == 'M1' else 300 if tf == 'M5' else 3600
            cases = ((rows, context['as_of']-1, 'DATA_INVALID'),
                     (rows+[dict(rows[-1], time=context['as_of'])], context['as_of'], 'DATA_INVALID'),
                     (rows, context['as_of']+step, 'STALE'),
                     (rows[:10], rows[9]['time']+step, 'DATA_MISSING'))
            for sample, now, expected in cases:
                with self.subTest(model=sid, status=expected):
                    card = st.analyze_strategy(sid, 'FIXTURE', tf, sample, now, context)
                    self.assertEqual(card['status'], expected)
                    self.assertFalse(card['actionable'])
                    self.assertIsNone(card['execution_plan'])

    def test_all_models_refuse_malformed_price_and_reversed_time(self):
        for sid in REGISTRY_MODELS:
            rows, tf, context = scenario(sid, 'BUY')
            broken = copy.deepcopy(rows); broken[-1]['close'] = float('nan')
            for sample in (broken, list(reversed(rows))):
                with self.subTest(model=sid):
                    card = st.analyze_strategy(sid, 'FIXTURE', tf, sample, context['as_of'], context)
                    self.assertEqual(card['status'], 'DATA_INVALID')
                    self.assertFalse(card['actionable'])
                    json.dumps(card, allow_nan=False)

    def test_composite_advisory_and_quote_routes_are_distinct_both_directions(self):
        for side in ('BUY', 'SELL'):
            rows, tf, context = scenario(ADVISORY_MODEL, side)
            card = st.analyze_strategy(ADVISORY_MODEL, 'TEST', tf, rows, context['as_of'])
            self.assertEqual(card['status'], 'WAIT')
            self.assertFalse(card['actionable'])
            self.assertIsNone(card['execution_plan'])
            quote = ({'bid': 103.9, 'ask': 104., 'time': context['as_of']} if side == 'BUY' else
                     {'bid': 96., 'ask': 96.1, 'time': context['as_of']})
            result = composite.run(rows, quote=quote)
            self.assertEqual(result['status'], 'READY')
            self.assertEqual(result['candidate']['side'], 'LONG' if side == 'BUY' else 'SHORT')


class ModelAcceptanceById(unittest.TestCase):
    """One separately reported test per model; no aggregate-only coverage."""


def model_test(sid):
    def run(self):
        for side in ('BUY', 'SELL'):
            rows, tf, context = scenario(sid, side)
            card = st.analyze_strategy(sid, 'TEST', tf, rows, context['as_of'], context)
            if sid == ADVISORY_MODEL:
                self.assertEqual(card['status'], 'WAIT')
                self.assertFalse(card['actionable'])
                quote = ({'bid':103.9, 'ask':104., 'time':context['as_of']} if side == 'BUY' else
                         {'bid':96., 'ask':96.1, 'time':context['as_of']})
                result = composite.run(rows, quote=quote)
                self.assertEqual(result['status'], 'READY')
                self.assertEqual(result['candidate']['side'], 'LONG' if side == 'BUY' else 'SHORT')
            else:
                self.assertTrue(card['actionable'], (sid, side, card['status']))
                self.assertEqual(card['direction'], side)
                entry, stop = card['entry']['price'], card['stop']['price']
                self.assertTrue(stop < entry if side == 'BUY' else stop > entry)
                self.assertTrue(all(t['price'] > entry if side == 'BUY' else t['price'] < entry for t in card['targets']))
            invalid = st.analyze_strategy(sid, 'TEST', tf, rows, context['as_of']-1, context)
            self.assertEqual(invalid['status'], 'DATA_INVALID')
            self.assertFalse(invalid['actionable'])
            short = st.analyze_strategy(sid, 'TEST', tf, rows[:10], context['as_of'], context)
            self.assertEqual(short['status'], 'DATA_MISSING')
            self.assertFalse(short['actionable'])
    run.__name__ = 'test_model_'+sid
    return run


MODEL_TEST_COVERAGE = {'test_model_'+sid: [sid] for sid in REGISTRY_MODELS}
for _sid in REGISTRY_MODELS:
    setattr(ModelAcceptanceById, 'test_model_'+_sid, model_test(_sid))


def test_declared_model_coverage_is_bijective():
    assert set(MODEL_TEST_COVERAGE)=={'test_model_'+sid for sid in REGISTRY_MODELS}
    assert sorted(sid for covered in MODEL_TEST_COVERAGE.values() for sid in covered)==sorted(REGISTRY_MODELS)
