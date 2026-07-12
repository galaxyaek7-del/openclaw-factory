# ADR-018 — تدقيق سلسلة الوكلاء + ربط Scout بالتوزيع والتسعير الحقيقي

**التاريخ:** 2026-07-12
**الحالة:** معتمَد، منفَّذ جزئياً (ربط فقط — لا منطق أعمال جديد).
**السياق:** آخر جلسة بناء تقني قبل التحول الكامل للتسويق (توجيه الرئيس، 2026-07-12). التركيز: من يمرّر مخرجاته لمن، لا بناء أي وكيل جديد.

---

## 1. خريطة الربط الفعلية اليوم (قبل هذا القرار)

| من | إلى | الحالة |
|---|---|---|
| `market_hunter.py`/`profit_oracle.py` (Golden Hunter) | `factory_loop.js` → `triggerGenerateBook` → `distributor.py` | ✅ مربوط (ADR-009/010) |
| `factory_loop.js`'s `hunt()`/`healEmptyBooks()` | `book_generator.py` → `distributor.py` | ✅ مربوط (عبر `triggerGenerateBook`) |
| `book_generator.py` (Dual Inspection: `inspectors.py`) | نتيجة `published`/`inspection` | ✅ مدمج داخل `generate_book()` نفسها |
| `distributor.py` | `channels/gumroad_arm.py` → `sales_ledger.jsonl` | ✅ مربوط |
| `sales_ledger.jsonl` (بيع حقيقي) | `factory_loop.js` (استطلاع كل تِكّة) | ✅ مربوط اليوم سابقاً (ADR-016) |
| `/api/scout/run` (زر Scout في اللوحة) | `book_generator.py` | ✅ مربوط (مباشرة، بلا `/generate-book`) |
| **`/api/scout/run` → `distributor.py`** | — | ❌ **معزول** — كتاب Scout يُنتَج ولا يُوزَّع تلقائياً أبداً، خلافاً لكل مسارات `factory_loop.js` الأخرى |
| **`/api/scout/run` → `profit_oracle.butter_price()`** | — | ❌ **معزول** — سعر Scout مجرد تخمين Groq مقيَّد بتعليمة نصية ">=30$"، لا رقم `butter_price()` الحقيقي المستخدم في مسار Golden Hunter |
| وكلاء الدردشة الأربعة: `builder`, `design`, `qa`, `publisher`, `finance` (`/api/agent/:name`) | خط الإنتاج الحقيقي | ❌ **معزولون بالكامل** — نص استشاري لبشري فقط؛ لا `Publisher` يُطعِّم عنوان/وصف `distributor.py`، لا `Design` يُطعِّم `cover_generator.py`، لا `Finance`/`QA` يُطعِّمان `economics.py`/`inspectors.py` الحقيقيَّين |
| `reality.py`, `self_awareness.js` | القرارات الآلية | ⚪ مقصود أن يبقيا للقراءة فقط (لوحات صحة، لا أفعال) — ليس فجوة |

## 2. القرارات المنفَّذة اليوم (ربط فقط)

**ADR-18.1 — ربط `/api/scout/run` بـ`distributor.py`.**
بعد نجاح `book_generator.py` ونشر حقيقي (`published !== false`)، `autoDistributeScoutBook()` تقرأ آخر سطر `books/_generation_log.jsonl` (نفس آلية `readLastGenerationRecord()` المستوردة من `factory_loop.js` دون تعديلها) وتستدعي `distributor.py` عبر دالة مشتركة جديدة `runDistributor()` (استُخرجت من جسم `/api/distribute` نفسه — بلا تغيير سلوك). `dry_run` يتبع نفس بوابة `FACTORY_LIVE_PUBLISH` الموجودة أصلاً في `factory_loop.js`، منسوخة حرفياً في `server.js`.

**ADR-18.2 — ربط `/api/scout/run` بـ`profit_oracle.butter_price()` الحقيقية.**
بعد تحديد `brief` (من Groq أو fallback)، يُستدعى `getButterPrice(brief.topic)` — نفس الدالة المُصدَّرة والمُختبَرة أصلاً من `factory_loop.js` لمسار Golden Hunter — لتحديد السعر النهائي، بدل ترك السعر تخميناً نصياً من Groq. فشل الحساب يُطبَّق عليه نفس سقوط آمن (`fallback_floor_clamped`, حد 30$) الموجود في `briefFromGoldenOpportunity()`.

**ADR-18.3 — لا ربط لوكلاء الدردشة الأربعة اليوم.**
ربط `Publisher`/`Design`/`Finance`/`QA` الفعلي بخط الإنتاج (مثلاً: إخراج Publisher يصبح عنوان/وصف `distributor.py` الحقيقي) يتطلب تعديل `schemas/product.py`/`distributor.py` — أي لمس منطق أعمال، وهو خارج تفويض هذه الجلسة الصريح ("لا تلمس منطق الأعمال"، ووقت 30-45 دقيقة). **يبقى فجوة موثَّقة، لا شيء أُنجز بشأنها اليوم** — يستحق جلسة مركّزة مستقلة، تماماً مثل `PRODUCT_VISION.md`.

## 3. قرار سرعة النبض: يبقى 10 دقائق، **لا** يُخفَّض إلى 5

**الفحص:** أطول سلسلة داخل تِكّة واحدة هي `triggerGenerateBook` (حد 150 ثانية لـ`/generate-book`) + `triggerDistribute` (حد 140 ثانية لـ`/api/distribute`) = **حتى ~290 ثانية (4.83 دقيقة) في أسوأ الحالات الفعلية** — تحدث فقط عندما يُنتج `hunt()`/`healEmptyBooks()`/`golden_hunter_bridge` كتاباً حقيقياً، لا في كل تِكّة. لا يوجد حارس منع تداخل التِكّات (`setInterval` لا ينتظر انتهاء `safeTick()` السابقة).

**القرار: لا، ليس آمناً عند 5 دقائق.** عند 300 ثانية فاصل، أي تِكّة تُصادف توليداً+توزيعاً حقيقياً فعلياً (أسوأ حالة ~290 ثانية) تترك هامش أمان شبه معدوم (~10 ثوانٍ) قبل أن يبدأ الفاصل التالي — خطر تِكّتين متزامنتين (توليد كتاب مزدوج، استدعاء Groq مضاعف، تعارض على `books/_generation_log.jsonl`) حقيقي وغير مقبول. إضافة حارس "تِكّة قيد التنفيذ" كانت ستُصلح هذا، لكنها تُعتبَر منطقاً جديداً (لا ربطاً بحتاً) وخارج تفويض اليوم الصريح. **الفاصل يبقى 10 دقائق كما هو — لا تعديل على `INTERVAL_MS`.**

## 4. الأثر

- ملف مُعدَّل: `server.js` (دالة `runDistributor()` مشتركة، `autoDistributeScoutBook()`، ربط `getButterPrice()` داخل `/api/scout/run`؛ `/api/distribute` نفسها بلا تغيير سلوك، فقط إعادة استخدام).
- ملف غير مُعدَّل: `factory_loop.js`, `distributor.py`, `book_generator.py`, `channels/*`, `profit_oracle.py`, `economics.py`, `inspectors.py` — كل منطق الأعمال سليم كما كان.
- `INTERVAL_MS` في `factory_loop.js`: **بلا تغيير** (يبقى 600000ms/10 دقائق) — قرار موثَّق أعلاه، ليس سهواً.
- فجوة موثَّقة لا مُنفَّذة: ربط وكلاء الدردشة الأربعة (Publisher/Design/Finance/QA) بخط الإنتاج الحقيقي — تحتاج جلسة مستقلة.
