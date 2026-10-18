"""Versioned history controls across every model without lowering warm-up safety."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_registry_acceptance import REGISTRY_MODELS, scenario

from nexus import strategies as st


# Vulture review: unittest/pytest discovers and executes this TestCase by module inspection.
class ModelConfiguration(unittest.TestCase):
    def setUp(self):
        self.path=Path(st.__file__).parent/'config/models.yaml'
        self.profile=st.load_model_config(self.path)

    def test_all_58_have_default_minimum_maximum_and_pinned_rule_version(self):
        schema=json.loads(self.path.with_name('models.schema.json').read_text(encoding='utf-8'))
        self.assertEqual(58,len(self.profile['rules']))
        self.assertEqual(set(REGISTRY_MODELS),set(schema['properties']['rules']['required']))
        for sid,entry in self.profile['rules'].items():
            with self.subTest(model=sid):
                bounds=schema['properties']['rules']['properties'][sid]['properties']['min_bars']
                self.assertEqual(entry['min_bars'],bounds['default'])
                self.assertEqual(st.REGISTRY[sid]['min_bars'],bounds['minimum'])
                self.assertEqual(50000,bounds['maximum'])
                self.assertEqual(st.REGISTRY[sid]['version'],entry['rule_version'])
                width=schema['properties']['rules']['properties'][sid]['properties']['entry_zone_atr_fraction']
                self.assertEqual(.15,entry['entry_zone_atr_fraction'])
                self.assertEqual(.15,width['default'])
                self.assertEqual(.01,width['minimum'])
                self.assertEqual(.15,width['maximum'])

    def test_raising_minimum_changes_each_model_gate_and_revision_without_global_mutation(self):
        for sid in REGISTRY_MODELS:
            rows,tf,context=scenario(sid,'BUY')
            profile=copy.deepcopy(self.profile)
            profile['version']='1.0.1'
            profile['rules'][sid]['min_bars']=max(len(rows)+1,profile['rules'][sid]['min_bars'])
            with self.subTest(model=sid):
                original=st.analyze_strategy(sid,'FIXTURE',tf,rows,context['as_of'],context)
                configured=st.analyze_strategy(sid,'FIXTURE',tf,rows,context['as_of'],{**context,'model_config':profile})
                self.assertNotEqual('DATA_MISSING',original['status'])
                self.assertEqual('DATA_MISSING',configured['status'])
                self.assertFalse(configured['actionable'])
                self.assertNotEqual(original['id'],configured['id'])
                self.assertNotEqual(original['model_config']['revision'],configured['model_config']['revision'])
                self.assertEqual(self.profile,st.load_model_config(self.path))

    def test_invalid_bounds_types_versions_missing_and_unknown_models_are_rejected(self):
        sid=REGISTRY_MODELS[0]
        for value in (True,0,-1,1.5,50001,'65'):
            profile=copy.deepcopy(self.profile);profile['rules'][sid]['min_bars']=value
            with self.subTest(value=value),self.assertRaises(ValueError):st.validate_model_config(profile)
        for mutation in ('version','rule_version','missing','extra','schema','field'):
            p=copy.deepcopy(self.profile)
            if mutation=='version':p['version']='latest'
            elif mutation=='rule_version':p['rules'][sid]['rule_version']='old'
            elif mutation=='missing':p['rules'].pop(sid)
            elif mutation=='extra':p['rules']['unknown']=p['rules'][sid]
            elif mutation=='schema':p['schema_version']=True
            else:p['rules'][sid]['ignored_threshold']=1
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):st.validate_model_config(p)

    def test_duplicate_keys_rejected_and_canonical_hash_ignores_order(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'bad.json'
            path.write_text('{"schema_version":1,"schema_version":1}',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'Duplicate'):st.load_model_config(path)
        reordered={k:self.profile[k] for k in reversed(self.profile)}
        self.assertEqual(st.model_config_revision(self.profile),st.model_config_revision(reordered))

    def test_acquisition_and_replay_warmup_follow_configured_history(self):
        from nexus.engine import _analysis_bar_count
        from nexus.quant import replay
        rows,tf,context=scenario('ema_cross','BUY')
        profile=copy.deepcopy(self.profile)
        profile['version']='1.0.1'
        profile['rules']['ema_cross']['min_bars']=2000
        with patch.object(st,'_MODEL_CONFIG',profile):
            self.assertGreaterEqual(_analysis_bar_count('H1'),2000)
            self.assertEqual(2000,st.configured_minimum('ema_cross'))
            self.assertEqual([],replay(rows,'ema_cross',timeframe=tf,context=context)['trades'])

    def test_changed_profile_invalidates_cached_quant_certificate(self):
        from nexus.engine import PLAN_VERSION, Engine
        with tempfile.TemporaryDirectory() as directory:
            engine=Engine(Path(st.__file__).resolve().parents[2],Path(directory))
            try:
                engine._connect(True)
                now=engine.clock();old=engine._quant_config('GOLD#')
                certificate={'strategy_id':'ema_cross','version':st.REGISTRY['ema_cross']['version'],
                             'plan_version':PLAN_VERSION,'data_kind':'synthetic','symbol':'GOLD#','timeframe':'H1',
                             'cost_config_hash':engine._cost_hash(old),'checked_at':now,
                             'certificate_expires_at':now+3600,'data_time':now-1}
                self.assertTrue(engine._certificate_valid(certificate,'GOLD#','H1','ema_cross'))
                profile=copy.deepcopy(self.profile);profile['version']='1.0.1'
                profile['rules']['ema_cross']['min_bars']=2000
                with patch.object(st,'_MODEL_CONFIG',profile):
                    self.assertNotEqual(old['model_config_revision'],engine._quant_config('GOLD#')['model_config_revision'])
                    self.assertFalse(engine._certificate_valid(certificate,'GOLD#','H1','ema_cross'))
            finally:
                engine.stop_worker()
                if engine.store:engine.store.close()
                engine.cache.db.close();engine.news.db.close()

    def test_tightening_configured_zone_changes_the_real_fresh_quote_gate(self):
        from nexus.engine import Engine
        rows,tf,context=scenario('ema_cross','BUY')
        wide=st.analyze_strategy('ema_cross','FIXTURE',tf,rows,context['as_of'],context)
        profile=copy.deepcopy(self.profile);profile['version']='1.1.1'
        profile['rules']['ema_cross']['entry_zone_atr_fraction']=.05
        narrow=st.analyze_strategy('ema_cross','FIXTURE',tf,rows,context['as_of'],{**context,'model_config':profile})
        a=st.atr(rows);quote=wide['entry']['price']+.1*a
        with tempfile.TemporaryDirectory() as directory:
            engine=Engine(Path(st.__file__).resolve().parents[2],Path(directory),clock=lambda:context['as_of'])
            try:
                engine._connect(True);engine.broker.is_simulation=False
                engine.broker._prices['STOCK.A']=quote-engine.broker.symbol('STOCK.A')['point']
                engine.settings={'validation_policy':'forward_demo'}
                proposal={'id':'configured-zone','symbol':'STOCK.A','side':'BUY','strategy_id':'ema_cross',
                          'timeframe':tf,'validation_policy':'forward_demo','signal_validated':True,
                          'sl':wide['stop']['price'],'tp':wide['targets'][0]['price'],
                          'expires_at':wide['expires_at'],'entry_zone':wide['entry']['zone']}
                self.assertEqual(quote,engine._fresh_proposal(proposal)['entry'])
                with self.assertRaisesRegex(ValueError,'السعر خارج منطقة الدخول'):
                    engine._fresh_proposal({**proposal,'entry_zone':narrow['entry']['zone']})
                self.assertEqual([],engine.broker.sent)
            finally:
                engine.stop_worker()
                if engine.store:engine.store.close()
                engine.cache.db.close();engine.news.db.close()

    def test_zone_width_cannot_be_widened_or_malformed(self):
        for value in (0,.151,1,True,float('nan'),float('inf'),'0.15'):
            profile=copy.deepcopy(self.profile)
            profile['rules']['ema_cross']['entry_zone_atr_fraction']=value
            with self.subTest(value=value),self.assertRaises(ValueError):st.validate_model_config(profile)
