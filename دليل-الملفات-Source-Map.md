# دليل الملفات | Source code map (العربية + English)

## ابحث من هنا | Start here
هذه نسخة مصدر منظّمة للإصدار 0.7.16. افتح `src/nexus/` لكود التطبيق، `tests/` لفحوصه، و`ui/` لتصميم الشاشات.
This is an organized source snapshot for version 0.7.16. Start in `src/nexus/` for application logic, `tests/` for verification, and `ui/` for the interface.

## خريطة سريعة | Quick map
| المسار / Path | الدور بالعربية | Role in English |
|---|---|---|
| `src/nexus/engine.py` | دورة تحليل السوق | Market scan and analysis cycle |
| `src/nexus/strategies.py`, `specialists.py`, `local_models.py`, `extended_models.py` | النماذج والقواعد | Model and rule evaluators |
| `src/nexus/committee.py`, `multischool.py`, `confluence.py` | جمع الأدلة والقرار وأسباب الرفض | Evidence aggregation and decision reasons |
| `src/nexus/risk.py`, `execution.py`, `broker.py`, `demo_live.py` | فحوص المخاطر وتنفيذ الوسيط | Risk guards and broker execution paths |
| `src/nexus/store.py`, `learning_journal.py`, `learning/` | التخزين والتدقيق والتعلم الظلي | Persistence, audit and shadow learning |
| `src/nexus/external_research.py`, `llm_research.py` | موصلات البحث وLLM الاختيارية | External research and optional LLM connectors |
| `src/nexus/config/` | الإعدادات ومخططات التحقق | Configuration and validation schemas |
| `tests/test_*.py` | اختبارات الوحدة والتكامل | Unit and integration tests |
| `tools/` | أدوات الجودة والمتصفح والبحث | Quality, browser and research utilities |
| `ui/` | ملفات HTML/CSS/JS للواجهة | Frontend HTML/CSS/JS |
| `docs/agent-rules/` | تعريفات منظمة للنماذج | Structured model contracts |
| `docs/` | مواصفات وشرح البنية والمصادر | Architecture, API and safety specifications |

## كلمات للبحث | Search terms
- قرار اللجنة / committee: `decide`, `reason_codes`, `eligible`
- شموع الدقيقة المكتملة / closed M1 bars: `M1`, `completed`, `as_of`, `bar_close_time`
- المخاطر / risk: `RiskManager`, `max_exposure`, `daily_loss`, `portfolio`
- إرسال الوسيط / broker send: `order_send`, `DEMO_LIVE`, `trade_allowed`
- لماذا لم يدخل؟ / rejection reasons: `COMMITTEE_DECISION`, `REJECT`, `WAIT`, `cost-adjusted`, `entry zone`
- التعلم الظلي / shadow learning: `OBSERVATIONAL`, `proposal`, `drift`, `acceptance`
- APIs: `NEXUS_MASSIVE_API_KEY`, `Frankfurter`, `BLS`, `World Bank`, `NEXUS_GEMINI_API_KEY`, `NEXUS_GROQ_API_KEY`, `NEXUS_OPENROUTER_API_KEY`

## حالة معمارية مهمة | Important architecture note
الموجود 58 مقيّم قواعد محلي، وليس 58 وكيل AI مستقل. مزودات LLM اختيارية للتعليق البحثي ولا تصوّت ولا ترسل أوامر. مسار السكالب الحالي يستخدم إشارة M1 مع تأكيد M15/H1؛ H4 غير موصول بمسار القرار السريع في هذه النسخة. يجب تقييم أي تعديل على بيانات زمنية بعد التكاليف.
The codebase contains 58 deterministic rule evaluators, not 58 autonomous AI agents. LLM providers are optional research commentary only. The current fast path uses M1 signals with M15/H1 confirmation; H4 is not wired into the fast decision path. Any policy change needs chronological after-cost evaluation.

لا تشمل الحزمة مفاتيح API أو سجلات أو قواعد بيانات تداول. أرقام حسابات الاختبار أُخفيت. هذه حزمة مصدر وليست تطبيقاً جاهزاً للتشغيل، ولا تعني أن منفذ DEMO يعمل.
No API keys, runtime logs, or trading databases are included. Test account identifiers were anonymized. This is source, not a runnable release, and does not mean DEMO execution is active.
