# Quant Trading AI 0.6.22

## سبب توقف الدخول وإصلاحه

في 16 أكتوبر 2026 عند 20:51:53 بتوقيت دبي، غابت صفقة MSFT المؤكدة سابقًا من المراكز المفتوحة قبل ظهور إغلاقها في تاريخ الوسيط. وصل إثبات الإغلاق عند 20:51:56. المنظومة ألغت التفويض فورًا أثناء الفجوة، وبقيت قراءة فقط بعد اكتمال المطابقة. هذا سبب مباشر لتوقف التداول، منفصل عن شروط قبول الاستراتيجيات.

الإصلاح: عندما تختفي صفقة مؤكدة سابقًا فقط، تحتفظ المنظومة بحجز المخاطرة وتمنع جميع الأوامر الجديدة، وتعيد قراءة سجل الوسيط ضمن نافذة تسوية قصيرة. بعد إثبات الإغلاق يستمر التفويض القائم. إذا انتهت مهلة إعادة القراءة، أو تغير الحساب أو اليوم أو الاتصال أو الصلاحيات، يُلغى التفويض. لا تُعاد الأوامر المرسلة، ولا يُعاد تفعيل تفويض ملغى تلقائيًا. النتائج غير المحسومة السابقة وأوامر الإدارة غير المؤكدة لا تستفيد من استثناء الصفقة المؤكدة الغائبة.

مهلة إعادة القراءة 6 ثوانٍ وبحد أقصى 25 قراءة؛ مكالمة وسيط مفردة قد تتجاوز هذه المدة. تُحفظ بداية الانتظار ونتيجته ومدته واستمرار التفويض في سجل دائم. لا تُحرر المخاطرة اعتمادًا على غياب الصفقة وحده.

## السكالب والتفويض

- أزرار منفصلة: سكالب عادي، سكالب سريع، وإيقاف السكالب.
- الاختيار مسودة واضحة؛ زر «تطبيق نمط السكالب المحدد» يعتمد التغيير عبر مسار التفويض والفحص المعتاد.
- يستحيل تفعيل العادي والسريع معًا. لكل نمط حقول مخاطرة وهدف مستقلة؛ القيم الناقصة تمنع تفعيله.
- التبديل يحافظ على الحد والهدف اليوميين المحفوظين ولا يغلق المراكز الحالية أو يحذف سجلها.
- بطاقة التفويض مختصرة: تعرض الحالة والحد والهدف وأزرار النمط، وتفتح تفاصيل الحدود والمسح عند الطلب. لا تُخفى حالة المخاطرة أو النمط النشط.

## التحقق والحدود

نجحت 513 وحدة اختبار، منها خمسة اختبارات جديدة لفجوة الإغلاق الطبيعية وتأخر التاريخ وانتهاء المهلة وتغير الحساب والغموض المستقل. نجحت اختبارات الواجهة لاختيار النمط وتطبيقه والتنافي بين النمطين واختلاف الأهداف وحفظ حدود اليوم ومنع القيم الناقصة. إعادة فحص اختبارات التسوية بعد إضافة سجل النتائج نجحت أيضًا: 19 اختبارًا.

لا يغير الإصلاح قواعد الاستراتيجيات أو مستوى تأكيد الدخول أو الوقف الفني أو سياسة جني الدولار. تحسين الجدوى المالية، وخصوصًا الفرق بين الهدف الفني وهدف الدولار، يبقى عملًا مستقلًا يحتاج اختبارًا بسياسة الخروج نفسها. الاختبارات تمنع رجوع الخطأ الذي تغطيه؛ ليست ضمانًا لغياب كل الأخطاء أو لتحقيق ربح يومي.

## English release summary

Previously confirmed broker positions could disappear from the live book about three seconds before their exit deals appeared in history. Periodic reconciliation immediately revoked execution authorization. Version 0.6.22 introduces a bounded, read-only confirmation window for newly missing, previously confirmed entries. All sends remain blocked and risk stays reserved until affirmative closure evidence arrives. Expiry, unrelated uncertainty, account/day/permission changes and disconnection still revoke authorization. Previously revoked authorization is never automatically restored.

Separate normal, fast and off buttons select a draft mode; explicit application uses the existing authorization and risk path. Only one variant can be enabled. The authorization card is compact, with detailed daily settings and scan statistics collapsed on demand. Entry strategy rules, stops and cash exit policy are unchanged. Automated tests do not establish profitability.
