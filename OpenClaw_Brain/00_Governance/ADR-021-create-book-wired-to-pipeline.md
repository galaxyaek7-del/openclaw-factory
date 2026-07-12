# ADR-021 — `create_book()` مربوطة الآن بالفحص المزدوج + السجل + التوزيع

**التاريخ:** 2026-07-12
**الحالة:** معتمَد، منفَّذ، مختبَر حياً من طرف إلى طرف (dry-run فقط).
**يُغلق:** الفجوة الأخيرة الموثَّقة في `ADR-020`/`PRICING_AND_FIRST_PRODUCTS.md` — "لا يوجد رابط فعلي بين `create_book()` وDual Inspection/السجل/`distributor.py`".

## القرار

دالة جديدة `generate_printable()` في `book_generator.py` تستدعي `create_book()` **بلا أي تعديل على منطقها الداخلي** (نفس القيد الصريح)، ثم تُمرِّر نتيجتها عبر **نفس** خط الأنابيب الذي تستخدمه `generate_book()` بالفعل: `inspectors.py`'s `final_inspection()` (بـ`platform="gumroad_digital"`)، `_log_generation()`، ودائرة `_record_rejected_niche()`. مُوصَّلة بـCLI `book_generator.py --json` عبر `product_type: "printable"` في مدخل JSON.

## التحقق الحي (dry-run فقط، لا نشر حي)

توليد فعلي حقيقي لـ"Monthly Budget Planner" (`type=budget`, 15 صفحة, $5) عبر `book_generator.py --json`:
- **الفحص الفني:** نجح بالكامل (PDF صالح 15 صفحة، لا نص placeholder، لا غلاف منفصل متوقَّع لأن `create_book()` يرسم الغلاف داخل نفس الملف).
- **الفحص التجاري:** نجح بالكامل — `profit_score: 71/100`، و**`butter_price: "net $4.50 clears floor $2.50 (platform: gumroad_digital)"`** — يؤكد حياً أن أرضية Gumroad المنفصلة ($2.50، `ADR-020`) تعمل فعلياً عبر المسار الحقيقي، لا نظرياً فقط.
- **`published: true`**، مُسجَّل في `books/_generation_log.jsonl` الحقيقي.
- `schemas/product.py`'s `Product.from_jsonl_record()` على نفس السجل: `product_type="printable"`, `price_usd=5.0`, `needs_pricing=False` — يقرأ الحقل الجديد بشكل صحيح.
- `distributor.py --json` (`dry_run: true`) على نفس السجل: محاولة توزيع حقيقية عبر `channels/gumroad_arm.py`، فشل آمن متوقَّع (`"arm not ready: unavailable"` — لا `GUMROAD_ACCESS_TOKEN`)، بلا أي استثناء أو عطل.

**الحلقة الكاملة (توليد → فحص → تسجيل → ترجمة Product → محاولة توزيع dry-run) عملت من طرف إلى طرف بلا أي تدخل يدوي بينها.**

## الأثر

- ملف مُعدَّل: `book_generator.py` (دالة جديدة `generate_printable()` + فرع CLI جديد في `main()` — `create_book()` وكل الدوال الأخرى بلا أي تعديل).
- ملف حقيقي جديد: `books/monthly_budget_planner.pdf` + سطر جديد في `books/_generation_log.jsonl` (من الاختبار الحي أعلاه — ليس منتجاً وهمياً، لكنه أيضاً لم يُنشَر حياً على Gumroad ولن يُنشَر بلا `FACTORY_LIVE_PUBLISH=true` + توكن حقيقي، كلاهما غائب اليوم).
- لا تعديل على `inspectors.py`, `distributor.py`, `channels/*`, `schemas/product.py` — كلها استُخدمت كما هي.
