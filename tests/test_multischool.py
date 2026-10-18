"""Synthetic coordinator checks of multi-school authority; no actual MT5 orders."""
import copy
import hashlib
import json
import unittest
from unittest.mock import patch

import test_engine_confluence as fixtures

from nexus import multischool, strategies
from nexus.learning import digest
from nexus.risk import protocol_certificate_hash

ROOT=fixtures.ROOT

class MultiSchoolTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.EngineConfluenceTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.engine=self.fixture.engine;self.now=self.fixture.now
        ref={'schema':1,'definition':multischool.DEFINITION,'modules':{}}
        for name in multischool.MODULES:
            blob=(ROOT/'src/nexus'/name).read_bytes();dest=self.engine.root/'src/nexus'/name
            dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(blob)
            ref['modules'][name]=hashlib.sha256(blob).hexdigest()
        ref['revision']=digest(ref)
        (self.engine.root/'docs/knowledge/multi-school-reference.json').write_text(json.dumps(ref),encoding='utf-8')
        self.profiles={'fast':{'enabled':True,'target_value':100,'risk_percent':1,'profit_percent':2,'min_reward_risk':2}}

    def start(self):
        self.fixture.start(decision_protocol='multi_school_v1',scalping=self.profiles,scalp_only=True)
        # Activation changes the spread policy and invalidates the old scan.
        # Drive the coordinator's fresh scan before evaluating fixture entries.
        self.engine.scanner.step(99)

    def test_fast_authorization_rescans_under_waived_spread_policy(self):
        self.fixture.start(decision_protocol='multi_school_v1',scalping=self.profiles,scalp_only=True)
        self.assertFalse(self.engine.scanner.spread_filter)
        self.assertFalse(self.engine.scanner.snapshot()['complete'])
        self.assertTrue(self.engine.scanner.queue)
        self.assertEqual(self.engine.broker.sent,[])

    def test_default_target_is_independent_of_display_language(self):
        for method in ('2 * proposed stop distance', multischool.arabic('2 * proposed stop distance'), 'custom display text'):
            for side in ('BUY', 'SELL'):
                sign=1 if side=='BUY' else -1
                card={'actionable':True,'direction':side,'entry':{'price':100},'stop':{'price':100-sign},
                      'targets':[{'price':100+2*sign,'method':method}]}
                if method=='custom display text':card['targets'][0]['method_code']='DEFAULT_STRUCTURAL_2R'
                original=copy.deepcopy(card)
                with patch('nexus.multischool.decide',return_value={}) as route:
                    multischool.decision([card],{},self.now,{})
                target=route.call_args.args[0][0]['targets'][0]
                self.assertEqual(target['price'],100+3*sign)
                self.assertEqual(target['method_code'],'MULTI_STRUCTURAL_3R')
                self.assertEqual(card,original)

    def test_model_specific_target_is_not_extended(self):
        card={'actionable':True,'direction':'BUY','entry':{'price':100},'stop':{'price':99},
              'targets':[{'price':101.5,'method':'model-specific resistance'}]}
        with patch('nexus.multischool.decide',return_value={}) as route:
            multischool.decision([card],{},self.now,{})
        self.assertEqual(route.call_args.args[0][0],card)

    def preflight_bars(self):
        return [{'time':self.now-(32-i)*60,'open':1.08,'high':1.081,'low':1.079,
                 'close':1.08,'tick_volume':100} for i in range(32)]

    def test_news_hard_gate_skips_heavy_models_and_recovers_on_next_visit(self):
        self.start();self.engine.settings['fast_profit_protection']=True
        trend={tf:{'direction':'BUY'} for tf in ('M15','H1')}
        result={'proposals':[],'ranked':[],'as_of':self.now,'expires_at':self.now,'decision':'WAIT','reasons':[]}
        with patch.object(self.engine,'_multi_fast_preflight',return_value=None), \
             patch.object(self.engine.news,'gate',side_effect=[{'ok':False,'blackout':True},{'ok':True,'blackout':False}]), \
             patch.object(self.engine,'_cash_trend_context',return_value=trend), \
             patch.object(self.engine,'_multi_result',return_value=result) as models,patch.object(self.engine,'_rank'):
            self.assertFalse(self.engine._multi_analyze_symbol(self.fixture.symbol))
            models.assert_not_called()
            self.assertFalse(self.engine._multi_analyze_symbol(self.fixture.symbol))
            models.assert_called_once_with(self.fixture.symbol)
        self.assertEqual(self.engine.broker.sent,[])

    def test_disagreeing_or_neutral_trends_cannot_use_heavy_fast_lane(self):
        self.start();self.engine.settings['fast_profit_protection']=True
        for directions in (('BUY','SELL'),('NEUTRAL','NEUTRAL'),('BUY','NEUTRAL')):
            with self.subTest(directions=directions), \
                 patch.object(self.engine.news,'gate',return_value={'ok':True,'blackout':False}), \
                 patch.object(self.engine,'_cash_trend_context',return_value={tf:{'direction':side} for tf,side in zip(('M15','H1'),directions)}):
                result=self.engine._multi_fast_hard_gate(self.fixture.symbol)
                self.assertEqual(result['proposals'],[])
                self.assertEqual(result['analysis_deferred']['stage'],'existing_mandatory_entry_gates')
        self.assertEqual(self.engine.broker.sent,[])

    def test_hard_gate_does_not_change_non_cash_or_non_fast_policy(self):
        self.start()
        with patch.object(self.engine.news,'gate',side_effect=AssertionError('Unexpected policy shortcut')):
            self.assertIsNone(self.engine._multi_fast_hard_gate(self.fixture.symbol))
            self.engine.settings['fast_profit_protection']=True
            self.engine.settings['scalp_only']=False
            self.assertIsNone(self.engine._multi_fast_hard_gate(self.fixture.symbol))

    def test_fast_preflight_leaves_zone_choice_to_agent(self):
        self.start()
        with patch.object(self.engine.broker,'bars',return_value=self.preflight_bars()), \
             patch.object(self.engine.broker,'tick',return_value={'time':self.now,'bid':1.09,'ask':1.0901}):
            self.assertIsNone(self.engine._multi_fast_preflight(self.fixture.symbol))
        self.assertEqual(self.engine.broker.sent,[])

    def test_fast_preflight_allows_either_side_inside_original_zone(self):
        self.start()
        for bid,ask in ((1.08,1.0801),(1.0796,1.08)):
            with patch.object(self.engine.broker,'bars',return_value=self.preflight_bars()), \
                 patch.object(self.engine.broker,'tick',return_value={'time':self.now,'bid':bid,'ask':ask}):
                self.assertIsNone(self.engine._multi_fast_preflight(self.fixture.symbol))

    def test_fast_preflight_rechecks_quotes_on_same_completed_bar(self):
        self.start()
        quotes=[{'time':self.now,'bid':1.09,'ask':1.0901},{'time':self.now,'bid':1.08,'ask':1.0801}]
        with patch.object(self.engine.broker,'bars',return_value=self.preflight_bars()), \
             patch.object(self.engine.broker,'tick',side_effect=quotes):
            self.assertIsNone(self.engine._multi_fast_preflight(self.fixture.symbol))
            self.assertIsNone(self.engine._multi_fast_preflight(self.fixture.symbol))

    def test_fast_preflight_never_accepts_stale_or_future_quotes(self):
        self.start()
        for stamp in (self.now-16,self.now+1):
            with patch.object(self.engine.broker,'bars',return_value=self.preflight_bars()), \
                 patch.object(self.engine.broker,'tick',return_value={'time':stamp,'bid':1.08,'ask':1.0801}):
                self.assertIsNotNone(self.engine._multi_fast_preflight(self.fixture.symbol))

    def test_cache_retains_context_for_more_than_32_symbols(self):
        self.start()
        self.engine.scanner.rows.update({f'fixture-{i}':{} for i in range(50)})
        self.engine._multi_card_cache={(f'old-{i}','M5'):('unused',[]) for i in range(110)}
        self.engine._multi_cards(self.fixture.symbol)
        self.assertGreater(len(self.engine._multi_card_cache),96)
        self.assertLessEqual(len(self.engine._multi_card_cache),len(self.engine.scanner.rows)*3)

    def test_activation_requires_current_multi_source_manifest(self):
        self.start();self.assertTrue(self.engine._fast_enabled())
        p=self.engine.root/'src/nexus/multischool.py';p.write_text('changed',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'source changed'):self.start()

    def test_all_agents_and_small_timeframes_are_observed_without_broker_send(self):
        self.start();cards,books=self.engine._multi_cards(self.fixture.symbol)
        self.assertEqual(set(books),{'M1','M5','M15'})
        self.assertEqual(len(cards),len(books)*len(self.engine.rule_library))
        self.assertEqual({c['strategy_id'] for c in cards},set(self.engine.rule_library))
        self.assertEqual(self.engine.broker.sent,[])
        result=self.engine._multi_result(self.fixture.symbol)
        self.assertEqual(len(result['school_participation']),len(self.engine.rule_library))
        self.assertEqual(result['decision_protocol'],'multi_school_v1')

    def test_multi_certificate_has_independent_identity_and_tamper_veto(self):
        self.start()
        p={'decision_protocol':'multi_school_v1','protocol_revision':multischool.PROTOCOL_REVISION,
           'decision_matrix':{'passed':True},'symbol':self.fixture.symbol,'requested_profit_percent':2}
        p['decision_matrix']['certificate_hash']=protocol_certificate_hash(p)
        self.engine.risk.validate_protocol_certificate(p)
        p['requested_profit_percent']=3
        with self.assertRaisesRegex(ValueError,'certificate'):self.engine.risk.validate_protocol_certificate(p)
        p['decision_protocol']='four_school_v1'
        with self.assertRaisesRegex(ValueError,'identity'):self.engine.risk.validate_protocol_certificate(p)

    def test_quote_changes_do_not_recompute_closed_bar_models(self):
        self.start()
        with patch('nexus.multischool.analyze_all',wraps=multischool.analyze_all) as analyze:
            self.engine._multi_cards(self.fixture.symbol)
            first=analyze.call_count
            self.assertEqual(first,3)
            original=self.engine.broker.symbol
            def changed(symbol):return {**original(symbol),'bid':1.081,'ask':1.082}
            with patch.object(self.engine.broker,'symbol',side_effect=changed):
                self.engine._multi_cards(self.fixture.symbol)
            self.assertEqual(analyze.call_count,first)

    def test_committee_cannot_invent_signal_when_all_models_wait_or_missing(self):
        self.start();cards,_=self.engine._multi_cards(self.fixture.symbol)
        for c in cards:c.update(status='WAIT',actionable=False)
        result=multischool.decision(cards,{},self.now,{})
        self.assertFalse(result['proposals'])
        self.assertEqual(self.engine.broker.sent,[])

    def fixture_cards(self,symbol,tf,bars,now,context):
        common={'symbol':symbol,'quality':'VALIDATED_OHLC','coverage':'IMPLEMENTED','version':'1.0.0',
          'data_time':self.now-1,'expires_at':self.now+59,'news_requirements':['calendar'],
          'conditions_met':['explicit synthetic fixture condition'],'conditions_missing':[],
          'direction':'BUY','score':90,'timeframe':tf,'evidence':[],
          'invalidation':{'price':1.075},'execution_plan':{'timeframe':tf,'max_hold_bars':12},
          'targets':[{'price':1.095,'method':'explicit fixture target'}]}
        if tf=='M1':return [{**common,'id':'multi-fixture-entry','strategy_id':'engulfing','evidence_group':'candle',
          'status':'READY','actionable':True,'entry':{'price':1.08,'zone':[1.079,1.081],'triggered':True},'stop':{'price':1.075}},
          {**common,'id':'multi-fixture-M1-support','strategy_id':'ema_cross','evidence_group':'trend',
           'status':'WAIT','actionable':False,'entry':None,'stop':None}]
        if tf=='M5':return [{**common,'id':'multi-fixture-support','strategy_id':'ema_cross','evidence_group':'trend',
          'status':'WAIT','actionable':False,'entry':None,'stop':None}]
        return []

    def test_multi_signal_reaches_single_synthetic_sender_without_ict_chain(self):
        self.start()
        self.engine.running=True
        # This synthetic model fixture declares its own wider zone; the actual
        # fixed-zone preflight is covered separately against broker bar fixtures.
        with patch.object(self.engine,'_multi_fast_preflight',return_value=None),patch('nexus.multischool.analyze_all',side_effect=self.fixture_cards),patch('nexus.confluence._ict',side_effect=AssertionError('ICT chain must not be mandatory')):
            self.engine._multi_analyze_symbol(self.fixture.symbol)
            self.assertTrue(self.engine.decisions[self.fixture.symbol]['proposals'],self.engine.decisions[self.fixture.symbol])
            self.engine._trade_candidates(fast_only=True)
            self.engine._trade_candidates(fast_only=True)
        self.assertEqual(len(self.engine.broker.sent),1,self.engine.opportunities)
        saved=self.engine.store.intents()[0]
        self.assertLessEqual(saved['reserved'],10)
        self.assertEqual(saved['payload']['proposal']['decision_protocol'],'multi_school_v1')
        self.assertEqual(saved['payload']['proposal']['execution_style'],'SCALP')

    def test_matrix_records_each_actual_model_without_inventing_neutral_votes(self):
        self.start()
        with patch('nexus.multischool.analyze_all',side_effect=self.fixture_cards):
            result=self.engine._multi_result(self.fixture.symbol)
        self.assertTrue(result['proposals'],result)
        matrix=result['proposals'][0]['decision_matrix']
        rows=matrix['school_evidence']
        self.assertEqual({row['strategy_id'] for row in rows},{'engulfing','ema_cross'})
        selected=next(row for row in rows if row['role']=='ENTRY_TRIGGER')
        context=next(row for row in rows if row['strategy_id']=='ema_cross')
        self.assertEqual(selected['direction'],'BUY')
        self.assertEqual(context['status'],'WAIT')
        self.assertEqual(context['role'],'SUPPORTING')
        self.assertNotIn('volume_profile',matrix)
        self.engine.cards_by_symbol[self.fixture.symbol][0]['direction']='SELL'
        self.assertEqual(selected['direction'],'BUY')
        self.assertEqual(self.engine.broker.sent,[])

    def test_strong_m1_opposing_families_can_select_sell(self):
        self.start()
        def cards(*args):
            result=self.fixture_cards(*args)
            if args[1]=='M1':
                template=result[0]
                result.extend([{**template,'id':'sell-candle','strategy_id':'pin_rejection','evidence_group':'candle',
                  'direction':'SELL','score':100,'entry':{'price':1.08,'zone':[1.079,1.081],'triggered':True},
                  'stop':{'price':1.085},'targets':[{'price':1.065}]},
                  {**template,'id':'sell-transform','strategy_id':'rsi_rebound','evidence_group':'momentum',
                  'version':strategies.REGISTRY['rsi_rebound']['version'],
                  'direction':'SELL','score':100,'entry':{'price':1.08,'zone':[1.079,1.081],'triggered':True},
                  'stop':{'price':1.085},'targets':[{'price':1.065}]}])
            return result
        with patch('nexus.multischool.analyze_all',side_effect=cards):
            result=self.engine._multi_result(self.fixture.symbol)
        self.assertEqual(len(result['proposals']),1)
        self.assertEqual(result['proposals'][0]['side'],'SELL')
        self.assertEqual(self.engine.broker.sent,[])

    def test_agent_can_accept_one_minority_opposing_model(self):
        self.start()
        def cards(*args):
            result=self.fixture_cards(*args)
            if args[1]=='M1':result.append({**result[0],'id':'minority-sell','strategy_id':'pin_rejection',
                'direction':'SELL','entry':{'price':1.08,'zone':[1.079,1.081],'triggered':True},
                'stop':{'price':1.085},'targets':[{'price':1.065}]})
            return result
        with patch('nexus.multischool.analyze_all',side_effect=cards):result=self.engine._multi_result(self.fixture.symbol)
        self.assertEqual(result['proposals'][0]['side'],'BUY')
        self.assertEqual(result['proposals'][0]['decision_matrix']['entry_policy'],'autonomous_M1')

    def test_agent_still_needs_independent_m1_evidence(self):
        self.start()
        def cards(*args):return self.fixture_cards(*args)[:1]
        with patch('nexus.multischool.analyze_all',side_effect=cards):result=self.engine._multi_result(self.fixture.symbol)
        self.assertFalse(result['proposals'])
        self.assertEqual(self.engine.broker.sent,[])

    def test_actual_net_cost_check_replaces_stop_spread_heuristic(self):
        self.start()
        quote={'time':self.now,'bid':1.078,'ask':1.08}
        with patch('nexus.multischool.analyze_all',side_effect=self.fixture_cards),patch.object(self.engine.broker,'tick',return_value=quote):
            result=self.engine._multi_result(self.fixture.symbol)
        self.assertTrue(result['proposals'],result)
        p=result['proposals'][0]
        self.assertGreater((quote['ask']-quote['bid'])/abs(1.08-p['sl']),.2)
        self.assertGreaterEqual(float(p['decision_matrix']['net_rr_preview']['net_reward_risk']),2)

    def test_agent_cannot_waive_minimum_net_reward_risk(self):
        self.start()
        def cards(*args):
            result=self.fixture_cards(*args)
            if args[1]=='M1':result[0]['targets']=[{'price':1.086,'method':'bounded fixture target'}]
            return result
        with patch('nexus.multischool.analyze_all',side_effect=cards):result=self.engine._multi_result(self.fixture.symbol)
        self.assertFalse(result['proposals'])
        self.assertTrue(any('MULTI_EXECUTION_GATE' in r['reason_codes'] for r in result['ranked']))
        self.assertEqual(self.engine.broker.sent,[])

    def test_schools_cannot_duplicate_same_symbol_bar(self):
        self.start();self.engine.running=True
        def cards(*args):
            result=self.fixture_cards(*args)
            if args[1]=='M1':result.append({**result[0],'id':'same-buy-other-school','strategy_id':'pin_rejection'})
            return result
        with patch.object(self.engine,'_multi_fast_preflight',return_value=None),patch('nexus.multischool.analyze_all',side_effect=cards):
            result=self.engine._multi_result(self.fixture.symbol)
            self.assertEqual(len(result['proposals']),1)
            self.engine._multi_analyze_symbol(self.fixture.symbol);self.engine._trade_candidates(fast_only=True)
            after=self.engine._multi_result(self.fixture.symbol)
        self.assertEqual(len(self.engine.broker.sent),1)
        self.assertFalse(after['proposals'])

if __name__=='__main__':unittest.main()
