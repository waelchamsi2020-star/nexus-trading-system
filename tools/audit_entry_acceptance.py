"""Run explicitly scoped entry fixtures and publish a non-exhaustive model map.

Other unit tests may cover additional models. This map claims only these
executed suites, never that an unlisted model is broken or untested globally.
"""
import hashlib
import importlib
import io
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from nexus.learning import load_library
from nexus.strategies import REGISTRY


class RecordingResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.outcomes = {}

    def addSuccess(self, test):
        super().addSuccess(test)
        self.outcomes[test.id()] = 'PASS'

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.outcomes[test.id()] = 'FAIL'

    def addError(self, test, err):
        super().addError(test, err)
        self.outcomes[test.id()] = 'ERROR'


def run():
    specs=[('test_specialists','Specialists','analyzer buy/sell; shared price plan with explicitly stubbed regime; malformed/unfinished input', lambda m:list(m.LEGACY_FIXTURES)),
           ('test_extended_theories','ExtendedTheories','fractal and OBV fixtures through causal pivots and shared plans', lambda m:list(m.NEW_MODELS)),
           ('test_harmonic_end_to_end','HarmonicPipelineTests','unmocked candles to causal pivots, both directions, confirmation, invalidation, ratios and expiry', lambda m:['harmonic_'+kind for kind in m.PRICES]),
           ('test_local_models','LocalModels','local formulas both directions; shared plan uses injected pivots; selected model-specific missing-data and anchor tests; not full candle-to-plan acceptance', lambda m:list(m.lm.MODELS)),
           ('test_local_model_pipeline','LocalModelPipeline','unmocked candle-to-plan buy/sell; input immutability; unfinished trigger rejection; required partner/daily context on applicable models; missing tick activity for order_flow', lambda m:list(m.PIPELINE_MODELS)),
           ('test_registry_acceptance','RegistryAcceptance','all 58 contracts and negative data cases; unmocked BUY/SELL candle-to-plan for 57 executable models; advisory composite remains WAIT and separate quoted evaluator accepts both sides', lambda m:list(m.REGISTRY_MODELS)),
           ('test_registry_acceptance','ModelAcceptanceById','one independent named test per model: both directions, price bracket, unfinished and short-history refusal; separate quote evaluator for advisory composite', lambda m:list(m.REGISTRY_MODELS))]
    suites=[];rows=[];hashes={}
    for module_name,class_name,scope,model_ids in specs:
        module=importlib.import_module(module_name);cls=getattr(module,class_name)
        models=model_ids(module)
        assert set(models)<=set(REGISTRY)
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(cls)
        names=unittest.defaultTestLoader.getTestCaseNames(cls)
        suites.append(suite)
        rows.extend({'model':sid,'version':REGISTRY[sid]['version'],'suite':module_name+'.'+class_name,
                     'scope':scope,'test_methods':[name for name in names if name=='test_model_'+sid] if class_name=='ModelAcceptanceById' else names} for sid in models)
        source=Path(module.__file__);hashes[source.name]=hashlib.sha256(source.read_bytes()).hexdigest()
    for name in ('tools/discover_entry_fixtures.py','tests/fixtures/discovered-entry-seeds.json',
                 'tests/test_remaining_entry_pipeline.py','tests/test_pivot_model.py','tests/test_confluence.py'):
        hashes[name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    log=io.StringIO();result=unittest.TextTestRunner(stream=log,verbosity=1,resultclass=RecordingResult).run(unittest.TestSuite(suites))
    rules=load_library(ROOT);covered={r['model'] for r in rows}
    report={'type':'SCOPED_ENTRY_ACCEPTANCE_MAP','passed':result.wasSuccessful(),'test_methods_run':result.testsRun,
            'mapped_models':rows,'unmapped_in_this_report':sorted(set(REGISTRY)-covered),
            'registry_fully_mapped':covered==set(REGISTRY),
            'executable_buy_sell_pipelines':57 if result.wasSuccessful() else None,
            'advisory_model':'four_school_confluence',
            'scope_complete_for_entire_registry':False,'profitability_proven':False,'orders_sent':0,
            'remaining_scope':['per-model parameter boundary and lifecycle exhaustion',
                               'chronological broker-data evaluation after verified costs',
                               'whole-school completeness is not established by branch fixtures'],
            'source_hashes':next(iter(rules.values()))['source_hashes'],'test_source_sha256':hashes,
            'test_log':log.getvalue()}
    report['independent_model_tests'] = [
        {'model_id':sid, 'models_covered':[sid],
         'test':'test_registry_acceptance.ModelAcceptanceById.test_model_'+sid,
         'file':'tests/test_registry_acceptance.py',
         'result':result.outcomes.get('test_registry_acceptance.ModelAcceptanceById.test_model_'+sid,'NOT_RUN')}
        for sid in sorted(REGISTRY)]
    (ROOT/'reports/entry-acceptance-map.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'passed':result.wasSuccessful(),'test_methods':result.testsRun,'mapped_models':len(covered),
                      'models_not_mapped_here':len(REGISTRY)-len(covered),'orders_sent':0}))
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':sys.exit(run())
