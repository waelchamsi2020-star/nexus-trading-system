"""Build a factual MT5-data coverage report from the versioned school catalog."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "docs" / "school-catalog" / "catalog.json"
OUTPUT = ROOT / "outputs" / "mt5-school-assessment.md"

DIRECT = {"completed_ohlc", "tick_volume", "session_clock"}
CONDITIONAL = {"long_history", "paired_history", "real_volume", "calendar"}
NOT_GUARANTEED = {"depth_history", "signed_trades", "positioning", "corporate_actions"}


def classify(school: dict) -> tuple[str, str]:
    models = school.get("runtime_models") or []
    requirements = set(school.get("requirements") or [])
    if not models:
        return "مرجع فقط", "لا نموذج تنفيذ مسجل لهذه المدرسة"
    if requirements - DIRECT - CONDITIONAL - NOT_GUARANTEED:
        return "جزئي/بيانات خارج MT5", "متطلبات مرجعية لا يضمنها MT5"
    if requirements & NOT_GUARANTEED:
        return "تقريب أو مشروط", "عمق السوق/تدفق الصفقات أو بيانات مشابهة غير مضمونة"
    if requirements & CONDITIONAL:
        return "مشروط", "التاريخ/الأصل المقارن/الحجم/التقويم يحتاج تحققًا لكل رمز"
    return "قواعد محلية قابلة للتقييم", "المدخلات الأساسية متاحة من شموع وتكات MT5"


def main() -> None:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    schools = catalog["schools"]
    lines = [
        "# تقييم المدارس على بيانات MT5 — 24 أكتوبر 2026",
        "",
        "هذا جرد آلي لعقود البيانات والكود، وليس شهادة اكتمال نظري أو ربحية. "
        "التقييم الفعلي لكل رمز يتطلب التحقق من توافر البيانات وحداثتها لدى الوسيط.",
        "",
        f"عدد المدارس المرجعية: {len(schools)}. عدد القواعد المحلية في السجل: "
        f"{sum(len(s.get('runtime_models') or []) for s in schools)} ربطًا بالنماذج؛ "
        "قد يرتبط النموذج بأكثر من مدرسة، لذلك لا يُجمع هذا العدد كعدد نماذج فريدة.",
        "",
        "| المدرسة | نماذج محلية مرتبطة | تقييم MT5 | السبب المحدد |",
        "|---|---:|---|---|",
    ]
    for school in schools:
        status, reason = classify(school)
        name = str(school["name_ar"]).replace("|", "\\|")
        lines.append(f"| {name} | {len(school.get('runtime_models') or [])} | {status} | {reason} |")
    lines += [
        "",
        "## حدود البيانات",
        "",
        "- شموع OHLC المكتملة، عداد التكات ووقت الجلسة: يمكن قراءتها من MT5 عند توفر الرمز والتاريخ.",
        "- الحجم الحقيقي، التاريخ الطويل، الأزواج المقارنة والتقويم: تُفحص لكل رمز/وسيط، ولا تُفترض.",
        "- عمق السوق قد يتاح كلقطة لبعض الرموز، لكنه ليس تاريخ عمق سوق مضمونًا. "
        "عداد التكات ليس سجل صفقات موقعة ولا Order Flow حقيقيًا.",
        "- القوائم المالية والتوزيعات والتقييم الأساسي للشركات ليست بيانات MT5 القياسية. "
        "وجود نص مرجعي أو حاسبة لا يجعله نموذج إرسال.",
        "",
        "## قراءة النتيجة",
        "",
        "المدارس ذات قواعد محلية قابلة للتقييم تنتج دلائل محددة وفق الكود الموجود؛ "
        "هذا لا يغطي كل تفسيرات المدرسة ولا يضمن إشارة أو صفقة. "
        "المدارس المرجعية فقط لا تدخل التنفيذ بوصفها وكلاء مستقلة.",
        "",
        "## خدمات البحث الخارجية في التطبيق عند الفحص",
        "",
        "Frankfurter وBLS: استجابة OK بعد تحديث بحثي يدوي. World Bank: انتهى الطلب بمهلة. "
        "Massive وFRED وGemini وGroq وOpenRouter: CONFIG_REQUIRED لعدم توفر مفاتيح في عملية التطبيق. "
        "هذه المصادر ليست مصدر سعر تنفيذ ولا تملك سلطة إرسال أوامر؛ MT5 وحده مصدر سعر التنفيذ.",
        "",
        "## معيار تطوير المدرسة إلى نطاق أوسع",
        "",
        "لكل قاعدة جديدة: تعريف مدخلات متاحة من MT5، شراء/بيع/إبطال، وقت تأكيد بلا نظر للمستقبل، "
        "وقف وهدف وتكلفة، واختبارات لحالات القبول والرفض. إذا غابت البيانات تُعلن القاعدة امتناعًا "
        "ولا تستبدلها ببيانات اصطناعية أو نموذج لغوي.",
        "",
    ]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
