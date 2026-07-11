# ADR-012 — تعميم Product schema لقبول كل خطوط الإنتاج (اقتراح، لا تنفيذ)

**التاريخ:** 2026-07-11
**الحالة:** اقتراح للمراجعة. لم يُنفَّذ أي سطر كود بموجب هذا الـADR.
**السبب:** استجابة لطلب "المرحلة 2" من `PRODUCT_VISION.md` — راجع `schemas/product.py`، هل يقبل خطوط الإنتاج التسعة الأخرى فعلياً؟
**تصحيح ترقيم:** طُلب هذا كـADR-011، لكن `ADR-011-readiness-certificate.md` مُسجَّل بالفعل بهذا الرقم (نفس اليوم، مهمة سابقة). يُستخدَم ADR-012 هنا، وADR-013 للاقتراح التالي (`base_arm.py`) — تسلسل صحيح، لا تعارض.

---

## الجواب المباشر: لا، `schemas/product.py` لا يقبل هذه الأنواع فعلياً

`product_type` موجود كحقل (أُضيف في جلسة سابقة، `schemas/product.py:110`) — لكن تعليقه الخاص يعترف بصدق: **"just a label, not a dispatch table"**. لا شيء في الكود يتفرّع بناءً عليه. المشكلة الحقيقية أعمق من غياب حقل — هي أن **مسار التسعير الوحيد الموجود مكتوب لكتاب KDP حرفياً**، لا لأي شيء آخر.

## الأدلة (كل سطر حقيقي، لا افتراض)

### 1. التسعير مربوط بمنصة كتاب واحدة، بالاسم الحرفي

`schemas/product.py:150`:
```python
result = economics.evaluate(raw_price_hint, "kdp_ebook", config, page_count=page_count)
```
`"kdp_ebook"` نص ثابت مكتوب مباشرة في الكود — التعليق في السطر 41-48 يعترف: *"Product has no platform field yet, so this is a documented assumption, not a guess about data"*. لقالب Notion أو اشتراك SaaS، `economics.evaluate()` سيُستدعى بنفس "kdp_ebook" وهو **خاطئ بنيوياً**، لا مجرد غير دقيق — `config/economics.json`'s `royalty_tiers` مصمَّمة لهوامش KDP، لا لمنتج بلا "طباعة" أو تكلفة توزيع مختلفة تماماً.

### 2. `page_count` مفهوم كتاب صرف

`schemas/product.py:149`:
```python
page_count = record.get("pages")
```
يُمرَّر إلى `economics.evaluate()`'s `market_realism_check` (فحص "هل السعر معقول لعدد الصفحات هذا؟"). لا معنى لـ"عدد صفحات" لقالب Excel أو أيقونة SVG أو اشتراك شهري. أي خط إنتاج جديد سيحتاج إما تمرير `None` (يُسقِط الفحص بصمت) أو معياراً مختلفاً كلياً (مثلاً: عدد المكوّنات لقالب، أو المدة بالدقائق لصوتي).

### 3. `from_jsonl_record()` مربوطة حصرياً بسجل واحد

الاسم نفسه (`from_jsonl_record`) وكل حقول الاستخراج (`inspection.title`, `cover.path`, `record.get("pages")`) مأخوذة من `books/_generation_log.jsonl` تحديداً — الملف الذي يكتبه `book_generator.py` فقط. لا يوجد جسر مكافئ لأي محرك إنتاج آخر لأن لا محرك آخر موجود بعد — لكن هذا يعني أن **إضافة خط إنتاج جديد يتطلب إما تعديل هذه الدالة (تكسير مبدأ Open/Closed) أو دالة موازية بلا نمط موحَّد**.

### 4. لا حقل واحد لنموذج التسعير

`Product` (الأسطر 90-110) — 13 حقلاً، كلها تفترض ضمنياً "دفعة واحدة مقابل ملف واحد":
```python
price_usd: float | None       # رقم واحد. لا "شهري" أو "سنوي" أو "ترخيص أبدي"
file_path: str                # ملف واحد. لا حزمة، لا "بلا ملف" (SaaS)
```
لا حقل `pricing_model` (one_time / subscription / license). لا حقل `recurring_interval`. لا حقل `license_tier`.

### 5. `channels/gumroad_arm.py` يرث نفس الافتراض مباشرة

`channels/gumroad_arm.py:71`:
```python
"price_cents": round(product.price_usd * 100),
```
سعر واحد يُحوَّل لسنتات مباشرة — يعمل لبيع لمرة واحدة فقط. أي ذراع SaaS مستقبلية ستحتاج مفهوماً مختلفاً كلياً (اشتراك متكرر، لا "سعر × 100").

---

## الاقتراح (تصميم، لا كود يُطبَّق الآن)

### أ. حقول جديدة على `Product` (إضافية، افتراضات آمنة — لا كسر لأي مستدعٍ حالي)

```python
@dataclass
class Product:
    # ... الحقول الـ13 الحالية بلا تغيير ...
    pricing_model: str = "one_time"      # "one_time" | "subscription" | "license"
    recurring_interval: str | None = None  # "monthly" | "yearly" — فقط عند subscription
    platform_hint: str | None = None     # يحل محل "kdp_ebook" الثابت — يُمرَّر صراحة، لا يُخمَّن
```
كل حقل جديد له افتراض آمن (`"one_time"`, `None`) — أي كود قائم يستدعي `Product(...)` بالكلمات المفتاحية الحالية يستمر بالعمل دون تعديل، بنفس نمط إضافة `product_type` سابقاً.

### ب. فصل منطق التسعير عن `from_jsonl_record()` — دالة تقييم قابلة للحقن

بدل استدعاء `economics.evaluate(price, "kdp_ebook", config, page_count=...)` مباشرة داخل `from_jsonl_record()`، تُفصَل خطوة "تقييم السعر" إلى دالة/معامل قابل للاستبدال حسب `product_type`:

```python
# دالة توجيه — ليست جزءاً من economics.py نفسه، طبقة رفيعة فوقه
def _resolve_pricing_strategy(product_type: str) -> dict:
    """يُرجع {platform_key, realism_check_field} حسب نوع المنتج.
    كتاب -> {"platform_key": "kdp_ebook", "realism_check_field": "pages"}
    قالب -> {"platform_key": "template_digital", "realism_check_field": None}  # لا فحص واقعية بعد
    ...
    """
```
هذا **لا يتطلب تعديل `economics.py` اليوم** — فقط يعني أن `config/economics.json` سيحتاج مستقبلاً `royalty_tiers` إضافية لكل منصة/نوع، وأن `from_jsonl_record()` (أو معادلها المستقبلي) يستشير هذا الجدول بدل الاسم الثابت.

### ج. جسور منفصلة لكل محرك إنتاج، لا دالة واحدة متضخّمة

بدل تعديل `from_jsonl_record()` نفسها لدعم مصادر جديدة (يكسر Open/Closed — ADR-4)، كل محرك إنتاج مستقبلي (`template_engine`, إلخ) يحصل على دالة جسر خاصة به تُنتج نفس `Product` الموحَّد:
```python
Product.from_jsonl_record(record)          # موجود، كتب فقط
Product.from_template_record(record)       # مستقبلي، عند بناء template_engine
Product.from_saas_signup(record)           # مستقبلي، مفهوم مختلف تماماً (لا ملف أصلاً)
```
كل دالة مسؤولة عن ترجمة شكل بياناتها الخاص إلى نفس الحقول الموحَّدة — بالضبط الفلسفة الأصلية لهذا الملف ("الفرق الوحيد يُحَل هنا، لا داخل كل ذراع") تُطبَّق الآن على مصادر الإنتاج، لا فقط على أذرع النشر.

### د. الاشتراكات (SaaS) — تغيير أعمق، ليس اليوم

`price_usd` كرقم واحد + `pricing_model="subscription"` غير كافٍ وحده — يحتاج مفهوم "إيراد متكرر حقيقي" لا موجود في أي مكان بالمصنع:
- `data/sales_ledger.jsonl` (`channels/ledger.py`) يسجّل حدثاً واحداً لكل بيع — لا مفهوم "اشتراك نشط" يتجدَّد.
- `reality.py`'s `net_revenue()`/`count_units_sold()` يفترضان مبيعات لمرة واحدة.
- هذا **لا يُصمَّم بالتفصيل هنا** — فقط يُوثَّق كحفرة معروفة (Hole Inventory، بنفس أسلوب `OCTOPUS_ARCHITECTURE.md` §7) لأن `PRODUCT_VISION.md` يطلب صراحة أن يقبله التصميم لاحقاً، لا أن يُبنى الآن.

## ما هذا الاقتراح لا يفعله

- لا يعدّل `schemas/product.py` فعلياً.
- لا يبني أي محرك إنتاج جديد.
- لا يصمّم بنية الاشتراكات الكاملة — يوثّقها كفجوة معروفة فقط.
- لا يغيّر `economics.py` أو `config/economics.json`.

## الحفر المفتوحة (صادقة، غير مُغلَقة بهذا الاقتراح)

1. لا معيار "واقعية سعر" (`market_realism_check`) موجود لأي نوع منتج غير الكتب — سيحتاج تصميماً مستقلاً لكل نوع عند بنائه فعلياً.
2. لا مفهوم "حزمة ملفات" (بدل ملف واحد) — يلزم لخطوط مثل القوالب المرخصة أو حزم الأصول الإبداعية.
3. لا مفهوم "بلا ملف إطلاقاً" — يلزم لـSaaS (المنتج وصول لخدمة، لا تنزيل).
