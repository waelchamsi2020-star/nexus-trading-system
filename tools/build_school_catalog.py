"""Build the bilingual, referenced 58-entry school catalog offline.

This is a curated reference and development checklist, not 58 trading engines.
Canonical principles, operational checklists and Quant Trading AI house rules have separate
provenance. The builder never downloads data or calls a model or broker API.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nexus.strategies import registry_manifest

DEST = ROOT / "docs" / "school-catalog"
CATALOG_VERSION = "1.2.0"
PROTOCOL_VERSION = "1.0.0"

SOURCES = {
    "cmt": ("CMT Association: Technical Analysis — Modern Perspectives", "https://cmtassociation.org/wp-content/uploads/2019/01/Technical-Analysis-Modern-Perspectives-CMT-Association.pdf", "تأطير التحليل الفني ونظرية داو، وليس اعتماد عتبات نماذج Quant Trading AI", "Technical-analysis and Dow framework; no endorsement of Quant Trading AI thresholds"),
    "fidelity": ("Fidelity: Technical Indicator Guide", "https://www.fidelity.com/learning-center/trading-investing/technical-analysis/using-technical-analysis", "تصنيف الأدوات الفنية؛ قوائم التحقق التشغيلية من إعداد Quant Trading AI", "Technical tool categories; operational checklists are Quant Trading AI authored"),
    "indicators": ("Fidelity: Charting Indicators — definitions and calculations", "https://www.fidelity.com/products/atp/pdf/ATPChartingIndicators.pdf", "تعريفات المؤشرات ومحاور القمم والقيعان؛ ليس مصدر صيغة محور الجلسة", "Indicator and swing-pivot definitions; not the source of the session-pivot formula"),
    "session_pivots": ("Fidelity: Charting Platform Indicators Reference Guide, January 2020, pp. 20–21", "https://www.fidelity.com/webcontent/ap130058-research-experience-content/23.01/chartGuide/indicators.pdf", "صيغة محور الجلسة السابقة ومستويات الدعم والمقاومة؛ حدود الجلسة المحلية معلنة منفصلًا", "Prior-period pivot and support/resistance formulas; local session boundaries are declared separately"),
    "obv": ("Fidelity: On Balance Volume (OBV)", "https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/obv", "تراكم الحجم بإشارة تغير الإغلاق والتباعد؛ عتبات العودة والتأكيد قواعد النموذج المحلي", "Close-signed cumulative volume and divergence; reclaim/confirmation thresholds are local model rules"),
    "fractal_definition": ("MetaTrader 5 Help: Fractals", "https://www.metatrader5.com/en/terminal/help/indicators/bw_indicators/fractals", "تعريف فراكتل خمس شموع وإشارة إلى مرشح أليغيتر؛ النموذج المحلي ليس نظام بيل ويليامز الكامل", "Five-bar fractal definition and Alligator-filter context; the local model is not the full Bill Williams system"),
    "vintages": ("Federal Reserve Bank of St. Louis: ALFRED Help", "https://alfred.stlouisfed.org/help", "نسخ البيانات الاقتصادية وتواريخ الإتاحة؛ المرجع لا يضيف جلب بيانات خارجيًا", "Economic-data vintages and availability dates; reference does not add external data fetching"),
    "residual_income": ("CFA Institute: Residual Income Valuation", "https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/residual-income-valuation", "الدخل المتبقي وتكلفة حقوق الملكية؛ محفوظ مرجعيًا ولا توجد حاسبة دخل متبقٍ مسجلة", "Residual income and equity charge; reference only, with no registered residual-income calculator"),
    "yield_duration": ("CFA Institute: Yield-Based Bond Duration Measures and Properties", "https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/yield-based-bond-duration-measures-and-properties", "حساسية السعر للعائد وحدود التقريب الخطي؛ لا يدعي تنفيذ محرك منحنى أو خيارات", "Yield sensitivity and linear-approximation limits; no curve/option engine implementation is claimed"),
    "fibonacci": ("Fidelity: Fibonacci Retracement", "https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/fibonacci-retracement", "مستويات التصحيح وتمييز مستوى النصف عن نسب فيبوناتشي", "Retracement levels and distinction of the midpoint from Fibonacci ratios"),
    "elliott": ("Elliott Wave International: Impulse", "https://www.elliottwave.com/waveopedia/impulse/", "قيود الموجة الدافعة الاعتيادية وتمييز القطرية", "Ordinary impulse constraints and distinction from diagonals"),
    "waveopedia": ("Elliott Wave International: Waveopedia", "https://www.elliottwave.com/waveopedia/", "العائلات الموجية والدرجات؛ لا ينسخ المرجع المحتوى الكامل", "Wave families and degrees; the full source is not reproduced"),
    "harmonic": ("Scott Carney / Harmonic Trader: AB=CD", "https://harmonictrader.com/harmonic-patterns/abcd-pattern/", "هندسة تساوي الضلعين وتوافق النسب؛ حدود Quant Trading AI خاصة بالنموذج", "Equal-leg geometry and ratio confluence; Quant Trading AI tolerances are model specific"),
    "wyckoff": ("Wyckoff Analytics: The Wyckoff Method", "https://www.wyckoffanalytics.com/wyckoff-method/", "القوانين الثلاثة والسياق المرحلي؛ نموذج الكسر والاختبار محلي محدود", "Three laws and phase context; the local spring-test model is bounded"),
    "gann": ("MetaTrader 5 Help: Gann Tools", "https://www.metatrader5.com/en/terminal/help/objects/gann", "هندسة أدوات جان وحساسية المقياس فقط؛ لا يوثق جميع كتابات جان", "Gann drawing geometry and scale sensitivity only; not all Gann writings"),
    "ict": ("The Inner Circle Trader: Fair Value Gap & Market Structure Shifts", "https://www.youtube.com/watch?v=Bkt8B3kLATQ", "مصدر صاحب المنهج لمفاهيم الفجوة وتحول الهيكل؛ التطبيق المحلي تعريف معلن", "Author source for gap and structure-shift concepts; local implementation is explicitly defined"),
    "neowave": ("Glenn Neely: NEoWave Forecasting Explained", "https://www.neowave.com/neowave-explained.asp", "حدود المنهج وقابلية التأكيد؛ ليس كتاب قواعد نيو ويف الكامل", "Method scope and confirmation; not the complete NEoWave rulebook"),
    "fractals": ("MetaQuotes: iFractals", "https://www.mql5.com/en/docs/indicators/ifractals", "واجهة مؤشر الفركتال؛ لا تثبت وجود فوضى حتمية في السوق", "Fractal indicator interface; does not establish deterministic market chaos"),
    "depth": ("CME Group: Market by Order", "https://www.cmegroup.com/articles/faqs/market-by-order-mbo.html", "تمييز دفتر الأوامر عن الشموع وعدد التكات", "Distinguishes an order book from bars and tick counts"),
    "liquidity": ("CME Group: Liquidity Tool Methodology", "https://www.cmegroup.com/education/articles-and-reports/understanding-the-cme-liquidity-tool-methodology", "السبريد والعمق وتكلفة تنفيذ الحجم", "Spread, depth and size-dependent execution cost"),
    "cot": ("CFTC: Commitments of Traders", "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm", "تقارير تمركز مجمعة دورية، وليست تدفق صفقات آنيًا", "Periodic aggregate positioning, not real-time trade flow"),
    "calendar": ("MetaQuotes: CalendarValueHistory", "https://www.mql5.com/en/docs/calendar/calendarvaluehistory", "مصدر أحداث المنصة وإسناد الوقت إلى خادم التداول", "Terminal calendar events and trade-server time convention"),
    "sec": ("SEC: Beginners' Guide to Financial Statements", "https://www.sec.gov/about/reports-publications/investorpubsbegfinstmtguide", "القوائم المالية الأساسية؛ قوائم التحقق من إعداد Quant Trading AI", "Core financial statements; checklists are Quant Trading AI authored"),
    "company": ("CFA Institute: Company Analysis — Past and Present", "https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/company-analysis-past-and-present", "تقييم نشاط الشركة والأداء؛ لا يعتمد درجات محلية مفترضة", "Business and performance analysis; no endorsement of local scoring"),
    "industry": ("CFA Institute: Industry and Competitive Analysis", "https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/industry-and-competitive-analysis", "العوامل القطاعية والتنافسية", "Industry and competitive drivers"),
    "porter": ("CFA Institute: Industry Structure and Competitive Strategy", "https://rpc.cfainstitute.org/research/financial-analysts-journal/1980/industry-structure-and-competitive-strategy-keys-to-profitability", "القوى التنافسية الخمس", "Five competitive forces"),
    "valuation": ("CFA Institute: Equity Valuation — Concepts and Basic Tools", "https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/equity-valuation-concepts-basic-tools", "اختيار عائلة نموذج التقييم وحدود القيمة المقدرة", "Valuation-model selection and estimated-value limits"),
    "ddm": ("CFA Institute: Discounted Dividend Valuation", "https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/discounted-dividend-valuation", "تدفقات توزيعات الأرباح وشرط النمو النهائي", "Dividend cash flows and terminal-growth condition"),
    "fcf": ("CFA Institute: Free Cash Flow Valuation", "https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/free-cash-flow-valuation", "توافق تدفق الشركة أو المساهم مع معدل الخصم", "Matching firm/equity cash flows to the discount rate"),
    "multiples": ("CFA Institute: Market-Based Valuation — Price and Enterprise Value Multiples", "https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/market-based-valuation-price-enterprise-value-multiples", "تناسق بسط المضاعف ومقامه والمقارنة المناسبة", "Consistent multiple numerator/denominator and suitable comparables"),
    "behavior": ("CFA Institute: Behavioral Finance — Careers and Definition", "https://www.cfainstitute.org/insights/articles/behavioral-finance-careers", "تأثير الانحيازات في القرار؛ إجراءات ضبطها محلية", "Decision biases; mitigation procedures are locally authored"),
    "graham": ("CFA Institute: Investment vs. Speculation — Minsky Criteria", "https://blogs.cfainstitute.org/blog/2013/03/04/investment-vs-speculation-using-the-minsky-criteria/", "إسناد مفهوم التحليل والحفاظ على الأصل إلى جراهام؛ لا ينقل كتبه", "Attributes thorough analysis and principal safety to Graham; does not reproduce his books"),
    "garp": ("CFA Institute: GARP Investing — Golden or Garbage?", "https://rpc.cfainstitute.org/blogs/enterprising-investor/2019/garp-investing-golden-or-garbage", "تداخل القيمة والنمو وحدود النمط", "Value/growth overlap and style limits"),
    "index": ("Investor.gov: Index Funds", "https://www.investor.gov/introduction-investing/investing-basics/investment-products/mutual-funds-and-exchange-traded-4", "تتبع المؤشر والمخاطر والرسوم", "Index tracking, risk and fees"),
    "fund": ("SEC: Invest Wisely — Mutual Funds", "https://www.sec.gov/files/investor/pubs/inwsmf.htm", "نشرة الصندوق والأهداف والمصروفات", "Fund prospectus, objectives and expenses"),
    "commodity": ("CME Group: What Is Contango and Backwardation?", "https://www.cmegroup.com/education/courses/introduction-to-precious-metals/what-is-contango-and-backwardation.hideSubnav.educationIframe.html?hideAddThisExt=y&hideFooter=y&hideHeader=y&hideRightRail=y", "شكل منحنى العقود؛ لا يعني اتجاهًا مضمونًا للسعر الفوري", "Futures-curve shape; not a guaranteed spot-price direction"),
    "currency": ("CFA Institute: Capital Flows and the FX Market", "https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/capital-flows-and-the-fx-market", "أنظمة الصرف والتدفقات وتحديد الزوج", "Exchange-rate regimes, flows and currency-pair definition"),
    "currency_management": ("CFA Institute: Currency Management — An Introduction", "https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/currency-management-introduction", "العائد بالعملة المحلية والتحوط والكاري", "Domestic-currency return, hedging and carry"),
    "bond": ("Investor.gov: Bonds — FAQs", "https://www.investor.gov/introduction-investing/investing-basics/investment-products/bonds-or-fixed-income-products/bonds", "حقوق حامل السند ومخاطر الائتمان", "Bondholder cash-flow rights and credit risk"),
    "duration": ("CFA Institute: Interest Rate Risk and Return", "https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/interest-rate-risk-and-return", "المدة ومخاطر إعادة الاستثمار وأفق الحيازة", "Duration, reinvestment risk and holding horizon"),
}

DATA = {
    "completed_ohlc": ("شموع سعر مكتملة بتوقيت موثق", "Completed timestamped OHLC bars"),
    "long_history": ("تاريخ كافٍ وتكلفة تداول موثقة", "Sufficient history and documented trading costs"),
    "real_volume": ("حجم تداول فعلي موثق المصدر", "Source-identified actual traded volume"),
    "tick_volume": ("عدد تكات معلن كبديل نشاط فقط", "Tick counts explicitly identified as an activity proxy"),
    "paired_history": ("تاريخ أصل مقابل محدد ومتزامن", "Explicit synchronized comparison-asset history"),
    "session_clock": ("تعريف جلسة وخادم تداول ومنطقة زمنية", "Session, trade-server and time-zone definitions"),
    "positioning": ("ملف محلي لتمركز أو مشاعر مؤرخ بوقت النشر", "Local positioning/sentiment file with publication times"),
    "signed_trades": ("صفقات فعلية بسعر وحجم واتجاه مبادر موثق", "Actual trades with price, size and verified aggressor side"),
    "depth_history": ("دفتر أوامر تاريخي بالتحديثات والإلغاءات", "Historical order-book updates and cancellations"),
    "calendar": ("تقويم المنصة مع القيم وأوقات النشر الفعلية", "Terminal calendar values and actual publication times"),
    "financial_statements": ("قوائم مالية محلية مع الفترة ووقت إتاحتها", "Local financial statements with period and availability time"),
    "issuer_identity": ("هوية المصدر ونوع الأداة والعملة وحقوقها", "Issuer identity, instrument type, currency and rights"),
    "filings": ("إفصاحات وتقارير محلية موثقة المصدر", "Source-identified local filings and reports"),
    "macro_series": ("سلاسل اقتصادية محلية مع النسخة المتاحة وقت القرار", "Local economic series with their decision-time vintages"),
    "peer_data": ("بيانات شركات مقارنة متوافقة الفترة والمحاسبة", "Peer data with consistent periods and accounting"),
    "cash_forecasts": ("توقعات تدفق نقدي محلية وافتراضاتها", "Local cash-flow forecasts and assumptions"),
    "discount_rates": ("معدلات خصم ونمو وعملة وتواتر متناسقة", "Consistent discount/growth rates, currency and frequency"),
    "dividends": ("توزيعات نقدية موثقة وسياسة التوزيع", "Verified cash dividends and distribution policy"),
    "security_terms": ("شروط أصل الاستحقاق والكوبون والخيارات", "Maturity, coupon, seniority and embedded-option terms"),
    "yield_curves": ("منحنيات عائد وخصم وفروق ائتمان مؤرخة", "Timestamped yield/discount curves and credit spreads"),
    "commodity_balance": ("إنتاج واستهلاك ومخزون وتسليم موثق محليًا", "Locally verified production, use, inventories and delivery data"),
    "futures_curve": ("عقود آجلة منفصلة وتواريخ استحقاق وترحيل", "Individual futures contracts, expiries and roll history"),
    "fund_holdings": ("مكونات صندوق وصافي أصول ونشرة ورسوم", "Fund holdings, NAV, prospectus and fees"),
    "index_membership": ("عضوية وأوزان مؤشر كما عُرفت تاريخيًا", "Point-in-time index membership and weights"),
    "corporate_actions": ("تجزئات وتوزيعات وإصدارات وتغييرات أسهم", "Splits, distributions, issuance and share-count changes"),
    "asset_appraisals": ("تقديرات أصول والتزامات وتكلفة تصفية", "Asset/liability appraisals and liquidation costs"),
    "behavior_log": ("سجل قرارات وتوقعات وتعديلات مؤرخ", "Timestamped decision, forecast and revision journal"),
}

ENTRIES = []


def add(id, category, order, ar, en, rules, exceptions, requirements, refs, strategies=(), related=(), alias=None, scope=None):
    """Rule tuples: (Arabic, English[, provenance, source ids])."""
    rules = list(rules) + ENRICHMENTS.get(id, [])
    refs = list(dict.fromkeys(list(refs) + [source for rule in rules if len(rule) > 3 for source in rule[3]]))
    records = []
    for n, rule in enumerate(rules, 1):
        provenance = rule[2] if len(rule) > 2 else "OPERATIONAL_CHECKLIST"
        sources = rule[3] if len(rule) > 3 else []
        record = {"id": f"{id}.r{n:02d}", "version": CATALOG_VERSION,
                  "kind": provenance, "text_ar": rule[0], "text_en": rule[1],
                  "reference_ids": list(sources), "execution_authority": "REFERENCE_TEXT_ONLY"}
        if len(rule) > 4:
            record["formal_definition"] = rule[4]
        records.append(record)
    scope = scope or ("مرجع مبادئ وقائمة تحقق؛ لا يدّعي حصر المدرسة أو تنفيذ جميع نماذجها.", "Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.")
    if strategies:
        runtime = ("مرتبطة بنماذج Quant Trading AI محددة فقط؛ الربط لا يحوّل بقية قواعد المدرسة إلى إشارات تنفيذ.", "Mapped to specific Quant Trading AI models only; mapping does not make all other school rules executable.")
        execution = "BOUNDED_MODELS"
    elif category in ("fundamental", "approach") or any(k in requirements for k in ("signed_trades", "positioning", "depth_history")):
        runtime = ("مرجع محفوظ؛ يحتاج بيانات محلية موثقة وتنفيذًا حسابيًا منفصلًا قبل التصويت أو التنفيذ.", "Stored reference; verified local data and a separate numerical implementation are required before voting or execution.")
        execution = "LOCAL_DATA_REQUIRED"
    else:
        runtime = ("مرجع محفوظ؛ لا يوجد نموذج تداول مسجل يغطي هذه المدرسة في الإصدار الحالي.", "Stored reference; the current release has no registered trading model covering this school.")
        execution = "REFERENCE_ONLY"
    ENTRIES.append({
        "id": id, "category": category, "order": order, "name_ar": ar, "name_en": en,
        "rules_ar": [x["text_ar"] for x in records], "rules_en": [x["text_en"] for x in records], "rule_records": records,
        "exceptions_ar": [x[0] for x in exceptions], "exceptions_en": [x[1] for x in exceptions],
        "requirements": list(requirements), "requirements_ar": [DATA[k][0] for k in requirements], "requirements_en": [DATA[k][1] for k in requirements],
        "scope_ar": scope[0], "scope_en": scope[1], "runtime_scope_ar": runtime[0], "runtime_scope_en": runtime[1],
        "knowledge_status": "REFERENCED_RULES", "execution_status": execution,
        "complete_school": False, "strategy_ids": list(strategies), "mapped_strategy_ids": list(strategies),
        "related_ids": list(related), "alias_of": alias,
        "references": [{"id": key, "title": SOURCES[key][0], "url": SOURCES[key][1], "scope_ar": SOURCES[key][2], "scope_en": SOURCES[key][3]} for key in refs],
        "unavailable_data_policy_ar": "قائمة بيانات المدرسة تخص المرجع الشامل. لكل نموذج محدود عقد مدخلات مستقل؛ نقص مدخل مطلوب في عقده يمنع إشارته. البدائل التقريبية معلنة ولا تثبت توفر بيانات المدرسة الأصلية، والربط بالمرجع لا يمنح أهلية تنفيذ تلقائية.",
        "unavailable_data_policy_en": "School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.",
    })


def technical():
    add("ta_classical", "technical", 1, "التحليل الفني الكلاسيكي", "Classical Technical Analysis", [
        ("عرّف اتجاهًا صاعدًا بقمم وقيعان أعلى، وهابطًا بأدنى، ونطاقًا عند غياب التسلسل.", "Classify higher highs/lows, lower highs/lows, or a range when neither sequence holds."),
        ("الدعم والمقاومة مناطق مرتبطة بمحاور مؤكدة؛ دوّن مصدر المستوى وعدد اختباره.", "Treat support/resistance as zones around confirmed pivots; record anchors and tests."),
        ("لا يكتمل نموذج انعكاسي قبل كسر خط تأكيده؛ قياس ارتفاع النموذج إسقاط تقديري.", "A reversal pattern needs its confirmation break; projected height is an estimate."),
        ("عرّف إغلاق الاختراق وهامش التقلب وإعادة الاختبار وشروط الإبطال قبل الفحص.", "Specify breakout close, volatility tolerance, retest and invalidation before scanning."),
        ("لا تعد القمم اللاحقة معروفة عند ظهور النموذج؛ سجّل زمن تأكيد كل محور.", "Do not use later pivots at formation time; retain each pivot confirmation time."),
    ], [("الخط المرسوم بأثر رجعي قد يعطي تأكيدًا وهميًا.", "Retrospectively drawn lines can produce false confirmation."), ("الأهداف الهندسية ليست احتمالات نجاح مثبتة.", "Geometric targets are not validated success probabilities.")], ["completed_ohlc", "long_history"], ["cmt", "fidelity"], ["classic_reversal_patterns", "geometric_triangle_breakout", "support_bounce", "breakout_retest"], ["ta_dow", "ta_chart_patterns", "ta_market_structure"])
    add("ta_dow", "technical", 2, "نظرية داو", "Dow Theory", [
        ("افصل الاتجاه الرئيسي عن الثانوي والتذبذب القصير.", "Separate primary, secondary and short-term movements.", "SOURCE_PRINCIPLE", ["cmt"]),
        ("تأكيد متوسطين سوقيين مستقلين جزء من الصياغة التاريخية؛ تحليل رمز واحد بديل محدود.", "Independent market-average confirmation belongs to the historical formulation; one-symbol structure is a bounded proxy.", "SOURCE_PRINCIPLE", ["cmt"]),
        ("يستمر الاتجاه إلى أن تظهر قرينة انعكاس محددة، لا لمجرد توقع نهايته.", "Maintain the trend hypothesis until a defined reversal signal appears.", "SOURCE_PRINCIPLE", ["cmt"]),
        ("قيّم تأييد الحجم مع الاتجاه إذا كان حجمًا فعليًا متاحًا.", "Assess volume confirmation when actual traded volume is available.", "SOURCE_PRINCIPLE", ["cmt"]),
        ("نموذج Quant Trading AI يفحص محاور سعر مؤكدة؛ لا يثبت جميع مبادئ داو.", "Quant Trading AI checks confirmed price pivots; it does not verify every Dow principle.", "HOUSE_DEFINITION", []),
    ], [("المتوسطات الأصلية لا تساوي أي زوج أدوات مترابط عشوائيًا.", "Original market averages are not interchangeable with arbitrary correlated pairs."), ("يجب إعلان تأخر تأكيد الاتجاه.", "Trend-confirmation delay must be declared.")], ["completed_ohlc", "paired_history", "real_volume"], ["cmt"], ["dow_structure", "interasset_confirmation"], ["ta_intermarket"])
    add("ta_indicators", "technical", 3, "المؤشرات الفنية", "Technical Indicators", [
        ("احفظ الصيغة وفترة الحساب والمدخل وطريقة التمهيد والقيم الابتدائية.", "Store formula, lookback, input, smoothing and initialization."),
        ("المتوسطات أدوات اتجاه؛ المتذبذبات أدوات زخم؛ لا تستخدم تشبعًا كأمر عكسي وحده.", "Moving averages measure trend and oscillators measure momentum; an extreme alone is not a reversal order."),
        ("احسب التقاطع من قيم الشمعتين المكتملتين وليس من تبدل لحظي.", "Detect crossovers from two completed bars rather than intrabar flicker."),
        ("لا تجمع مؤشرات مشتقة من البيانات نفسها كأدلة مستقلة.", "Do not count indicators derived from the same data as independent evidence."),
        ("طابق السلسلة المحسوبة مع التهيئة؛ المتوسط الحجمي بتكات الأسعار ليس متوسط حجم صفقات فعلي.", "Match calculation and configuration; a tick-weighted mean is not actual trade-volume VWAP."),
    ], [("فروق تهيئة المنصة قد تغير أول قيم المؤشر.", "Platform initialization can change early indicator values."), ("إزاحات إيشيموكو يجب إسنادها للزمن الصحيح دون تسرب مستقبل.", "Ichimoku offsets require correct timestamps without future leakage.")], ["completed_ohlc", "long_history", "tick_volume"], ["indicators"], ["ema_cross", "rsi_rebound", "ichimoku_cross", "volatility_breakout", "atr_channel_break", "vwap_reclaim"], ["ta_quantitative"])
    add("ta_quantitative", "technical", 4, "التحليل الفني الإحصائي والكمي", "Quantitative / Statistical Technical Analysis", [
        ("حوّل الفرضية إلى إشارة ومدخل وهدف وإبطال يمكن إعادة حسابها.", "Translate the hypothesis into reproducible signal, entry, target and invalidation."),
        ("قسّم البيانات زمنيًا إلى تطوير وتحقق واختبار؛ امنع التسرب وإعادة اختيار الاختبار.", "Use chronological development, validation and test splits; prevent leakage and test-set reuse."),
        ("احسب الأداء بعد السبريد والعمولة والانزلاق والتمويل حيث ينطبق.", "Measure performance after spread, commission, slippage and applicable financing."),
        ("أعلن عدد المشاهدات وعدم اليقين والتراجع وحساسية المعلمات وتعدد التجارب.", "Report sample count, uncertainty, drawdown, parameter sensitivity and multiple trials."),
        ("درجة الانحراف المعياري لا تثبت طبيعية التوزيع أو استقراره؛ اختبر الفرضية منفصلًا.", "A z-score does not establish Gaussianity or stationarity; test those assumptions separately."),
        ("التعلم يقارن نتائج نسخ معلنة؛ لا يرفع حدود المخاطرة ولا يعيد كتابة المرجع ذاتيًا.", "Learning compares explicit versions; it does not raise risk limits or silently rewrite the reference."),
    ], [("المعامل غير القابل للقياس ليس صفرًا ولا نجاحًا.", "An undefined statistic is neither zero nor success."), ("عينات الصفقات المتداخلة ليست تجارب مستقلة.", "Overlapping trade samples are not independent trials.")], ["completed_ohlc", "long_history"], ["fidelity"], ["zscore_reversion", "regression_reentry", "band_reentry", "momentum_acceleration"], ["fa_quantitative"])
    add("ta_elliott", "technical", 5, "نظرية موجات إليوت", "Elliott Wave Theory", [
        ("في الدافعة الاعتيادية لا تتجاوز الموجة الثانية منشأ الأولى.", "In an ordinary impulse, wave two must not pass the start of wave one.", "SOURCE_PRINCIPLE", ["elliott"]),
        ("الموجة الثالثة ليست الأقصر بين الأولى والثالثة والخامسة.", "Wave three is not the shortest of waves one, three and five.", "SOURCE_PRINCIPLE", ["elliott"]),
        ("الرابعة لا تدخل مجال الأولى في الدافعة الاعتيادية؛ القطرية عائلة مختلفة.", "Wave four does not overlap wave one in an ordinary impulse; diagonals are a separate family.", "SOURCE_PRINCIPLE", ["elliott"]),
        ("تحقق من التقسيمات والدرجة؛ احتفظ بترقيم بديل وإبطاله بدل ترقيم وحيد يقيني.", "Check subdivisions and degree; keep alternate counts with invalidations rather than one certain count."),
        ("التناوب والنسب إرشادات ترجيح وليست جميعها قيودًا إلزامية.", "Alternation and ratios are ranking guidelines rather than universally mandatory rules."),
        ("التنفيذ الحالي فرضية ضلع أول وتصحيح ثم كسر؛ ليس محلل موجات دافعة وتصحيحية متداخلًا كاملًا.", "Current execution is a first-leg/pullback/break hypothesis, not a complete nested motive/corrective-wave parser.", "HOUSE_DEFINITION", []),
    ], [("لا تطبق قيود الدافعة على القطرية أو جميع التصحيحات.", "Do not apply ordinary impulse constraints to diagonals or every correction."), ("المحاور غير المؤكدة تبقى مرشحات.", "Unconfirmed pivots remain candidates.")], ["completed_ohlc", "long_history"], ["elliott", "waveopedia"], ["elliott_candidate", "elliott_impulse_reversal", "elliott_zigzag_reversal"], ["ta_neowave", "ta_fibonacci"])
    add("ta_harmonic", "technical", 6, "الهارمونيك", "Harmonic Analysis", [
        ("ثبّت نقاط النموذج بالترتيب الزمني؛ قس أطوال الأضلاع قبل حساب نسبها.", "Fix chronologically ordered pivots and measure leg lengths before ratios."),
        ("في تساوي الضلعين يقترب طول الضلع الأخير من الأول مع تصحيح وسطي وإسقاط متوافقين.", "Equal-leg geometry combines a final leg near the first-leg length with a compatible retracement and projection.", "SOURCE_PRINCIPLE", ["harmonic"]),
        ("لكل عائلة جدول نسب مستقل؛ لا تسمِّ نموذجًا لم يطابق جدول عائلته.", "Each pattern family needs its own ratio table; do not name unmatched geometry as that pattern."),
        ("احفظ سماحية القياس ومنطقة التوافق وتأكيد العودة والإبطال قبل ظهور الإشارة.", "Predefine measurement tolerance, confluence zone, reversal confirmation and invalidation."),
        ("نموذج Quant Trading AI المنفذ هو تساوي الضلعين فقط؛ العائلات الأخرى تحتاج وحدات واختبارات منفصلة.", "The executed Quant Trading AI model is equal-leg only; other families require separate modules and tests.", "HOUSE_DEFINITION", []),
    ], [("اكتمال النسب لا يضمن انعكاسًا.", "Ratio completion does not guarantee reversal."), ("تغيير المحاور بعد النتيجة يسبب انحيازًا.", "Changing pivots after observing the outcome introduces bias.")], ["completed_ohlc"], ["harmonic"], ["harmonic_abcd"], ["ta_harmonic_patterns", "ta_fibonacci"])
    add("ta_price_action", "technical", 7, "حركة السعر", "Price Action", [
        ("ابدأ بسياق اتجاه أو نطاق ومستوى معروف قبل الشمعة.", "Begin with trend/range context and a level known before the signal bar."),
        ("قارن جسم الشمعة وظلالها ومدى إغلاقها بالمجال السابق والتقلب.", "Compare body, wicks and close location with the prior range and volatility."),
        ("رفض المستوى يحتاج لمسًا ثم إغلاقًا يعود بعيدًا عنه؛ الظل وحده ليس اتجاهًا مؤكدًا.", "A rejection requires a level test and a close away from it; a wick alone is not confirmed direction."),
        ("عرّف دخول الاختراق أو إعادة الاختبار وإبطال القراءة خارج البنية.", "Specify breakout/retest entry and structural invalidation."),
        ("سجّل شمعة التأكيد والاقتباس الحالي؛ لا تدخل بعد ابتعاد السعر عن المنطقة المعلنة.", "Record confirmation bar and current quote; do not enter after price leaves the declared zone."),
    ], [("سلوك الشمعة لا يكشف هوية المشتري أو البائع.", "Bar behavior does not reveal participant identity."), ("إشارات وسط النطاق تحتاج شروطًا مختلفة عن الأطراف.", "Mid-range signals require different conditions from boundary signals.")], ["completed_ohlc"], ["fidelity"], ["support_bounce", "pin_rejection", "inside_bar_break", "engulfing", "breakout_retest"], ["ta_candlesticks", "ta_false_breakout"])
    add("ta_time", "technical", 8, "التحليل الزمني", "Time Analysis", [
        ("حدّد ساعة الخادم والتحويل الزمني والتوقيت الصيفي وأيام العطل.", "Define server time, conversion, daylight saving and holidays."),
        ("لا تقارن نافذة افتتاح غير مكتملة بنافذة مكتملة.", "Do not compare an incomplete opening window with a completed one."),
        ("تعريف دورة أو موسمية يجب تثبيته قبل الاختبار لا بعد مطابقة قمم سابقة.", "Fix cycle/seasonality definitions before testing rather than fitting past peaks."),
        ("احسب انتهاء شمعة الشهر بالتقويم وليس بعدد ثابت من الثواني.", "Use calendar arithmetic for monthly closes rather than fixed seconds."),
        ("نموذج الافتتاح الحالي يستخدم نافذة معلنة بالتوقيت العالمي؛ ليست جلسة بورصة مستنتجة تلقائيًا.", "The local opening-range model uses a declared UTC window, not an automatically inferred exchange session.", "HOUSE_DEFINITION", []),
    ], [("اختلاف تقويم العقود يغير عينات الزمن.", "Different contract calendars change time samples."), ("الدورية المقدرة تحتاج تاريخًا يغطي عدة دورات.", "Estimated periodicity requires history spanning several cycles.")], ["completed_ohlc", "session_clock", "long_history"], ["indicators", "calendar"], ["utc_opening_range", "seasonality"], ["ta_cycles"])
    add("ta_sentiment", "technical", 9, "المشاعر والتمركز", "Sentiment / Positioning Analysis", [
        ("حدّد ما تقيسه العينة: استطلاع أو خيارات أو تمركز أو سجل داخلي.", "Identify the sample: survey, options, positioning or internal journal."),
        ("استخدم وقت نشر البيانات وليس تاريخ الفترة التي تصفها في الاختبار.", "Use publication time, not the described period date, in backtests."),
        ("تقارير تمركز المتداولين دورية مجمعة ولا تمثل أوامر لحظية.", "Commitments-of-Traders reports are periodic aggregates, not live orders.", "SOURCE_PRINCIPLE", ["cot"]),
        ("لا تفترض أن التطرف يعني انعكاسًا فوريًا؛ اختبر الاستمرار والانعكاس كفرضيتين.", "An extreme does not imply immediate reversal; test continuation and reversal separately."),
        ("لا تستنتج مشاعر المشاركين الحقيقية من لون الشمعة وحده.", "Do not infer actual participant sentiment from candle color alone."),
    ], [("اختلاف عينة الوسيط عن السوق الكلي يجب إظهاره.", "Broker-sample versus whole-market differences must be visible."), ("الغياب ليس مشاعر محايدة بل بيانات ناقصة.", "Missing sentiment is missing data, not neutral sentiment.")], ["positioning", "completed_ohlc"], ["cot", "behavior"], related=["fa_behavioral"])
    add("ta_ict", "technical", 10, "منهج ICT", "Inner Circle Trader (ICT)", [
        ("عرّف نطاق السياق والقمم والقيعان المعروفة قبل البحث عن سحب مستوى.", "Define context range and known highs/lows before detecting a sweep."),
        ("الفجوة الثلاثية الصاعدة هي فراغ بين قمة الأولى وقاع الثالثة، والهابطة عكسه؛ الشموع مكتملة.", "A bullish three-bar gap lies between bar-one high and bar-three low; bearish is mirrored, using completed bars.", "HOUSE_DEFINITION", []),
        ("تحول الهيكل يتطلب كسر محور مؤكد وفق تعريف إغلاق أو ظل معلن.", "A structure shift needs a confirmed-pivot break under a declared close/wick convention."),
        ("افصل الدليل السعري عن ادعاء وجود أوامر مؤسسات؛ السعر وحده لا يثبت هوية الأوامر.", "Separate price evidence from institutional-order claims; price alone does not prove order identity."),
        ("ثبّت منطقة أول عودة وشروط إبطالها ونافذة الجلسة بدل إعادة رسمها بعد النتيجة.", "Fix first-return zone, invalidation and session window rather than redrawing after the outcome."),
    ], [("مصطلحات المنهج تختلف بحسب الدرس والإصدار؛ المرجع يصرح بتعريفه المحلي.", "Terminology varies by lesson/version; the catalog states its local definition."), ("لا تعتبر كل فجوة دليلًا مستقلًا عن حركة السعر ذاتها.", "Do not count a gap as evidence independent of its underlying price move.")], ["completed_ohlc", "session_clock"], ["ict"], ["smc_ict_proxy", "fvg_first_return", "smt_proxy", "four_school_confluence"], ["ta_liquidity", "ta_smart_money", "ta_market_structure"])
    add("ta_wyckoff", "technical", 11, "ويكوف", "Wyckoff Method", [
        ("القوانين الأساسية هي العرض والطلب، السبب والنتيجة، والجهد والنتيجة.", "The three laws concern supply/demand, cause/effect and effort/result.", "SOURCE_PRINCIPLE", ["wyckoff"]),
        ("قارن الحركة بالحجم الحقيقي عندما يتوفر؛ عدد التكات مقياس نشاط محدود.", "Compare price movement with actual volume when available; tick count is a bounded activity measure."),
        ("لا تسمِّ النطاق تجميعًا أو توزيعًا يقينيًا؛ احتفظ بإعادة التجميع وإعادة التوزيع كبدائل.", "Do not label a range as certain accumulation/distribution; retain reaccumulation/redistribution alternatives."),
        ("السحب أسفل نطاق والعودة ثم اختبار أخف يحتاج نطاقًا سابقًا وابتعادًا وتأكيدًا.", "A spring, return and lighter test require a pre-existing range, departure and confirmation."),
        ("قياس السبب بالأشكال النقطية يحتاج بياناته وخوارزمية أعمدته، ولا يستبدل بعدد شموع عشوائي.", "Point-and-figure cause measurement needs explicit data and column construction, not arbitrary bar counts."),
    ], [("أحداث المراحل ليست قائمة تظهر كلها في كل حالة.", "Not every phase event occurs in every case."), ("المنفذ الحالي نموذج سحب واختبار محلي فقط.", "Current execution covers only a local spring-test model.")], ["completed_ohlc", "real_volume", "tick_volume"], ["wyckoff"], ["wyckoff_spring"], ["ta_volume_theories", "ta_supply_demand"])
    add("ta_gann", "technical", 12, "جان", "Gann Analysis", [
        ("ثبّت وحدة السعر ووحدة الزمن والمقياس؛ زاوية الرسم البصري تتغير مع تمديد المحور.", "Fix price/time units and scale; visual angles change when axes are stretched."),
        ("أدوات المروحة والشبكة تمثل علاقات هندسية من مرساة معلنة.", "Fan/grid tools express geometric relationships from a declared anchor.", "SOURCE_PRINCIPLE", ["gann"]),
        ("توقع نقطة زمنية يحتاج نافذة سماحية وشرط سعر مستقل وإبطالًا.", "A projected time point needs a tolerance window, independent price condition and invalidation."),
        ("شبكة الجذر المحلية تستخدم تطبيع التقلب وإزاحة ربع وحدة؛ هذه قاعدة Quant Trading AI وليست قانونًا مثبتًا لجميع أسواق جان.", "The local root grid uses volatility normalization and a quarter-unit shift; this is a Quant Trading AI rule, not a universal Gann law.", "HOUSE_DEFINITION", []),
        ("افصل الإسقاط الحسابي عن نسبة نجاحه التي تحتاج اختبارًا مستقلًا.", "Separate the arithmetic projection from its independently tested success rate."),
    ], [("لا يثبت هذا المرجع جميع دورات جان أو مربع التسعة التاريخي.", "This catalog does not establish all Gann cycles or historical Square-of-Nine rules."), ("تغيير المقياس بعد الإشارة يبطل المقارنة.", "Changing scale after the signal invalidates comparisons.")], ["completed_ohlc", "session_clock", "long_history"], ["gann"], ["gann"], ["ta_time", "ta_cycles"])
    add("ta_fibonacci", "technical", 13, "فيبوناتشي", "Fibonacci Analysis", [
        ("اختر ضلعًا مؤكدًا من قاع إلى قمة أو عكسه ثم احفظ المرساة.", "Select and retain a confirmed low-to-high or high-to-low anchor leg."),
        ("قِس التصحيح كنسبة إلى طول الضلع؛ نسب شائعة هي 38.2 و61.8 بالمئة.", "Measure retracement as a fraction of leg length; common levels include 38.2% and 61.8%.", "SOURCE_PRINCIPLE", ["fibonacci"]),
        ("النصف مستوى شائع في الأدوات لكنه ليس نسبة فيبوناتشي أصلية.", "The midpoint is commonly plotted but is not an original Fibonacci ratio.", "SOURCE_PRINCIPLE", ["fibonacci"]),
        ("الإسقاط من نهاية التصحيح يختلف عن قياس تصحيح داخل الضلع.", "Projection from a retracement endpoint differs from within-leg retracement."),
        ("عامل المستوى كمنطقة مرشحة تتطلب تأكيدًا، ولا تبحث عن نسبة توافق بأثر رجعي.", "Treat a level as a candidate zone requiring confirmation; avoid retrospective ratio fitting."),
    ], [("اختيار مرساة مختلفة يغير القراءة.", "Different anchors change the reading."), ("توافق مستويات عدة لا يضمن انعكاس السعر.", "Multiple-level confluence does not guarantee reversal.")], ["completed_ohlc"], ["fibonacci"], ["fib_retracement", "harmonic_abcd"], ["ta_harmonic", "ta_elliott"])
    add("ta_market_structure", "technical", 14, "هيكل السوق", "Market Structure", [
        ("احفظ قاعدة تأكيد المحور وعدد الشموع على جانبيه ووقت إتاحته.", "Store pivot confirmation rule, left/right bar counts and availability time."),
        ("عرّف القمم والقيعان الخارجية والداخلية وفق نفس الدرجة الزمنية.", "Define external/internal highs and lows at a consistent time scale."),
        ("كسر الهيكل واستمرار الاتجاه وتغير الشخصية تسميات تحتاج تعريفًا محددًا.", "Structure break, continuation and character change need explicit definitions."),
        ("اعتبر كسر الإغلاق وكسر الظل أحداثًا مختلفة، وسجّل المستوى الذي انكسر.", "Treat close and wick breaks separately and record the broken level."),
        ("عند تناقض درجات الهيكل أعلن التضارب بدل دمجها في اتجاه واحد.", "Expose cross-scale structural conflicts rather than merging them into one direction."),
    ], [("تأكيد القمة يتأخر عن وقت حدوثها.", "A pivot becomes confirmed after its occurrence."), ("هيكل السعر لا يثبت توزيع ملكية أوامر السوق.", "Price structure does not establish order ownership.")], ["completed_ohlc"], ["cmt"], ["dow_structure", "breakout_retest", "donchian_20"], ["ta_dow", "ta_ict"])
    add("ta_supply_demand", "technical", 15, "العرض والطلب", "Supply & Demand Zones", [
        ("منطقة السعر نموذج استجابة تاريخية؛ ليست قياسًا مباشرًا لكمية العرض والطلب المتبقية.", "A price zone models historical response, not directly measured remaining supply/demand."),
        ("عرّف الأساس السابق والاندفاع خارج النطاق وحدود المنطقة قبل العودة.", "Define the base, displacement and zone bounds before a return."),
        ("احفظ عدد الزيارات والعمر والكسر السابق؛ أول عودة تختلف عن إعادة الاختبار المتكررة.", "Store visits, age and prior breaks; a first return differs from repeated tests."),
        ("أبطل المنطقة عند حدث كسر معلن ولا تنقل الحد بعد الخسارة.", "Invalidate at a declared break event and do not move the boundary after a loss."),
        ("لا تسمِّ المنطقة أمرًا مؤسسيًا إلا ببيانات تثبت ذلك.", "Do not label the zone an institutional order without supporting order data."),
    ], [("الظلال الواسعة قد تجعل حجم الوقف غير مناسب.", "Wide wicks can make the stop size unsuitable."), ("جميع قواعد حد الاندفاع والعمر محلية قابلة للاختبار.", "Displacement and expiry thresholds are local testable definitions.")], ["completed_ohlc"], ["fidelity"], ["supply_demand_proxy", "base_first_return"], ["ta_liquidity", "ta_smart_money"])
    add("ta_liquidity", "technical", 16, "السيولة", "Liquidity Analysis", [
        ("سيولة التنفيذ تقاس بالسبريد والعمق والتكلفة للحجم المقترح.", "Execution liquidity concerns spread, depth and cost at the proposed size.", "SOURCE_PRINCIPLE", ["liquidity"]),
        ("قمم متساوية أو قيعان سابقة مستويات مرشحة؛ لا تثبت حجم أوامر الوقف.", "Equal highs/prior lows are candidate levels, not proof of stop-order size."),
        ("السحب المحلي عبور حد سابق ثم إغلاق عائد داخله؛ احفظ نافذة حساب الحد.", "A local sweep crosses a prior boundary then closes back inside; retain the boundary window.", "HOUSE_DEFINITION", []),
        ("افصل سحب المستوى عن استمرار الاختراق بواسطة شرط العودة والمهلة.", "Separate sweeps from sustained breakouts using return and expiry conditions."),
        ("عند توفر العمق سجّل الإلغاء والتنفيذ وتغير السبريد؛ العمق وحده ليس سيولة مضمونة.", "With depth, record cancellations, trades and spread changes; displayed depth alone is not guaranteed liquidity."),
    ], [("الوقف غير ظاهر عادة في دفتر علني كامل.", "Stop orders are generally not fully visible in public books."), ("الأوامر المعروضة يمكن إلغاؤها قبل وصول الطلب.", "Displayed orders may be canceled before execution.")], ["completed_ohlc", "depth_history"], ["liquidity", "depth"], ["failed_range_break", "smc_ict_proxy", "smt_proxy"], ["ta_order_flow", "ta_false_breakout"])
    add("ta_smart_money", "technical", 17, "مفاهيم الأموال الذكية", "Smart Money Concepts", [
        ("عرّف مجموعة المفاهيم والنسخة بدل اسم عام غير قابل للفحص.", "Declare the concept set and version instead of an untestable umbrella name."),
        ("حدد تحول الهيكل والاندفاع والمنطقة والفجوة بقواعد سعر قابلة لإعادة الإنتاج.", "Define structure shift, displacement, zone and gap with reproducible price rules."),
        ("رتّب السياق ثم الحدث ثم التأكيد ثم التنفيذ، مع مهلة انتهاء لكل مرشح.", "Order context, event, confirmation and execution, with candidate expiry."),
        ("إسناد الهوية لمؤسسة أو صانع سوق يحتاج بيانات مشاركين ولا يستنتج من شموع.", "Institution/market-maker attribution needs participant data and is not inferred from bars."),
        ("المفاهيم المتداخلة تشارك عائلة دليل واحدة لمنع تضخيم التصويت.", "Overlapping concepts share an evidence family to avoid vote inflation."),
    ], [("لا يوجد معيار عالمي وحيد لجميع استعمالات المصطلح.", "There is no single universal standard for every use of the term."), ("نجاح تسمية بأثر رجعي لا يثبت قاعدة دخول.", "A convincing retrospective label does not validate an entry rule.")], ["completed_ohlc", "depth_history"], ["ict", "depth"], ["smc_ict_proxy", "fvg_first_return", "base_first_return", "smt_proxy"], ["ta_ict", "ta_supply_demand", "ta_liquidity"])
    add("ta_volume", "technical", 18, "تحليل الحجم", "Volume Analysis", [
        ("ميّز حجم الصفقات الفعلي عن عدد تحديثات السعر والحجم غير المتاح.", "Distinguish actual trade volume, quote-update count and unavailable volume."),
        ("قارن الحجم بمرجع سابق مماثل الجلسة والأداة، لا بعتبة مطلقة عامة.", "Compare volume with prior similar-session/instrument observations, not a universal absolute threshold."),
        ("الاختراق المصحوب بنشاط أعلى قرينة تحتاج اختبارًا؛ الحجم لا يحدد اتجاه الصفقة وحده.", "Higher-activity breakouts are a testable clue; volume alone does not determine side."),
        ("المتوسط المرجح الحقيقي يحتاج سعرًا وحجمًا فعليين؛ النسخة المعتمدة على التكات تسمى تقريبًا.", "True VWAP needs prices and actual sizes; a tick-count version is labeled a proxy."),
        ("لا تبنِ توزيع الحجم حسب السعر من حجم شمعة مجمع دون افتراض توزيع معلن.", "Do not infer volume-at-price from aggregated bar volume without an explicit allocation assumption."),
    ], [("حجم وسيط واحد ليس الحجم العالمي لسوق العملات.", "One broker's volume is not global FX volume."), ("استبدال الحجم المفقود بصفر يفسد المقارنة.", "Replacing missing volume with zero corrupts comparisons.")], ["completed_ohlc", "real_volume", "tick_volume"], ["indicators", "depth"], ["vwap_reclaim", "tick_activity_rejection", "order_flow", "obv_divergence_reclaim"], ["ta_volume_theories", "ta_order_flow"])
    add("ta_candlesticks", "technical", 19, "الشموع اليابانية", "Japanese Candlestick Patterns", [
        ("عرّف الجسم والظل الأعلى والأسفل كنسب من مدى الشمعة مع منع المدى الصفري.", "Define body and upper/lower wicks as range fractions; reject zero range."),
        ("الابتلاع يتعلق بعلاقة الجسمين وفق تعريف معلن؛ ابتلاع المدى الكامل شرط مختلف.", "Engulfing concerns bodies under an explicit convention; full-range engulfing is different."),
        ("الدوجي والظل الطويل إشارات تردد أو رفض تحتاج سياق مستوى واتجاه.", "Doji and long wicks suggest indecision/rejection only with level/trend context."),
        ("النموذج المتعدد يحتاج ترتيبًا زمنيًا وشروط فجوة صالحة للأداة والجلسة.", "Multi-bar patterns need chronological order and gap assumptions appropriate to instrument/session."),
        ("انتظر اكتمال الشموع وتأكيدًا معلنًا؛ لا تصوّت للنموذج وللبرايس أكشن كدليلين مستقلين.", "Wait for completed bars and declared confirmation; do not count the same candlestick and price-action event twice."),
    ], [("سوق مستمر قد لا يحقق فجوات يومية لبعض النماذج التقليدية.", "Continuous markets may lack traditional daily-gap conditions."), ("اسم الشمعة لا يحدد وقفًا أو حجمًا تلقائيًا.", "A candle name does not automatically define stop or size.")], ["completed_ohlc"], ["fidelity", "indicators"], ["engulfing", "pin_rejection", "inside_bar_break"], ["ta_price_action"])
    add("ta_chart_patterns", "technical", 20, "الأنماط السعرية والهندسية", "Chart / Geometric Patterns", [
        ("افحص الرأس والكتفين والقمتين أو القاعين بمحاور مؤكدة وتناظر معلن وخط عنق.", "Test head/shoulders and double tops/bottoms using confirmed pivots, explicit symmetry tolerance and neckline."),
        ("المثلث يحتاج حدودًا متقاربة وعدة لمسات وتسلسلًا قبل الاختراق.", "A triangle needs converging bounds, multiple touches and pre-break chronology."),
        ("الراية والوتد والمستطيل عائلات مختلفة؛ لا تطلق الاسم من شكل تقريبي فقط.", "Flags, wedges and rectangles are separate families; approximate resemblance is insufficient."),
        ("دون الكسر المؤكد تبقى الهندسة مرشحًا؛ الهدف إسقاط ارتفاع معلن.", "Without confirmed breakout, geometry remains a candidate; targets use declared height projection."),
        ("احفظ جودة الملاءمة والانحرافات وعمر النموذج وأحداث الإبطال.", "Store fit quality, residuals, age and invalidation events."),
    ], [("معلمات السماحية وخط العنق خاصة بالتطبيق.", "Tolerance and neckline parameters are implementation specific."), ("لا ينفذ الإصدار كل الأعلام والأوتاد والعائلات الممكنة.", "The release does not execute every flag, wedge or possible family.")], ["completed_ohlc", "long_history"], ["fidelity"], ["classic_reversal_patterns", "geometric_triangle_breakout", "darvas_box"], ["ta_classical"])
    add("ta_false_breakout", "technical", 21, "الاختراق الكاذب", "False Breakout", [
        ("احسب مستوى النطاق من الشموع السابقة للإشارة فقط.", "Calculate the range boundary only from bars preceding the signal."),
        ("عبور ثم عودة داخل الحد شرط مختلف عن مجرد لمس الحد.", "A cross then return is distinct from a boundary touch."),
        ("عرّف هل الفشل يقع في الشمعة نفسها أو بعد عدد محدد من الشموع.", "Specify same-bar failure or a bounded later-return window."),
        ("تأكيد الإغلاق وحجم الاختراق بالنسبة للتقلب يضبطان ضوضاء المستوى.", "Close confirmation and breakout size relative to volatility control boundary noise."),
        ("الإبطال وراء أقصى امتداد للسحب؛ الخروج يتبع خطة معلنة.", "Invalidation lies beyond the sweep extreme; exit follows a declared plan."),
    ], [("العودة اللحظية قبل إغلاق الشمعة قد تختفي.", "An intrabar return may disappear before close."), ("لا تفترض تعمد اصطياد الوقف من الحدث السعري.", "Do not infer deliberate stop hunting from price behavior.")], ["completed_ohlc"], ["fidelity"], ["failed_range_break", "pin_rejection", "tick_activity_rejection"], ["ta_liquidity", "ta_price_action"])
    add("ta_neowave", "technical", 22, "نيو ويف", "NEoWave", [
        ("المنهج توسعة متخصصة للتحليل الموجي، وليس اسمًا بديلًا لفرضية موجتين محلية.", "The method is a specialized wave-analysis extension, not another name for a local two-leg hypothesis."),
        ("حدد طريقة بناء الموجات والدرجة وقياس السعر والزمن قبل محاولة الترقيم.", "Declare wave construction, degree, price and time measurements before labeling."),
        ("افصل شرط بناء النموذج عن التأكيد اللاحق؛ الترقيم قبل التأكيد يبقى مرشحًا.", "Separate pattern formation from later confirmation; pre-confirmation labels remain candidates."),
        ("كل نموذج يحتاج مصدرًا وقيودًا محددة واختبارات حالات قبل إضافته كمحلل تنفيذي.", "Each model needs identified sources, precise constraints and case tests before executable registration."),
        ("المرجع الحالي يحفظ نطاق المنهج وخطة ترميزه؛ لا ينسخ كتابه ولا يدّعي محلل نيو ويف كاملًا.", "This catalog stores scope and an implementation plan; it neither reproduces the book nor claims a complete NEoWave parser."),
    ], [("قواعد إليوت الأساسية لا تكفي لإعلان اكتمال نيو ويف.", "Basic Elliott rules do not establish complete NEoWave coverage."), ("اختلاف أخذ العينات قد يغير الوحدة الموجية.", "Sampling choices may change wave units.")], ["completed_ohlc", "long_history", "session_clock"], ["neowave"], related=["ta_elliott"], scope=("نطاق منهجي وقائمة متطلبات تطوير موثقة، وليس قواعد نيو ويف الأصلية كاملة.", "Documented method scope and development prerequisites, not the entire original NEoWave rulebook."))
    add("ta_order_flow", "technical", 23, "تدفق الأوامر", "Order Flow", [
        ("تدفق التنفيذ يتطلب صفقات فعلية بحجم وسعر واتجاه مبادر؛ تحديث الاقتباس ليس صفقة.", "Executed flow needs actual trades with size, price and aggressor side; a quote update is not a trade."),
        ("دلتا التنفيذ هي حجم شراء مبادر ناقص بيع مبادر وفق تصنيف موثق.", "Execution delta is aggressive buy volume minus aggressive sell volume under a documented classifier."),
        ("دفتر العمق يتطلب أوامر معروضة وتعديلات وإلغاءات؛ صفقة منفذة حدث منفصل.", "Depth needs displayed orders, updates and cancellations; a completed trade is a separate event.", "SOURCE_PRINCIPLE", ["depth"]),
        ("بصمة السعر تجمع الحجم حسب السعر والجانب؛ الخريطة الحرارية تحتاج تاريخ سيولة معروضة.", "A footprint aggregates size by price and side; a heatmap requires historical displayed liquidity."),
        ("الامتصاص مرشح يستلزم تدفقًا فعليًا مع استجابة سعر محدودة، لا ظل شمعة وحده.", "Absorption candidates need actual flow with limited price response, not a candle wick alone."),
        ("وكيل النشاط الحالي يستخدم التكات وموقع الإغلاق؛ ليس دلتا أو بصمة أو دفترًا حقيقيًا.", "The current activity agent uses tick counts and close location; it is not true delta, footprint or book analysis.", "HOUSE_DEFINITION", []),
    ], [("تعذر تحديد جانب المبادرة يمنع حساب دلتا موثوقة.", "Unverified aggressor side prevents reliable delta."), ("العمق المحلي قد يغطي وسيطًا أو سوقًا واحدًا فقط.", "Local depth may cover only one broker or venue.")], ["signed_trades", "depth_history", "tick_volume"], ["depth", "liquidity"], ["order_flow", "tick_activity_rejection"], ["ta_volume", "ta_liquidity"])
    add("ta_chaos_fractal", "technical", 24, "الفوضى والفركتال", "Chaos & Fractal Analysis", [
        ("افصل فراكتل المحور الفني عن البعد الفركتالي وعن ادعاء نظام فوضوي حتمي.", "Separate a technical pivot fractal, fractal dimension and a deterministic-chaos claim."),
        ("فراكتل خمس شموع لا يؤكد الوسط قبل اكتمال الشمعتين اللاحقتين.", "A five-bar pivot fractal cannot confirm its middle bar before two subsequent bars complete."),
        ("تقدير البعد أو معامل هيرست يحتاج طريقة وعينة وفحص حساسية وانحياز.", "Dimension/Hurst estimation needs a method, sample, sensitivity and bias checks."),
        ("إزاحة مؤشر مرسومة للأمام لا تعني إتاحة قيمة مستقبلية للتحليل.", "A forward chart offset does not make future observations available."),
        ("لا تحوّل مجرد شكل متكرر إلى دليل على قابلية التنبؤ الحتمي.", "A recurring shape does not establish deterministic predictability."),
    ], [("كسر الفراكتل المحلي لا ينفذ مرشحات أليغيتر ولا جميع نظام بيل ويليامز، ولا يثبت الفوضى الحتمية.", "The local fractal break implements neither Alligator filters nor the full Bill Williams system, and does not establish deterministic chaos."), ("تقديرات السلاسل القصيرة قد تكون غير مستقرة.", "Short-series estimates can be unstable.")], ["completed_ohlc", "long_history"], ["fractals", "fractal_definition"], ["fractal_5_breakout"], related=["ta_market_structure", "ta_cycles"])
    add("ta_cycles", "technical", 25, "نظرية الدورات", "Cycle Theory", [
        ("حدّد هل الدورة تقويمية أم طيفية أم ناتجة من نشاط اقتصادي.", "Identify calendar, spectral or economic cycles."),
        ("ثبّت إزالة الاتجاه وطول العينة ونطاق الفترات قبل تقدير الدورة.", "Predefine detrending, sample length and searched periods."),
        ("اختبر الاستقرار والطور والسعة على فترة لاحقة ولا تعدّل الطور لاستيعاب كل قمة.", "Test stability, phase and amplitude on later data rather than refitting every peak."),
        ("الموسمية المحلية للعملات تستخدم أشهرًا سابقة مكتملة فقط مع حد أدنى معلن للعينات.", "Local FX seasonality uses only completed prior same-month samples with a declared sample minimum.", "HOUSE_DEFINITION", []),
        ("قس أثر تعدد الفترات المجربة وقارن بنموذج بلا دورة.", "Account for multiple searched periods and compare with a no-cycle baseline."),
    ], [("الدورية المقدرة قد تتلاشى مع تغير نظام السوق.", "Estimated periodicity may disappear after regime change."), ("الموسمية الشهرية ليست محلل دورات شاملًا.", "Monthly seasonality is not a comprehensive cycle engine.")], ["completed_ohlc", "long_history", "session_clock"], ["indicators"], ["seasonality", "utc_opening_range"], ["ta_time", "fa_macro"])
    add("ta_intermarket", "technical", 26, "الارتباط بين الأسواق", "Intermarket Analysis", [
        ("صرّح بالأصل المقابل من هوية الأداة والعملات لا من تشابه الاسم.", "Declare comparison assets from instrument/currency identity, not similar names."),
        ("زامن الشموع وفترات التداول؛ لا تقارن قيمة حالية بأصل مغلق قديم.", "Synchronize bars and sessions; do not compare a live asset with stale closed-market data."),
        ("احسب الارتباط على العوائد غالبًا؛ ارتباط مستويات السعر قد يكون زائفًا.", "Prefer returns for correlation; price-level correlations may be spurious."),
        ("الارتباط متغير ولا يثبت سببية أو تكاملًا مشتركًا أو قيادة زمنية.", "Correlation varies and does not prove causality, cointegration or lead/lag."),
        ("اختبر سحب حدود مختلفًا عن كسر مشترك، مع تعريف نافذة وسماحية مسبق.", "Test divergent sweeps separately from joint breakouts with predeclared windows/tolerances."),
    ], [("الأزواج المحلية الحالية محددة ببيانات العملات المعلنة، وليست جميع علاقات العالم.", "Current local pairs use explicit currency metadata, not all global relationships."), ("مضاعفات سعر مختلفة تحتاج تطبيعًا مناسبًا.", "Different price scales need suitable normalization.")], ["completed_ohlc", "paired_history", "long_history"], ["cmt"], ["interasset_confirmation", "smt_proxy"], ["ta_dow", "fa_currency", "fa_commodity"])
    add("ta_volume_theories", "technical", 27, "نظريات الحجم", "Volume Theories", [
        ("هذا بند مرجعي متداخل مع تحليل الحجم ويحتفظ به لترتيب قائمة المستخدم.", "This overlapping volume entry is retained to preserve the user's list."),
        ("الرصيد الحجمي يضيف أو يطرح الحجم وفق تغير الإغلاق؛ ليس دلتا صفقات.", "On-balance volume signs volume by close change; it is not trade delta."),
        ("التراكم والتوزيع المبني على موقع الإغلاق تقدير رياضي، وليس قياس هوية المشاركين.", "Close-location accumulation/distribution is an arithmetic estimate, not participant identification."),
        ("تحليل الانتشار والحجم يقارن المدى والإغلاق والحجم بسياق سابق؛ لا يثبت نية مؤسسية.", "Volume-spread analysis compares range, close and volume with prior context; it does not prove institutional intent."),
        ("لا تمنح المتغيرات المشتقة من الحجم نفسه أصواتًا مستقلة متعددة.", "Do not give multiple independent votes to transformations of the same volume evidence."),
    ], [("الحجم الحقيقي مطلوب لقراءة حجم حقيقية، والتكات تقريب معلن.", "Actual-volume analysis requires actual volume; tick counts remain labeled proxies."), ("لا تنفذ جميع مؤشرات الحجم بمجرد حفظ تعريفها.", "Storing definitions does not implement every volume indicator.")], ["completed_ohlc", "real_volume", "tick_volume"], ["indicators", "obv"], ["vwap_reclaim", "tick_activity_rejection", "order_flow", "obv_divergence_reclaim"], ["ta_volume", "ta_wyckoff"], "ta_volume")
    add("ta_harmonic_patterns", "technical", 28, "النماذج التوافقية", "Harmonic Patterns", [
        ("بند مرتبط بالهارمونيك مع الاحتفاظ بترتيبه الأصلي؛ لا ينتج صوتًا إضافيًا.", "Alias of harmonic analysis retained in original order; it produces no extra vote."),
        ("تتضمن العائلات المرجعية تساوي الضلعين وغارتلي والخفاش والفراشة والسلطعون؛ النموذج الحسابي الحالي يغطي تساوي الضلعين فقط، ولا توجد جداول تنفيذ لبقية العائلات.", "Referenced families include equal-leg, Gartley, Bat, Butterfly and Crab; the current computational model covers equal-leg only, with no executable ratio tables for the other families.", "HOUSE_DEFINITION", []),
        ("جدول كل عائلة يحدد نسب التصحيح والإسقاط ونقطة الإبطال ومصدره.", "Each family needs sourced retracement/projection ratios and invalidation."),
        ("احفظ مناطق التوافق المرشحة والتحقق النهائي منفصلين، واختبر النموذجين الصاعد والهابط.", "Store candidate confluence and final verification separately; test bullish and bearish cases."),
        ("الموجود تنفيذيًا تساوي الضلعين فقط؛ بقية العائلات مرجع تطوير ولا تُسمى منفذة.", "Only equal-leg is currently executable; other families remain a development reference.", "HOUSE_DEFINITION", []),
    ], [("لا يعاد استخدام نسب عائلة لعائلة أخرى.", "Do not reuse one family's ratios for another."), ("المكتبة لا تعيد نشر كتب أو رسوم المصدر.", "The library does not republish source books or figures.")], ["completed_ohlc"], ["harmonic"], ["harmonic_abcd"], ["ta_harmonic"], "ta_harmonic")
    add("ta_gaps", "technical", 29, "تحليل الفجوات", "Gap Analysis", [
        ("الفجوة السعرية بين جلستين هي فرق افتتاح عن إغلاق سابق؛ الفجوة الثلاثية تعريف مختلف.", "A session price gap is open versus prior close; a three-bar gap is a different definition."),
        ("حدد جلسة ومرجع سعر وقاعدة استحقاق وتعديل أحداث الشركات قبل اكتشاف الفجوة.", "Define session, price basis, expiry and corporate-action treatment before gap detection."),
        ("ميّز فجوة عادية واختراق واستمرار وإرهاق كفرضيات تتطلب سياقًا لا اسمًا يقينيًا.", "Treat common, breakaway, continuation and exhaustion gaps as context-dependent hypotheses."),
        ("احسب الملء الجزئي والكامل والمهلة وأسباب الإبطال دون افتراض أن كل فجوة ستُملأ.", "Define partial/full fill, expiry and invalidation without assuming every gap fills."),
        ("منفذ العودة الأولى الحالي خاص بالفجوة الثلاثية ولا يغطي جميع فجوات افتتاح البورصات.", "Current first-return execution covers three-bar gaps, not every exchange opening-gap family.", "HOUSE_DEFINITION", []),
    ], [("فجوة ترحيل عقد أو تقسيم سهم ليست اختلالًا سعريًا عاديًا.", "A contract-roll or split discontinuity is not an ordinary trading gap."), ("السبريد قد يخلق فجوة ظاهرية في سلسلة جانب اقتباس واحد.", "Spread can create apparent gaps in a one-sided quote series.")], ["completed_ohlc", "session_clock", "corporate_actions"], ["indicators", "ict"], ["fvg_first_return", "smc_ict_proxy"], ["ta_ict", "ta_classical"])
    add("ta_pivots", "technical", 30, "النقاط المحورية", "Pivot Points", [
        ("في الصيغة التقليدية المحور يساوي متوسط أعلى وأدنى وإغلاق الجلسة السابقة.", "In the traditional formula, pivot equals prior-session high, low and close average.", "SOURCE_PRINCIPLE", ["session_pivots"]),
        ("المقاومة الأولى ضعف المحور ناقص الأدنى، والدعم الأول ضعف المحور ناقص الأعلى.", "First resistance is twice pivot minus prior low; first support is twice pivot minus prior high.", "SOURCE_PRINCIPLE", ["session_pivots"]),
        ("الدرجة الثانية تضيف أو تطرح مدى الجلسة السابقة؛ بقية العائلات تحفظ بصيغ منفصلة.", "Second levels add/subtract prior range; other families require separate formulas."),
        ("اعتمد جلسة سابقة مكتملة فقط وحدد هل المرجع يومي أو أسبوعي أو شهري.", "Use only a completed prior session and specify daily/weekly/monthly reference."),
        ("المحور الحسابي يختلف عن قمة أو قاع هيكلي؛ المستوى وحده ليس إشارة دخول.", "A calculated pivot differs from a swing pivot; the level alone is not an entry signal."),
    ], [("تغير حدود اليوم أو عائلة الصيغة يغير المستويات.", "Day boundaries and formula family change levels."), ("النموذج المحلي يستعيد محور يوم مكتمل وفق ساعة افتتاح الشمعة اليومية في المنصة؛ لا يغطي جميع عائلات المحاور أو تقاويم البورصات.", "The local model reclaims a completed daily pivot using the terminal D1 opening clock; it does not cover every pivot family or exchange calendar.")], ["completed_ohlc", "session_clock"], ["session_pivots"], ["classic_pivot_reclaim"], related=["ta_market_structure", "ta_classical"])


def fundamental():
    add("fa_quantitative", "fundamental", 1, "التحليل الأساسي الكمي", "Quantitative Fundamental Analysis", [
        ("احفظ تعريف كل نسبة ومقامها ووحدتها وفترة التقرير.", "Store each ratio's definition, denominator, units and reporting period."),
        ("حلل الربحية والسيولة والرفع المالي والتغطية وجودة التدفق بدل رقم منفرد.", "Analyze profitability, liquidity, leverage, coverage and cash-flow quality rather than one metric."),
        ("القيم الصفرية والسالبة والبيانات الناقصة حالات مختلفة يجب إظهارها.", "Zero, negative and missing values are distinct states that must remain visible."),
        ("قارن الفترة نفسها ومعايير محاسبية متوافقة وصحح البنود غير المتكررة بشفافية.", "Compare like periods and compatible accounting; disclose non-recurring-item adjustments."),
        ("لا تضع التقرير ضمن عينة قبل نشره؛ افصل النسخة الأصلية عن إعادة البيان.", "Do not include a report before publication; distinguish original from restated versions."),
        ("سعر عقد فرق ليس قائمة مالية للشركة الأساسية.", "A CFD price is not the underlying company's financial statement."),
    ], [("النسب القطاعية تختلف ولا توجد عتبات جودة عامة صحيحة لكل شركة.", "Sector ratios differ; no universal quality threshold is valid for every firm."), ("مقام قريب من الصفر قد يجعل المضاعف غير مفيد.", "A near-zero denominator can make a multiple uninformative.")], ["financial_statements", "issuer_identity", "corporate_actions"], ["sec", "company"], related=["fa_company", "fa_relative", "ta_quantitative"])
    add("fa_qualitative", "fundamental", 2, "التحليل النوعي", "Qualitative Fundamental Analysis", [
        ("وثق نموذج العمل ومصدر الإيراد والعملاء والموردين وتركيزهم.", "Document business model, revenue sources, customers, suppliers and concentration."),
        ("قيّم الحوكمة والحوافز وتخصيص رأس المال والتعاملات مع الأطراف المرتبطة.", "Review governance, incentives, capital allocation and related-party dealings."),
        ("افصل تصريح الإدارة عن واقعة موثقة وعن تقدير المحلل.", "Separate management claims, verified facts and analyst estimates."),
        ("حوّل فرضية الميزة التنافسية إلى مؤشرات تحقق وتاريخ انتهاء ومخاطر مضادة.", "Turn a competitive-advantage hypothesis into verification indicators, expiry and counter-risks."),
        ("احفظ المراجع المحلية ومقاطع الدليل بإذن مناسب؛ لا تدّع فهمًا آليًا شاملًا من ملف الاسم فقط.", "Retain local references and appropriately permitted evidence; a file name does not establish complete automated understanding."),
    ], [("الدرجات النوعية تقديرات تحتاج تفسيرًا وليست حقائق مالية.", "Qualitative scores are explained judgments, not financial facts."), ("غياب الدليل لا يعادل جودة عالية.", "Absent evidence does not imply high quality.")], ["filings", "issuer_identity", "behavior_log"], ["company"], related=["fa_industry", "fa_company", "fa_behavioral"])
    add("fa_macro", "fundamental", 3, "الاقتصاد الكلي", "Macroeconomic Analysis", [
        ("افصل مستوى النشاط عن نموه وتسارعه، والتضخم الكلي عن الأساسي حيث تتوفر البيانات.", "Separate activity level, growth and acceleration, and headline/core inflation where available."),
        ("قارن البيانات الفعلية بتوقع سابق موثق وبنسخة سابقة متاحة، وليس بتوقع أعيد لاحقًا.", "Compare actual values with a documented prior expectation and available prior vintage, not a later revised forecast."),
        ("قرار الفائدة ومسارها المتوقع والتمويل الحقيقي قنوات مختلفة؛ لا تفرض علاقة سعر ثابتة.", "Policy-rate decisions, expected paths and real funding conditions are different channels; do not impose a fixed price response."),
        ("احفظ وقت النشر والمنطقة الزمنية وتأخير المصدر وإعادة المراجعة.", "Store release time, time zone, source delay and revisions."),
        ("التقويم يحدد حدثًا وقيمًا عند توفرها؛ لا يكفي وحده لبناء نموذج اقتصادي شامل.", "A calendar supplies events/available values; it is insufficient for a complete macro model."),
        ("امنع التصويت عند غياب السلسلة اللازمة؛ حظر الخبر التشغيلي مستقل عن اتجاه الخبر.", "Abstain when required series are missing; operational news blackout is independent of news direction."),
    ], [("رد فعل السوق يعتمد على التسعير السابق والسيولة والسياق.", "Market reaction depends on prior pricing, liquidity and context."), ("السلسلة المعدلة النهائية لا تمثل ما كان معروفًا تاريخيًا.", "A final revised series is not what was historically known.")], ["macro_series", "calendar", "session_clock"], ["calendar", "currency"], related=["fa_currency", "fa_bond", "fa_commodity", "ap_top_down"])
    add("fa_industry", "fundamental", 4, "تحليل القطاع", "Industry Analysis", [
        ("حدد حدود الصناعة والمنتج والسوق الجغرافي قبل مقارنة الشركات.", "Define industry, product and geographic-market boundaries before comparing firms."),
        ("افحص المنافسة القائمة والداخلين والبدائل وقوة الموردين وقوة المشترين.", "Examine rivalry, entrants, substitutes, supplier power and buyer power.", "SOURCE_PRINCIPLE", ["porter"]),
        ("اربط دورة الطلب والقدرة الإنتاجية والتنظيم والتقنية بإيرادات وهوامش القطاع.", "Connect demand cycle, capacity, regulation and technology to sector revenue/margins."),
        ("اختَر مجموعة مقارنة متوافقة نموذج العمل والعملة والدورة لا التسمية فقط.", "Select peers with comparable business models, currencies and cycle exposure, not just labels."),
        ("احفظ أسباب التفوق أو الخصم والمخاطر التي تنقض فرضية القطاع.", "Record premium/discount rationale and risks that falsify the sector thesis."),
    ], [("متوسط القطاع قد يخفي شركات مختلفة جذريًا.", "A sector average can hide materially different businesses."), ("بيانات الشركات الناجية فقط تحيز المقارنة.", "Survivor-only samples bias comparisons.")], ["peer_data", "filings", "macro_series"], ["industry", "porter"], related=["fa_company", "fa_relative", "ap_top_down"])
    add("fa_company", "fundamental", 5, "تحليل الشركة", "Company Analysis", [
        ("اربط قائمة الدخل والمركز المالي والتدفق النقدي والإيضاحات.", "Reconcile income statement, balance sheet, cash-flow statement and notes."),
        ("فكك الإيراد إلى حجم وسعر ومزيج، وميز النمو العضوي عن الاستحواذ.", "Decompose revenue into volume, price and mix; separate organic growth from acquisitions."),
        ("قارن الربح المحاسبي بالنقد التشغيلي وبالاستثمار اللازم لاستمرار العمل.", "Compare accounting earnings with operating cash and required sustaining investment."),
        ("احفظ جدول الدين والاستحقاقات والفوائد والأسهم المخففة والالتزامات المحتملة.", "Retain debt maturities, interest, diluted shares and contingent liabilities."),
        ("ابنِ سيناريوهات متسقة للهوامش ورأس المال العامل والاستثمار والتمويل.", "Construct internally consistent margin, working-capital, investment and funding scenarios."),
    ], [("الأرباح المعدلة تحتاج جسرًا إلى الأرقام الرسمية.", "Adjusted earnings need a bridge to reported figures."), ("زيادة الربح للسهم قد تأتي من إعادة شراء لا نمو النشاط.", "EPS growth can come from buybacks rather than business growth.")], ["financial_statements", "issuer_identity", "filings", "corporate_actions"], ["sec", "company"], related=["fa_qualitative", "fa_quantitative", "ap_bottom_up"])
    add("fa_graham_dodd", "fundamental", 6, "جراهام ودود", "Graham & Dodd / Security Analysis", [
        ("القرار يستند إلى تحليل الأصل ومتانة ميزانيته وعائد معقول، لا إلى توقع سعر فقط.", "Base decisions on the asset, balance-sheet resilience and reasonable return rather than price prediction alone."),
        ("افصل السعر السوقي عن نطاق قيمة محافظ مبني على أرباح أو أصول قابلة للفحص.", "Separate market price from a conservative inspectable earnings/asset value range."),
        ("هامش الأمان فرق بين السعر وتقدير القيمة مع عدم يقين؛ لا توجد نسبة موحدة إلزامية.", "Margin of safety is a price/value gap with estimation uncertainty; no universal mandatory percentage exists."),
        ("طبع الأرباح الدورية وراجع الدين وجودة الأصول وخطر التلف أو التصفية.", "Normalize cyclical earnings and review debt, asset quality, impairment and liquidation risk."),
        ("لا تستخدم صيغة تاريخية تقريبية لجراهام كقانون تقييم شامل.", "Do not treat an approximate historical Graham formula as a universal valuation law."),
    ], [("الخصم الظاهر قد يكون فخ قيمة بسبب تدهور دائم.", "An apparent discount can be a value trap under persistent deterioration."), ("الحفاظ على الأصل هدف تحليلي وليس ضمانًا.", "Principal protection is an analytical objective, not a guarantee.")], ["financial_statements", "issuer_identity", "asset_appraisals"], ["graham", "valuation"], related=["fa_value", "fa_asset_based", "ap_dcf"])
    add("fa_behavioral", "fundamental", 7, "المالية السلوكية", "Behavioral Finance", [
        ("ميّز الثقة المفرطة والتأكيد والتثبيت والخوف من الخسارة والحداثة في سجل القرار.", "Identify overconfidence, confirmation, anchoring, loss aversion and recency in the decision journal."),
        ("اكتب توقعًا ودليلًا ناقضًا قبل النتيجة لتجنب إعادة تفسير الماضي.", "Write forecasts and falsifying evidence before outcomes to avoid hindsight rewriting."),
        ("قارن الفرضية ببديل وقاعدة أساس قبل اعتماد تفسير واحد.", "Compare a thesis with an alternative and baseline before accepting one explanation."),
        ("راجع تغيير المعلمات وحدود المخاطرة بعد ربح أو خسارة كسلوك مستقل.", "Review parameter/risk-limit changes after wins or losses as separate behavior."),
        ("دراسة التحيز لا تثبت اتجاه السوق، والمشاعر السوقية تحتاج عينة بيانات مستقلة.", "Bias analysis does not establish market direction; market sentiment needs a separate data sample."),
    ], [("لا يشخص النظام حالة نفسية من صفقة.", "The system does not diagnose a psychological condition from a trade."), ("الربح لا يثبت خلو القرار من تحيز.", "A profit does not prove an unbiased decision.")], ["behavior_log", "positioning"], ["behavior"], related=["ta_sentiment", "fa_qualitative"])
    add("fa_value", "fundamental", 8, "استثمار القيمة", "Value Investing", [
        ("حدد قيمة داخلية بنموذج مناسب واحتفظ بنطاق عدم اليقين.", "Estimate intrinsic value with a suitable model and uncertainty range."),
        ("اختبر سبب انخفاض السعر: دورة عابرة أم تدهور دائم أم التزام غير ظاهر.", "Investigate cheapness: temporary cycle, permanent deterioration or hidden liability."),
        ("أضف تكلفة رأس المال وإعادة الاستثمار اللازمة بدل افتراض نمو مجاني.", "Include capital cost and required reinvestment rather than free growth."),
        ("احفظ محفز تصحيح الفجوة وأفقه ومخاطر بقائها دون فرض موعد مضمون.", "Record possible gap-closing catalysts, horizon and persistence risks without guaranteed timing."),
        ("انخفاض مضاعف واحد ليس بديلًا عن تحليل التدفقات والميزانية.", "A low single multiple is not a substitute for cash-flow and balance-sheet analysis."),
    ], [("قيمة التصفية وقيمة الاستمرار قد تختلفان جذريًا.", "Liquidation and going-concern values can differ materially."), ("القيمة التقديرية تتغير مع الحقائق الجديدة.", "Estimated value changes with new facts.")], ["financial_statements", "cash_forecasts", "discount_rates", "asset_appraisals"], ["valuation", "fcf"], related=["fa_graham_dodd", "fa_absolute", "fa_relative"])
    add("fa_growth", "fundamental", 9, "استثمار النمو", "Growth Investing", [
        ("افصل نمو الإيراد ونمو الربح ونمو التدفق ونمو الربح للسهم المخفف.", "Separate revenue, earnings, cash-flow and diluted-EPS growth."),
        ("اختبر حجم السوق والاحتفاظ بالعملاء وهوامش الوحدة وقدرة التنفيذ.", "Test addressable market, customer retention, unit economics and execution capacity."),
        ("اربط النمو بالاستثمار والتمويل وتخفيف ملكية المساهمين.", "Link growth to reinvestment, funding and shareholder dilution."),
        ("انقل معدلات النمو العالية إلى استقرار معقول تدريجيًا بدل تمديدها إلى الأبد.", "Fade high growth toward a defensible stable state rather than extending it forever."),
        ("اختبر قيمة الشركة تحت تأخر النمو أو ضعف الهوامش أو ارتفاع معدل الخصم.", "Stress value for slower growth, weaker margins and higher discount rates."),
    ], [("النمو لا يعني أن أي سعر مقبول.", "Growth does not make every price acceptable."), ("الاستحواذ قد يرفع الإيراد دون خلق قيمة.", "Acquisitions can grow revenue without creating value.")], ["financial_statements", "cash_forecasts", "discount_rates", "corporate_actions"], ["company", "fcf"], related=["fa_garp", "fa_absolute"])
    add("fa_income", "fundamental", 10, "استثمار الدخل", "Income Investing", [
        ("ميّز توزيعات أرباح الأسهم وكوبون السند وتوزيع الصندوق ورد رأس المال.", "Distinguish equity dividends, bond coupons, fund distributions and return of capital."),
        ("قارن الدخل النقدي بالتدفق المتاح والتزامات الدين والإنفاق اللازم.", "Compare cash income with available cash, debt obligations and required investment."),
        ("احسب العائد على السعر الحالي بعد الضرائب والرسوم عند إدخالها.", "Compute current-price yield after supplied taxes/fees where applicable."),
        ("اختبر احتمال خفض التوزيع ومخاطر الائتمان والفائدة والقيمة الرأسمالية.", "Test distribution cuts, credit, rate and capital-value risks."),
        ("عوائد عالية ناتجة من انهيار السعر ليست دليل جودة.", "High yields caused by price collapse are not evidence of quality."),
    ], [("التوزيع النقدي قد يتغير ولا يساوي عائدًا كليًا مضمونًا.", "Distributions can change and do not guarantee total return."), ("عقد الفرق قد يعكس تعديلًا نقديًا ولا يمنح ملكية السهم.", "A CFD may reflect cash adjustments without granting share ownership.")], ["dividends", "financial_statements", "security_terms", "fund_holdings"], ["ddm", "bond", "fund"], related=["ap_ddm", "fa_bond", "fa_fund"])
    add("fa_garp", "fundamental", 11, "النمو بسعر معقول", "Growth at a Reasonable Price (GARP)", [
        ("اجمع فرضية نمو قابلة للتمويل مع تقييم لا يفترض نجاحًا مثاليًا.", "Combine financeable growth with valuation that does not assume perfect execution."),
        ("مضاعف الربح إلى النمو يحتاج ربحًا موجبًا ونموًا موجبًا وتحديد وحدة النمو.", "PEG requires positive earnings, positive growth and explicit growth units."),
        ("النمو المتوقع يختلف عن الماضي؛ احفظ مصدر التوقع وتاريخه وأفقه.", "Expected growth differs from history; store source, date and horizon."),
        ("قارن الربحية والرفع المالي وإعادة الاستثمار بدل حد مضاعف ثابت وحده.", "Compare profitability, leverage and reinvestment rather than one fixed multiple cutoff."),
        ("لا تعامل نسبة معينة للمضاعف إلى النمو كقانون عالمي أو أمر تداول مباشر.", "Do not treat a particular PEG level as a universal law or direct order."),
    ], [("النمو السالب يجعل التفسير الاعتيادي للمضاعف إلى النمو غير مناسب.", "Negative growth makes conventional PEG interpretation unsuitable."), ("المنهج يتداخل مع القيمة والنمو ولا يضيف دليلًا مستقلًا تلقائيًا.", "The style overlaps value/growth and does not automatically add independent evidence.")], ["financial_statements", "cash_forecasts", "peer_data"], ["garp", "multiples"], related=["fa_value", "fa_growth"])
    add("fa_index", "fundamental", 12, "الاستثمار في المؤشرات", "Index Investing", [
        ("حدد منهج بناء المؤشر: سوق موزون أو متساوٍ أو عوامل، وقواعد إعادة التوازن.", "Specify market-cap, equal-weight or factor construction and rebalance rules."),
        ("تتبع المؤشر هدف المنتج وليس ضمانًا لمطابقة العائد أو انعدام المخاطرة.", "Index tracking is a product objective, not guaranteed replication or absence of risk.", "SOURCE_PRINCIPLE", ["index"]),
        ("قِس فرق التتبع وتذبذبه والرسوم والضرائب والتنفيذ.", "Measure tracking difference/error, fees, taxes and execution."),
        ("راجع تركّز القطاعات والمصدرين والأوزان وتغير العضوية تاريخيًا.", "Review sector/issuer/weight concentration and point-in-time membership changes."),
        ("عقد مؤشر لدى الوسيط ليس صندوق مؤشر يملك مكوناته.", "A broker index contract is not an index fund owning constituents."),
    ], [("اختبار مكونات اليوم بأثر رجعي يسبب انحياز البقاء.", "Backtesting today's constituents causes survivorship bias."), ("المؤشر قد يكون مركزًا رغم عدد مكوناته.", "An index may be concentrated despite many constituents.")], ["index_membership", "fund_holdings", "corporate_actions"], ["index"], related=["fa_fund", "fa_equity"])
    add("fa_fund", "fundamental", 13, "الاستثمار في الصناديق", "Fund Investing", [
        ("اقرأ الهدف والقيود ونوع البنية القانونية والنشرة المحلية الموثقة.", "Review objectives, restrictions, legal structure and verified local prospectus."),
        ("افحص المكونات والرافعة والسيولة والتداخل مع بقية المحفظة.", "Inspect holdings, leverage, liquidity and portfolio overlap."),
        ("الرسوم التشغيلية ورسوم الدخول والخروج والتمويل تخفض العائد بآليات مختلفة.", "Operating, entry/exit and funding costs affect return through different mechanisms."),
        ("قارن أداء صافي الرسوم بمعيار مناسب مع مخاطر وأفق مماثلين.", "Compare net-of-fee performance with a suitable risk/horizon-matched benchmark."),
        ("للصندوق المتداول أو المغلق افصل السعر عن صافي قيمة الأصول والعلاوة أو الخصم.", "For traded/closed-end funds, distinguish market price from NAV and premium/discount."),
    ], [("صندوقان متشابهَا الاسم قد يختلفان في الفئة والرسوم والمكونات.", "Similarly named funds may differ in share class, fees and holdings."), ("الأداء السابق وحده ليس قاعدة اختيار كافية.", "Past performance alone is not a sufficient selection rule.")], ["fund_holdings", "filings", "issuer_identity"], ["fund"], related=["fa_index", "fa_income", "fa_asset_based"])
    add("fa_commodity", "fundamental", 14, "تحليل السلع", "Commodity Fundamental Analysis", [
        ("حدد السلعة والجودة والمكان ووحدة التسعير والتسليم.", "Identify commodity, grade, location, quote units and delivery terms."),
        ("وازن الإنتاج والاستهلاك والواردات والصادرات والمخزون بالموسم والمنطقة.", "Reconcile production, use, imports, exports and inventory by season/region."),
        ("منحنى صاعد مع الأجل يسمى كونتانغو، والهابط باكورديشن؛ لا يضمن اتجاه السعر الفوري.", "An upward futures curve is contango and a downward curve backwardation; neither guarantees spot direction.", "SOURCE_PRINCIPLE", ["commodity"]),
        ("افصل تغير السعر الفوري عن عائد الترحيل والتمويل والتخزين.", "Separate spot moves from roll, financing and storage effects."),
        ("عقد وسيط مستمر يحتاج توثيق طريقة الترحيل؛ لا يعوض بيانات توازن السلعة.", "A continuous broker contract needs a documented roll method; it does not replace commodity-balance data."),
    ], [("أسعار أماكن التسليم المختلفة ليست قابلة للمقارنة بلا فروق أساس.", "Delivery locations are not comparable without basis adjustments."), ("تغير عقد الاستحقاق قد يشوه العائد المحسوب.", "Expiry changes can distort calculated returns.")], ["commodity_balance", "futures_curve", "issuer_identity", "macro_series"], ["commodity"], related=["fa_macro", "ta_intermarket"])
    add("fa_currency", "fundamental", 15, "تحليل العملات", "Currency Fundamental Analysis", [
        ("حدد عملة الأساس والاقتباس ومعنى ارتفاع السعر قبل حساب العائد.", "Identify base/quote currencies and the meaning of a price rise before return calculation."),
        ("افصل سعر الصرف الاسمي والحقيقي ونظام التعويم أو الربط.", "Distinguish nominal/real exchange rates and floating/pegged regimes.", "SOURCE_PRINCIPLE", ["currency"]),
        ("قارن فروق الفائدة والتضخم والنمو والتدفقات والمخاطر بين البلدين.", "Compare rate, inflation, growth, flow and risk differences between both economies."),
        ("الكاري يضم التمويل والحركة السعرية ومخاطر تغير النظام؛ ليس عائد فائدة مضمونًا.", "Carry combines financing, price movement and regime risk; it is not guaranteed interest income."),
        ("تحقق من سواب الوسيط والتحوط والعملة التي يقاس فيها الربح.", "Verify broker swap, hedging and the currency in which profit is measured."),
    ], [("فروق الفائدة لا تعطي اتجاهًا قصيرًا ثابتًا.", "Rate differentials do not give a fixed short-term direction."), ("ربط العملة قد يحد الحركة لكنه يخلق خطر انقطاع مختلفًا.", "A peg may constrain moves while creating a different discontinuity risk.")], ["macro_series", "calendar", "issuer_identity", "yield_curves"], ["currency", "currency_management"], related=["fa_macro", "ta_intermarket"])
    add("fa_bond", "fundamental", 16, "تحليل السندات", "Bond Analysis", [
        ("عرّف القيمة الاسمية والكوبون وتواتره والاستحقاق والأولوية والخيارات.", "Define principal, coupon/frequency, maturity, seniority and embedded options."),
        ("القيمة تساوي التدفقات التعاقدية المخصومة؛ تميّز السعر النظيف عن المتسخ والفائدة المستحقة.", "Value contractual discounted cash flows; distinguish clean/dirty price and accrued interest."),
        ("قِس حساسية الفائدة بالمدة والتحدب مع حدود تقريبها.", "Measure rate sensitivity using duration/convexity with approximation limits."),
        ("حلل قدرة خدمة الدين والضمانات والاسترداد وفروق الائتمان.", "Analyze debt service, collateral, recovery and credit spreads."),
        ("العائد للاستحقاق يعتمد على الحيازة والدفعات وإعادة الاستثمار؛ ليس ربحًا محققًا دائمًا.", "Yield to maturity depends on holding, payments and reinvestment; it is not always realized return."),
    ], [("السند القابل للاستدعاء يحتاج تقييم الخيار؛ الخصم البسيط غير كافٍ.", "Callable bonds require option valuation; simple discounting is insufficient."), ("حاسبة السند المحلية محدودة للتدفقات المدخلة ولا تستنتج جودة المصدر.", "The local bond calculator handles supplied cash flows and does not infer issuer quality.")], ["security_terms", "yield_curves", "financial_statements", "issuer_identity"], ["bond", "duration"], related=["fa_income", "ap_present_value"])
    add("fa_equity", "fundamental", 17, "تحليل الأسهم", "Equity Analysis", [
        ("حدد حقوق الفئة والأصوات والسيولة والأسهم المخففة ومطالبات أعلى من المساهمين.", "Identify class rights, votes, liquidity, diluted shares and claims senior to equity."),
        ("راجع الربحية وجودة التدفق والدين والنمو وإعادة الاستثمار.", "Review profitability, cash quality, debt, growth and reinvestment."),
        ("قارن قيمة المساهم بقيمة المنشأة مع جسر واضح للدين والنقد والمطالبات الأخرى.", "Reconcile equity and enterprise values through debt, cash and other claims."),
        ("قيمة السهم تعتمد على عدد أسهم متوافق مع مستوى التدفقات والمطالبات.", "Per-share value needs a share count consistent with cash flows and claims."),
        ("عقد الفرق على سهم لا يمنح تلقائيًا نفس الحقوق أو سياسة الأرباح.", "An equity CFD does not automatically provide the same rights or dividend policy."),
    ], [("إجراءات الشركات تغير السعر وعدد الأسهم والعائد.", "Corporate actions change price, share count and return."), ("قيمة السهم المقدرة ليست سعر تنفيذ مضمونًا.", "Estimated share value is not a guaranteed execution price.")], ["financial_statements", "issuer_identity", "corporate_actions", "cash_forecasts"], ["valuation", "company"], related=["fa_company", "fa_absolute", "fa_relative"])
    add("fa_absolute", "fundamental", 18, "التقييم المطلق", "Absolute / Intrinsic Valuation", [
        ("حدد هل التدفق للمساهم أم لجميع ممولي الشركة أم توزيعات أم دخل متبقٍ.", "Specify equity, firm, dividend or residual-income cash-flow basis."),
        ("طابق تدفق المساهم مع تكلفة حقوق الملكية وتدفق المنشأة مع تكلفة رأس مال مناسبة.", "Match equity flows with cost of equity and firm flows with a suitable capital cost.", "SOURCE_PRINCIPLE", ["fcf"]),
        ("قيمة نهائية بنمو دائم تحتاج معدل خصم أكبر من النمو واتساقًا اقتصاديًا.", "Perpetual-growth terminal value needs discount rate greater than growth and economic consistency."),
        ("احتفظ بسيناريوهات وحساسية للنمو والهوامش والخصم، لا رقم قيمة وحيدًا.", "Retain scenarios and growth/margin/discount sensitivity rather than one value."),
        ("وثق تاريخ توقعات التدفق ومصدرها؛ حاسبة صحيحة لا تجعل الفرضيات صحيحة.", "Document forecast date/source; a correct calculator does not make assumptions correct."),
    ], [("التدفق السالب أو الهيكل المالي المتغير يحتاج نموذجًا مناسبًا.", "Negative cash flows or changing leverage require an appropriate model."), ("تضخم وعملة التدفق والخصم يجب أن يتطابقا.", "Cash-flow/discount inflation basis and currency must match.")], ["cash_forecasts", "discount_rates", "financial_statements", "issuer_identity"], ["valuation", "fcf", "ddm"], related=["ap_dcf", "ap_ddm", "ap_present_value"])
    add("fa_relative", "fundamental", 19, "التقييم النسبي", "Relative Valuation", [
        ("اختر نظراء متوافقين في النشاط والنمو والمخاطر والمحاسبة.", "Select peers with compatible business, growth, risk and accounting."),
        ("مضاعف السعر يستخدم مقياسًا يعود للمساهم، ومضاعف المنشأة مقياسًا لجميع الممولين.", "Price multiples use equity measures; enterprise multiples use measures for all capital providers.", "SOURCE_PRINCIPLE", ["multiples"]),
        ("طابق تاريخ السعر والفترة الماضية أو المتوقعة وعدد الأسهم.", "Match price date, trailing/forward period and share count."),
        ("أعلن البنود غير المتكررة والقيم السالبة والمتطرفة وطريقة تلخيص العينة.", "Disclose exceptional items, negatives, outliers and sample aggregation."),
        ("رخص الشركة قياسًا بنظير مبالغ فيه لا يثبت أنها دون قيمتها الداخلية.", "Cheapness against an overpriced peer does not establish intrinsic undervaluation."),
    ], [("مضاعف الربح المعتاد لا يفسر أرباحًا سالبة.", "Conventional P/E does not meaningfully interpret negative earnings."), ("خصم النظير قد يبرره اختلاف جودة أو مخاطر.", "A peer discount may reflect quality or risk differences.")], ["peer_data", "financial_statements", "issuer_identity", "corporate_actions"], ["multiples"], related=["ap_relative", "ap_multiples", "fa_absolute"])
    add("fa_asset_based", "fundamental", 20, "التقييم القائم على الأصول", "Asset-Based Valuation", [
        ("عرّف الاستمرار أو التصفية، وهوية الأصول وحقوق ملكيتها وقيودها.", "Define going concern or liquidation, asset identity, ownership and restrictions."),
        ("عدّل قيمة الأصول والالتزامات إلى أساس متناسق موثق.", "Adjust assets/liabilities to a documented consistent valuation basis."),
        ("صافي قيمة الأصول يساوي قيمة الأصول المعدلة ناقص الالتزامات والمطالبات السابقة.", "Net asset value equals adjusted assets less liabilities and senior claims."),
        ("أدخل تكاليف البيع والضرائب والزمن والخصومات ومطالبات خارج الميزانية.", "Include selling costs, tax, timing, discounts and off-balance-sheet claims."),
        ("القيمة لكل سهم تتطلب عدد أسهم وحقوقًا متوافقة؛ القيمة الدفترية ليست تلقائيًا قيمة سوقية.", "Per-share value needs consistent shares/rights; book value is not automatically market value."),
    ], [("قد لا يظهر أصل غير ملموس مهم في الدفاتر.", "Important intangible assets may be absent from books."), ("تقدير الأصل يحتاج مصدرًا وتاريخًا ولا يستنتج من الشارت.", "Asset appraisals need source/date and cannot be inferred from a chart.")], ["asset_appraisals", "financial_statements", "issuer_identity"], ["valuation", "sec"], related=["ap_asset_based", "fa_graham_dodd"])


def approaches():
    add("ap_top_down", "approach", 1, "المنهج التنازلي", "Top-Down Approach", [
        ("ابدأ بفرضية اقتصاد ونظام مخاطرة ثم قطاع ثم شركة أو أداة.", "Start with macro/risk regime, then sector, then issuer/instrument."),
        ("اربط كل مستوى بقناة انتقال معلنة وتوقع قابل للتفنيد.", "Link levels through explicit transmission channels and falsifiable forecasts."),
        ("لا تختَر قطاعًا أو شركة لمجرد توافق قصة؛ افحص بياناتها وتقييمها.", "Do not select sectors/firms for narrative fit alone; review data and valuation."),
        ("احفظ تواريخ بيانات جميع المستويات وتجنب تكرار الدليل المشترك.", "Keep availability times across all levels and avoid double-counting shared evidence."),
        ("المنهج يرتب البحث ولا يمثل حاسبة قيمة أو قاعدة تداول منفردة.", "The approach organizes research rather than providing one valuation calculator or trade rule."),
    ], [("الاقتصاد الجيد لا يضمن ربح سهم مرتفع السعر.", "A strong economy does not guarantee returns on an expensive stock."), ("تعطل قناة الانتقال يبطل الفرضية الجزئية.", "A broken transmission channel invalidates that part of the thesis.")], ["macro_series", "peer_data", "financial_statements", "issuer_identity"], ["industry", "company"], related=["fa_macro", "fa_industry", "fa_company", "ap_bottom_up"])
    add("ap_bottom_up", "approach", 2, "المنهج التصاعدي", "Bottom-Up Approach", [
        ("ابدأ بحقوق الأداة واقتصاديات نشاط الشركة وميزانيتها.", "Start with instrument rights, company economics and balance sheet."),
        ("ابنِ تدفقات أو أصولًا أو نظراء وفق ملاءمة الشركة.", "Build cash-flow, asset or peer models suitable to the company."),
        ("اختبر الاعتماد على القطاع والفائدة والعملة حتى إن لم تبدأ بالاقتصاد.", "Stress sector, rate and currency dependence even when research starts at company level."),
        ("قارن النتيجة بمحفظة المخاطر والسيولة والتركيز.", "Compare the result with portfolio risk, liquidity and concentration."),
        ("حفظ قصة شركة لا يعطي إذنًا تلقائيًا لشراء عقد وسيط عليها.", "A stored company thesis does not automatically authorize a broker contract trade."),
    ], [("الاستقلال عن التوقع الاقتصادي لا يعني غياب التعرض الاقتصادي.", "Independence from macro forecasting does not mean no macro exposure."), ("مصدر مالي غير موثق يمنع قيمة قابلة للاعتماد.", "Unverified financial inputs prevent a reliable value estimate.")], ["financial_statements", "issuer_identity", "cash_forecasts", "discount_rates"], ["company", "valuation"], related=["fa_company", "fa_value", "ap_top_down"])
    add("ap_ddm", "approach", 3, "خصم توزيعات الأرباح", "Dividend Discount Model (DDM)", [
        ("القيمة الحالية هي مجموع التوزيعات المستقبلية المخصومة والقيمة المتبقية إن كان الأفق محدودًا.", "Present value sums discounted future dividends and any finite-horizon terminal value.", "SOURCE_PRINCIPLE", ["ddm"]),
        ("في النمو الدائم القيمة تساوي التوزيع القادم مقسومًا على معدل الخصم ناقص النمو.", "Constant-growth value is next-period dividend divided by discount rate minus growth.", "SOURCE_PRINCIPLE", ["ddm"]),
        ("يشترط أن يكون الخصم أكبر من النمو مع وحدة زمن وعملة متوافقتين.", "Discount rate must exceed growth with consistent period units and currency."),
        ("النمو المتعدد المراحل يحتاج توزيعًا لكل فترة ونموًا نهائيًا قابلًا للاستمرار.", "Multistage growth requires period-specific dividends and sustainable terminal growth."),
        ("راجع صلة التوزيعات بقدرة الشركة على الدفع؛ لا تدخل توزيع السنة الماضية كالتوزيع القادم دون افتراض.", "Check payouts against capacity; do not substitute last dividend for next dividend without an explicit assumption."),
    ], [("الشركة التي لا توزع قد تحتاج نموذج تدفق أو دخل متبقٍ آخر.", "Non-paying firms may require cash-flow or residual-income models."), ("معدل خصم قريب من النمو يجعل التقدير شديد الحساسية.", "A discount rate near growth makes the estimate highly sensitive.")], ["dividends", "cash_forecasts", "discount_rates", "issuer_identity"], ["ddm"], related=["fa_income", "fa_absolute", "ap_present_value"])
    add("ap_dcf", "approach", 4, "خصم التدفقات النقدية", "Discounted Cash Flow (DCF)", [
        ("حدد نوع التدفق: للمساهم أو لجميع ممولي الشركة؛ لا تخلط أساسين في عملية واحدة.", "Declare equity or firm cash flows and do not mix bases in one valuation."),
        ("خصم التدفق للمساهم بتكلفة حقوقه، وتدفق الشركة بمعدل متوافق مع هيكل رأس المال.", "Discount equity flows at equity cost and firm flows at a rate consistent with capital structure.", "SOURCE_PRINCIPLE", ["fcf"]),
        ("قيمة الأفق تجمع التدفقات المخصومة ثم القيمة النهائية المخصومة من تاريخها.", "Finite-horizon value adds discounted cash flows and terminal value discounted from its terminal date."),
        ("احفظ الافتراضات الخاصة بالنمو والهامش وإعادة الاستثمار والضريبة والعملة.", "Store growth, margin, reinvestment, tax and currency assumptions."),
        ("انتقل من قيمة المنشأة إلى قيمة المساهم بإضافة أصول غير تشغيلية وطرح المطالبات المناسبة.", "Bridge enterprise to equity by adding non-operating assets and subtracting relevant claims."),
        ("أظهر حساسية قيمة الأفق والنمو والخصم ولا تعتبر الناتج المالي إشارة تنفيذ وحده.", "Expose horizon/growth/discount sensitivity; calculator output alone is not an execution signal."),
    ], [("حاسبة التدفقات المدخلة لا تتوقع تلقائيًا التدفق المستقبلي.", "A supplied-flow calculator does not automatically forecast future cash flows."), ("المضاعف النهائي والقيمة بالنمو الدائم افتراضان مختلفان.", "Terminal multiples and perpetual-growth value are different assumptions.")], ["cash_forecasts", "discount_rates", "financial_statements", "issuer_identity"], ["fcf"], related=["fa_absolute", "ap_present_value"])
    add("ap_relative", "approach", 5, "منهج التقييم النسبي", "Relative Valuation / Comparables Approach", [
        ("يرتبط بهذا البند مرجع التقييم النسبي دون صوت تحليلي مكرر.", "This entry links to relative valuation without a duplicate analytical vote."),
        ("حدد مجموعة المقارنة وتاريخها وقواعد استبعاد الحالات غير الملائمة.", "Define peer set, date and unsuitable-case exclusions."),
        ("طبّق مضاعفًا متوافقًا على مقياس مالي من الفترة نفسها.", "Apply a compatible multiple to a same-period financial measure."),
        ("اعرض نطاق المقارنة والتشتت وأسباب تعديل الخصم أو العلاوة.", "Show range, dispersion and discount/premium adjustment rationale."),
        ("المقارنة تقدر سعرًا نسبيًا ولا تثبت قيمة مطلقة أو نجاح تداول.", "Comparison estimates relative value rather than intrinsic value or trade success."),
    ], [("اختيار نظراء بعد النتيجة يفسد قابلية الاختبار.", "Selecting peers after outcomes undermines testing."), ("قس اختلاف المخاطر والنمو قبل تعديل المضاعف.", "Assess risk/growth differences before adjusting multiples.")], ["peer_data", "financial_statements", "issuer_identity"], ["multiples"], related=["fa_relative", "ap_multiples"], alias="fa_relative")
    add("ap_asset_based", "approach", 6, "منهج صافي الأصول", "Asset-Based Valuation Approach", [
        ("يرتبط بالتقييم القائم على الأصول ولا يمثل مدرسة جديدة مستقلة.", "This links to asset-based valuation rather than a separate school."),
        ("احصر الأصول والالتزامات والمطالبات خارج الميزانية مع مصدر وتاريخ لكل بند.", "Inventory assets, liabilities and off-balance-sheet claims with source/date per item."),
        ("ثبّت الاستمرار أو التصفية والقيمة السوقية أو تكلفة الاستبدال بحسب الملاءمة.", "Specify going-concern/liquidation and suitable market/replacement values."),
        ("اطرح الالتزامات والتكاليف والضرائب ثم طابق النتيجة مع حقوق المساهم.", "Subtract liabilities, costs and taxes, then match the result to equity claims."),
        ("اختبر حساسية الخصومات ومدة التسييل ولا تستخدم القيمة الدفترية دون مراجعة.", "Stress haircuts and liquidation time; do not use book values without review."),
    ], [("مبالغ بنود مستوردة صحيحة شكليًا قد تكون تقديرات غير حديثة.", "Structurally valid imported amounts may still be stale estimates."), ("القيمة السالبة ليست خطأ حسابيًا تلقائيًا.", "Negative net value is not automatically an arithmetic error.")], ["asset_appraisals", "financial_statements", "issuer_identity"], ["sec", "valuation"], related=["fa_asset_based"], alias="fa_asset_based")
    add("ap_present_value", "approach", 7, "نماذج القيمة الحالية", "Present Value Models", [
        ("قيمة التدفق في زمن معلوم تساوي التدفق مقسومًا على واحد زائد معدل الفترة مرفوعًا إلى عدد الفترات.", "A known-time flow is discounted by one plus the period rate raised to the period count."),
        ("أوقات غير متساوية تحتاج كسور سنوات واتفاق عد أيام موثق.", "Unequal times need year fractions and a documented day-count convention."),
        ("طابق معدل اسمي أو فعلي وتواتر تركيب مع أوقات التدفقات.", "Match nominal/effective rate and compounding frequency to cash-flow times."),
        ("افصل التدفق المتوقع عن التعاقدي، ومعدل واحد عن منحنى خصم.", "Separate expected/contractual flows and a single rate from a discount curve."),
        ("تجمع التدفقات بعد الخصم؛ التمويل والعملة والتضخم جزء من فرضيات الاتساق.", "Sum flows after discounting; financing, currency and inflation belong to consistency assumptions."),
    ], [("صحة الخصم لا تثبت تحقق التدفق.", "Correct discounting does not prove that cash flows will occur."), ("فترات أو معدلات غير صالحة ترفض بدل إنتاج قيمة متخيلة.", "Invalid periods/rates are rejected rather than producing fabricated values.")], ["cash_forecasts", "discount_rates", "issuer_identity"], ["ddm", "duration"], related=["ap_ddm", "ap_dcf", "fa_bond"])
    add("ap_multiples", "approach", 8, "نماذج المضاعفات", "Multiplier / Multiples Models", [
        ("هذا التطبيق الحسابي ضمن التقييم النسبي، ويظل ظاهرًا لترتيب القائمة الأصلية.", "This arithmetic application belongs to relative valuation and remains visible in the original list."),
        ("مضاعف السعر إلى الربح يستخدم ربح السهم، ومضاعف المنشأة يستخدم أساسًا متوافقًا للمنشأة.", "P/E uses per-share earnings; enterprise multiples use a compatible firm-wide measure."),
        ("القيمة المقترحة تساوي مقياسًا ماليًا موثقًا مضروبًا بمضاعف مختار موثق.", "Proposed value equals a documented financial measure times a documented selected multiple."),
        ("اسحب الدين والنقد والمطالبات والأسهم في جسر مستقل عند الانتقال إلى سعر السهم.", "Use a separate debt/cash/claims/shares bridge when converting to per-share value."),
        ("احفظ نطاق المضاعف ومصدر اختياره ولا تنشئ نظيرًا من سعر الشارت فقط.", "Store multiple range and selection source; do not fabricate peers from chart prices."),
    ], [("المقياس السالب قد يجعل المضاعف التقليدي غير صالح للتفسير.", "Negative measures can make conventional multiples uninterpretable."), ("البسط والمقام يجب أن يعودا إلى نفس أصحاب المطالبات.", "Numerator/denominator must refer to the same claimholders.")], ["peer_data", "financial_statements", "issuer_identity"], ["multiples"], related=["fa_relative", "ap_relative"], alias="ap_relative")


CALCULATORS = {
    "fa_quantitative": ["multiples", "nav"], "fa_graham_dodd": ["nav", "dcf", "multiples"],
    "fa_value": ["dcf", "nav", "multiples"], "fa_growth": ["dcf"], "fa_income": ["ddm", "bond"],
    "fa_garp": ["multiples"], "fa_fund": ["nav"], "fa_bond": ["bond", "pv"],
    "fa_equity": ["dcf", "ddm", "multiples", "nav"], "fa_absolute": ["dcf", "ddm", "pv"],
    "fa_relative": ["multiples"], "fa_asset_based": ["nav"],
    "ap_ddm": ["ddm"], "ap_dcf": ["dcf"], "ap_relative": ["multiples"],
    "ap_asset_based": ["nav"], "ap_present_value": ["pv", "bond"], "ap_multiples": ["multiples"],
}


# Appended rules preserve existing IDs. Formulas describe research definitions;
# they are never evaluated from this catalog or promoted to committee votes.
ENRICHMENTS = {
    "ta_elliott": [
        ("الدافعة الأصلية لها تقسيمات داخلية خمس ثم ثلاث ثم خمس ثم ثلاث ثم خمس؛ تحقق هندسة ستة محاور وحده لا يثبت هذه التقسيمات.", "A standard impulse has internal 5-3-5-3-5 subdivisions; six-pivot geometry alone does not verify those subdivisions.", "SOURCE_PRINCIPLE", ["waveopedia"]),
        ("تصحيح الزجزاج تقسيمه الداخلي خمس ثم ثلاث ثم خمس؛ نسب تصحيح الوسطى وحدود طول الأخيرة في النماذج المحلية معاملات تنفيذية معلنة.", "A zigzag has internal 5-3-5 subdivisions; local B-retracement and C-length bounds are declared execution parameters.", "OPERATIONAL_CHECKLIST"),
        ("النماذج المحلية تفصل فرضية الموجتين، وهندسة الدافعة، وهندسة التصحيح الثلاثي؛ لكل نموذج تأكيد وإبطال وهدف وإصدار ونتائج محفوظة مستقلة.", "Local models separate the two-wave hypothesis, impulse geometry and ABC geometry; each keeps its own confirmation, invalidation, target, revision and outcomes.", "HOUSE_DEFINITION"),
    ],
    "ta_time": [
        ("تأكيد نافذة الزمن يحدث عند نهايتها الفعلية؛ احفظ زمن تكوّن المستوى وزمن إتاحته وزمن القرار منفصلة.", "An interval confirms at its actual end; retain formation, availability and decision times separately."),
        ("اختبر التوقيت أو الدورة على عينة لاحقة؛ اختيار نافذة بعد رؤية حركة السعر فرضية جديدة بإصدار جديد.", "Test timing/cycles on later observations; choosing a window after seeing the move creates a new versioned hypothesis."),
    ],
    "ta_market_structure": [
        ("تاريخ رسم المحور ليس تاريخ معرفته؛ الكسر الصالح يأتي بعد إتاحة تأكيد المحور ولا يستعير كسرًا أقدم.", "A pivot's chart timestamp is not its availability time; an eligible break follows confirmation and cannot reuse an earlier break."),
    ],
    "ta_neowave": [
        ("دوّن قياسات السعر والمدة وترتيب الموجات وشرط التأكيد لكل فرضية؛ حفظ الاسم لا ينفذ مصفوفة نيو ويف الكاملة.", "Record price, duration, wave sequence and confirmation for each hypothesis; storing the name does not implement the full NEoWave rule matrix."),
    ],
    "ta_chaos_fractal": [
        ("الفراكتل الصاعد ذو قمة وسطى أعلى من قمتي كل جانب؛ والهابط ذو قاع وسطى أدنى من قاعي كل جانب.", "An upward fractal has a central high above both highs on each side; a downward fractal reverses the low comparison.", "SOURCE_PRINCIPLE", ["fractal_definition"]),
        ("نموذج الخمس شموع المحلي يستعمل مقارنات صارمة وكسر إغلاق جديد بعد التأكيد؛ المساواة والسماحات وعمر المستوى موثقة في عقد نسخته.", "The local five-bar model uses strict comparisons and a fresh post-confirmation close break; ties, tolerances and level age are defined in its versioned contract.", "HOUSE_DEFINITION", []),
    ],
    "ta_volume": [
        ("الرصيد الحجمي التراكمي يتغير بمقدار حجم الشمعة بإشارة تغير الإغلاق؛ الإغلاق المساوي لا يغير الرصيد.", "Cumulative OBV changes by the bar's volume signed by the close change; an unchanged close leaves OBV unchanged.", "SOURCE_PRINCIPLE", ["obv"], {"expression": "OBV[t] = OBV[t-1] + sign(C[t]-C[t-1]) * V[t]", "variables": {"C": "completed close", "V": "declared bar-volume series"}, "domain": "V >= 0; unchanged close has sign 0", "units": "declared volume units"}),
        ("قارن الرصيد عند محوري السعر نفسيهما بعد تأكيدهما؛ التباعد مرشح يتطلب عودة سعرية ولا يثبت انعكاسًا وحده.", "Compare OBV at the same confirmed price pivots; divergence is a candidate requiring a price reclaim, not standalone reversal proof."),
    ],
    "ta_volume_theories": [
        ("القيمة الابتدائية لرصيد الحجم اعتباطية؛ يلزم مصدر حجم واحد متسق، ولا تخلط وحدات الصفقات بالتكات داخل السلسلة.", "OBV's initial value is arbitrary; use one consistent volume source and do not mix traded units and tick counts within the series."),
    ],
    "ta_pivots": [
        ("ثبّت H وL وC للجلسة المكتملة قبل شمعة الإشارة؛ لا تعيد حساب المرجع بمدى اليوم الجاري.", "Freeze completed-session H, L and C before the trigger bar; do not rebuild the reference from the current day's range."),
        ("في المستويات الأساسية P=(H+L+C)/3 وR2=P+(H-L) وS2=P-(H-L)، حيث H وL وC تخص الفترة السابقة.", "The basic levels use P=(H+L+C)/3, R2=P+(H-L), S2=P-(H-L), with H, L and C from the prior period.", "SOURCE_PRINCIPLE", ["session_pivots"], {"expression": "P=(H+L+C)/3; R1=2*P-L; S1=2*P-H; R2=P+H-L; S2=P-H+L", "variables": {"H": "prior completed-session high", "L": "prior completed-session low", "C": "prior completed-session close"}, "domain": "L <= C <= H; fixed source and completed session", "units": "instrument price"}),
    ],
    "fa_quantitative": [
        ("الهامش التشغيلي يساوي دخل التشغيل مقسومًا على صافي الإيراد، ودوران المخزون يساوي تكلفة المبيعات مقسومة على متوسط مخزون الفترة.", "Operating margin divides operating income by net revenue; inventory turnover divides cost of sales by average period inventory.", "SOURCE_PRINCIPLE", ["sec"], {"expression": "operating_margin = operating_income / net_revenue; inventory_turnover = cost_of_sales / average_inventory", "variables": {"average_inventory": "(opening_inventory + closing_inventory)/2"}, "domain": "positive denominators; matching reporting period", "units": "margin fraction; turnover times per period"}),
        ("تختلف نسبة الدين المالي إلى الحقوق عن إجمالي الالتزامات إلى الحقوق؛ احفظ تعريف البسط ولا تقارن تعريفين كأنهما واحد.", "Financial debt/equity differs from total liabilities/equity; retain numerator definitions and do not compare them as one ratio."),
    ],
    "fa_qualitative": [
        ("احفظ دليلًا مؤيدًا وآخر مضادًا ومصدرًا وتاريخًا لكل حكم نوعي؛ المستند المتأخر لا يعيد كتابة الحكم التاريخي.", "Retain supporting/counterevidence, source and date for each judgment; later documents do not rewrite historical assessments."),
    ],
    "fa_macro": [
        ("نسخة البيانات الاقتصادية هي القيم التي كانت متاحة في تاريخ محدد؛ المراجعة اللاحقة لا تصبح معلومة سابقة.", "An economic vintage is the data available at a specified historical date; later revisions do not become earlier knowledge.", "SOURCE_PRINCIPLE", ["vintages"]),
        ("نمو الفترة يساوي x[t]/x[t-1]-1؛ النمو السنوي يقارن بالفترة النظيرة، ويجب إعلان التعديل الموسمي والتسنين.", "Period growth uses x[t]/x[t-1]-1; year-over-year growth uses the corresponding prior-year period, with seasonal adjustment and annualization declared.", "SOURCE_PRINCIPLE", ["vintages"], {"expression": "growth = x[t]/x[t-k]-1", "variables": {"k": "1 for adjacent period; observations per year for year-over-year"}, "domain": "nonzero compatible base; same vintage and series definition", "units": "fraction; multiply by 100 for percent"}),
    ],
    "fa_industry": [
        ("افصل نمو الطلب عن إضافة المعروض وتغير الحصة؛ زيادة مبيعات القطاع لا تضمن تحسن ربحية كل شركة.", "Separate demand growth, added supply and share changes; higher industry sales do not ensure every firm's profitability improves."),
    ],
    "fa_company": [
        ("احسب تطابق صافي الربح مع التدفق التشغيلي عبر البنود غير النقدية ورأس المال العامل؛ اختلاف التصنيف المحاسبي يحتاج تسوية معلنة.", "Reconcile net income and operating cash through noncash items and working capital; differing accounting classifications need explicit adjustments."),
        ("لا تجمع أربعة تقارير تراكمية كأرباع مستقلة؛ حوّل التدفقات منذ بداية السنة إلى فترات منفصلة قبل حساب الاثني عشر شهرًا.", "Do not sum four year-to-date reports as separate quarters; derive discrete periods before trailing-twelve-month totals."),
    ],
    "fa_graham_dodd": [
        ("إذا استعمل هامش الأمان النسبي فعرّفه صراحة مثل (V-P)/V مع قيمة موجبة متحفظة؛ النسبة اختيار محلي وليست عتبة منسوبة لجراهام.", "When using relative margin of safety, explicitly define a measure such as (V-P)/V with positive conservative value; its threshold is local, not attributed to Graham.", "OPERATIONAL_CHECKLIST", []),
    ],
    "fa_behavioral": [
        ("قارن التوقع المكتوب بنتيجته ومعدل الأساس وسجل خطأ التقدير؛ لا تختَر الصفقات الرابحة وحدها لتقييم الانضباط.", "Compare recorded forecasts with outcomes and base rates, and retain estimation error; do not assess discipline from winners alone."),
    ],
    "fa_value": [
        ("دوّن قيمة السيناريو المحافظ والسعر القابل للتنفيذ وتاريخيهما وعملة المطالبة؛ فرق قيمة لشركة ليس فرق سعر لعقد دون جسر موثق.", "Retain conservative value, executable price, dates and claim currency; an issuer valuation gap requires a documented bridge to the broker contract."),
    ],
    "fa_growth": [
        ("النمو المركب السنوي هو (النهاية/البداية)^(1/السنوات)-1 عند قاعدة موجبة ومدة موجبة؛ التحول من خسارة إلى ربح لا يعطى هذا المعدل.", "CAGR is (ending/beginning)^(1/years)-1 for a positive base and positive horizon; a loss-to-profit transition is not assigned this rate."),
    ],
    "fa_income": [
        ("عرّف العائد الماضي بمجموع التوزيعات النقدية لفترة معلنة على السعر الحالي؛ العائد المتوقع والتوزيع الخاص ورد رأس المال يعرض كل منها منفصلًا.", "Define trailing yield using cash distributions over a declared period divided by current price; show forward yield, special payouts and return of capital separately."),
    ],
    "fa_garp": [
        ("PEG=(P/E)/g%؛ نمو 10% يدخل بوصفه 10 لا 0.10، ويجب تطابق أفق الربح والنمو؛ PEG المنخفض وحده لا يثبت الجودة.", "PEG=(P/E)/g%; 10% growth enters as 10, not 0.10, with compatible earnings/growth horizons; low PEG alone does not establish quality.", "SOURCE_PRINCIPLE", ["multiples"], {"expression": "PEG = PE / growth_percent", "variables": {"growth_percent": "100 * growth_fraction"}, "domain": "positive earnings and growth; declared forecast horizon", "units": "PE divided by percentage points"}),
    ],
    "fa_index": [
        ("قارن عائد الصندوق بعائد مؤشر مطابق العملة والتوزيعات والتواريخ بعد الرسوم؛ فرق التتبع يختلف عن تذبذب فروق التتبع.", "Compare fund returns with a benchmark matching currency, distributions and dates after fees; tracking difference differs from variability of tracking differences."),
    ],
    "fa_fund": [
        ("قيمة الوحدة الصافية تستخدم أصول الصندوق ناقص التزاماته على الوحدات القائمة عند التقييم؛ سعر البورصة قد يختلف عنها.", "Per-unit NAV uses fund assets less liabilities divided by outstanding units at valuation time; exchange price may differ from NAV."),
    ],
    "fa_commodity": [
        ("المخزون رصيد والإنتاج والاستهلاك تدفقات لفترة؛ طابق الوحدة والمكان والدرجة ووقت القياس قبل بناء ميزان السلعة.", "Inventory is a stock; production/use are period flows. Match units, location, grade and measurement time before a commodity balance."),
    ],
    "fa_currency": [
        ("عائد الأصل بالعملة المحلية هو (1+عائد الأصل الأجنبي)*(1+عائد العملة الأجنبية)-1 عند تعريف سعر الصرف بوحدات المحلية لكل أجنبية.", "Domestic return is (1+foreign-asset return)*(1+foreign-currency return)-1 when FX is domestic units per foreign unit.", "SOURCE_PRINCIPLE", ["currency_management"], {"expression": "R_domestic=(1+R_asset)*(1+R_fx)-1", "variables": {"R_fx": "S_end/S_start-1; S is domestic currency per foreign currency"}, "domain": "same holding interval; unhedged asset; positive S", "units": "return fractions"}),
    ],
    "fa_bond": [
        ("المدة المعدلة تقرب تغير السعر النسبي بسالب المدة في تغير العائد العشري؛ هي تقريب محلي حساس لحجم الحركة وليست توقع عائد.", "Modified duration approximates relative price change as minus duration times the decimal yield change; accuracy depends on move size and it does not forecast returns.", "SOURCE_PRINCIPLE", ["yield_duration"], {"expression": "delta_price / price ~= -modified_duration * delta_yield", "variables": {"delta_yield": "decimal yield change; 1 basis point = 0.0001"}, "domain": "small yield change; same yield convention; fixed-flow assumptions", "units": "relative price fraction"}),
        ("احفظ تاريخ التسوية والفائدة المستحقة وسعرًا نظيفًا أو شاملًا؛ السند القابل للاستدعاء يحتاج معالجة خيار لا تمنحها حاسبة كوبون ثابت.", "Retain settlement date, accrued interest and clean/full price basis; a callable bond needs option treatment beyond a fixed-coupon calculator."),
    ],
    "fa_equity": [
        ("طابق فئة السهم وحقوقها وعدد الأسهم المخفف مع القيمة؛ الأسهم الحرة للسيولة ليست بديلًا عن الأسهم القائمة في التقييم.", "Match share class, rights and diluted share count to value; free float for liquidity does not replace outstanding shares in valuation."),
    ],
    "fa_absolute": [
        ("الدخل المتبقي لكل سهم RI[t]=EPS[t]-r*B[t-1]؛ نموذج القيمة يضيف القيمة الدفترية الحالية إلى القيمة الحالية للدخل المتبقي المتوقع.", "Per-share residual income uses RI[t]=EPS[t]-r*B[t-1]; value adds current book value to the present value of expected residual income.", "SOURCE_PRINCIPLE", ["residual_income"], {"expression": "RI[t]=EPS[t]-r*B[t-1]; V[0]=B[0]+sum(RI[t]/(1+r)^t)", "variables": {"B": "common-equity book value per share", "r": "required equity return for the period"}, "domain": "consistent common-equity accounting, distributions and share basis", "units": "currency per share; r as fraction"}),
        ("نموذج الدخل المتبقي مرجع بحث فقط في هذه النسخة؛ لا تنفذه حاسبات DCF أو NAV بالاسم، وتحتاج بنود الدخل الشامل تسوية مناسبة.", "Residual-income valuation is research reference only in this release; DCF/NAV calculators do not implement it by association, and comprehensive-income items need appropriate reconciliation."),
    ],
    "fa_relative": [
        ("احسب ربح السهم التاريخي من التقارير المتاحة يوم السعر؛ نتيجة معدلة نشرت بعده تبقى نسخة لاحقة.", "Compute historical EPS from reports available on the price date; restatements released later remain later vintages.", "SOURCE_PRINCIPLE", ["multiples"]),
    ],
    "fa_asset_based": [
        ("افحص الرهون والحقوق السابقة ومصاريف التصفية قبل القسمة على الأسهم؛ لا تخصم الدين مرتين إذا دخل بالفعل ضمن الالتزامات.", "Review liens, senior claims and liquidation costs before dividing by shares; do not subtract debt twice when already included in liabilities."),
    ],
    "ap_top_down": [
        ("لكل قناة انتقال أفق وزمن إتاحة ومحفز إبطال؛ لا يعد توافق الاقتصاد والقطاع والشركة ثلاث أدلة مستقلة إذا اشتقت من خبر واحد.", "Each transmission channel needs a horizon, availability time and falsifier; macro, sector and company agreement are not three independent observations when derived from one release."),
    ],
    "ap_bottom_up": [
        ("اعرض جسرًا بين حقيقة مالية وافتراض وناتج حسابي؛ اختبر أثر تراجع فرضية الشركة قبل نسب نتيجة التقييم إلى دقة المنهج.", "Show the bridge from financial fact to assumption to calculation; stress a failed company thesis before attributing valuation results to method accuracy."),
    ],
    "ap_ddm": [
        ("قيمة نهاية السنة n هي D[n+1]/(r-g)، ثم تخصم من نهاية n؛ لا تستخدم D[n] مكان التوزيع التالي ولا تخصم النهاية مرتين.", "Year-n terminal value uses D[n+1]/(r-g) and is discounted from year n; do not substitute D[n] or discount the terminal amount twice.", "SOURCE_PRINCIPLE", ["ddm"], {"expression": "V[0]=sum(D[t]/(1+r)^t, t=1..n) + D[n+1]/((r-g)*(1+r)^n)", "variables": {"D": "per-share expected cash dividend", "r": "period equity discount rate", "g": "sustainable terminal growth"}, "domain": "r > g; 1+r > 0; consistent period and currency", "units": "currency per share; rates as fractions"}),
    ],
    "ap_dcf": [
        ("FCFF=NI+NCC+الفائدة*(1-الضريبة)-الاستثمار الثابت-استثمار رأس المال العامل؛ وFCFE=NI+NCC-الاستثمارين+صافي الاقتراض.", "FCFF=NI+NCC+interest*(1-tax)-fixed investment-working-capital investment; FCFE=NI+NCC-fixed investment-working-capital investment+net borrowing.", "SOURCE_PRINCIPLE", ["fcf"], {"expression": "FCFF=NI+NCC+interest*(1-tax)-FCInv-WCInv; FCFE=NI+NCC-FCInv-WCInv+net_borrowing", "variables": {"NCC": "noncash charges with required adjustments", "FCInv": "net fixed-capital investment", "WCInv": "operating working-capital investment"}, "domain": "same reporting period; reconciled accounting classifications", "units": "currency per period; tax as fraction"}),
        ("EBITDA والربح المحاسبي ليسا تدفقًا حرًا؛ لا تهمل الاستثمار ورأس المال العامل ثم تسمي الناتج FCFF.", "EBITDA and accounting earnings are not free cash flow; omitting investment and working capital does not produce FCFF.", "SOURCE_PRINCIPLE", ["fcf"]),
        ("قيمة النهاية TV[n]=CF[n+1]/(r-g) تخصم من n؛ تدفق الشركة يخصم بـWACC وتدفق المساهم بتكلفة حقوقه مع جسر دين ونقد بلا ازدواج.", "Terminal TV[n]=CF[n+1]/(r-g) is discounted from n; use WACC for firm flows, equity cost for shareholder flows, and a debt/cash bridge without double-counting."),
    ],
    "ap_relative": [
        ("احفظ مجموعة النظراء بما فيها المستبعدون وأسبابهم وطريقة الوسيط أو المتوسط وأوزانه؛ لا تحذف القيم المتطرفة بعد معرفة النتيجة.", "Retain peers, excluded cases/reasons and median/mean weighting; do not remove outliers after observing outcomes."),
    ],
    "ap_asset_based": [
        ("ميز قيمة الأصول المعدلة من القيمة الدفترية، وسعر البيع المتوقع من سعر بيع قابل للتنفيذ خلال مدة معلنة.", "Separate adjusted asset value from book value and expected sale price from a realizable sale within a declared horizon."),
    ],
    "ap_present_value": [
        ("في المعدل الثابت PV=sum(CF[t]/(1+r)^t)؛ يجب أن تكون 1+r موجبة والتدفقات الموقعة والفترات معلنة ولا تعوض قيمة ناقصة بصفر.", "For a fixed rate, PV=sum(CF[t]/(1+r)^t); require positive 1+r and explicit signed flows/times, keeping missing values distinct from zero.", "OPERATIONAL_CHECKLIST", [], {"expression": "PV=sum(CF[t]/(1+r)^t)", "variables": {"CF": "explicit signed cash flow", "t": "time in discount-rate periods"}, "domain": "1+r > 0; t >= 0; finite supplied inputs", "units": "currency; rate per matching period"}),
    ],
    "ap_multiples": [
        ("عرّف EV بالقيمة السوقية للحقوق والدين والمطالبات الملائمة ناقص النقد القابل للخصم؛ لا تستخدم P/EBITDA بدل EV/EBITDA.", "Define EV from market equity, debt and relevant claims less eligible cash; do not substitute P/EBITDA for EV/EBITDA.", "SOURCE_PRINCIPLE", ["multiples"]),
    ],
}


def rule_protocol(entry):
    """A deterministic research-record specification, not a new signal engine."""
    return {
        "id": entry["id"] + ".protocol", "schema_version": 1,
        "version": PROTOCOL_VERSION, "rule_set_version": CATALOG_VERSION,
        "status": "RESEARCH_RECORD_SPECIFICATION", "optional": True,
        "execution_authority": "NONE", "evaluates_rule_text": False,
        "summary_ar": [
            "مدخلات المرجع: " + "؛ ".join(entry["requirements_ar"]) + ". كل نموذج برمجي مرتبط يستعمل عقد مدخلاته المحدد.",
            "التأكيد: احفظ وقت الملاحظة ووقت إتاحة البيانات ووقت القرار؛ لا تستخدم بيانات نشرت أو محورًا تأكد بعد القرار.",
            "معاملات القواعد: احفظ القيمة ووحدتها ومرجعها أو إصدار النموذج؛ افصل معادلة المصدر عن السماحة أو الافتراض المحلي.",
            "الإبطال: أعلن سببًا قابلًا للفحص ومدة صلاحية قبل معرفة النتيجة، واحفظ القواعد غير المحسومة دون تعويض البيانات بصفر.",
            "التعلم: اربط النتائج بإصدار القاعدة والأداة والفريم وحالة السوق؛ احتفظ بالإخفاقات وقارن فترة لاحقة بعد التكاليف.",
            "التطوير: إصدار جديد موثق واختبارات اتجاهين وإبطال ومراجعة لاحقة؛ حفظ المرجع لا يرسل أمرًا أو يرفع المخاطرة أو يعدل الكود تلقائيًا."
        ],
        "summary_en": [
            "Reference inputs: " + "; ".join(entry["requirements_en"]) + ". Each linked coded model uses its specific input contract.",
            "Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.",
            "Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.",
            "Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.",
            "Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.",
            "Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically."
        ],
        "entry": {
            "research_review_rule_ids": [rule["id"] for rule in entry["rule_records"]],
            "semantics": "DOCUMENT_REVIEW_AND_UNRESOLVED_ITEMS; NOT_BOOLEAN_TRADE_CONDITIONS",
            "text_ar": "تبدأ مراجعة المدرسة بهوية أصل ووقت قرار ومصدر بيانات معلوم؛ تعالج قواعد المرجع وحدوده قبل حفظ فرضية. الإشارة التنفيذية تحتاج عقد نموذج مسجل مستقل.",
            "text_en": "Start research with instrument identity, decision time and identified data; review the school's rules/limits before recording a thesis. An executable signal requires a separate registered model contract.",
        },
        "invalidation": {
            "conditions_ar": list(entry["exceptions_ar"]), "conditions_en": list(entry["exceptions_en"]),
            "policy": "RECORD_FALSIFIER_AND_EXPIRY_BEFORE_OUTCOME; DO_NOT_BACKDATE_REVISIONS",
            "execution_authority": "REGISTERED_MODEL_CONTRACT_ONLY",
        },
        "data_prerequisites": {
            "scope": "SCHOOL_REFERENCE", "keys": list(entry["requirements"]),
            "missing_policy": "DATA_MISSING; DO_NOT_SUBSTITUTE_ZERO_OR_UNDECLARED_PROXY",
            "runtime_policy": "EACH_REGISTERED_MODEL_USES_ITS_OWN_MANDATORY_INPUT_CONTRACT",
        },
        "confirmation": {
            "required_times": ["observation_time", "available_at", "decision_time"],
            "conditional_times": {"price_pivot_or_pattern": "confirmed_at", "forecast": "created_at"},
            "eligibility": "available_at <= decision_time; confirmed_at/created_at <= decision_time when applicable",
            "revision_policy": "USE_POINT_IN_TIME_VINTAGE; RETAIN_ORIGINAL_AND_LATER_REVISIONS_SEPARATELY",
            "bar_policy": "COMPLETE_BARS_ONLY; PIVOT_CONFIRMATION_PRECEDES_ELIGIBLE_BREAK",
        },
        "parameter_provenance": {
            "required_fields": ["name", "value", "units", "origin", "reference_or_model_version", "effective_at"],
            "origins": ["SOURCE_DEFINITION", "HOUSE_MODEL_PARAMETER", "LOCAL_DOCUMENTED_ASSUMPTION"],
            "policy": "SOURCE_FORMULA_IS_SEPARATE_FROM_LOCAL_TOLERANCE; NO_UNIVERSAL_PROFITABILITY_THRESHOLD",
            "reference_ids": [ref["id"] for ref in entry["references"]],
        },
        "output": {
            "type": "RESEARCH_RECORD", "issues_trade_order": False, "creates_committee_vote": False,
            "required_fields": ["school_id", "rule_set_version", "protocol_version", "instrument_id", "decision_time", "input_snapshot_hash", "source_ids", "parameter_provenance", "reviewed_rule_ids", "unresolved_rule_ids", "falsifier", "expires_at", "state"],
            "states": ["RESEARCH_RECORDED", "UNRESOLVED", "DATA_MISSING", "INVALIDATED"],
            "score_semantics": "NO_WIN_PROBABILITY_OR_CONFIDENCE_IS_INFERRED_FROM_RULE_COUNT",
        },
        "learning": {
            "mode": "OBSERVE_OUTCOMES_ONLY", "rewrites_rules": False, "raises_risk_limits": False,
            "required_fields": ["research_record_id", "rule_set_version", "outcome_horizon", "outcome_available_at", "baseline", "cost_assumptions"],
            "policy": "COMPARE_VERSIONED_HYPOTHESES_ON_LATER_DATA; KEEP_FAILURES_AND_MISSING_OUTCOMES",
        },
        "change_policy": {
            "mode": "VERSIONED_REVIEWED_CHANGE", "automatic_promotion": False,
            "required_evidence": ["source_scope", "parameter_rationale", "causal_timing", "input_contract", "bullish_bearish_and_invalidation_cases", "later_period_validation"],
            "runtime_model_ids": list(entry["strategy_ids"]),
            "school_complete": False,
        },
    }


def validate(payload):
    schools = payload["schools"]
    expected = {"technical": 30, "fundamental": 20, "approach": 8}
    if len(schools) != 58 or len({s["id"] for s in schools}) != 58:
        raise ValueError("Catalog must preserve all 58 unique user entries")
    ids = {s["id"] for s in schools}
    for category, count in expected.items():
        seq = [s["order"] for s in schools if s["category"] == category]
        if seq != list(range(1, count + 1)):
            raise ValueError("Category order mismatch: " + category)
    for s in schools:
        if len(s["rules_ar"]) != len(s["rules_en"]) or len(s["rules_ar"]) < 4:
            raise ValueError("Incomplete bilingual rule list: " + s["id"])
        if set(s["related_ids"]) - ids or (s["alias_of"] and s["alias_of"] not in ids):
            raise ValueError("Broken catalog relation: " + s["id"])
        if not s["references"] or s["complete_school"]:
            raise ValueError("Missing references or false exhaustive claim")
        if s["requirements"] != list(dict.fromkeys(s["requirements"])):
            raise ValueError("Duplicate requirement")
        for rule in s["rule_records"]:
            if rule["kind"] == "SOURCE_PRINCIPLE" and not rule["reference_ids"]:
                raise ValueError("Unattributed source principle")
            if set(rule["reference_ids"]) - set(SOURCES):
                raise ValueError("Unknown source")
    return payload


def build():
    ENTRIES.clear()
    technical()
    fundamental()
    approaches()
    additions = {
        'ta_classical': ['rectangle_breakout', 'flag_breakout', 'darvas_rising_boxes'],
        'ta_indicators': ['stochastic_rebound', 'rsi_wilder_rebound', 'macd_signal_cross', 'adx_di_cross', 'cci_reentry', 'williams_reentry'],
        'ta_harmonic': ['harmonic_gartley', 'harmonic_bat', 'harmonic_butterfly'],
        'ta_harmonic_patterns': ['harmonic_gartley', 'harmonic_bat', 'harmonic_butterfly'],
        'ta_fibonacci': ['harmonic_gartley', 'harmonic_bat', 'harmonic_butterfly'],
        'ta_wyckoff': ['wyckoff_range_expansion'],
        'ta_ict': ['liquidity_bos_retest'],
        'ta_liquidity': ['liquidity_bos_retest'],
        'ta_smart_money': ['liquidity_bos_retest'],
        'ta_candlesticks': ['three_bar_reversal'],
        'ta_chart_patterns': ['rectangle_breakout', 'flag_breakout', 'darvas_rising_boxes'],
        'ta_volume': ['mfi_tick_rebound', 'wyckoff_range_expansion'],
        'ta_volume_theories': ['mfi_tick_rebound', 'wyckoff_range_expansion'],
    }
    for entry in ENTRIES:
        entry['strategy_ids'] = list(dict.fromkeys(entry['strategy_ids']+additions.get(entry['id'], [])))
        entry['mapped_strategy_ids'] = list(entry['strategy_ids'])
    models = {model["id"]: model for model in registry_manifest()}
    for entry in ENTRIES:
        entry["requirements_scope"] = "SCHOOL_REFERENCE"
        entry["rule_set_version"] = CATALOG_VERSION
        entry["rule_protocol"] = rule_protocol(entry)
        entry["runtime_models"] = [
            {"id": sid, "version": models[sid]["version"],
             "inputs": models[sid]["data_requirements"],
             "minimum_bars": models[sid]["min_bars"],
             "evidence_group": models[sid]["evidence_group"],
             "definition": models[sid]["contract"]["definition"],
             "school_complete": False}
            for sid in entry["strategy_ids"]]
        calculators = CALCULATORS.get(entry["id"], [])
        entry["available_calculators"] = calculators
        if calculators:
            entry["runtime_scope_ar"] += " تتوفر حاسبات محلية لتقييم مدخلات صريحة موثقة؛ لا تجمع البيانات المالية ولا تصدر أوامر تداول."
            entry["runtime_scope_en"] += " Local calculators evaluate explicit documented inputs; they do not collect financial facts or issue trade orders."
    payload = {
        "schema_version": 1, "catalog_version": CATALOG_VERSION, "curated_as_of": "2026-10-11",
        "counts": {"technical": 30, "fundamental": 20, "approach": 8, "total": 58},
        "completeness_ar": "القائمة تغطي جميع البنود الثمانية والخمسين التي طلبها المستخدم. القواعد ملخصات أصلية موثقة وقوائم تحقق وبيان نطاق، وليست نسخة كاملة من جميع كتب المدارس أو إثبات اكتمال تنفيذها. البنود المتداخلة محفوظة بروابط ولا تضاعف أصوات اللجنة.",
        "completeness_en": "All 58 user-listed entries are preserved. Rules are original sourced summaries, checklists and scope declarations, not complete reproductions of every school's literature or proof of full executable coverage. Overlapping entries are linked and do not multiply committee votes.",
        "data_policy": "MT5_ONLY_RUNTIME_WITH_EXPLICIT_LOCAL_REFERENCE_INPUTS",
        "runtime_external_fetch": False, "model_api_required": False,
        "provenance_ar": "مبدأ مصدر: مختصر من المرجع المحدد. قائمة تحقق تشغيلية: إجراء مراجعة من إعداد Quant Trading AI. تعريف محلي: قاعدة النموذج في كود Quant Trading AI. المصادر مرجعية ولا تُجلب تلقائيًا عند التداول.",
        "provenance_en": "SOURCE_PRINCIPLE is a concise sourced principle; OPERATIONAL_CHECKLIST is a Quant Trading AI-authored review procedure; HOUSE_DEFINITION is a declared Quant Trading AI code rule. References are not fetched automatically during trading.",
        "development_policy_ar": "أي توسيع يضيف قاعدة بإصدار ودليل مصدر ومدخلات واختبارات صاعدة وهابطة وحالات إبطال. حفظ المعرفة منفصل عن الترخيص بالتنفيذ. التعلم يرصد النتائج ولا يغيّر القواعد أو المخاطرة دون إصدار مراجَع.",
        "development_policy_en": "Every extension adds a versioned rule, source evidence, inputs, bullish/bearish and invalidation tests. Knowledge storage is separate from execution authority. Learning records outcomes; it does not change rules or risk without a reviewed version.",
        "schools": ENTRIES,
    }
    validate(payload)
    DEST.mkdir(parents=True, exist_ok=True)
    canonical = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    (DEST / "catalog.json").write_text(canonical, encoding="utf-8")
    lines = ["# مرجع مدارس Quant Trading AI — الإصدار " + CATALOG_VERSION, "", payload["completeness_ar"], "", payload["provenance_ar"], "", payload["development_policy_ar"], "",
             "الحفظ والتشغيل محليان. بيانات السوق تأتي من MT5. القوائم المالية وبيانات التقييم غير الموجودة في المنصة تحتاج ملفات محلية موثقة، ولا تُستنتج من الشموع. وجود حاسبة لا يجعل الافتراضات صحيحة ولا يحوّل التقييم إلى أمر تداول.", ""]
    categories = {"technical": "مدارس التحليل الفني — 30 بندًا", "fundamental": "مدارس التحليل الأساسي — 20 بندًا", "approach": "مناهج التحليل الأساسي — 8 بنود"}
    for category, title in categories.items():
        lines += ["## " + title, ""]
        for entry in (s for s in ENTRIES if s["category"] == category):
            lines += [f"### {entry['order']}. {entry['name_ar']}", "", f"المعرف: `{entry['id']}` — {entry['name_en']}", "", entry["scope_ar"], "", "القواعد وقائمة المراجعة:", ""]
            kind_ar = {"SOURCE_PRINCIPLE": "مبدأ مصدر", "OPERATIONAL_CHECKLIST": "قائمة تحقق", "HOUSE_DEFINITION": "تعريف محلي"}
            for rule in entry["rule_records"]:
                source_suffix = ""
                if rule["reference_ids"]:
                    source_suffix = " — " + "، ".join(f"[{SOURCES[r][0]}]({SOURCES[r][1]})" for r in rule["reference_ids"])
                lines.append(f"- **{kind_ar[rule['kind']]}:** {rule['text_ar']}{source_suffix}")
            lines += ["", "الاستثناءات والحدود:", ""] + ["- " + x for x in entry["exceptions_ar"]]
            lines += ["", "البيانات المطلوبة:", ""] + ["- " + x for x in entry["requirements_ar"]]
            lines += ["", "آلية تطبيق القواعد ومراجعتها — الإصدار " + PROTOCOL_VERSION, ""] + ["- " + x for x in entry["rule_protocol"]["summary_ar"]]
            lines += ["", "نطاق التطبيق الحالي: " + entry["runtime_scope_ar"], "", entry["unavailable_data_policy_ar"], ""]
            if entry["strategy_ids"]:
                lines += ["النماذج المرتبطة: " + "، ".join("`" + x + "`" for x in entry["strategy_ids"]), ""]
            if entry["available_calculators"]:
                lines += ["الحاسبات المحلية المتاحة: " + "، ".join("`" + x + "`" for x in entry["available_calculators"]), ""]
            if entry["alias_of"]:
                lines += [f"بند متداخل مرتبط بـ `{entry['alias_of']}`؛ محفوظ لتطابق القائمة الأصلية.", ""]
            lines += ["المراجع وحدود الاستناد:", ""] + [f"- [{ref['title']}]({ref['url']}): {ref['scope_ar']}" for ref in entry["references"]] + [""]
    (DEST / "reference-ar.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    english=["# Quant Trading AI school reference — version " + CATALOG_VERSION, "", payload["completeness_en"], "", payload["provenance_en"], "", payload["development_policy_en"], ""]
    kind_en={"SOURCE_PRINCIPLE":"Source principle","OPERATIONAL_CHECKLIST":"Operational checklist","HOUSE_DEFINITION":"Quant Trading AI computational definition"}
    for category,title in (("technical","Technical analysis — 30 entries"),("fundamental","Fundamental analysis — 20 entries"),("approach","Fundamental approaches — 8 entries")):
        english += ["## "+title,""]
        for entry in (s for s in ENTRIES if s["category"]==category):
            english += [f"### {entry['order']}. {entry['name_en']}", "", f"ID: `{entry['id']}`", "", entry["scope_en"], "", "Rules and review checklist:", ""]
            for rule in entry["rule_records"]:
                suffix=" — "+", ".join(f"[{SOURCES[r][0]}]({SOURCES[r][1]})" for r in rule["reference_ids"]) if rule["reference_ids"] else ""
                english.append(f"- **{kind_en[rule['kind']]}:** {rule['text_en']}{suffix}")
            english += ["", "Exceptions and limits:", ""]+["- "+x for x in entry["exceptions_en"]]
            english += ["", "Required data:", ""]+["- "+x for x in entry["requirements_en"]]
            english += ["", "Rule application and review protocol — version " + PROTOCOL_VERSION, ""] + ["- " + x for x in entry["rule_protocol"]["summary_en"]]
            english += ["", "Current scope: "+entry["runtime_scope_en"], "", entry["unavailable_data_policy_en"], ""]
            if entry["strategy_ids"]:english += ["Linked models: "+", ".join("`"+x+"`" for x in entry["strategy_ids"]),""]
            if entry["available_calculators"]:english += ["Available local calculators: "+", ".join(entry["available_calculators"]),""]
            if entry["alias_of"]:english += [f"Overlapping entry: `{entry['alias_of']}`. This does not create another committee vote.",""]
            english += ["Sources and attribution scope:",""]+[f"- [{ref['title']}]({ref['url']}): {ref['scope_en']}" for ref in entry["references"]]+[""]
    (DEST / "reference-en.md").write_text("\n".join(english)+"\n",encoding="utf-8")
    manifest = {"schema_version": 1, "catalog_version": payload["catalog_version"], "entries": 58,
                "rule_count": sum(len(s["rule_records"]) for s in ENTRIES), "data_keys": sorted(DATA),
                "files": {f: hashlib.sha256((DEST/f).read_bytes()).hexdigest() for f in ("catalog.json", "reference-ar.md", "reference-en.md")}}
    (DEST / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"entries": 58, "rules": manifest["rule_count"], "counts": payload["counts"], "catalog_sha256": manifest["files"]["catalog.json"]}))
    return payload


if __name__ == "__main__":
    build()
