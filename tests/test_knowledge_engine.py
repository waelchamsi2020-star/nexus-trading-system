import copy
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from nexus.engine import Engine
from nexus.learning import load_library
from nexus.strategies import REGISTRY

ROOT=Path(__file__).resolve().parents[1]

# Vulture review: unittest/pytest discovers and executes this TestCase by module inspection.
class KnowledgeEngine(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.engine=Engine(ROOT,Path(self.tmp.name));self.engine._connect(True)
        self.addCleanup(self.close)
    def close(self):
        self.engine.stop_worker();self.engine.store.close();self.engine.news.db.close();self.engine.cache.db.close()
    def test_chart_records_rule_identity_and_export_contains_reference_and_memory(self):
        self.engine._action({'action':'chart','symbol':'GOLD#','timeframe':'M5'})
        cards=self.engine.chart['cards'];self.assertEqual({c['strategy_id'] for c in cards},set(REGISTRY))
        self.assertTrue(all(len(c['rule_revision'])==64 for c in cards))
        self.engine._update_learning(force=True)
        self.assertGreaterEqual(self.engine.learning_state['observations'],len(REGISTRY))
        self.assertEqual(self.engine.executor.status()['mode'],'READ_ONLY')
        result=self.engine._action({'action':'knowledge_export'})
        with zipfile.ZipFile(result['path']) as z:
            payload=json.loads(z.read('knowledge-learning.json'))
            self.assertIn('learning-state.json',z.namelist())
        self.assertEqual(len(payload['reference']),len(REGISTRY))
        self.assertEqual({r['id'] for r in payload['current_rules']},set(REGISTRY))
        self.assertTrue(payload['source_archive']['complete'])
        self.assertEqual(payload['learning_reference']['model_version'],'chart-logistic-v1')
        self.assertEqual(set(payload['learning_reference']['source_modules']),{'learning/__init__.py','learning/proposals.py','learning/sandbox.py','learning/drift_monitor.py','learning_journal.py','risk.py','store.py'})
        self.assertFalse(payload['learning_reference']['execution_authority'])
        self.assertFalse(payload['evaluation']['auto_changes'])
        def keys(value):
            if isinstance(value,dict):return list(value)+[key for child in value.values() for key in keys(child)]
            if isinstance(value,list):return [key for child in value for key in keys(child)]
            return []
        # Inert source copies may contain a function called account_key; no
        # account identity is exported as a data field.
        self.assertNotIn('account_key',keys(payload))
    def test_failed_history_fetch_keeps_evidence_and_reports_learning_error(self):
        self.engine._update_learning(force=True);original=dict(self.engine.learning_state)
        with patch.object(self.engine.broker,'deals',return_value=None):self.engine._update_learning(force=True)
        self.assertIn('unavailable',self.engine.learning_state['error'])
        self.assertEqual(self.engine.learning_state['closed_records'],original['closed_records'])
        self.engine._publish();self.assertTrue(self.engine.snapshot()['learning']['error'])
    def test_library_covers_all_current_rules_with_exact_source(self):
        library=load_library(ROOT);self.assertEqual(set(library),set(REGISTRY))
        for rule in library.values():
            self.assertTrue(rule['algorithm_python']);self.assertEqual(len(rule['revision']),64)
            self.assertFalse(rule['school_complete'])
            self.assertEqual(rule['learning_contract']['mode'],'SHADOW_ONLY')
            self.assertEqual(len(rule['learning_contract']['features']),8)
            self.assertFalse(rule['learning_contract']['legacy_feature_backfill'])

    def test_proposal_retains_detached_original_chart_features(self):
        self.engine.settings['validation_policy']='forward_demo'
        self.engine.scanner.rows['GOLD#']={'eligible':True}
        selected={}
        def proposal(cards,*args):
            card=next(c for c in cards if c.get('chart_features'))
            selected['card']=card
            return {'decision':'WAIT','proposals':[{'id':card['id'],'data_time':card['data_time']}],
                    'ranked':[],'reasons':[]}
        with patch('nexus.engine.decide',side_effect=proposal),patch.object(self.engine,'_rank'):
            self.engine._analyze_symbol('GOLD#')
        original=self.engine.decisions['GOLD#']['proposals'][0]
        feature=copy.deepcopy(original['chart_features'])
        self.assertEqual(feature,selected['card']['chart_features'])
        self.assertEqual(original['rule_revision'],selected['card']['rule_revision'])
        selected['card']['chart_features']['values']['return_1_atr']=1234
        self.assertEqual(original['chart_features'],feature)
        self.assertEqual(self.engine.executor.status()['mode'],'READ_ONLY')

    def test_tampered_learning_source_reference_cannot_be_exported(self):
        read=Path.read_text
        def altered(path,*args,**kwargs):
            content=read(path,*args,**kwargs)
            if path.name=='learning-reference.json':
                document=json.loads(content);document['policy']['iterations']+=1
                return json.dumps(document)
            return content
        with patch.object(Path, 'read_text', new=altered), self.assertRaisesRegex(ValueError, 'Learning reference fingerprint mismatch'):
            self.engine._export_knowledge()

    def test_learning_integrity_error_precedes_other_export_reference_errors(self):
        read=Path.read_text
        def altered(path,*args,**kwargs):
            content=read(path,*args,**kwargs)
            if path.name=='learning-reference.json':
                document=json.loads(content);document['policy']['iterations']+=1
                return json.dumps(document)
            return content
        with patch.object(Path,'read_text',new=altered), patch.object(
                self.engine,'_load_multi_reference',side_effect=ValueError('Multi-school execution source changed: store.py')) as multi:
            with self.assertRaisesRegex(ValueError,'Learning reference fingerprint mismatch'):
                self.engine._export_knowledge()
            multi.assert_not_called()

    def test_valid_learning_reference_does_not_disable_multi_school_guard(self):
        with patch.object(self.engine,'_load_multi_reference',side_effect=ValueError('Multi-school execution source changed: store.py')), self.assertRaisesRegex(ValueError,'Multi-school execution source changed: store.py'):
            self.engine._export_knowledge()
