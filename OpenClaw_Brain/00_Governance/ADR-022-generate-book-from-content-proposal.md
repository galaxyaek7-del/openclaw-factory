# ADR-022 (مقترَح، لا تنفيذ) — `generate_book_from_content()`: حقن محتوى بشري-Claude

**التاريخ:** 2026-07-12
**الحالة:** 🔴 اقتراح فقط، جزء من `HIGH_VALUE_STRATEGY.md` — لم يُنفَّذ.

## المشكلة

`generate_book()` (`book_generator.py`) يستدعي Groq داخلياً دائماً عبر `ai_generate_book_content()` — لا مسار لتزويده بمحتوى مكتوب مسبقاً (مثلاً: دليل ألّفه الرئيس بالتعاون مع Claude في محادثة حقيقية). أي منتج قيمة عالية يحتاج محتوى أعمق مما ينتجه نموذج سريع/رخيص (`llama-3.1-8b-instant`) بمحاولة واحدة.

## المقترَح

دالة جديدة موازية، **بنفس نمط `generate_printable()` المبني والمختبَر فعلياً اليوم (`ADR-021`)**:

```python
def generate_book_from_content(title, subtitle, chapters, price, theme="blue",
                                author="", output=None, product_type="book"):
    # chapters: [{"title": str, "content": str}, ...] — مكتوبة يدوياً بالكامل
    # يتخطّى ai_generate_book_content()/Groq بالكامل
    # يستدعي create_ai_book() الموجودة فعلاً بلا أي تعديل عليها
    # نفس Dual Inspection + _log_generation() + _record_rejected_niche()
    # التي تستخدمها generate_book()/generate_printable()
```

`product_type` قابل للتمرير (`"book"` أو `"premium"` — يرتبط بـ`ADR-024` لأرضية ربح مناسبة).

## لماذا لا تعديل على `generate_book()` نفسها

يخالف مبدأ Open/Closed (`PRINCIPAL_ARCHITECT_CHARTER.md` §2 مبدأ #3) — قدرة جديدة = دالة جديدة، لا تعديل في النواة. `ai_generate_book_content()`/`_fallback_book_content()` يبقيان كما هما لمسار Scout/hunt()/Golden Hunter العادي.

## الأثر المتوقَّع (عند التنفيذ الفعلي لاحقاً)

- ملف مُعدَّل: `book_generator.py` (دالة جديدة + فرع CLI جديد، مطابق لنمط `ADR-021`).
- لا تعديل على `create_ai_book()`, `inspectors.py`, `distributor.py`, `channels/*`.
- يحتاج اختباراً حياً مطابقاً لما جرى مع "Monthly Budget Planner" اليوم قبل أي استخدام حقيقي.
