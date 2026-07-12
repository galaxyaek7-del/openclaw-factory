# ADR-023 (مقترَح، لا تنفيذ) — دمج حزم متعددة الملفات في PDF واحد قبل Gumroad

**التاريخ:** 2026-07-12
**الحالة:** 🔴 اقتراح فقط، جزء من `HIGH_VALUE_STRATEGY.md` — لم يُنفَّذ.

## الاكتشاف

بمراجعة `channels/gumroad_publisher.py`'s `create_product()` اليوم: يرفع **ملفاً واحداً فقط** لكل منتج —
```python
files = {"file": (file_path.name, fh, "application/pdf")}
```
منتج "حزمة" (دليل + قوالب، مثل `HIGH_VALUE_STRATEGY.md`'s المقترَح الأول) يحتاج أكثر من ملف تقنياً.

## المقترَح: دمج، لا توسيع Gumroad API

بدل تعديل `channels/gumroad_arm.py`/`gumroad_publisher.py` (خطر إضافي، سطح هجوم أكبر على تكامل منصة خارجية حساس فعلاً) — **دمج كل مكوّنات الحزمة في ملف PDF واحد نهائي عبر `pypdf`** (مثبَّتة بالفعل، استُخدمت اليوم في `diagnostics/arabic_rendering_check/check_arabic_rendering.py`) قبل أن يصل الملف لـ`distributor.py` أصلاً. مثال مفاهيمي:

```python
from pypdf import PdfWriter
merger = PdfWriter()
for component_pdf in [guide_pdf, budget_tracker_pdf, habit_tracker_pdf]:
    merger.append(component_pdf)
merger.write(final_bundle_pdf)
```

## لماذا هذا أأمن

- **لا تعديل على `channels/gumroad_arm.py`/`gumroad_publisher.py`** — كلاهما مُختبَران، يعملان، ولمسهما يعني إعادة اختبار تكامل منصة خارجية حقيقية.
- الدمج يحدث **قبل** `distributor.py` بمرحلة كاملة — دالة مساعدة مستقلة (مثلاً `bundle_builder.py`)، لا تُعدِّل أي عقد قائم (`BaseArm`, `Product`).
- عيب معروف: كل ملف يصبح PDF واحد طويل بدل ملفات منفصلة قابلة للتنزيل فردياً — مقبول لمرحلة إثبات المفهوم، قابل لإعادة نظر لاحقاً إن أظهرت المبيعات طلباً على ملفات منفصلة.

## الأثر المتوقَّع (عند التنفيذ الفعلي لاحقاً)

- ملف جديد مقترَح: `bundle_builder.py` (مستقل، بنفس فلسفة `distributor.py`/`ledger.py` — لا استيراد من داخل `channels/`).
- لا تعديل على أي ملف قائم في `channels/`.
