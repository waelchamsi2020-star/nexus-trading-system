'use strict';
(() => {
  const en = {
    'اكتشاف نسخ MT5':'Discover MT5 installations','اكتشاف نسخ MT5 المثبتة على هذا الجهاز':'Discover MT5 installations on this device','اختر نسخة MT5':'Choose an MT5 installation','لم يُعثر على نسخة تلقائيًا؛ أدخل مسار terminal64.exe يدويًا.':'No installation was found automatically; enter the terminal64.exe path manually.','اكتمل البحث عن نسخ MT5 المثبتة.':'Finished searching for installed MT5 terminals.',
    'مطابقة سجل الوسيط':'Reconcile broker ledger','اكتملت مطابقة سجل الوسيط':'Broker ledger reconciliation completed','تعذرت المطابقة؛ راجع السجل':'Reconciliation failed; review the audit log',
    'نتائج اختارها المتعلم':'Shadow-selected outcomes','العائد الصافي خارج التدريب (R)':'Holdout net expectancy (R)','تقييم العائد':'Economic review',
    'تجاوز النطاق الحسابي':'Numerical range exceeded','العينة المختارة غير كافية':'Insufficient selected outcomes','العائد الصافي غير موجب':'Nonpositive net expectancy','عينة موجبة للمراجعة فقط':'Positive sample for research only',
    'الشارت والتحليل':'Chart & Analysis','التقويم والأخبار':'Calendar & News','الصفقات':'Positions','الأداء':'Performance','المكتبة والتعلم':'Library & Learning',
    'تفاصيل المصادر':'Source details','تغطية النماذج':'Model coverage','نتائج الاختبار التاريخي':'Backtest results','نتائج تعلم القواعد':'Rule learning results','نتائج التعلم من الشموع':'Chart learning results','تفاصيل النماذج':'Model details','حدود المرجع':'Reference scope',
    'خيارات متقدمة':'Advanced options',
    'الأسواق':'Markets','فحص':'Scan','التفاصيل':'Details',
    'صافي اليوم':'Daily net','محقق إجمالي':'Gross realized','التكاليف المنسوبة':'Attributed costs','صافي الخسارة':'Net loss','خسارة عائمة':'Floating loss','الاتصال':'Connection','لا توجد فرصة دخول مؤهلة الآن.':'No qualified entry opportunity now.',

    'قرار التداول':'Trading decision','المسح':'Scan','إعدادات السكالب':'Scalp settings','مخاطرة الصفقة %':'Trade risk %','هدف خطة الصفقة %':'Trade-plan target %','هدف النمط بعملة الحساب':'Mode target in account currency','العائد / المخاطرة':'Reward / risk','السكالب السريع':'Fast scalp','إعدادات إضافية':'Advanced settings',

    'التداول':'Trading','حدود اليوم':'Daily limits','حد الخسارة':'Loss limit','هدف الربح':'Profit target','مبلغ':'Amount','نسبة %':'Percent %','تطبيق':'Apply','تغييرات غير مطبقة':'Unapplied changes',

    'إيقاف الدخول الجديد':'Stop New Entries',
    'ابدأ التداول':'Start trading',
    'نشط':'Active',
    'تفاصيل الحساب':'Calculation details',
    'الرئيسية':'Home','الشروط':'Conditions','سجل اليوم':'Today’s log',
    'يبدأ اليوم عند 02:00 بتوقيت دبي':'Day starts at 02:00 Dubai time',

    "ملف حالة التعلم محفوظ محليًا ويُرفق بتصدير المعرفة والتشخيص. قاعدة البيانات تحفظ التاريخ الكامل؛ الخسارة حالة للمراجعة وليست دليلًا تلقائيًا على خطأ القاعدة.":"The learning-state file is saved locally and included in knowledge and diagnostic exports. The database retains full history; a loss is a review case, not automatic proof of a rule defect.",
    "تعذر حفظ ملف حالة التعلم؛ تبقى قاعدة البيانات مرجعًا، وراجع تقرير التشخيص.":"The learning-state mirror could not be saved. The database remains authoritative; review diagnostics.",
    "يظهر تأكيد حفظ ملف التعلم بعد اكتمال تحديث سجل الوسيط.":"Learning-file confirmation appears after the broker-history refresh completes.",
    "ترجيح العائلات دون نسبة تصويت ثابتة":"Evidence-family weighting without a fixed vote percentage",
    "ترجيح عائلات أدلة الدقيقة؛ يلزم عائلتان ودعم يتجاوز المعارضة دون نسبة تصويت ثابتة؛ فحص التكلفة الصافية مستقل":"M1 evidence-family weighting: at least two families and support exceeding opposition, without a fixed vote percentage; independent net-cost validation.",
    "الدعم":"Support",
    "المعارضة":"Opposition",
    "صافي الدليل":"Net evidence",
    "النماذج المسجلة":"Registered models",
    "البطاقات الصالحة الحديثة":"Fresh eligible cards",
    "البطاقات المستبعدة":"Excluded cards",
    "نقص البيانات لا يؤكد أي اتجاه.":"Missing data confirms neither direction.",
    "لم يكتمل تاريخ تهيئة المؤشر":"Indicator warm-up history is incomplete",
    "لم تكتمل هندسة الهارمونيك ذات المحاور الخمسة":"Five-pivot harmonic geometry is incomplete",
    "لم يكتمل تأكيد نقطة الهارمونيك الأخيرة":"The final harmonic pivot confirmation is incomplete",
    "سماحات نسب الهارمونيك وشروط تأكيد التنفيذ قواعد محلية معلنة":"Harmonic ratio tolerances and execution confirmation are declared house rules",
    "يلزم عدد تكات موجب ومحدود لحاسبة التدفق التقريبي":"Positive finite tick counts are required for the flow proxy",
    "التدفق المرجح بالتكات تقريب نشاط سعري وليس تدفق أموال فعلياً":"Tick-weighted flow is a price-activity proxy, not actual money flow",
    "يلزم عدد تكات موجب ومحدود لنموذج توسع النطاق":"Positive finite tick counts are required for range expansion",
    "توسع النطاق يستخدم نشاط التكات ولا يقيس حجم تداول مؤسسي فعلي":"Range expansion uses tick activity and does not measure actual institutional volume",
    "قاعدة تنفيذ محلية موثقة؛ لا تمثل جميع تفسيرات المدرسة ولا تثبت ربحيتها.":"Documented local execution rule; it neither covers every school interpretation nor proves profitability.",
    "هدف جني الدولار لدى الوسيط":"Broker one-dollar cash profit target",
    "صافي الخسائر المحققة المحتسبة":"Net realized losses counted",
    "المتبقي = حد اليوم − صافي الخسائر المحققة − المخاطرة المحجوزة − التعرض الإضافي. الأرباح المحققة تعوض الخسائر دون زيادة الحد؛ إعادة التشغيل لا تمحو السجل.":"Remaining = daily limit minus net realized losses, reserved risk and additional exposure. Realized gains offset losses without increasing the limit; restarting preserves the ledger.",
    "سكالب الدقيقة مع تأكيد اتجاه ربع الساعة والساعة. جني الربح عند صافي دولار واحد دون انتظار الدولارين؛ يوضع الهدف لدى الوسيط حين تسمح شروطه. الانزلاق قد يقلل الربح الفعلي. هدف التحليل الهيكلي لا يمثل عائد الخروج النقدي.":"M1 scalping with completed M15 and H1 trend confirmation. Take profit at one net dollar without waiting for two; install the broker target when allowed. Slippage may reduce the realized profit. The structural analysis target does not represent the cash exit return.",
    "اتجاه ربع الساعة والساعة لا يؤكد اتجاه الدخول على الدقيقة":"Completed M15 and H1 trend do not confirm the M1 direction",
    "تاريخ الفريمات الأكبر غير كافٍ لتأكيد الاتجاه":"Higher timeframe trend history missing",
    "بيانات اتجاه الفريمات الأكبر قديمة":"Higher timeframe trend data stale",
    "تغير الربح النقدي قبل إرسال أمر الإدارة":"Cash profit changed before management send",
    "حماية الربح بالدولار تتطلب حسابًا تجريبيًا بعملة الدولار":"Dollar profit protection requires a USD Demo account",
    "جني الربح عند دولار واحد":"Take profit at one net dollar",
    "جني الربح لتعذر تثبيت الحماية":"Take profit because the broker profit floor cannot be placed",
    "حماية ربح الدولار بوقف الوسيط":"Protect the dollar profit with a broker stop",
    "مسار متعدد المدارس من شموع MT5؛ يفحص جميع الوكلاء المنفذين ويجمع عائلتي أدلة وفريمين، دون إلزام بتسلسل ICT. البيانات الناقصة لا تعطي تصويتًا.":"Multi-school MT5 candle route; evaluates all implemented agents and requires two evidence families and two timeframes, without a mandatory ICT chain. Missing data abstains.",
    "أدلة الدقيقة لا ترجح اتجاهًا بوضوح (M1 directional evidence has no clear advantage)":"M1 directional evidence has no clear advantage",
    "أدلة الدقيقة لا ترجح اتجاهًا بوضوح":"M1 directional evidence has no clear advantage",
    "ترجيح عائلات أدلة الدقيقة؛ يلزم عائلتان وتفوق 20٪ على الاتجاه المقابل؛ فحص التكلفة الصافية مستقل":"M1 evidence-family vote: two families and a 20% directional advantage; independent net-cost checks.",
    "وكيل سكالب محلي يقود القرار من الدقيقة ويوازن أدلة المدارس؛ لا يشترط اتفاق الفريمات. تبقى التكلفة الصافية ووقف الخسارة وحدود المال ملزمة.":"Local scalp agent leads from M1 and weighs school evidence without mandatory timeframe agreement. Net costs, protective stops and financial limits remain binding.",
    "هذا الفريم للتأكيد فقط؛ الدخول محصور بفريم السكالب المحدد.":"This timeframe provides context only; entry is restricted to the selected scalp timeframe.",
    "ربح الصفقة المستهدف % من قيمة الحساب":"Trade profit target % of Equity",
    "اختياري":"Optional",
    "عدد التكات":"Tick count",
    "القيمة المرجعية":"Baseline",
    "نسبة النشاط":"Activity ratio",
    "موقع الإغلاق":"Close location",
    "مؤشر ضغط تقريبي":"Pressure proxy",
    "رفض سعري مع نشاط التكات التقريبي":"Bar tick-activity rejection proxy",
    "عدد تكات موجب":"Positive tick counts",
    "بدائل محلية منفذة":"Implemented local alternatives",
    "تحليل محلي؛ التقويم من منصة الوسيط فقط؛ مصادر الإنترنت الخارجية معطلة":"Local analysis; broker-platform calendar only; external internet sources disabled",
    "يلزم عدد تكات موجب لكل شمعة لحساب مؤشر النشاط المحلي":"positive bar tick counts required for local activity proxy",
    "نشاط تكات الشموع وموقع الإغلاق مؤشر تقريبي؛ لا يمثل تدفق أوامر أو حجم صفقات محدد الاتجاه":"Bar tick activity and close-location proxy; not real order flow or signed volume",

    "نسبة التصحيح":"Retracement",
    "نسبة تشابه الضلعين":"Leg equality ratio",
    "نسبة الامتداد":"Projection",
    "الترقيمات المرشحة":"Candidate counts",
    "الترقيمات الهندسية الصالحة":"Valid geometric counts",
    "القواعد":"Rules",
    "الهندسة مطابقة":"Geometry valid",
    "الدرجات المتداخلة مفحوصة":"Nested degrees verified",
    "الموجة الثانية لا تتجاوز البداية":"Wave two preserves origin",
    "الموجة الثالثة تتجاوز الأولى":"Wave three exceeds wave one",
    "الرابعة لا تتداخل مع الأولى":"Wave four avoids overlap",
    "الثالثة ليست الأقصر":"Wave three is not shortest",
    "الخامسة تتجاوز الثالثة":"Nontruncated fifth wave",
    "الملامسة الأولى":"First touch",
    "وقت تكوّن المنطقة":"Zone formation time",
    "الذيل السفلي":"Lower wick",
    "الذيل العلوي":"Upper wick",
    "الانحراف":"Deviation",
    "الميل":"Slope",
    "مقياس التقلب":"Volatility scale",
    "الهارمونيك: نموذج الأضلاع المتساوية":"Harmonics: Equal-Leg Pattern",
    "يلزم أربعة محاور هارمونيك متعاقبة ومؤكدة":"four confirmed alternating harmonic pivots",
    "نسب الأضلاع خارج الحدود المحددة للنموذج":"equal-leg ratios outside declared bounds",
    "يلزم اختراق جديد بعد تأكيد النقطة الرابعة خلال ثماني شموع":"fresh break after D confirmation within eight bars",
    "هندسة أضلاع متساوية مؤكدة":"confirmed equal-leg geometry",
    "اختراق جديد بعد تأكيد النموذج":"fresh post-confirmation break",
    "يلزم بقاء النقطة الرابعة سليمة واختراق جديد قبل بلوغ هدف النقطة الثالثة":"unbroken D and fresh confirmation break before C target",
    "هدف المحور الثالث للنموذج":"harmonic C pivot target",
    "نموذج الأضلاع المتساوية فقط؛ تأكيد الدخول والسماحات قواعد خاصة بهذه النسخة ولا تغطي كل الهارمونيك":"Equal-leg model only; not all harmonic patterns; entry confirmation and tolerances are house rules",

    "قواعد التخصص":"Specialist rules","حالة السوق":"Market regime","اتجاه":"Trend","نطاق":"Range","مختلط":"Mixed","تقلب مرتفع":"High volatility",
    "العودة الأولى للفجوة السعرية":"Three-bar gap first return",
    "العودة الأولى لمنطقة الأساس":"Displacement base first return",
    "اختراق قناة عشرين شمعة":"20-bar channel breakout",
    "فشل اختراق النطاق":"Failed range breakout",
    "رفض الذيل عند حد سعري":"Boundary pin rejection",
    "اختراق الشمعة الداخلية":"Inside bar breakout",
    "العودة داخل النطاق الإحصائي":"Two-deviation band reentry",
    "اختراق قناة التقلب":"ATR channel breakout",
    "تسارع الزخم السعري":"Normalized momentum acceleration",
    "اختراق نطاق بداية اليوم العالمي":"UTC first-hour range breakout",
    "عودة إلى قناة الانحدار":"Regression residual reentry",
    "تحققت قاعدة التخصص":"specialist rule confirmed",
    "لم يكتمل شرط دخول التخصص":"specialist trigger not completed",
    "مستويات قاعدة التخصص":"specialist levels",
    "تعريف خوارزمي محدد وليس مدرسة كاملة أو إثباتًا للربحية":"house definition; not a complete school or profitability claim",
    "حالة السوق خارج النطاق المعلن للاستراتيجية":"market regime outside declared scope",
    "هدف المتوسط المحدد للاستراتيجية":"specialist mean target",

    'اختبار أمامي على Demo دون اشتراط التأهيل التاريخي':'Forward Demo testing without historical qualification',
    'اختبار أمامي تجريبي — غير مؤهل تاريخيًا':'Forward Demo test — not historically qualified',
    'اختبار أمامي تجريبي بإشارة استراتيجية؛ التأهيل التاريخي غير مشترط':'Forward Demo strategy signal; historical qualification is not required',
    'نظرة عامة':'Overview','الأسواق والفرص':'Markets & Opportunities','الأبحاث والشارت':'Research & Chart','الأخبار والاقتصاد':'News & Economy','الصفقات والأوامر':'Positions & Orders','الأداء والتغطية':'Performance & Coverage','السجل والأعطال':'Audit & Diagnostics','الإعداد والاتصال':'Setup & Connection','مركز القيادة':'Command Center','كل قرار، له سبب.':'Every decision has a reason.','أسواق متعددة. أبحاث مستقلة. ميزانية مخاطرة واحدة.':'Multiple markets. Independent research. One risk budget.','تفويض اليوم':'Today’s Authorization','ميزانية اليوم':'Today’s Budget','التقدم نحو الهدف':'Progress to Target','اكتشاف الأسواق':'Market Discovery','ماذا ترى لجنة القرار؟':'What Does the Committee See?',
    'كل رموز الوسيط':'All Broker Symbols','اكتشاف الرموز، فحص أهليتها، ثم ترتيب المرشحين.':'Discover symbols, validate eligibility, then rank candidates.','بدء دورة مسح':'Start Scan','الفرص المرتبة':'Ranked Opportunities','الترتيب لا يمنح صلاحية التنفيذ':'Ranking does not authorize execution','قائمة الرموز الكاملة':'Complete Symbol List','جميع الحالات':'All statuses','مؤهل':'Eligible','مستبعد':'Excluded','غير مؤهل حاليًا':'Not eligible right now','غير المؤهلة حاليًا':'Not currently eligible','غير مفحوص':'Unchecked','سبب الحالة':'Status reason','الأبحاث الفنية ولجنة القرار':'Technical Research & Decision Committee','من الفكرة إلى الدليل':'From Idea to Evidence','كل مدرسة تعرض قواعدها وبياناتها وحدودها بصورة مستقلة.':'Each school shows its rules, data and limits independently.','اختر رمزًا':'Select a symbol','عرض':'Load','الشارت والأدلة':'Chart & Evidence','لا توجد بيانات':'No data','صعود':'Up','هبوط':'Down','مستويات الأدلة':'Evidence Levels','قرار اللجنة':'Committee Decision','الأسباب المؤيدة والمعارضة':'Supporting and Opposing Reasons','بطاقات المدارس':'School Cards','درجة جودة الأدلة ليست احتمال نجاح':'Evidence quality is not a win probability',
    'وقائع موثقة وتغطية معلنة':'Verified Facts & Declared Coverage','الخبر واقعة؛ تفسير أثره احتمال مستقل عنها.':'News is a fact; its effect is a separate inference.','مصادر مجانية فقط':'Free Sources Only','حالة المصادر':'Source Status','الوصول والحداثة وحدود التغطية':'Access, Freshness & Coverage Limits','الوقائع والأخبار':'Facts & News','الجدول الاقتصادي':'Economic Calendar','لا نفترض توفر توقعات مجانية':'Free forecasts are not assumed','المخاطر والتنفيذ والمطابقة':'Risk, Execution & Reconciliation','نتيجة الوسيط هي المرجع؛ الإرسال لا يعني التنفيذ.':'The broker result is authoritative; sending is not filling.','نيات تحتاج موافقة':'Intents Requiring Approval','الموافقة لا تتجاوز فحص المخاطر':'Approval never bypasses risk checks','المراكز':'Positions','الأوامر':'Orders','سجل نيات التداول':'Trading Intent Log','من الاقتراح إلى النتيجة المؤكدة':'From proposal to confirmed result',
    'قياس النتائج وحدود التنفيذ':'Measured Results & Execution Limits','قائمة صريحة بما يعمل، وما اكتمل جزئيًا، وما لم يُنفذ.':'A clear list of what works, what is partial and what is not implemented.','الأداء حسب الاستراتيجية والأصل':'Performance by Strategy & Asset','تكاليف فعلية ونتائج محققة':'Actual costs and realized results','تغطية المدارس والوظائف':'School & Function Coverage','الجزئي وغير المنفذ لا يُقدمان كصوت صالح':'Partial and unimplemented schools do not vote','التحقق الكمي':'Quantitative Validation','نتائج تاريخية قبل الاعتماد':'Historical results before approval','سجل دائم قابل للتتبع':'Persistent Traceable Audit','القرارات والعمليات':'Decisions & Operations','لماذا دخل؟ لماذا خرج؟ لماذا انتظر؟ وما الذي ينقصه؟':'Why did it enter, exit or wait, and what is missing?','جمع التشخيص':'Export Diagnostics','سجل القرارات والأعطال':'Decision & Error Log','كل الأحداث':'All Events','أعطال ورفض':'Errors & Rejections','عمليات تداول':'Trading Events','مخاطر':'Risk','نتيجة التشخيص':'Diagnostic Result',
    'الإعداد الأول':'Initial Setup','اتصل، ثم تحقق.':'Connect, then verify.','افتح MT5 وسجل الدخول بحساب Demo قبل الاتصال.':'Open MT5 and sign in to a Demo account before connecting.','محلي على Windows':'Local on Windows','منصة MetaTrader 5':'MetaTrader 5 Platform','اتصال بالمنصة وفحص الحساب':'Connect & Verify Account','جسر الجلسات والتقويم':'Sessions & Calendar Bridge','تثبيت ملفات الجسر في المنصة':'Install Bridge Files','تجربة محلية ببيانات اصطناعية':'Local Synthetic Simulation','تشغيل المحاكاة المحلية':'Start Local Simulation','تسلسل التشغيل':'Operating Sequence','حالة الخدمات والموارد':'Services & Resources','AI شبكي':'Neural AI','ذكاء كمي · غرفة العمليات':'Quant intelligence · Operations room','تحليل · قراءة فقط':'Analytics · Read only','أخضر':'Green','أزرق':'Blue','رمادي':'Gray','رملي':'Sand','أبيض':'White','العربية':'Arabic','جاري فحص الخدمة':'Checking Service','المخاطرة المتبقية':'Remaining Risk','المستخدمة':'Used','الحد':'Limit','الخسائر المحققة المحتسبة':'Counted Realized Losses','الخسائر العائمة المحتسبة':'Counted Floating Losses','المخاطرة المحجوزة':'Reserved Risk','محقق قبل التكاليف':'Realized Before Costs','عائم':'Floating','تكاليف المنظومة المنسوبة':'Attributed System Costs','تكاليف غير منسوبة':'Unattributed Costs','رجوع':'Back','تأكيد':'Confirm','قراءة فقط':'Read Only','تجريبي تلقائي':'Automatic Demo','تجريبي بموافقة يدوية':'Manual Demo','لا توجد فرص مؤهلة معروضة.':'No qualified opportunities are displayed.','لا توجد نتائج.':'No Results','لا توجد نتائج مؤكدة':'No Confirmed Results','منفذ':'Implemented','منفذ جزئيًا':'Partial','غير منفذ':'Not Implemented','مرفوض':'Rejected','نشط':'Active','متصل':'Connected','غير متصل':'Disconnected','انتظار':'Wait','شراء':'Buy','بيع':'Sell'
  };
  Object.assign(en,{
    'حاسبات التقييم المالي المحلية':'Local financial valuation calculators',
    'أدخل سيناريو ماليًا موثق المصدر بصيغة بيانات منظمة. المدخلات يزودها المستخدم ولا تتحقق منها المنصة تلقائيًا. الحساب لا يمنح صلاحية تداول ولا يمثل قيمة عقد الوسيط.':'Enter a documented financial scenario in structured data. Inputs are supplied by the user and are not automatically verified by the platform. The calculation grants no trading authority and does not represent the broker contract value.',
    'النماذج المتاحة: القيمة الحالية، التدفقات النقدية المخصومة، خصم الأرباح، صافي الأصول، المضاعفات، وتسعير السند عند حد دفعة الكوبون. يجب أن تتوافق فترة التدفقات مع فترة معدل الخصم، ويجب تسجيل المصدر ووقت النشر ووقت التقييم.':'Available models: present value, discounted cash flow, dividend discount, net assets, multiples and bond pricing at a coupon boundary. Cash-flow periods must match discount-rate periods. Record the source, publication time and valuation time.',
    'مدخلات السيناريو المالي':'Financial scenario inputs',
    'إدراج مثال اصطناعي معلن':'Insert labeled synthetic example',
    'احسب السيناريو محليًا':'Calculate scenario locally',
    'لا توجد نتيجة تقييم مالي محفوظة.':'No stored financial valuation result.',
    'القيمة الحالية':'Present value',
    'التدفقات النقدية المخصومة':'Discounted cash flow',
    'خصم الأرباح':'Dividend discount',
    'صافي الأصول':'Net asset value',
    'المضاعفات المالية':'Financial multiples',
    'تسعير السند':'Bond pricing',
    'نموذج مالي غير معروف':'Unknown financial model',
    'قيمة المنشأة':'Enterprise value',
    'قيمة حقوق الملكية':'Equity value',
    'القيمة لكل سهم':'Value per share',
    'القيمة النهائية المخصومة':'Discounted terminal value',
    'السعر عند حد دفعة الكوبون':'Price at coupon boundary',
    'مضاعف المقارنة الوسيط':'Median peer multiple',
    'سيناريو يقدمه المستخدم؛ لم يتحقق مصدر مالي مستقل من مدخلاته. الحساب حساس للافتراضات ولا يمنح صلاحية إرسال أوامر.':'User-supplied scenario; inputs have not been independently verified. Calculations are sensitive to assumptions and grant no order-sending authority.',
    'وقت التقييم':'Valuation time',
    'وقت نشر المدخلات':'Input publication time',
    'نسبة القيمة النهائية من قيمة المنشأة':'Terminal share of enterprise value',
    'بصمة المدخلات':'Input fingerprint',
    'أُدرج مثال اصطناعي للتوضيح؛ الأرقام ليست بيانات سوق أو شركة فعلية.':'A synthetic illustrative example was inserted; figures are not actual market or company data.',
    'أدخل كائن بيانات منظمًا صالحًا قبل حساب السيناريو.':'Enter a valid structured data object before calculating the scenario.',
    'حُسب السيناريو المالي محليًا دون توصية تداول.':'The financial scenario was calculated locally without a trading recommendation.',
    'Quant Trading AI — مؤسسة التداول التجريبي':'Quant Trading AI — Demo Trading Institution','Quant Trading AI الرئيسية':'Quant Trading AI Home','إصدار تجريبي قيد التحقق':'Demo Release Under Validation','مساحة العمل المحلية':'Local Workspace','تنفيذ على حساب تجريبي فقط':'Demo-account execution only','غرفة العمليات':'Operations Room','التنقل الرئيسي':'Main navigation','تعمل على جهازك':'Runs on this device','حالة اليوم وسجل القرارات محفوظان محليًا':'Today’s state and decision log are stored locally','فتح القائمة':'Open menu','لغة الواجهة':'Interface language','ألوان الواجهة':'Interface theme','تحديث البيانات':'Refresh data','بيانات اصطناعية • محاكاة محلية':'Synthetic Data • Local Simulation','هذه الأسعار والنتائج للتجربة فقط؛ ليست سوقًا حيًا ولا اتصالًا بالوسيط.':'These prices and results are for testing only; they are neither a live market nor a broker connection.','إدارة مصدر البيانات ←':'Manage data source ←','دون تنفيذ':'No Execution','لم تُستلم بيانات بعد':'No data received yet','رصيد الحساب':'Account Balance','عملة الحساب غير متاحة':'Account currency unavailable','قيمة الحساب':'Account Equity','الرصيد + الربح والخسارة العائمة':'Balance plus floating profit and loss','الحساب المتصل':'Connected Account','افتح الإعداد للاتصال بمنصة MT5':'Open Setup to connect to MT5','نوع الحساب غير معروف':'Unknown account type','حدد الحد والهدف قبل منح صلاحية الدخول.':'Set the limit and target before authorizing entries.','وحدة القيم':'Value unit','مبلغ بعملة الحساب':'Account-currency amount','نسبة من Equity %':'Percentage of Equity %','قيمة المخاطرة اليومية المسموحة':'Allowed daily risk','أدخل القيمة':'Enter a value','ميزانية مشتركة لكل صفقات المنظومة.':'Shared budget for all system trades.','الهدف اليومي الصافي':'Net daily target','بعد احتساب التكاليف الفعلية.':'After actual costs.','المخاطرة ميزانية يومية إجمالية مشتركة بين الصفقات، وحدّ تقديري قد تتجاوزه الفجوات والانزلاق. الأرباح لا تزيد الميزانية تلقائيًا، والهدف لا يضمن الربح.':'Risk is one daily budget shared by all trades. It is an estimate that gaps and slippage can exceed. Profits do not automatically increase the budget, and the target does not guarantee profit.','تلقائي':'Automatic','دون موافقة لكل صفقة':'No approval for each trade','موافقة يدوية':'Manual approval','اعتماد النية قبل إرسالها':'Approve an intent before sending it','افتراضات التكاليف':'Cost assumptions','تُحتسب عند تحديد الحجم':'Applied during position sizing','عمولة دورة كاملة لكل لوت':'Round-trip commission per lot','أدخل عمولة الوسيط':'Enter broker commission','فتح + إغلاق بعملة الحساب. أدخل 0 صراحة إذا لا توجد عمولة.':'Open plus close in account currency. Enter 0 explicitly when there is no commission.','احتياطي الانزلاق بالنقاط':'Slippage reserve in points','قيمة محافظة عند حساب الحجم.':'A conservative position-sizing value.','ابدأ التداول التجريبي التلقائي':'Start Automatic Demo Trading','تتحقق طبقة التنفيذ من الحساب والمخاطرة قبل كل إرسال.':'The execution layer validates the account and risk before every send.','Ⅱ إيقاف الدخول الجديد':'Ⅱ Stop New Entries','إلغاء أوامر المنظومة':'Cancel System Orders','إغلاق مراكز المنظومة':'Close System Positions','تعتمد الميزانية على نتائج اليوم المحفوظة؛ إعادة التشغيل لا تمحوها.':'The budget uses stored daily results; restarting does not erase them.','من':'of','هدف غير محدد':'Target not set','يُعرض التقدم وفق حساب المحرك، مع فصل الربح المحقق والعائم والتكاليف.':'Progress follows the engine calculation, separating realized profit, floating profit and costs.','خريطة الأسواق ←':'Market map ←','لم تبدأ دورة مسح.':'No scan cycle has started.','↻ فحص الرموز المتاحة':'↻ Scan Available Symbols','عرض الأدلة ←':'View evidence ←','عند توافر البيانات تظهر الفرص وأسباب الدخول أو الانتظار هنا.':'When data is available, opportunities and reasons to enter or wait appear here.','↻ بدء دورة مسح':'↻ Start Scan','0 رمز':'0 symbols','ابحث بالرمز أو فئة الأصل أو سبب الاستبعاد':'Search by symbol, asset class or exclusion reason','بحث الرموز':'Search symbols','تصفية الأهلية':'Filter eligibility','رمز الشارت':'Chart symbol','فريم الشارت':'Chart timeframe','شارت الشموع ومستويات التحليل':'Candlestick chart and analysis levels','اختر رمزًا لعرض أسعار الوسيط وبطاقات التحليل.':'Select a symbol to display broker prices and analysis cards.','لن يُرسم شارت قبل استلام بيانات صالحة.':'The chart is drawn only after valid data is received.','تُدار المراكز المفوضة فقط':'Only authorized positions are managed','هوية ثابتة تمنع تكرار الإرسال':'A stable identifier prevents duplicate sends','تظهر هنا نتائج التحقق الكمي المتاحة وحالة اعتماد الاستراتيجيات.':'Available quantitative-validation results and strategy approval status appear here.','↓ جمع التشخيص':'↓ Export Diagnostic Report','↓ تصدير تقرير التشخيص':'↓ Export Diagnostic Report','ينشئ ملفًا محليًا قابلًا للمراجعة بالذكاء الصناعي دون أسرار الاتصال':'Creates a local AI-readable report without connection secrets','ابحث في الأسباب والرموز والعمليات':'Search reasons, symbols and operations','بحث السجل':'Search log','تصفية السجل':'Filter log','اضغط «جمع التشخيص» لإنشاء تقرير حالة النظام دون أسرار الاتصال.':'Click “Export Diagnostic Report” to create an AI-readable system report without connection secrets.','اضغط «تصدير تقرير التشخيص» لإنشاء تقرير حالة محلي قابل للمراجعة دون أسرار الاتصال.':'Click “Export Diagnostic Report” to create a local reviewable system report without connection secrets.','مسار تطبيق المنصة':'Platform application path','اختياري للاكتشاف التلقائي':'Optional when auto-discovery is available','مسار ملف الجسر JSON':'JSON bridge-file path','حساب Demo فقط. الحساب الحقيقي وحساب المسابقة والنوع غير المعروف مرفوضة داخل طبقة التنفيذ، حتى لو تغير الحساب أثناء التشغيل.':'Demo account only. Real, contest and unknown account types are rejected by the execution layer, even if the account changes while running.','أضف الجسر إلى شارت في MT5 لقراءة جلسات الوسيط والتقويم. الجسر يقرأ البيانات فقط؛ إرسال الأوامر مسؤولية محرك Quant Trading AI.':'Attach the bridge to one MT5 chart to read broker sessions and the calendar. The bridge only reads data; the Quant Trading AI engine sends orders.','بعد التثبيت: افتح Navigator في MT5، حدّث Expert Advisors، وأضف Quant Trading AI إلى أي شارت. غياب بيانات الجسر يمنع الدخول عندما تكون مطلوبة.':'After installation, open Navigator in MT5, refresh Expert Advisors, and attach Quant Trading AI to any chart. Missing bridge data blocks entries when that data is required.','محاكاة':'Simulation','اختبر الواجهة ومسار القرارات والمخاطر دون منصة أو وسيط. تظهر علامة المحاكاة على كامل التطبيق، وتبقى النتائج منفصلة عن التداول الفعلي.':'Test the interface and the decision and risk paths without a platform or broker. Simulation is clearly marked throughout the app and its results remain separate from broker trading.','اتصل بحساب Demo':'Connect a Demo account','تحقق من هوية الحساب والسيرفر ونوعه.':'Verify the account identity, server and type.','افحص الأسواق':'Scan markets','انتظر اكتمال دورة المسح وراجع الاستبعادات.':'Wait for the scan cycle to finish and review exclusions.','حدد المخاطرة والهدف':'Set risk and target','امنح تفويض اليوم من الشاشة الرئيسية.':'Grant today’s authorization from the overview.','راقب القرارات':'Monitor decisions','يختار النظام الانتظار عندما لا توجد فرصة مؤهلة.':'The system waits when no qualified opportunity exists.','Quant Trading AI · مؤسسة تداول تجريبي محلية':'Quant Trading AI · Local Demo Trading Institution','لا يوجد تفويض بالتنفيذ':'No execution authorization','توقيت العرض: دبي UTC+4':'Display time: Dubai UTC+4',
    'محايد':'Neutral','رفض':'Reject','إعداد مكتمل':'Setup Ready','بيانات ناقصة':'Missing Data','بيانات غير صالحة':'Invalid Data','قديم':'Stale','غير معروف':'Unknown','شموع مفحوصة':'Validated Bars','مقترح':'Proposed','معتمد':'Approved','جارٍ الإرسال':'Sending','أُرسل':'Sent','مقبول':'Accepted','تنفيذ جزئي':'Partially Filled','ملغى':'Cancelled','نتيجة غير محسومة':'Unresolved','لم يُفحص بعد':'Not Checked Yet','بانتظار الموافقة':'Pending Approval','عطل':'Error','متوقف':'Stopped','تجريبي':'Demo','حقيقي — مرفوض':'Real — Rejected','مسابقة — مرفوض':'Contest — Rejected','مفتوح':'Open','مغلق':'Closed','متاح':'Available','غير متاح':'Unavailable','سليم':'OK','غير مختبر':'Untested','موقوف':'Halted','بلغ الهدف — جارٍ تأكيد الخروج':'Target Reached — Confirming Exit','بلغ حد المخاطرة':'Risk Limit Reached','مركز موحد لكل رمز':'Netting Position per Symbol','مراكز متعددة لكل رمز':'Multiple Positions per Symbol','فوركس':'Forex','معادن':'Metals','مؤشرات':'Indices','طاقة':'Energy','أسهم':'Stocks','أصول رقمية':'Crypto Assets','عقود آجلة':'Futures','أخرى':'Other','الدخول الجديد متوقف':'New Entries Stopped','تعذر التحقق من البيانات':'Data Validation Failed','غير مفعل':'Disabled','عينة غير كافية':'Insufficient Sample','غير مؤهل':'Ineligible','مؤهل للبحث التجريبي':'Qualified for Demo Research','قرار لجنة الأبحاث':'Research Committee Decision','اتصال للقراءة فقط':'Read-only Connection','إلغاء تفويض التنفيذ':'Execution Authorization Revoked','إجراء مرفوض':'Action Rejected','تعذر تحليل الرمز':'Symbol Analysis Failed','أُرسل أمر إلى الوسيط':'Order Sent to Broker','تنفيذ مؤكد لدى الوسيط':'Broker Fill Confirmed','إنشاء نية تداول':'Trading Intent Created','رفض محرك المخاطر':'Risk Engine Rejection','مطابقة العمليات مع الوسيط':'Broker Reconciliation','حديث بحسب وقت النشر':'Fresh by Publication Time','المصدر قديم أو غير متاح':'Source Stale or Unavailable',
    'السعر':'Price','المنطقة':'Zone','شرط الدخول':'Entry Trigger','تحقق الشرط':'Trigger Met','التوقيت':'Time','شمعة الإشارة':'Signal Bar','شرط الإبطال':'Invalidation Condition','طريقة التقييم':'Evaluation Method','طريقة الاشتقاق':'Derivation Method','النسبة':'Ratio','نوع الدليل':'Evidence Type','الدليل':'Evidence','القيمة':'Value','رقم الشمعة':'Bar Index','تأكيد المستوى':'Level Confirmation','التغطية':'Coverage','السبب':'Reason','التفسير':'Explanation','جني الربح':'Take Profit','الحد الأقصى لشموع الاحتفاظ':'Maximum Holding Bars','الفريم':'Timeframe','أهداف جزئية':'Partial Targets','حماية الربح عند':'Break Even At','السماح بالإضافة':'Allow Addition','الوقف لا يتسع':'Stop May Only Tighten','إبطال السيناريو':'Scenario Invalidation','الحالة':'Status','المصدر':'Source','الهوية':'ID','الرمز':'Symbol','الاتجاه':'Side','الحجم':'Volume','وقف التنفيذ':'Execution Stop','الهدف':'Target','الربح':'Profit','التبييت':'Swap','العمولة':'Commission','الرسوم':'Fees','ملكية المنظومة':'System Ownership','التعليق':'Comment','رقم الوسيط':'Broker Ticket','المتوقع':'Forecast','الفعلي':'Actual','السابق':'Previous','المراجع':'Revised','اختياري عند الاكتشاف التلقائي':'Optional when auto-discovery is available'
  });
  Object.assign(en,{
    'نعم':'Yes','لا':'No','أحداث سياسية شاملة':'Broad Political Events','أخبار عاجلة شاملة':'Broad Breaking News','ملاحظة':'Note','مصادر رسمية':'Official Sources','الذاكرة بالغيغابايت':'Memory in GB','عدد الأنوية':'CPU Count','النموذج':'Model','متحقق':'Verified','احتياطي تكلفة الإغلاق':'Estimated Exit Cost','المحقق الصافي':'Realized Net','تعرض خارجي':'External Exposure','نظام التشغيل':'Operating System','أنوية منطقية':'Logical CPUs','النموذج المحلي':'Local Model','إجمالي الذاكرة GB':'Total Memory GB','الذاكرة المتاحة GB':'Available Memory GB',
    'الخدمة لم تُرجع بيانات صالحة. أعد تشغيل Quant Trading AI من ملف التشغيل.':'The service did not return valid data. Restart Quant Trading AI from its executable.','انتهت مهلة الاتصال. قد تكون العملية أُرسلت؛ راجع سجل التنفيذ قبل أي محاولة جديدة.':'The request timed out. It may have been sent; review the execution log before trying again.','تعذر تنفيذ الإجراء.':'The action could not be completed.','تعذر الوصول إلى الخدمة المحلية.':'The local service is unavailable.','لم تكتمل أي دورة مسح؛ لا يمكن الادعاء بفحص السوق كله.':'No scan cycle has completed; the whole market cannot be claimed as scanned.','اجتاز الفحص المستقل':'Passed Independent Check','غير معلنة':'Not Declared','إبطال التحليل':'Analysis Invalidation','هدف':'Target','مصدر':'Source','قديم أو غير متاح':'Stale or Unavailable','الدخول':'Entry','السعر الحالي':'Current Price','الوقف / الهدف':'Stop / Target','الملكية':'Ownership','هوية النية':'Intent ID','المخاطرة':'Risk','سبب القرار / النتيجة':'Decision / Result Reason','آخر تحديث':'Last Update','المحقق قبل التكاليف':'Realized Before Costs','وظيفة':'Function','غير متاحة':'Unavailable','بيان التغطية غير مستلم.':'Coverage statement not received.','لا يعني غياب البيان اكتمال المدارس أو الوظائف.':'A missing statement does not mean all schools or functions are complete.','الرمز والفريم':'Symbol & Timeframe','نوع البيانات':'Data Type','الوسيط':'Broker','اصطناعية أو غير متحققة':'Synthetic or Unverified','التأهيل':'Qualification','الأسباب والحدود':'Reasons & Limits','لم تُستلم نتائج تحقق كمي مؤهلة. لا تُعرض جودة القواعد بوصفها احتمال نجاح.':'No eligible quantitative-validation results were received. Rule quality is not presented as a win probability.','حدث':'Event','مركز موحد لكل رمز (Netting)':'One Netting Position per Symbol','مراكز متعددة (Hedging)':'Multiple Hedging Positions','الاختبار':'Test','الصلاحية':'Validity',
    'النتائج تقيس استراتيجيات ثابتة على عينات زمنية خارج التدريب وبعد التكاليف. R وحدة مسافة الوقف، وليست ربحًا بعملة الحساب. نتيجة البحث لا تمنح التنفيذ تلقائيًا.':'Results measure fixed strategies on chronological out-of-training samples after costs. R is one stop-distance unit, not profit in account currency. Research results do not automatically authorize execution.','أدخل مخاطرة وهدفًا موجبين قبل التفعيل.':'Enter positive risk and target values before activation.','النسبة يجب ألا تتجاوز 100%.':'The percentage must not exceed 100%.','أدخل عمولة دورة كاملة معروفة لكل لوت، واحتياطيًا غير سالب للانزلاق.':'Enter a known round-trip commission per lot and a non-negative slippage reserve.','تم طلب تفعيل التفويض. راجع الحالة وقرار المخاطر.':'Authorization activation was requested. Review the status and risk decision.','أُرسل طلب إيقاف الدخول الجديد. راجع حالة المحرك.':'The request to stop new entries was sent. Review engine status.','إلغاء أوامر المنظومة':'Cancel System Orders','سيحاول النظام إلغاء أوامره المعلقة فقط، ثم يطابق النتيجة مع الوسيط قبل تحرير المخاطرة المحجوزة.':'The system will cancel only its pending orders, then reconcile the broker result before releasing reserved risk.','إلغاء الأوامر':'Cancel Orders','تم إرسال طلب الإلغاء؛ راجع نتائج الوسيط.':'The cancellation request was sent; review broker results.','إغلاق مراكز المنظومة':'Close System Positions','سيوقف النظام الدخول الجديد ويحاول إغلاق المراكز التي يملك تفويض إدارتها بالسعر المتاح. الإغلاق قد يختلف عن الربح المعروض؛ النتيجة تُؤكد بعد رد الوسيط والتكاليف.':'The system will stop new entries and try to close authorized positions at the available price. The result can differ from displayed profit and is confirmed after broker response and costs.','إغلاق المراكز':'Close Positions','تم طلب الإغلاق؛ لا يُعد مكتملًا قبل تأكيد الوسيط.':'Closure was requested; it is not complete until broker confirmation.','بدأ طلب فحص قائمة الرموز الكاملة.':'A full symbol-list scan was requested.','تم طلب الاتصال وفحص الحساب.':'Connection and account validation were requested.','تم طلب تثبيت ملفات الجسر.':'Bridge-file installation was requested.','تم التثبيت.':'Installed.','تفعيل محاكاة محلية':'Start Local Simulation','سيُستخدم مصدر اصطناعي واضح العلامة لاختبار التطبيق. نتائجه لا تثبت الربحية ولا الاتصال بمنصة MT5، ولا تُعد اختبارًا فعليًا لدى الوسيط.':'A clearly marked synthetic source will test the app. Its results do not prove profitability or an MT5 connection and are not a broker test.','بدء المحاكاة':'Start Simulation','تم طلب تفعيل المصدر الاصطناعي.':'Synthetic-source activation was requested.','تحقق كمي':'Quant Validation','حدد عمولة دورة كاملة لكل لوت في «تفويض اليوم» قبل الاختبار الكمي.':'Set the round-trip commission per lot in “Today’s Authorization” before quantitative validation.','جارٍ طلب التحقق…':'Requesting Validation…','طُلب التحقق الكمي؛ النتيجة لا تمنح صلاحية تنفيذ تلقائيًا.':'Quantitative validation was requested; its result does not automatically authorize execution.','إيقاف Quant Trading AI':'Stop Quant Trading AI','سيُلغى تفويض الدخول وتُغلق الخدمة المحلية. هذا الإجراء لا يغلق المراكز المفتوحة لدى الوسيط ولا يلغي أوامره. لإدارتها استخدم إجراءات المنظومة قبل الخروج.':'Entry authorization will be revoked and the local service closed. This does not close broker positions or cancel broker orders; use system actions before exiting.','إيقاف الخدمة':'Stop Service','أُوقفت الخدمة المحلية. يمكنك إغلاق هذه النافذة وإعادة التشغيل من ملف Quant Trading AI.':'The local service stopped. Close this window and restart from the Quant Trading AI executable.','أُرسِل طلب إيقاف الخدمة المحلية.':'The local-service shutdown request was sent.','الخدمة متوقفة':'Service Stopped','اعتماد نية تداول تجريبي':'Approve Demo Trading Intent','اعتماد النية':'Approve Intent','تم طلب اعتماد النية؛ راجع النتيجة.':'Intent approval was requested; review the result.','تم طلب جمع التشخيص.':'Diagnostic report export was requested.','تم إنشاء التقرير؛ راجع سجل العمليات للحصول على مساره.':'The report was created; review the operation log for its path.'
  });
  Object.assign(en,{
    'تجريبي فقط':'DEMO ONLY','الإنجليزية':'English','نسبة من قيمة الحساب %':'Percentage of Equity %','مسار ملف الجسر':'Bridge file path','توقيت العرض: دبي (التوقيت العالمي +4)':'Display time: Dubai (UTC+4)','Quant Trading AI — محاكاة محلية':'Quant Trading AI — Local Simulation',
    'افتح MT5 وسجل الدخول بحساب تجريبي قبل الاتصال.':'Open MT5 and sign in to a Demo account before connecting.','محلي على نظام ويندوز':'Local on Windows','محلي على ويندوز':'Local on Windows','منصة ميتاتريدر 5':'MetaTrader 5 Platform',
    'حساب تجريبي فقط. الحساب الحقيقي وحساب المسابقة والنوع غير المعروف مرفوضة داخل طبقة التنفيذ، حتى لو تغير الحساب أثناء التشغيل.':'Demo account only. Real, contest and unknown account types are rejected by the execution layer, even if the account changes while running.',
    'بعد التثبيت: افتح لوحة المستكشف في MT5، وحدّث قائمة المستشارين الآليين، ثم أضف جسر Quant Trading AI إلى أي شارت. غياب بيانات الجسر يمنع الدخول عندما تكون مطلوبة.':'After installation, open Navigator in MT5, refresh Expert Advisors, then attach the Quant Trading AI bridge to any chart. Missing bridge data blocks entries when required.',
    'اتصل بحساب تجريبي':'Connect a Demo account','اتصل بحساب تجريبي أو فعّل المحاكاة المحلية أولًا.':'Connect a Demo account or start local simulation first.',
    'لا يمكن التحويل دون توفر قيمة الحساب.':'Cannot convert without available Equity.','إجمالي الذاكرة بالغيغابايت':'Total Memory GB','الذاكرة المتاحة بالغيغابايت':'Available Memory GB',
    'جارٍ التحقق من طلب التفعيل الجديد':'Validating the new activation request'
  });
  Object.assign(en,{
    'داو والتحليل الكلاسيكي':'Dow Theory & Classical Analysis','حركة السعر والشموع':'Price Action & Candlesticks','الدعم والمقاومة':'Support & Resistance','الأنماط الانعكاسية الكلاسيكية':'Classical Reversal Patterns','الأنماط الهندسية':'Geometric Chart Patterns','الاختراق وإعادة الاختبار':'Breakout & Retest','صندوق دارفاس':'Darvas Box','إيشيموكو':'Ichimoku','فيبوناتشي':'Fibonacci','اتباع الاتجاه':'Trend Following','مؤشرات الزخم':'Momentum Indicators','مؤشرات التقلب':'Volatility Indicators','العودة إلى المتوسط والتحليل الإحصائي':'Mean Reversion & Statistical Analysis','متوسط السعر المرجح بالحجم والمرساة':'VWAP & Anchored VWAP','العلاقات بين الأصول':'Intermarket Relationships','الهارمونيك':'Harmonic Patterns','موجات إليوت':'Elliott Wave','وايكوف':'Wyckoff','مفاهيم الأموال الذكية والسيولة':'Smart Money Concepts, ICT & Liquidity','العرض والطلب':'Supply & Demand','اختلاف السيولة بين الأصول':'SMT Divergence','الموسمية':'Seasonality','جان ومربع التسعة والدورات الزمنية':'Gann, Square of Nine & Time Cycles','تدفق الأوامر':'Order Flow','نموذج القمتين':'Double Top','نموذج القاعين':'Double Bottom','نموذج الرأس والكتفين':'Head and Shoulders','نموذج الرأس والكتفين المعكوس':'Inverse Head and Shoulders','مثلث متماثل':'Symmetrical Triangle','مثلث صاعد':'Ascending Triangle','مثلث هابط':'Descending Triangle','نموذج انعكاسي':'Reversal Pattern','فحص نماذج انعكاسية':'Reversal Pattern Scan','نموذج هندسي':'Geometric Pattern',
    'شراء عند تحقق قاعدة الدخول المعلنة على شمعة مكتملة فقط':'Buy only after the declared completed-bar entry trigger','بيع عند تحقق قاعدة الدخول المعلنة على شمعة مكتملة فقط':'Sell only after the declared completed-bar entry trigger',
    'السوق مغلق حسب جلسة الوسيط':'Market closed according to the broker session','الأسعار مفقودة أو قديمة أو غير سليمة':'Quotes are missing, stale or invalid','السبريد مرتفع مقارنة بالنطاق الأخير':'Spread is high relative to the recent range','الدخول الجديد غير مسموح لهذا العقد':'New entries are not allowed for this contract','الجسر غير صالح: بيانات الجسر قديمة أو غير متصلة':'Bridge invalid: bridge data is stale or disconnected',
    'لا تغطية شاملة للأحداث السياسية أو الأخبار العاجلة؛ انعدام خبر ليس دليلًا على انعدام حدث.':'No comprehensive political-event or breaking-news coverage; no reported news does not prove no event exists.','مصدر صناعي للاختبار':'Synthetic Test Source','ليس مصدر أخبار حي':'Not a Live News Source','حديث':'Fresh','تم الوصول والفحص':'Reached and Checked',
    'التحقق التاريخي قيد التنفيذ':'Historical validation is running','غير مثبت؛ التحليل الحسابي لا يحتاج خدمة ذكاء اصطناعي مدفوعة':'Not installed; deterministic analysis does not require a paid AI service','القبول النهائي لم يجتز بعد؛ راجع تقرير التحقق المرفق.':'Final acceptance has not passed; review the attached validation report.','ويندوز':'Windows',
    'النتائج تقيس استراتيجيات ثابتة على عينات زمنية خارج التدريب وبعد التكاليف. وحدة المخاطرة تساوي مسافة وقف واحدة، وليست ربحًا بعملة الحساب. نتيجة البحث لا تمنح التنفيذ تلقائيًا.':'Results measure fixed strategies on chronological out-of-training samples after costs. One risk unit equals one stop distance, not account-currency profit. Research results do not automatically authorize execution.','العائد المتوقع بوحدة المخاطرة':'Expected Return in Risk Units','التراجع بوحدة المخاطرة':'Drawdown in Risk Units',
    'سعر البيع / سعر الشراء':'Bid / Ask','اكتمل التحقق الكمي':'Quantitative Validation Completed','فُعّل التفويض':'Authorization Activated','إعدادات اليوم':'Daily Settings','عاد الاتصال بوضع القراءة فقط':'Connection Restored in Read-only Mode',
    'حجم تداول حقيقي للشمعة أو مؤشر تغيرات معلّم بوضوح':'Real bar volume or a clearly labelled tick proxy','مرساة زمنية صريحة':'Explicit Time Anchor','شموع متزامنة للأصل المقارن':'Aligned Partner OHLC','تاريخ معدل لعدة سنوات':'Adjusted Multi-year History','صفقات محددة الاتجاه':'Signed Trades','عمق سوق تاريخي':'Historical Market Depth',
    'حدود اليوم السابق تظل محفوظة؛ أعد التفويض لحساب النتائج الحالية.':'Previous day limits remain stored; authorize again to calculate current results.','انقطاع الاتصال؛ يلزم مطابقة الحساب وإعادة التفعيل':'Connection was lost; reconcile the account and reactivate.','انقطاع MT5. الدخول الجديد متوقف.':'MT5 disconnected. New entries are stopped.',
    'RSS رسمي منشور للاشتراك؛ تعرض عناوين وروابط فقط مع نسبة المصدر.':'Official published RSS subscription; titles and links only, with source attribution.','مصدر حكومي رسمي؛ التوافر غير مضمون وقد يمنع الطلبات الآلية.':'Official government source; availability is not guaranteed and automated requests may be blocked.','الشروط تقيد بعض إعادة الاستخدام بغير التجاري؛ غير مفعل لهذه المؤسسة حتى مراجعة الترخيص.':'Terms restrict some non-commercial reuse; disabled for this institution pending licence review.'
  });
  Object.assign(en,{
    'الاحتياطي الفيدرالي':'Federal Reserve','البنك المركزي الأوروبي':'European Central Bank','مكتب إحصاءات العمل':'Bureau of Labor Statistics','بنك إنجلترا':'Bank of England','التقويم الاقتصادي للمنصة':'MT5 Economic Calendar',
    'RSS رسمي منشور للاشتراك؛ حقوق المصدر محفوظة، لا إعادة نشر مقالات كاملة.':'Official published RSS subscription; source rights are reserved and full articles are not republished.',
    'قد يرتبط البيان بالعملة والسياسة النقدية. اتجاه الأثر غير مستنتج من العنوان.':'The release may relate to the currency and monetary policy. The direction of impact is not inferred from the headline.',
    'عنوان رسمي؛ لا يمثل أخبارًا عاجلة شاملة':'Official headline; it does not provide comprehensive breaking-news coverage',
    'طلب إغلاق الخدمة':'Local service shutdown requested','إغلاق التطبيق؛ يلزم إعادة التفعيل':'Application closed; reactivation is required',
    'عدد الصفقات خارج العينة أقل من الحد المطلوب (fewer than required OOS trades)':'Fewer than the required out-of-sample trades',
    'معامل الربح خارج العينة غير قابل للقياس أو دون العتبة (OOS profit factor unmeasurable or below threshold)':'Out-of-sample profit factor is unmeasurable or below the threshold',
    'متوسط العائد بعد التكاليف غير موجب أو غير قابل للقياس (nonpositive or unmeasurable cost-adjusted expectancy)':'Cost-adjusted expectancy is nonpositive or unmeasurable',
    'الاستراتيجية لا تملك نتائج مؤهلة خارج العينة على بيانات الوسيط بعد التكاليف (strategy lacks eligible chronological cost-adjusted broker OOS evidence)':'The strategy lacks eligible chronological cost-adjusted broker out-of-sample evidence',
    'التغطية المطلوبة للأخبار أو التقويم ناقصة أو قديمة، أو يقع الوقت داخل حظر حدث (required news/calendar coverage missing, stale, or in event blackout)':'Required news or calendar coverage is missing or stale, or the time falls within an event blackout',
    'السعر الحالي خارج منطقة الدخول المعتمدة (current quote outside approved entry zone)':'The current quote is outside the approved entry zone',
    'الفريمات تختلف في الاتجاه (timeframes disagree)':'Timeframes disagree',
    'مدارس ذات إعداد دخول مفعّل تختلف في الاتجاه (triggered schools disagree)':'Triggered schools disagree',
    'عدد عائلات الأدلة أقل من اثنتين بعد تجميع المؤشرات المترابطة (fewer than two distinct evidence families after dependency grouping)':'Fewer than two distinct evidence families remain after dependency grouping',
    'التراجع خارج العينة يتجاوز الحد الثابت (OOS drawdown exceeds fixed threshold)':'Out-of-sample drawdown exceeds the fixed threshold',
    'انتظار: لا يوجد إعداد دخول مكتمل ومفعّل وحديث (no fresh completed and triggered entry setup)':'Wait: no fresh, completed and triggered entry setup exists',
    'السبريد يتجاوز 20% من مسافة الوقف المقترح (spread exceeds 20 percent of proposed stop distance)':'Spread exceeds 20% of the proposed stop distance',
    'فشل تأهيل السوق أو الجلسة أو حداثة البيانات (market eligibility, session or freshness failed)':'Market eligibility, session or data-freshness validation failed',
    'تعذر تحويل التكاليف لوحدات السعر':'Costs could not be converted to price units',
    'يلزم دليل متوافق من فريمين مكتملين على الأقل (need corroborating evidence on at least two completed timeframes)':'Corroborating evidence is required on at least two completed timeframes',
    'محقق خلال اليوم؛ لا يشمل مسار Equity داخل الصفقة':'Realized during the day; excludes the intratrade Equity path',
    'VWAP وAnchored VWAP':'VWAP and Anchored VWAP','SMC وICT والسيولة':'SMC, ICT and Liquidity'
  });
  Object.assign(en,{
    '100 × عدد الشروط المتحققة ÷ إجمالي الشروط؛ صفر عند غياب الشروط. هذه درجة تحقق القواعد وليست احتمال نجاح':'100 × met conditions ÷ total conditions; zero when no conditions are present. This is a rule-completion score, not a win probability.',
    '300 شمعة داخل اليوم لا تكفي لإثبات الموسمية':'300 intraday bars cannot establish seasonality.',
    'RSI بمتوسط ربح وخسارة بسيط متحرك وليس تنعيم وايلدر':'Simple rolling gain/loss RSI; deliberately not Wilder smoothing.',
    'أعلى درجة فقط لكل عائلة أدلة مترابطة؛ يلزم عائلتان على الأقل، ومعايير كمية ثابتة':'Keep only the highest score in each dependent evidence family; at least two families and fixed quantitative criteria are required.',
    'تجميع الأدلة يقلل العد المكرر للمؤشرات المترابطة ولا يثبت استقلالها الإحصائي':'Evidence grouping reduces duplicate counting of correlated indicators; it does not prove statistical independence.',
    'محرك المخاطر المستقل يملك حق الرفض النهائي؛ اللجنة لا ترسل الأوامر':'The independent risk engine has final veto authority; the committee does not send orders.',
    'جلسة صناعية للاختبار':'Synthetic test session.',
    'عقد صناعي للاختبارات':'Synthetic test contract.',
    'متصل للقراءة. التفويض يبدأ فقط بعد إدخال حدود اليوم والضغط على ابدأ.':'Connected in read-only mode. Authorization starts only after entering today’s limits and pressing Start.',
    'بدأ فحص جميع رموز المنصة؛ تابع عداد الإنجاز.':'Scanning all platform symbols has started; follow the progress counter.',
    'اعتمد تفويض Demo وحدود اليوم المحفوظة. ينتظر النظام فرصة تستوفي جميع الفحوص.':'Demo authorization and today’s stored limits are active. The system is waiting for an opportunity that passes every check.',
    'أوقف الدخول الجديد؛ تستمر إدارة المراكز ضمن التفويض القائم.':'New entries are stopped; authorized positions continue to be managed.',
    'سجلت محاولات إلغاء أوامر المنظومة؛ التأكيد من الوسيط ظاهر في السجل.':'System-order cancellation attempts were recorded; broker confirmation appears in the log.',
    'أوقف الدخول الجديد وسجل محاولات إغلاق مراكز المنظومة؛ تحقق من تأكيد الوسيط والنتائج.':'New entries were stopped and system-position close attempts were recorded; verify broker confirmations and results.',
    'حدّث الشارت وبطاقات المدارس من الشموع المكتملة.':'The chart and school cards were updated from completed bars.',
    'بدأ التحقق التاريخي بالترتيب الزمني؛ نتائجه تظهر في الأداء.':'Chronological historical validation has started; its results appear under Performance.',
    'جُمعت ملفات التشخيص محليًا. لا ترفع تلقائيًا. راجع أرقام الحساب والتذاكر قبل مشاركتها.':'Diagnostic files were created locally and are not uploaded automatically. Review account and ticket numbers before sharing.',
    'نتيجة فحص الموافقة مسجلة في السجل.':'The approval-check result was recorded in the log.',
    'الإجراء في قائمة العمل؛ ستظهر نتيجته وحالته في السجل.':'The action is queued; its result and status will appear in the log.',
    'إجراء غير معروف':'Unknown action.',
    'الخدمة توقفت؛ أعد تشغيل التطبيق':'The service has stopped; restart the application.',
    'توقف العامل قبل تأكيد نتيجة الإجراء؛ لا تُعد إرساله تلقائيًا':'The worker stopped before confirming the action result; do not submit it again automatically.',
    'اتصل بـMT5 Demo أو اختر المحاكاة أولًا':'Connect an MT5 Demo account or select local simulation first.',
    'رمز أو فريم غير معتمد':'Unsupported symbol or timeframe.',
    'اختر رمزًا وفريمًا أولًا':'Select a symbol and timeframe first.',
    'الاقتراح غير متاح أو منتهي؛ أعد الفحص':'The proposal is unavailable or expired; run the scan again.',
    'انتهت صلاحية الاقتراح':'The proposal expired.',
    'دليل التحقق الكمي منتهي أو تغيرت نسخته أو تكاليفه؛ أعد التحقق':'The quantitative-validation evidence expired or its version or costs changed; validate again.',
    'نتائج المحاكاة لا تمنح أهلية تنفيذ على الوسيط':'Simulation results do not authorize broker execution.',
    'السعر خارج منطقة الدخول':'The current price is outside the entry zone.',
    'توجد مراكز أو أوامر في المصدر الحالي؛ أدرها أو أعد تشغيل التطبيق قبل تبديل المصدر.':'The current source has positions or orders; manage them or restart the application before changing the source.',
    'انقطع اتصال MT5 وأعيد ربطه؛ يلزم تفعيل Demo من جديد':'The MT5 connection was restored; Demo authorization must be activated again.',
    'أعيد فتح قناة MT5 لكن المنصة غير متصلة بالخادم':'The MT5 channel reopened, but the terminal is not connected to its server.',
    'تعذر تحويل العمولة لوحدات السعر':'Commission could not be converted to price units.',
    'تكاليف البحث تختلف عن التفويض القائم؛ استخدم القيم المعتمدة أو أعد التفويض.':'Research costs differ from the active authorization; use the authorized values or authorize again.',
    'تكاليف معروفة وغير سالبة مطلوبة للتحقق التاريخي':'Known, non-negative costs are required for historical validation.',
    'الاستراتيجية الجزئية أو غير المنفذة لا يمكن تأهيلها':'A partial or unimplemented strategy cannot be qualified.',
    'التاريخ غير كافٍ لتقسيم التدريب والحظر والاختبار زمنياً':'History is insufficient for chronological training, embargo and test partitions.',
    'بيانات اصطناعية أو محاكاة أو غير موثقة لا تؤهل التنفيذ لدى الوسيط':'Synthetic, simulated or unverified data cannot qualify broker execution.',
    'عدد الصفقات خارج العينة أقل من الحد المطلوب':'The number of out-of-sample trades is below the required minimum.',
    'معامل الربح خارج العينة غير قابل للقياس أو دون العتبة':'Out-of-sample profit factor is unmeasurable or below the threshold.',
    'متوسط العائد بعد التكاليف غير موجب أو غير قابل للقياس':'Cost-adjusted expectancy is non-positive or unmeasurable.',
    'التراجع خارج العينة يتجاوز الحد الثابت':'Out-of-sample drawdown exceeds the fixed limit.',
    'شهادة التحقق الكمي منتهية أو وقت فحصها غير متسق':'The quantitative-validation certificate expired or has an inconsistent check time.',
    'نتائج التحقق الكمي لا تطابق الإصدار أو الرمز أو الفريم':'Quantitative-validation results do not match the version, symbol or timeframe.',
    'وقت بيانات التحقق الكمي مفقود أو يقع في المستقبل':'The quantitative-validation data time is missing or in the future.',
    'التغطية المطلوبة للأخبار أو التقويم ناقصة أو قديمة، أو يقع الوقت داخل حظر حدث':'Required news or calendar coverage is missing or stale, or the time falls within an event blackout.',
    'الفريمات تختلف في الاتجاه':'Timeframes disagree.',
    'مدارس ذات إعداد دخول مفعّل تختلف في الاتجاه':'Triggered schools disagree.',
    'عدد عائلات الأدلة أقل من اثنتين بعد تجميع المؤشرات المترابطة':'Fewer than two distinct evidence families remain after dependency grouping.',
    'يلزم دليل متوافق من فريمين مكتملين على الأقل':'Corroborating evidence is required on at least two completed timeframes.',
    'أسعار الدخول أو الوقف أو الهدف ناقصة أو غير صالحة':'Entry, stop or target prices are missing or invalid.',
    'يجب أن يقع سعر الدخول بين الوقف والهدف في اتجاه الصفقة':'Entry must lie between the stop and target in the trade direction.',
    'فشل تأهيل السوق أو الجلسة أو حداثة البيانات':'Market eligibility, session or data-freshness validation failed.',
    'السبريد يتجاوز 20% من مسافة الوقف المقترح':'Spread exceeds 20% of the proposed stop distance.',
    'السعر الحالي خارج منطقة الدخول المعتمدة':'The current quote is outside the approved entry zone.',
    'انتظار: لا يوجد إعداد دخول مكتمل ومفعّل وحديث':'Wait: no fresh, completed and triggered entry setup exists.',
    'تحقق الدخول مع اتفاق الفريمات وعائلات أدلة مختلفة؛ اكتملت الأخبار المطلوبة واجتازت الاستراتيجية معايير خارج العينة الثابتة':'The entry trigger, timeframe agreement, independent evidence families, required news coverage and fixed out-of-sample gates all passed.',
    'Quant Trading AI مفتوح بالفعل. استُخدمت النافذة الحالية بدل تشغيل نسخة ثانية.':'Quant Trading AI is already open. The existing window was used instead of starting a second instance.',
    'ثبت جسر القراءة. في MT5 افتح Navigator ثم Refresh، واسحب QuantTradingAI_ReadOnlyBridge إلى أي شارت. لا يحتوي الجسر أوامر تداول.':'The read bridge was installed. In MT5 open Navigator, choose Refresh, and attach QuantTradingAI_ReadOnlyBridge to any chart. The bridge contains no trading commands.'
  });
  Object.assign(en,{
    'اسم النموذج':'Pattern Name','نوع النموذج':'Pattern Type','نقاط الانقلاب المؤكدة':'Confirmed Swings',
    'خط العنق السابق':'Previous Neckline','خط العنق الحالي':'Current Neckline','الهدف المحسوب':'Calculated Target',
    'ارتفاع النموذج':'Pattern Height','هامش التطابق':'Match Tolerance','فرق الكتفين':'Shoulder Difference',
    'آخر تأكيد لنقطة انقلاب':'Latest Confirmed Pivot','ميل الحد العلوي لكل شمعة':'Upper Boundary Slope per Bar',
    'ميل الحد السفلي لكل شمعة':'Lower Boundary Slope per Bar','خطأ ملاءمة الحد العلوي':'Upper Boundary Fit Error',
    'خطأ ملاءمة الحد السفلي':'Lower Boundary Fit Error','الارتفاع الأولي':'Initial Height','الارتفاع الحالي':'Current Height',
    'الحد العلوي الحالي':'Current Upper Boundary','الحد السفلي الحالي':'Current Lower Boundary',
    'الإغلاقات السابقة داخل النموذج':'Prior Closes Inside Pattern','قمة':'High Pivot','قاع':'Low Pivot'
  });
  Object.assign(en,{
    'بانتظار تأكيد الوسيط؛ لن يُعاد إرسال الطلب':'Broker confirmation pending; request will not be resent',
    'نتيجة الوسيط لم تُحسم؛ يلزم المطابقة وإعادة التفعيل':'Broker result remains unresolved; reconciliation and reactivation are required',
    'المركز المنفذ غير ظاهر ولم يتأكد خروجه بعد':'Filled position is absent without confirmed exit'
  });
  Object.assign(en,{
    'متوافق':'Aligned','سياق مفحوص':'Evaluated context','متعارض':'Conflicting','لم يُفحص':'Not evaluated',
    'حياد مفحوص':'Evaluated neutral','سياق متوافق':'Aligned context','تقاطع المدارس الأربع':'Four-school confluence',
    'بروتوكول القرار':'Decision protocol','تقاطع المدارس الأربع — عائد لا يقل عن ١:٢':'Four-school confluence — at least 1:2 reward/risk',
    'التوقيت نموذج محلي معلن. الحجم الحقيقي عند السعر يظهر غير متاح عند غياب مصدره؛ الهدف اليومي لا يضمن الربح.':'Timing is a declared local model. Real volume at price is unavailable without its source; the daily target does not guarantee profit.',
    'خيارات السكالب والمخاطرة والهدف':'Scalping, risk and target options','نمط السكالب':'Scalping mode','إيقاف السكالب':'Scalping off',
    'سكالب عادي — دقيقة وخمس دقائق':'Normal scalping — M1 and M5','سكالب عالي التردد — متابعة محلية أسرع':'Fast scalping — faster local monitoring',
    'يتشارك السكالب ميزانية خسارة الحساب. النمط الأسرع محلي على منصة التداول؛ لا يمثل بنية تداول بورصية فائقة السرعة.':'Scalping shares the account loss budget. The faster mode runs locally on the trading terminal; it is not exchange HFT infrastructure.',
    'إعدادات السكالب العادي':'Normal scalp settings','إعدادات السكالب المتسارع':'Fast scalp settings',
    'مخاطرة الصفقة % من قيمة الحساب':'Trade risk as % of Equity','هدف السكالب الصافي بعملة الحساب':'Net scalp target in account currency',
    'الحد الأدنى للعائد مقابل المخاطرة':'Minimum reward/risk ratio','حدد النسبة':'Set the percentage','حدد الهدف':'Set the target',
    'تُقيّد المخاطرة المطلوبة بالميزانية المتبقية وحد الصفقة المشترك.':'Requested risk is capped by the remaining budget and shared per-trade limit.',
    'المخاطرة المطلوبة':'Requested risk','حد تقديري ضمن الميزانية المشتركة':'Estimated cap within the shared budget',
    'السكالب العادي':'Normal scalping','السكالب المتسارع':'Fast scalping',
    'بلغ هدف السكالب؛ الدخول لهذا النمط متوقف':'Scalp target reached; new entries for this mode are stopped',
    'نشط ضمن شروط التقاطع والمخاطر':'Active within confluence and risk rules',
    'حدد مخاطرة سكالب موجبة وهدفًا موجبًا وعائدًا لا يقل عن ١:٢.':'Set positive scalp risk and target, and a reward/risk ratio of at least 1:2.',
    'السكالب يتطلب بروتوكول تقاطع المدارس الأربع.':'Scalping requires the four-school confluence protocol.',
    'مصفوفة تقاطع المدارس':'School confluence matrix','المدرسة':'School','حالة الدليل':'Evidence status','الاتجاه':'Direction',
    'السيولة والهيكل والفجوة':'Liquidity, structure and gap','حجم الصفقات ونقطة التحكم':'Transaction volume and POC',
    'الدورات الزمنية المحلية':'Local timing cycles','الزخم والانحراف':'Momentum and divergence','الهيكل الموجي المحلي':'Local wave structure',
    'التوقيت محلي معلن؛ اكتمال القواعد ليس احتمال نجاح. الحجم غير المتاح لا يُستبدل بمؤشر تكات.':'Timing uses declared local rules; rule completion is not a win probability. Missing real volume is not replaced by tick activity.',
    'العائد السعري مقابل المخاطرة':'Price reward/risk ratio','فحص العائد الصافي بعد التكاليف قبل الإرسال':'Net reward/risk is checked after costs before sending'
  });
  const patterns = [
    [/^(\d+) رمز$/,m=>`${m[1]} symbols`],[/^(\d+) واقعة$/,m=>`${m[1]} facts`],[/^(\d+) حدث$/,m=>`${m[1]} events`],
    [/^(\d+) ظاهر من (\d+) رمز$/,m=>`${m[1]} shown of ${m[2]} symbols`],[/^(\d+) ظاهر من (\d+) حدث$/,m=>`${m[1]} shown of ${m[2]} events`],
    [/^تفويض: (.+)$/,m=>`Authorization: ${translate(m[1],'en')}`],[/^آخر تحديث: (.+)$/,m=>`Last update: ${m[1]}`],[/^آخر بيانات: (.+)$/,m=>`Latest data: ${m[1]}`],
    [/^عملة الحساب: (.+)$/,m=>`Account currency: ${m[1]}`],[/^يعادل (.+) من قيمة الحساب عند اعتماد التفويض\.$/,m=>`Equals ${m[1]} of Equity when authorization is granted.`],
    [/^المسح غير مكتمل · (.+) من (.+) رمزًا · بدأ (.+)\.$/,m=>`Scan incomplete · ${m[1]} of ${m[2]} symbols · started ${m[3]}.`],
    [/^اكتملت الدورة: (.+)\. التأهيل لا يعني وجود فرصة دخول\.$/,m=>`Cycle completed: ${m[1]}. Eligibility does not mean an entry opportunity exists.`],
    [/^توجد (\d+) محاولة مرفوضة في سجل القرارات\. (.*)$/,m=>`${m[1]} rejected attempts are recorded in the decision log. ${translate(m[2],'en')}`],
    [/^جودة الأدلة: (.+)$/,m=>`Evidence quality: ${m[1]}`],[/^صلاحية: (.+)$/,m=>`Valid until: ${m[1]}`],[/^المخاطر: (.+)$/,m=>`Risk: ${m[1]}`],
    [/^الدخول: (.+)$/,m=>`Entry: ${m[1]}`],[/^الإبطال: (.+)$/,m=>`Invalidation: ${m[1]}`],[/^النتيجة الكمية: (.+)$/,m=>`Quant result: ${m[1]}`],
    [/^إصدار:? (.+)$/,m=>`Version: ${m[1]}`],[/^البيانات: (.+)$/,m=>`Data: ${translate(m[1],'en')}`],[/^التحليل: (.+)$/,m=>`Analysis: ${translate(m[1],'en')}`],
    [/^آخر وصول: (.+)$/,m=>`Last access: ${m[1]}`],[/^الحداثة: (.+)$/,m=>`Freshness: ${translate(m[1],'en')}`],[/^شروط الاستخدام: (.+)$/,m=>`Terms: ${translate(m[1],'en')}`],
    [/^المراجعة: (.+)$/,m=>`Revision: ${m[1]}`],[/^المخاطرة: (.+) · الصلاحية: (.+)$/,m=>`Risk: ${m[1]} · valid until: ${m[2]}`],
    [/^هوية النية: (.+)$/,m=>`Intent ID: ${m[1]}`],[/^الاختبار: (.+)$/,m=>`Test: ${translate(m[1],'en')}`],[/^(.+) لوت$/,m=>`${m[1]} lots`],[/^توجد (\d+) عملية ذات إسناد غير مؤكد؛ (.+)$/,m=>`${m[1]} operations have uncertain attribution; ${translate(m[2],'en')}`]
  ];
  const fragments = [
    ['تفاصيل الفحص والعقد','Scan & Contract Details'],['عرض الشارت ←','Open Chart ←'],['الشارت ←','Chart ←'],['الأدلة المؤيدة','Supporting Evidence'],['التعارض أو النواقص','Conflicts or Gaps'],['لم تُرفق أدلة مؤيدة.','No supporting evidence was attached.'],['لم تُرفق تفاصيل التعارض؛ لا يعني ذلك غيابه.','No conflict details were attached; this does not prove their absence.'],['مدرسة غير مسماة','Unnamed School'],['غير معلن','Not Declared'],['السيناريو غير متاح.','Scenario unavailable.'],['جودة القواعد','Rule Quality'],['صوت صالح للاقتراح','Eligible Proposal Vote'],['مرشح لفحص اللجنة والمخاطر','Candidate for Committee and Risk Review'],['انتهاء الصلاحية','Expiry'],['عرض الأدلة والشروط وخطة التنفيذ','Show Evidence, Conditions & Execution Plan'],['لم تُرفق بيانات.','No data attached.'],['توقيت البيانات والتحليل','Data & Analysis Timing'],['الأدلة الرقمية والشموع','Numeric and Bar Evidence'],['الشروط المتحققة','Met Conditions'],['الشروط الناقصة','Missing Conditions'],['منطقة الدخول وشرطها','Entry Zone & Trigger'],['إبطال التحليل وشرطه','Analysis Invalidation'],['وقف التنفيذ المقترح','Proposed Execution Stop'],['الأهداف وطريقة اشتقاقها','Targets & Derivation'],['السيناريو البديل','Alternative Scenario'],['خطة إدارة الصفقة','Trade Management Plan'],['معادلة درجة الجودة','Quality Score Formula'],['متطلبات البيانات','Data Requirements'],['الافتراضات','Assumptions'],['المصادر','Sources'],['النواقص','Gaps'],['خبر بلا عنوان','Untitled News Item'],['مصدر غير مسمى','Unnamed Source'],['الرابط الأصلي ↗','Original Link ↗'],['تفسير الأثر المحتمل','Potential Effect Interpretation'],['لا يوجد تفسير معتمد.','No approved interpretation.'],['التوقيت والمصدر والقيَم','Time, Source & Values'],['الحدث','Event'],['النشر','Published'],['الاستلام','Received'],['منطقة المصدر الزمنية','Source Time Zone'],['مزود البيانات','Data Provider'],['المراجعات','Revisions'],['حدث اقتصادي','Economic Event'],['اعتماد النية','Approve Intent'],['لا توجد نيات تنتظر الموافقة.','No intents are awaiting approval.'],['تظهر هنا فقط في وضع الموافقة اليدوية.','They appear here only in manual-approval mode.'],['رقم الوسيط','Broker Ticket'],['نوع الأمر','Order Type'],['سعر الأمر','Order Price'],['وقت الإنشاء','Creation Time'],['الربح العائم','Floating Profit'],['خطة الإدارة','Management Plan'],['خارجية — للرقابة فقط','External — Monitor Only'],['للمنظومة','System Owned'],['ملكية تُحدد من المحرك','Ownership Determined by Engine'],['لا توجد مراكز مفتوحة مستلمة.','No received open positions.'],['لا توجد أوامر معلقة مستلمة.','No received pending orders.'],['لا توجد نيات تداول مسجلة.','No trading intents recorded.'],['نتائج محاكاة اصطناعية','Synthetic Simulation Results'],['نتائج الوسيط المؤكدة فقط','Confirmed Broker Results Only'],['صفقات مكتملة','Completed Trades'],['صافي محقق','Realized Net'],['تكاليف','Costs'],['أقصى تراجع','Maximum Drawdown'],['الاستراتيجية','Strategy'],['الأصل','Asset'],['عمليات الخروج','Exit Deals'],['التكاليف الموقعة','Signed Costs'],['الصافي','Net'],['التراجع','Drawdown'],['نوع النتائج','Result Type'],['سجل الوسيط','Broker Record'],['لا توجد نتائج كافية لتقييم الأداء.','Insufficient results to evaluate performance.'],['صفقات الاختبار','Test Trades'],['معامل الربح','Profit Factor'],['العائد المتوقع','Expected Return'],['حالة القبول','Acceptance Status'],['سبب الرفض','Rejection Reason'],['لا توجد نتائج تحقق كمي بعد.','No quantitative-validation results yet.'],['اتصال المنصة','Platform Connection'],['السماح بالتداول من المنصة','Platform Trading Permission'],['مسموح','Allowed'],['غير مسموح','Not Allowed'],['التداول عبر الواجهة','API Trading'],['معطل','Disabled'],['نمط الحساب','Account Mode'],['مصدر الأسعار','Price Source'],['حالة المحرك','Engine Status'],['وقت البيانات','Data Time'],['حالة المطابقة','Reconciliation Status'],['التخزين الدائم','Persistent Storage'],['موارد الجهاز','Device Resources'],['حد بداية اليوم','Day Boundary'],['حالة القبول النهائي','Final Acceptance Status'],['اصطناعي — محاكاة فقط','Synthetic — Simulation Only'],['منصة MT5','MT5 Platform'],['لا يوجد اتصال','No Connection'],['عمليات غير محسومة','Unresolved Operations'],['راجع سجل المطابقة','Review Reconciliation Log'],['سجل اليوم والنيات محلي؛ راجع تقرير التشخيص','Daily state and intents are local; review the diagnostic report'],['تفاصيل محفوظة','Stored Details'],['لا توجد أحداث بهذه التصفية.','No events match this filter.'],['تُسجل القرارات والأعطال عند حدوثها.','Decisions and errors are recorded when they occur.'],['المكتشفة','Discovered'],['المفحوصة','Checked'],['المؤهلة','Eligible'],['المستبعدة','Excluded'],['الانتظار قرار صالح؛ لا يُخفَّض معيار الدخول للاقتراب من الهدف.','Waiting is a valid decision; entry standards are not lowered to approach the target.'],['لم تظهر فرصة قابلة للاعتماد. تشرح اللجنة أسباب الانتظار عند اكتمال البيانات والتحليل.','No approvable opportunity appeared. The committee explains why it is waiting when data and analysis are complete.'],['لا يوجد قرار لجنة لهذا الرمز.','No committee decision exists for this symbol.'],['بطاقات المدارس منفردة لا تُجيز إرسال الأوامر.','Individual school cards do not authorize sending orders.'],['وقت آخر شمعة يظهر على الشارت','The latest bar time appears on the chart'],['لا توجد بطاقات مدارس بعد.','No school cards yet.'],['حدد الرمز والفريم ثم اضغط «عرض»، أو انتظر اكتمال تحليل السوق.','Select a symbol and timeframe, then click “Load”, or wait for market analysis to finish.'],['لم تُتحقق تغطية الأخبار. غياب الخبر لا يعني غياب الحدث؛ القرار يحتاج مصادره المطلوبة قبل الدخول.','News coverage is unverified. Missing news does not prove that no event exists; required sources must be available before entry.'],['التقويم المطلوب غير متحقق؛ ثبّت جسر القراءة وأضفه إلى شارت في MT5.','The required calendar is unverified; install the read bridge and attach it to an MT5 chart.'],['آخر فحص للتقويم','Latest calendar check'],['لا توجد مصادر أخبار متحققة.','No verified news sources.'],['تظهر المصادر المتاحة وحالات العطل وحدود التغطية عند الاتصال.','Available sources, failures and coverage limits appear after connection.'],['لا توجد وقائع مستلمة.','No received facts.'],['هذا لا يثبت غياب أحداث اقتصادية أو سياسية.','This does not prove that no economic or political events exist.'],['الجدول الاقتصادي غير متاح.','Economic calendar unavailable.'],['لا يُملأ بتوقعات أو أحداث مصطنعة.','It is not filled with fabricated forecasts or events.'],['المصدر الأصلي ←','Original Source ←'],['المصدر ↗','Source ↗'],['لا توجد رموز بهذه الحالة.','No symbols have this status.'],['اتصل بالمنصة وابدأ المسح لعرض قائمة الوسيط الكاملة.','Connect to the platform and start a scan to display the full broker symbol list.'],['الرمز','Symbol'],['فئة الأصل','Asset Class'],['الأهلية','Eligibility'],['السبريد (فرق سعر)','Spread'],['سبب الاستبعاد أو الحالة','Exclusion Reason or Status'],['آخر فحص','Last Check'],['وصف العقد','Contract Description'],['المسار لدى الوسيط','Broker Path'],['السماح بالتداول','Trading Permission'],['جلسة السوق','Market Session'],['آخر سعر','Latest Tick'],['توفر التاريخ','History Availability'],['حجم العقد','Contract Size'],['عملة الربح','Profit Currency'],['عملة الهامش','Margin Currency'],['خطوة السعر','Price Step'],['الحد الأدنى للوت','Minimum Lot'],['الحد الأقصى للوت','Maximum Lot'],['خطوة اللوت','Lot Step'],['حد الوقف بالنقاط','Stop Level in Points'],['تجميد التعديل بالنقاط','Freeze Level in Points'],['نمط التنفيذ','Execution Mode'],['تاريخ انتهاء العقد','Contract Expiration'],['حالة الهامش','Margin Status'],['أسباب الأهلية','Eligibility Reasons'],['الدخول معطل','Entries Disabled'],['شراء فقط','Buy Only'],['بيع فقط','Sell Only'],['إغلاق فقط','Close Only'],['شراء وبيع','Buy and Sell'],['غير متحققة','Unverified'],['مفتوحة','Open'],['مغلقة','Closed'],['غير منطبق أو غير متاح','Not Applicable or Unavailable'],['طلب السعر','Request'],['تنفيذ فوري','Instant Execution'],['تنفيذ سوقي','Market Execution'],['تنفيذ بورصة','Exchange Execution'],['لا يمكن التحويل دون Equity متاح.','Cannot convert without available Equity.'],['عملة الحساب','Account Currency'],['الخدمة المحلية غير متاحة','Local Service Unavailable'],['محاكاة محلية متصلة','Local Simulation Connected'],['MT5 متصل','MT5 Connected'],['المنصة غير متصلة','Platform Disconnected'],['الخدمة متاحة؛ وقت البيانات يظهر في كل قسم','Service available; data time appears in each section'],['اتصل بحساب Demo أو فعّل المحاكاة المحلية أولًا.','Connect a Demo account or start local simulation first.'],['الدخول الجديد متوقف:','New entries stopped:'],['ابدأ التداول التجريبي بموافقة يدوية','Start Manual-Approval Demo Trading'],['اختر رمزًا أولًا.','Select a symbol first.'],['اختر رمزًا للتحقق الكمي أولًا.','Select a symbol for quantitative validation first.'],['إيقاف الخدمة المحلية والخروج','Stop Local Service and Exit']
  ];
  const originals = new WeakMap();
  const attrOriginals = new WeakMap();
  const appliedText = new WeakMap();
  const appliedAttrs = new WeakMap();
  const hasArabic = (value) => /[\u0600-\u06ff]/.test(String(value ?? ''));
  Object.assign(en,{"استعادة النقطة المحورية اليومية": "Previous-session classic pivot reclaim", "اختراق فراكتال خماسي مؤكد": "Confirmed five-bar fractal breakout", "اختلاف OBV التقريبي واستعادة المستوى": "Tick-count OBV divergence and price reclaim proxy", "استعادة النقطة المحورية اليومية نموذج للفريمات داخل اليوم فقط": "daily pivot reclaim is an intraday model", "هدف أول مقاومة أو دعم للنقطة المحورية الكلاسيكية": "first classic pivot resistance or support", "يلزم مرجع يومي مكتمل من منصة التداول لحساب النقاط المحورية": "completed MT5 daily reference required for classic pivots", "مرجع النقطة المحورية أو يوم التفعيل خارج النطاق المعلن": "daily pivot reference or trigger session is outside declared scope", "معادلة النقطة المحورية كلاسيكية؛ الاستعادة وانتهاء المرجع بعد أربعة أيام والخروج تعريفات محلية": "Classic pivot formula; reclaim, four-day expiry and exits are house definitions", "يلزم 61 شمعة مكتملة لنموذج اختراق الفراكتال المحدود": "61 completed bars required for bounded fractal breakout", "يلزم 61 شمعة مكتملة لنموذج OBV التقريبي المحدود": "61 completed bars required for bounded OBV proxy", "يلزم عدد تكات موجب ومحدود لكل شمعة ضمن نافذة OBV": "positive finite tick counts required for every bounded OBV bar", "OBV المحسوب من اتجاه الإغلاق وعدد التكات بديل حجمي تقريبي للشموع؛ ليس حجم صفقات أو صفقات محددة الاتجاه أو تدفق أوامر فعلي": "Close-signed tick-count OBV is a candle-volume proxy; not traded-volume OBV, signed trades or real order flow", "شموع يومية مكتملة من منصة التداول": "Completed MT5 daily OHLC", "حُفظ مرجع المدارس وذاكرة التعلم؛ بعض ملفات المصدر التاريخية غير متاحة ومُبيّنة في التصدير": "School reference and learning memory saved; missing historical source files are listed in the export"});
  Object.assign(en,{"آلية تطبيق القواعد ومراجعتها": "Rule application and review protocol", "قيمة OBV التراكمية يجب أن تكون محدودة": "Cumulative OBV must be finite"});
  Object.assign(en,{"يجب أن تكون مستويات النقاط المحورية موجبة ومحدودة":"Classic pivot levels must be finite and positive"});
  Object.assign(en,{"إليوت: عودة بعد هندسة خمس موجات": "Elliott five-swing geometry reversal", "إليوت: عودة بعد هندسة زجزاج": "Elliott zigzag geometry reversal", "يلزم محاور متعاقبة مؤكدة لفحص الهندسة الموجية": "confirmed alternating pivots required for wave geometry", "هدف بنيوي عند محور الموجة السابقة": "prior wave structural target", "الهندسة الموجية فرضية؛ التقسيمات الداخلية والدرجات البديلة وترقيم إليوت الكامل غير محسومة": "Wave geometry is a hypothesis; nested subdivisions, alternate degrees and complete Elliott counts are not asserted"});
  Object.assign(en,{"تحليل يعمل · التنفيذ متوقف":"Analysis running · execution stopped","الواجهة تعرض التحليل للقراءة فقط ولا تملك تفويض إرسال أوامر.":"This interface is read-only and is not authorized to send orders.","التنفيذ متوقف":"Execution stopped","الدخول متوقف":"New entries paused","وقف الخسارة اليومي":"Daily loss limit reached","هدف اليوم":"Daily target reached","التنفيذ التجريبي يعمل":"Demo executor running","حالة المنفّذ غير متاحة":"Executor status unavailable","ملخص أفضل فرصة من الفرص المؤهلة":"Best of qualified opportunities","افتح الأبحاث لرؤية القائمة كاملة":"Open Research to see the full list","تعذرت قراءة حالة التنفيذ الحالية. لا تُعدّ البيانات القديمة حالة حية.":"Current executor status could not be read. Cached data is not live status."});
  function translate(value,lang='ar') {
    if (lang !== 'en' || typeof value !== 'string' || !value) return value;
    const leading=value.match(/^\s*/)?.[0]||'',trailing=value.match(/\s*$/)?.[0]||'',text=value.trim();
    if (!text) return value;
    const dubaiClock=text.match(/^(\d{2}:\d{2})\s+بتوقيت دبي$/);
    if(dubaiClock)return `${leading}${dubaiClock[1]} UTC+4${trailing}`;
    if (en[text]) return `${leading}${en[text]}${trailing}`;
    for (const [pattern,replacer] of patterns) {
      const match=text.match(pattern);
      if(match){
        let patterned=replacer(match);
        for (const [arabic,english] of fragments.sort((a,b)=>b[0].length-a[0].length)) patterned=patterned.split(arabic).join(english);
        if (hasArabic(patterned)) patterned='Untranslated system detail; export diagnostics for the complete local record.';
        return `${leading}${patterned}${trailing}`;
      }
    }
    let translated=text;
    for (const [arabic,english] of fragments.sort((a,b)=>b[0].length-a[0].length)) translated=translated.split(arabic).join(english);
    // Never mix scripts in English mode. Exact and patterned translations
    // above preserve the details of every normal UI and execution path. This
    // fail-closed label covers an unforeseen backend message until it is added
    // to the reviewed dictionary, while the full original remains in the local
    // diagnostic archive for troubleshooting.
    if (hasArabic(translated)) translated='Untranslated system detail; export diagnostics for the complete local record.';
    return `${leading}${translated}${trailing}`;
  }
  function apply(root=document,lang='ar') {
    lang=lang==='en'?'en':'ar';document.documentElement.lang=lang;document.documentElement.dir=lang==='en'?'ltr':'rtl';
    document.title='Quant Trading AI';
    const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);let node;
    while((node=walker.nextNode())){
      const current=node.nodeValue;
      const previous=appliedText.get(node);
      if(previous?.lang===lang&&previous.value===current)continue;
      if(lang==='en') {if(hasArabic(current)||!originals.has(node)) originals.set(node,current);node.nodeValue=translate(originals.get(node),'en');}
      else if(originals.has(node)) node.nodeValue=originals.get(node);
      appliedText.set(node,{lang,value:node.nodeValue});
    }
    (root.querySelectorAll?root.querySelectorAll('*'):[]).forEach((el)=>{
      if(!attrOriginals.has(el))attrOriginals.set(el,{});const saved=attrOriginals.get(el);
      if(!appliedAttrs.has(el))appliedAttrs.set(el,{});const applied=appliedAttrs.get(el);
      ['title','placeholder','aria-label'].forEach((attr)=>{if(!el.hasAttribute(attr)){delete applied[attr];return;}const current=el.getAttribute(attr);if(applied[attr]?.lang===lang&&applied[attr].value===current)return;if(lang==='en'){if(hasArabic(current)||!(attr in saved))saved[attr]=current;el.setAttribute(attr,translate(saved[attr],'en'));}else if(attr in saved)el.setAttribute(attr,saved[attr]);applied[attr]={lang,value:el.getAttribute(attr)};});
    });
  }
  Object.assign(en,{"يلزم أربعة محاور هارمونيك متعاقبة ومؤكدة": "four confirmed alternating harmonic pivots", "نسب الأضلاع خارج الحدود المحددة للنموذج": "equal-leg ratios outside declared bounds", "يلزم اختراق جديد بعد تأكيد النقطة الرابعة خلال ثماني شموع": "fresh break after D confirmation within eight bars", "هندسة أضلاع متساوية مؤكدة": "confirmed equal-leg geometry", "اختراق جديد بعد تأكيد النموذج": "fresh post-confirmation break", "يلزم بقاء النقطة الرابعة سليمة واختراق جديد قبل بلوغ هدف النقطة الثالثة": "unbroken D and fresh confirmation break before C target", "هدف المحور الثالث للنموذج": "harmonic C pivot target", "نموذج الأضلاع المتساوية فقط؛ تأكيد الدخول والسماحات قواعد خاصة بهذه النسخة ولا تغطي كل الهارمونيك": "Equal-leg model only; not all harmonic patterns; entry confirmation and tolerances are house rules", "انتظار اكتمال شروط الدخول": "wait for a complete entry setup", "الانتظار، أو إعداد مؤكد في الاتجاه الآخر": "wait or opposing confirmed setup", "إغلاق شمعة مكتملة خلف مستوى إبطال التحليل": "completed close beyond the analysis level", "تحققت القاعدة على آخر شمعة مكتملة؛ يجب أن يبقى السعر الحالي داخل منطقة الدخول": "declared rule on the latest completed bar; quote must remain inside zone", "وقف خلف البنية مع هامش 0.1 ATR ومسافة مخاطرة لا تقل عن 0.6 ATR": "structure with 0.1 ATR buffer and >=0.6 ATR risk", "هدف يساوي ضعفي مسافة الوقف المقترح": "2 * proposed stop distance", "متوسط عينة سابقة لشموع تفعيل الدخول": "pre-trigger sample mean", "يلزم وجود قمتين وقاعين مؤكدين": "two confirmed highs and lows", "بنية قمم وقيعان مؤكدة": "confirmed structure", "يلزم اختراق جديد بالإغلاق لقمة أو قاع مؤكد": "fresh close through confirmed swing", "جسم شمعة ابتلاعية": "engulfing body", "يلزم ابتلاع جسم الشمعة السابقة بحجم لا يقل عن نصف ATR": "body >= 0.5 ATR and engulfing", "حجم الجسم الابتلاعي مقارنة بالتقلب ATR": "engulfing body / ATR", "دعم مؤكد": "support", "مقاومة مؤكدة": "resistance", "ملامسة المستوى وإغلاق يدل على الرفض": "touch and close rejection", "يلزم رفض مؤكد عند مستوى الدعم أو المقاومة": "confirmed level rejection", "سقف النطاق السابق": "prior range top", "قاع النطاق السابق": "prior range bottom", "اختراق بإغلاق مكتمل": "close breakout", "إعادة اختبار لاحقة حافظت على المستوى": "subsequent retest holds", "يلزم اختراق يعقبه إعادة اختبار ناجحة": "breakout followed by retest", "سقف الصندوق تأكد بثلاث شموع لاحقة": "three closes confirm top", "صندوق مؤكد": "box confirmed", "يلزم اختراق جديد للصندوق": "fresh box breakout", "سحابة الوقت الحالي محسوبة قبل 26 شمعة مكتملة": "cloud calculated 26 completed bars earlier", "ترتيب خطي تنكان وكيجون يحدد السياق الاتجاهي": "Tenkan/Kijun directional ordering", "تقاطع جديد خارج السحابة المحسوبة دون بيانات مستقبلية": "fresh cross outside causal cloud", "يلزم تقاطع جديد وتحقق فلتر السحابة": "fresh cross and cloud filter", "يلزم قمة وقاع متعاقبان ومؤكدان": "confirmed alternating swing pair", "مستوى تصحيح 61.8%": "0.618 pullback", "تفعيل استعادة مستوى تصحيح 50%": "0.5 recovery trigger", "موجة سعرية مؤكدة": "confirmed swing", "استعادة المستوى بعد التصحيح": "pullback recovery", "يلزم لمس تصحيح 61.8% ثم استعادة جديدة لمستوى 50%": "0.618 touch and fresh 0.5 recovery", "ترتيب المتوسطين يعطي السياق الاتجاهي": "EMA directional ordering", "يلزم تقاطع جديد للمتوسطين EMA12 وEMA26": "fresh EMA crossover", "استعادة جديدة لعتبة الزخم": "fresh threshold recovery", "يلزم عبور RSI عائداً عبر 30 أو 70": "RSI recross 30 or 70", "مؤشر RSI14 بمتوسط بسيط": "simple RSI14", "نطاقات محسوبة من البيانات السابقة فقط": "prior-only bands", "انكماش التقلب": "contraction", "يلزم انكماش التقلب ثم إغلاق جديد خارج النطاق": "contraction then fresh outside-band close", "يلزم تشتت سعري موجب": "nonzero dispersion", "استقرار نسبي للمتوسط": "stable mean", "يلزم عودة درجة Z عبر العتبة وهدف متوسط صالح في اتجاه الصفقة": "fresh zscore recross with valid mean target", "المتوسط مقدر قبل شموع تفعيل الدخول": "mean estimated before both trigger bars", "يلزم ثلاث شموع مكتملة على الأقل بعد نقطة التثبيت": "at least three completed bars after anchor", "يلزم وزن حجم موجب لكل شمعة بعد التثبيت": "positive weights for each anchored bar", "متوسط مرجح بحجم شموع الوسيط": "bar VWAP", "بديل تقريبي للسعر النموذجي المرجح بعدد التكات": "tick-weighted typical-price proxy", "استعادة جديدة للمتوسط المرجح": "fresh weighted-mean reclaim", "يلزم عبور جديد للمتوسط المرجح": "fresh reclaim", "عدد التكات يقيس النشاط ولا يمثل حجم تداول مركزي": "Tick volume is activity count, not centralized traded volume", "المتوسط المرجح بالتكات بديل تقريبي وليس VWAP للصفقات الفعلية": "Tick-weighted mean is a proxy, not genuine transaction VWAP", "تقدير باستخدام السعر النموذجي للشمعة، وليس أسعار كل الصفقات": "Bar typical-price approximation, not trade-level VWAP", "الحجم الفعلي إن توفر مصدره الوسيط أو منصة التداول ولا يفترض أنه مركزي": "Real volume is venue/broker supplied, not asserted centralized", "يلزم أصل مقابل محدد وبيانات مكتملة متزامنة": "identified partner and completed aligned bars", "يلزم 42 شمعة متطابقة زمنياً بين الأصلين": "42 exactly time-aligned bars", "ارتباط 40 زوجاً من العوائد اللوغاريتمية السابقة": "40 prior log-return pairs", "ارتباط العوائد لا يقل عن 0.7": "return correlation >= 0.7", "يلزم اختراق جديد متوافق مع اتجاه الأصل المقابل": "fresh breakout with partner direction", "نسبة مرشحة لتشابه AB مع CD": "AB=CD candidate ratio", "تعريفات نسب الهارمونيك الكاملة وحسم التعاقب واختبار قاعدة دخول مستقلة غير مكتملة": "full harmonic ratio taxonomy, alternation resolution, and independently validated trigger", "ترقيم موجي غير فريد مع بدائل محتملة": "nonunique counts", "قواعد درجات الموجات والتعاقب وقاعدة الدخول المختبرة غير مكتملة": "complete nesting/alternation rules and validated execution trigger", "عدم يقين في مرحلة وايكوف": "phase uncertainty", "تعريف مراحل وايكوف A-E وتأكيدها بحجم صفقات موثوق غير مكتمل": "phase A-E formal inference and reliable traded-volume confirmation", "فجوة ثلاث شموع كبديل تقريبي لعدم التوازن": "OHLC FVG proxy", "نموذج الجلسات ودورة كتل الأوامر وقاعدة السيولة المختبرة غير مكتملة": "formal session model, order-block lifecycle and independently validated liquidity trigger", "شمعة سابقة كمنطقة أساس تقريبية": "prior candle base proxy", "عمر منطقة العرض والطلب وإبطالها واختبار الدخول عند العودة غير مكتمل": "zone freshness/lifecycle and retest execution validation", "مزامنة القمم بين الأصلين ودورة اختلاف SMT واختبار الدخول غير مكتملة": "partner-specific swing synchronization, divergence lifecycle and execution validation", "يلزم تاريخ عدة سنوات معدل للعقود واختبار موسمية خارج العينة": "multiple years, adjusted contract history and calendar bucket OOS validation", "300 شمعة داخل اليوم لا تكفي لإثبات الموسمية": "300 intraday bars cannot establish seasonality", "تعريف تطبيع السعر والزمن ومربع التسعة وقواعد التنفيذ غير منفذ": "declared price/time normalization, square-nine rules and validated execution definition", "بيانات اتجاه الصفقات وعمق السوق التاريخي الموثوق غير متاحة": "signed trades and reliable historical depth/venue data", "شموع MT5 وعدد التكات لا تنتج دلتا أو بصمة أوامر فعلية": "MT5 OHLC/tick counts cannot produce real delta or footprint", "آخر شمعة مكتملة قديمة": "last completed bar is stale", "يلزم نطاق سعري موجب قابل للتداول": "nonzero tradable range", "يلزم هدف موجب صالح في اتجاه الصفقة": "positive target in trade direction", "قيمة ATR صفرية": "zero ATR", "تاريخ البيانات غير كافٍ": "insufficient history", "شموع مكتملة من الوسيط": "broker completed OHLC", "شموع صناعية مكتملة للاختبار فقط": "synthetic completed OHLC", "شموع مكتملة بمصدر غير موثق": "completed OHLC with undeclared provenance", "التاريخ لا يغطي بداية مرساة الحساب المعلنة": "history does not cover the declared anchor boundary", "تعريف دارفاس محدد بصندوق 20 شمعة ولا يمثل جميع القراءات التقديرية": "Fixed 20-bar Darvas variant; not every discretionary box interpretation", "رسم شيكو إلى الماضي لا يستخدم كبيانات تنبؤية": "Chikou drawn retrospectively is not used as predictive input", "RSI بمتوسط ربح وخسارة بسيط متحرك وليس تنعيم وايلدر": "Simple rolling gain/loss RSI; deliberately not Wilder smoothing", "لا يفترض ثبات التوزيع أو كونه طبيعياً": "No stationarity or Gaussian distribution claim", "الارتباط متغير ولا يثبت السببية؛ تأكيد لأصل واحد وليس استراتيجية تحوط مزدوجة": "Correlation is unstable and not causal; single-leg confirmation, not a hedged pair strategy", "تشابه AB=CD وصفي ولا يثبت اكتمال نموذج غارتلي أو بات أو باترفلاي": "AB=CD resemblance is descriptive; not a completed Gartley/Bat/Butterfly signal", "ترقيم إليوت بدائل غير فريدة ولا يؤكد موجة مستقبلية": "Counts are alternatives; no unique Elliott interpretation or future wave is asserted", "كسر النطاق واستعادته لا يثبت التجميع أو نية مؤسسة": "A sweep/reclaim is not proof of accumulation or institutional intent", "فجوة ثلاث شموع لا تكشف الأوامر الفعلية أو التدفق المؤسسي": "Three-bar gap does not identify actual orders or institutional order flow", "منطقة أساس شمعة ليست أوامر عرض وطلب مرصودة": "OHLC base is not observed supply or demand orders", "لا يستنتج اتجاه SMT عند غياب بيانات الأصل المقابل": "No SMT direction inferred from a missing partner", "الفريم غير مدعوم": "unsupported timeframe", "وقت التحليل غير صالح": "invalid analysis time", "سعر أو وقت مفقود أو غير محدود": "missing or nonfinite OHLC/time", "يجب أن تكون أوقات الشموع UTC متزايدة ودون تكرار": "bars must have unique ascending UTC times", "شمعة غير مكتملة أو من المستقبل": "unfinished or future bar", "علاقة أسعار الفتح والإغلاق والقمة والقاع غير صحيحة": "invalid OHLC geometry", "بيانات الحجم أو السبريد غير صالحة": "invalid volume/spread", "هندسة مؤكدة لنموذج القمتين أو القاعين": "confirmed double-top or double-bottom geometry", "هندسة مؤكدة لنموذج الرأس والكتفين": "confirmed head-and-shoulders geometry", "إغلاق مكتمل جديد عبر خط العنق": "fresh completed close through the neckline", "يلزم نموذج انعكاسي كلاسيكي مؤكد وفق الحدود الرقمية المعلنة": "confirmed classical reversal geometry", "يلزم كسر خط العنق على آخر شمعة مكتملة": "neckline break on the latest completed bar", "هندسة نموذج انعكاسي كلاسيكي": "classical reversal geometry", "إسقاط ارتفاع النموذج من خط العنق": "pattern height projected from neckline", "يلزم ثلاث قمم وثلاثة قيعان مؤكدة": "three confirmed highs and three confirmed lows", "هندسة مثلث متقارب مؤكدة": "converging triangle geometry", "إغلاق مكتمل جديد خارج حدود المثلث": "fresh completed close outside triangle", "يلزم مثلث متقارب بخطين صالحين من قمم وقيعان مؤكدة": "confirmed converging triangle", "يلزم كسر المثلث على آخر شمعة مكتملة": "triangle breakout on the latest completed bar", "إسقاط ارتفاع المثلث من إغلاق الاختراق": "triangle height projected from breakout close", "خطوط الانحدار تصف قمم وقيعان OHLC مؤكدة ولا تدعي مطابقة خطوط الاتجاه التقديرية": "Regression lines describe confirmed OHLC pivots; they do not imply exact discretionary trendlines", "أسماء النماذج تصف هندسة OHLC معلنة ولا تضمن التنبؤ": "Pattern names describe explicit OHLC geometry, not a forecast guarantee", "تحققت قاعدة التخصص": "specialist rule confirmed", "لم يكتمل شرط دخول التخصص": "specialist trigger not completed", "مستويات قاعدة التخصص": "specialist levels", "تعريف خوارزمي محدد وليس مدرسة كاملة أو إثباتًا للربحية": "house definition; not a complete school or profitability claim", "حالة السوق خارج النطاق المعلن للاستراتيجية": "market regime outside declared scope", "هدف المتوسط المحدد للاستراتيجية": "specialist mean target", "يلزم عدد تكات موجب لكل شمعة لحساب مؤشر النشاط المحلي": "positive bar tick counts required for local activity proxy", "نشاط تكات الشموع وموقع الإغلاق مؤشر تقريبي؛ لا يمثل تدفق أوامر أو حجم صفقات محدد الاتجاه": "Bar tick activity and close-location proxy; not real order flow or signed volume", "لم تكتمل شروط النموذج المحلي": "local model conditions incomplete", "أدلة النموذج المحلي": "local model evidence", "يلزم أصل مقابل محدد وبيانات منصة متزامنة": "aligned declared MT5 partner required", "يلزم سحب مستوى سابق قبل نموذج السيولة المحلي": "prior sweep required for local liquidity model", "النموذج الشهري المحلي مخصص لأزواج العملات المعلنة فقط": "local monthly model supports declared currency pairs only", "يلزم تاريخ يومي مكتمل متعدد السنوات من المنصة": "completed multi-year MT5 daily history required", "انقطاع سعري كبير في العينة الشهرية المحلية": "historical discontinuity in local monthly sample", "يلزم ثلاث عينات مكتملة سابقة للشهر نفسه": "three complete earlier same-month samples required", "فرضية موجتين محلية؛ لا تؤكد ترقيم إليوت المتداخل أو اكتمال موجة مستقبلية": "Local wave 1-2 hypothesis; nested Elliott counts and future wave completion are not asserted", "كسر نطاق واختباره مع مؤشر تكات تقريبي؛ لا يثبت مراحل وايكوف الكاملة أو نية المؤسسات": "Range spring/test with tick-count proxy; no full Wyckoff phase or institutional intent inference", "سحب مستوى وعودة فجوة محليان؛ لا يمثلان أوامر مؤسسات أو تفسيرًا كاملًا للمدرسة": "Local sweep plus gap return; no institutional orders or full ICT interpretation", "عودة أولى لمنطقة شموع مع فلتر متوسط سابق؛ ليست أوامر عرض وطلب مرصودة": "First-return OHLC zone with prior EMA filter; not observed supply or demand orders", "شبكة جذر السعر المعيارية نموذج خاص؛ ليست نظرية جان الكاملة أو دورة زمنية طبيعية": "Volatility-normalized square-root grid is a house model; not complete Gann theory or a natural time cycle", "عينة شهرية خام للعملات من الوسيط؛ لا تفترض تاريخ عقود معدلًا أو ثباتًا أو ربحية موسمية": "Raw broker FX monthly sample; no adjusted futures history, stationarity or seasonal profitability claim", "تأكيد أصل مقابل محدد": "Declared paired-asset confirmation", "اختلاف نطاق أصلين: نموذج محلي": "Paired range divergence: local model", "إليوت: فرضية موجتين محلية": "Elliott: local wave 1-2 hypothesis", "وايكوف: نموذج كسر واختبار محلي": "Wyckoff: local spring-test model", "السيولة: سحب مستوى وعودة فجوة": "Liquidity: sweep and gap return", "العرض والطلب: عودة منطقة محلية": "Supply/demand: local zone return", "جان: شبكة جذر سعر معيارية": "Gann: normalized price-root grid", "تدفق النشاط: تقريب من شموع التكات": "Activity flow: bar-tick approximation", "موسمية العملات: نموذج شهري محلي": "FX seasonality: local monthly model", "ارتباط أربعين عائدًا سابقًا لا يقل عن 0.7، مع كسر جديد لنطاق عشرين شمعة يؤكده الأصل المقابل المحدد.": "Prior 40-return correlation at least 0.7; new 20-bar breakout confirmed by the declared paired asset.", "ارتباط لا يقل عن 0.7؛ يسحب أصل حد عشرين شمعة ويعود داخله دون أن يسحب الأصل المقابل حده.": "Correlation at least 0.7; one asset sweeps its prior 20-bar boundary and returns while its declared partner does not sweep.", "ثلاثة محاور مؤكدة متناوبة؛ الضلع الأول ضعفا نطاق التقلب على الأقل والتصحيح بين 38.2 و78.6 بالمئة، ثم كسر جديد خلال ست عشرة شمعة مع سلامة قاع أو قمة التصحيح.": "Three confirmed alternating pivots; first leg at least 2 ATR, retracement 0.382–0.786, fresh first-leg break within 16 bars with retracement intact.", "نطاق جانبي لأربعين شمعة؛ سحب حد ثم ابتعاد وإعادة اختبار بعدد تكات أقل خلال ثماني شموع، والهدف منتصف النطاق.": "40-bar sideways range; boundary sweep, departure, then lighter tick-count retest within eight bars; target range midpoint.", "سحب حد عشر شموع قبل فجوة اندفاع؛ أول عودة صالحة للفجوة خلال عشرين شمعة.": "Sweep of a prior 10-bar boundary before a displacement gap; first valid gap return within 20 bars.", "أول عودة إلى أساس اندفاع غير مكسور خلال عشرين شمعة، في اتجاه المتوسط الأسي السابق لعشرين شمعة.": "First return to an unbroken displacement base within 20 bars, aligned with the prior 20-bar EMA.", "قاعدة خاصة: مستوى جذر سعر معياري بنطاق التقلب وإزاحة ربع وحدة من محور مؤكد؛ عبور جديد خلال اثنتين وثلاثين شمعة مع سلامة المحور.": "House rule: ATR-normalized square-root level shifted by 0.25 from a confirmed pivot; fresh cross within 32 bars with anchor intact.", "عدد تكات لا يقل عن 1.2 من الوسيط السابق؛ ضغط موقع الإغلاق يعبر موجب أو سالب 0.35 مع كسر حد خمس شموع. لا يستخدم حجم صفقات محدد الاتجاه أو عمق سوق.": "Bar tick count at least 1.2 times the prior median; close-location pressure crosses ±0.35 and breaks a five-bar boundary. No signed trade volume or depth.", "أزواج العملات المعلنة فقط؛ ثلاث عينات شهرية سابقة مكتملة على الأقل من يوميات المنصة، ودرجة إحصائية مطلقة لا تقل عن اثنتين واتفاق ثلثي العينات مع كسر جديد لنطاق عشرين شمعة.": "Declared FX only; at least three completed prior same-month samples from MT5 D1, absolute t-score at least 2, direction agreement at least two thirds, fresh 20-bar break.", "نموذج محلي محدد القواعد؛ لا يمثل المدرسة الأصلية بكاملها. يجري فحص توفر البيانات وشروط الدخول بشكل منفصل.": "Bounded local model; not the complete original school. Data availability and entry conditions are checked separately.", "حالة التحليل الحالية": "Current analysis state", "لم يبدأ تحليل هذا النموذج بعد": "This model has not been analyzed yet", "قواعد النموذج": "Model rules", "إصدار": "Version", "أصل مقابل محدد": "Declared paired asset", "تاريخ يومي من الوسيط": "Broker daily history", "شموع الأصل المقابل المتزامنة": "Synchronized paired-asset bars"});
  Object.assign(en,{
    'مكتبة المدارس والتعلم':'Schools and learning',
    'معرفة محفوظة وقواعد قابلة للمراجعة':'Stored knowledge and reviewable rules',
    'مرجع ثنائي اللغة يربط المدرسة بقواعدها ونماذجها وبياناتها المطلوبة.':'A bilingual reference linking each school to its rules, models and required data.',
    '↓ تصدير المعرفة والتعلم':'↓ Export knowledge and learning',
    'دليل المدارس والمناهج':'Schools and approaches catalog',
    'ابحث في المدارس والقواعد والبيانات المطلوبة':'Search schools, rules and required data',
    'بحث مكتبة المدارس':'Search school library',
    'تصفية مدارس التحليل':'Filter analysis schools',
    'كل المدارس والمناهج':'All schools and approaches',
    'التحليل الفني':'Technical analysis',
    'التحليل الأساسي':'Fundamental analysis',
    'مناهج التقييم والتحليل':'Valuation and analysis approaches',
    'التعلم من تطبيق القواعد':'Learning from rule application',
    'ملف المرجع المحلي':'Local reference file',
    'يصدر المرجع وإصدارات القواعد ونتائج التعلم إلى ملف محلي يمكن مراجعته وتطويره.':'Exports the reference, rule versions and learning results to a local file for review and development.',
    'لم يكتمل وصف هذا المرجع باللغة المختارة.':'The reference description in the selected language is incomplete.',
    'فئة غير معروفة':'Unknown category',
    'لا توجد قواعد محفوظة لهذا القسم.':'No stored rules for this section.',
    'المدارس والمناهج':'Schools and approaches',
    'القواعد المرجعية':'Reference rules',
    'مبدأ من المصدر':'Source principle',
    'قائمة تحقق تشغيلية':'Operational checklist',
    'تعريف حسابي محلي':'Quant Trading AI computational definition',
    'حاسبات محلية متاحة':'Available local calculators',
    'نماذج مرتبطة بالكود':'Linked coded models',
    'إصدارات القواعد المحفوظة':'Stored rule versions',
    'تعذر تحميل المرجع؛ راجع تقرير التشخيص.':'Reference loading failed; review the diagnostic report.',
    'المرجع محفوظ محليًا بإصدارات قابلة للتتبع. القاعدة المرجعية لا تعني أن المدرسة منفذة بالكامل؛ تعرض كل بطاقة النماذج البرمجية المرتبطة وحدودها وبياناتها المطلوبة.':'The reference is stored locally with traceable versions. A reference rule does not mean a fully implemented school; each card shows the linked coded models, their scope and required data.',
    'المصدر المرجعي ↗':'Reference source ↗',
    'تسمية مرتبطة بمرجع آخر':'Name linked to another reference',
    'مراجع ذات صلة':'Related references',
    'النماذج البرمجية المرتبطة':'Linked coded models',
    'مرجع محفوظ؛ لا يوجد نموذج تداول مرتبط حاليًا.':'Stored reference; no trading model is currently linked.',
    'القوائم المالية والتدفقات النقدية وتوقعات الشركات وبيانات القطاع غير متاحة من شموع المنصة وحدها. القواعد محفوظة كمرجع ولا تصدر توصية تنفيذ دون بياناتها.':'Financial statements, cash flows, company forecasts and sector data are not available from platform candles alone. Rules are stored as a reference and issue no execution recommendation without their required data.',
    'عرض القواعد والاستثناءات والبيانات':'View rules, exceptions and data',
    'الاستثناءات وحدود التفسير':'Exceptions and interpretation limits',
    'البيانات المطلوبة':'Required data',
    'المراجع الأصلية':'Original references',
    'لا توجد مراجع بهذه التصفية.':'No references match this filter.',
    'تظهر المكتبة المحفوظة بعد تحميل الخدمة المحلية.':'The stored library appears after the local service loads.',
    'ملاحظات تطبيق القواعد':'Rule-application observations',
    'نتائج مكتملة محفوظة':'Stored closed outcomes',
    'نتائج صالحة للتعلم':'Eligible learning outcomes',
    'نتائج مستبعدة':'Excluded outcomes',
    'تعلم بالملاحظة':'Observational learning',
    'حالة التعلم غير متاحة':'Learning state unavailable',
    'تعذر تقييم سجل التعلم؛ راجع تقرير التشخيص.':'Learning evaluation failed; review the diagnostic report.',
    'عينة غير كافية':'Insufficient sample',
    'مراجعة تراجع النتائج':'Review deterioration',
    'مرشح للبحث':'Research candidate',
    'أدلة متباينة':'Mixed evidence',
    'تقلب مرتفع':'High volatility',
    'النموذج وإصدار القاعدة':'Model and rule version',
    'حالة السوق':'Market regime',
    'نتائج العينة':'Sample outcomes',
    'متوسط العائد بوحدة المخاطرة':'Mean return in risk units',
    'متوسط مرجح بالحداثة':'Recency-weighted mean',
    'معدل النتائج الموجبة المنعم':'Smoothed positive-outcome rate',
    'نتائج العينة اللاحقة':'Later holdout outcomes',
    'عائد العينة اللاحقة':'Holdout return',
    'حالة المراجعة البحثية':'Research review status',
    'لم تتوفر نتائج مكتملة كافية لبدء تقييم التعلم.':'There are not enough closed outcomes to evaluate learning.',
    'النتائج تتأثر باختيار الصفقات وترابطها وقد تتغير بعد تصحيح التكاليف. معدل النتائج الموجبة تاريخي منعم؛ ليس احتمال نجاح الصفقة القادمة ولا إثباتًا للربحية. وحدة المخاطرة تعتمد على مخاطرة الدخول الأصلية.':'Results are affected by trade selection and correlation and may change after cost corrections. The positive-outcome rate is a smoothed historical measure, not the next trade’s success probability or proof of profitability. Risk units use original entry risk.',
    'حُفظ تقرير المعرفة والتعلم محليًا.':'The knowledge and learning report was saved locally.',
    'مسار الملف المحلي':'Local file path',
    'راجع سجل العمليات للحصول على مسار المرجع.':'Review the operations log for the reference path.'
  });
  Object.assign(en,{'يجب أن تكون أسعار التنفيذ موجبة ومحدودة':'Execution prices must be finite and positive.'});
  Object.assign(en,{'اختبار أمامي على الحساب التجريبي دون اشتراط التأهيل التاريخي':'Forward Demo testing without historical qualification'});
  Object.assign(en,{'التأهيل التاريخي لبروتوكول المدارس الأربع غير متاح؛ اختر الاختبار الأمامي على الحساب التجريبي.':'Historical qualification for the four-school protocol is unavailable; choose forward Demo testing.'});
  Object.assign(en,{'إعدادات التكاليف المحفوظة غير صالحة؛ راجع تقرير التشخيص.':'The stored cost settings are invalid; review the diagnostic report.'});
  Object.assign(en,{
    'السكالب غير مفعل':'Scalping is off',
    'محدد؛ ينتظر استئناف التنفيذ':'Configured; waiting for execution to resume',
    'تقدم دورة السكالب المتسارع':'Fast scalp sweep progress',
    'مدة آخر دورة مكتملة':'Last completed sweep duration',
    'زمن العودة المرصود لنفس الرمز':'Observed revisit time for the same symbol',
    'ثانية':'seconds',
    'لم تكتمل دورة بعد':'No completed sweep yet',
    'لم يُقَس بعد':'Not measured yet',
    'المدة مرصودة وتتغير حسب البيانات والوسيط؛ لا تمثل سرعة مضمونة.':'These observed timings vary with the data and broker; they are not a guaranteed speed.'
  });
  Object.assign(en,{
    'الطلب قيد التنفيذ ولم تصل هوية متابعته؛ راجع السجل قبل إعادة الإرسال.':'The request is pending without a tracking ID; review the log before submitting it again.',
    'الإجراء في قائمة العمل؛ انتظر نتيجته باستخدام معرّف الطلب.':'The action is queued; use its request ID to wait for the result.',
    'معرّف الإجراء غير موجود أو انتهت مدة حفظ نتيجته':'The action ID is unknown or its saved result has expired.',
    'قائمة الإجراءات ممتلئة؛ لم يُرسل هذا الإجراء':'The action queue is full; this action was not submitted.',
    'الخدمة توقفت قبل تنفيذ الإجراء؛ لم يُنفذ':'The service stopped before this action ran; it was not executed.',
    'معرّف طلب واحد مطلوب':'Exactly one request ID is required.',
    'الخدمة توقفت؛ أعد تشغيل التطبيق':'The service has stopped; restart the application.',
    'الطلب في قائمة العمل؛ ننتظر النتيجة الفعلية دون إعادة إرساله.':'The request is queued; waiting for its actual result without submitting it again.',
    'تعذر التحقق من نتيجة الطلب؛ راجع السجل قبل إعادة الإرسال.':'The request result could not be verified; review the log before submitting it again.',
    'لم تنته العملية ضمن مهلة المتابعة؛ قد تكتمل لاحقًا. راجع السجل قبل إعادة الإرسال.':'The operation has not finished within the tracking period and may complete later. Review the log before submitting it again.',
    'التعلم المحلي من خصائص الشموع':'Local learning from candle features',
    'تقييم مستقل عن التنفيذ':'Evaluation independent of execution',
    'نتائج مرتبطة بخصائص الدخول':'Outcomes linked to entry features',
    'نتائج بلا خصائص دخول أصلية':'Outcomes without original entry features',
    'خصائص مستبعدة بعد التحقق':'Features excluded after validation',
    'الحد الأدنى لكل إصدار ورمز وفريم':'Minimum per revision, symbol and timeframe',
    'نتائج التدريب':'Training outcomes',
    'نتائج متداخلة مستبعدة':'Purged overlapping outcomes',
    'خطأ النموذج في العينة اللاحقة':'Model holdout Brier error',
    'خطأ خط الأساس في العينة اللاحقة':'Baseline holdout Brier error',
    'عينة التدريب تحتوي نتيجة من فئة واحدة':'Training sample contains only one outcome class',
    'تم التقييم البحثي المستقل':'Independent research evaluation completed',
    'لم تتوفر صفقات مكتملة تحمل خصائص الدخول الأصلية لهذا التعلم.':'No closed trades with original entry features are available for this learning.',
    'يتعلم مصنف محلي من ثماني خصائص للشموع المكتملة ونتائج الصفقات بعد التكاليف. تُحفظ الخصائص وقت قرار الدخول ولا تُستنتج لاحقًا من شارت جديد. يُدرّب على عينة سابقة ويُقيّم على عينة لاحقة منفصلة، مع استبعاد نتائج لم تكن قد أغلقت عند بداية التقييم. يقارن أخطاء التنبؤ بخط أساس بسيط. لا يغير هذا التقييم قواعد التداول أو المخاطرة أو أوزان اللجنة تلقائيًا.':'A local classifier learns from eight completed-candle features and after-cost trade outcomes. Features are frozen at the entry decision and never inferred from a later chart. It trains on earlier observations and evaluates a separate later sample, purging outcomes that had not closed when evaluation began. Prediction errors are compared with a simple baseline. This evaluation does not automatically change trading rules, risk or committee weights.'
  });
  Object.assign(en,{
    'نتائج الفحص غير المؤهلة':'Ineligible scan results',
    'تشمل الانتظار والرفض وانتهاء الصلاحية؛ ليست جميعها أوامر مرفوضة.':'Includes waiting, rejection and expiry; these are not all rejected orders.',
    'الانتظار قرار صالح؛ لا يُخفَّض معيار الدخول للاقتراب من الهدف.':'Waiting is a valid decision; entry criteria are not lowered to approach the target.',
    'انتظار تأكيد إغلاق الوسيط':'Waiting for broker exit confirmation',
    'نتيجة مطابقة إغلاق الوسيط':'Broker exit reconciliation result',
    'حد الخسارة اليومي':'Daily loss limit',
    'الهدف اليومي':'Daily target',
    'تعديل حدود اليوم والتفويض':'Edit daily limits and authorization',
    'تفاصيل دورة الفحص':'Scan cycle details',
    'اختيار نمط السكالب':'Choose scalp mode',
    'سكالب عادي':'Normal scalp',
    'سكالب سريع':'Fast scalp',
    'تطبيق نمط السكالب المحدد':'Apply selected scalp mode',
    'حدد النمط واضبط قيمه ثم اضغط تطبيق؛ الاختيار وحده لا يغير التداول.':'Select a mode, set its values, then apply. Selection alone does not change trading.',
    'اختيار غير مطبق بعد؛ اضبط قيم النمط ثم اضغط تطبيق.':'Selection not applied yet; set the mode values, then apply.',
    'اعتمد حدود اليوم أولًا من نموذج التفويض.':'Authorize the daily limits in the activation form first.',
    'طُلب تطبيق نمط السكالب؛ راجع النمط النشط بعد التأكيد.':'Scalp mode application requested; check the active mode after confirmation.',
    'وقت هذا القرار':'Time of this decision',
    'لا يوجد أمر مرتبط بهوية هذا الاقتراح في السجل المعروض.':'No order linked to this proposal identity appears in the displayed ledger.',
    'حالة الأمر المرتبط بهذا الاقتراح':'Order status linked to this proposal',
    'وقت إنشاء الأمر':'Order creation time',
    'القرار الحالي وحالة الأمر سجلان منفصلان؛ رفض إشارة جديدة لا يلغي تنفيذًا سابقًا.':'The current decision and order status are separate records; rejecting a new signal does not undo an earlier execution.',
    'منتهي الصلاحية':'Expired',
    'إشارة الدخول المختارة':'Selected entry trigger',
    'دليل مساند':'Supporting evidence',
    'دليل معارض':'Opposing evidence',
    'دون تصويت اتجاهي':'No directional vote',
    'بنية السعر والشموع':'Price structure and candles',
    'المؤشرات المشتقة من السعر':'Price-derived indicators',
    'الحجم أو نشاط التكات':'Volume or tick activity',
    'الأصل المقابل':'Paired asset',
    'أدلة جميع نماذج التحليل':'Evidence from all analysis models',
    'هذه نتائج النماذج المحفوظة مع قرار الدخول، وليست أصوات خمس مدارس مستقلة. تُجمع الأدلة المترابطة قبل الترجيح.':'These model evaluations were saved with the entry decision. They are not five independent school votes. Related evidence is grouped before weighting.',
    'تفاصيل كل نموذج':'Details of every model',
    'الدور في القرار':'Role in the decision',
    'هذا قرار سابق لا يحتوي تفاصيل النماذج المحفوظة؛ لا يُستنتج منه الحياد.':'This older decision has no saved model details; neutrality cannot be inferred.',
    'تدفق النشاط من التكات تقريب، وليس تدفق صفقات فعليًا. درجات اكتمال القواعد ليست احتمالات ربح.':'Tick activity is a proxy, not actual transaction flow. Rule-completion scores are not win probabilities.',
    'انتهت صلاحية هذا الاقتراح؛ حالة الأمر المنفذ تُراجع بشكل مستقل.':'This proposal has expired; the executed order status is tracked separately.'
  });
  Object.assign(en,{
    'من البيانات إلى النتيجة':'From data to outcome','بانتظار بيانات الشارت':'Waiting for chart data','مسار الشارت محدث':'Chart path updated',
    '١ · الإدخال':'1 · Input','٢ · فحص البيانات':'2 · Data checks','٣ · المدارس':'3 · Schools','٤ · لجنة القرار':'4 · Decision committee','٥ · المخاطر والتنفيذ':'5 · Risk and execution',
    'شموع الرمز والفريم المختارين من الوسيط':'Broker candles for the selected symbol and timeframe','التوقيت والترتيب واكتمال الشموع':'Candle time, order and completion',
    'كل نموذج يعرض دليله وحدوده منفردًا':'Each model reports its own evidence and limits','تجمع الأدلة وتعرض قرارها وأسبابه':'Combines evidence and reports its decision and reasons',
    'طبقة منفصلة؛ لا ينشأ أمر من بطاقة المدرسة':'Separate layer; a school card does not create an order','لا توجد عينة شارت مفحوصة':'No chart sample has been checked',
    'صالحة زمنيًا حتى':'Time-validated through','الشمعة الحالية غير مستخدمة':'The current unfinished candle is not used','بطاقة من النماذج المسجلة +':'registered model cards +',
    'تحليل منفصل لا يصوت للجنة':'separate analysis that does not vote in the committee','فرصة معروضة؛ التفاصيل وأسباب الانتظار تحت قرار اللجنة':'opportunities shown; details and wait reasons are under the committee decision',
    'وضع النظام':'System mode','تحليل فقط':'Analysis only','خط الاتجاه':'Trend Line','تحليل مستقل للشارت · لا يرسل أوامر':'Independent chart analysis · sends no orders',
    'لم يبدأ':'Not started','اختر رمزًا وفريمًا ثم اعرض الشارت لقراءة محاور الاتجاه والخطوط والكسر المؤكد.':'Choose a symbol and timeframe, then display the chart to inspect trend pivots, lines and confirmed breaks.',
    'خط الاتجاه / Trend Line':'Trend Line school','لا يوجد كسر مؤكد لخط صالح من ثلاث قمم أو قيعان محورية مكتملة.':'No confirmed break of a valid line formed from three completed swing highs or lows.',
    'شراء':'BUY','بيع':'SELL','محايد':'NEUTRAL','إشارة تحليلية فقط.':'Research observation only.','إغلاق مكتمل فوق مقاومة هابطة؛ إشارة تحليلية فقط.':'Completed close above descending resistance; research observation only.',
    'إغلاق مكتمل تحت دعم صاعد؛ إشارة تحليلية فقط.':'Completed close below ascending support; research observation only.',
    'لم تتوفر ثلاثة محاور مؤكدة متقاربة بما يكفي لبناء خط صالح.':'Three sufficiently aligned confirmed pivots are not available to form a valid line.',
    'دعم صاعد':'Rising support','مقاومة هابطة':'Falling resistance','الميل لكل شمعة':'Slope per candle','السعر عند آخر إغلاق':'Price at latest close',
    'خطأ الملاءمة / ATR':'Fit error / ATR','المحاور المؤكدة':'Confirmed pivots','الشموع المكتملة':'Completed candles','نطاق التقلب ATR':'ATR volatility range',
    'صلاحية التنفيذ':'Execution authority','لم يتكون خط صالح من ثلاثة محاور مؤكدة بعد.':'No valid line from three confirmed pivots has formed yet.',
    'قاعدة المدرسة':'School rule','ثلاث نقاط محورية مؤكدة؛ كسر لا يثبت إلا بإغلاق مكتمل.':'Three confirmed pivot points; a break is recognized only on a completed close.',
    'لا يصوت للجنة ولا يرسل أوامر.':'It does not vote in the committee or send orders.'
  });
  window.NEXUS_I18N={en,translate,apply};
})();
