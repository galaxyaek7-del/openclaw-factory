# ADR-027 — أرضية اقتصادية رابعة `gumroad_elite` لـTier 1 ($97-$497)

**التاريخ:** 2026-07-13
**الحالة:** معتمَد، منفَّذ، مختبَر.
**يُنفِّذ:** `ELITE_ASSET_DOCTRINE.md` — مهمة #5 ("Tier 1: أرضية $97+، ربما $297+").

## القرار

منصة اقتصادية رابعة مستقلة `gumroad_elite` في `config/economics.json`، بنفس نمط الإضافة المستقل الذي أثبت نفسه مرتين (`gumroad_digital` في `ADR-020`، `gumroad_premium` في `ADR-024`):

- **أرضية ربح: $70.00 صافي** (يعادل تقريباً سعر $97 عند عمولة Gumroad 90%: `97 × 0.9 = 87.3`).
- **نطاق `butter_price(niche, product_type="elite")`: $97–$497** — فرع مستقل تماماً عن فرعي `"printable"`/`"premium"`، لا صيغة مشتركة، حتى لا يتأثر أي منهما بإضافة هذا.
- **سقف واقعية سوق مستقل:** $10/صفحة، حزمة أقصر من 15 صفحة تُحدُّ عند $97 (الأرضية نفسها، لا إعفاء كامل من الفحص).

`kdp_ebook` ($6.00)، `gumroad_digital` ($2.50)، `gumroad_premium` ($25.00): **بلا أي تغيير** — تحقَّق حياً بمقارنة مباشرة قبل/بعد.

## التحقق

- `economics.evaluate(97, "gumroad_elite", ...)` → معتمَد (net $87.30 يتجاوز أرضية $70).
- `economics.evaluate(50, "gumroad_elite", ...)` → مرفوض (net $45 دون الأرضية).
- حزمة قصيرة (5 صفحات) بسعر $497 → `market_realistic: False`، سعر مقترَح ≤ $97 — نفس فلسفة السقف في `gumroad_premium`، لا استثناء.
- `butter_price()` لكل من `"book"`/`"printable"` مطابق حرفياً لما قبل هذا التغيير (3 نيتشات، مقارنة مباشرة ضد commit سابق).
- 7 اختبارات جديدة في `tests/test_butter_price_tiers.py`.

## الأثر

- ملفات مُعدَّلة: `config/economics.json`, `economics.py` (تعديل سطر واحد في `net_profit()`'s platform tuple)، `profit_oracle.py` (`MIN/MAX_BUTTER_PRICE_ELITE` + فرع `"elite"` مستقل في `butter_price()`)، `book_generator.py` (`_economics_platform_for("elite")`)، `schemas/product.py` (توجيه `product_type="elite"`).
- `kdp_ebook`, `gumroad_digital`, `gumroad_premium`: **بلا أي تغيير**.
