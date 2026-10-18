"""Advisory registration for the separately guarded four-school protocol.

Research cards do not grant execution. Engine and RiskManager must re-evaluate
the protocol with an executable quote and its independently checked net ratio.
The lazy import avoids a circular dependency through common OHLC primitives.
"""
import copy

from .strategies import REGISTRY, _register, _result


@_register('four_school_confluence','تقاطع المدارس الأربع',
           ['Liquidity sweep','BOS','FVG','POC','Local timing','RSI divergence','ABC geometry'],
           'structure',40)
def confluence_reference(b,c):
    from .confluence import evaluate
    refresh_contract()
    result=evaluate(c['symbol'],c['timeframe'],b,c['as_of'],c.get('tick_size',1e-8),
                    profile=None,quote=None)
    # No indicative candle price or research card may turn into an executable
    # quote. Keep this card advisory even when geometric research is complete.
    reasons=[item['ar'] for item in result['reasons']]
    return _result(missing=reasons or ['يلزم سعر تنفيذ فعلي وفحص صافي العائد قبل منح التنفيذ'],
                   evidence=[{'kind':'decision_matrix','value':result['matrix']}],
                   assumptions=['تعريف تقاطع محلي؛ لا يثبت اكتمال المدارس أو احتمالية ربح'],
                   status='WAIT')


meta=REGISTRY['four_school_confluence']
meta['data_requirements']=['completed_ohlc','fresh_executable_quote','actual_volume_profile_or_declared_local_timing']
meta['contract']=copy.deepcopy(REGISTRY['smc_ict_proxy']['contract'])
meta['contract'].update(
    rule_id='four_school_confluence',rule_version=meta['version'],minimum_bars=40,
    price_plan='Actual quote, original untouched gap, protected sweep stop and nearest unswept liquidity; net reward/risk checked independently',
    executable_specialists=[],
    data_requirements=meta['data_requirements'],school_complete=False,
    definition={'name_en':'Four-school structural confluence',
                'implementation':'nexus.confluence.evaluate',
                'rules_source':'confluence.py',
                'scope':'Versioned local composite; advisory cards never grant execution.',
                'scope_ar':'تقاطع محلي بإصدار مستقل؛ بطاقات الأبحاث لا تمنح التنفيذ.',
                'rules':['Linked causal sweep/BOS/FVG; actual POC or declared timing, exact reward/risk >=2 and independent net-cost send guard'],
                'rules_ar':['تسلسل سببي لسحب السيولة وكسر الهيكل والفجوة؛ نقطة تحكم فعلية أو توقيت معلن، وعائد/مخاطرة لا يقل عن اثنين مع حارس مستقل لصافي التكاليف قبل الإرسال']})


def refresh_contract():
    from .confluence import definition
    source=definition()
    meta['contract']['definition']={
        'name_en':source['name_en'],'scope':source['scope_en'],'scope_ar':source['scope_ar'],
        'implementation':'nexus.confluence.evaluate','rules_source':'confluence.py',
        'rules':[rule['en'] for rule in source['rules']],
        'rules_ar':[rule['ar'] for rule in source['rules']],
        'parameters':source['parameters'],'profile_schema':source['profile_schema'],
        'protocol_revision':source['revision'],'timing_definition':source['timing_definition'],
        'volume_scope':source['volume_scope'],'source':source['sources'][0]}
