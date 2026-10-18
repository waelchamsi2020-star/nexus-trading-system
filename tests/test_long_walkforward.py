"""Synthetic proofs of scheduling, causal fitting, unique replay and censoring.

These fixtures test the research engine. They are not price data or edge
evidence, and they never connect to a broker or submit an order.
"""
import copy
import importlib.util
import unittest
from pathlib import Path

from nexus.quant import replay

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('long_walkforward_fixture', ROOT / 'tools/long_walkforward.py')
engine = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(engine)
_cache_spec = importlib.util.spec_from_file_location('long_signal_cache_fixture', ROOT / 'tools/long_signal_cache.py')
causal_cache = importlib.util.module_from_spec(_cache_spec)
_cache_spec.loader.exec_module(causal_cache)


def card(side='BUY', *, hold=12, stop=None, target=None, invalidation=None):
    stop = (98. if side == 'BUY' else 102.) if stop is None else stop
    target = (110. if side == 'BUY' else 90.) if target is None else target
    return {'status': 'READY', 'coverage': 'IMPLEMENTED', 'direction': side,
            'entry': {'triggered': True, 'zone': [95., 105.]}, 'stop': {'price': stop},
            'targets': [{'price': target}], 'invalidation': {'price': invalidation},
            'execution_plan': {'max_hold_bars': hold}}


def fixture_cache(count=130, *, side='BUY', signals=(20,), gap_index=None):
    bars = [{'time': 1_600_000_000 + index * 3600, 'open': 100., 'high': 100.5,
             'low': 99.5, 'close': 100., 'tick_volume': 100 + index,
             'real_volume': 0, 'spread': 2} for index in range(count)]
    if gap_index is not None:
        for row in bars[gap_index:]:
            row['time'] += 3 * 3600
    starts, atrs = causal_cache.segment_arrays(bars, 'H1', 'CONTINUOUS')
    return {'symbol': 'SYNTHETIC', 'timeframe': 'H1', 'bars': bars,
            'segment_starts': starts, 'atr_values': atrs,
            'specification': {'point': .01, 'profit_currency': 'USD', 'contract_size': 100000., 'symbol': 'SYNTHETIC'},
            'cards': {'engulfing': [{'index': index, 'card': card(side)} for index in signals]},
            'provenance': {'csv_sha256': 'SYNTHETIC_UNIT_FIXTURE_NOT_REAL_DATA'}}


def fitted_fold(start=20, end=100, *, baseline=1., fold_id=0):
    return {'fold_id': fold_id, 'test_start': start, 'test_end': end, 'training_atr_median': baseline}


class LongWalkforwardTests(unittest.TestCase):
    def test_actual_H1_30860_and_M5_100000_window_schedules_and_24_bar_embargo(self):
        for count, train, test, step, expected_count, final_end in (
                (30860, 5000, 1000, 500, 50, 30524),
                (100000, 20000, 5000, 2500, 30, 97524)):
            with self.subTest(count=count):
                folds = engine.schedule(count, train=train, test=test, step=step, embargo=24)
                self.assertEqual(expected_count, len(folds))
                self.assertEqual(train + 24, folds[0]['test_start'])
                self.assertEqual(final_end, folds[-1]['test_end'])
                for index, fold in enumerate(folds):
                    self.assertEqual(index, fold['fold_id'])
                    self.assertEqual(train, fold['train_end'] - fold['train_start'])
                    self.assertEqual(24, fold['test_start'] - fold['train_end'])
                    self.assertEqual(test, fold['test_end'] - fold['test_start'])
                    self.assertLessEqual(fold['test_end'], count)
                    if index:
                        self.assertEqual(step, fold['test_start'] - folds[index - 1]['test_start'])
        offset = engine.schedule(130, train=20, test=40, step=20, offset=500)
        self.assertEqual(500, offset[0]['train_start'])
        self.assertEqual(544, offset[0]['test_start'])

    def test_window_schedule_rejects_reduced_embargo_and_holes(self):
        for changed in ({'embargo': 23}, {'step': 41}, {'train': True}, {'count': 0}):
            args = {'count': 130, 'train': 20, 'test': 40, 'step': 20, 'embargo': 24, **changed}
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                engine.schedule(**args)

    def test_training_ATR_invariant_to_every_future_price_and_respects_gap_warmup(self):
        cache = fixture_cache(count=200)
        folds = engine.schedule(200, train=50, test=40, step=20)
        first = engine.fit_baselines(cache, folds[:1])[0]
        changed = copy.deepcopy(cache)
        # Alter all observations at/after exclusive training end, including
        # embargo and test. Recompute ATR from OHLC rather than patching the fit.
        for row in changed['bars'][folds[0]['train_end']:]:
            row.update(open=1000., high=1200., low=800., close=1050.)
        changed['segment_starts'], changed['atr_values'] = causal_cache.segment_arrays(changed['bars'], 'H1', 'CONTINUOUS')
        self.assertEqual(first, engine.fit_baselines(changed, folds[:1])[0])
        gapped = fixture_cache(count=200, gap_index=30)
        fitted = engine.fit_baselines(gapped, folds[:1])[0]
        # Valid training ATR endpoints:14..29 and44..49; none crosses gap30.
        self.assertEqual(22, fitted['training_atr_windows'])
        self.assertEqual(1., fitted['training_atr_median'])

    def test_primary_open_position_survives_new_fold_and_new_volatility_baseline(self):
        cache = fixture_cache(signals=(20, 25, 34))
        folds = [fitted_fold(20, 70, baseline=1., fold_id=0),
                 fitted_fold(25, 100, baseline=.01, fold_id=1)]
        book = engine.replay_book(cache, 'engulfing', folds, start=20, end=100)
        self.assertEqual(1, len(book['trades']))
        trade = book['trades'][0]
        self.assertEqual((20, 21, 33, 0), (trade['signal_index'], trade['entry_index'], trade['exit_index'], trade['fold_id']))
        self.assertEqual('TIME_NEXT_OPEN', trade['exit_reason'])
        self.assertEqual([34], [r['signal_index'] for r in book['rejected']])
        self.assertEqual('TRAINING_ATR_ENVELOPE', book['rejected'][0]['reason'])

    def test_overlapping_diagnostic_books_repeat_a_trade_but_primary_does_not(self):
        cache = fixture_cache(signals=(64, 70, 80, 90, 100))
        folds = engine.fit_baselines(cache, engine.schedule(130, train=20, test=40, step=20))
        primary = engine.replay_book(cache, 'engulfing', folds, start=folds[0]['test_start'], end=folds[-1]['test_end'])
        first = engine.replay_book(cache, 'engulfing', folds, start=folds[0]['test_start'], end=folds[0]['test_end'], fixed_fold=0)
        second = engine.replay_book(cache, 'engulfing', folds, start=folds[1]['test_start'], end=folds[1]['test_end'], fixed_fold=1)
        self.assertIn(65, [t['entry_index'] for t in first['trades']])
        self.assertIn(65, [t['entry_index'] for t in second['trades']])
        keys = [(t['entry_time'], t['exit_time']) for t in primary['trades']]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(1, sum(t['entry_index'] == 65 for t in primary['trades']))
        self.assertLess(len(primary['trades']), len(first['trades']) + len(second['trades']))
        result = engine.run_study(cache, train=20, test=40, step=20, model_ids=['engulfing'])
        self.assertEqual(primary, result['primary_base_books']['engulfing'])
        self.assertEqual(cache['provenance']['csv_sha256'], result['source_data_sha256'])
        self.assertFalse(result['qualified'])
        self.assertFalse(result['execution_authority'])

    def test_unknown_gap_before_entry_during_hold_or_at_time_exit_has_no_invented_R(self):
        for gap in (21, 23, 33):
            with self.subTest(gap=gap):
                cache = fixture_cache(signals=(20,), gap_index=gap)
                book = engine.replay_book(cache, 'engulfing', [fitted_fold()], start=20, end=100)
                self.assertEqual([], book['trades'])
                self.assertEqual(1, len(book['censored']))
                censored = book['censored'][0]
                self.assertIsNone(censored['r'])
                self.assertNotIn('exit', censored)
                self.assertNotIn('net_price_pnl', censored)
                self.assertEqual('UNOBSERVED_ENTRY' if gap == 21 else 'CENSORED_MISSING_INTRABAR', censored['state'])
                if gap != 21:
                    self.assertEqual(gap - 1, censored['last_observed_index'])

    def test_unknown_gap_at_invalidation_exit_censors_then_later_conditional_episode_can_close(self):
        cache = fixture_cache(signals=(20, 70), gap_index=23)
        cache['cards']['engulfing'][0]['card'] = card(stop=95., invalidation=99.)
        cache['bars'][22].update(open=100., high=100.2, low=98.7, close=98.8)
        book = engine.replay_book(cache, 'engulfing', [fitted_fold()], start=20, end=110)
        self.assertEqual(1, len(book['censored']))
        self.assertEqual('CENSORED_MISSING_INTRABAR', book['censored'][0]['state'])
        self.assertIsNone(book['censored'][0]['r'])
        self.assertEqual(1, len(book['trades']))
        self.assertEqual(70, book['trades'][0]['signal_index'])

    def test_cash_commission_USDJPY_uses_exit_quote_for_USD_fee_conversion(self):
        trade = {'entry': 150., 'stop': 149., 'exit': 150.2, 'gross_price_pnl': .2}
        specification = {'profit_currency': 'JPY', 'symbol': 'USDJPY', 'contract_size': 100000.}
        priced = engine.price_trades([trade], 7., specification)[0]
        expected_fee_jpy_per_unit = 7. * 150.2 / 100000.
        self.assertAlmostEqual(expected_fee_jpy_per_unit, priced['commission_price_units'])
        self.assertAlmostEqual(.2 - expected_fee_jpy_per_unit, priced['net_price_pnl'])
        self.assertAlmostEqual(.2 - expected_fee_jpy_per_unit, priced['r'])
        dollar = engine.price_trades([trade], 7., {**specification, 'profit_currency': 'USD'})[0]
        self.assertEqual(.00007, dollar['commission_price_units'])
        self.assertGreater(priced['commission_price_units'], dollar['commission_price_units'])
        with self.assertRaises(ValueError):
            engine.price_trades([trade], 7., {**specification, 'symbol': 'EURJPY'})

    def test_continuous_book_matches_authoritative_core_replay_for_BUY_and_SELL(self):
        keys = ('entry_index', 'exit_index', 'entry_time', 'exit_time', 'side', 'entry', 'stop',
                'target', 'exit', 'gross_price_pnl', 'exit_reason', 'ambiguous_bar', 'r')
        for side in ('BUY', 'SELL'):
            with self.subTest(side=side):
                cache = fixture_cache(count=100, side=side, signals=(20, 25, 40, 60, 80))
                indexed_cards = {row['index']: row['card'] for row in cache['cards']['engulfing']}

                def signal(history, as_of, base_time=cache['bars'][0]['time'], cards=indexed_cards):
                    index = (history[-1]['time'] - base_time) // 3600
                    self.assertEqual(history[-1]['time'] + 3600, as_of)
                    return cards.get(index, {'status': 'WAIT'})

                reference = replay(cache['bars'], 'engulfing', cache['symbol'], 'H1', start_index=20,
                                   end_index=100, config={'point': .01, 'slippage_price': .1,
                                   'commission_per_unit': 0.}, context={'tick_size': .01,
                                   'train_atr_median': 1.}, signal_fn=signal)
                book = engine.replay_book(cache, 'engulfing', [fitted_fold()], start=20, end=100)
                self.assertTrue(reference['trades'])
                self.assertEqual(len(reference['trades']), len(book['trades']))
                self.assertEqual([{key: trade[key] for key in keys} for trade in reference['trades']],
                                 [{key: trade[key] for key in keys} for trade in book['trades']])


if __name__ == '__main__':
    unittest.main()
