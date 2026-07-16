# ADR-058 — Real Market Evidence Engine: صفر % جودة أدلة اليوم، وهذا صحيح

**التاريخ:** 2026-07-16
**الحالة:** مُنفَّذ ومُختبَر بالكامل (315 اختباراً بايثون + 69 جافاسكريبت، كلها تمر).
**يُنفِّذ:** "Executive Directive – Phase 5: Real Market Evidence" — "Never fabricate. If data cannot be verified, return UNKNOWN."

---

## الحد الصريح: لا استخراج بيانات Amazon حي، ولن يكون

هذا المصنع **لا يملك ولم يملك أبداً** واجهة برمجية مجانية وقانونية لـAmazon. المصدر الحقيقي الوحيد لبيانات Amazon في تاريخ هذا الكود بأكمله هو `niche_validator_v2.py` — أوفلاين ويدوي عمداً: إنسان يحفظ صفحة نتائج بحث Amazon حقيقية من متصفحه (Ctrl+S)، والسكربت يُحلِّل هذا الملف محلياً. **بناء استخراج آلي حي من Amazon كان سيخالف شروط استخدام Amazon نفسها ومبدأ "صفر خطر على حساب Amazon" الذي يوثِّقه `niche_validator_v2.py` بنفسه صراحة** — حد معماري واعٍ من هذه الجلسة، لا سهواً، ولم يُتجاوَز هنا.

## القرار

حزمة `real_market_evidence/` — تجمع الـ10 مقاييس المطلوبة، **حصراً** من `profit_oracle._find_niche_report()` (نفس البحث الحقيقي الذي يستخدمه `_score_competition()`/`_score_margin()` أصلاً منذ `ADR-041/042` — إعادة استخدام حرفية، لا بحث ثانٍ).

```
real_market_evidence/
  types.py                — عقد Evidence (source/timestamp/confidence/raw_value/normalized_value/explanation) + METRICS
  evidence_collector.py     — collect_evidence(niche) + evidence_quality_summary(niches)
```

## أربعة من عشرة مقاييس: Unknown بنيوياً، حتى مع تقرير محفوظ حقيقي

`Best Seller Rank`، `marketplace age`، `update frequency`، `seller concentration` **لا تظهر في لقطة صفحة نتائج بحث واحدة أبداً** — BSR يظهر فقط في صفحة تفاصيل منتج فردي (لا يحفظها `niche_validator_v2.py` اليوم)، والثلاثة الأخرى تحتاج مراقبة متكرِّرة عبر الزمن أو نسبة بائع لكل قائمة، غير مُستخرَجة من نوع الصفحة المحفوظة أصلاً. `Revenue indicators` **Unknown دائماً بلا شرط** — Amazon لا يُظهر أرقام مبيعات علنية مهما حَفِظت.

المقاييس الستة المتبقية (عدد نتائج البحث، عدد القوائم المنافسة، توزيع الأسعار، توزيع المراجعات، تشبُّع الفئة) **حقيقية بالكامل عند وجود تقرير محفوظ** — تُقرَأ مباشرة من حقول `niche_validator_v2.py`'s الحقيقية الموجودة أصلاً في `metrics.total_results`/`books_analyzed`/`price`/`reviews`. `category_saturation` مُشتقّة من `total_results` مقابل `profit_oracle.MAX_COMPETITION` — نفس الحد الموجود أصلاً، لا سقف جديد مُخترَع.

## التحقُّق الحقيقي على الحالة الفعلية اليوم: 0% جودة أدلة

**تأكَّد مباشرة قبل الكتابة:** `niche_reports/` فارغ تماماً — صفر تقرير Amazon محفوظ في هذا المصنع. تشغيل `evidence_quality_summary()` على أي مجموعة نيتشات حقيقية اليوم يُعيد **`evidence_quality_pct: 0.0`** — كل الـ10 مقاييس Unknown لكل نيتش، بلا استثناء. **هذا هو المقياس الصحيح لمعنى النجاح المطلوب صراحة: "measured only by increasing evidence quality, never by increasing accepted opportunities"** — اليوم 0%، وهذا صادق، لا خلل.

## هل يُغيِّر هذا أي قرار قبول/رفض؟ لا — والسبب موثَّق

هذا المحرِّك **لا يُعدِّل** `profit_oracle.py` — آلية "فضِّل الدليل الحقيقي على التقدير عند وجوده" موجودة أصلاً منذ `ADR-041/042` عبر `_find_niche_report()` نفسها. بما أن صفر تقرير محفوظ موجود اليوم، **إعادة تشغيل التقييم الكامل (كما طُلِب) على نفس الفرص الـ39 تُنتج نتائج مطابقة تماماً** لتشغيل `ADR-057` — لا تغيير، لأن لا بيانات حقيقية جديدة ظهرت. هذا متوقَّع، لا خلل: **بمجرد أن يحفظ إنسان تقريراً حقيقياً واحداً لنيتش واحد، `real_market_evidence` و`profit_oracle.py` كلاهما سيعكسان بيانات منافسة/تسعير/مراجعات حقيقية لذلك النيتش تحديداً فوراً، بلا أي تغيير كود إضافي.**

## الأثر

- ملفات جديدة: 3 تحت `real_market_evidence/` + هذا الـADR.
- `tests/test_real_market_evidence.py`: 9 اختبارات جديدة (المجموع الآن 315 بايثون).
- صفر تغيير على `profit_oracle.py`، `niche_validator_v2.py`، أو أي طبقة تسجيل موجودة.
- صفر استخراج بيانات Amazon حي — لن يُبنى، حد معماري واعٍ.
