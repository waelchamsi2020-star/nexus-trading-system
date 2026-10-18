import copy
import unittest

from test_registry_acceptance import REGISTRY_MODELS, scenario

from nexus import strategies as st
from nexus.model_phases import SetupTracker
from nexus.timeframes import bar_close_time


# Vulture review: unittest/pytest discovers and executes this TestCase by module inspection.
class ModelPhases(unittest.TestCase):
    def card(self,sid):
        rows,tf,context=scenario(sid,'BUY')
        return st.analyze_strategy(sid,'FIXTURE',tf,rows,context['as_of'],context),rows[-1]

    def test_all_executable_models_setup_armed_structural_invalidation_is_terminal(self):
        families=set()
        for sid in REGISTRY_MODELS:
            if sid=='four_school_confluence':continue
            card,last=self.card(sid);families.add(card['evidence_group'])
            with self.subTest(model=sid,family=card['evidence_group']):
                tracker=SetupTracker(card)
                self.assertEqual('SETUP',tracker.phase)
                self.assertEqual('ARMED',tracker.arm(card['valid_at']))
                level=card['invalidation']['price']
                close=level*.999
                bar=dict(last,time=card['data_time'],open=level,close=close,high=level*1.001,low=close*.999)
                at=bar_close_time(bar['time'],card['timeframe'])
                self.assertEqual('INVALIDATED',tracker.observe(bar,at))
                self.assertEqual('INVALIDATED',tracker.observe(bar,at+1000))
                with self.assertRaises(ValueError):tracker.arm(at+1000)
                self.assertFalse(tracker.snapshot()['execution_authority'])
        self.assertEqual({st.REGISTRY[sid]['evidence_group'] for sid in REGISTRY_MODELS},families)

    def test_all_executable_models_expire_without_inventing_invalidation(self):
        for sid in REGISTRY_MODELS:
            if sid=='four_school_confluence':continue
            card,last=self.card(sid)
            with self.subTest(model=sid):
                tracker=SetupTracker(card);tracker.arm(card['valid_at'])
                price=max(last['close'],card['invalidation']['price'])*1.01
                bar=dict(last,time=card['data_time'],open=price,high=price*1.001,low=price*.999,close=price)
                self.assertEqual('EXPIRED',tracker.observe(bar,card['expires_at']))
                self.assertEqual(['SETUP','ARMED','EXPIRED'],[x['phase'] for x in tracker.events])

    def test_advisory_card_cannot_arm_and_input_history_is_detached(self):
        card,_=self.card('four_school_confluence');tracker=SetupTracker(card)
        with self.assertRaises(ValueError):tracker.arm(card['valid_at'])
        before=copy.deepcopy(tracker.card);card['status']='READY';card['actionable']=True
        self.assertEqual(before,tracker.card)

    def test_future_and_rewritten_candles_and_backward_clock_are_rejected(self):
        card,last=self.card('ema_cross');tracker=SetupTracker(card);tracker.arm(card['valid_at'])
        with self.assertRaises(ValueError):tracker.observe(dict(last,time=card['expires_at']),card['valid_at'])
        with self.assertRaises(ValueError):tracker.arm(card['valid_at']-1)
        tracker.observe(last,card['valid_at'])
        with self.assertRaises(ValueError):tracker.observe(dict(last,tick_volume=12345),card['valid_at'])

    def test_rejected_event_does_not_advance_clock_and_duplicate_can_expire(self):
        card,last=self.card('ema_cross');tracker=SetupTracker(card);tracker.arm(card['valid_at'])
        before=tracker.snapshot()
        with self.assertRaises(ValueError):
            tracker.observe(dict(last,time=card['expires_at']),card['valid_at']+1)
        self.assertEqual(before,tracker.snapshot())
        tracker.observe(last,card['valid_at'])
        self.assertEqual('EXPIRED',tracker.observe(last,card['expires_at']))
