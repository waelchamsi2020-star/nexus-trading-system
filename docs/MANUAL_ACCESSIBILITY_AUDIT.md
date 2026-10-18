# نتائج الوصولية الآلية — اسم الملف تاريخي

المنفذ: Playwright/Chromium. لا يمثل تدقيقًا بشريًا أو اعتماد WCAG كاملًا.
142فحصًا ناجحًا؛48axe بلا مخالفات؛0JavaScript errors. الملاحظات البشرية اختيارية.

| الشاشة | Tab order | Focus visible | Enter | Esc | حصر Tab | الدليل | ملاحظات بشرية |
|---|---|---|---|---|---|---|---|
| دخول/الجلسة | PASS | PASS | PASS | لا ينطبق | لا ينطبق | page_token_session_authenticated؛رفض401؛keyboard_*_overview/setup؛لا نموذج كلمة مرور مستقل | |
| شراء | PASS | PASS | PASS:إرسال ونتيجة | PASS:إلغاء دون إرسال | PASS داخل التأكيد | keyboard_*_buy؛submit_buy_*؛keyboard_form_traversal_positions | |
| بيع | PASS | PASS | PASS:إرسال ونتيجة | PASS:إلغاء دون إرسال | PASS داخل التأكيد | keyboard_*_sell؛submit_sell_*؛keyboard_form_traversal_positions | |
| مصالحة | PASS | PASS | PASS:تشغيل فعلي مع سجل | لا ينطبق:إجراء فوري | لا ينطبق | keyboard_*_setup؛keyboard_reconcile_focus_visible؛run_reconciliation_* | |
| تأكيد | PASS | PASS | PASS:اعتماد | PASS:إلغاء | PASS:Tab/Shift+Tab داخل الحوار | keyboard_dialog_focus_trap_buy/sell؛keyboard_escape_cancels_buy/sell | |
| خطأ | PASS:زر إعادة المحاولة | PASS | PASS:تعافٍ من503 | PASS:لا يخفي الفشل | لا ينطبق | keyboard_error_focus_visible/enter_recovers/escape_does_not_hide_failure | |

المصدر: reports/browser-e2e.json. الصور: reports/browser/keyboard-*-before.png وafter.png؛خطأقبل/بعدمضافان.
الفجوة الصغيرة: قارئ الشاشة والإدراك البصري البشري غير مقاسين آليًا؛لا مطالبة المستخدم بتنفيذهما لهذه الدفعة.
التداول في الاختبار اصطناعي ومعزول؛لا اتصال إرسال إلىMT5.
