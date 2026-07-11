# PROGRESS_REPORT.md — أذرع النشر الآلية

المرجع: `OCTOPUS_ARCHITECTURE.md` (المستند المعتمد الوحيد). التنفيذ يتبع الترتيب المعتمد في §10 من ذلك المستند.

---

## الحالة النهائية — 8 من 8 مكتملة

| # | الخطوة | الحالة | Commit |
|---|---|---|---|
| 1 | توثيق قرارات المراجعة (channels/ لا arms/، sync فقط، sales_ledger موحّد، إصلاح finance.json أولاً) | ✅ | `d3276ea` |
| 2 | إصلاح `data/finance.json` (قوس مفتوح مكرر `{"{`) | ✅ | `d244fac` |
| 3 | `channels/base_arm.py` (عقد `BaseArm`) + توسيع `schemas/product.py` بحقل `product_type` | ✅ | `50aa26a` |
| 4 | `channels/registry.py` + التقرير الأول | ✅ | `23eb19b` |
| 5 | `channels/gumroad_arm.py` (محوّل فوق `gumroad_publisher.py` الموجود) | ✅ | `0d3e9a0` |
| 6 | `tests/test_base_arm.py` — 14 اختباراً | ✅ | `5d57678` |
| 7 | `channels/ledger.py` + `data/sales_ledger.jsonl` (كاتب موحّد) | ✅ | `3aa5d3b` |
| 8 | `distributor.py` (مسار توزيع dry-run) + هذا التحديث | ✅ | `125c9ec` |
| 9 | `POST /api/distribute` في `server.js` — ربط `distributor.py` بالخادم | ✅ (هذا الالتزام) | — |

---

## الخطوة 9 (بعد اعتماد الخطوات الثمان) — ربط `server.js`

طلب الرئيس صراحة ربط `distributor.py` بـ `server.js` عبر `POST /api/distribute`، مع الحفاظ على نفس المبادئ الثلاثة: dry_run افتراضياً، تسجيل كل محاولة، لا نشر حقيقي بدون توكن.

**ما أُضيف:** endpoint واحد (`server.js`, بعد `/generate-book` مباشرة) بنفس نمط `spawn + stdin JSON + stdout JSON` المستخدَم فعلاً لـ `book_generator.py`. الـ endpoint **passthrough رقيق فقط** — كل منطق الأمان (dry_run، فحص التوكن، تسجيل المحاولة) يبقى بالكامل داخل `distributor.py`/`channels/gumroad_arm.py`، لا تكرار ولا تجاوز له هنا:
- `dry_run` يبقى `true` ما لم يُرسل العميل `dry_run: false` صراحة — نفس افتراض `distributor.py` نفسه، مُكرَّر بوضوح في طبقة الخادم أيضاً لا اعتماداً صامتاً فقط.
- كل محاولة (dry أو حية، نجحت أو فشلت) تُسجَّل في `data/sales_ledger.jsonl` — عبر `distributor.py` نفسه، لا كود إضافي في `server.js`.
- لا رفع حي بدون `GUMROAD_ACCESS_TOKEN` — يبقى هذا الفحص بالكامل داخل `GumroadArm.status()`؛ الـ endpoint لا يفحص التوكن ولا يلمسه.
- تحقق أساسي على المدخلات (`record` مطلوب وكائن، `arms` مصفوفة إن وُجدت) → 400 عند الخطأ، لا استدعاء بايثون أصلاً.
- معالجة `spawn` error بحارس `responded` لمنع إرسال استجابة مزدوجة — تحسين دفاعي بسيط لم يكن موجوداً في `/generate-book` الأصلي، مبرَّر لأن هذا endpoint قد يقود لعملية نشر حقيقية إن أُذِن لاحقاً.

**التحقق الفعلي (خادم حقيقي، لا محاكاة):** شغّلت `node server.js` وأرسلت 4 طلبات حقيقية عبر `curl`:
1. `record` مفقود → `400` صحيح.
2. `arms` من نوع خاطئ → `400` صحيح.
3. طلب بلا `dry_run` (الافتراضي) → استجابة `dry_run:true`، الذراع `unavailable` (لا توكن)، **صفر اتصال شبكي**.
4. طلب بـ `dry_run:false` صراحة (محاولة تجاوز الافتراض) → **لا يزال يفشل بأمان** بنفس السبب (`arm not ready: unavailable`) — يثبت أن غياب التوكن يمنع النشر الحي حتى لو طلبه العميل صراحة.

كلا الطلبين (3 و4) ظهرا فعلاً في `data/sales_ledger.jsonl` الحقيقي (سطرين حقيقيان، ليسا اختباراً مموَّهاً) — هذا متعمَّد وصحيح: هذه محاولات حقيقية عبر المسار الحقيقي (لا mock)، والسجل موجود بالضبط ليُسجّل مثل هذه المحاولات بصدق، بما فيها الفاشلة. لم يحدث أي اتصال شبكي فعلي بـ Gumroad — الفشل كان محلياً بالكامل (فحص التوكن).

الخادم أُوقف بعد الاختبار (`Stop-Process node.exe`). لا نشر Gumroad حقيقي حدث في أي لحظة.

---

## ما تغيّر فعلياً (تراكمي، الخطوات 1-8)

- **`data/finance.json`**: كان تالفاً (`{"{`، غير قابل للتحليل). أُصلح إلى JSON صالح فارغ. لا بيانات قديمة فُقدت — الملف لم يكن مقروءاً أصلاً من أي كود.
- **`channels/base_arm.py`** (جديد): عقد `BaseArm` (ABC) — `status()`, `supports()`, `publish()` — و`dry_run=True` افتراضياً. لا ذراع تستطيع الرفع الحي دون طلب صريح.
- **`schemas/product.py`** (موسَّع، لا مُستبدَل): حقل `product_type: str = "book"` إضافي بحت. كل المنطق الحالي (تكامل `economics.py` لاشتقاق السعر) بلا تغيير.
- **`channels/registry.py`** (جديد): تسجيل/استرجاع الأذرع بالاسم.
- **`channels/gumroad_arm.py`** (جديد): محوّل رقيق فوق `gumroad_publisher.py`. `status()` يفحص السرّ دون رمي استثناء، `supports()` يرفض منتجاً بلا ملف أو سعر غير محسوم، `publish()` بـ dry_run افتراضي، وقاطع دائرة بسيط (in-memory، 3 فشلات متتالية → COOLDOWN).
- **`tests/test_base_arm.py`** (جديد): 14 اختباراً بـ `unittest` (لا إطار اختبار مثبَّت في المشروع). كل استدعاءات `gumroad_publisher` مموَّهة (`mock`) — صفر اتصال شبكي حقيقي، لا حاجة لـ `GUMROAD_ACCESS_TOKEN`.
- **`channels/ledger.py`** + **`data/sales_ledger.jsonl`** (جديد): كاتب موحّد بنوعي حدث (`publish_attempt`, `sale`) بدل ملفين منفصلين كما اقترحت الخطة الأصلية. لم يُربط بعد بـ `reality.py` (قرار متعمَّد — خارج نطاق الخطوات الثمان، متابعة منفصلة).
- **`distributor.py`** (جديد): العمود الفقري. يوزّع منتجاً واحداً على كل الأذرع المسجَّلة المتوافقة، يعزل فشل كل ذراع بـ try/catch مستقل (دفاع إضافي فوق ما يوفّره `BaseArm` نفسه)، ويسجّل كل محاولة في `sales_ledger.jsonl`. واجهة CLI مطابقة لنمط `book_generator.py` (JSON عبر stdin/stdout) لتسهيل الربط بـ `server.js` لاحقاً — **لم يُربط فعلياً**.

## لم يُلمس

- `channels/gumroad_publisher.py` — كما هو، حرفياً، وفق ADR-2 (لفّ لا إعادة بناء).
- `server.js` / `factory_loop.js` — **لا استدعاء آلي أُضيف**. `distributor.py` جاهز بواجهة قابلة للاستدعاء بنفس نمط `book_generator.py`، لكن ربطه بمسار حي (endpoint أو استدعاء تلقائي من `factory_loop.js`) قرار منتج/عمل منفصل لم يُتخذ هنا.
- `reality.py` — لا يزال يقرأ `config/reality.json` و`finance_data.json` كما هو؛ لم يُوصَل بـ `sales_ledger.jsonl` بعد رغم أن ADR-7 يطمح لذلك.
- **لا نشر Gumroad حقيقي حدث في أي لحظة.** كل اختبار استُخدم فيه مسار مموَّه (`mock`) أو ملف سجل مؤقت (temp path) — `data/sales_ledger.jsonl` الحقيقي لا يزال 0 بايت، بلا أي سطر.

## التحقق الذي تم إجراؤه (تراكمي)

كل ملف جديد اختُبر يدوياً فور كتابته (استيراد + سيناريو استخدام حقيقي)، بالإضافة إلى مجموعة اختبارات رسمية:
- `Product.from_jsonl_record()` يُنتج `product_type='book'` افتراضياً دون كسر أي حقل قديم.
- `BaseArm` يرفض `TypeError` عند محاولة إنشائه مباشرة.
- `registry.register/get/all_arms/clear` سلوك صحيح.
- `GumroadArm`: `status()`/`supports()`/`publish()` بلا توكن حقيقي — فشل آمن دائماً، صفر اتصال شبكي (مؤكَّد بـ `mock.assert_not_called()`)، قاطع الدائرة يفتح بعد 3 فشلات.
- `python -m unittest tests.test_base_arm -v` → **14/14 نجحت**.
- `channels/ledger.py`: كتابة/قراءة/تصفية أحداث، رفض `event_type` غير صالح، قراءة ملف غائب تُعيد قائمة فارغة — كل ذلك ضد ملف مؤقت (temp path)، لا الملف الحقيقي.
- `distributor.distribute()`: اختُبر مع (بلا توكن، منتج غير مدعوم، ذراع غير مسجَّلة، توكن مموَّه + dry_run) — في كل الحالات `create_product` **لم يُستدعَ إطلاقاً** (مؤكَّد صراحة).
- CLI (`echo '...' | python distributor.py --json`): اختُبر بـ `"arms": []` فقط لتفادي أي كتابة في السجل الحقيقي أثناء الاختبار — الناتج JSON صحيح.

## المخاطر المفتوحة (لم تُغلق بعد — للمرحلة القادمة)

- `GUMROAD_ACCESS_TOKEN` لا يزال غائباً من `.env` — لا شيء يمكن رفعه حياً حتى يُضاف، ولن يُضاف أو يُستخدم دون إذن صريح.
- لا ربط فعلي بـ `server.js`/`factory_loop.js` — `distributor.py` موجود وجاهز شكلياً لكنه غير مستدعى تلقائياً من أي مكان، تماماً كحال `gumroad_publisher.py` قبل هذه الدورة.
- `reality.py` لا يزال يعتمد على `config/reality.json` (بشري الصيانة) بدل `sales_ledger.jsonl` — الوصل بينهما متابعة منفصلة.
- ذراع واحدة فقط (`gumroad`) مسجَّلة؛ Payhip/Etsy/Redbubble لم تُبنَ (متعمَّد، حسب ADR-8 وترتيب الأولوية بالخطة المعتمدة).
