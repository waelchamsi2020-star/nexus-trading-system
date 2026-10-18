"""Export exact, versioned local agent rules without accessing a trading account."""
import hashlib
import inspect
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nexus import local_models, specialists, strategies, timeframes

# Scope notes describe this implementation, not a complete textbook or proof
# that a named theory predicts prices. Execution remains in strategies.py.
THEORY_SCOPE = {
    "dow_structure": "تعريف محلي لاتجاه القمم والقيعان المؤكدة ثم اختراق جديد؛ لا يمثل نظرية داو كاملة.",
    "engulfing": "ابتلاع جسم الشمعة السابقة مع حد أدنى لحجم الجسم نسبة إلى التقلب.",
    "support_bounce": "ملامسة دعم أو مقاومة من محور مؤكد ثم رفض سعري بإغلاق مكتمل.",
    "classic_reversal_patterns": "قمة وقاع مزدوجان والرأس والكتفان وعكسه؛ هندسة مؤكدة واختراق خط العنق.",
    "geometric_triangle_breakout": "مثلث صاعد أو هابط أو متماثل من محاور مؤكدة وخطوط متقاربة؛ دخول عند اختراق جديد.",
    "breakout_retest": "اختراق نطاق سابق ثم إعادة اختبار ناجحة وفق ترتيب زمني محدد.",
    "fib_retracement": "تصحيح لموجة مؤكدة ولمس 61.8% ثم استعادة 50%؛ تعريف محدد وليس جميع تطبيقات فيبوناتشي.",
    "darvas_box": "نسخة محددة لصندوق سعري سابق وتأكيد السقف ثم الاختراق، وليست كل قراءات دارفاس.",
    "vwap_reclaim": "عبور المتوسط المرجح لشموع اليوم؛ وزن التكات بديل تقريبي ولا يساوي حجم صفقات مركزيًا.",
    "ichimoku_cross": "تقاطع واتجاه خطي تنكان وكيجون خارج سحابة سببية محسوبة من الماضي.",
    "ema_cross": "تقاطع جديد بين المتوسطين الأسيين 12 و26.",
    "rsi_rebound": "عودة مؤشر القوة النسبية عبر 30 أو70؛ النسخة الحالية بمتوسط بسيط لا بتنعيم وايلدر.",
    "volatility_breakout": "انكماش ثم إغلاق جديد خارج نطاق محسوب من الشموع السابقة.",
    "zscore_reversion": "عودة درجة معيارية عبر عتبة مع هدف متوسط صالح؛ لا يفترض ثبات التوزيع.",
    "interasset_confirmation": "تأكيد الاتجاه من أصل مقابل محدد ومتزامن؛ يحتاج ربطًا صريحًا ولا يخمن الأصل المقابل.",
    "harmonic_abcd": "نموذج الأضلاع المتساوية بنسب محددة ومحاور مؤكدة وتفعيل لاحق وإبطال وهدف؛ بقية أنماط الهارمونيك خارج النطاق.",
    "elliott_candidate": "فحص هندسي لبدائل خمس موجات مع بيان القواعد المتحققة والمخالفة؛ الدرجات المتداخلة وقاعدة الدخول غير مكتملتين.",
    "wyckoff_spring": "رصد كسر نطاق واستعادته؛ لا يثبت مراحل التجميع أو التصريف ولا نية المؤسسات.",
    "smc_ict_proxy": "فجوة ثلاث شموع من الأسعار؛ نموذج الجلسات ودورة كتل الأوامر وتفعيل السيولة غير مكتملة.",
    "supply_demand_proxy": "مرشح منطقة أساس قبل اندفاع؛ إبطال المنطقة وعمرها وقواعد العودة غير مكتملة.",
    "smt_proxy": "مقارنة محاور أصلين متزامنين مطلوبة؛ لا توجد إشارة تنفيذ قبل تعريف الربط ودورة الاختلاف.",
    "seasonality": "تحتاج تاريخًا متعدد السنوات ومعدلًا واختبارًا حسب فئات التقويم؛ تاريخ قصير لا يثبت موسمية.",
    "gann": "يلزم تحديد مقياس السعر والزمن وقواعد مربع التسعة وقاعدة دخول قابلة للاختبار؛ غير منفذ حاليًا.",
    "order_flow": "يتطلب صفقات موقعة وعمق سوق تاريخيًا موثوقًا؛ شموع وتكات الوسيط لا تنتج بصمة أوامر حقيقية.",
    "four_school_confluence": "بروتوكول مستقل لتقاطع سيولة وهيكل وفجوة مع حجم صفقات فعلي أو توقيت محلي؛ الوقف هيكلي والعائد مفحوص بعد التكاليف. لا يثبت ربحية أو اكتمال المدارس.",
}


def export(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    source = Path(strategies.__file__).read_bytes()
    source_hash = hashlib.sha256(source).hexdigest()
    theory_scope = dict(THEORY_SCOPE)
    theory_scope.update({id: "تعريف تخصص خوارزمي؛ القواعد والمعاملات موثقة في العقد المرفق. " + strategies.REGISTRY[id]["school"] for id in specialists.SPECS})
    theory_scope.update({id: "نموذج محلي محدد القواعد، وليس المدرسة كاملة: " + model[1] for id,model in local_models.MODELS.items()})
    if set(theory_scope) != set(strategies.REGISTRY):
        raise ValueError("Every registered agent must have an explicit theory scope")
    records = []
    for meta in strategies.registry_manifest():
        analyzer = strategies.REGISTRY[meta["id"]]["analyzer"]
        rules = inspect.getsource(analyzer)
        record = dict(meta, theory_scope_ar=theory_scope[meta["id"]],
                      execution_enabled=meta["coverage"] == "IMPLEMENTED",
                      rules_python=rules,
                      rules_sha256=hashlib.sha256(rules.encode()).hexdigest(),
                      source_module_sha256=source_hash,
                      execution_note="Implemented rules still require committee, quote, risk and broker approval; this is not a profitability certificate.")
        (destination / (meta["id"] + ".json")).write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        records.append(record)
        # Each agent gets a Python artifact as requested. Keep shared helpers in
        # the exact sibling source snapshot; do not silently enable partial rules.
        module = ('"""Saved agent definition; research only, no broker access."""\n'
                  'from snapshot.nexus import strategies as _shared\n\n'
                  f'AGENT_ID = {meta["id"]!r}\n'
                  f'THEORY_SCOPE_AR = {theory_scope[meta["id"]]!r}\n'
                  f'COVERAGE = {meta["coverage"]!r}\n'
                  f'RULES_SHA256 = {record["rules_sha256"]!r}\n'
                  'def analyze(symbol, timeframe, bars, as_of=None, context=None):\n'
                  '    return _shared.analyze_strategy(AGENT_ID, symbol, timeframe, bars, as_of, context)\n')
        compile(module, meta["id"], "exec")
        (destination / (meta["id"] + ".py")).write_text(module, encoding="utf-8")
    # Preserve common indicators, validation, sizing of price levels and pattern helpers,
    # not just the individual function bodies which depend on them.
    (destination / "strategies_source.py").write_bytes(source)
    snapshot = destination / "snapshot" / "nexus"
    snapshot.mkdir(parents=True, exist_ok=True)
    (snapshot.parent / "__init__.py").write_text("", encoding="utf-8")
    (snapshot / "__init__.py").write_text("", encoding="utf-8")
    (snapshot / "strategies.py").write_bytes(source)
    specialist_source = Path(specialists.__file__).read_bytes()
    (snapshot / "specialists.py").write_bytes(specialist_source)
    local_source=Path(local_models.__file__).read_bytes()
    (snapshot / "local_models.py").write_bytes(local_source)
    timing_source=Path(timeframes.__file__).read_bytes()
    (snapshot / "timeframes.py").write_bytes(timing_source)
    from nexus import confluence, confluence_registry
    confluence_source=Path(confluence.__file__).read_bytes()
    adapter_source=Path(confluence_registry.__file__).read_bytes()
    (snapshot/'confluence.py').write_bytes(confluence_source)
    (snapshot/'confluence_registry.py').write_bytes(adapter_source)
    from nexus import extended_models, indicators
    indicator_source=Path(indicators.__file__).read_bytes()
    extended_source=Path(extended_models.__file__).read_bytes()
    (snapshot/'indicators.py').write_bytes(indicator_source)
    (snapshot/'extended_models.py').write_bytes(extended_source)
    config_hashes={}
    for name in ('config/models.yaml','config/models.schema.json'):
        blob=(Path(strategies.__file__).parent/name).read_bytes()
        (snapshot/name).parent.mkdir(parents=True,exist_ok=True)
        (snapshot/name).write_bytes(blob)
        config_hashes[name]=hashlib.sha256(blob).hexdigest()
    manifest = {"schema_version": 2, "timeframes_sha256":hashlib.sha256(timing_source).hexdigest(), "source_module_sha256": source_hash,
                "specialists_sha256": hashlib.sha256(specialist_source).hexdigest(),
                "local_models_sha256": hashlib.sha256(local_source).hexdigest(),
                "confluence_sha256":hashlib.sha256(confluence_source).hexdigest(),
                "confluence_registry_sha256":hashlib.sha256(adapter_source).hexdigest(),
                "indicators_sha256":hashlib.sha256(indicator_source).hexdigest(),
                "extended_models_sha256":hashlib.sha256(extended_source).hexdigest(),
                "config_hashes":config_hashes,
                "agents": [{k: v for k, v in r.items() if k != "rules_python"} for r in records]}
    (destination / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    result = export(ROOT / "docs" / "agent-rules")
    print(f"Exported {len(result['agents'])} agents with exact source and hashes.")
