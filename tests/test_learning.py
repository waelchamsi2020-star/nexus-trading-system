"""Learning memory is a research ledger, never an execution-policy authority.

Broker fixtures below exercise attribution and accounting; their returns are
synthetic unit evidence and do not establish any trading performance.
"""
import copy
import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace

from nexus.learning import (
    LearningMemory,
    digest,
    knowledge_export_sources,
    load_library,
)
from nexus.risk import MAGIC, comment_for
from nexus.store import Store


def rule(version='1.0.0'):
    value={'id':'fixture_rule','version':version,'scope':'A bounded test definition'}
    return {**value,'revision':digest(value)}


def intent(index=1, account='A', reference=None, state='CLOSED', risk=10):
    reference=reference or rule()
    identity=hashlib.sha256(f'fixture intent {index}'.encode()).hexdigest()
    return {'id':identity,'fixture_index':index,'account_key':account,'kind':'ENTRY','state':state,'reserved':0,
            'payload':{'confirmed':True,'original_risk':risk,'position_ids':[1000+index],
                       'result':{'order':2000+index},'proposal':{
                           'strategy_id':reference['id'],'strategy_version':reference['version'],
                           'rule_revision':reference['revision'],'symbol':'TEST','timeframe':'H1',
                           'market_regime':'TREND','side':'BUY'}}}


def fills(item, result=20, closed_at=500):
    index=item['fixture_index']
    shared={'symbol':'TEST','magic':MAGIC,'position_id':1000+index,
            'comment':comment_for(item['id']),'commission':0.,'fee':0.,'swap':0.,'volume':1.}
    return [{**shared,'ticket':index*10+1,'order':2000+index,'type':0,'entry':0,
             'profit':0.,'time':closed_at-10},
            {**shared,'ticket':index*10+2,'order':3000+index,'type':1,'entry':1,
             'profit':float(result),'time':closed_at}]


class LearningTests(unittest.TestCase):
    def setUp(self):
        self.store=Store(':memory:')
        self.addCleanup(self.store.close)
        self.reference=rule()
        self.memory=LearningMemory(self.store,{self.reference['id']:self.reference})

    def ingest(self,item=None,deals=None,account='A',simulation=False):
        item=item or intent(reference=self.reference)
        self.memory.ingest(account,[item],fills(item) if deals is None else deals,10000,simulation)
        return self.memory.export(account)

    def revisions(self):
        return self.store.db.execute('SELECT COUNT(*) FROM learning_outcome_revisions').fetchone()[0]

    def test_reference_hash_and_defensive_copy_are_enforced(self):
        damaged=copy.deepcopy(self.reference);damaged['scope']='silently changed'
        with self.assertRaisesRegex(ValueError,'fingerprint'):
            LearningMemory(self.store,{damaged['id']:damaged})
        self.reference['version']='caller rewrite'
        self.assertEqual(self.memory.library['fixture_rule']['version'],'1.0.0')
        self.assertEqual(self.memory.export('A')['reference'][0]['version'],'1.0.0')

    def test_corrupted_stored_reference_cannot_be_reused(self):
        self.store.db.execute('UPDATE knowledge_versions SET payload=?',(json.dumps(dict(self.reference,version='tampered')),))
        with self.assertRaisesRegex(ValueError,'fingerprint'):
            LearningMemory(self.store,{'fixture_rule':self.reference})
        with self.assertRaisesRegex(ValueError,'fingerprint'):
            self.ingest()
        with self.assertRaisesRegex(ValueError,'fingerprint'):
            self.memory.export('A')

    def test_export_rejects_stored_rule_identity_mismatch(self):
        self.store.db.execute('UPDATE knowledge_versions SET rule_id=?',('different_rule',))
        with self.assertRaisesRegex(ValueError,'identity mismatch'):
            self.memory.export('A')

    def test_rule_key_cannot_alias_another_identity(self):
        with self.assertRaisesRegex(ValueError,'identity'):
            LearningMemory(self.store,{'other_id':self.reference})

    def test_observation_dedup_is_bar_revision_and_account_scoped(self):
        card={'strategy_id':'fixture_rule','symbol':'TEST','timeframe':'H1','data_time':100,
              'status':'WAIT','direction':'NONE','conditions_missing':['trigger'],'score':0}
        self.memory.observe('A',[card],200)
        self.assertEqual(card['rule_revision'],self.reference['revision'])
        changed=dict(card,status='READY',score=99)
        self.memory.observe('A',[changed],201)
        self.memory.observe('B',[changed],201)
        self.memory.observe('A',[dict(changed,data_time=101)],202)
        self.assertEqual(self.memory.snapshot('A')['observations'],2)
        self.assertEqual(self.memory.snapshot('B')['observations'],1)
        saved=json.loads(self.store.db.execute('SELECT payload FROM rule_observations WHERE account=? ORDER BY at LIMIT 1',('A',)).fetchone()[0])
        self.assertEqual(saved['status'],'WAIT')
        self.assertEqual(self.memory.snapshot('A')['closed_records'],0)

    def test_unknown_observed_rules_are_not_given_a_false_revision(self):
        self.memory.observe('A',[{'strategy_id':'unknown','symbol':'TEST','data_time':1}],2)
        self.assertEqual(self.memory.snapshot('A')['observations'],0)

    def test_one_closed_owned_versioned_fill_is_a_realized_label(self):
        data=self.ingest()
        self.assertEqual(data['evaluation']['eligible_records'],1)
        self.assertEqual(data['outcomes'][0]['net_r'],2.)
        self.assertEqual(data['outcomes'][0]['exclusions'],[])
        self.assertEqual(data['evaluation']['models'][0]['status'],'INSUFFICIENT')

    def test_no_label_for_open_partial_unconfirmed_or_missing_fills(self):
        for state,confirmed,count in [('FILLED',True,2),('PARTIAL',True,2),('CLOSED',False,2),('CLOSED',True,1)]:
            with self.subTest(state=state,confirmed=confirmed,count=count):
                item=intent(reference=self.reference,state=state);item['payload']['confirmed']=confirmed
                self.assertEqual(self.ingest(item,fills(item)[:count])['evaluation']['closed_records'],0)

    def test_partial_exit_overclose_and_reversal_cannot_label(self):
        for volume,entry in [(0.5,1),(1.5,1),(1.,2)]:
            with self.subTest(volume=volume,entry=entry):
                item=intent(reference=self.reference);deals=fills(item);deals[-1].update(volume=volume,entry=entry)
                self.assertEqual(self.ingest(item,deals)['evaluation']['eligible_records'],0)

    def test_volume_must_balance_each_position_not_only_total(self):
        item=intent(reference=self.reference);deals=fills(item)
        item['payload']['position_ids'].append(999)
        deals[-1]['position_id']=999
        self.assertEqual(self.ingest(item,deals)['evaluation']['closed_records'],0)

    def test_nonfinite_nonpositive_volume_future_or_incoherent_fill_cannot_label(self):
        changes=[{'volume':0},{'volume':True},{'volume':float('nan')},{'volume':float('inf')},
                 {'time':0},{'time':10001},{'symbol':'OTHER'},{'type':0}]
        for change in changes:
            with self.subTest(change=change):
                item=intent(reference=self.reference);deals=fills(item);deals[-1].update(change)
                self.assertEqual(self.ingest(item,deals)['evaluation']['eligible_records'],0)

    def test_lost_broker_history_revokes_current_label_keeps_revision_audit(self):
        item=intent(reference=self.reference)
        self.ingest(item)
        self.assertEqual(self.revisions(),1)
        self.assertEqual(self.ingest(item,[])['evaluation']['eligible_records'],0)
        self.assertEqual(self.revisions(),2)
        self.assertTrue(any(r.get('revoked') for r in self.memory.export('A')['outcome_correction_history']))
        self.assertEqual(self.ingest(item)['evaluation']['eligible_records'],1)
        self.assertEqual(self.revisions(),2)

    def test_entry_and_exit_fees_swap_and_late_linked_fee_reconcile(self):
        item=intent(reference=self.reference);deals=fills(item,result=20)
        deals[0].update(commission=-2,fee=-1)
        deals[1].update(commission=-2,swap=-1)
        first=self.ingest(item,deals)
        self.assertEqual(first['outcomes'][0]['net'],14.)
        late={'ticket':99,'order':2001,'position_id':1001,'type':7,'magic':0,
              'profit':-3,'commission':0,'fee':0,'swap':0,'time':600,'comment':''}
        second=self.ingest(item,deals+[late])
        self.assertEqual(second['outcomes'][0]['net_r'],1.1)
        self.assertEqual(second['evaluation']['eligible_records'],1)
        self.assertEqual(self.revisions(),2)

    def test_repeated_and_reordered_deals_do_not_create_learning_revisions(self):
        item=intent(reference=self.reference);deals=fills(item)
        first=self.ingest(item,deals)
        second=self.ingest(item,list(reversed(deals))+deals)
        self.assertEqual(first['outcomes'],second['outcomes'])
        self.assertEqual(self.revisions(),1)

    def test_conflicting_broker_ticket_fails_without_altering_previous_label(self):
        item=intent(reference=self.reference);deals=fills(item)
        self.ingest(item,deals)
        with self.assertRaisesRegex(ValueError,'Conflicting'):
            self.ingest(item,deals+[dict(deals[-1],profit=999)])
        self.assertEqual(self.memory.snapshot('A')['eligible_records'],1)
        self.assertEqual(self.revisions(),1)

    def test_unversioned_and_wrong_versions_are_recorded_but_never_learned(self):
        changes=[{'rule_revision':None},{'strategy_version':'other'},
                 {'strategy_id':'other'},{'rule_revision':'unregistered'}]
        for change in changes:
            with self.subTest(change=change):
                item=intent(reference=self.reference);item['payload']['proposal'].update(change)
                data=self.ingest(item)
                self.assertEqual(data['evaluation']['excluded_records'],1)
                self.assertIn('legacy_or_mismatched_rule',data['outcomes'][0]['exclusions'])

    def test_invalid_risk_and_synthetic_results_are_excluded(self):
        for risk in [0,-1,True,'10',float('nan'),float('inf'),1e-320]:
            with self.subTest(risk=risk):
                data=self.ingest(intent(reference=self.reference,risk=risk))
                self.assertEqual(data['evaluation']['eligible_records'],0)
                self.assertIn('invalid_initial_risk',data['outcomes'][0]['exclusions'])
        data=self.ingest(simulation=True)
        self.assertIn('synthetic_results',data['outcomes'][0]['exclusions'])
        self.assertEqual(data['evaluation']['eligible_records'],0)

    def test_foreign_magic_does_not_become_owned_even_when_order_matches(self):
        item=intent(reference=self.reference);deals=fills(item)
        deals[-1]['magic']=111
        self.assertEqual(self.ingest(item,deals)['evaluation']['closed_records'],0)

    def test_unallocated_and_unknown_costs_exclude_known_labels(self):
        for typ in (7,99):
            with self.subTest(typ=typ):
                item=intent(reference=self.reference);deals=fills(item)
                deals.append({'ticket':98,'type':typ,'magic':0,'profit':-2,'time':600})
                data=self.ingest(item,deals)
                self.assertEqual(data['evaluation']['eligible_records'],0)
                self.assertIn('unresolved_cost_attribution',data['outcomes'][0]['exclusions'])

    def test_ambiguous_position_link_cannot_train_either_owner(self):
        first=intent(1,reference=self.reference);second=intent(2,reference=self.reference)
        second['payload']['position_ids']=first['payload']['position_ids'][:]
        deals=fills(first)+fills(second)
        self.memory.ingest('A',[first,second],deals,10000)
        self.assertEqual(self.memory.snapshot('A')['eligible_records'],0)

    def test_account_isolation_and_no_risk_or_execution_mutation(self):
        self.store.ensure_day('A',50,100,1000,1000)
        self.store.halt_day('A','preserved halt',1000)
        before=list(self.store.db.iterdump())
        item_a=intent(1,'A',self.reference);item_b=intent(2,'B',self.reference)
        originals=copy.deepcopy([item_a,item_b])
        self.memory.ingest('A',[item_a,item_b],fills(item_a)+fills(item_b),10000)
        self.assertEqual([item_a,item_b],originals)
        self.assertEqual(self.memory.snapshot('A')['eligible_records'],1)
        self.assertEqual(self.memory.snapshot('B')['eligible_records'],0)
        self.assertEqual(self.store.get_day('A',1000)['risk_amount'],50)
        self.assertEqual(self.store.day_halt('A',1000)['reason'],'preserved halt')
        self.assertEqual(self.store.intents(),[])
        self.assertFalse(self.memory.snapshot('A')['auto_changes'])
        tables=['days','intents','audit','day_halts']
        after=list(self.store.db.iterdump())
        for table in tables:
            self.assertEqual([line for line in before if f'INSERT INTO "{table}"' in line],
                             [line for line in after if f'INSERT INTO "{table}"' in line])

    def test_export_scopes_observation_and_cost_correction_evidence_by_account(self):
        a=intent(1,'A',self.reference);b=intent(2,'B',self.reference)
        self.memory.ingest('A',[a],fills(a),10000)
        self.memory.ingest('B',[b],fills(b,result=-30),10000)
        base={'strategy_id':'fixture_rule','symbol':'A-SYMBOL','timeframe':'H1','data_time':1,'status':'WAIT'}
        self.memory.observe('A',[base],100)
        self.memory.observe('B',[dict(base,symbol='B-SYMBOL')],100)
        exported=self.memory.export('A')
        self.assertEqual(exported['outcome_correction_history'][0]['net'],20.)
        self.assertEqual(exported['observation_evidence'][0]['symbol'],'A-SYMBOL')
        self.assertEqual(len(exported['outcome_correction_history']),1)
        self.assertEqual(exported['export_window']['correction_total'],1)
        self.assertNotIn('B-SYMBOL',json.dumps(exported))
        self.assertEqual(exported['outcomes'][0]['outcome_id'],exported['outcome_correction_history'][0]['outcome_id'])

    def test_export_bounds_evidence_and_declares_truncation(self):
        cards=[{'strategy_id':'fixture_rule','symbol':'TEST','timeframe':'H1','data_time':i,'status':'WAIT'} for i in range(1001)]
        self.memory.observe('A',cards,100)
        result=self.memory.export('A')
        self.assertEqual(len(result['observation_evidence']),1000)
        self.assertEqual(result['export_window']['observation_total'],1001)
        self.assertTrue(result['export_window']['observations_truncated'])
        self.assertFalse(result['export_window']['corrections_truncated'])

    def test_legacy_correction_migration_never_guesses_orphan_account(self):
        self.ingest()
        saved=self.store.db.execute('SELECT id,fingerprint,at,payload FROM learning_outcome_revisions').fetchone()
        self.store.db.execute('DROP TABLE learning_outcome_revisions')
        self.store.db.execute('CREATE TABLE learning_outcome_revisions(id TEXT NOT NULL,fingerprint TEXT NOT NULL,at REAL NOT NULL,payload TEXT NOT NULL,PRIMARY KEY(id,fingerprint))')
        self.store.db.execute('INSERT INTO learning_outcome_revisions VALUES(?,?,?,?)',tuple(saved))
        self.store.db.execute('INSERT INTO learning_outcome_revisions VALUES(?,?,?,?)',('orphan','orphan-fingerprint',1,'{}'))
        self.memory=LearningMemory(self.store,{'fixture_rule':self.reference})
        self.assertEqual(self.memory.export('A')['export_window']['correction_total'],1)
        self.assertEqual(self.memory.export('B')['export_window']['correction_total'],0)
        self.assertIsNone(self.store.db.execute('SELECT account FROM learning_outcome_revisions WHERE id=?',('orphan',)).fetchone()[0])

    def populate(self,values,reference=None,symbol='TEST'):
        reference=reference or self.reference
        items=[];deals=[]
        for index,value in enumerate(values,1):
            item=intent(index,reference=reference);item['payload']['proposal']['symbol']=symbol
            trade=fills(item,result=value*10,closed_at=100+index*20)
            for record in trade:record['symbol']=symbol
            items.append(item);deals.extend(trade)
        # Deliberately reverse broker ordering: evaluation must sort by closure.
        self.memory.ingest('A',list(reversed(items)),list(reversed(deals)),10000)
        return self.memory.snapshot('A')

    def test_minimum_40_and_latest_12_holdout_are_both_enforced(self):
        snapshot=self.populate([1.]*39)
        self.assertEqual(snapshot['models'][0]['status'],'INSUFFICIENT')
        snapshot=self.populate([1.]*40)
        model=snapshot['models'][0]
        self.assertEqual(model['samples'],40)
        self.assertEqual(model['holdout_samples'],12)
        self.assertEqual(model['status'],'CANDIDATE_RESEARCH')
        self.assertFalse(model['live_weight_changed'])

    def test_chronological_holdout_detects_deterioration_without_shuffling(self):
        model=self.populate([2.]*28+[-1.]*12)['models'][0]
        self.assertGreater(model['mean_r'],0)
        self.assertEqual(model['holdout_mean_r'],-1.)
        self.assertEqual(model['status'],'REVIEW_DETERIORATION')
        self.assertLess(model['ewma_r'],0)

    def test_holdout_gain_after_negative_training_is_mixed_not_promotion(self):
        model=self.populate([-1.]*28+[2.]*12)['models'][0]
        self.assertEqual(model['status'],'MIXED_EVIDENCE')
        self.assertFalse(model['live_weight_changed'])

    def test_revisions_keep_independent_populations(self):
        newer=rule('2.0.0')
        LearningMemory(self.store,{newer['id']:newer})
        self.populate([1.]*20)
        items=[];deals=[]
        for index in range(21,41):
            item=intent(index,reference=newer);items.append(item);deals.extend(fills(item,closed_at=100+index*20))
        self.memory.ingest('A',items,deals,10000)
        data=self.memory.snapshot('A')
        self.assertEqual(data['stored_versions'],2)
        self.assertEqual(len(data['models']),2)
        self.assertTrue(all(m['samples']==20 and m['status']=='INSUFFICIENT' for m in data['models']))


class KnowledgeFileTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        source=self.root/'docs/agent-rules/snapshot/nexus';source.mkdir(parents=True)
        self.archive=self.root/'docs/knowledge/sources';self.archive.mkdir(parents=True)
        self.hashes={}
        for name in ('strategies.py','specialists.py','local_models.py','timeframes.py'):
            body=f'# immutable fixture {name}\n'.encode();(source/name).write_bytes(body)
            self.hashes[name]=hashlib.sha256(body).hexdigest()
            (self.archive/f'{self.hashes[name]}-{name}').write_bytes(body)
        reference={'id':'fixture','version':'1','source_hashes':self.hashes}
        self.reference={**reference,'revision':digest(reference)}
        self.document={'schema':1,'source_hashes':self.hashes,'rules':[self.reference]}
        self.path=self.root/'docs/knowledge/library.json'
        self.save()

    def save(self):
        self.path.write_text(json.dumps(self.document),encoding='utf-8')

    def test_reference_and_all_dependency_fingerprints_are_verified(self):
        self.assertEqual(load_library(self.root)['fixture'],self.reference)
        source=self.root/'docs/agent-rules/snapshot/nexus/strategies.py'
        source.write_text('# changed helper\n',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'source fingerprint'):
            load_library(self.root)

    def test_tampered_rule_duplicate_and_missing_dependencies_are_rejected(self):
        self.document['rules'][0]=dict(self.reference,version='changed');self.save()
        with self.assertRaisesRegex(ValueError,'rule fingerprint'):load_library(self.root)
        self.document['rules']=[self.reference,self.reference];self.save()
        with self.assertRaisesRegex(ValueError,'Duplicate'):load_library(self.root)
        self.document['rules']=[self.reference];self.document['source_hashes']={};self.save()
        with self.assertRaisesRegex(ValueError,'dependency manifest'):load_library(self.root)

    def test_valid_rule_revision_cannot_point_to_different_manifest(self):
        altered={k:v for k,v in self.reference.items() if k!='revision'}
        altered['source_hashes']={**self.hashes,'strategies.py':'incorrect'}
        self.document['rules']=[{**altered,'revision':digest(altered)}];self.save()
        with self.assertRaisesRegex(ValueError,'manifest mismatch'):load_library(self.root)

    def test_current_dependency_schema_requires_both_protocol_modules(self):
        self.document['dependency_schema']=2;self.save()
        with self.assertRaisesRegex(ValueError,'dependency manifest'):load_library(self.root)
        source=self.root/'docs/agent-rules/snapshot/nexus'
        for name in ('confluence.py','confluence_registry.py'):
            body=f'# current fixture {name}\n'.encode();(source/name).write_bytes(body)
            self.hashes[name]=hashlib.sha256(body).hexdigest()
        reference={'id':'fixture','version':'2','dependency_schema':2,'source_hashes':self.hashes}
        self.document['rules']=[{**reference,'revision':digest(reference)}];self.save()
        self.assertEqual(load_library(self.root)['fixture']['dependency_schema'],2)
        (source/'confluence.py').write_text('# changed protocol\n',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'source fingerprint'):load_library(self.root)

    def historical(self,archive=True):
        body=b'# earlier immutable strategies fixture\n'
        source_hash=hashlib.sha256(body).hexdigest()
        historical={k:v for k,v in self.reference.items() if k!='revision'}
        historical.update(version='previous',source_hashes={**self.hashes,'strategies.py':source_hash})
        historical['revision']=digest(historical)
        if archive:(self.archive/f'{source_hash}-strategies.py').write_bytes(body)
        return historical

    def test_export_sources_include_exact_history_and_deduplicate_shared_dependencies(self):
        historical=self.historical()
        manifest,files=knowledge_export_sources(self.root,[historical,self.reference,self.reference])
        self.assertTrue(manifest['complete']);self.assertEqual(manifest['missing'],[])
        self.assertEqual(manifest['reference_revisions'],2);self.assertEqual(len(files),5)
        for source in manifest['sources']:
            self.assertEqual(hashlib.sha256(files[source['path']]).hexdigest(),source['sha256'])
            self.assertTrue(source['path'].startswith('docs/knowledge/sources/'))
            self.assertNotIn('..',source['path'])
            self.assertEqual(len(source['revisions']),1 if source['name']=='strategies.py' else 2)
        historic_path=f"docs/knowledge/sources/{historical['source_hashes']['strategies.py']}-strategies.py"
        self.assertEqual(files[historic_path],b'# earlier immutable strategies fixture\n')

    def test_export_reports_missing_historical_sources_and_unknown_legacy_hashes(self):
        historical=self.historical(archive=False);legacy=rule('legacy')
        manifest,files=knowledge_export_sources(self.root,[historical,self.reference,legacy])
        self.assertFalse(manifest['complete']);self.assertEqual(len(files),4)
        self.assertEqual(len(manifest['missing']),5)
        absent=[item for item in manifest['missing'] if item['revision']==historical['revision']]
        self.assertEqual(len(absent),1)
        self.assertEqual(absent[0]['reason'],'missing_source_archive')
        self.assertEqual(absent[0]['sha256'],historical['source_hashes']['strategies.py'])
        self.assertEqual({item['name'] for item in manifest['missing'] if item['revision']==legacy['revision']},set(self.hashes))
        self.assertTrue(all(item['reason']=='missing_dependency_hash' for item in manifest['missing'] if item['revision']==legacy['revision']))

    def test_export_rejects_tampered_archive_even_when_snapshot_remains_valid(self):
        source=self.archive/f"{self.hashes['strategies.py']}-strategies.py"
        source.write_bytes(b'# tampered stored dependency\n')
        with self.assertRaisesRegex(ValueError,'archive fingerprint mismatch'):
            knowledge_export_sources(self.root,[self.reference])

    def test_export_rejects_dependency_path_traversal_and_malformed_digests(self):
        declarations=[{**self.hashes,'../strategies.py':self.hashes['strategies.py']},
                      {**self.hashes,'C:\\private.py':self.hashes['strategies.py']},
                      {**self.hashes,'strategies.py':'../outside'},
                      {**self.hashes,'strategies.py':'a'*63+'/'},
                      {**self.hashes,'strategies.py':None}]
        for hashes in declarations:
            with self.subTest(hashes=hashes):
                value={k:v for k,v in self.reference.items() if k!='revision'}
                value['source_hashes']=hashes;value['revision']=digest(value)
                with self.assertRaises(ValueError):knowledge_export_sources(self.root,[value])

    def test_export_rejects_tampered_rule_before_resolving_archive(self):
        with self.assertRaisesRegex(ValueError,'rule fingerprint mismatch'):
            knowledge_export_sources(self.root,[dict(self.reference,version='tampered')])

    def test_engine_zip_keeps_current_catalog_history_sources_and_gap_status(self):
        from nexus.engine import Engine
        historical=self.historical()
        store=Store(':memory:');self.addCleanup(store.close)
        LearningMemory(store,{historical['id']:historical})
        memory=LearningMemory(store,{self.reference['id']:self.reference})
        store.db.executescript('''
            CREATE TABLE financial_scenarios(account TEXT,created REAL,payload TEXT);
            CREATE TABLE school_reference_versions(revision TEXT,payload TEXT);
            CREATE TABLE execution_reference_versions(revision TEXT,payload TEXT);
        ''')
        catalog={'schools':[{'id':'fixture','scope':'Fixture school catalog'}]}
        engine=SimpleNamespace(root=self.root,data=self.root,store=store,learner=memory,
            broker=SimpleNamespace(account=lambda:{'login':'fixture','server':'fixture','platform_id':'fixture'}),
            rule_library={self.reference['id']:self.reference},knowledge=catalog,learning_state={},
            _update_learning=lambda **kwargs:None,_audit=lambda *args:None,
            _load_execution_reference=lambda:None,execution_reference_error='',_execution_tables=lambda:None)
        result=Engine._export_knowledge(engine)
        self.assertTrue(result['source_archive_complete'])
        with zipfile.ZipFile(result['path']) as bundle:
            payload=json.loads(bundle.read('knowledge-learning.json'))
            self.assertEqual(payload['current_rules'],[self.reference]);self.assertEqual(payload['schools'],catalog)
            self.assertEqual({item['revision'] for item in payload['reference']},{self.reference['revision'],historical['revision']})
            self.assertEqual(len(bundle.namelist()),len(set(bundle.namelist())))
            for item in payload['source_archive']['sources']:
                self.assertEqual(hashlib.sha256(bundle.read(item['path'])).hexdigest(),item['sha256'])
        (self.archive/f"{historical['source_hashes']['strategies.py']}-strategies.py").unlink()
        result=Engine._export_knowledge(engine)
        self.assertFalse(result['source_archive_complete']);self.assertEqual(result['missing_sources'],1)
        with zipfile.ZipFile(result['path']) as bundle:
            payload=json.loads(bundle.read('knowledge-learning.json'))
            self.assertFalse(payload['source_archive']['complete'])
            self.assertEqual(payload['source_archive']['missing'][0]['revision'],historical['revision'])


if __name__=='__main__':
    unittest.main()
