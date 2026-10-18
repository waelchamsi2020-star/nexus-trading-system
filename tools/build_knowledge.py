"""Build reproducible local references; runtime never evaluates reference text."""
import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from export_agent_rules import export

from nexus.learning import CHART_MODEL_POLICY, LEARNING_SOURCE_MODULES, digest

REFERENCES={
 'elliott_candidate':{'url':'https://www.elliottwave.com/waveopedia/impulse/',
    'principles_ar':['في الدافعة القياسية لا تتجاوز الثانية بداية الأولى، والثالثة ليست الأقصر بين الموجات الدافعة، والرابعة لا تتداخل مع نطاق الأولى.','هذه القيود لا تجعل فرضية الموجتين في البرنامج ترقيمًا كاملًا لكل درجات إليوت.']},
 'harmonic_abcd':{'url':'https://harmonictrader.com/harmonic-patterns/abcd-pattern/',
    'principles_ar':['النموذج يجمع تعاقب الأضلاع وعلاقات التصحيح والامتداد؛ تشابه ضلعين وحده لا يثبت اكتمال كل النماذج الهارمونيكية.','سماحات الدخول والعمر والوقف في البرنامج اختيارات تنفيذية معلنة وليست قواعد مصدرية شاملة.']},
 'wyckoff_spring':{'url':'https://www.wyckoffanalytics.com/wyckoff-method/',
    'principles_ar':['قراءة العرض والطلب والجهد والنتيجة وسياق النطاق جزء من المدرسة.','كسر نطاق واختباره في البرنامج نموذج محلي؛ لا يستنتج تلقائيًا جميع المراحل أو نية المؤسسات.']},
 'order_flow':{'url':'https://www.cmegroup.com/articles/faqs/market-by-order-mbo.html',
    'principles_ar':['بيانات عمق دفتر الأوامر تختلف عن شموع السعر وعدد تحديثات السعر.','المؤشر الحالي تقريب نشاط من الشموع، وليس إعادة بناء دفتر أوامر أو دلتا حقيقية.']},
}

def build():
    manifest=export(ROOT/'docs/agent-rules')
    hashes={name:manifest[key] for name,key in [('strategies.py','source_module_sha256'),('specialists.py','specialists_sha256'),('local_models.py','local_models_sha256'),('timeframes.py','timeframes_sha256'),('confluence.py','confluence_sha256'),('confluence_registry.py','confluence_registry_sha256'),('indicators.py','indicators_sha256'),('extended_models.py','extended_models_sha256')]}
    hashes.update(manifest['config_hashes'])
    out=ROOT/'docs/knowledge';(out/'versions').mkdir(parents=True,exist_ok=True)
    archive=out/'sources';archive.mkdir(exist_ok=True)
    for name,expected in hashes.items():
        blob=(ROOT/'docs/agent-rules/snapshot/nexus'/name).read_bytes()
        if hashlib.sha256(blob).hexdigest()!=expected:raise ValueError('Rule source archive fingerprint mismatch')
        target=archive/f'{expected}-{name}'
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists() and target.read_bytes()!=blob:raise ValueError('Immutable rule source archive conflict')
        if not target.exists():target.write_bytes(blob)
    rules=[]
    for entry in manifest['agents']:
        saved=json.loads((ROOT/'docs/agent-rules'/(entry['id']+'.json')).read_text(encoding='utf-8'))
        tree=ast.parse(saved['rules_python'])
        comparisons=list(dict.fromkeys(ast.unparse(n) for n in ast.walk(tree) if isinstance(n,ast.Compare)))
        contract=entry['contract']
        rule={'schema':1,'id':entry['id'],'name_ar':entry['school'],'version':entry['version'],
              'dependency_schema':4,
              'scope_ar':entry['theory_scope_ar'],'school_complete':False,
              'definition_type':'VERSIONED_COMPUTATIONAL_DEFINITION',
              'inputs':entry['data_requirements'],'minimum_bars':entry['min_bars'],
              'family':entry['evidence_group'],'contract':contract,
              'conditions_code':comparisons,'algorithm_python':saved['rules_python'],
              'source_hashes':hashes,'source_reference':REFERENCES.get(entry['id']) or ({'url':contract['definition']['source']} if contract['definition'].get('source') else None),
              'reference_note':'Source principles and house thresholds are distinct; no claim to cover all interpretations.',
              'invariants':['completed_bars_only','no_future_data','missing_data_abstains','single_risk_authority','no_direct_broker_access'],
              'change_process':['new_immutable_revision','positive_and_negative_fixtures','chronological_holdout_after_costs','demo_forward_review','versioned_release'],
              'learning_policy':'Versioned observations, attributable closed outcomes and local chart-feature classifier evaluation; no automatic mutation of rules, risk or live votes.',
              'learning_contract':{
                  'feature_version':'ohlc-v1','model_version':'chart-logistic-v1',
                  'features':['return_1_atr','return_5_atr','ema_gap_atr','rsi_centered','close_location','efficiency_20','volatility_ratio_log','tick_activity_log'],
                  'feature_input_window':41,'feature_snapshot':'original_completed_mt5_entry_decision',
                  'label':'broker_confirmed_owned_closed_trade_net_r_after_costs > 0',
                  'identity':['rule_revision','protocol_revision','execution_style','scalp_policy_revision','execution_policy_revision','symbol','timeframe'],
                  'minimum_samples':60,'minimum_train_samples':40,'minimum_holdout_samples':12,
                  'split':'chronological_70_30_with_unavailable_training_labels_purged',
                  'normalization':'training_only','evaluation':['holdout_brier','holdout_log_loss','training_prevalence_baseline'],
                  'mode':'SHADOW_ONLY','execution_authority':False,
                  'legacy_feature_backfill':False,'automatic_rule_mutation':False}}
        revision=digest(rule);rule['revision']=revision;rules.append(rule)
        target=out/'versions'/f"{rule['id']}-{revision}.json"
        blob=json.dumps(rule,ensure_ascii=False,indent=2)
        if target.exists() and target.read_text(encoding='utf-8')!=blob:raise ValueError('Immutable knowledge revision conflict')
        target.write_text(blob,encoding='utf-8')
    library={'schema':1,'dependency_schema':4,'source_hashes':hashes,'rules':rules,'all_schools_complete':False}
    from nexus.indicators import FORMULAS
    formulas={'schema':1,'library_version':'1.0.0','formulas':FORMULAS,
              'source_sha256':hashes['indicators.py'],'implementation':'nexus.indicators',
              'historical_indicators':'Legacy SMA RSI/ATR and first-close-seeded EMA remain unchanged in strategies.py.',
              'parity_policy':'Formula/seed/method/history must match before claiming terminal parity.'}
    (out/'indicator-library.json').write_text(json.dumps(formulas,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'library.json').write_text(json.dumps(library,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# مرجع القواعد المحلية','',f'يحتوي هذا الإصدار على {len(rules)} تعريفًا حسابيًا. لا يعني ذلك اكتمال جميع مدارس التحليل.','',
           'كل ملف يحتوي المدخلات والشروط البرمجية والكود الكامل وبصمات توابعه وحدوده وخطوات تطويره. لا ينفذ البرنامج نص المرجع كتعليمات أو كود ديناميكي.','']
    lines.extend(['تُحفظ ملفات القواعد والتوابع المشتركة بإصدارات غير قابلة للاستبدال داخل sources، باسم بصمة الملف متبوعة باسمه. يمكن ربط source_hashes في المرجع بهذه الملفات عند إعادة مراجعة إصدار سابق. لا يعني وجود ملف إصدار اكتمال بيانات الاختبار أو صلاحية نتيجة تداول.',''])
    for rule in rules:
        lines.extend([f"## {rule['name_ar']}",rule['scope_ar'],'',f"[ملف المرجع وإصداره](versions/{rule['id']}-{rule['revision']}.json)",''])
    (out/'README.md').write_text('\n'.join(lines),encoding='utf-8')
    valuation_source=(ROOT/'src/nexus/valuation.py').read_text(encoding='utf-8')
    valuation={'schema':1,'version':'1.0.0','models':['pv','dcf','ddm','nav','multiples','bond'],
               'data_policy':'local_explicit_financial_scenarios','execution_authority':False,
               'source_sha256':hashlib.sha256(valuation_source.encode()).hexdigest(),
               'source_python':valuation_source,
               'inputs_note':'Period-end cashflows; currency and financial source required; publication cannot follow evaluation time; DCF uses FCFF/WACC; DDM uses next dividend/cost of equity; bond only at coupon boundary.'}
    valuation['revision']=digest(valuation)
    (out/'valuation-reference.json').write_text(json.dumps(valuation,ensure_ascii=False,indent=2),encoding='utf-8')
    modules={}
    for name in LEARNING_SOURCE_MODULES:
        blob=(ROOT/'src/nexus'/name).read_bytes()
        modules[name]={'source_python':blob.decode('utf-8'),'sha256':hashlib.sha256(blob).hexdigest()}
    learner={'schema':1,'model_version':CHART_MODEL_POLICY['model_version'],
             'feature_version':CHART_MODEL_POLICY['feature_version'],'policy':dict(CHART_MODEL_POLICY),
             'execution_authority':False,'automatic_rule_mutation':False,'source_modules':modules,
             'source_policy':'inert review copies; never imported from a reference export'}
    learner['revision']=digest(learner)
    blob=json.dumps(learner,ensure_ascii=False,indent=2)
    version=out/'versions'/f"learning-reference-{learner['revision']}.json"
    if version.exists() and version.read_text(encoding='utf-8')!=blob:
        raise ValueError('Immutable learning reference conflict')
    version.write_text(blob,encoding='utf-8')
    (out/'learning-reference.json').write_text(blob,encoding='utf-8')
    from nexus import confluence, scalping
    execution_modules={}
    for name in ('confluence.py','confluence_registry.py','scalping.py','risk.py','execution.py','engine.py'):
        content=(ROOT/'src/nexus'/name).read_bytes()
        execution_modules[name]={'sha256':hashlib.sha256(content).hexdigest(),'source_python':content.decode('utf-8')}
    execution_reference={'schema':1,'decision_protocol':'four_school_v1',
        'protocol_definition':confluence.definition(),
        'scalp_definition':{**scalping.POLICY_DEFINITION,'revision':scalping.POLICY_REVISION},
        'source_modules':execution_modules,'automatic_rule_mutation':False,
        'data_scope':'Actual MT5 OHLC and quotes; no real volume-at-price adapter currently enabled',
        'historical_qualification_scope':'Legacy single-strategy certificates do not qualify the composite protocol'}
    execution_reference['revision']=digest(execution_reference)
    content=json.dumps(execution_reference,ensure_ascii=False,indent=2)
    historical=out/'versions'/f"execution-reference-{execution_reference['revision']}.json"
    if historical.exists() and historical.read_text(encoding='utf-8')!=content:
        raise ValueError('Immutable execution reference conflict')
    historical.write_text(content,encoding='utf-8')
    (out/'execution-reference.json').write_text(content,encoding='utf-8')
    from nexus.multischool import DEFINITION, MODULES
    multi={"schema":1,"definition":DEFINITION,"modules":{name:hashlib.sha256((ROOT/"src/nexus"/name).read_bytes()).hexdigest() for name in MODULES}}
    multi["revision"]=digest(multi)
    (out/"multi-school-reference.json").write_text(json.dumps(multi,ensure_ascii=False,indent=2),encoding="utf-8")
    return library

if __name__=='__main__':print('Built knowledge references:',len(build()['rules']))
