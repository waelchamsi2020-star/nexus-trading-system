'use strict';
(() => {
  const $ = (id) => document.getElementById(id);
  const token = window.__NEXUS_TOKEN__ || document.querySelector('meta[name="nexus-token"]')?.content || '';
  const titles = {overview:'الرئيسية',markets:'الأسواق والفرص',research:'الأبحاث والشارت',news:'الأخبار والاقتصاد',positions:'الصفقات والأوامر',performance:'الأداء والتغطية',knowledge:'مكتبة المدارس والتعلم',audit:'السجل والأعطال',setup:'الإعداد والاتصال'};
  const labels = {READ_ONLY:'قراءة فقط',MANUAL_DEMO:'تجريبي بموافقة يدوية',AUTO_DEMO:'تجريبي تلقائي',BUY:'شراء',SELL:'بيع',HIGH:'قمة',LOW:'قاع',NEUTRAL:'محايد',WAIT:'انتظار',WAITING:'انتظار',REJECT:'رفض',REJECTED:'مرفوض',READY:'إعداد مكتمل',PARTIAL:'منفذ جزئيًا',IMPLEMENTED:'منفذ',UNIMPLEMENTED:'غير منفذ',DATA_MISSING:'بيانات ناقصة',DATA_INVALID:'بيانات غير صالحة',STALE:'قديم',UNKNOWN:'غير معروف',VALIDATED_OHLC:'شموع مفحوصة',PROPOSED:'مقترح',APPROVED:'معتمد',SENDING:'جارٍ الإرسال',SENT:'أُرسل',ACCEPTED:'مقبول',FILLED:'منفذ',PARTIAL_FILLED:'تنفيذ جزئي',CANCELLED:'ملغى',CANCELED:'ملغى',UNRESOLVED:'نتيجة غير محسومة',UNCERTAIN:'نتيجة غير محسومة',PENDING:'لم يُفحص بعد',ELIGIBLE:'مؤهل',EXCLUDED:'مستبعد',PENDING_APPROVAL:'بانتظار الموافقة',ERROR:'عطل',STOPPED:'متوقف',RUNNING:'نشط',ACTIVE:'نشط',DISCONNECTED:'غير متصل',CONNECTED:'متصل',DEMO:'تجريبي',REAL:'حقيقي — مرفوض',CONTEST:'مسابقة — مرفوض',OPEN:'مفتوح',CLOSED:'مغلق',AVAILABLE:'متاح',UNAVAILABLE:'غير متاح',OK:'سليم',MISSING:'غير متاح',UNTESTED:'غير مختبر',HALTED:'موقوف',TARGET_REACHED:'بلغ الهدف — جارٍ تأكيد الخروج',RISK_LIMIT:'بلغ حد المخاطرة',netting:'مركز موحد لكل رمز',hedging:'مراكز متعددة لكل رمز',FOREX:'فوركس',METALS:'معادن',INDICES:'مؤشرات',ENERGY:'طاقة',STOCKS:'أسهم',CRYPTO:'أصول رقمية',FUTURES:'عقود آجلة',OTHER:'أخرى',forex:'فوركس',metals:'معادن',indices:'مؤشرات',energy:'طاقة',stocks:'أسهم',crypto:'أصول رقمية',futures:'عقود آجلة',other:'أخرى'};
  const phrases = {'wait for a complete entry setup':'انتظار إعداد دخول مكتمل','wait or opposing confirmed setup':'انتظار أو إعداد معاكس مؤكد','100 * met / (met + missing), 0 if no conditions; rule coverage, not win probability':'100 × عدد الشروط المتحققة ÷ مجموع الشروط؛ صفر عند غياب الشروط. تقيس اكتمال القواعد، وليست احتمال نجاح.','broker completed OHLC':'شموع مكتملة من الوسيط','completed close beyond the analysis level':'إغلاق شمعة مكتملة خارج مستوى التحليل','declared rule on the latest completed bar; quote must remain inside zone':'قاعدة معلنة على آخر شمعة مكتملة؛ يجب بقاء السعر داخل المنطقة','structure with 0.1 ATR buffer and >=0.6 ATR risk':'بنية السوق مع هامش تقلب مقداره 0.1، ومسافة مخاطرة لا تقل عن 0.6 من نطاق التقلب','2 * proposed stop distance':'ضعف مسافة الوقف المقترح','insufficient history':'تاريخ أسعار غير كافٍ','last completed bar is stale':'آخر شمعة مكتملة قديمة','zero ATR':'نطاق تقلب صفري','nonzero tradable range':'نطاق أسعار صالح للتداول','signed trades and reliable historical depth/venue data':'صفقات فعلية باتجاه معروف وعمق تاريخي موثوق للسوق','MT5 OHLC/tick counts cannot produce real delta or footprint':'شموع المنصة وعدد تغيرات الأسعار لا ينتجان دلتا أو مخطط بصمة تداول حقيقيين','fresh close through confirmed swing':'إغلاق جديد يتجاوز قمة أو قاعًا مؤكدًا','two confirmed highs and lows':'قمتان وقاعان مؤكدان','confirmed structure':'بنية سوق مؤكدة','body >= 0.5 ATR and engulfing':'شمعة ابتلاعية وجسم لا يقل عن نصف نطاق التقلب','engulfing body':'جسم شمعة ابتلاعية','confirmed level rejection':'رفض سعري عند مستوى مؤكد','touch and close rejection':'ملامسة المستوى ثم إغلاق رافض له','support':'دعم','resistance':'مقاومة','calendar':'تقويم اقتصادي','completed_ohlc':'شموع أسعار مكتملة','multiple years, adjusted contract history and calendar bucket OOS validation':'عدة سنوات وعقود معدلة واختبار موسمية خارج العينة','300 intraday bars cannot establish seasonality':'300 شمعة لحظية لا تكفي لإثبات الموسمية'};
  Object.assign(phrases,{"Completed M15 and H1 trend do not confirm the M1 direction": "اتجاه ربع الساعة والساعة لا يؤكد اتجاه الدخول على الدقيقة", "Higher timeframe trend history missing": "تاريخ الفريمات الأكبر غير كافٍ لتأكيد الاتجاه", "Higher timeframe trend data stale": "بيانات اتجاه الفريمات الأكبر قديمة", "Cash profit changed before management send": "تغير الربح النقدي قبل إرسال أمر الإدارة", "Dollar profit protection requires a USD Demo account": "حماية الربح بالدولار تتطلب حسابًا تجريبيًا بعملة الدولار"});
  Object.assign(labels,{"FAST_CASH_BROKER_TP": "هدف جني الدولار لدى الوسيط", "FAST_CASH_TARGET": "جني الربح عند دولار واحد", "FAST_CASH_PROTECT_FALLBACK": "جني الربح لتعذر تثبيت الحماية", "FAST_CASH_PROTECTION": "حماية ربح الدولار بوقف الوسيط"});
  Object.assign(labels,{ENTRIES_STOPPED:'الدخول الجديد متوقف',DATA_ERROR:'تعذر التحقق من البيانات',DISABLED:'غير مفعل',INSUFFICIENT:'عينة غير كافية',INELIGIBLE:'غير مؤهل',QUALIFIED_DEMO_RESEARCH:'مؤهل للبحث التجريبي',UNKNOWN_RESULT:'نتيجة غير محسومة',RESULT_UNCERTAIN:'نتيجة غير محسومة'});
  Object.assign(labels,{COMMITTEE_DECISION:'قرار لجنة الأبحاث',CONNECTED_READ_ONLY:'اتصال للقراءة فقط',AUTHORIZATION_REVOKED:'إلغاء تفويض التنفيذ',ACTION_REJECTED:'إجراء مرفوض',ANALYSIS_ERROR:'تعذر تحليل الرمز',ORDER_SENT:'أُرسل أمر إلى الوسيط',ORDER_FILLED:'تنفيذ مؤكد لدى الوسيط',INTENT_CREATED:'إنشاء نية تداول',RISK_REJECTED:'رفض محرك المخاطر',RECONCILIATION:'مطابقة العمليات مع الوسيط'});
  Object.assign(labels,{FRESH:'حديث بحسب وقت النشر',SOURCE_STALE:'المصدر قديم أو غير متاح'});
  Object.assign(phrases,{
    'Broker confirmation pending; request will not be resent':'بانتظار تأكيد الوسيط؛ لن يُعاد إرسال الطلب',
    'Broker result remains unresolved':'نتيجة الوسيط لم تُحسم؛ يلزم المطابقة وإعادة التفعيل',
    'Filled position is absent without confirmed exit':'المركز المنفذ غير ظاهر ولم يتأكد خروجه بعد'
  });
  Object.assign(labels,{'Darvas Box':'صندوق دارفاس','VWAP وAnchored VWAP':'متوسط السعر المرجح بالحجم والمرساة','SMC وICT والسيولة':'مفاهيم الأموال الذكية والسيولة','SMT':'اختلاف السيولة بين الأصول',nt:'ويندوز','NEXUS-SYNTHETIC':'Quant Trading AI — محاكاة محلية','Federal Reserve':'الاحتياطي الفيدرالي','European Central Bank':'البنك المركزي الأوروبي','Bureau of Labor Statistics':'مكتب إحصاءات العمل','Bank of England':'بنك إنجلترا','MT5 Economic Calendar':'التقويم الاقتصادي للمنصة',double_top:'نموذج القمتين',double_bottom:'نموذج القاعين',head_and_shoulders:'نموذج الرأس والكتفين',inverse_head_and_shoulders:'نموذج الرأس والكتفين المعكوس',symmetrical_triangle:'مثلث متماثل',ascending_triangle:'مثلث صاعد',descending_triangle:'مثلث هابط',reversal_pattern:'نموذج انعكاسي',reversal_pattern_scan:'فحص نماذج انعكاسية',geometric_pattern:'نموذج هندسي'});
  Object.assign(labels,{dow_structure:'داو والتحليل الكلاسيكي',engulfing:'حركة السعر والشموع',support_bounce:'الدعم والمقاومة',classic_reversal_patterns:'الأنماط الانعكاسية الكلاسيكية',geometric_triangle_breakout:'الأنماط الهندسية',breakout_retest:'الاختراق وإعادة الاختبار',darvas_box:'صندوق دارفاس',ichimoku_cross:'إيشيموكو',fib_retracement:'فيبوناتشي',ema_cross:'اتباع الاتجاه',rsi_rebound:'مؤشرات الزخم',volatility_breakout:'مؤشرات التقلب',zscore_reversion:'العودة إلى المتوسط والتحليل الإحصائي',vwap_reclaim:'متوسط السعر المرجح بالحجم والمرساة',interasset_confirmation:'العلاقات بين الأصول',harmonic_abcd:'الهارمونيك',elliott_candidate:'موجات إليوت',wyckoff_spring:'وايكوف',smc_ict_proxy:'مفاهيم الأموال الذكية والسيولة',supply_demand_proxy:'العرض والطلب',smt_proxy:'اختلاف السيولة بين الأصول',seasonality:'الموسمية',gann:'جان ومربع التسعة والدورات الزمنية',order_flow:'تدفق الأوامر',QUANT_COMPLETED:'اكتمل التحقق الكمي',AUTHORIZATION_ACTIVATED:'فُعّل التفويض',DAILY_SETTINGS:'إعدادات اليوم',CONNECTION_RESTORED_READ_ONLY:'عاد الاتصال بوضع القراءة فقط'});
  Object.assign(labels,{bar_real_volume_or_labeled_tick_proxy:'حجم تداول حقيقي للشمعة أو مؤشر تغيرات معلّم بوضوح',explicit_anchor:'مرساة زمنية صريحة',aligned_partner_ohlc:'شموع متزامنة للأصل المقارن',multi_year_adjusted_history:'تاريخ معدل لعدة سنوات',signed_trades:'صفقات محددة الاتجاه',historical_depth:'عمق سوق تاريخي'});
  Object.assign(phrases,{'Ambiguous equal-endpoint session':'مدة الجلسة غامضة: وقت البداية والنهاية متساويان دون فرق يوم؛ الدخول ممنوع حتى التحقق','Broker session schedule':'جدول جلسات الوسيط','No trade session returned':'لم تُرجع المنصة جلسة تداول لهذا الرمز','Permanent Demo-only guard: Real, Contest and unknown accounts are refused':'حظر دائم: الحساب الحقيقي وحساب المسابقة والنوع غير المعروف مرفوضة؛ الحساب التجريبي فقط','READ_ONLY: explicit Demo activation is required':'وضع القراءة فقط؛ يلزم تفعيل صريح للحساب التجريبي','Terminal disconnected or trading/API disabled':'المنصة غير متصلة أو صلاحية التداول أو واجهة التداول البرمجية معطلة','Account trading/expert permission disabled':'صلاحية التداول أو المستشارين معطلة في الحساب','Account, server or terminal changed':'تغير الحساب أو الخادم أو المنصة؛ التفويض السابق غير صالح','Account changed since activation':'تغير الحساب منذ التفعيل','UTC day changed; explicit activation is required':'بدأ يوم عالمي جديد؛ يلزم تفعيل صريح لحدود اليوم','Authorized risk settings changed':'تغيرت إعدادات المخاطرة المفوضة','Unresolved broker result blocks every send':'نتيجة وسيط غير محسومة تمنع كل إرسال جديد','New entries are stopped':'الدخول الجديد متوقف','Activation requested':'جارٍ التحقق من طلب التفعيل الجديد','Broker reconciliation is incomplete; activation refused':'مطابقة العمليات مع الوسيط غير مكتملة؛ التفعيل مرفوض','Only the authorized Demo account is eligible':'الحساب التجريبي المفوض وحده مؤهل للتنفيذ','Market session unknown or closed':'جلسة السوق غير متحققة أو مغلقة','Market session data is stale':'بيانات جلسة السوق قديمة','Economic calendar coverage unknown':'تغطية التقويم الاقتصادي غير متحققة','Economic calendar is stale':'التقويم الاقتصادي قديم','Calendar currency coverage is incomplete for this contract':'تغطية عملات التقويم ناقصة لهذا العقد','Economic calendar does not cover current time':'التقويم الاقتصادي لا يغطي الوقت الحالي','High-impact economic event blackout':'حظر تداول حول حدث اقتصادي مرتفع الأهمية','Tick is stale or from the future':'آخر سعر قديم أو يحمل توقيتًا مستقبليًا','Fresh quote is outside the qualified entry zone':'السعر الحديث خارج منطقة الدخول المؤهلة','Unbounded external or unstopped account exposure':'تعرض خارجي أو مركز دون وقف يضيف مخاطرة حساب غير محدودة','Daily target/loss policy has stopped entry':'سياسة الهدف أو الخسارة اليومية أوقفت الدخول','Minimum broker lot exceeds risk or margin budget':'أقل لوت يسمح به الوسيط يتجاوز المخاطرة أو الهامش المتاح','Final contract risk exceeds permitted budget':'مخاطرة العقد النهائية تتجاوز الميزانية المسموحة','Ambiguous broker result':'نتيجة الوسيط غير محسومة','Ambiguous broker result; reconciliation and reactivation required':'نتيجة الوسيط غير محسومة؛ يلزم المطابقة ثم إعادة التفعيل','Position ownership is not proven':'ملكية المركز للمنظومة غير مثبتة؛ إدارته مرفوضة','External trades are mixed into the netting position':'صفقات خارجية مختلطة في المركز الموحد؛ إدارة المركز مرفوضة'});
  Object.assign(phrases,{'M1 directional evidence has no clear advantage':'أدلة الدقيقة لا ترجح اتجاهًا بوضوح'});
  Object.assign(phrases,{'no fresh completed and triggered entry setup':'لا يوجد إعداد دخول مكتمل حديث تحققت شروطه','required news/calendar coverage missing, stale, or in event blackout':'مصدر الأخبار أو التقويم المطلوب ناقص أو قديم، أو الحدث في فترة الحظر','strategy lacks eligible chronological cost-adjusted broker OOS evidence':'تفتقر الاستراتيجية إلى اختبار مؤهل ببيانات الوسيط خارج العينة وبعد التكاليف','quant evidence version, instrument or timeframe mismatch':'اختلاف إصدار القواعد أو الرمز أو الفريم عن الاختبار الكمي','simulation evidence cannot qualify broker proposal':'نتيجة المحاكاة لا تؤهل اقتراحًا للتنفيذ لدى الوسيط','timeframes disagree':'تعارض بين الفريمات','triggered schools disagree':'تعارض بين المدارس ذات الإعداد المكتمل','fewer than two distinct evidence families after dependency grouping':'أقل من عائلتي أدلة مختلفتين بعد تجميع الأدلة المترابطة','need corroborating evidence on at least two completed timeframes':'يلزم دليل مؤيد من فريمين مكتملين على الأقل','missing or invalid execution prices':'أسعار التنفيذ مفقودة أو غير صالحة','execution stop and target must bracket entry':'يجب أن يكون الوقف والهدف على جانبي الدخول الصحيحين','market eligibility, session or freshness failed':'فشل فحص أهلية السوق أو الجلسة أو حداثة البيانات','spread exceeds 20 percent of proposed stop distance':'فرق السعر يتجاوز 20% من مسافة الوقف المقترح','current quote outside approved entry zone':'السعر الحالي خارج منطقة الدخول المعتمدة','triggered entry; distinct evidence families and timeframe agreement; required news and fixed OOS gates passed':'تحقق شرط الدخول مع عائلات أدلة مختلفة واتفاق الفريمات، واجتازت تغطية الأخبار والاختبارات الكمية حدود القبول الثابتة','FULL':'خروج كامل','completed_bar_close':'إغلاق شمعة مكتملة','Explicit Demo activation is required':'يلزم تفعيل صريح للحساب التجريبي','User stopped new entries':'أوقف المستخدم الدخول الجديد','Daily policy stopped new entries':'سياسة اليوم أوقفت الدخول الجديد','Demo authorization activated':'اعتمد تفويض الحساب التجريبي','User deactivated trading':'ألغى المستخدم تفويض التداول'});
  Object.assign(phrases,{'00:00 UTC / 04:00 Asia/Dubai':'00:00 بالتوقيت العالمي / 04:00 بتوقيت دبي'});
  Object.assign(labels,{"fvg_first_return": "العودة الأولى للفجوة السعرية", "base_first_return": "العودة الأولى لمنطقة الأساس", "donchian_20": "اختراق قناة عشرين شمعة", "failed_range_break": "فشل اختراق النطاق", "pin_rejection": "رفض الذيل عند حد سعري", "inside_bar_break": "اختراق الشمعة الداخلية", "band_reentry": "العودة داخل النطاق الإحصائي", "atr_channel_break": "اختراق قناة التقلب", "momentum_acceleration": "تسارع الزخم السعري", "utc_opening_range": "اختراق نطاق بداية اليوم العالمي", "regression_reentry": "عودة إلى قناة الانحدار"});
  Object.assign(labels,{TREND:'اتجاه',RANGE:'نطاق',MIXED:'مختلط',HIGH_VOLATILITY:'تقلب مرتفع'});
  Object.assign(labels,{"tick_activity_rejection": "رفض سعري مع نشاط التكات التقريبي", "positive_tick_volume": "عدد تكات موجب"});
  Object.assign(labels,{"interasset_confirmation": "تأكيد أصل مقابل محدد", "smt_proxy": "اختلاف نطاق أصلين: نموذج محلي", "elliott_candidate": "إليوت: فرضية موجتين محلية", "wyckoff_spring": "وايكوف: نموذج كسر واختبار محلي", "smc_ict_proxy": "السيولة: سحب مستوى وعودة فجوة", "supply_demand_proxy": "العرض والطلب: عودة منطقة محلية", "gann": "جان: شبكة جذر سعر معيارية", "order_flow": "تدفق النشاط: تقريب من شموع التكات", "seasonality": "موسمية العملات: نموذج شهري محلي"});
  Object.assign(labels,{explicit_partner_symbol:'أصل مقابل محدد',broker_daily_history:'تاريخ يومي من الوسيط'});
  let state = {}, hasState = false, busy = false, currentView = 'overview', unit = 'money', selectedSymbol = '', lastRender = '', lastPollError = '', chartBars = [], chartGeometry = null;
  let executionFormRestored = false, executionFormDirty = false, executionFormStamp = '';
  Object.assign(labels,{CONFIRMED:'متوافق',CONTEXT:'سياق مفحوص',CONFLICT:'متعارض',NOT_EVALUATED:'لم يُفحص',LONG:'شراء',SHORT:'بيع',EVALUATED_NEUTRAL:'حياد مفحوص',CONTEXT_CONFIRMED:'سياق متوافق',four_school_confluence:'تقاطع المدارس الأربع'});
  Object.assign(labels,{EXPIRED:'منتهي الصلاحية'});
  Object.assign(labels,{BROKER_EXIT_CONFIRMATION_WAIT:'انتظار تأكيد إغلاق الوسيط',BROKER_EXIT_CONFIRMATION_RESULT:'نتيجة مطابقة إغلاق الوسيط'});
  Object.assign(labels,{'Four-school historical qualification is unavailable; choose forward_demo':'التأهيل التاريخي لبروتوكول المدارس الأربع غير متاح؛ اختر الاختبار الأمامي على الحساب التجريبي.'});
  let pollTimer = null, pollPromise = null, pollingEnabled = false;
  const headerElement = document.querySelector('.topbar');
  if (headerElement) {
    const measureHeader = () => document.documentElement.style.setProperty('--header-height',`${Math.ceil(headerElement.getBoundingClientRect().height)}px`);
    if (window.ResizeObserver) new window.ResizeObserver(measureHeader).observe(headerElement);
    window.addEventListener('resize',measureHeader);
    measureHeader();
  }
  const prefsKey = 'nexus.preferences.v1';
  let prefs = {};
  try { prefs = JSON.parse(localStorage.getItem(prefsKey) || '{}') || {}; } catch (_) {}
  const language = () => prefs.language === 'en' ? 'en' : 'ar';
  const isEnglish = () => language() === 'en';
  const uiText = (value) => window.NEXUS_I18N?.translate(value,language()) ?? value;
  const applyI18n = () => window.NEXUS_I18N?.apply(document,language());
  const h = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const arr = (v) => Array.isArray(v) ? v : [];
  const obj = (v) => v && typeof v === 'object' && !Array.isArray(v) ? v : {};
  const first = (...v) => v.find((x) => x !== undefined && x !== null);
  const finite = (v) => typeof v === 'number' && Number.isFinite(v);
  const num = (v, digits = 2) => finite(v) ? new Intl.NumberFormat(isEnglish() ? 'en-GB' : 'ar-AE-u-nu-latn',{maximumFractionDigits:digits,minimumFractionDigits:digits === 2 ? 2 : 0}).format(v) : '—';
  const tr = (v) => {
    if (v === undefined || v === null || v === '') return '—';
    if (typeof v !== 'string') return String(v);
    if (isEnglish()) {
      if (phrases[v]) return v;
      if (labels[v]) return uiText(labels[v]);
      const bilingual = v.match(/^[\u0600-\u06ff][^()]*\(([^()]*[A-Za-z][^()]*)\)\s*$/);
      if (bilingual) return bilingual[1].trim();
      if (/[\u0600-\u06ff]/.test(v)) return uiText(v);
      return v;
    }
    if (labels[v] || phrases[v]) return labels[v] || phrases[v];
    const scenario = v.match(/^(BUY|SELL) only after the declared completed-bar trigger$/);
    if (scenario) return `${tr(scenario[1])} فقط بعد تحقق شرط معلن على شمعة مكتملة`;
    const need = v.match(/^need (\d+) completed bars, have (\d+)$/);
    if (need) return `يلزم ${need[1]} شمعة مكتملة؛ المتاح ${need[2]}`;
    return /[\u0600-\u06ff]/.test(v) ? v.replace(/\s*\([^()]*[A-Za-z][^()]*\)\s*$/,'').trim() : v;
  };
  const plain = (v) => { if (v === undefined || v === null || v === '') return '—'; if (typeof v === 'boolean') return v ? (isEnglish() ? 'Yes' : 'نعم') : (isEnglish() ? 'No' : 'لا'); if (typeof v === 'object') return Array.isArray(v) ? v.map(plain).join(isEnglish() ? ', ' : '، ') : Object.entries(v).map(([k,x]) => `${uiText(extraFieldLabels[k] || fieldLabel(k))}: ${plain(x)}`).join(' · '); return tr(v); };
  // The exported report keeps its stable English schema. The on-screen copy
  // localizes schema keys too, so Arabic mode does not become snake_case text.
  // Field labels for explicit theory evidence are installed after declaration.
  const diagnosticFieldLabels={
    mode:['الوضع','Mode'],account_key:['هوية الحساب','Account identity'],day:['اليوم','Day'],settings:['الإعدادات','Settings'],
    daily_risk:['المخاطرة اليومية','Daily risk'],daily_target:['الهدف اليومي','Daily target'],risk_unit:['وحدة المخاطرة','Risk unit'],target_unit:['وحدة الهدف','Target unit'],
    commission_per_lot:['العمولة لكل لوت','Commission per lot'],slippage_points:['احتياطي الانزلاق بالنقاط','Slippage allowance in points'],
    max_trade_fraction:['الحد الأقصى لنسبة الصفقة','Maximum trade fraction'],correlation_cap_fraction:['حد الارتباط','Correlation cap'],
    max_proposal_age:['أقصى عمر للاقتراح','Maximum proposal age'],max_session_age:['أقصى عمر لبيانات الجلسة','Maximum session-data age'],
    max_calendar_age:['أقصى عمر للتقويم','Maximum calendar age'],max_tick_age:['أقصى عمر للسعر','Maximum quote age'],margin_fraction:['نسبة الهامش','Margin fraction'],
    risk_amount:['قيمة المخاطرة','Risk amount'],target_amount:['قيمة الهدف','Target amount'],reason:['السبب','Reason'],reasons:['الأسباب','Reasons'],
    action:['الإجراء','Action'],strategy_id:['الاستراتيجية','Strategy'],symbol:['الرمز','Symbol'],timeframe:['الفريم','Timeframe'],qualified:['مؤهل','Qualified'],
    status:['الحالة','Status'],metrics:['المقاييس','Metrics'],trades:['الصفقات','Trades'],wins:['الصفقات الرابحة','Winning trades'],losses:['الصفقات الخاسرة','Losing trades'],
    sample_win_fraction:['نسبة الفوز في العينة','Sample win fraction'],profit_factor:['معامل الربح','Profit factor'],net_r:['الصافي بوحدة المخاطرة','Net R'],
    expectancy_r:['العائد المتوقع بوحدة المخاطرة','Expectancy R'],max_drawdown_r:['أقصى تراجع بوحدة المخاطرة','Maximum drawdown R'],
    gross_profit_r:['إجمالي الربح بوحدة المخاطرة','Gross profit R'],gross_loss_r:['إجمالي الخسارة بوحدة المخاطرة','Gross loss R'],
    ambiguous_stop_first_trades:['صفقات غامضة احتُسب فيها الوقف أولًا','Ambiguous stop-first trades'],net_price_units:['الصافي بوحدات السعر','Net price units'],
    metric_limit:['حدود المقياس','Metric limit'],decision:['القرار','Decision'],ranked:['الترتيب','Ranking'],card_id:['معرف البطاقة','Card ID'],side:['الاتجاه','Side'],
    score:['الدرجة','Score'],evidence_families:['عائلات الأدلة','Evidence families'],price_structure:['بنية السعر','Price structure'],price_transform:['تحويل السعر','Price transform'],
    volume_weighted:['مرجح بالحجم','Volume weighted'],supporting:['الأدلة المؤيدة','Supporting evidence'],opposing:['الأدلة المعارضة','Opposing evidence'],
    reason_codes:['رموز الأسباب','Reason codes'],eligible:['مؤهل','Eligible'],simulation:['محاكاة','Simulation'],trade_mode:['نمط الحساب','Account mode'],
    at:['التوقيت','Time'],settings_digest:['بصمة الإعدادات','Settings fingerprint'],intent_id:['هوية نية التداول','Trade intent ID'],risk:['المخاطرة','Risk'],
    request:['الطلب','Request'],result:['النتيجة','Result'],error:['العطل','Error'],message:['التفسير','Message'],entry:['الدخول','Entry'],stop:['الوقف','Stop'],
    targets:['الأهداف','Targets'],volume:['الحجم','Volume'],price:['السعر','Price'],sl:['وقف التنفيذ','Stop loss'],tp:['الهدف','Take profit'],
    order:['رقم الأمر','Order ticket'],deal:['رقم الصفقة','Deal ticket'],position:['رقم المركز','Position ticket'],comment:['التعليق','Comment'],
    account:['الحساب','Account'],terminal:['المنصة','Terminal'],connected:['متصل','Connected'],trade_allowed:['التداول مسموح','Trading allowed'],
    tradeapi_disabled:['واجهة التداول معطلة','Trading API disabled'],entries_paused:['الدخول متوقف','Entries paused'],authorization:['التفويض','Authorization']
  };
  const diagnosticKey = (key,index) => {
    const pair=diagnosticFieldLabels[key];
    if (pair) return pair[isEnglish()?1:0];
    const known=fieldLabel(key);
    if (known!==key) return known;
    return isEnglish()?String(key).replaceAll('_',' '):`تفصيل تقني ${index+1}`;
  };
  const localizedData = (v) => {
    if (typeof v === 'string') return tr(v);
    if (Array.isArray(v)) return v.map(localizedData);
    if (v && typeof v === 'object') return Object.fromEntries(Object.entries(v).map(([k,x],index) => [diagnosticKey(k,index),localizedData(x)]));
    return v;
  };
  const extraFieldLabels={political:'أحداث سياسية شاملة',breaking_news:'أخبار عاجلة شاملة',note:'ملاحظة',calendar:'تقويم اقتصادي',official_feeds:'مصادر رسمية',memory_gb:'الذاكرة بالغيغابايت',cpu_count:'عدد الأنوية',model:'النموذج',available:'متاح',ok:'سليم',known:'متحقق',connected:'متصل',estimated_exit_cost:'احتياطي تكلفة الإغلاق',realized_net:'المحقق الصافي',net_pnl:'الصافي',external_exposure:'تعرض خارجي',os:'نظام التشغيل',logical_cpus:'أنوية منطقية',local_language_model:'النموذج المحلي',total_memory_gb:'إجمالي الذاكرة بالغيغابايت',available_memory_gb:'الذاكرة المتاحة بالغيغابايت'};
  Object.assign(extraFieldLabels,{"tick_count": "عدد التكات", "baseline": "القيمة المرجعية", "activity_ratio": "نسبة النشاط", "close_location": "موقع الإغلاق", "pressure_proxy": "مؤشر ضغط تقريبي"});
  Object.assign(extraFieldLabels,{"retracement": "نسبة التصحيح", "equality": "نسبة تشابه الضلعين", "projection": "نسبة الامتداد", "candidates": "الترقيمات المرشحة", "valid_counts": "الترقيمات الهندسية الصالحة", "rules": "القواعد", "geometry_valid": "الهندسة مطابقة", "nested_structure_verified": "الدرجات المتداخلة مفحوصة", "wave2_above_origin": "الموجة الثانية لا تتجاوز البداية", "wave3_beyond_wave1": "الموجة الثالثة تتجاوز الأولى", "wave4_no_overlap": "الرابعة لا تتداخل مع الأولى", "wave3_not_shortest": "الثالثة ليست الأقصر", "nontruncated_wave5": "الخامسة تتجاوز الثالثة", "first_touch": "الملامسة الأولى", "formation_time": "وقت تكوّن المنطقة", "lower_wick": "الذيل السفلي", "upper_wick": "الذيل العلوي", "deviation": "الانحراف", "slope": "الميل", "scale": "مقياس التقلب"});
  const account = () => obj(state.account);
  const currency = () => account().currency || '';
  const money = (v) => finite(v) ? `${num(v)}${currency() ? ` ${currency()}` : ''}` : '—';
  Object.assign(labels,{"classic_pivot_reclaim": "استعادة النقطة المحورية اليومية", "fractal_5_breakout": "اختراق فراكتال خماسي مؤكد", "obv_divergence_reclaim": "اختلاف OBV التقريبي واستعادة المستوى", "completed_mt5_daily_ohlc": "شموع يومية مكتملة من منصة التداول"});
  Object.assign(labels,{"elliott_impulse_reversal": "إليوت: عودة بعد هندسة خمس موجات", "elliott_zigzag_reversal": "إليوت: عودة بعد هندسة زجزاج"});
  const schoolName = (v) => {
    const meta=arr(state.coverage).find(row=>[row.id,row.school,row.strategy].includes(v));
    if(meta)return isEnglish()?first(obj(obj(meta.contract).definition).name_en,tr(meta.school)):meta.school;
    return tr(first(labels[v],v,'مدرسة غير مسماة'));
  };
  const date = (v, withDate = true) => {
    if (v === undefined || v === null || v === '') return '—';
    const d = new Date(typeof v === 'number' ? (v < 1e12 ? v * 1000 : v) : v);
    if (Number.isNaN(d.getTime())) return tr(v);
    return new Intl.DateTimeFormat(isEnglish() ? 'en-GB' : 'ar-AE-u-nu-latn',{timeZone:'Asia/Dubai',...(withDate ? {month:'short',day:'numeric'} : {}),hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}).format(d);
  };
  const set = (id, v) => { if ($(id)) $(id).textContent = uiText(v ?? '—'); };
  const empty = (title, note = '') => `<div class="empty"><span>${h(uiText(title))}</span>${note ? `<small>${h(uiText(note))}</small>` : ''}</div>`;
  const cls = (v) => ['READY','IMPLEMENTED','CONNECTED','APPROVED','FILLED','BUY','OK','AVAILABLE','ACTIVE','RUNNING'].includes(v) ? 'green' : ['REJECT','REJECTED','ERROR','DATA_INVALID','REAL','CONTEST','DISCONNECTED','RISK_LIMIT'].includes(v) ? 'red' : ['PARTIAL','STALE','UNRESOLVED','UNCERTAIN','UNIMPLEMENTED','DATA_MISSING','UNKNOWN'].includes(v) ? 'amber' : '';
  const badge = (v) => `<span class="mini-pill ${cls(v)}">${h(tr(v))}</span>`;
  function fieldLabel(k) { return uiText({price:'السعر',zone:'المنطقة',trigger:'شرط الدخول',triggered:'تحقق الشرط',time:'التوقيت',signal_bar_time:'شمعة الإشارة',condition:'شرط الإبطال',evaluation:'طريقة التقييم',method:'طريقة الاشتقاق',fraction:'النسبة',kind:'نوع الدليل',label:'الدليل',value:'القيمة',index:'رقم الشمعة',confirmed_at:'تأكيد المستوى',ratio:'النسبة',coverage:'التغطية',reason:'السبب',message:'التفسير',take_profit:'جني الربح',max_hold_bars:'الحد الأقصى لشموع الاحتفاظ',timeframe:'الفريم',partial_targets:'أهداف جزئية',break_even_at_r:'حماية الربح عند',allow_addition:'السماح بالإضافة',stop_may_only_tighten:'الوقف لا يتسع',invalidation:'إبطال السيناريو',status:'الحالة',source:'المصدر',id:'الهوية',symbol:'الرمز',side:'الاتجاه',volume:'الحجم',sl:'وقف التنفيذ',tp:'الهدف',profit:'الربح',swap:'التبييت',commission:'العمولة',fee:'الرسوم',magic:'ملكية المنظومة',comment:'التعليق',ticket:'رقم الوسيط',expected:'المتوقع',actual:'الفعلي',previous:'السابق',revised:'المراجع',name:'اسم النموذج',pattern:'نوع النموذج',confirmed_swings:'نقاط الانقلاب المؤكدة',neckline_previous:'خط العنق السابق',neckline_now:'خط العنق الحالي',target:'الهدف المحسوب',height:'ارتفاع النموذج',tolerance:'هامش التطابق',shoulder_difference:'فرق الكتفين',last_pivot_confirmed_at:'آخر تأكيد لنقطة انقلاب',latest_pivot_confirmed_at:'آخر تأكيد لنقطة انقلاب',upper_slope_per_bar:'ميل الحد العلوي لكل شمعة',lower_slope_per_bar:'ميل الحد السفلي لكل شمعة',upper_residual:'خطأ ملاءمة الحد العلوي',lower_residual:'خطأ ملاءمة الحد السفلي',initial_height:'الارتفاع الأولي',current_height:'الارتفاع الحالي',upper_now:'الحد العلوي الحالي',lower_now:'الحد السفلي الحالي',prior_closes_inside:'الإغلاقات السابقة داخل النموذج'}[k] || k); }
  function savePrefs() { try {localStorage.setItem(prefsKey, JSON.stringify(prefs));} catch (_) {} }
  function toast(message, error = false) { const node = document.createElement('div'); node.className = `toast${error ? ' error' : ''}`; node.textContent = uiText(tr(message)); $('toast-region').appendChild(node); setTimeout(() => node.remove(), 6500); }
  let confirmationActive=false;
  async function confirm(title, message, accept = 'تأكيد', dangerous = false) {
    const dialog = $('confirm-dialog');
    if (confirmationActive) return false;
    set('confirm-title',title); set('confirm-text',message); set('confirm-accept',accept); $('confirm-accept').className = `button ${dangerous ? 'danger' : 'primary'}`;
    if (!dialog.showModal) return window.confirm(`${title}\n\n${message}`);
    confirmationActive=true;
    return new Promise((resolve) => {
      const finish=(value)=>{dialog.removeEventListener('close',closed);dialog.removeEventListener('cancel',cancelled);dialog.removeEventListener('keydown',trap);confirmationActive=false;resolve(value);};
      // A queued close event from Escape must not settle a newly reopened dialog.
      const closed=()=>{if(!dialog.open)finish(dialog.returnValue==='confirm');};
      const cancelled=()=>finish(false);
      const trap=(event)=>{
        if(event.key!=='Tab')return;
        const controls=Array.from(dialog.querySelectorAll('button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex="0"]')).filter(e=>e.getClientRects().length);
        if(!controls.length)return;
        const first=controls[0],last=controls[controls.length-1];
        if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
        else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
      };
      dialog.addEventListener('close',closed);dialog.addEventListener('cancel',cancelled);dialog.addEventListener('keydown',trap);
      dialog.returnValue='';dialog.showModal();
    });
  }

  async function api(path, options = {}) {
    const controller = new AbortController(); const timeout = setTimeout(() => controller.abort(), 25000);
    try {
      const response = await fetch(path,{cache:'no-store',credentials:'same-origin',...options,signal:controller.signal,headers:{'X-Nexus-Token':token,...(options.body ? {'Content-Type':'application/json'} : {}),...options.headers}});
      const contentType = response.headers.get('content-type') || '';
      if (!contentType.includes('application/json')) throw new Error('الخدمة لم تُرجع بيانات صالحة. أعد تشغيل Quant Trading AI من ملف التشغيل.');
      const result = await response.json();
      if (!response.ok || result.ok === false) throw new Error(tr(first(result.error,result.message,`رفضت الخدمة الطلب (${response.status}).`)));
      return result;
    } catch (err) { if (err.name === 'AbortError') throw new Error('انتهت مهلة الاتصال. قد تكون العملية أُرسلت؛ راجع سجل التنفيذ قبل أي محاولة جديدة.'); throw err; }
    finally { clearTimeout(timeout); }
  }
  async function action(name, payload = {}, success = '') {
    if (busy) return null;
    busy = true; updateControls();
    try {
      let result = await api('/api/action',{method:'POST',body:JSON.stringify({action:name,...payload})});
      if (result.queued) {
        if (!/^[0-9a-f]{32}$/.test(result.request_id||'')) throw new Error(uiText('الطلب قيد التنفيذ ولم تصل هوية متابعته؛ راجع السجل قبل إعادة الإرسال.'));
        toast(uiText('الطلب في قائمة العمل؛ ننتظر النتيجة الفعلية دون إعادة إرساله.'));
        const deadline=Date.now()+90000;
        let completed=false;
        while(Date.now()<deadline) {
          await new Promise(resolve=>setTimeout(resolve,400));
          const receipt=await api(`/api/action-result?id=${encodeURIComponent(result.request_id)}`);
          if(receipt.status==='PENDING')continue;
          if(receipt.status!=='COMPLETE'||!receipt.result||typeof receipt.result!=='object')throw new Error(uiText('تعذر التحقق من نتيجة الطلب؛ راجع السجل قبل إعادة الإرسال.'));
          result=receipt.result;
          if(result.ok===false)throw new Error(tr(first(result.error,result.message,'تعذر تنفيذ الإجراء.')));
          completed=true;break;
        }
        if(!completed)throw new Error(uiText('لم تنته العملية ضمن مهلة المتابعة؛ قد تكتمل لاحقًا. راجع السجل قبل إعادة الإرسال.'));
      }
      if (result.state) { state = result.state; hasState = true; render(); }
      else await poll(false);
      // The caller supplies a reviewed, localized UI success message. Backend
      // messages remain useful in diagnostics but must not override it and
      // reintroduce the source language after the user selected English.
      if (success || result.message) toast(tr(success || result.message));
      return result;
    } catch (err) { toast(err.message || 'تعذر تنفيذ الإجراء.',true); await poll(false); return null; }
    finally { busy = false; updateControls(); }
  }
  function poll(schedule = true) {
    // Recurring intent belongs to the polling loop, not to the request that
    // happens to own this refresh. An overlapping manual refresh must not
    // consume the scheduled callback and permanently stop updates.
    if (schedule) pollingEnabled = true;
    if (pollPromise) return pollPromise;
    clearTimeout(pollTimer); pollTimer = null;
    pollPromise = (async () => {
      try {
        const result = await api('/api/state'); state = result.state || result; hasState = true; lastPollError = ''; $('service-error').hidden = true;
        const stamp = JSON.stringify(state);
        if (stamp !== lastRender) {lastRender = stamp; render();} else updateConnection();
      } catch (err) {lastPollError = err.message || 'تعذر الوصول إلى الخدمة المحلية.'; set('service-error',lastPollError); $('service-error').hidden = false; updateConnection(); updateControls();}
      finally {
        pollPromise = null;
        if (pollingEnabled) pollTimer = setTimeout(() => pollingEnabled ? poll() : undefined,lastPollError ? 6000 : 2500);
      }
    })();
    return pollPromise;
  }
  function go(view) {
    if (!titles[view]) view = 'overview'; currentView = view;
    document.querySelectorAll('.view').forEach((x) => x.classList.toggle('active',x.id === `view-${view}`));
    document.querySelectorAll('.nav-item[data-view]').forEach((x) => {
      const active=x.dataset.view === view;
      x.classList.toggle('active',active);
      if(active)x.setAttribute('aria-current','page');else x.removeAttribute('aria-current');
    });
    const more=$('nav-more');
    if(more)more.open=['news','knowledge','audit'].includes(view);
    set('view-title',uiText(titles[view])); document.querySelector('.shell').classList.remove('menu-open');
    if (location.hash !== `#${view}`) history.replaceState(null,'',`#${view}`);
    if (view === 'research') requestAnimationFrame(drawChart);
    if (hasState) render();
  }
  function updateConnection() {
    const connected = hasState && !lastPollError && first(account().connected,obj(state.terminal).connected,!!account().login);
    const pill = $('connection-pill'); const label = lastPollError ? 'الخدمة المحلية غير متاحة' : connected ? (state.simulation ? 'محاكاة محلية متصلة' : 'MT5 متصل') : hasState ? 'المنصة غير متصلة' : 'جاري فحص الخدمة';
    pill.className = `pill ${lastPollError ? 'red' : connected ? state.simulation ? 'amber' : 'green' : 'neutral'}`; pill.innerHTML = `<i></i>${h(uiText(label))}`;
  }
  const executionRunning=()=>['AUTO_DEMO','MANUAL_DEMO'].includes(state.mode)&&!obj(state.execution).entries_paused;
  function updateControls() {
    document.querySelectorAll('button').forEach((x) => {if (!x.classList.contains('nav-item') && !x.dataset.go && !x.dataset.unit && !['menu-toggle','refresh-button','confirm-accept'].includes(x.id) && !x.closest('dialog') && !x.dataset.symbol) x.disabled = busy;});
    const canStart = hasState && !lastPollError && !!account().login && (account().trade_mode === 0 || account().type === 'DEMO' || account().account_type === 'DEMO');
    $('start-button').disabled = busy || (!canStart&&!executionRunning());
    set('start-hint',!canStart ? 'اتصل بحساب تجريبي أو فعّل المحاكاة المحلية أولًا.' : obj(state.execution).reason ? `${obj(state.execution).entries_paused ? 'الدخول الجديد متوقف: ' : ''}${tr(state.execution.reason)}` : 'تتحقق طبقة التنفيذ من الحساب والمخاطرة قبل كل إرسال.');
    const manual = document.querySelector('input[name="mode"]:checked').value === 'MANUAL_DEMO';
    $('start-button').innerHTML = h(uiText(executionRunning()?'إيقاف الدخول الجديد':'ابدأ التداول')); 
    $('scan-button').disabled = busy || !hasState || !account().login; $('market-scan-button').disabled = $('scan-button').disabled;
  }
  function updateConversions() {
    document.querySelectorAll('[data-unit]').forEach((x) => x.classList.toggle('selected',x.dataset.unit === unit));
    document.querySelectorAll('.input-unit').forEach((x) => x.textContent = unit === 'percent' ? '%' : currency() || 'عملة الحساب');
    const equity = account().equity, r = Number($('risk-input').value), t = Number($('target-input').value);
    set('risk-conversion',unit === 'percent' && r > 0 ? finite(equity) ? `يعادل ${money(equity * r / 100)} من قيمة الحساب عند اعتماد التفويض.` : 'لا يمكن التحويل دون توفر قيمة الحساب.' : 'ميزانية مشتركة لكل صفقات المنظومة.');
    set('target-conversion',unit === 'percent' && t > 0 ? finite(equity) ? `يعادل ${money(equity * t / 100)} من قيمة الحساب عند اعتماد التفويض.` : 'لا يمكن التحويل دون توفر قيمة الحساب.' : 'بعد احتساب التكاليف الفعلية.');
  }
  function render() {
    updateConnection(); $('simulation-banner').hidden = !state.simulation;
    set('app-version',`Quant Trading AI ${state.version || ''}`.trim());
    set('running-version',`v${state.version || '—'}`);
    const a = account(), r = obj(state.risk), p = obj(state.performance), mode = state.mode || 'READ_ONLY';
    set('account-balance',money(a.balance)); set('account-equity',money(a.equity)); set('account-currency',a.currency ? `عملة الحساب: ${a.currency}` : 'عملة الحساب غير متاحة');
    const rawAccountName=typeof a.name==='string'?a.name.trim():'';
    const accountName=rawAccountName&&!/^(?:(?:null|none|undefined)\s*)+$/i.test(rawAccountName)?rawAccountName:'';
    set('account-login',a.login ? `# ${a.login}${accountName ? ` · ${accountName}` : ''}` : 'غير متصل'); set('account-server',a.server ? tr(a.server) : 'افتح الإعداد للاتصال بمنصة MT5');
    const type = a.trade_mode === 0 ? 'DEMO' : a.trade_mode === 1 ? 'CONTEST' : a.trade_mode === 2 ? 'REAL' : first(a.type,a.account_type,'UNKNOWN');
    $('account-type').className = `mini-pill ${cls(type)}`; set('account-type',tr(type));
    const headerMode=mode==='READ_ONLY'?'تحليل يعمل · التنفيذ متوقف':mode==='AUTO_DEMO'?uiText('نشط'):tr(mode);
    set('header-execution-mode',headerMode);
    $('header-execution-mode').title=mode==='READ_ONLY'?uiText('الواجهة تعرض التحليل للقراءة فقط ولا تملك تفويض إرسال أوامر.'):tr(obj(state.execution).reason||'');
    $('header-execution-mode').setAttribute('aria-label',`${headerMode}. ${$('header-execution-mode').title}`);
    set('active-mode',tr(mode)); set('position-mode',tr(mode)); set('footer-state',mode === 'READ_ONLY' ? 'لا يوجد تفويض بالتنفيذ' : `تفويض: ${tr(mode)}`);
    const status = typeof state.status === 'string' ? state.status : first(obj(state.status).state,obj(state.status).label,'STOPPED');
    $('engine-state').className = `pill ${cls(status) || (mode !== 'READ_ONLY' ? 'green' : 'neutral')}`; set('engine-state',tr(status)); $('engine-state').hidden=tr(status)===tr(mode);
    const received = first(state.last_update,state.updated_at,state.as_of,state.timestamp,obj(state.terminal).updated_at);
    set('last-update',received ? date(received,false) : '—');
    set('day-id',first(r.day_id,r.day,state.day_id,'—'));
    if(obj(state.execution).reason)set('start-hint',tr(state.execution.reason));
    if(mode!=='READ_ONLY' && obj(state.settings).validation_policy==='forward_demo'){
      const experimental=tr('اختبار أمامي تجريبي — غير مؤهل تاريخيًا');
      set('start-hint',experimental);set('active-mode',mode==='AUTO_DEMO'?uiText('نشط'):tr(mode));set('position-mode',tr(mode));
    }
    const remaining = first(r.remaining,r.remaining_budget,r.available), limit = first(r.limit,r.risk_amount,r.risk_limit,r.daily_limit,r.budget), realizedLoss = first(r.realized_net_loss,r.realized_loss,r.realized_losses,r.loss_realized), floatingLoss = first(r.floating_loss,r.floating_losses,r.loss_floating), reserved = first(r.reserved,r.reserved_risk), used = first(r.used,r.used_risk,finite(limit) && finite(remaining) ? limit - remaining : undefined);
    set('risk-remaining',money(remaining)); set('risk-used',money(used)); set('risk-limit',money(limit)); set('realized-loss',money(realizedLoss)); set('floating-loss',money(floatingLoss)); set('reserved-risk',money(reserved));
    $('risk-progress').style.width = finite(used) && limit > 0 ? `${Math.min(100,Math.max(0,used / limit * 100))}%` : '0%';
    if (r.policy) set('risk-policy',tr(r.policy)); else if (finite(r.exposure)) set('risk-policy',isEnglish()
      ? `Additional counted exposure: ${money(r.exposure)}, including ${money(r.external_exposure)} external exposure. The daily state is stored; restarting does not erase it.${arr(r.unbounded).length ? ` Unbounded risks: ${plain(r.unbounded)}` : ''}`
      : `تعرض إضافي محتسب: ${money(r.exposure)}، منه خارجي ${money(r.external_exposure)}. حالة اليوم محفوظة؛ إعادة التشغيل لا تمحوها.${arr(r.unbounded).length ? ` مخاطر غير محدودة: ${plain(r.unbounded)}` : ''}`);
    const realized = first(r.realized_gross,r.realized_pnl,r.realized,p.realized_pnl,p.realized), floating = first(r.floating_net,r.floating_pnl,r.floating,p.floating_pnl,p.floating), actualCosts = finite(r.commission_fee) && finite(r.swap) ? -(r.commission_fee + r.swap) : undefined, costs = first(r.costs,p.costs,actualCosts), net = first(r.net_target,r.net_pnl,r.net_progress,p.net_pnl,p.net), target = first(r.target,r.target_amount,r.daily_target,obj(state.settings).target_money);
    set('realized-pnl',money(realized)); set('floating-pnl',money(floating)); set('costs-pnl',money(costs)); set('net-progress',money(net)); set('daily-target',finite(target) ? money(target) : 'هدف غير محدد');
    const progress = finite(net) && target > 0 ? net / target * 100 : null;
    set('target-percent',finite(progress) ? `${num(progress,1)}%` : '—'); $('target-progress').style.width = finite(progress) ? `${Math.min(100,Math.max(0,progress))}%` : '0%';
    const unattributedCosts=first(r.unattributed_costs,p.unattributed_costs),costUncertainty=arr(first(r.cost_uncertainty,p.cost_uncertainty));
    set('unattributed-costs',money(unattributedCosts));
    $('cost-attribution-note').hidden=!(unattributedCosts>0||costUncertainty.length);
    set('cost-attribution-note',isEnglish()
      ? `Unattributed costs: ${money(unattributedCosts)}. They are deducted conservatively from progress; attribution uncertainty blocks entries.${costUncertainty.length ? ` ${costUncertainty.length} operation(s) have uncertain attribution; new entries remain blocked until reconciliation.` : ' Review reconciliation before treating every cost as attributed.'} Reaching the target is not shown as confirmed profit until the realized result is verified.`
      : `تكاليف غير منسوبة: ${money(unattributedCosts)}. تُخصم تحفظيًا من التقدم؛ غموض الإسناد يمنع الدخول.${costUncertainty.length ? ` توجد ${costUncertainty.length} عملية ذات إسناد غير مؤكد؛ الدخول الجديد ممنوع حتى المطابقة.` : ' راجع المطابقة قبل اعتبار جميع التكاليف منسوبة.'} لا يُعرض بلوغ الهدف كربح مؤكد قبل التحقق من النتيجة المحققة.`);
    if (r.net_formula || p.net_formula) set('net-formula',tr(r.net_formula || p.net_formula)); else if (finite(r.net_target)) set('net-formula',isEnglish()
      ? `Estimated net = attributed realized net + floating net − exit-cost reserve (${money(r.estimated_exit_cost)}) − unattributed costs (${money(unattributedCosts)}). Attributed costs are already included in realized net and are not subtracted twice.`
      : `الصافي التقديري = المحقق الصافي المنسوب + العائم الصافي − احتياطي الإغلاق (${money(r.estimated_exit_cost)}) − التكاليف غير المنسوبة (${money(unattributedCosts)}). التكاليف المنسوبة داخلة في المحقق الصافي ولا تُطرح مرتين.`);
    for (const [id,value] of [['realized-pnl',realized],['floating-pnl',floating],['net-progress',net]]) $(id).className = finite(value) ? value < 0 ? 'negative' : value > 0 ? 'positive' : '' : '';
    set('positions-badge',arr(state.positions).length); updateConversions(); renderExecutionSettings(); renderScan();
    const painters={overview:renderOpportunities,markets:()=>{renderSymbols();renderOpportunities();},research:renderResearch,news:renderNews,positions:renderPositions,performance:renderPerformance,knowledge:renderKnowledge,audit:renderEvents,setup:renderSetup};
    painters[currentView]?.();
    updateControls();
    if (state.error) {set('service-error',plain(state.error));$('service-error').hidden = false;}
    applyI18n();
    window.renderDemoPanel?.(state.demo_live);
  }
  function renderScan() {
    const s = obj(state.scan); const metrics = [['المكتشفة',s.discovered],['المفحوصة',s.checked],['المؤهلة',s.eligible],['غير المؤهلة حاليًا',s.excluded]];
    const html = metrics.map(([label,value]) => `<div class="scan-metric"><strong>${num(value,0)}</strong><span>${label}</span></div>`).join('');
    $('overview-scan').innerHTML = html; $('market-scan').innerHTML = html;
    const ratio = s.discovered > 0 && finite(s.checked) ? s.checked / s.discovered * 100 : 0; $('scan-progress').style.width = `${Math.min(100,ratio)}%`;
    const text = s.complete === true ? `اكتملت الدورة: ${date(s.cycle_finished)}. التأهيل لا يعني وجود فرصة دخول.` : s.cycle_started ? `المسح غير مكتمل · ${num(s.checked,0)} من ${num(s.discovered,0)} رمزًا · بدأ ${date(s.cycle_started)}.` : 'لم تكتمل أي دورة مسح؛ لا يمكن الادعاء بفحص السوق كله.';
    set('scan-status',text); set('market-scan-state',text);
  }
  function rows() {return arr(obj(state.scan).rows);}
  const symbolName = (r) => r.symbol || r.name || '';
  function renderSymbols() {
    const term = $('symbol-search').value.trim().toLowerCase(), filter = $('symbol-filter').value;
    const records = rows().filter((r) => {const eligible = r.eligible === true, checked = first(r.checked,r.checked_at,r.last_checked,r.last_scan); return (filter === 'all' || filter === 'eligible' && eligible || filter === 'excluded' && r.eligible === false && checked || filter === 'unchecked' && !checked) && (!term || plain(r).toLowerCase().includes(term));});
    set('symbols-count',`${records.length} ظاهر من ${rows().length} رمز`);
    updateChartSymbols();
    if (!records.length) {$('symbols-table').innerHTML = empty('لا توجد رموز بهذه الحالة.','اتصل بالمنصة وابدأ المسح لعرض قائمة الوسيط الكاملة.');return;}
    $('symbols-table').innerHTML = `<table><thead><tr><th>الرمز</th><th>فئة الأصل</th><th>الأهلية</th><th>سعر البيع / سعر الشراء</th><th>السبريد (فرق سعر)</th><th>سبب الحالة أو تحذير التكلفة</th><th>آخر فحص</th></tr></thead><tbody>${records.map((r) => {const tick = obj(r.tick), checked = first(r.checked,r.checked_at,r.last_scan), status = !checked ? 'غير مفحوص' : r.eligible === true ? 'مؤهل' : 'غير مؤهل حاليًا', reason = [...arr(r.reasons),...arr(r.warnings)].filter(Boolean).join(' • ') || first(r.reason,r.status);return `<tr data-symbol="${h(symbolName(r))}" tabindex="0"><td><span class="symbol-name">${h(symbolName(r))}</span></td><td>${h(tr(first(r.asset_class,r.category,r.classification)))}</td><td><span class="mini-pill ${r.eligible === true ? 'green' : checked ? 'amber' : ''}">${status}</span></td><td dir="ltr">${num(first(r.bid,tick.bid),6)} / ${num(first(r.ask,tick.ask),6)}</td><td>${num(first(r.spread,r.spread_price),6)}</td><td title="${h(plain(reason))}">${h(plain(reason))}</td><td>${h(date(first(r.checked_at,r.last_checked,r.last_scan,r.as_of)))}</td></tr>`;}).join('')}</tbody></table>`;
    if (selectedSymbol && $('symbol-details').hidden === false) showSymbol(selectedSymbol,false);
  }
  function updateChartSymbols() {
    const selected = $('chart-symbol').value;
    const symbols = Array.from(new Set([...rows().map(symbolName),...arr(state.cards).map((c) => c.symbol),obj(state.chart).symbol].filter(Boolean)));
    $('chart-symbol').innerHTML = `<option value="">اختر رمزًا</option>${symbols.map((s) => `<option value="${h(s)}">${h(s)}</option>`).join('')}`;
    $('chart-symbol').value = symbols.includes(selected) ? selected : symbols.includes(prefs.symbol) ? prefs.symbol : obj(state.chart).symbol || '';
  }
  function showSymbol(symbol,scroll = true) {
    selectedSymbol = symbol; const r = rows().find((x) => symbolName(x) === symbol); if (!r) return;
    const contract = {...obj(r.spec),...obj(r.contract),...obj(r.info),...r}; const session = obj(r.session), tick = obj(r.tick);
    const details = [['وصف العقد',contract.description],['المسار لدى الوسيط',contract.path],['السماح بالتداول',first(r.trade_mode_name,({0:'الدخول معطل',1:'شراء فقط',2:'بيع فقط',3:'إغلاق فقط',4:'شراء وبيع'})[contract.trade_mode])],['جلسة السوق',session.known === false ? `غير متحققة: ${plain(session.reason)}` : session.open === true ? 'مفتوحة' : session.open === false ? 'مغلقة' : first(r.market_status,r.session_status)],['آخر سعر',date(first(r.tick_time,tick.time))],['توفر التاريخ',first(r.history_bars,r.history_count,r.bar_count,r.history_status)],['حجم العقد',contract.trade_contract_size],['عملة الربح',contract.currency_profit],['عملة الهامش',contract.currency_margin],['خطوة السعر',first(contract.trade_tick_size,contract.point)],['الحد الأدنى للوت',contract.volume_min],['الحد الأقصى للوت',contract.volume_max],['خطوة اللوت',contract.volume_step],['حد الوقف بالنقاط',contract.trade_stops_level],['تجميد التعديل بالنقاط',contract.trade_freeze_level],['نمط التنفيذ',({0:'طلب السعر',1:'تنفيذ فوري',2:'تنفيذ سوقي',3:'تنفيذ بورصة'})[contract.trade_exemode]],['تاريخ انتهاء العقد',contract.expiration_time ? date(contract.expiration_time) : 'غير منطبق أو غير متاح'],['حالة الهامش',first(r.margin_status,r.margin_check)],['أسباب الأهلية',plain(first(r.reasons,r.reason))]];
    $('symbol-details').hidden = false; $('symbol-details').innerHTML = `<div class="panel-heading"><h2><span class="symbol-name">${h(symbol)}</span> · تفاصيل الفحص والعقد</h2><button class="text-button" data-open-chart="${h(symbol)}">عرض الشارت ←</button></div><div class="detail-grid">${details.map(([k,v]) => `<div class="detail-item"><span>${h(k)}</span><b>${h(plain(v))}</b></div>`).join('')}</div>`;
    if (scroll) $('symbol-details').scrollIntoView({behavior:'smooth',block:'nearest'});
  }
  function allOpportunities() {return arr(state.opportunities);}
  function executionCosts() {
    // These previously authorized settings remain part of sizing and testing,
    // even though the activation form no longer asks the trader to enter them.
    const settings=obj(state.settings), costs={commission_per_lot:first(settings.commission_per_lot,0),slippage_points:first(settings.slippage_points,10)};
    if(Object.values(costs).some(value=>!finite(value)||value<0)) throw new Error(uiText('إعدادات التكاليف المحفوظة غير صالحة؛ راجع تقرير التشخيص.'));
    return costs;
  }
  function scalpSettingsPayload() {
    const selected=$('scalp-mode-input').value||'off', profiles={};
    for(const variant of ['normal','fast']) {
      const value=(field)=>{const input=$(`scalp-${variant}-${field}`);return input.value.trim()?Number(input.value):null;};
      const profile={enabled:selected===variant,variant,risk_percent:value('risk'),target_value:value('target'),min_reward_risk:value('rr')??2};
      const profit=value('profit');if(profit!==null)profile.profit_percent=profit;
      if(profile.enabled && (!(profile.risk_percent>0&&profile.risk_percent<=100&&Number.isFinite(profile.risk_percent))||!(profile.target_value>0&&Number.isFinite(profile.target_value))||!(profile.min_reward_risk>=2&&Number.isFinite(profile.min_reward_risk)))) throw new Error(uiText('حدد مخاطرة سكالب موجبة وهدفًا موجبًا وعائدًا لا يقل عن ١:٢.'));
      profiles[variant]=profile;
    }
    return profiles;
  }
  function selectScalpMode(variant) {
    if(!['normal','fast'].includes(variant))return;
    $('scalp-mode-input').value=variant;
    executionFormDirty=true;
    $('scalp-options').open=true;
    renderExecutionSettings();
  }
  function scalpModeActivationPayload() {
    const saved=obj(state.settings),risk=Number(saved.risk_amount),target=Number(saved.target_amount);
    if(!Number.isFinite(risk)||risk<=0||!Number.isFinite(target)||target<=0)throw new Error(uiText('اعتمد حدود اليوم أولًا من نموذج التفويض.'));
    const profiles=scalpSettingsPayload();
    return {risk_value:risk,target_value:target,unit:'amount',
      mode:['AUTO_DEMO','MANUAL_DEMO'].includes(state.mode)?state.mode:document.querySelector('input[name="mode"]:checked').value,
      decision_protocol:saved.decision_protocol||'multi_school_v1',validation_policy:saved.validation_policy||'forward_demo',
      scalp_only:true,scalping:profiles,fast_profit_protection:!!saved.fast_profit_protection,
      fast_cash_target_usd:first(saved.fast_cash_target_usd,1),...executionCosts()};
  }
  function renderExecutionSettings() {
    const settings=Object.keys(obj(state.settings)).length?obj(state.settings):obj(state.setup), profiles=obj(settings.scalping),stamp=JSON.stringify([settings.decision_protocol,settings.validation_policy,profiles]);
    set('authorization-loss-value',money(first(obj(state.risk).risk_amount,settings.risk_amount)));
    set('authorization-goal-value',money(first(obj(state.risk).target_amount,settings.target_amount)));
    set('execution-policy-note',settings.decision_protocol==='multi_school_v1'?(settings.scalp_only&&obj(obj(settings.scalping).fast).enabled?'وكيل سكالب محلي يقود القرار من الدقيقة ويوازن أدلة المدارس؛ لا يشترط اتفاق الفريمات. تبقى التكلفة الصافية ووقف الخسارة وحدود المال ملزمة.':'مسار متعدد المدارس من شموع MT5؛ يفحص جميع الوكلاء المنفذين ويجمع عائلتي أدلة وفريمين، دون إلزام بتسلسل ICT. البيانات الناقصة لا تعطي تصويتًا.'):'التوقيت نموذج محلي معلن. الحجم الحقيقي عند السعر يظهر غير متاح عند غياب مصدره؛ الهدف اليومي لا يضمن الربح.');
    if(settings.fast_profit_protection&&obj(profiles.fast).enabled)set('execution-policy-note','سكالب الدقيقة مع تأكيد اتجاه ربع الساعة والساعة. جني الربح عند صافي دولار واحد دون انتظار الدولارين؛ يوضع الهدف لدى الوسيط حين تسمح شروطه. الانزلاق قد يقلل الربح الفعلي. هدف التحليل الهيكلي لا يمثل عائد الخروج النقدي.');
    if(hasState&&account().login&&!executionFormDirty&&(!executionFormRestored||stamp!==executionFormStamp)) {
      $('scalp-mode-input').value=obj(profiles.fast).enabled?'fast':obj(profiles.normal).enabled?'normal':'off';
      for(const variant of ['normal','fast']) {
        const profile=obj(profiles[variant]);
        for(const [field,key] of [['risk','risk_percent'],['target','target_value'],['rr','min_reward_risk'],['profit','profit_percent']]) if(finite(profile[key])) $(`scalp-${variant}-${field}`).value=String(profile[key]);
      }
      executionFormRestored=true;executionFormStamp=stamp;
    }
    const variant=$('scalp-mode-input').value, requested=variant==='normal'||variant==='fast'?Number($(`scalp-${variant}-risk`).value):0;
    document.querySelectorAll('[data-scalp-mode]').forEach(button=>{
      const selected=button.dataset.scalpMode===variant;button.classList.toggle('selected',selected);
      button.setAttribute('aria-pressed',String(selected));button.disabled=busy;
    });
    for(const name of ['normal','fast'])$(`scalp-profile-${name}`).hidden=variant!==name;
    set('scalp-mode-draft',executionFormDirty?uiText('تغييرات غير مطبقة'):''); $('scalp-mode-draft').hidden=!executionFormDirty; $('apply-scalp-mode').hidden=!executionFormDirty||!executionRunning();
    $('apply-scalp-mode').disabled=busy||!account().login;
    const amount=requested>0&&finite(account().equity)?account().equity*requested/100:0;
    const budget=obj(state.risk), cap=Math.min(amount,finite(budget.remaining)?budget.remaining:0,(budget.risk_amount||0)*(obj(state.settings).max_trade_fraction||.2));
    set('scalp-risk-preview',amount>0?`${uiText('المخاطرة المطلوبة')}: ${money(amount)} · ${uiText('حد تقديري ضمن الميزانية المشتركة')}: ${money(cap)}`:'تُقيّد المخاطرة المطلوبة بالميزانية المتبقية وحد الصفقة المشترك.');
    const controls=obj(state.scalping), scheduler=obj(state.fast_scheduler);
    const connected=first(account().connected,obj(state.terminal).connected,!!account().login);
    const executionActive=connected&&['AUTO_DEMO','MANUAL_DEMO'].includes(state.mode)&&!obj(state.execution).entries_paused;
    const profileFor=name=>Object.keys(obj(obj(controls[name]).settings)).length?obj(controls[name].settings):obj(profiles[name]);
    const statusFor=(control,profile)=>control.latched||obj(control.progress).latched?'بلغ هدف السكالب؛ الدخول لهذا النمط متوقف':!profile.enabled?'غير مفعل':executionActive?'نشط':'محدد؛ ينتظر استئناف التنفيذ';
    const activeVariant=['fast','normal'].find(name=>profileFor(name).enabled);
    set('scalp-active-status',activeVariant?`${uiText(activeVariant==='fast'?'سكالب سريع':'سكالب عادي')} — ${uiText(statusFor(obj(controls[activeVariant]),profileFor(activeVariant)))}`:uiText('السكالب غير مفعل'));
    $('fast-scheduler-status').hidden=!scheduler.enabled;
    $('fast-scheduler-details').hidden=!scheduler.enabled;
    $('fast-scheduler-status').innerHTML=scheduler.enabled?[
      [uiText('تقدم دورة السكالب المتسارع'),`${num(scheduler.checked_in_sweep,0)} / ${num(scheduler.symbols_total,0)}`],
      [uiText('مدة آخر دورة مكتملة'),finite(scheduler.last_sweep_seconds)?`${num(scheduler.last_sweep_seconds)} ${uiText('ثانية')}`:uiText('لم تكتمل دورة بعد')],
      [uiText('زمن العودة المرصود لنفس الرمز'),finite(scheduler.observed_revisit_seconds)?`${num(scheduler.observed_revisit_seconds)} ${uiText('ثانية')}`:uiText('لم يُقَس بعد')]
    ].map(([label,value])=>`<div class="detail-item"><span>${h(label)}</span><b>${h(value)}</b></div>`).join(''):'';
    $('scalp-progress').innerHTML=['normal','fast'].map(name=>{
      const control=obj(controls[name]), progress=obj(control.progress||control), profile=profileFor(name), target=first(profile.target_value,progress.target_value), net=first(progress.progress_net,progress.net_target,progress.net_progress,progress.net);
      return `<div class="detail-item"><span>${h(uiText(name==='normal'?'السكالب العادي':'السكالب المتسارع'))}</span><b>${money(net)} / ${money(target)}</b><small>${h(uiText(statusFor(control,profile)))}</small></div>`;
    }).join('');
  }
  function decisionMatrixHTML(matrix) {
    if(!matrix||typeof matrix!=='object')return '';
    if(matrix.route==='MULTI_SCHOOL_OHLC') {
      const evidence=arr(matrix.school_evidence),roles={ENTRY_TRIGGER:'إشارة الدخول المختارة',SUPPORTING:'دليل مساند',OPPOSING:'دليل معارض',NO_DIRECTIONAL_VOTE:'دون تصويت اتجاهي'};
      const families={price_structure:'بنية السعر والشموع',price_transform:'المؤشرات المشتقة من السعر',volume_weighted:'الحجم أو نشاط التكات',other_asset:'الأصل المقابل'};
      const rows=evidence.map((row)=>{
        const valid=['READY','WAIT'].includes(row.status),direction=valid?(row.direction==='NEUTRAL'?uiText('حياد مفحوص'):tr(row.direction)):'—';
        return `<tr><td>${h(schoolName(row.school||row.strategy_id))}</td><td>${h(row.timeframe||'—')}</td><td>${badge(row.status||'NOT_EVALUATED')}</td><td>${h(direction)}</td><td>${h(uiText(roles[row.role]||'دون تصويت اتجاهي'))}</td></tr>`;
      }).join('');
      const trend=Object.values(obj(matrix.higher_timeframe_trend)).map(row=>`<span>${h(row.timeframe)}: ${h(tr(row.direction))}</span>`).join('');
      const familyRows=Object.entries(obj(matrix.evidence_families)).map(([key,value])=>`<span>${h(uiText(families[key]||key))}: ${num(value,1)}</span>`).join('');
      const balance=obj(matrix.directional_evidence), coverage=obj(matrix.evidence_coverage);
      const consensus=finite(balance.net)?`<p class="tiny-note">${h(uiText('ترجيح العائلات دون نسبة تصويت ثابتة'))}: ${h(uiText('الدعم'))} ${num(balance.support,1)} · ${h(uiText('المعارضة'))} ${num(balance.opposition,1)} · ${h(uiText('صافي الدليل'))} ${num(balance.net,1)}</p>`:'';
      const participation=finite(coverage.registered_models)?`<p class="tiny-note">${h(uiText('النماذج المسجلة'))}: ${num(coverage.registered_models,0)} · ${h(uiText('البطاقات الصالحة الحديثة'))}: ${num(coverage.fresh_eligible_cards,0)} · ${h(uiText('البطاقات المستبعدة'))}: ${num(coverage.excluded_cards,0)}. ${h(uiText('نقص البيانات لا يؤكد أي اتجاه.'))}</p>`:'';
      return `<div class="decision-matrix"><h3>${h(uiText('أدلة جميع نماذج التحليل'))}</h3><p class="tiny-note">${h(uiText('هذه نتائج النماذج المحفوظة مع قرار الدخول، وليست أصوات خمس مدارس مستقلة. تُجمع الأدلة المترابطة قبل الترجيح.'))}</p><div class="opportunity-meta">${familyRows}</div>${consensus}${participation}${trend?`<div class="opportunity-meta">${trend}</div>`:''}${evidence.length?`<details><summary>${h(uiText('تفاصيل كل نموذج'))} (${evidence.length})</summary><div class="table-scroll"><table><thead><tr><th>${h(uiText('المدرسة'))}</th><th>${h(uiText('الفريم'))}</th><th>${h(uiText('حالة الدليل'))}</th><th>${h(uiText('الاتجاه'))}</th><th>${h(uiText('الدور في القرار'))}</th></tr></thead><tbody>${rows}</tbody></table></div></details>`:`<p>${h(uiText('هذا قرار سابق لا يحتوي تفاصيل النماذج المحفوظة؛ لا يُستنتج منه الحياد.'))}</p>`}<p class="tiny-note">${h(uiText('تدفق النشاط من التكات تقريب، وليس تدفق صفقات فعليًا. درجات اكتمال القواعد ليست احتمالات ربح.'))}</p></div>`;
    }
    if(!['ict','volume_profile','time','momentum','elliott'].some(key=>matrix[key]))return '';
    const names={ict:'السيولة والهيكل والفجوة',volume_profile:'حجم الصفقات ونقطة التحكم',time:'الدورات الزمنية المحلية',momentum:'الزخم والانحراف',elliott:'الهيكل الموجي المحلي'};
    return `<div class="decision-matrix"><h3>${h(uiText('مصفوفة تقاطع المدارس'))}</h3><table><thead><tr><th>${h(uiText('المدرسة'))}</th><th>${h(uiText('حالة الدليل'))}</th><th>${h(uiText('الاتجاه'))}</th></tr></thead><tbody>${Object.entries(names).map(([key,name])=>{const row=obj(matrix[key]);return `<tr><td>${h(uiText(name))}</td><td>${badge(row.status||'NOT_EVALUATED')}</td><td>${h(row.direction?tr(row.direction):'—')}</td></tr>`;}).join('')}</tbody></table><p class="tiny-note">${h(uiText('التوقيت محلي معلن؛ اكتمال القواعد ليس احتمال نجاح. الحجم غير المتاح لا يُستبدل بمؤشر تكات.'))}</p>${matrix.structural_rr?`<div class="opportunity-meta"><span>${h(uiText('العائد السعري مقابل المخاطرة'))}: ${num(matrix.structural_rr.gross_rr,3)}</span><span>${h(uiText('فحص العائد الصافي بعد التكاليف قبل الإرسال'))}</span></div>`:''}</div>`;
  }
  function opportunityExpired(o) {return finite(o.expires_at)&&Number(o.expires_at)<=Date.now()/1000;}
  function linkedExecutionHTML(o) {
    const proposalId=first(o.intent_id,obj(o.proposal).id,o.id);
    const intent=arr(state.intents).find(i=>i.kind==='ENTRY'&&proposalId&&obj(obj(i.payload).proposal).id===proposalId);
    const heading=`<span>${h(uiText('وقت هذا القرار'))}: ${h(date(o.as_of))}</span>`;
    if(!intent)return `<div class="opportunity-meta">${heading}<span>${h(uiText('لا يوجد أمر مرتبط بهوية هذا الاقتراح في السجل المعروض.'))}</span></div>`;
    return `<div class="opportunity-meta">${heading}<span>${h(uiText('حالة الأمر المرتبط بهذا الاقتراح'))}: ${badge(intent.state)}</span><span>${h(uiText('وقت إنشاء الأمر'))}: ${h(date(intent.created))}</span></div><p class="tiny-note">${h(uiText('القرار الحالي وحالة الأمر سجلان منفصلان؛ رفض إشارة جديدة لا يلغي تنفيذًا سابقًا.'))}</p>`;
  }
  function opportunities() {return allOpportunities().filter((o)=>!opportunityExpired(o)&&(o.eligible===true||['APPROVE','APPROVED','EXECUTE','QUALIFIED'].includes(String(o.decision||o.status||'').toUpperCase())));}
  function opportunityHTML(o,index,full = true) {
    o={...obj(o.proposal),...o};
    const expired=opportunityExpired(o);
    const decision = expired?'EXPIRED':first(o.decision,o.side,o.direction,'WAIT'); const reason = expired?uiText('انتهت صلاحية هذا الاقتراح؛ حالة الأمر المنفذ تُراجع بشكل مستقل.'):arr(o.protocol_reasons).length?arr(o.protocol_reasons).map(r=>obj(r)[isEnglish()?'en':'ar']||r.code):first(o.reason,o.reasons,o.explanation,o.summary); const supporting = first(o.supporting,o.supporting_evidence,o.support), opposing = first(o.opposing,o.opposing_evidence,o.conflicts);
    o.risk_reason=first(o.risk_reason,obj(o.risk_result).reasons,obj(o.risk_result).reason,obj(o.risk_result).approved===true?'اجتاز الفحص المستقل':undefined);
    return `<div class="opportunity"><div class="opportunity-head"><div class="opportunity-identity"><span class="rank">${String(index + 1).padStart(2,'0')}</span><b class="symbol-name">${h(o.symbol || '—')}</b><span class="muted">${h(o.timeframe || '')}</span>${badge(decision)}</div>${o.symbol ? `<button class="text-button" data-open-chart="${h(o.symbol)}">الشارت ←</button>` : ''}</div><p class="opportunity-reason">${h(plain(reason))}</p><div class="opportunity-meta"><span>جودة الأدلة: ${num(first(o.score,o.quality_score),1)}${finite(first(o.score,o.quality_score)) ? ' / 100' : ''}</span><span>صلاحية: ${h(date(first(o.expires_at,o.valid_until)))}</span><span>المخاطر: ${h(plain(first(o.risk_reason,o.risk_status,obj(o.risk).reason)))}</span></div>${full ? `<div class="evidence-columns"><div><strong>الأدلة المؤيدة</strong>${listHTML(supporting,'لم تُرفق أدلة مؤيدة.')}</div><div><strong>التعارض أو النواقص</strong>${listHTML(opposing,'لم تُرفق تفاصيل التعارض؛ لا يعني ذلك غيابه.')}</div></div><div class="opportunity-meta"><span>الدخول: ${h(plain(first(o.entry,o.entry_zone)))}</span><span>الإبطال: ${h(plain(o.invalidation))}</span><span>النتيجة الكمية: ${h(plain(first(o.quant,o.quant_status)))}</span></div>` : ''}${decisionMatrixHTML(o.decision_matrix)}${linkedExecutionHTML(o)}</div>`;
  }
  function listHTML(values,missing = 'غير متاح') {const valuesArr = Array.isArray(values) ? values : values ? [values] : [];return valuesArr.length ? `<ul>${valuesArr.map((v) => {const card=typeof v==='string'?arr(state.cards).find((c)=>c.id===v):null;return `<li>${h(card?`${schoolName(card.school)} · ${card.timeframe}: ${tr(card.scenario)}`:plain(v))}</li>`;}).join('')}</ul>` : `<span class="muted">${h(missing)}</span>`;}
  function renderOpportunities() {
    const data = opportunities(), deferred = allOpportunities().length-data.length; $('opportunities').innerHTML = data.length ? data.map((o,i) => opportunityHTML(o,i)).join('') : empty('لا توجد فرص مؤهلة معروضة.',`${deferred ? `${uiText('نتائج الفحص غير المؤهلة')}: ${deferred}. ${uiText('تشمل الانتظار والرفض وانتهاء الصلاحية؛ ليست جميعها أوامر مرفوضة.')}` : ''} ${uiText('الانتظار قرار صالح؛ لا يُخفَّض معيار الدخول للاقتراب من الهدف.')}`);
    $('committee-summary').className = data.length ? '' : 'empty compact';
    $('committee-summary').innerHTML = data.length
      ? `<p class="tiny-note committee-preview-count">${h(uiText('ملخص أفضل فرصة من الفرص المؤهلة'))}: ${num(data.length,0)} · ${h(uiText('افتح الأبحاث لرؤية القائمة كاملة'))}</p>${opportunityHTML(data[0],0,false)}`
      : 'لا توجد فرصة دخول مؤهلة الآن.';
  }
  function renderResearch() {
    updateChartSymbols();
    const chart = obj(state.chart), symbol = chart.symbol || $('chart-symbol').value; const cards = arr(chart.cards).length ? chart.cards : arr(state.cards).filter((c) => !symbol || c.symbol === symbol);
    const openCards = new Set(Array.from(document.querySelectorAll('#research-cards details[open]')).map((d)=>d.dataset.cardId));
    const opportunity = chart.committee ? [{...chart.committee,symbol:chart.committee.symbol||symbol}] : arr(chart.committees).length ? chart.committees.map((c)=>({...c,symbol:c.symbol||symbol})) : opportunities().filter((o) => !symbol || o.symbol === symbol);
    $('research-committee').innerHTML = opportunity.length ? opportunity.map((o,i) => opportunityHTML(o,i,true)).join('') : empty('لا يوجد قرار لجنة لهذا الرمز.','بطاقات المدارس منفردة لا تُجيز إرسال الأوامر.');
    set('chart-title',chart.symbol ? `${chart.symbol} · ${chart.timeframe || '—'}` : 'الشارت والأدلة'); set('chart-time',chart.data_time || chart.as_of ? `آخر بيانات: ${date(first(chart.data_time,chart.as_of))}` : 'وقت آخر شمعة يظهر على الشارت');
    chartBars = arr(chart.bars).filter((b) => ['open','high','low','close'].every((k) => finite(b[k])));
    $('chart-empty').hidden = chartBars.length > 0;
    const omittedCards=!arr(chart.cards).length&&state.cards_truncated?`<p class="tiny-note">يعرض آخر ${cards.length} بطاقة من أصل ${num(state.cards_total,0)} لتسريع الواجهة؛ اختيار رمز وفريم يعرض أدلتهما الكاملة.</p>`:'';
    $('research-cards').innerHTML = omittedCards+(cards.length ? cards.map(cardHTML).join('') : empty('لا توجد بطاقات مدارس بعد.','حدد الرمز والفريم ثم اضغط «عرض»، أو انتظر اكتمال تحليل السوق.'));
    renderDecisionFlow(chart,cards,opportunity);
    renderTrendlineSchool(chart);
    document.querySelectorAll('#research-cards details').forEach((d,i)=>{d.dataset.cardId=[cards[i].school,cards[i].symbol,cards[i].timeframe].join(':');d.open=openCards.has(d.dataset.cardId);});
    requestAnimationFrame(drawChart);
  }
  function renderDecisionFlow(chart,cards,committee) {
    const bars=arr(chart.bars), analyses=arr(chart.school_analyses), latest=bars.at(-1),
      flowState=latest?`${num(bars.length,0)} شمعة · ${h(chart.symbol||'—')} · ${h(chart.timeframe||'—')}`:'بانتظار اختيار الرمز والفريم';
    set('flow-input',flowState);
    set('flow-quality',latest?`صالحة زمنيًا حتى ${date(latest.time)} · الشمعة الحالية غير مستخدمة`:'لا توجد عينة شارت مفحوصة');
    set('flow-schools',`${num(cards.length,0)} بطاقة من النماذج المسجلة + ${num(analyses.length,0)} تحليل منفصل لا يصوت للجنة`);
    set('flow-committee',committee.length?`${num(committee.length,0)} فرصة معروضة؛ التفاصيل وأسباب الانتظار تحت قرار اللجنة`:'لا يوجد قرار لجنة لهذا الرمز في هذه اللقطة');
    set('flow-execution',`${uiText('وضع النظام')}: ${h(uiText(state.mode||'READ_ONLY'))} · المدرسة المستقلة لا تملك سلطة إرسال`);
    const micro=obj(chart.microstructure), tickText=micro.ticks_status==='OK'?`تحديثات سعر في آخر دقيقة: ${num(micro.tick_observations,0)}`:'سجل التكات غير متاح من هذا المصدر',
      depthText=micro.depth_status==='OK'?`عمق وسيط متاح: ${micro.depth_levels===null?'نعم':num(micro.depth_levels,0)+' مستويات'}`:'عمق الوسيط غير متاح';
    if(micro.mode)set('flow-quality',`${$('flow-quality').textContent} · ${tickText} · ${depthText} · لا يُستنتج اتجاه صفقات منفذة`);
    set('decision-flow-status',latest?'مسار الشارت محدث':'بانتظار بيانات الشارت');
  }
  function renderTrendlineSchool(chart) {
    const result=arr(chart.school_analyses).find(x=>x.school_id==='trendline_school');
    const status=$('trendline-school-status'),target=$('trendline-school-result');
    if(!status||!target)return;
    if(!result){status.textContent=uiText('لم يبدأ');target.className='empty compact';target.textContent=uiText('اختر رمزًا وفريمًا ثم اعرض الشارت لقراءة محاور الاتجاه والخطوط والكسر المؤكد.');return;}
    status.textContent=uiText(result.status||'UNKNOWN');
    const direction=uiText(result.direction||'NEUTRAL'), lines=arr(result.boundaries), inputs=obj(result.inputs);
    const boundaryRows=lines.map(line=>`<div class="trendline-boundary"><b>${h(uiText(line.kind==='SUPPORT'?'دعم صاعد':'مقاومة هابطة'))}</b><span>${h(uiText('الميل لكل شمعة'))}: ${num(line.slope_per_bar,6)}</span><span>${h(uiText('السعر عند آخر إغلاق'))}: ${num(line.current_price,6)}</span><span>${h(uiText('خطأ الملاءمة / ATR'))}: ${num(inputs.atr?line.rms_residual/inputs.atr:null,3)}</span><span>${h(uiText('المحاور المؤكدة'))}: ${num(line.touch_count,0)}</span></div>`).join('');
    target.className='trendline-result';
    target.innerHTML=`<div class="trendline-summary"><strong>${h(direction)}</strong><p>${h(result.reason||'')}</p></div><div class="detail-grid"><div class="detail-item"><span>${h(uiText('الشموع المكتملة'))}</span><b>${num(inputs.completed_bars,0)}</b></div><div class="detail-item"><span>${h(uiText('المحاور المؤكدة'))}</span><b>${num(inputs.confirmed_pivots,0)}</b></div><div class="detail-item"><span>${h(uiText('نطاق التقلب ATR'))}</span><b>${finite(inputs.atr)?num(inputs.atr,6):'—'}</b></div><div class="detail-item"><span>${h(uiText('صلاحية التنفيذ'))}</span><b>${h(uiText('تحليل فقط'))}</b></div></div>${boundaryRows||`<p class="tiny-note">${h(uiText('لم يتكون خط صالح من ثلاثة محاور مؤكدة بعد.'))}</p>`}<p class="tiny-note">${h(uiText('قاعدة المدرسة'))}: ${h(uiText('ثلاث نقاط محورية مؤكدة؛ كسر لا يثبت إلا بإغلاق مكتمل.'))} ${h(uiText('لا يصوت للجنة ولا يرسل أوامر.'))}</p>`;
  }
  function cardHTML(c) {
    const definition=obj(obj(c.contract).definition), ruleDetails=isEnglish()?(definition.rules_en||definition.rules):(definition.rules_ar||definition.rules_en||definition.rules);
    const fields = [['حالة كود القاعدة',c.code_implementation],['اكتمال المدرسة',c.school_complete?'مكتملة حسب تعريفها':'تفسير محلي محدود'],['نطاق المدرسة',c.scope_description],['بدائل محلية منفذة',c.contract?.executable_specialists],['قواعد التخصص',ruleDetails],['معاملات القاعدة',definition.parameters],['حالة السوق',c.market_regime?.name],['الأدلة الرقمية والشموع',c.evidence],['الشروط المتحققة',c.conditions_met],['الشروط الناقصة',c.conditions_missing],['منطقة الدخول وشرطها',first(c.entry,c.entry_zone)],['إبطال التحليل وشرطه',c.invalidation],['وقف التنفيذ المقترح',first(c.stop,c.execution_stop)],['الأهداف وطريقة اشتقاقها',c.targets],['السيناريو البديل',c.alternative],['خطة إدارة الصفقة',c.execution_plan],['معادلة درجة الجودة',c.score_formula],['متطلبات البيانات',c.data_requirements],['الافتراضات',c.assumptions],['المصادر',c.sources],['النواقص',c.gaps]];
    return `<article class="research-card"><div class="research-card-header"><div><h3>${h(schoolName(first(c.school,c.name,c.strategy)))}</h3><small>إصدار ${h(c.version || 'غير معلن')} · ${h(schoolName(c.strategy || c.strategy_id || ''))}</small></div>${badge(c.status || 'UNKNOWN')}</div><div class="card-tags">${badge(c.direction || 'NEUTRAL')}<span class="mini-pill">${h(c.symbol || '—')} · ${h(c.timeframe || '—')}</span><span class="mini-pill">البيانات: ${h(tr(c.quality || 'UNKNOWN'))}</span></div><p class="scenario">${h(tr(c.scenario || 'السيناريو غير متاح.'))}</p><div class="detail-grid"><div class="detail-item"><span>الشروط</span><b>${h(tr(c.status || 'WAIT'))}</b></div><div class="detail-item"><span>صوت صالح للاقتراح</span><b>${c.actionable === true && c.status === 'READY' ? 'مرشح لفحص اللجنة والمخاطر' : 'لا'}</b></div><div class="detail-item"><span>انتهاء الصلاحية</span><b>${h(date(c.expires_at))}</b></div></div><details><summary>عرض الأدلة والشروط وخطة التنفيذ</summary>${fields.map(([label,value]) => `<div class="card-field"><strong>${h(label)}</strong>${Array.isArray(value) ? listHTML(value,'لم تُرفق بيانات.') : h(plain(value))}</div>`).join('')}<div class="card-field"><strong>توقيت البيانات والتحليل</strong>البيانات: ${h(date(c.data_time))}<br>التحليل: ${h(date(first(c.analyzed_at,c.valid_at)))}<br>الصلاحية: ${h(date(c.expires_at))}</div></details></article>`;
  }
  function drawChart() {
    const canvas = $('price-chart'), width = canvas.clientWidth, height = canvas.clientHeight; if (!width || !height) return;
    const dpr = window.devicePixelRatio || 1;canvas.width = width*dpr;canvas.height = height*dpr;const ctx = canvas.getContext('2d');ctx.scale(dpr,dpr);ctx.clearRect(0,0,width,height);
    if (!chartBars.length) {chartGeometry = null;return;}
    const bars = chartBars.slice(-110), chart = obj(state.chart), cards = arr(chart.cards).length ? chart.cards : arr(state.cards).filter((c) => c.symbol === chart.symbol && c.timeframe === chart.timeframe);
    let low = Math.min(...bars.map((b) => b.low)), high = Math.max(...bars.map((b) => b.high));const spread = Math.max(high-low,high*.0001);low -= spread*.1;high += spread*.12;
    const left = 12,right = 82,top = 16,bottom = 31,plotW = width-left-right,plotH = height-top-bottom,step = plotW/bars.length;
    const y = (v) => top + (high-v)/(high-low)*plotH;
    ctx.font = '10px Segoe UI';ctx.textAlign = 'left';ctx.textBaseline = 'middle';
    for(let i=0;i<5;i++){const price=low+(high-low)*i/4,yy=y(price);ctx.strokeStyle='#23392b';ctx.lineWidth=.5;ctx.beginPath();ctx.moveTo(left,yy);ctx.lineTo(width-right+5,yy);ctx.stroke();ctx.fillStyle='#809a87';ctx.fillText(num(price,price<10?5:2),width-right+11,yy);}
    bars.forEach((b,i)=>{const x=left+(i+.5)*step,up=b.close>=b.open;ctx.strokeStyle=up?'#57c99b':'#ef8790';ctx.fillStyle=ctx.strokeStyle;ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(x,y(b.high));ctx.lineTo(x,y(b.low));ctx.stroke();ctx.fillRect(x-Math.max(2,step*.56)/2,Math.min(y(b.open),y(b.close)),Math.max(2,step*.56),Math.max(1,Math.abs(y(b.open)-y(b.close))));});
    const offset=Math.max(0,chartBars.length-bars.length), schoolAnalyses=arr(chart.school_analyses);
    schoolAnalyses.forEach(analysis=>arr(analysis.boundaries).forEach(line=>{
      const indices=arr(line.pivot_indices);if(indices.length<2||!finite(line.current_price)||!finite(line.slope_per_bar))return;
      const globalLast=Math.max(0,Number(line.bar_count)-1),start=Math.max(offset,Math.min(...indices)),end=globalLast;
      if(start>=globalLast||end<offset)return;
      const localStart=start-offset,localEnd=end-offset;
      const startPrice=line.current_price+line.slope_per_bar*(start-globalLast);
      const endPrice=line.current_price;
      ctx.save();ctx.strokeStyle=line.kind==='SUPPORT'?'#56d6bf':'#f0b85b';ctx.lineWidth=2;ctx.setLineDash([5,4]);ctx.globalAlpha=.9;
      ctx.beginPath();ctx.moveTo(left+(localStart+.5)*step,y(startPrice));ctx.lineTo(left+(localEnd+.5)*step,y(endPrice));ctx.stroke();ctx.restore();
    }));
    const levels=[]; cards.forEach((c)=>{arr(c.evidence).forEach((e)=>{const price=first(e.price,e.kind==='horizontal_level'?e.value:undefined);if(finite(price)) levels.push({price,label:tr(e.label||e.kind),color:'#e5ba68'});});const stop=obj(c.stop).price;if(finite(stop))levels.push({price:stop,label:'وقف التنفيذ',color:'#ef8790'});const invalidation=obj(c.invalidation).price;if(finite(invalidation))levels.push({price:invalidation,label:'إبطال التحليل',color:'#e5ba68'});arr(c.targets).forEach((t)=>{if(finite(t.price))levels.push({price:t.price,label:'هدف',color:'#c2f57a'});});});
    const used=new Set();levels.filter((l)=>l.price>low&&l.price<high).slice(0,15).forEach((l)=>{const key=Math.round(y(l.price)/6);if(used.has(key))return;used.add(key);ctx.save();ctx.setLineDash([4,6]);ctx.strokeStyle=l.color;ctx.globalAlpha=.5;ctx.beginPath();ctx.moveTo(left,y(l.price));ctx.lineTo(width-right,y(l.price));ctx.stroke();ctx.setLineDash([]);ctx.globalAlpha=.9;ctx.font='9px Segoe UI';ctx.textAlign='right';ctx.fillStyle=l.color;ctx.fillText(l.label,width-right-5,y(l.price)-7);ctx.restore();});
    ctx.font='9px Segoe UI';ctx.fillStyle='#6d8b75';ctx.textAlign='center';for(let i=0;i<5;i++){const idx=Math.min(bars.length-1,Math.floor(i*(bars.length-1)/4));ctx.fillText(date(bars[idx].time,false).slice(0,5),left+(idx+.5)*step,height-12);}
    chartGeometry={bars,left,step,width};
  }
  const newsSourceNames={
    'federal reserve':'الاحتياطي الفيدرالي','federal reserve board':'مجلس الاحتياطي الفيدرالي','board of governors of the federal reserve system':'مجلس محافظي الاحتياطي الفيدرالي',
    'european central bank':'البنك المركزي الأوروبي','bureau of labor statistics':'مكتب إحصاءات العمل','u.s. bureau of labor statistics':'مكتب إحصاءات العمل الأمريكي',
    'bank of england':'بنك إنجلترا','mt5 economic calendar':'التقويم الاقتصادي للمنصة','synthetic':'مصدر اصطناعي للاختبار'
  };
  const newsCurrencies={USD:'الدولار الأمريكي',EUR:'اليورو',GBP:'الجنيه الإسترليني',JPY:'الين الياباني',CHF:'الفرنك السويسري',CAD:'الدولار الكندي',AUD:'الدولار الأسترالي',NZD:'الدولار النيوزيلندي',CNY:'اليوان الصيني',CNH:'اليوان الصيني الخارجي',SEK:'الكرونة السويدية',NOK:'الكرونة النرويجية',DKK:'الكرونة الدنماركية',HKD:'دولار هونغ كونغ',SGD:'الدولار السنغافوري',MXN:'البيزو المكسيكي',ZAR:'الراند الجنوب أفريقي',TRY:'الليرة التركية',INR:'الروبية الهندية',BRL:'الريال البرازيلي',KRW:'الوون الكوري',XAU:'الذهب',XAG:'الفضة'};
  const calendarEventNames=[
    [/\bnational day\b/i,'عطلة اليوم الوطني'],[/\b(?:bank|public) holiday\b/i,'عطلة رسمية'],[/\bnew year(?:'s)? day\b/i,'عطلة رأس السنة'],[/\bchristmas day\b/i,'عطلة عيد الميلاد'],[/\bthanksgiving day\b/i,'عطلة عيد الشكر'],[/\bindependence day\b/i,'عطلة يوم الاستقلال'],
    [/\bcore retail sales\b/i,'مبيعات التجزئة الأساسية'],[/\bretail sales\b/i,'مبيعات التجزئة'],[/\bmanufacturing pmi\b/i,'مؤشر مديري المشتريات الصناعي'],[/\bservices pmi\b/i,'مؤشر مديري المشتريات الخدمي'],[/\bcomposite pmi\b/i,'مؤشر مديري المشتريات المركب'],[/\b(?:purchasing managers(?:'|’)?) index\b|\bpmi\b/i,'مؤشر مديري المشتريات'],
    [/\bcore (?:consumer price index|cpi)\b/i,'مؤشر أسعار المستهلكين الأساسي'],[/\bconsumer price index\b|\bcpi\b/i,'مؤشر أسعار المستهلكين'],[/\bcore (?:producer price index|ppi)\b/i,'مؤشر أسعار المنتجين الأساسي'],[/\bproducer price index\b|\bppi\b/i,'مؤشر أسعار المنتجين'],[/\bcore pce price index\b/i,'مؤشر أسعار نفقات الاستهلاك الشخصي الأساسي'],[/\bpce price index\b/i,'مؤشر أسعار نفقات الاستهلاك الشخصي'],
    [/\bgross domestic product\b|\bgdp\b/i,'الناتج المحلي الإجمالي'],[/\bnon[- ]?farm payrolls?\b|\bnon[- ]?farm employment change\b/i,'تغير الوظائف غير الزراعية'],[/\bunemployment rate\b/i,'معدل البطالة'],[/\bemployment change\b/i,'تغير التوظيف'],[/\baverage hourly earnings\b/i,'متوسط الأجور في الساعة'],[/\b(?:initial )?jobless claims\b/i,'طلبات إعانة البطالة'],[/\bjolts job openings\b/i,'فرص العمل الشاغرة'],
    [/\binterest rate decision\b|\bofficial bank rate\b|\bfederal funds rate\b|\bmain refinancing rate\b|\bcash rate\b|\bovernight rate\b/i,'قرار سعر الفائدة'],[/\bmonetary policy statement\b/i,'بيان السياسة النقدية'],[/\bmeeting minutes\b/i,'محضر اجتماع السياسة النقدية'],
    [/\bindustrial production\b/i,'الإنتاج الصناعي'],[/\bmanufacturing production\b/i,'الإنتاج الصناعي التحويلي'],[/\btrade balance\b/i,'الميزان التجاري'],[/\bcurrent account\b/i,'الحساب الجاري'],[/\bdurable goods orders\b/i,'طلبات السلع المعمرة'],[/\bfactory orders\b/i,'طلبات المصانع'],[/\bconstruction spending\b/i,'الإنفاق على البناء'],
    [/\bconsumer confidence\b/i,'ثقة المستهلك'],[/\bconsumer sentiment\b/i,'معنويات المستهلك'],[/\bbusiness confidence\b/i,'ثقة الأعمال'],[/\binflation expectations\b/i,'توقعات التضخم'],[/\bpersonal income\b/i,'الدخل الشخصي'],[/\bpersonal spending\b/i,'الإنفاق الشخصي'],
    [/\bnew home sales\b/i,'مبيعات المنازل الجديدة'],[/\bexisting home sales\b/i,'مبيعات المنازل القائمة'],[/\bpending home sales\b/i,'مبيعات المنازل المعلقة'],[/\bhousing starts\b/i,'بدء بناء المنازل'],[/\bbuilding permits\b/i,'تصاريح البناء'],[/\bhome price index\b/i,'مؤشر أسعار المنازل'],
    [/\bcrude oil inventories\b/i,'مخزونات النفط الخام'],[/\bnatural gas storage\b/i,'مخزونات الغاز الطبيعي'],[/\bcapacity utilization\b/i,'معدل استغلال الطاقة الإنتاجية'],[/\bbusiness inventories\b/i,'مخزونات الأعمال'],[/\bwholesale inventories\b/i,'مخزونات الجملة'],
    [/\b(?:speech|speaks|testifies)\b/i,'تصريحات لمسؤول اقتصادي'],[/\bbond auction\b|\bnote auction\b/i,'مزاد أدوات دين حكومية']
  ];
  const hasUntranslatedNewsWords=(value)=>/[A-Za-z]{2,}/.test(String(value??'').replace(/https?:\/\/\S+/gi,' ').replace(/\b(?:Quant Trading AI|MT5|RSS|XML|UTC|GMT|USD|EUR|GBP|JPY|CHF|CAD|AUD|NZD|CNY|CNH|SEK|NOK|DKK|HKD|SGD|MXN|ZAR|TRY|INR|BRL|KRW|XAU|XAG)\b/g,' '));
  function newsArabicText(value,fallback='غير متاح') {const rendered=plain(value);return isEnglish()||!hasUntranslatedNewsWords(rendered)?rendered:fallback;}
  function newsSourceName(value) {if(isEnglish())return plain(value);const raw=String(value??'').trim(),known=newsSourceNames[raw.toLowerCase()];if(known)return known;return newsArabicText(raw||'مصدر غير مسمى','مصدر أخبار رسمي');}
  function newsCurrency(value) {if(isEnglish())return plain(value);const code=String(value??'').trim().toUpperCase();return code?newsCurrencies[code]||'عملة مرتبطة بالحدث':'عملة غير محددة';}
  function newsAssets(value) {const values=Array.isArray(value)?value:value?[value]:[];return values.length?values.map(newsCurrency).join('، '):'أصول غير محددة';}
  function newsTimezone(value) {if(isEnglish())return plain(value);const zone=String(value??'').trim().toUpperCase();return ({UTC:'التوقيت العالمي',GMT:'توقيت غرينتش',UNKNOWN:'غير معروفة'})[zone]||newsArabicText(value,'منطقة زمنية خارجية');}
  function newsStatusText(value) {if(isEnglish())return plain(value);const code=String(value??'UNKNOWN').trim().toUpperCase(),known={SUCCESS:'متاح',FAILED:'تعذر الوصول',FAILURE:'تعذر الوصول',TIMEOUT:'انتهت مهلة الاتصال',REFRESHING:'جارٍ التحديث'}[code];return known||newsArabicText(tr(code),'حالة غير معروفة');}
  function newsBadge(value) {return `<span class="mini-pill ${cls(value)}">${h(newsStatusText(value))}</span>`;}
  function newsMetric(value) {if(value===undefined||value===null||value==='')return '—';if(typeof value==='number')return String(value);if(isEnglish())return plain(value);const raw=String(value).trim();if(/^(?:n\/?a|none|null|unknown)$/i.test(raw))return '—';const scaled=raw.match(/^([+\-]?\d+(?:[.,]\d+)?)\s*([KMBT])(%?)$/i);if(scaled){const unit={K:'ألف',M:'مليون',B:'مليار',T:'تريليون'}[scaled[2].toUpperCase()];return `${scaled[1]} ${unit}${scaled[3]}`;}return /[A-Za-z]/.test(raw)?'—':raw;}
  function calendarImportance(value) {if(isEnglish())return plain(value);const key=typeof value==='number'?String(value):String(value??'').trim().toUpperCase();return ({0:'الأهمية غير محددة',1:'أهمية منخفضة',2:'أهمية متوسطة',3:'أهمية مرتفعة',NONE:'الأهمية غير محددة',LOW:'أهمية منخفضة',MEDIUM:'أهمية متوسطة',MODERATE:'أهمية متوسطة',HIGH:'أهمية مرتفعة'})[key]||'الأهمية غير محددة';}
  function calendarEventName(value,currency) {
    if(isEnglish())return plain(value);
    const raw=String(value??'').trim();if(!hasUntranslatedNewsWords(raw))return plain(raw||'حدث اقتصادي');
    const match=calendarEventNames.find(([pattern])=>pattern.test(raw));
    if(!match)return `حدث اقتصادي رسمي مرتبط بعملة ${newsCurrency(currency)}`;
    const qualifiers=[];
    if(/\b(?:flash|prelim(?:inary)?)\b/i.test(raw))qualifiers.push('قراءة أولية');else if(/\bfinal\b/i.test(raw))qualifiers.push('قراءة نهائية');else if(/\brevised\b/i.test(raw))qualifiers.push('قراءة مراجعة');
    if(/\b(?:ex(?:cluding)?\s+auto(?:s|mobiles?)?|excluding vehicles)\b/i.test(raw))qualifiers.push('باستثناء السيارات');
    if(/\bm\/m\b|month[- ]on[- ]month/i.test(raw))qualifiers.push('تغير شهري');else if(/\bq\/q\b|quarter[- ]on[- ]quarter/i.test(raw))qualifiers.push('تغير ربع سنوي');else if(/\by\/y\b|year[- ]on[- ]year/i.test(raw))qualifiers.push('تغير سنوي');
    return `${match[1]}${qualifiers.length?` — ${qualifiers.join('، ')}`:''}`;
  }
  function newsCoverageText(value) {
    if(!value||typeof value!=='object'||Array.isArray(value))return newsArabicText(value,'تفاصيل التغطية غير متاحة بالعربية.');
    if(isEnglish())return plain(value);
    return Object.entries(value).map(([key,item],index)=>`${extraFieldLabels[key]||fieldLabel(key)!==key?extraFieldLabels[key]||fieldLabel(key):`تفصيل التغطية ${index+1}`}: ${typeof item==='object'&&item!==null?newsCoverageText(item):newsArabicText(item,'غير متحقق')}`).join(' · ');
  }
  function renderNews() {
    const n=obj(state.news),sources=arr(n.sources),items=arr(n.items).map((x)=>({...x,freshness:first(x.freshness,x.status,x.source_fresh===false?'SOURCE_STALE':x.fresh===true?'FRESH':x.fresh===false?'STALE':'UNKNOWN'),original_url:first(x.original_url,x.source_url,x.url),expected:first(x.expected,x.forecast),revisions:first(x.revisions,x.revision)})),calendar=(Array.isArray(n.calendar)?n.calendar:arr(obj(n.calendar).events)).map((e)=>({...e,time:first(e.time,e.time_utc),source:first(e.source,e.provider,obj(n.calendar).provider),revised:first(e.revised,e.revised_previous),url:first(e.original_url,e.source_url,e.url)}));
    const coverage=n.coverage;const calendarState=obj(n.calendar);set('news-coverage',`${coverage&&Object.keys(obj(coverage)).length?newsCoverageText(coverage):'لم تُتحقق تغطية الأخبار. غياب الخبر لا يعني غياب الحدث؛ القرار يحتاج مصادره المطلوبة قبل الدخول.'}${calendarState.known===false?' التقويم المطلوب غير متحقق؛ ثبّت جسر القراءة وأضفه إلى شارت في MT5.':calendarState.as_of?` آخر فحص للتقويم: ${date(calendarState.as_of)}.`:''}`);
    $('news-sources').innerHTML=sources.length?sources.map((s)=>`<div class="source-card"><div class="source-card-head"><h3>${h(newsSourceName(first(s.name,s.id,'مصدر')))}</h3>${newsBadge(first(s.status,s.available===true?'AVAILABLE':s.available===false?'UNAVAILABLE':'UNKNOWN'))}</div><p>${h(newsArabicText(first(s.coverage,s.description,s.reason),'تفاصيل المصدر بلغة خارجية؛ راجع الرابط الأصلي.'))}</p><small>آخر وصول: ${h(date(first(s.received_at,s.last_success,s.last_checked,s.fetched_at)))}<br>الحداثة: ${h(newsArabicText(first(s.freshness,s.fresh===true?'حديث':s.fresh===false?'قديم أو غير متاح':undefined,s.updated_at?date(s.updated_at):undefined),'الحداثة غير متحققة'))}<br>شروط الاستخدام: ${h(newsArabicText(first(s.terms_status,s.terms),'شروط الاستخدام متاحة في رابط المصدر الأصلي.'))}</small>${safeLink(first(s.url,s.original_url),'المصدر الأصلي ←')}</div>`).join(''):empty('لا توجد مصادر أخبار متحققة.','تظهر المصادر المتاحة وحالات العطل وحدود التغطية عند الاتصال.');
    set('news-count',`${items.length} واقعة`);
    $('news-items').innerHTML=items.length?items.map((x)=>{const sourceName=newsSourceName(first(x.source,x.source_name,'مصدر غير مسمى')),headline=newsArabicText(first(x.title,x.headline,'خبر بلا عنوان'),`بيان رسمي جديد من ${sourceName}`);return `<article class="news-item"><h3>${h(headline)}</h3><div class="news-meta"><span>${h(sourceName)}</span>${safeLink(first(x.original_url,x.url),'الرابط الأصلي ↗')}<span>${h(newsAssets(first(x.assets,x.symbols)))}</span>${newsBadge(first(x.freshness,x.status,'UNKNOWN'))}</div><p class="facts">${h(newsArabicText(first(x.facts,x.summary,x.text),'تفاصيل البيان منشورة في رابط المصدر الأصلي.'))}</p><div class="effect"><b>تفسير الأثر المحتمل</b>${h(newsArabicText(first(x.interpretation,x.potential_effect,x.effect,'لا يوجد تفسير معتمد.'),'لم يُعتمد تفسير عربي للأثر؛ لا يُستنتج الاتجاه من العنوان.'))}</div><details><summary>التوقيت والمصدر والقيَم</summary><div class="detail-grid">${[['الحدث',date(x.event_time)],['النشر',date(first(x.published_at,x.publication_time))],['الاستلام',date(first(x.received_at,x.received_time))],['منطقة المصدر الزمنية',newsTimezone(x.timezone)],['مزود البيانات',newsSourceName(x.provider)],['السابق',newsMetric(x.previous)],['المتوقع',newsMetric(x.expected)],['الفعلي',newsMetric(x.actual)],['المراجعات',newsMetric(x.revisions)]].map(([k,v])=>`<div class="detail-item"><span>${h(k)}</span><b>${h(v)}</b></div>`).join('')}</div></details></article>`;}).join(''):empty('لا توجد وقائع مستلمة.','هذا لا يثبت غياب أحداث اقتصادية أو سياسية.');
    $('calendar-items').innerHTML=calendar.length?calendar.map((x)=>`<article class="calendar-item"><h3>${h(calendarEventName(first(x.name,x.title,x.event,'حدث اقتصادي'),x.currency))}</h3><small>${h(date(first(x.time,x.event_time)))} · ${h(newsCurrency(first(x.currency,x.country,'')))} · ${h(calendarImportance(first(x.importance,x.impact)))}</small><div class="calendar-values">${[['السابق',x.previous],['المتوقع',first(x.expected,x.forecast)],['الفعلي',x.actual]].map(([k,v])=>`<div><span>${h(k)}</span>${h(newsMetric(v))}</div>`).join('')}</div><div class="news-meta"><span>المراجعة: ${h(newsMetric(x.revised))}</span><span>${h(newsSourceName(first(x.source,'')))}</span>${safeLink(x.url,'المصدر ↗')}</div></article>`).join(''):empty('الجدول الاقتصادي غير متاح.','لا يُملأ بتوقعات أو أحداث مصطنعة.');
    renderExternalResearch(n.external_research);
    renderLLMResearch(state.llm_research);
  }
  function renderExternalResearch(value) {
    const data=obj(value),providers=arr(data.providers),items=arr(data.items);
    const labels={massive_fx:'Massive · بيانات فوركس تاريخية',frankfurter:'Frankfurter · سعر صرف يومي',bls_cpi:'BLS · التضخم الأمريكي',world_bank_gdp:'World Bank · النمو الاقتصادي'};
    const status={OK:'متاح',ERROR:'تعذر الجلب',CONFIG_REQUIRED:'مفتاح API مطلوب'};
    set('external-research-status',`${data.refreshing?'جارٍ جلب المصادر…':data.last_refresh?`آخر جلب: ${date(data.last_refresh)}`:'لم تُجلب البيانات بعد'} · استخدام تنفيذي: لا شيء؛ أسعار وأوامر MT5 هي المرجع.`);
    $('external-research-providers').innerHTML=providers.length?providers.map((p)=>`<div class="source-card"><div class="source-card-head"><h3>${h(labels[p.id]||p.name||p.id||'مصدر')}</h3>${newsBadge(status[p.status]||p.status||'UNKNOWN')}</div><p>${h(newsArabicText(p.coverage||p.reason,'بيانات بحثية خارجية'))}</p><small>آخر استلام: ${h(date(p.received_at))}<br>الحداثة: ${p.fresh===true?'حديث بحسب سياسة المصدر':p.status==='OK'?'قديم':'غير متاح'}</small>${safeLink(p.url,'التوثيق الأصلي ↗')}</div>`).join(''):empty('لا توجد قراءة محفوظة.','اضغط تحديث المصادر لجلب البيانات العامة وإظهار حالة Massive.');
    $('external-research-items').innerHTML=items.length?items.map((item)=>{
      let detail='';
      if(item.kind==='forex_daily_bars'){const bars=arr(item.bars),last=bars[bars.length-1];detail=`${h(item.symbol||'')} · ${bars.length} شمعة يومية · آخر إغلاق: ${h(last?last.close:'—')} · المصدر يسجل عروض أسعار Bid.`;}
      else if(item.kind==='reference_fx_rate')detail=`${h(item.base||'')} / ${h(item.quote||'')} = ${h(item.rate)} · تاريخ الرصد: ${h(item.observation_date||'—')} · سعر يومي مرجعي.`;
      else detail=`${h(item.name||item.series_id||'مؤشر اقتصادي')} · ${h(item.value)} · الفترة: ${h(item.period||item.observation_date||item.year||'—')}`;
      return `<article class="panel"><h3>${h(labels[item.provider]||item.provider||'مصدر')}</h3><p>${detail}</p><small>وقت استلام NEXUS: ${h(date(item.observed_at))}</small></article>`;
    }).join(''):'';
  }
  function renderLLMResearch(value) {
    const data=obj(value),providers=arr(data.providers),results=arr(data.results);
    const labels={READY:'جاهز',CONFIG_REQUIRED:'يحتاج مفتاح ونموذج',OK:'تم التحليل',ERROR:'تعذر التحليل'};
    set('llm-research-status',`${data.refreshing?'يجري التحليل…':data.last_run?`آخر تحليل: ${date(data.last_run)}`:'لم يُشغّل التحليل'} · صلاحية التنفيذ: لا شيء.`);
    $('llm-research-providers').innerHTML=providers.length?providers.map((p)=>`<div class="source-card"><div class="source-card-head"><h3>${h(p.name||p.id||'موفّر')}</h3>${newsBadge(labels[p.status]||p.status||'غير معروف')}</div><p>${h(p.model||'اضبط اسم النموذج ومفتاحه في متغيرات البيئة.')}</p></div>`).join(''):empty('لا توجد موفّرات.','اضبط مفاتيح API وأسماء النماذج اختيارياً ثم أعد فتح التطبيق.');
    $('llm-research-results').innerHTML=results.length?results.map((r)=>{const result=obj(r.result);return `<article class="panel"><div class="panel-heading"><h3>${h(r.name||r.provider||'موفّر')}</h3>${newsBadge(labels[r.status]||r.status||'غير معروف')}</div><small>${h(r.model||'')}</small>${r.reason?`<p>${h(r.reason)}</p>`:''}${result.assessment?`<p>${h(result.assessment)}</p>`:''}${arr(result.observations).length?`<ul>${arr(result.observations).map((x)=>`<li>${h(x)}</li>`).join('')}</ul>`:''}${arr(result.limitations).length?`<p class="muted">حدود القراءة: ${arr(result.limitations).map((x)=>h(x)).join(' · ')}</p>`:''}<small>الصلاحية: بحث ظلي فقط · ${h(date(r.received_at))}</small></article>`;}).join(''):'';
  }
  function safeLink(url,label) {if(typeof url!=='string')return '';try{const parsed=new URL(url);if(!['http:','https:'].includes(parsed.protocol))return '';return `<a href="${h(parsed.href)}" target="_blank" rel="noopener noreferrer">${h(label)}</a>`;}catch(_){return '';}}
  function table(columns,data,none) {if(!data.length)return empty(none);return `<table><thead><tr>${columns.map(([label])=>`<th>${h(label)}</th>`).join('')}</tr></thead><tbody>${data.map((r)=>`<tr>${columns.map(([,value])=>`<td>${value(r)}</td>`).join('')}</tr>`).join('')}</tbody></table>`;}
  const ownership=(x)=>x.owned===false||x.external===true?'خارجية — للرقابة فقط':x.owned===true||x.nexus_owned===true?'للمنظومة':'ملكية تُحدد من المحرك';
  function renderPositions() {
    const positions=arr(state.positions),orders=arr(state.orders),intents=arr(state.intents).map((x)=>{const p=obj(x.payload),proposal=obj(p.proposal),request=obj(p.request);return {...proposal,...request,...x,symbol:first(x.symbol,proposal.symbol,request.symbol),side:first(x.side,proposal.side,request.side),volume:first(x.volume,request.volume),status:first(x.status,x.state),reserved_risk:first(x.reserved_risk,x.reserved),reason:first(x.reason,p.reason,p.error,p.message),updated_at:first(x.updated_at,x.updated),created_at:first(x.created_at,x.created)};});
    const pending=state.mode==='MANUAL_DEMO'?[...intents.filter((x)=>['PROPOSED','PENDING_APPROVAL'].includes(x.status)),...opportunities().filter((x)=>x.proposal&&!x.attempted&&!intents.some((i)=>i.id===x.intent_id)).map((x)=>({...x.proposal,id:x.intent_id,reason:first(x.proposal.reason,x.reasons),status:'PENDING_APPROVAL'}))]:[];
    $('pending-approval-panel').hidden=pending.length===0;
    $('pending-intents').innerHTML=pending.length?pending.map((x)=>`<div class="intent-item"><div><h3><span class="symbol-name">${h(x.symbol)}</span> · ${h(tr(first(x.side,x.direction)))} · ${num(x.volume,3)} لوت</h3><p>${h(plain(first(x.reason,x.explanation)))}<br>المخاطرة: ${money(first(x.risk_amount,x.risk))} · الصلاحية: ${h(date(x.expires_at))}<br>هوية النية: <span dir="ltr">${h(x.id||x.intent_id)}</span></p></div><button class="button primary" data-approve="${h(x.id||x.intent_id)}">اعتماد النية</button></div>`).join(''):empty('لا توجد نيات تنتظر الموافقة.','تظهر هنا فقط في وضع الموافقة اليدوية.');
    $('positions-table').innerHTML=table([['رقم الوسيط',(x)=>h(x.ticket)],['الرمز',(x)=>`<span class="symbol-name">${h(x.symbol)}</span>`],['الاتجاه',(x)=>h(tr(first(x.side,x.direction,x.type===0?'BUY':x.type===1?'SELL':undefined)))],['الحجم',(x)=>num(x.volume,3)],['الدخول',(x)=>num(first(x.price_open,x.entry),6)],['السعر الحالي',(x)=>num(first(x.price_current,x.price),6)],['الوقف / الهدف',(x)=>`${num(x.sl,6)} / ${num(x.tp,6)}`],['الربح العائم',(x)=>`<span class="${x.profit<0?'negative':'positive'}">${money(x.profit)}</span>`],['التبييت',(x)=>money(x.swap)],['الملكية',(x)=>h(ownership(x))],['خطة الإدارة',(x)=>h(plain(first(x.management_reason,x.plan,x.comment)))]],positions,'لا توجد مراكز مفتوحة مستلمة.');
    $('orders-table').innerHTML=table([['رقم الوسيط',(x)=>h(x.ticket)],['الرمز',(x)=>h(x.symbol)],['نوع الأمر',(x)=>h(tr(first(x.side,x.direction,x.type)))],['الحجم',(x)=>num(first(x.volume_current,x.volume),3)],['سعر الأمر',(x)=>num(first(x.price_open,x.price),6)],['الحالة',(x)=>badge(first(x.status,x.state,'UNKNOWN'))],['الملكية',(x)=>h(ownership(x))],['وقت الإنشاء',(x)=>h(date(first(x.time_setup,x.time)))]],orders,'لا توجد أوامر معلقة مستلمة.');
    const sessionRows=window.QuantSessionView?window.QuantSessionView.select(intents,Date.now()/1000):{rows:intents,older:0,omitted:0};
    const archivedIntents=sessionRows.older+sessionRows.omitted+Math.max(0,Number(state.intents_omitted)||0);
    set('intents-session-note',isEnglish()?`Day starts at 02:00 Dubai · ${sessionRows.rows.length} shown · ${archivedIntents} archived`: `يبدأ اليوم 02:00 دبي · المعروض ${sessionRows.rows.length} · المؤرشف ${archivedIntents}`);
    $('intents-table').innerHTML=table([['هوية النية',(x)=>`<span dir="ltr" title="${h(x.id||x.intent_id)}">${h(String(x.id||x.intent_id||'—').slice(0,18))}</span>`],['الرمز',(x)=>h(x.symbol)],['الاتجاه',(x)=>h(tr(first(x.side,x.direction)))],['الحالة',(x)=>badge(first(x.status,'UNKNOWN'))],['المخاطرة',(x)=>money(first(x.risk_amount,x.reserved_risk))],['سبب القرار / النتيجة',(x)=>h(plain(first(x.reason,x.error,x.message)))],['آخر تحديث',(x)=>h(date(first(x.updated_at,x.created_at,x.time)))]],sessionRows.rows,'لا توجد نيات تداول مسجلة.');
  }
  function renderPerformance() {
    const p=obj(state.performance),strategyRows=arr(first(p.rows,p.by_strategy)),assetRows=arr(p.by_asset);
    const all=[...strategyRows,...assetRows].filter(x=>Number(first(x.closed_deals,x.trades,x.count,0))>0||
      ['gross','realized_pnl','gross_pnl','profit','costs','net_pnl','net','drawdown'].some(k=>finite(x[k])&&Number(x[k])!==0));
    set('performance-label',p.source==='DEMO_SERVICE_20261019'?(p.trades===null?'بانتظار سجل المنفّذ':p.complete?'المنفّذ التجريبي • سجل الوسيط':'المنفّذ التجريبي • سجل جزئي'):state.simulation?'نتائج محاكاة اصطناعية':'نتائج الوسيط المؤكدة فقط');$('performance-label').className=`pill ${state.simulation?'amber':'neutral'}`;
    $('performance-metrics').innerHTML=[['صفقات مكتملة',first(p.trades,p.closed_trades)],['صافي محقق',first(p.net_realized,p.realized_net)],['تكاليف',p.costs],['أقصى تراجع',p.max_drawdown]].map(([label,value],i)=>`<div class="scan-metric"><strong>${i===0?num(value,0):money(value)}</strong><span>${label}</span></div>`).join('');
    $('performance-table').innerHTML=table([['الاستراتيجية',(x)=>h(schoolName(first(x.school,x.strategy,x.name,'—')))],['الأصل',(x)=>h(x.symbol||'—')],['عمليات الخروج',(x)=>num(first(x.closed_deals,x.trades,x.count),0)],['المحقق قبل التكاليف',(x)=>money(first(x.gross,x.realized_pnl,x.gross_pnl,x.profit))],['التكاليف الموقعة',(x)=>money(x.costs)],['الصافي',(x)=>money(first(x.net_pnl,x.net))],['التراجع',(x)=>money(x.drawdown)],['نوع النتائج',(x)=>h(x.simulation===true?'محاكاة':state.simulation?'محاكاة':first(x.validation,'سجل الوسيط'))]],all,'لا توجد نتائج كافية لتقييم الأداء.');
    const coverage=Array.isArray(state.coverage)?state.coverage:arr(first(obj(state.coverage).schools,obj(state.coverage).items,obj(state.coverage).strategies));
    $('coverage-list').innerHTML=coverage.length?coverage.map((c)=>{
      const definition=obj(obj(c.contract).definition),id=first(c.id,c.strategy),cards=arr(state.cards).filter(x=>first(x.strategy_id,x.id)===id),counts={...obj(obj(state.card_activity_by_strategy)[id])};
      if(!Object.keys(counts).length)cards.forEach(x=>{const key=x.status||'UNKNOWN';counts[key]=(counts[key]||0)+1;});
      const activity=Object.entries(counts).map(([key,n])=>`${tr(key)}: ${n}`).join(' · ');
      const scope=isEnglish()?definition.scope:definition.scope_ar;
      const rules=isEnglish()?definition.rules:definition.rules_ar;
      return `<article class="coverage-card">${badge(first(c.coverage,c.status,'UNKNOWN'))}<h3>${h(schoolName(first(c.school,c.name,c.id,'وظيفة')))}</h3><p>${h(plain(c.data_requirements))}</p>${scope?`<p>${h(scope)}</p>`:''}<p><strong>${h(uiText('حالة التحليل الحالية'))}</strong><br>${h(activity||uiText('لم يبدأ تحليل هذا النموذج بعد'))}</p>${arr(rules).length?`<details><summary>${h(uiText('قواعد النموذج'))}</summary><p>${arr(rules).map(h).join('<br>')}</p></details>`:''}<small>${h(uiText('إصدار'))}: ${h(c.version||'—')}</small></article>`;
    }).join(''):empty('بيان التغطية غير مستلم.','لا يعني غياب البيان اكتمال المدارس أو الوظائف.');
    const quantRows=arr(state.quant_results);
    if(quantRows.length){$('quant-summary').className='';$('quant-summary').innerHTML=`<div class="notice">النتائج تقيس استراتيجيات ثابتة على عينات زمنية خارج التدريب وبعد التكاليف. وحدة المخاطرة تساوي مسافة وقف واحدة، وليست ربحًا بعملة الحساب. نتيجة البحث لا تمنح التنفيذ تلقائيًا.</div><div class="table-scroll">${table([['الاستراتيجية',(q)=>h(schoolName(q.school||q.strategy_id))],['الرمز والفريم',(q)=>h(`${q.symbol} · ${q.timeframe}`)],['نوع البيانات',(q)=>h(q.data_kind==='broker'||q.data_kind==='broker_verified'?'الوسيط':'اصطناعية أو غير متحققة')],['التأهيل',(q)=>badge(q.qualified?'مؤهل للبحث التجريبي':q.status||'REJECTED')],['صفقات الاختبار',(q)=>num(obj(q.metrics).trades,0)],['معامل الربح',(q)=>num(obj(q.metrics).profit_factor,2)],['العائد المتوقع بوحدة المخاطرة',(q)=>num(obj(q.metrics).expectancy_r,3)],['التراجع بوحدة المخاطرة',(q)=>num(obj(q.metrics).max_drawdown_r,2)],['الأسباب والحدود',(q)=>h(plain(q.reasons))]],quantRows,'لا توجد نتائج.')}</div>`;}
    else{const quant=first(p.quantitative,p.quant,state.quant);$('quant-summary').className=quant?'':'empty compact';$('quant-summary').textContent=quant?plain(quant):'لم تُستلم نتائج تحقق كمي مؤهلة. لا تُعرض جودة القواعد بوصفها احتمال نجاح.';}
  }
  // Catalog strings are authored independently in both languages. Select the
  // requested field directly; translated fallback prose is not a rule reference.
  const knowledgeField=(value,key)=>first(value[`${key}_${language()}`],uiText('لم يكتمل وصف هذا المرجع باللغة المختارة.'));
  const knowledgeCategory=(value)=>uiText({technical:'التحليل الفني',fundamental:'التحليل الأساسي',approach:'مناهج التقييم والتحليل'}[value]||'فئة غير معروفة');
  const knowledgeList=(values,records=[])=>arr(values).length?`<ul>${arr(values).map((v,i)=>{const label={SOURCE_PRINCIPLE:'مبدأ من المصدر',OPERATIONAL_CHECKLIST:'قائمة تحقق تشغيلية',HOUSE_DEFINITION:'تعريف حسابي محلي'}[records[i]?.kind];return `<li>${label?`<small class="knowledge-rule-kind">${h(uiText(label))}</small>`:''}${h(v)}</li>`;}).join('')}</ul>`:empty('لا توجد قواعد محفوظة لهذا القسم.');
  const knowledgeExpanded=new Set();let knowledgeMarkup='';
  function renderKnowledge() {
    const k=obj(state.knowledge),learning=obj(state.learning),schools=arr(k.schools),lookup=new Map(schools.map(s=>[s.id,s]));
    const rules=schools.reduce((total,s)=>total+arr(s.rules_en).length,0),modelIds=new Set(schools.flatMap(s=>arr(s.strategy_ids)));
    $('knowledge-summary').innerHTML=[['المدارس والمناهج',schools.length],['القواعد المرجعية',rules],['نماذج مرتبطة بالكود',modelIds.size],['إصدارات القواعد المحفوظة',learning.stored_versions]].map(([label,value])=>`<div class="scan-metric"><strong>${num(value,0)}</strong><span>${h(uiText(label))}</span></div>`).join('');
    set('knowledge-policy',k.error ? uiText('تعذر تحميل المرجع؛ راجع تقرير التشخيص.') : '');
    const query=String($('knowledge-search').value||'').trim().toLocaleLowerCase(),category=$('knowledge-filter').value||'all';
    const filtered=schools.filter(s=>(category==='all'||s.category===category)&&(!query||[knowledgeField(s,'name'),...arr(s[`rules_${language()}`]),...arr(s[`requirements_${language()}`]),knowledgeField(s,'scope')].join(' ').toLocaleLowerCase().includes(query)));
    set('knowledge-count',isEnglish()?`${filtered.length} of ${schools.length} references · version ${k.catalog_version||'—'}`:`${filtered.length} من ${schools.length} مرجع · الإصدار ${k.catalog_version||'—'}`);
    const coverage=arr(state.coverage),seenCards=new Set(),cards=[...arr(state.cards),...arr(obj(state.chart).cards)].filter(c=>{const key=[c.strategy_id,c.symbol,c.timeframe].join('|');if(seenCards.has(key))return false;seenCards.add(key);return true;});
    const catalogMarkup=filtered.length?filtered.map(s=>{
      const linked=arr(s.strategy_ids),alias=lookup.get(s.alias_of),requirements=arr(s[`requirements_${language()}`]),related=arr(s.related_ids).map(id=>lookup.get(id)).filter(Boolean);
      const runtimeScope=knowledgeField(s,'runtime_scope');
      const calculatorName=id=>uiText({pv:'القيمة الحالية',dcf:'التدفقات النقدية المخصومة',ddm:'خصم الأرباح',nav:'صافي الأصول',multiples:'المضاعفات المالية',bond:'تسعير السند'}[id]||'نموذج مالي غير معروف');
      const runtime=linked.map(id=>{
        const c=coverage.find(x=>first(x.id,x.strategy_id,x.strategy)===id),definition=obj(obj(c?.contract).definition),states={...obj(obj(state.card_activity_by_strategy)[id])};
        if(!Object.keys(states).length)cards.filter(x=>first(x.strategy_id,x.strategy,x.id)===id).forEach(x=>{const status=x.status||'UNKNOWN';states[status]=(states[status]||0)+1;});
        const activity=Object.entries(states).map(([status,n])=>`${tr(status)}: ${n}`).join(' · ');
        return `<div class="knowledge-runtime"><strong>${h(schoolName(first(c?.school,c?.name,id)))}</strong><span>${h(activity||uiText('لم يبدأ تحليل هذا النموذج بعد'))}</span></div>`;
      }).join('')+(runtimeScope?`<p class="tiny-note">${h(runtimeScope)}</p>`:'')+(arr(s.available_calculators).length?`<p class="tiny-note">${h(uiText('حاسبات محلية متاحة'))}: ${arr(s.available_calculators).map(id=>h(calculatorName(id))).join(' · ')}</p>`:'');
      const referenceLinks=arr(s.references).map(r=>{
        const label=isEnglish()?first(r.title,'Reference'):uiText('المصدر المرجعي ↗');
        return `<li>${safeLink(r.url,label)}${r[`scope_${language()}`]?`<small>${h(r[`scope_${language()}`])}</small>`:''}</li>`;
      }).join('');
      return `<article class="knowledge-card"><div class="knowledge-card-heading"><span class="mini-pill">${h(knowledgeCategory(s.category))}</span><span class="knowledge-order">${num(s.order,0)}</span></div><h3>${h(knowledgeField(s,'name'))}</h3>${alias?`<p class="tiny-note">${h(uiText('تسمية مرتبطة بمرجع آخر'))}: ${h(knowledgeField(alias,'name'))}</p>`:''}${related.length?`<p class="tiny-note">${h(uiText('مراجع ذات صلة'))}: ${related.map(school=>h(knowledgeField(school,'name'))).join(' · ')}</p>`:''}<details class="knowledge-models"><summary>${h(uiText('النماذج البرمجية المرتبطة'))}</summary>${runtime||`<p>${h(uiText('مرجع محفوظ؛ لا يوجد نموذج تداول مرتبط حاليًا.'))}</p>`}</details>${s.category!=='technical'&&!linked.length?`<details><summary>${h(uiText('البيانات المطلوبة'))}</summary><p class="knowledge-data-note">${h(uiText('القوائم المالية والتدفقات النقدية وتوقعات الشركات وبيانات القطاع غير متاحة من شموع المنصة وحدها. القواعد محفوظة كمرجع ولا تصدر توصية تنفيذ دون بياناتها.'))}</p></details>`:''}<details data-knowledge-details="${h(s.id)}"${knowledgeExpanded.has(s.id)?' open':''}><summary>${h(uiText('عرض القواعد والاستثناءات والبيانات'))}</summary><p>${h(knowledgeField(s,'scope'))}</p><h4>${h(uiText('القواعد المرجعية'))}</h4>${knowledgeList(s[`rules_${language()}`],arr(s.rule_records))}<h4>${h(uiText('الاستثناءات وحدود التفسير'))}</h4>${knowledgeList(s[`exceptions_${language()}`])}<h4>${h(uiText('البيانات المطلوبة'))}</h4>${knowledgeList(requirements)}${s.rule_protocol?`<h4>${h(uiText('آلية تطبيق القواعد ومراجعتها'))} · ${h(s.rule_protocol.version||'—')}</h4>${knowledgeList(s.rule_protocol[`summary_${language()}`])}`:''}${referenceLinks?`<h4>${h(uiText('المراجع الأصلية'))}</h4><ul class="knowledge-references">${referenceLinks}</ul>`:''}</details></article>`;
    }).join(''):empty('لا توجد مراجع بهذه التصفية.','تظهر المكتبة المحفوظة بعد تحميل الخدمة المحلية.');
    if(catalogMarkup!==knowledgeMarkup){$('knowledge-schools').innerHTML=catalogMarkup;knowledgeMarkup=catalogMarkup;}
    const stats=[['ملاحظات تطبيق القواعد',learning.observations],['نتائج مكتملة محفوظة',learning.closed_records],['نتائج صالحة للتعلم',learning.eligible_records],['نتائج مستبعدة',learning.excluded_records]];
    $('learning-summary').innerHTML=stats.map(([label,value])=>`<div class="scan-metric"><strong>${num(value,0)}</strong><span>${h(uiText(label))}</span></div>`).join('');
    set('learning-mode',learning.mode==='OBSERVATIONAL'?'تعلم بالملاحظة':'حالة التعلم غير متاحة');
    set('learning-policy',learning.error ? uiText('تعذر تقييم سجل التعلم؛ راجع تقرير التشخيص.') : isEnglish()?`Each rule version retains its observations and confirmed closed-trade outcomes. Research review requires at least ${learning.minimum_samples||40} eligible outcomes and ${learning.holdout_minimum||12} later holdout outcomes. Current learning stores evidence and research candidates; it does not change trading rules, live weights or risk limits automatically.`:`يحتفظ كل إصدار من القاعدة بملاحظاته ونتائج الصفقات المكتملة المؤكدة. تتطلب المراجعة البحثية ${learning.minimum_samples||40} نتيجة صالحة على الأقل و${learning.holdout_minimum||12} نتيجة لاحقة خارج عينة التقييم. التعلم الحالي يحفظ الأدلة والمرشحين للبحث؛ لا يغير قواعد التداول أو الأوزان الحية أو حدود المخاطرة تلقائيًا.`);
    const memoryFile=obj(learning.persistence);
    set('learning-persistence',memoryFile.ok===true?uiText('ملف حالة التعلم محفوظ محليًا ويُرفق بتصدير المعرفة والتشخيص. قاعدة البيانات تحفظ التاريخ الكامل؛ الخسارة حالة للمراجعة وليست دليلًا تلقائيًا على خطأ القاعدة.'):memoryFile.ok===false?uiText('تعذر حفظ ملف حالة التعلم؛ تبقى قاعدة البيانات مرجعًا، وراجع تقرير التشخيص.'):uiText('يظهر تأكيد حفظ ملف التعلم بعد اكتمال تحديث سجل الوسيط.'));
    const learningStatus=value=>uiText({INSUFFICIENT:'عينة غير كافية',REVIEW_DETERIORATION:'مراجعة تراجع النتائج',CANDIDATE_RESEARCH:'مرشح للبحث',MIXED_EVIDENCE:'أدلة متباينة'}[value]||'حالة التعلم غير متاحة');
    const regimeName=value=>uiText({trend:'اتجاه',range:'نطاق',volatile:'تقلب مرتفع',unknown:'غير معروف',TREND:'اتجاه',RANGE:'نطاق',VOLATILE:'تقلب مرتفع',UNKNOWN:'غير معروف'}[value]||'غير معروف');
    $('learning-models').innerHTML=table([['النموذج وإصدار القاعدة',x=>`${h(schoolName(x.strategy_id))}<small class="knowledge-revision">${h(uiText('إصدار'))}: ${h(x.revision||'—')}</small>`],['الرمز والفريم',x=>h(`${x.symbol||'—'} · ${x.timeframe||'—'}`)],['حالة السوق',x=>h(regimeName(x.regime))],['نتائج العينة',x=>num(x.samples,0)],['متوسط العائد بوحدة المخاطرة',x=>num(x.mean_r,3)],['متوسط مرجح بالحداثة',x=>num(x.ewma_r,3)],['معدل النتائج الموجبة المنعم',x=>finite(x.smoothed_positive_rate)?`${num(x.smoothed_positive_rate*100,1)}%`:'—'],['نتائج العينة اللاحقة',x=>num(x.holdout_samples,0)],['عائد العينة اللاحقة',x=>num(x.holdout_mean_r,3)],['حالة المراجعة البحثية',x=>h(learningStatus(x.status))]].map(([label,fn])=>[uiText(label),fn]),arr(learning.models),'لم تتوفر نتائج مكتملة كافية لبدء تقييم التعلم.');
    set('learning-limitations','النتائج تتأثر باختيار الصفقات وترابطها وقد تتغير بعد تصحيح التكاليف. معدل النتائج الموجبة تاريخي منعم؛ ليس احتمال نجاح الصفقة القادمة ولا إثباتًا للربحية. وحدة المخاطرة تعتمد على مخاطرة الدخول الأصلية.');
    const chartLearning=obj(learning.chart_learning);
    set('chart-learning-mode',chartLearning.mode==='SHADOW_ONLY'?'تقييم مستقل عن التنفيذ':'حالة التعلم غير متاحة');
    $('chart-learning-summary').innerHTML=[['نتائج مرتبطة بخصائص الدخول',chartLearning.eligible_records],['نتائج بلا خصائص دخول أصلية',chartLearning.missing_features],['خصائص مستبعدة بعد التحقق',chartLearning.invalid_features],['الحد الأدنى لكل إصدار ورمز وفريم',chartLearning.minimum_samples||60]].map(([label,value])=>`<div class="scan-metric"><strong>${num(value,0)}</strong><span>${h(uiText(label))}</span></div>`).join('');
    set('chart-learning-policy',uiText('يتعلم مصنف محلي من ثماني خصائص للشموع المكتملة ونتائج الصفقات بعد التكاليف. تُحفظ الخصائص وقت قرار الدخول ولا تُستنتج لاحقًا من شارت جديد. يُدرّب على عينة سابقة ويُقيّم على عينة لاحقة منفصلة، مع استبعاد نتائج لم تكن قد أغلقت عند بداية التقييم. يقارن أخطاء التنبؤ بخط أساس بسيط. لا يغير هذا التقييم قواعد التداول أو المخاطرة أو أوزان اللجنة تلقائيًا.'));
    const chartStatus=value=>uiText({INSUFFICIENT:'عينة غير كافية',ONE_CLASS_TRAINING:'عينة التدريب تحتوي نتيجة من فئة واحدة',EVALUATED_SHADOW:'تم التقييم البحثي المستقل'}[value]||'حالة التعلم غير متاحة');
    const economicStatus=value=>uiText({NUMERIC_RANGE_INVALID:'تجاوز النطاق الحسابي',INSUFFICIENT_SELECTED_OUTCOMES:'العينة المختارة غير كافية',NONPOSITIVE_NET_EXPECTANCY:'العائد الصافي غير موجب',RESEARCH_ONLY_POSITIVE_SAMPLE:'عينة موجبة للمراجعة فقط'}[value]||'حالة التعلم غير متاحة');
    $('chart-learning-models').innerHTML=table([['النموذج وإصدار القاعدة',x=>`${h(schoolName(x.strategy_id))}<small class="knowledge-revision">${h(x.revision||'—')}</small>`],['الرمز والفريم',x=>h(`${x.symbol||'—'} · ${x.timeframe||'—'}`)],['نتائج العينة',x=>num(x.samples,0)],['نتائج التدريب',x=>num(x.train_samples,0)],['نتائج العينة اللاحقة',x=>num(x.holdout_samples,0)],['نتائج متداخلة مستبعدة',x=>num(x.purged_overlapping_labels,0)],['خطأ النموذج في العينة اللاحقة',x=>num(obj(x.holdout_model).brier,4)],['خطأ خط الأساس في العينة اللاحقة',x=>num(obj(x.holdout_baseline).brier,4)],['نتائج اختارها المتعلم',x=>num(obj(obj(x.economic_review).selected).outcomes,0)],['العائد الصافي خارج التدريب (R)',x=>num(obj(obj(x.economic_review).selected).mean_net_r,3)],['تقييم العائد',x=>h(economicStatus(x.economic_review_status))],['حالة المراجعة البحثية',x=>h(chartStatus(x.status))]].map(([label,fn])=>[uiText(label),fn]),arr(chartLearning.models),'لم تتوفر صفقات مكتملة تحمل خصائص الدخول الأصلية لهذا التعلم.');
    set('school-drift-title',isEnglish()?'Feature drift by school · training μ ± 3σ':'انحراف الخصائص حسب المدرسة · متوسط التدريب ± 3σ');
    $('school-drift-dashboard').setAttribute('aria-label',isEnglish()?'Feature drift by school':'انحراف الخصائص حسب المدرسة');
    const driftRows=schools.map(s=>{
      const matched=arr(chartLearning.models).filter(m=>arr(s.strategy_ids).includes(m.strategy_id));
      const fitted=matched.filter(m=>arr(obj(m.drift_review).training_control_limits).length);
      return {school:s,matched,fitted,alerts:fitted.filter(m=>obj(m.drift_review).status==='RESEARCH_DRIFT_ALERT').length};
    });
    $('school-drift-dashboard').innerHTML=table([
      [isEnglish()?'School':'المدرسة',x=>h(knowledgeField(x.school,'name'))],
      [isEnglish()?'Separate contexts':'سياقات منفصلة',x=>num(x.matched.length,0)],
      [isEnglish()?'Alerts':'تنبيهات',x=>num(x.alerts,0)],
      [isEnglish()?'Training bounds':'حدود التدريب',x=>x.fitted.length?x.fitted.map(m=>`<details><summary>${h(schoolName(m.strategy_id))} · ${h(m.symbol)} · ${h(m.timeframe)} · ${h(String(m.revision||'').slice(0,12))}</summary>${arr(obj(m.drift_review).training_control_limits).map(v=>`<div dir="ltr">${h(v.feature)}: [${h(num(v.lower,4))}, ${h(num(v.upper,4))}] · μ=${h(num(v.training_mean,4))} · σ=${h(num(v.training_std,4))}</div>`).join('')}</details>`).join(''):h(isEnglish()?'Not evaluable: insufficient training data':'غير قابل للتقييم: بيانات التدريب غير كافية')]
    ],driftRows,isEnglish()?'No school reference loaded':'لم يحمل مرجع المدارس');
    renderValuation();
  }
  function renderValuation(report=state.valuation) {
    const v=obj(report);
    if(!v.model){$('valuation-results').innerHTML=empty('لا توجد نتيجة تقييم مالي محفوظة.');return;}
    const modelName=uiText({pv:'القيمة الحالية',dcf:'التدفقات النقدية المخصومة',ddm:'خصم الأرباح',nav:'صافي الأصول',multiples:'المضاعفات المالية',bond:'تسعير السند'}[v.model]||'نموذج مالي غير معروف');
    const fields=[['القيمة الحالية',v.present_value,true],['قيمة المنشأة',v.enterprise_value,true],['قيمة حقوق الملكية',v.equity_value,true],['القيمة لكل سهم',v.value_per_share,true],['القيمة النهائية المخصومة',v.terminal_pv,true],['السعر عند حد دفعة الكوبون',v.clean_price_at_coupon_boundary,true],['مضاعف المقارنة الوسيط',v.median_multiple,false]];
    $('valuation-results').innerHTML=`<div class="knowledge-valuation-result"><h3>${h(modelName)}</h3><p>${h(uiText('سيناريو يقدمه المستخدم؛ لم يتحقق مصدر مالي مستقل من مدخلاته. الحساب حساس للافتراضات ولا يمنح صلاحية إرسال أوامر.'))}</p><div class="detail-grid">${fields.filter(([,value])=>finite(value)).map(([label,value,monetary])=>`<div class="detail-item"><span>${h(uiText(label))}</span><b>${num(value,4)}${monetary?` ${h(v.currency||'')}`:''}</b></div>`).join('')}<div class="detail-item"><span>${h(uiText('وقت التقييم'))}</span><b>${h(date(v.as_of))}</b></div><div class="detail-item"><span>${h(uiText('وقت نشر المدخلات'))}</span><b>${h(date(v.published_at))}</b></div></div>${finite(v.terminal_fraction)?`<p>${h(uiText('نسبة القيمة النهائية من قيمة المنشأة'))}: ${num(v.terminal_fraction*100,1)}%</p>`:''}<small>${h(uiText('بصمة المدخلات'))}: <span dir="ltr">${h(v.input_fingerprint||'—')}</span></small></div>`;
  }
  function renderEvents() {
    const events=arr(state.events).map((e)=>({...e,kind:first(e.kind,e.event),time:first(e.time,e.at),data:first(e.data,e.payload),reason:first(e.reason,obj(e.payload).reason,obj(e.payload).reasons,obj(e.payload).error,obj(e.payload).message)})),term=$('event-search').value.trim().toLowerCase(),filter=$('event-filter').value;
    const records=events.filter((e)=>{const search=plain(e).toLowerCase(),kind=String(first(e.kind,e.type,e.event,'')).toLowerCase();return (!term||search.includes(term))&&(filter==='all'||filter==='error'&&(/error|reject|fault|fail|unresolved/.test(kind)||String(e.level).toLowerCase()==='error')||filter==='trade'&&/trade|order|intent|send|fill|close/.test(kind)||filter==='risk'&&/risk|limit|budget/.test(kind));});
    set('events-count',`${records.length} ظاهر من ${events.length} حدث`);
    $('events-list').innerHTML=records.length?[...records].sort((a,b)=>Number(first(b.time,b.at,b.created_at,b.timestamp,0))-Number(first(a.time,a.at,a.created_at,a.timestamp,0))).map((e)=>{const details=first(e.data,e.details,e.payload);return `<article class="event-item"><div class="event-time"><span>${h(date(first(e.time,e.at,e.created_at,e.timestamp)))}</span><span>${h(tr(first(e.level,e.kind,e.type,e.event,'حدث')))}</span></div><div><h3>${h(plain(first(e.title,e.message,e.kind,e.type,e.event,'حدث')))}</h3><p>${h(plain(first(e.reason,e.explanation,e.message,obj(e.payload).reason)))}</p>${details?`<details><summary>تفاصيل محفوظة</summary><pre>${h(JSON.stringify(localizedData(details),null,2))}</pre></details>`:''}</div></article>`;}).join(''):empty('لا توجد أحداث بهذه التصفية.','تُسجل القرارات والأعطال عند حدوثها.');
  }
  function renderSetup() {
    const t=obj(state.terminal),a=account();$('terminal-details').innerHTML=`<dl class="metric-list"><div><dt>اتصال المنصة</dt><dd>${h(t.connected===true?'متصل':t.connected===false?'غير متصل':'غير معروف')}</dd></div><div><dt>السماح بالتداول من المنصة</dt><dd>${h(t.trade_allowed===true?'مسموح':t.trade_allowed===false?'غير مسموح':'غير معروف')}</dd></div><div><dt>التداول عبر الواجهة</dt><dd>${h(t.tradeapi_disabled===true?'معطل':t.tradeapi_disabled===false?'متاح':'غير معروف')}</dd></div><div><dt>نمط الحساب</dt><dd>${h(a.margin_mode===0?'مركز موحد لكل رمز':a.margin_mode===2?'مراكز متعددة لكل رمز':'غير معروف')}</dd></div></dl>`;
    const services=obj(state.services);const rowsData=[['مصدر الأسعار',state.simulation?'اصطناعي — محاكاة فقط':t.connected?'منصة MT5':'لا يوجد اتصال'],['حالة المحرك',tr(typeof state.status==='string'?state.status:undefined)],['وقت البيانات',date(first(state.last_update||undefined,state.updated_at,state.as_of))],['حالة المطابقة',plain(first(state.reconciliation,services.reconciliation,arr(obj(state.execution).unresolved).length?'عمليات غير محسومة':'راجع سجل المطابقة'))],['التخزين الدائم',plain(first(state.storage,services.storage,'سجل اليوم والنيات محلي؛ راجع تقرير التشخيص'))],['موارد الجهاز',plain(first(state.resources,services.resources))],['حد بداية اليوم',plain(state.day_boundary)],['حالة القبول النهائي',plain(state.acceptance)]];
    $('service-details').innerHTML=rowsData.map(([name,value])=>`<div class="service-item"><strong>${h(name)}</strong><span>${h(value)}</span></div>`).join('');
  }
  document.querySelectorAll('[data-view]').forEach((x)=>x.addEventListener('click',()=>go(x.dataset.view)));
  document.querySelectorAll('[data-go]').forEach((x)=>x.addEventListener('click',()=>go(x.dataset.go)));
  document.querySelectorAll('[data-unit]').forEach((x)=>x.addEventListener('click',()=>{unit=x.dataset.unit;prefs.unit=unit;savePrefs();updateConversions();}));
  $('risk-input').addEventListener('input',updateConversions);$('target-input').addEventListener('input',updateConversions);
  document.querySelectorAll('input[name="mode"]').forEach((x)=>x.addEventListener('change',()=>{prefs.mode=x.value;savePrefs();updateControls();}));
  $('menu-toggle').addEventListener('click',()=>document.querySelector('.shell').classList.toggle('menu-open'));
  $('refresh-button').addEventListener('click',()=>poll(false));
  $('external-research-refresh').addEventListener('click',async()=>{if(!busy)await action('refresh_external_research',{},'بدأ تحديث مصادر البيانات البحثية.');});
  $('llm-research-run').addEventListener('click',async()=>{if(!busy)await action('run_llm_research',{},'بدأ التحليل الظلي للمخرجات الحالية.');});
  const applyTheme=(name)=>{const allowed=['neural','forest','midnight','graphite','sand','white'];name=allowed.includes(name)?name:'neural';document.documentElement.dataset.theme=name;prefs.theme=name;savePrefs();};
  const applyLanguage=(name)=>{name=name==='en'?'en':'ar';prefs.language=name;savePrefs();document.body.classList.toggle('language-en',name==='en');if(hasState)render();else applyI18n();set('view-title',uiText(titles[currentView]));};
  $('theme-select').addEventListener('change',(e)=>applyTheme(e.target.value));$('language-select').addEventListener('change',(e)=>applyLanguage(e.target.value));
  $('start-button').addEventListener('click',async(e)=>{
    if(!executionRunning())return;
    e.preventDefault();
    if(!busy)await action('stop',{},'أُرسل طلب إيقاف الدخول الجديد. راجع حالة المحرك.');
  });
  $('start-form').addEventListener('submit',async(e)=>{
    e.preventDefault();
    if(executionRunning()){
      if(!busy)await action('stop',{},'أُرسل طلب إيقاف الدخول الجديد. راجع حالة المحرك.');
      return;
    }
    const risk=Number($('risk-input').value),target=Number($('target-input').value),mode=document.querySelector('input[name="mode"]:checked').value;
    if(!Number.isFinite(risk)||risk<=0||!Number.isFinite(target)||target<=0){toast('أدخل مخاطرة وهدفًا موجبين قبل التفعيل.',true);return;}
    if(unit==='percent'&&(risk>100||target>100)){toast('النسبة يجب ألا تتجاوز 100%.',true);return;}
    let scalping,costs;try{scalping=scalpSettingsPayload();costs=executionCosts();}catch(err){toast(err.message,true);return;}
    const storedExecution=Object.keys(obj(state.settings)).length?obj(state.settings):obj(state.setup);
    const selectedProtocol=storedExecution.decision_protocol==='multi_school_v1'?'multi_school_v1':'four_school_v1';
    await action('start',{risk_value:risk,target_value:target,unit,mode,decision_protocol:selectedProtocol,scalping,scalp_only:selectedProtocol==='multi_school_v1'||!!storedExecution.scalp_only,validation_policy:'forward_demo',...costs},'تم طلب تفعيل التفويض. راجع الحالة وقرار المخاطر.');
  });
  for(const id of ['scalp-mode-input','scalp-normal-risk','scalp-normal-target','scalp-normal-rr','scalp-fast-risk','scalp-fast-target','scalp-fast-rr','scalp-normal-profit','scalp-fast-profit']) $(id).addEventListener('input',()=>{executionFormDirty=true;renderExecutionSettings();});
  document.querySelectorAll('[data-scalp-mode]').forEach(button=>button.addEventListener('click',()=>selectScalpMode(button.dataset.scalpMode)));
  $('apply-scalp-mode').addEventListener('click',async()=>{
    let payload;try{payload=scalpModeActivationPayload();}catch(err){$('scalp-options').open=true;toast(err.message,true);return;}
    const result=await action('start',payload,'طُلب تطبيق نمط السكالب؛ راجع النمط النشط بعد التأكيد.');
    if(result?.ok){executionFormDirty=false;executionFormRestored=false;renderExecutionSettings();}
  });

  $('stop-button').addEventListener('click',()=>action('stop',{},'أُرسل طلب إيقاف الدخول الجديد. راجع حالة المحرك.'));
  $('cancel-button').addEventListener('click',async()=>{if(await confirm('إلغاء أوامر المنظومة','سيحاول النظام إلغاء أوامره المعلقة فقط، ثم يطابق النتيجة مع الوسيط قبل تحرير المخاطرة المحجوزة.','إلغاء الأوامر',true))await action('cancel',{},'تم إرسال طلب الإلغاء؛ راجع نتائج الوسيط.');});
  $('flatten-button').addEventListener('click',async()=>{if(await confirm('إغلاق مراكز المنظومة','سيوقف النظام الدخول الجديد ويحاول إغلاق المراكز التي يملك تفويض إدارتها بالسعر المتاح. الإغلاق قد يختلف عن الربح المعروض؛ النتيجة تُؤكد بعد رد الوسيط والتكاليف.','إغلاق المراكز',true))await action('flatten',{},'تم طلب الإغلاق؛ لا يُعد مكتملًا قبل تأكيد الوسيط.');});
  ['scan-button','market-scan-button'].forEach((id)=>$(id).addEventListener('click',()=>action('scan',{},'بدأ طلب فحص قائمة الرموز الكاملة.')));
  $('connect-form').addEventListener('submit',async(e)=>{e.preventDefault();const terminal_path=$('terminal-path').value.trim(),bridge_path=$('bridge-path').value.trim();prefs.terminal_path=terminal_path;prefs.bridge_path=bridge_path;savePrefs();await action('connect',{terminal_path,bridge_path},'تم طلب الاتصال وفحص الحساب.');});
  const terminalDiscovery=document.createElement('div');terminalDiscovery.className='action-row';terminalDiscovery.id='terminal-discovery';
  const discoverTerminalsButton=document.createElement('button');discoverTerminalsButton.className='button secondary';discoverTerminalsButton.type='button';discoverTerminalsButton.textContent=tr('اكتشاف نسخ MT5');discoverTerminalsButton.setAttribute('aria-label',tr('اكتشاف نسخ MT5 المثبتة على هذا الجهاز'));
  const terminalChoices=document.createElement('select');terminalChoices.id='terminal-choices';terminalChoices.setAttribute('aria-label',tr('اختر نسخة MT5'));terminalChoices.hidden=true;
  terminalDiscovery.appendChild(discoverTerminalsButton);terminalDiscovery.appendChild(terminalChoices);$('connect-form').insertAdjacentElement('afterbegin',terminalDiscovery);
  discoverTerminalsButton.addEventListener('click',async()=>{const result=await action('discover_mt5_terminals',{},'اكتمل البحث عن نسخ MT5 المثبتة.');if(!result)return;terminalChoices.textContent='';let discoveredTerminalCount=0;for(const terminal of result.terminals||[]){const option=document.createElement('option');option.value=terminal.path;option.textContent=`${terminal.name} — ${terminal.path}`;terminalChoices.appendChild(option);discoveredTerminalCount+=1;}terminalChoices.hidden=discoveredTerminalCount===0;if(!discoveredTerminalCount)toast(tr('لم يُعثر على نسخة تلقائيًا؛ أدخل مسار terminal64.exe يدويًا.'),true);else{$('terminal-path').value=terminalChoices.value;}});
  terminalChoices.addEventListener('change',()=>{if(!terminalChoices.value)return;$('terminal-path').value=terminalChoices.value;prefs.terminal_path=terminalChoices.value;savePrefs();});
  $('install-bridge-button').addEventListener('click',async()=>{const r=await action('install_bridge',{terminal_path:$('terminal-path').value.trim()},'تم طلب تثبيت ملفات الجسر.');if(r)set('bridge-install-result',`${plain(first(r.instructions,r.message,r.result,r.path,'تم التثبيت.'))} افتح لوحة المستكشف في المنصة، وحدّث قائمة المستشارين الآليين، ثم أضف الجسر إلى أي شارت. الجسر للقراءة فقط.`);});
  $('reconcile-button').addEventListener('click',async()=>{await action('reconcile',{},'اكتملت مطابقة سجل الوسيط');});
  $('simulation-button').addEventListener('click',async()=>{if(await confirm('تفعيل محاكاة محلية','سيُستخدم مصدر اصطناعي واضح العلامة لاختبار التطبيق. نتائجه لا تثبت الربحية ولا الاتصال بمنصة MT5، ولا تُعد اختبارًا فعليًا لدى الوسيط.','بدء المحاكاة')){const r=await action('simulation',{},'تم طلب تفعيل المصدر الاصطناعي.');if(r)go('overview');}});
  $('chart-load').addEventListener('click',loadChart);async function loadChart(symbolOverride){const symbol=typeof symbolOverride==='string'?symbolOverride:$('chart-symbol').value,timeframe=$('chart-timeframe').value;if(!symbol){toast('اختر رمزًا أولًا.',true);return;}prefs.symbol=symbol;prefs.timeframe=timeframe;savePrefs();await action('chart',{symbol,timeframe});}
  const backtestButton=document.createElement('button');backtestButton.id='backtest-button';backtestButton.className='button secondary';backtestButton.type='button';backtestButton.textContent='تحقق كمي';$('chart-load').insertAdjacentElement('afterend',backtestButton);
  backtestButton.addEventListener('click',async()=>{const symbol=$('chart-symbol').value,timeframe=$('chart-timeframe').value;if(!symbol){toast('اختر رمزًا للتحقق الكمي أولًا.',true);return;}let costs;try{costs=executionCosts();}catch(err){toast(err.message,true);return;}const old=backtestButton.textContent;backtestButton.textContent='جارٍ طلب التحقق…';try{const result=await action('backtest',{symbol,timeframe,...costs},'طُلب التحقق الكمي؛ النتيجة لا تمنح صلاحية تنفيذ تلقائيًا.');if(result)go('performance');}finally{backtestButton.textContent=old;}});
  const shutdownRow=document.createElement('div');shutdownRow.className='action-row';const shutdownButton=document.createElement('button');shutdownButton.className='button subtle';shutdownButton.id='shutdown-button';shutdownButton.type='button';shutdownButton.textContent='إيقاف الخدمة المحلية والخروج';shutdownRow.appendChild(shutdownButton);document.querySelector('#view-setup > .panel').appendChild(shutdownRow);
  shutdownButton.addEventListener('click',async()=>{if(!await confirm('إيقاف Quant Trading AI','سيُلغى تفويض الدخول وتُغلق الخدمة المحلية. هذا الإجراء لا يغلق المراكز المفتوحة لدى الوسيط ولا يلغي أوامره. لإدارتها استخدم إجراءات المنظومة قبل الخروج.','إيقاف الخدمة'))return;if(busy)return;busy=true;updateControls();pollingEnabled=false;clearTimeout(pollTimer);try{await api('/api/action',{method:'POST',body:JSON.stringify({action:'shutdown'})});set('service-error','أُوقفت الخدمة المحلية. يمكنك إغلاق هذه النافذة وإعادة التشغيل من ملف Quant Trading AI.');$('service-error').hidden=false;toast('أُرسِل طلب إيقاف الخدمة المحلية.');}catch(err){toast(err.message,true);}finally{busy=false;lastPollError='الخدمة متوقفة';updateConnection();updateControls();}});
  document.addEventListener('click',async(e)=>{const chart=e.target.closest('[data-open-chart]'),approve=e.target.closest('[data-approve]'),symbol=e.target.closest('tr[data-symbol]');if(chart){go('research');$('chart-symbol').value=chart.dataset.openChart;await loadChart(chart.dataset.openChart);}else if(approve){if(await confirm('اعتماد نية تداول تجريبي',`ستُرسل النية ${approve.dataset.approve} لفحص الحساب والمخاطر والأسعار مجددًا. إذا اجتازت الفحص، ينفذها مرسل الأوامر الوحيد.`, 'اعتماد النية'))await action('approve',{intent_id:approve.dataset.approve},'تم طلب اعتماد النية؛ راجع النتيجة.');}else if(symbol)showSymbol(symbol.dataset.symbol);});
  $('symbols-table').addEventListener('keydown',(e)=>{if(e.key==='Enter'&&e.target.matches('tr[data-symbol]'))showSymbol(e.target.dataset.symbol);});
  ['symbol-search','symbol-filter'].forEach((id)=>$(id).addEventListener(id.endsWith('search')?'input':'change',renderSymbols));
  ['event-search','event-filter'].forEach((id)=>$(id).addEventListener(id.endsWith('search')?'input':'change',renderEvents));
  $('diagnostics-button').addEventListener('click',async()=>{const r=await action('diagnostics',{},'تم طلب جمع التشخيص.');if(r){$('diagnostics-result-panel').hidden=false;const d=first(r.diagnostics,r.result,r.report,r.path,r.message);$('diagnostics-result').className='';$('diagnostics-result').textContent=plain(d||'تم إنشاء التقرير؛ راجع سجل العمليات للحصول على مساره.');}});
  ['knowledge-search','knowledge-filter'].forEach(id=>$(id).addEventListener(id.endsWith('search')?'input':'change',renderKnowledge));
  document.addEventListener('toggle',e=>{const id=e.target.dataset?.knowledgeDetails;if(id){if(e.target.open)knowledgeExpanded.add(id);else knowledgeExpanded.delete(id);}},true);
  $('knowledge-export-button').addEventListener('click',async()=>{const r=await action('knowledge_export',{},'حُفظ تقرير المعرفة والتعلم محليًا.');if(r){$('knowledge-export-panel').hidden=false;const path=first(r.path,obj(r.knowledge_export).path,obj(r.result).path);$('knowledge-export-result').className='knowledge-export-path';$('knowledge-export-result').textContent=path?`${uiText('مسار الملف المحلي')}: ${path}`:uiText('راجع سجل العمليات للحصول على مسار المرجع.');}});
  $('valuation-example-button').addEventListener('click',()=>{$('valuation-input').value=JSON.stringify({model:'dcf',asset:'ILLUSTRATIVE_EXAMPLE',currency:'USD',as_of:1700000000,published_at:1699000000,source:'User-supplied illustrative scenario; invented example',cashflows:[100,110,120],discount_rate:0.10,terminal_growth:0.02,debt:200,cash:50,shares:100},null,2);toast('أُدرج مثال اصطناعي للتوضيح؛ الأرقام ليست بيانات سوق أو شركة فعلية.');});
  $('valuation-analyze-button').addEventListener('click',async()=>{let data;try{data=JSON.parse($('valuation-input').value);if(!data||typeof data!=='object'||Array.isArray(data))throw new Error();}catch(_){toast('أدخل كائن بيانات منظمًا صالحًا قبل حساب السيناريو.',true);return;}const r=await action('fundamental_analyze',{data},'حُسب السيناريو المالي محليًا دون توصية تداول.');if(r?.valuation)renderValuation(r.valuation);});
  $('price-chart').addEventListener('mousemove',(e)=>{if(!chartGeometry)return;const rect=e.currentTarget.getBoundingClientRect(),x=e.clientX-rect.left,idx=Math.floor((x-chartGeometry.left)/chartGeometry.step),b=chartGeometry.bars[idx];if(!b){$('chart-tooltip').hidden=true;return;}$('chart-tooltip').hidden=false;set('chart-tooltip',`${date(b.time)} | O ${num(b.open,6)} · H ${num(b.high,6)} · L ${num(b.low,6)} · C ${num(b.close,6)} | Tick count ${num(b.tick_volume,0)}${finite(b.real_volume)&&b.real_volume>0?` · Real volume ${num(b.real_volume,0)}`:''}`);});
  $('price-chart').addEventListener('mouseleave',()=>$('chart-tooltip').hidden=true);window.addEventListener('resize',drawChart);window.addEventListener('hashchange',()=>go(location.hash.slice(1)));
  $('terminal-path').value=prefs.terminal_path||'';$('bridge-path').value=prefs.bridge_path||'';unit=['money','percent'].includes(prefs.unit)?prefs.unit:'money';document.querySelector('input[name="mode"][value="AUTO_DEMO"]').checked=true;if(Array.from($('chart-timeframe').options||[]).some((o)=>o.value===prefs.timeframe))$('chart-timeframe').value=prefs.timeframe;if(prefs.design_theme_version!==1){prefs.theme='neural';prefs.design_theme_version=1;savePrefs();}$('theme-select').value=prefs.theme||'neural';$('language-select').value=prefs.language==='en'?'en':'ar';applyTheme($('theme-select').value);applyLanguage($('language-select').value);
  const tickClock=()=>set('clock',`${new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Dubai',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date())}  ${isEnglish()?'UTC+4':'بتوقيت دبي'}`);tickClock();setInterval(tickClock,1000);
  go(location.hash.slice(1));render();poll();
})();





