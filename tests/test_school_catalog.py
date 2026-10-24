import json
import tempfile
import unittest
from pathlib import Path
from shutil import copytree

from nexus.school_catalog import catalog
from nexus.strategies import REGISTRY, registry_manifest

ROOT=Path(__file__).resolve().parents[1]


class SchoolReferenceTests(unittest.TestCase):
    def test_exact_user_categories_have_bilingual_specific_rules_and_valid_models(self):
        document=catalog(ROOT);entries=document['schools'];ids={s['id'] for s in entries}
        manifest={row['id']:row for row in registry_manifest()}
        self.assertEqual(document['counts'],{'technical':30,'fundamental':20,'approach':8,'total':58})
        self.assertFalse(document['model_api_required']);self.assertFalse(document['runtime_external_fetch'])
        all_rules=[]
        for school in entries:
            self.assertGreaterEqual(len(school['rules_ar']),4)
            self.assertEqual(len(school['rules_ar']),len(school['rules_en']))
            self.assertFalse(school['complete_school'])
            self.assertTrue(school['references'])
            self.assertTrue(all(ref['url'].startswith('https://') for ref in school['references']))
            self.assertLessEqual(set(school['strategy_ids']),set(REGISTRY),school['id'])
            self.assertEqual(school['requirements_scope'],'SCHOOL_REFERENCE')
            self.assertEqual([m['id'] for m in school['runtime_models']],school['strategy_ids'])
            for model in school['runtime_models']:
                self.assertEqual(model['version'],REGISTRY[model['id']]['version'])
                self.assertEqual(model['inputs'],REGISTRY[model['id']]['data_requirements'])
                self.assertEqual(model['minimum_bars'],REGISTRY[model['id']]['min_bars'])
                self.assertEqual(model['definition'],manifest[model['id']]['contract']['definition'])
            self.assertLessEqual(set(school['related_ids']),ids)
            if school['alias_of']:self.assertIn(school['alias_of'],ids)
            for record in school['rule_records']:
                self.assertEqual(record['text_ar'],school['rules_ar'][int(record['id'][-2:])-1])
                self.assertIn(record['kind'],('SOURCE_PRINCIPLE','OPERATIONAL_CHECKLIST','HOUSE_DEFINITION'))
                if record['kind']=='SOURCE_PRINCIPLE':self.assertTrue(record['reference_ids'])
                all_rules.append(record['text_en'])
        self.assertGreater(len(all_rules),296)
        self.assertEqual(document['catalog_version'],'1.2.0')
        self.assertGreater(len(set(all_rules)),280,'schools need distinct rules rather than repeated generic prose')
        self.assertEqual({model for school in entries for model in school['strategy_ids']},set(REGISTRY),'every current executable model needs a school reference')

    def test_reference_fingerprint_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as temp:
            destination=Path(temp)/'docs/school-catalog';copytree(ROOT/'docs/school-catalog',destination)
            self.assertEqual(len(catalog(temp)['schools']),58)
            path=destination/'catalog.json';value=json.loads(path.read_text(encoding='utf-8'))
            value['schools'][0]['rules_en'][0]='Modified after release'
            path.write_text(json.dumps(value),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'fingerprint'):catalog(temp)

    def test_missing_financial_inputs_and_overlapping_schools_do_not_create_votes(self):
        entries={s['id']:s for s in catalog(ROOT)['schools']}
        self.assertEqual(entries['ta_harmonic_patterns']['alias_of'],'ta_harmonic')
        self.assertEqual(entries['ap_relative']['alias_of'],'fa_relative')
        self.assertEqual(entries['ap_multiples']['alias_of'],'ap_relative')
        for s in entries.values():
            if s['category'] in ('fundamental','approach'):
                self.assertEqual(s['strategy_ids'],[])
                self.assertEqual(s['execution_status'],'LOCAL_DATA_REQUIRED')
                self.assertIn('DATA_MISSING',s['unavailable_data_policy_en'])
        self.assertTrue({'classic_pivot_reclaim','fractal_5_breakout','obv_divergence_reclaim'} <= set(REGISTRY))

    def test_versioned_protocol_and_formulas_are_inert_research_material(self):
        formulas=[]
        for school in catalog(ROOT)['schools']:
            protocol=school['rule_protocol']
            self.assertEqual(protocol['rule_set_version'],school['rule_set_version'])
            self.assertEqual(protocol['entry']['research_review_rule_ids'],[r['id'] for r in school['rule_records']])
            self.assertEqual(protocol['data_prerequisites']['keys'],school['requirements'])
            self.assertEqual(len(protocol['summary_ar']),len(protocol['summary_en']))
            self.assertFalse(protocol['evaluates_rule_text'])
            self.assertFalse(protocol['output']['issues_trade_order'])
            self.assertFalse(protocol['output']['creates_committee_vote'])
            self.assertFalse(protocol['learning']['rewrites_rules'])
            self.assertFalse(protocol['change_policy']['automatic_promotion'])
            for rule in school['rule_records']:
                if 'formal_definition' in rule:
                    definition=rule['formal_definition'];formulas.append(rule['id'])
                    self.assertTrue(all(definition.get(field) for field in ('expression','variables','domain','units')))
        self.assertGreaterEqual(len(formulas),8)


if __name__=='__main__':unittest.main()
