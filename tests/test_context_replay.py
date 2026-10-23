"""Independent synthetic proofs for veto-before-entry replay semantics.

These are mechanics fixtures, never market evidence or profitability results.
"""
import copy
import unittest

from test_long_walkforward import engine, fitted_fold, fixture_cache

from nexus.quant import replay
from nexus.regime_router import load_routing_config, route_signal
from nexus.timeframes import bar_close_time

ECONOMIC_FIELDS = ('entry_index', 'exit_index', 'entry_time', 'exit_time', 'side',
                   'entry', 'stop', 'target', 'exit', 'gross_price_pnl',
                   'commission_price_units', 'net_price_pnl', 'r',
                   'exit_reason', 'ambiguous_bar')


def economic_rows(trades):
    return [{key: trade[key] for key in ECONOMIC_FIELDS} for trade in trades]


class ContextReplay(unittest.TestCase):
    def test_omitted_signal_gate_matches_independent_core_replay_for_both_sides_and_all_costs(self):
        for side in ('BUY', 'SELL'):
            cache = fixture_cache(count=100, side=side, signals=(20, 25, 40, 60, 80))
            indexed = {row['index']: row['card'] for row in cache['cards']['engulfing']}

            def signal(history, as_of, base_time=cache['bars'][0]['time'], cards=indexed):
                index = (history[-1]['time'] - base_time) // 3600
                self.assertEqual(bar_close_time(history[-1]['time'], 'H1'), as_of)
                return cards.get(index, {'status': 'WAIT'})

            book = engine.replay_book(cache, 'engulfing', [fitted_fold()], start=20, end=100)
            self.assertTrue(book['trades'])
            self.assertTrue(all('routing' not in trade for trade in book['trades']))
            for fee in (0., 3., 7.):
                with self.subTest(side=side, round_trip_commission=fee):
                    reference = replay(
                        cache['bars'], 'engulfing', cache['symbol'], 'H1', start_index=20, end_index=100,
                        config={'point': .01, 'slippage_price': .1, 'commission_per_unit': fee / 100000.},
                        context={'tick_size': .01, 'train_atr_median': 1.}, signal_fn=signal)
                    actual = engine.price_trades(book['trades'], fee, cache['specification'])
                    self.assertEqual(economic_rows(reference['trades']), economic_rows(actual))

    def test_always_allow_preserves_fill_prices_costs_rejections_and_censoring(self):
        for side in ('BUY', 'SELL'):
            for gap in (None, 23):
                with self.subTest(side=side, gap=gap):
                    cache = fixture_cache(count=100, side=side, signals=(20, 25, 40, 60, 80), gap_index=gap)
                    snapshot = copy.deepcopy(cache)
                    baseline = engine.replay_book(cache, 'engulfing', [fitted_fold()], start=20, end=100)
                    calls = []

                    def allow(model, index, card, fold, recorded=calls, source=cache):
                        recorded.append((model, index, fold['fold_id']))
                        self.assertIs(card, source['cards'][model][next(
                            position for position, row in enumerate(source['cards'][model]) if row['index'] == index)]['card'])
                        return {'allowed': True, 'regime': 'TREND_UP', 'rule_version': '1.0.0',
                                'routing_fingerprint': '0' * 64, 'classifier_fingerprint': '1' * 64}

                    gated = engine.replay_book(cache, 'engulfing', [fitted_fold()], start=20, end=100,
                                               signal_gate=allow)
                    self.assertTrue(calls)
                    self.assertEqual(snapshot, cache)
                    self.assertEqual(baseline['rejected'], gated['rejected'])
                    self.assertEqual([{key: value for key, value in row.items() if key != 'routing'}
                                      for row in gated['censored']], baseline['censored'])
                    for fee in (0., 3., 7.):
                        old = engine.price_trades(baseline['trades'], fee, cache['specification'])
                        new = engine.price_trades(gated['trades'], fee, cache['specification'])
                        self.assertEqual(economic_rows(old), economic_rows(new))

    def test_vetoing_first_signal_replays_later_signal_previously_hidden_by_position_overlap(self):
        cache = fixture_cache(count=100, signals=(20, 25, 40))
        baseline = engine.replay_book(cache, 'engulfing', [fitted_fold()], start=20, end=100)
        self.assertEqual([20, 40], [trade['signal_index'] for trade in baseline['trades']])
        observed, audited = [], []

        def veto_first(model, index, _card, fold):
            observed.append((model, index, fold['fold_id']))
            return {'allowed': index != 20, 'regime': 'RANGE', 'reason': 'SYNTHETIC_CONTEXT_VETO'}

        new = engine.replay_book(cache, 'engulfing', [fitted_fold()], start=20, end=100,
                                 signal_gate=veto_first, gate_audit=audited.append)
        self.assertEqual([25, 40], [trade['signal_index'] for trade in new['trades']])
        self.assertEqual([20, 25, 40], [row[1] for row in observed])
        self.assertEqual(1, len(audited))
        self.assertEqual('REGIME_ROUTING_REJECTED', audited[0]['event'])
        self.assertEqual(20, audited[0]['signal_index'])
        # Merely filtering the old ledger could never create the new signal25.
        filtered_old = [trade for trade in baseline['trades'] if trade['signal_index'] != 20]
        self.assertNotEqual([trade['signal_index'] for trade in filtered_old],
                            [trade['signal_index'] for trade in new['trades']])

    def test_real_uncertain_classifier_blocks_every_signal_even_when_model_route_is_all(self):
        cache = fixture_cache(count=130, signals=(20, 64, 80, 100))
        config = load_routing_config()
        config['models']['engulfing']['regimes'] = ['ALL']
        decisions, audited = [], []

        def gate(model, index, _card, _fold):
            history = cache['bars'][:index + 1]
            result = route_signal(model, history, 'H1', bar_close_time(history[-1]['time'], 'H1'), config=config)
            decisions.append(result)
            return result

        result = engine.replay_book(cache, 'engulfing', [fitted_fold(end=120)], start=20, end=120,
                                    signal_gate=gate, gate_audit=audited.append)
        self.assertEqual([], result['trades'])
        self.assertEqual([], result['censored'])
        self.assertEqual(4, len(result['rejected']))
        self.assertEqual(4, len(audited))
        self.assertTrue(all(row['regime'] == 'UNCERTAIN' and row['allowed'] is False for row in decisions))
        self.assertTrue(all('UNCERTAIN_CONTEXT_BLOCKED' in row['reasons'] for row in decisions))

    def test_every_veto_is_audited_with_exact_closed_signal_and_fold_identity(self):
        cache = fixture_cache(signals=(20, 25, 40))
        audit = []
        result = engine.replay_book(
            cache, 'engulfing', [fitted_fold(fold_id=7)], start=20, end=100,
            signal_gate=lambda *_args: {'allowed': False, 'regime': 'UNCERTAIN'}, gate_audit=audit.append)
        self.assertEqual(audit, result['rejected'])
        self.assertEqual([20, 25, 40], [row['signal_index'] for row in audit])
        for row in audit:
            self.assertEqual('engulfing', row['model_id'])
            self.assertEqual(7, row['fold_id'])
            self.assertEqual(bar_close_time(cache['bars'][row['signal_index']]['time'], 'H1'), row['signal_time'])
            self.assertEqual('UNCERTAIN', row['routing']['regime'])

    def test_audit_write_failure_propagates_and_no_later_signal_is_examined(self):
        cache = fixture_cache(signals=(20, 25, 40))
        called = []

        def gate(_model, index, _card, _fold):
            called.append(index)
            return {'allowed': False, 'regime': 'UNCERTAIN'}

        def failed_audit(_event):
            raise OSError('SYNTHETIC AUDIT DISK FAILURE')

        with self.assertRaisesRegex(OSError, 'AUDIT DISK FAILURE'):
            engine.replay_book(cache, 'engulfing', [fitted_fold()], start=20, end=100,
                               signal_gate=gate, gate_audit=failed_audit)
        self.assertEqual([20], called)

    def test_malformed_gate_results_and_gate_exceptions_never_become_implicit_permission(self):
        cache = fixture_cache(signals=(20,))
        for bad in (None, True, {}, {'allowed': 1}, {'allowed': 'yes'}):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, 'explicit boolean'):
                engine.replay_book(cache, 'engulfing', [fitted_fold()], start=20, end=100,
                                   signal_gate=lambda *_args, result=bad: result)

        def failure(*_args):
            raise RuntimeError('SYNTHETIC CONTEXT CALCULATION FAILURE')

        with self.assertRaisesRegex(RuntimeError, 'CONTEXT CALCULATION FAILURE'):
            engine.replay_book(cache, 'engulfing', [fitted_fold()], start=20, end=100, signal_gate=failure)

    def test_study_applies_gate_to_primary_and_diagnostic_windows_without_granting_authority(self):
        cache = fixture_cache(count=130, signals=(64, 70, 80, 90, 100))
        audit = []
        result = engine.run_study(
            cache, train=20, test=40, step=20, model_ids=['engulfing'],
            signal_gate=lambda *_args: {'allowed': False, 'regime': 'UNCERTAIN'}, gate_audit=audit.append)
        self.assertEqual({'PRIMARY_UNIQUE', 'OVERLAPPING_WINDOW_DIAGNOSTIC'}, {row['book'] for row in audit})
        self.assertEqual(5, sum(row['book'] == 'PRIMARY_UNIQUE' for row in audit))
        self.assertGreater(sum(row['book'] == 'OVERLAPPING_WINDOW_DIAGNOSTIC' for row in audit), 5)
        for scenario in result['scenarios']:
            self.assertEqual(0, scenario['models'][0]['trades'])
            self.assertEqual(0, scenario['models'][0]['net_r'])
            self.assertTrue(all(row['trades'] == 0 for row in scenario['models'][0]['window_metrics']))
        self.assertFalse(result['qualified'])
        self.assertFalse(result['execution_authority'])
