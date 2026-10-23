# خطة بنية الوكلاء متعددة المدارس | Multi-school Agent Architecture Plan

**الحالة / Status:** تصميم مقترح فقط — لم يتغير كود التداول ولم تُرسل أوامر.  
**النسخة المرجعية / Source snapshot:** Quant Trading AI 0.7.16 (working-tree source bundle).

## 1. الهدف | Goal

تحويل النماذج المسجلة إلى وكلاء تحليل مستقلين بعقود موحدة، ثم تجميع أدلتهم في لجنة قرار قابلة للتفسير. الوكلاء يحللون؛ لا يملكون صلاحية المخاطر أو الوسيط. تبقى إشارة الدخول على شمعة M1 مكتملة، بينما يقدّم H4/H1 الاتجاه والسياق، وM15 يؤكد البنية، ويمكن استخدام M5 كفحص جودة اختياري لا كشرط دخول.  
Turn registered models into independent, typed analysis agents and aggregate their evidence through an explainable committee. Agents analyze; they cannot change risk limits or call the broker. Entry remains on a completed M1 bar, with H4/H1 providing context and M15 confirming structure; M5 may be an optional quality check, never a mandatory entry signal.

## 2. الوضع الحالي المثبت من المصدر | Verified current source state

- يوجد 58 معرّف نموذج/قاعدة مسجل، وليس 58 عملية ذكاء لغوي مستقلة. هي مقيمات حتمية تعيد أدلة وحالة وسبب انتظار أو نقص.
- مسار السكالب الحالي يقرأ إشارة M1 ويستخدم تأكيد M15/H1؛ H4 غير موصول بمسار قرار السكالب السريع. المطلوب H4 + M15 + دخول M1 يستلزم تغيير سياسة وقياساً جديداً.
- لجنة القرار، فلاتر الوقت والتكلفة والمخاطر منفصلة في الكود. سجل الفرص المصنفة ليس إذناً بالتنفيذ؛ الأهلية الحالية أضيق من “السوق مؤهل”.
- LLM connectors: Gemini وGroq وOpenRouter موجودة كتعليق بحثي اختياري فقط. لا تصويت ولا تنفيذ، ولا مفاتيح صالحة ثبتت في بيئة المراجعة.
- مصدر البحث الخارجي: Frankfurter وBLS وWorld Bank نجحت في فحص حزمة سابق؛ Massive يتطلب مفتاحاً وخطة مناسبة. هذه ليست أسعار MT5 التنفيذية.
- ن8ن غير مربوط بالبرنامج. يصلح لاحقاً للتقارير والتنبيهات والجدولة، وليس لاتخاذ قرار دخول أو حفظ بيانات اعتماد الوسيط.

## 3. الشكل المقترح | Proposed architecture

```text
MT5 read-only market data
        │ completed native bars + bid/ask + sessions
        ▼
Data Quality & Timeframe Service ── rejects stale/missing/future bars
        │
        ├── Context agents: D1/H4/H1 trend and regime
        ├── Technical-school agents: structure, trend, momentum,
        │   volatility, statistical, candle, harmonic, liquidity/SMC,
        │   volume-proxy (each claim explicitly bounded by available data)
        ├── Fundamental/news agents: timestamped calendar/news/macro facts
        └── Cost/market-state agent: spread, session, volatility, execution cost
                    │ typed evidence only
                    ▼
         School Committee / Decision Orchestrator
         - deduplicate correlated evidence
         - enforce H4 direction + M15 confirmation + M1 trigger
         - show SUPPORT / CONFLICT / MISSING / EXPIRED per school
                    │ proposal only
                    ▼
         Independent Risk Gate (cash limits, portfolio, broker constraints)
                    │ separately authorized only
                    ▼
         MT5 execution adapter → audit → reconciliation

Shadow learning: closed outcomes → cost-corrected labels → offline evaluation
                 → proposal/sandbox → human review; never self-edits live rules.
```

## 4. عقد كل وكيل | Agent contract

كل وكيل يستقبل لقطة موحدة للرمز، والأطر المطلوبة، والشموع المكتملة، وقت اللقطة، الأسعار، السبريد، جلسة السوق، وتوافر البيانات. يعيد `agent_id`, `school`, `model_ids`, `symbol`, `as_of`, `bar_close_time`, `direction`, `state`, `evidence`, `missing_inputs`, `invalidations`, `expiry`, `cost_context`, `version`, و`confidence_basis`.

Each agent receives a normalized symbol snapshot, required native timeframes, completed bars, snapshot time, quote, spread, session, and data availability. It returns typed evidence, direction, state, missing inputs, invalidation, expiry, cost context, code/config version, and an explanation. Confidence must be calibrated from held-out data or omitted; raw model scores are not probabilities.

**ممنوع / Never:** مفاتيح API، أو حسابات وسيط، أو إرسال/إغلاق أوامر، أو تعديل حدود المخاطر داخل الوكلاء. لا تخترع حجم تداول حقيقي من tick_volume؛ سمّه proxy. لا تستخدم شمعة غير مكتملة أو إعادة تجميع اصطناعية للتنفيذ.

## 5. لجنة القرار المقترحة | Decision committee

1. بوابة البيانات: شمعة مكتملة ومتتابعة، سعر/سبريد حديثان، مصدر/منطقة زمنية معروفة.  
2. سياق الاتجاه: H4 يحدد long/short/neutral؛ H1 يراجع الاتساق. إذا تعارض H4 وH1 فالحالة `CONFLICT` أو `WAIT`، لا تصويت أغلبية يتجاوزها.  
3. التأكيد: M15 يحتاج بنية واتجاهاً متوافقين مع السياق؛ غياب البيانات يعني `WAIT`.  
4. المُحفّز: نموذج M1 يقدّم trigger محدداً على شمعة مكتملة وسعر قابل للتنفيذ. M5 لا يحل محل M1.  
5. استقلال الدليل: لا تُحسب مؤشرات مشتقة من السعر نفسه كأنها مدارس مستقلة. وضع حد مساهمة لكل عائلة، وقياس الارتباط خارج العينة.  
6. التكلفة: احسب صافي العائد المتوقع من bid/ask وسيط MT5 والعمولة والانزلاق الموثق. لا تُقبل منطقة إذا كان هدفها الصافي دون التكلفة/الحد الأدنى المقرر.  
7. خروج قابل للتفسير: موافقة/رفض مع أسماء المدارس التي أيدت أو عارضت، والبيانات المفقودة، والسبب المحدد.

1. Data gate validates completed, contiguous bars and fresh broker quote. 2. H4 establishes long/short/neutral; H1 checks alignment. A conflict yields WAIT. 3. M15 confirms structure; missing data yields WAIT. 4. A named M1 model triggers on a closed bar. 5. Correlated indicators do not count as independent schools. 6. Costs use broker bid/ask and evidenced commission/slippage. 7. Every decision records supporting, opposing, missing, and expired evidence.

## 6. توزيع الـ58 | Mapping the 58 models

لا تنشئ 58 خدمة/عملية LLM. أنشئ 58 `AgentAdapter` خفيفة، واحدة لكل سجل نموذج، ثم اجمعها في وكلاء عائلات لإدارة السياق والكفاءة. يحتفظ كل adapter بمعرّف النموذج واختباره الحالي وعقد الشراء/البيع/الإبطال. وكيل العائلة لا يغيّر قاعدة النموذج.

Do not launch 58 separate LLM services. Create 58 lightweight `AgentAdapter`s, one per registry model, and group them into school-family agents for context and efficiency. Each adapter keeps its model ID, current tests, and buy/sell/invalidation contract. Family agents cannot rewrite model rules.

التقسيم يبدأ من قيمة `school` الموجودة في `strategies.REGISTRY` و`specialists.SPECS`، لا من تصنيف جديد مخترع. قبل تفعيل أي مدرسة، يلزم: بيانات صالحة، اختبار إيجابي وسلبي، lifecycle setup/armed/invalidated/expired، قبول long/short، تقييم زمني بعد التكاليف، وعدد عينات واضح. إذا لم يتوفر الدليل، تظهر `RESEARCH_ONLY` ولا تدخل اللجنة التنفيذية.

## 7. الأخبار والتحليل الأساسي وواجهات API | News, fundamentals and APIs

- **MT5** هو المصدر المرجعي لسعر التنفيذ والحساب والصفقات.  
- **Frankfurter/BLS/World Bank** سياق مرجعي يومي/اقتصادي؛ لا توقيت M1. أرفق observation date وpublished/received time وsource.  
- **Massive** مفيد للبحث/مقارنة التاريخ فقط بحسب خطة وبياناته؛ لا تستبدل به شموع الوسيط أو السبريد. المفتاح غير متوفر في فحص الحزمة السابق.  
- **News/calendar**: مزود واحد موثوق أولاً مع وقت نشر/تعديل ودرجة الأهمية والمنطقة الزمنية؛ انقطاعه يصبح `NEWS_DATA_STALE` لا افتراض “لا خبر”.  
- **LLMs**: تستخدم لتلخيص أدلة غير حساسة أو صياغة تفسير بعد اكتمال القرار. لا تدخل في المسار الحرج للدقيقة، لأنها خارجية ومتقلبة التأخير، ولا تملك تصويتاً نهائياً.  
- لا تضف API لمجرد العدد. لكل موصل: ترخيص، تكلفة وحدود، freshness SLA، health check، اختبارات schema/timezone، وإجراء عند الفشل.

## 8. دور n8n | Appropriate n8n role

استخدم n8n كطبقة تنسيق خارجية اختيارية: جدولة تقرير يومي، إرسال تنبيه بعد رفض/انقطاع، حفظ نتائج دراسة، أو إنشاء مهمة مراجعة. يتلقى بيانات مختصرة عبر webhook موثّق من التطبيق. لا تعط n8n كلمة مرور MT5 أو API يسمح بإرسال أمر، ولا تجعله يعيد المحاولة على عمليات مالية. فشل n8n لا يوقف المحرك ولا يغيّر قراراً.

Use n8n only for optional orchestration: scheduled summaries, outage/rejection notifications, research-result archival, or review tasks. Use an authenticated, minimal webhook payload. Never give n8n MT5 credentials or an order-capable API; never retry financial actions. Its failure must not block or alter the trading engine.

## 9. التعلم والحوكمة | Learning and governance

سجل الإشارة والرفض والقرار والصفقة والإغلاق والتكلفة والنسخ البرمجية لكل مدرسة. اربط نتائج الإغلاق بمعرف المركز، لا بصف الدخول فقط. أنشئ train/validation/test زمنية متتابعة مع embargo ومنع تسريب. قيّم بعد كل التكاليف وعلى أكثر من رمز/حقبة. استعمل bootstrap/تصحيح تعدد المقارنات مع عدد النماذج المجرّبة. التعلم يصدر proposal في sandbox فقط؛ لا يغيّر الأوزان أو الحدود الحية آلياً.

Record signal, veto, decision, fill, close, costs, and code/config version per school. Link exit to broker position ID. Use chronological train/validation/test, embargo, leakage checks, costs, symbols and eras. Apply bootstrap/multiple-testing correction. Learning may produce a sandbox proposal only; no live self-modification.

## 10. خطة تنفيذ مرحلية | Phased implementation plan

| المرحلة | العمل | بوابة القبول |
|---|---|---|
| 0 — خط أساس | حفظ 0.7.16، hash المصدر، أخذ نسخة من بيانات المستخدم، وقياس سبب كل `WAIT/REJECT` | تقرير ثابت بلا أوامر جديدة |
| 1 — العقود | JSON schema موحد للأدلة والرفض والانتهاء، adapters للنماذج الـ58 | 58/58 معرفاً، مدخلات ومخرجات واختبارات قابلة للتتبع |
| 2 — سياق متعدد الأطر | استخدام شموع MT5 الأصلية D1/H4/H1/M15/M1، لا توليد أطر تنفيذ | اختبارات توقيت/اكتمال/no-lookahead وتعارض H4/H1 |
| 3 — committee shadow | تطبيق H4 context → M15 confirm → M1 trigger على replay فقط | comparison paired على نفس الفترات والتكاليف، لا أضعف من baseline خارج العينة |
| 4 — الأخبار وAPI | health/freshness لكل موصل، مصدر/وقت/حدود/فشل | لا بيانات stale تدخل قرار؛ انقطاع موصل لا يوقف خدمة السعر ولا يمرر صفقة |
| 5 — الاختبار الاقتصادي | walk-forward، commissions/spread/slippage، bootstrap وmultiple comparison | نتائج خارج العينة، سجلات كل veto، لا اعتماد عند نقص العينة |
| 6 — n8n اختياري | تنبيه/تقرير فقط من webhook محدود الصلاحيات | اختبار auth وreplay/idempotency، لا صلاحيات تداول |
| 7 — قبول DEMO | نشر مرشح مستقل، QA واجهة، مصالحة، مراجعة يدوية للحدود | تفويض صريح منفصل قبل أي إرسال DEMO؛ تبقى الواجهة READ_ONLY حتى ذلك |

## 11. مؤشرات المنتج | Acceptance metrics

- % قرارات يمكن إعادة بنائها من audit، و% فيها timestamp/نسخة/مصادر كاملة.
- نسبة الشموع الحديثة المكتملة، وأسباب عدم توافر كل إطار.
- معدل اختلاف المدارس حسب العائلة والنظام السوقي، مع correlation-adjusted evidence.
- دقة calibration فقط كمقياس تنبؤ؛ الربحية تقاس منفصلة بعد التكاليف.
- عدد الفرص التي رفضها كل gate، وكم منها كان بسبب quote freshness/spread/session/OOS evidence.
- latency p50/p95 من إغلاق شمعة M1 إلى إصدار proposal؛ لا تدخل LLM أو n8n في هذا المسار.
- tests: model contract + lifecycle + lookahead + accounting + execution fail-closed + browser/RTL/accessibility.

## 12. قرارات يجب عدم استعجالها | Do not rush

لا تغيّر H1 إلى M1 أو تقلّص هدف الدولار أو تخفف spread/OOS veto لكي يزيد عدد الصفقات. هدف 1–3 دولار لكل صفقة لا معنى له قبل تحويل العمولة والسبريد والانزلاق إلى نفس الدولار لكل حجم وحساب. لا يضمن تعدد الوكلاء عدداً أكبر من الصفقات أو الربح. لا يُفعّل التنفيذ إلا بعد التحقق من القفل والهوية والتفويض والحدود والمصالحة، وبشكل منفصل عن تطوير التصميم.

A multi-agent design does not guarantee more trades or profit. Do not weaken cost/OOS vetoes or shrink targets simply to increase trade count. A $1–$3 target must first be compared with broker spread, commission and slippage at the configured lot size. Keep execution separately authorized and fail-closed.

## 13. المراجع | References

- [n8n official docs](https://docs.n8n.io/) — workflow orchestration and integrations; [security audit](https://docs.n8n.io/hosting/securing/security-audit/).
- [Massive forex API docs](https://massive.com/docs/rest/forex/overview) and [current currencies pricing](https://massive.com/pricing?product=currencies).
- Local API connector design: `docs/MULTI_API_RESEARCH_BRIDGE.md`; LLM isolation: `src/nexus/llm_research.py`.
'''

## 6.1 تقسيم الوكلاء المقترح | Proposed school-agent grouping

العدد الفعلي اليوم: 58 مقيّم نموذج محلي، 0 وكيل LLM مستقل يعمل كعضو قرار، ولجنة قرار واحدة في الكود الحالي. الهدف المعماري المقترح ليس تشغيل 58 مكالمة LLM على كل دقيقة؛ بل 58 adapter حتمياً (واحد لكل نموذج) تحت 9 وكلاء عائلات تحليلية، ثم لجنة مركزية. لا يُعتمد أي تجميع إلا بعد مطابقة كل model_id واختبار عقده.

Current count: 58 local model evaluators, zero autonomous LLM decision agents, and one existing decision committee. The target is not 58 per-minute LLM calls: use 58 deterministic adapters under nine school-family agents, then one central committee. Final model-to-family mapping must be audited and tested before use.

| وكيل المدرسة / School agent | نطاقه المقترح / Proposed scope |
|---|---|
| الاتجاه والنظام / Trend & regime | اتجاه H4/H1، الانحدار، حالات السوق، تعارض الاتجاه |
| الهيكل والاختراق / Structure & breakout | قمم/قيعان، نطاقات، اختراق وإعادة اختبار، مستويات مرجعية |
| الشموع والانعكاس / Candles & reversal | أشكال الشموع، رفض سعري، نماذج انعكاس كلاسيكية |
| الزخم / Momentum | ROC/RSI/Stochastic/MACD ونماذج التسارع |
| التقلب والإحصاء / Volatility & statistics | ATR، القنوات، الانحراف/العودة للمتوسط، حدود صلاحية النموذج |
| الهندسة والتوافقي / Harmonic & geometry | Fibonacci، Elliott، نماذج هندسية؛ تُعرض كفرضيات بقواعد تحقق واضحة |
| السيولة والبنية الدقيقة / Liquidity & SMC | sweeps/BOS/FVG/POC؛ advisory ما لم تتوافر بيانات حقيقية مناسبة |
| الحجم / Volume | بيانات حجم تداول حقيقية إن قدمها الوسيط؛ وإلا توضع `tick_volume_proxy` بوضوح ولا تُسمى حجم سوق مركزي |
| الأخبار والأساسيات / News & fundamentals | تقويم وأخبار ومؤشرات اقتصادية مؤرخة؛ تعليق سياقي لا trigger دقيقة |

وكيل البيانات/التكلفة ومدير المخاطر مكوّنان خدميان مستقلان وليسا أصواتاً تحليلية. اللجنة المركزية تربط H4/H1 بالسياق وM15 بالتأكيد وM1 بالمحفز.  
The data/cost service and risk manager are independent gates, not analytical votes. The committee links higher-timeframe context to M15 confirmation and an M1 trigger.
