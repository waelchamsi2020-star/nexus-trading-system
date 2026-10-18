# بيانات MT5 الأصلية لبوابة البحث

## التصدير

في MT5: انقر يمينًا داخل Market Watch ثم Symbols (أو View → Symbols / Ctrl+U)،
ثم Bars → اختر رمز الوسيط والفريم M5 → Request → Export.
كرّر ذلك للفريم H1. مسار Tools → History Center يخص MT4، وليس مسار MT5 هنا.
المصدر الرسمي: https://www.metatrader5.com/en/terminal/help/trading/market_watch#history
MetaTrader يخزن تاريخ الدقيقة ويشتق منه الفريمات؛ «أصلية» هنا تعني تصدير الفريم
من المنصة، دون إعادة تجميع ملف M1 القصير داخل أداة البحث.

احفظ مثلًا data/real/M5/EURUSD_M5.csv وdata/real/H1/EURUSD_H1.csv.
لا ترفع بيانات الحساب الخاصة أو ملفات الأسعار إلى GitHub.

## متطلبات القبول الحالية

- 5000 شمعة مكتملة على الأقل لكل ملف، مرتبة زمنيًا، بلا تكرار أو فجوات.
- فارق الطوابع 300 ثانية لـM5 و3600 ثانية لـH1؛ لا شموع مستقبلية.
- التوقيت UTC فعليًا. تصدير المنصة قد يستعمل توقيت خادم الوسيط: تحقّق من
  الإزاحة وتغير التوقيت الصيفي وحوّلها تحويلًا موثقًا قبل التصريح timezone=UTC.
- ملف التقويم FX_UTC22_V1 يسمح بفجوات الجمعة22:00UTC إلى الأحد22:00UTC،
  وبغياب شموع25ديسمبر و1يناير UTC،ويرفض أي شمعة ناقصة خارج هذه الفترات.
  هذه سياسة بحثية مطلوبة من المتداول؛ليست جدول وسيط موثقًا،ولا تستنتج DST
  أو إغلاق الصيانة اليومي. العملات الرقمية وغيرها افتراضيًا CONTINUOUS.
- لا تُملأ أي فجوة بشموع مصطنعة. الحد الأدنى5000شمعة باقٍ؛4320تجتاز
  فحص التقويم وحده لكنها لا تجتاز قبول حجم الملف.
- مرجع ساعات وسيط كمثال على اختلاف التوقيت والعطلات،لا كإثبات لوسيط الحساب:
  https://www.oanda.com/us-en/trading/hours-of-operation/
  https://www.oanda.com/us-en/trading/holiday-trading-hours/
- الأعمدة: <DATE>, <TIME>, <OPEN>, <HIGH>, <LOW>, <CLOSE>, <TICKVOL>, <SPREAD>؛
  <VOL> اختياري. الفاصل فاصلة أو فاصلة منقوطة أو Tab؛ ترميز UTF-8.
- التاريخ YYYY.MM.DD والوقت HH:MM:SS. Tick Volume وكيل تقريبي، لا Order Flow حقيقي.
- العمولة موثقة لدورة كاملة لكل لوت بعملة الحساب. point وcontract_size من مواصفات
  الرمز. يشترط تطابق account_currency وprofit_currency؛ التحويل غير مدعوم هنا.
- تبقى سياسة الانزلاق10نقاط لكل جانب دون تخفيض؛ السبريد من كل صف.

## ملف الوصف المرافق

بجانب EURUSD_M5.csv أنشئ EURUSD_M5.metadata.json بالمفاتيح التالية.
القيم النصية REPLACE_ME تُستبدل بمصدر الوسيط؛ المثال ليس إثباتًا لتكلفة حسابك.
لا تستخدم صفر عمولة إلا إذا وثق الوسيط ذلك.

```json
{
  "source": "MT5_NATIVE",
  "aggregated": false,
  "symbol": "EURUSD",
  "timeframe": "M5",
  "timezone": "UTC",
  "account_currency": "USD",
  "profit_currency": "USD",
  "point": "REPLACE_ME_WITH_NUMBER",
  "contract_size": "REPLACE_ME_WITH_NUMBER",
  "commission_per_lot": "REPLACE_ME_WITH_ROUND_TRIP_NUMBER",
  "fee_source": "REPLACE_ME_WITH_BROKER_DOCUMENT_AND_DATE"
}
```

لـH1 عدّل timeframe إلى H1. لا تتضمن الملف رقم حساب أو كلمة مرور.

## التشغيل من جذر مصدر التطبيق

```powershell
python tools/edge_test.py --data-root data/real --output-dir reports/edge-native
```

المساران المستقبَلان: data/real/M5/*.csv وdata/real/H1/*.csv.
تُقرأ أوصاف جميع الملفات وتُطابق فريماتها قبل بدء التقييم؛ تحقق البيانات والتكاليف لكل ملف يسبق تقييمه. ينتج كل ملف تقريرًا منفصلًا في
reports/edge-native/M5 أو H1، مع SHA256 وتكاليفه ونتائج النماذج58.
ملف منفرد:

```powershell
python tools/edge_test.py --csv data/real/M5/EURUSD_M5.csv --metadata data/real/M5/EURUSD_M5.metadata.json --output reports/edge-M5.json
```

EDGE_FOUND: صافي R موجب و30صفقة محاكاة على الأقل فقط؛ لا يمثل دلالة إحصائية
أو تصريح تداول حي. نقص السياق اليومي/الأصل المقابل لا يُستبدل بدليل مصطنع.

## التصدير الآلي المحلي
تم استقبال10000شمعةلكلفريممنMT5للقراءةفقط؛SHA256والخصائصفيreports/native-auto-export.json. لمتُخترعالعمولةولمتُملأالفجوات. القيمالقالبيةفيmetadataتمنعالتقييمحتىتوثيقالتكاليف.
