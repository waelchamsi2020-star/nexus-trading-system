"""Independent arithmetic and causal decision fixtures, not profitability evidence."""
import copy
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_strategies import card

from nexus import committee
from nexus import extended_models as ext
from nexus import indicators as ind
from nexus import strategies as st
from nexus.learning import knowledge_export_sources, load_library


def book(count=90):
    return [{'time': 1700000000+i*60, 'open': 100., 'high': 101., 'low': 99., 'close': 100., 'tick_volume': 100}
            for i in range(count)]


def reflected(rows):
    return [dict(x, open=200-x['open'], high=200-x['low'], low=200-x['high'], close=200-x['close']) for x in rows]


class IndicatorTests(unittest.TestCase):
    def test_wilder_seed_and_recurrence_hand_calculation(self):
        self.assertEqual(ind.rma([1, 2, 3, 4, 5], 3)[:3], [None, None, 2])
        self.assertAlmostEqual(ind.rma([1, 2, 3, 4, 5], 3)[-1], 31/9)
        self.assertEqual(ind.ema([1, 2, 3, 4], 3), [None, None, 2, 3])
        self.assertEqual(ind.sma([1, 2, 3, 4], 3), [None, None, 2, 3])

    def test_rsi_independent_published_style_worked_sequence(self):
        closes = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42,
                  45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00]
        values = ind.rsi_wilder(closes)
        self.assertTrue(all(x is None for x in values[:14]))
        self.assertAlmostEqual(values[14], 70.4641350211, places=8)
        self.assertAlmostEqual(values[15], 66.2496185536, places=8)
        self.assertEqual(ind.rsi_wilder([1.]*20)[-1], 50)
        self.assertEqual(ind.rsi_wilder(list(range(20)))[-1], 100)
        self.assertEqual(ind.rsi_wilder(list(range(20, 0, -1)))[-1], 0)

    def test_stochastic_and_williams_range_math_and_warmup(self):
        rows = [{'high': i+2., 'low': float(i), 'close': i+1.} for i in range(10)]
        result = ind.stochastic(rows, 3, 2, 2)
        self.assertEqual(result['raw_k'][:3], [None, None, 75])
        self.assertEqual(result['k'][:4], [None, None, None, 75])
        self.assertEqual(result['d'][:5], [None, None, None, None, 75])
        self.assertEqual(ind.williams_r(rows, 3)[-1], -25)
        flat = [{'high': 1., 'low': 1., 'close': 1.}]*20
        self.assertEqual(ind.stochastic(flat)['d'][-1], 50)
        self.assertEqual(ind.williams_r(flat)[-1], -50)

    def test_atr_uses_previous_close_and_excludes_unknown_first_range(self):
        rows = [{'high': 11., 'low': 9., 'close': 10.}, {'high': 16., 'low': 14., 'close': 15.},
                {'high': 15., 'low': 12., 'close': 13.}, {'high': 14., 'low': 12., 'close': 13.}]
        self.assertEqual(ind.true_range(rows), [None, 6, 3, 2])
        self.assertEqual(ind.atr_wilder(rows, 2), [None, None, 4.5, 3.25])

    def test_adx_constant_direction_and_tied_expansion(self):
        rows = [{'high': i+2., 'low': float(i), 'close': i+1.} for i in range(10)]
        result = ind.adx_wilder(rows, 3)
        self.assertEqual(result['plus_di'][3], 50)
        self.assertEqual(result['minus_di'][3], 0)
        self.assertTrue(all(x is None for x in result['adx'][:5]))
        self.assertEqual(result['adx'][5], 100)
        ties = [{'high': 100+i, 'low': 100-i, 'close': 100.} for i in range(10)]
        tied = ind.adx_wilder(ties, 3)
        self.assertEqual(tied['plus_di'][-1], 0)
        self.assertEqual(tied['minus_di'][-1], 0)
        self.assertEqual(tied['adx'][-1], 0)

    def test_cci_mean_absolute_deviation_not_standard_deviation(self):
        rows = [{'high': float(x), 'low': float(x), 'close': float(x)} for x in (1, 2, 3, 4)]
        self.assertAlmostEqual(ind.cci(rows, 3)[-1], 100)
        self.assertEqual(ind.cci([{'high': 1., 'low': 1., 'close': 1.}]*20)[-1], 0)

    def test_macd_explicit_ema_signal_and_alignment(self):
        values = [1., 2., 3., 4., 5., 6.]
        result = ind.macd(values, 2, 3, 2)
        self.assertEqual(result['line'], [None, None, .5, .5, .5, .5])
        self.assertEqual(result['signal'], [None, None, None, .5, .5, .5])
        self.assertEqual(result['histogram'], [None, None, None, 0, 0, 0])

    def test_mfi_uses_direction_of_typical_price_and_positive_ticks(self):
        rows = [{'high': float(x), 'low': float(x), 'close': float(x), 'tick_volume': 1} for x in (1, 2, 1, 3)]
        self.assertAlmostEqual(ind.mfi_tick(rows, 3)[-1], 100*5/6)
        self.assertEqual(ind.mfi_tick([{'high': 1., 'low': 1., 'close': 1., 'tick_volume': 10}]*20)[-1], 50)
        for value in (None, 0, -1, True, float('nan'), float('inf')):
            bad = copy.deepcopy(rows); bad[-1]['tick_volume'] = value
            with self.assertRaises((TypeError, ValueError)):
                ind.mfi_tick(bad, 3)

    def test_all_indicators_are_prefix_causal_and_input_preserving(self):
        rows = book()
        for i, x in enumerate(rows):
            price = 100+math.sin(i/4)
            x.update(open=price, close=price+.1, high=price+1, low=price-1, tick_volume=100+i)
        original = copy.deepcopy(rows)
        calculations = [ind.atr_wilder, ind.stochastic, ind.adx_wilder, ind.cci, ind.williams_r, ind.mfi_tick,
                        lambda x: ind.rsi_wilder([z['close'] for z in x]),
                        lambda x: ind.macd([z['close'] for z in x])]
        for calculate in calculations:
            whole = calculate(rows); prefix = calculate(rows[:65])
            if isinstance(whole, dict):
                self.assertEqual({k:v[:65] for k,v in whole.items()}, prefix)
            else:
                self.assertEqual(whole[:65], prefix)
        self.assertEqual(rows, original)

    def test_invalid_parameters_and_nonfinite_values_fail_explicitly(self):
        for value in (0, -1, True, 2.5):
            with self.assertRaises(ValueError): ind.rma([1, 2, 3], value)
        with self.assertRaises(ValueError): ind.ema([1, float('nan')], 2)
        with self.assertRaises(ValueError): ind.macd([1, 2], 3, 2)


class AdditionalModelTests(unittest.TestCase):
    def test_every_new_contract_has_bilingual_rules_parameters_and_authority(self):
        self.assertEqual(len(ext.MODEL_IDS), 16)
        for sid in ext.MODEL_IDS:
            meta = st.REGISTRY[sid]; contract = meta['contract']; definition = contract['definition']
            self.assertEqual(contract['rule_id'], sid)
            self.assertFalse(contract['school_complete'])
            self.assertFalse(contract['direct_broker_authority'])
            self.assertEqual(contract['rule_version'], meta['version'])
            self.assertTrue(definition['rules_ar'] and definition['rules_en'] and definition['parameters'])
            self.assertIn(meta['evidence_group'], committee.GROUPS)

    def test_all_new_models_validate_data_and_never_mutate_the_input(self):
        rows = book(); now = rows[-1]['time']+60; original = copy.deepcopy(rows)
        for sid in ext.MODEL_IDS:
            result = st.analyze_strategy(sid, 'TEST', 'M1', rows, now, {'data_kind':'synthetic'})
            self.assertIn(result['status'], ('WAIT', 'READY'))
            self.assertEqual(st.analyze_strategy(sid, 'TEST', 'M1', rows, now-1)['status'], 'DATA_INVALID')
            self.assertEqual(st.analyze_strategy(sid, 'TEST', 'M1', rows[:20], rows[19]['time']+60)['status'], 'DATA_MISSING')
            bad = copy.deepcopy(rows); bad[-1]['high'] = float('nan')
            self.assertEqual(st.analyze_strategy(sid, 'TEST', 'M1', bad, now)['status'], 'DATA_INVALID')
            json.dumps(result, allow_nan=False)
        self.assertEqual(rows, original)

    def test_new_volume_models_abstain_on_missing_counts(self):
        rows = book(); rows[-2]['tick_volume'] = 0
        for sid in ('mfi_tick_rebound', 'wyckoff_range_expansion'):
            result = st.analyze_strategy(sid, 'TEST', 'M1', rows, rows[-1]['time']+60)
            self.assertEqual(result['status'], 'DATA_MISSING')
            self.assertFalse(result['actionable'])

    def test_rectangle_both_directions_and_unconfirmed_boundary(self):
        rows = book()
        for i, x in enumerate(rows[-21:-1]):
            x.update(high=102. if i in (2, 12) else 101.5, low=98. if i in (5, 16) else 98.5)
        rows[-1].update(open=101., high=103., low=100.5, close=102.5)
        for sample, side in ((rows, 'BUY'), (reflected(rows), 'SELL')):
            result = st.analyze_strategy('rectangle_breakout', 'TEST', 'M1', sample, sample[-1]['time']+60)
            self.assertEqual((result['status'], result['direction']), ('READY', side))
            self.assertTrue(result['actionable'])
        rows[-9]['high'] = 101.5
        self.assertFalse(st.analyze_strategy('rectangle_breakout', 'TEST', 'M1', rows, rows[-1]['time']+60)['actionable'])

    def test_flag_pole_retracement_and_fresh_break(self):
        rows = book()
        for i, x in enumerate(rows[-14:-9]):
            x.update(open=100+2*i, close=102+2*i, high=102.2+2*i, low=99.8+2*i)
        for i, x in enumerate(rows[-9:-1]):
            x.update(open=108-i*.2, close=107.8-i*.2, high=108.5-i*.2, low=107.5-i*.2)
        rows[-1].update(open=108, close=109., high=109.2, low=107.9)
        for sample, side in ((rows, 'BUY'), (reflected(rows), 'SELL')):
            result = ext.flag_breakout(sample, {})
            self.assertEqual((result['triggered'], result['direction']), (True, side))
        rows[-1]['close'] = 108.
        self.assertFalse(ext.flag_breakout(rows, {})['triggered'])

    def test_darvas_two_boxes_require_confirmation_and_progression(self):
        rows = book()
        for offset, window in enumerate((rows[-41:-21], rows[-21:-1])):
            for i, x in enumerate(window):
                x.update(open=100+offset, close=100+offset, high=102+offset if i==3 else 101+offset,
                         low=98+offset)
        rows[-1].update(open=102., close=103.5, high=104., low=101.)
        self.assertTrue(ext.darvas_rising_boxes(rows, {})['triggered'])
        rows[-2]['high'] = 103.
        self.assertFalse(ext.darvas_rising_boxes(rows, {})['triggered'])

    def test_harmonic_geometry_all_ratios_and_bearish_symmetry(self):
        # Independently chosen dimensionless XABCD coordinates meet every
        # interval; no future observation is used to select a trade fixture.
        patterns = {'gartley':[0., 100., 38.2, 83.2, 21.4],
                    'bat':[0., 100., 50., 80., 11.4],
                    'butterfly':[0., 100., 21.4, 75., -27.]}
        for kind, prices in patterns.items():
            pivots = [{'index': 10+i*5, 'kind': 'LOW' if i%2==0 else 'HIGH', 'price': 100+p, 'confirmed_at': 1000+i}
                      for i,p in enumerate(prices)]
            result = ext.harmonic_geometry(pivots, kind)
            self.assertIsNotNone(result, kind)
            self.assertEqual(result['direction'], 'BUY')
            mirrored = [dict(p, price=400-p['price'], kind='HIGH' if p['kind']=='LOW' else 'LOW') for p in pivots]
            self.assertEqual(ext.harmonic_geometry(mirrored, kind)['direction'], 'SELL')
            bad = copy.deepcopy(pivots); bad[-1]['price'] = bad[-2]['price']
            self.assertIsNone(ext.harmonic_geometry(bad, kind))
            bad = copy.deepcopy(pivots); bad[-1]['kind'] = bad[-2]['kind']
            self.assertIsNone(ext.harmonic_geometry(bad, kind))

    def test_harmonic_cannot_trade_on_confirmation_bar_or_breached_d(self):
        rows = book(); values = [100., 110., 103.82, 108.32, 102.14]
        pivots = [{'index': 60+i*5, 'kind': 'LOW' if i%2==0 else 'HIGH', 'price': v, 'confirmed_at': rows[62+i*5]['time']+60}
                  for i,v in enumerate(values)]
        for x in rows[81:]: x.update(open=103., close=103., high=104., low=102.5)
        rows[-2]['close'] = 103.5; rows[-1].update(open=103.5, close=104.5, high=105., low=103.)
        result = ext.harmonic_gartley(rows, {'pivots':pivots})
        self.assertTrue(result['triggered'])
        self.assertEqual(result['targets'][0]['price'], 108.32)
        on_confirm = rows[:83]
        self.assertFalse(ext.harmonic_gartley(on_confirm, {'pivots':pivots})['triggered'])
        rows[85]['low'] = 102.
        self.assertFalse(ext.harmonic_gartley(rows, {'pivots':pivots})['triggered'])

    def test_indicator_rebounds_need_a_fresh_cross_and_confirming_price(self):
        rows = book(); rows[-1].update(close=100.5)
        calculations = [('rsi_wilder_rebound','rsi_wilder',29.,31.), ('cci_reentry','cci',-101.,-99.),
                        ('williams_reentry','williams_r',-81.,-79.), ('mfi_tick_rebound','mfi_tick',19.,21.)]
        for sid, function, before, after in calculations:
            with patch.object(ind, function, return_value=[before]*(len(rows)-1)+[after]):
                self.assertTrue(st.REGISTRY[sid]['analyzer'](rows,{})['triggered'])
            with patch.object(ind, function, return_value=[after]*len(rows)):
                self.assertFalse(st.REGISTRY[sid]['analyzer'](rows,{})['triggered'])
            down = reflected(rows)
            a, z = ((71.,69.) if sid=='rsi_wilder_rebound' else (101.,99.) if sid=='cci_reentry' else
                    (-19.,-21.) if sid=='williams_reentry' else (81.,79.))
            with patch.object(ind, function, return_value=[a]*(len(rows)-1)+[z]):
                self.assertEqual(st.REGISTRY[sid]['analyzer'](down,{})['direction'], 'SELL')

    def test_new_dependencies_are_archived_and_exportable(self):
        root = Path(__file__).resolve().parents[1]; library = load_library(root)
        self.assertTrue(set(ext.MODEL_IDS) <= set(library))
        for sid in ext.MODEL_IDS:
            self.assertEqual(library[sid]['dependency_schema'], 4)
            self.assertIn('indicators.py', library[sid]['source_hashes'])
            self.assertIn('config/models.yaml', library[sid]['source_hashes'])
            self.assertIn('config/models.schema.json', library[sid]['source_hashes'])
        manifest, files = knowledge_export_sources(root, [library[ext.MODEL_IDS[0]]])
        self.assertTrue(manifest['complete'])
        self.assertEqual({x['name'] for x in manifest['sources']}, set(library[ext.MODEL_IDS[0]]['source_hashes']))
        self.assertEqual(len(files), 10)

    def test_stochastic_macd_adx_confirmation_and_rejection(self):
        rows = book(); rows[-1]['close'] = 100.5
        with patch.object(ind, 'stochastic', return_value={'k':[19.,21.], 'd':[18.,20.]}):
            self.assertEqual(ext.stochastic_rebound(rows,{})['direction'], 'BUY')
        with patch.object(ind, 'stochastic', return_value={'k':[19.,21.], 'd':[18.,22.]}):
            self.assertFalse(ext.stochastic_rebound(rows,{})['triggered'])
        with patch.object(ind, 'macd', return_value={'line':[.2,.4], 'signal':[.3,.3]}):
            self.assertEqual(ext.macd_signal_cross(rows,{})['direction'], 'BUY')
        with patch.object(ind, 'macd', return_value={'line':[-.4,-.2], 'signal':[-.3,-.3]}):
            self.assertFalse(ext.macd_signal_cross(rows,{})['triggered'])
        values={'plus_di':[20.,30.], 'minus_di':[25.,25.], 'adx':[25.,26.]}
        with patch.object(ind, 'adx_wilder', return_value=values):
            self.assertEqual(ext.adx_di_cross(rows,{})['direction'], 'BUY')
        with patch.object(ind, 'adx_wilder', return_value={**values,'adx':[27.,26.]}):
            self.assertFalse(ext.adx_di_cross(rows,{})['triggered'])

    def test_three_bar_reversal_direction_and_middle_body(self):
        rows=book()
        for i,x in enumerate(rows[:-3]):
            p=110-.1*i
            x.update(open=p,close=p-.1,high=p+.3,low=p-.4)
        rows[-3].update(open=100.5,close=98.5,high=100.6,low=98.4)
        rows[-2].update(open=98.5,close=98.6,high=98.8,low=98.2)
        rows[-1].update(open=98.6,close=100.,high=100.2,low=98.5)
        for sample,side in ((rows,'BUY'),(reflected(rows),'SELL')):
            result=ext.three_bar_reversal(sample,{})
            self.assertEqual((result['triggered'],result['direction']),(True,side))
        rows[-2].update(open=98.5,close=99.5,high=99.8)
        self.assertFalse(ext.three_bar_reversal(rows,{})['triggered'])

    def test_range_expansion_tick_proxy_and_causal_boundary(self):
        rows=book()
        for i,x in enumerate(rows[-41:-1]):
            p=100+(.5 if i%2 else -.5)
            x.update(open=p,close=p,high=103. if i==5 else p+.4,low=97. if i==10 else p-.4)
        rows[-1].update(open=100.,close=104.,high=104.2,low=99.8,tick_volume=200)
        for sample,side in ((rows,'BUY'),(reflected(rows),'SELL')):
            result=ext.wyckoff_range_expansion(sample,{})
            self.assertEqual((result['triggered'],result['direction']),(True,side))
        rows[-1]['tick_volume']=100
        self.assertFalse(ext.wyckoff_range_expansion(rows,{})['triggered'])

    def test_liquidity_sweep_bos_retest_order_and_first_touch(self):
        rows=book(); sweep=len(rows)-6
        rows[sweep].update(open=100.,high=100.5,low=98.5,close=99.5)
        rows[sweep+1].update(open=99.5,high=102.5,low=99.4,close=102.2)
        for x in rows[sweep+2:-1]:x.update(open=102.,close=102.,high=102.5,low=101.6)
        rows[-1].update(open=101.1,close=101.8,high=102.,low=101.)
        for sample,side in ((rows,'BUY'),(reflected(rows),'SELL')):
            result=ext.liquidity_bos_retest(sample,{})
            self.assertEqual((result['triggered'],result['direction']),(True,side))
        rows[-2]['low']=101.
        self.assertFalse(ext.liquidity_bos_retest(rows,{})['triggered'])

    def test_model_module_tampering_is_detected_before_reference_use(self):
        from shutil import copytree
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)
            copytree(root/'docs/knowledge',target/'docs/knowledge')
            copytree(root/'docs/agent-rules/snapshot',target/'docs/agent-rules/snapshot')
            source=target/'docs/agent-rules/snapshot/nexus/indicators.py'
            source.write_text('# changed formula',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'source fingerprint'):load_library(target)


class FamilyNetDecisionTests(unittest.TestCase):
    def decide(self, cards):
        return committee.decide(cards, {}, {'ok':True,'coverage':{'calendar':True}}, 1500,
                                portfolio={'validation_policy':'forward_demo', 'autonomous_fast':True,
                                           'decision_protocol':'multi_school_v1'})

    def test_all_valid_models_participate_without_fixed_vote_percentage(self):
        primary = card('entry', 'engulfing', 'M1', 'candle'); primary['score'] = 50.
        support = card('support', 'ema_cross', 'M1', 'trend'); support['score'] = 51.
        opposite = card('opposite', 'rsi_rebound', 'M1', 'momentum', side='SELL'); opposite['score'] = 100.
        result = self.decide([primary, support, opposite])
        self.assertEqual(result['decision'], 'BUY')
        row = next(x for x in result['ranked'] if x['side']=='BUY')
        self.assertEqual(row['directional_evidence']['net'], 1.)
        self.assertNotIn('required_advantage', row['directional_evidence'])
        # One hundred copies of the same transform must not overturn the vote.
        copies = [dict(opposite, id='copy'+str(i)) for i in range(100)]
        again = self.decide([primary, support, opposite]+copies)
        self.assertEqual(again['decision'], 'BUY')
        self.assertEqual(again['evidence_coverage']['fresh_eligible_cards'], 103)

    def test_ties_missing_and_single_family_are_not_confirmation(self):
        primary = card('entry', 'engulfing', 'M1', 'candle'); primary['score'] = 50.
        support = card('support', 'ema_cross', 'M1', 'trend'); support['score'] = 50.
        opposite = card('opposite', 'rsi_rebound', 'M1', 'momentum', side='SELL'); opposite['score'] = 100.
        result = self.decide([primary, support, opposite])
        self.assertEqual(result['proposals'], [])
        missing = dict(support, status='DATA_MISSING', score=100.)
        result = self.decide([primary, missing])
        self.assertEqual(result['proposals'], [])
        self.assertEqual(result['evidence_coverage']['excluded_cards'], 1)
        self.assertFalse(result['evidence_coverage']['missing_is_confirmation'])


if __name__ == '__main__': unittest.main()
