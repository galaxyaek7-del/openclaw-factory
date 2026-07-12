# pending_review/ — Human-in-the-Loop review queue for premium products

**نموذج "المراجعة المعلقة" (`HIGH_VALUE_EXECUTION_PLAN.md`).** لا API جديدة، لا تكلفة إضافية —
الرئيس يفتح Claude Code (نفس الاشتراك الحالي) دورياً، يقول "راجع المسودات المعلقة"، وClaude
(الجلسة نفسها) يقرأ/يُحسِّن/يُشغِّل السكربتات أدناه مباشرة عبر أدواته الحالية (Read/Edit/Bash) —
بلا استدعاء API جديد من داخل الكود مطلقاً.

## دورة حياة المسودة (4 مجلدات، لا قاعدة بيانات)

```
queue/      ← مسودة خام من Groq (رخيصة، آلية بالكامل) — بانتظار المراجعة
approved/   ← بعد تحسين المحتوى (بشري + Claude) — جاهزة للمعالجة الآلية
completed/  ← نجحت (published:true) — مؤرشَفة مع النتيجة الكاملة للتدقيق
rejected/   ← فشل الفحص المزدوج بعد المراجعة — مؤرشَفة مع السبب (نفس فلسفة REJECTED_NICHES.md)
```

## شكل ملف المسودة (JSON)

```json
{
  "title": "The AI-Powered Solopreneur System",
  "subtitle": "A real subtitle, not a placeholder",
  "chapters": [
    {"title": "Chapter 1: ...", "content": "Full chapter text..."}
  ],
  "price": 97,
  "product_type": "premium",
  "theme": "blue",
  "author": "OpenClaw Press",
  "created_at": "2026-07-12T20:00:00",
  "source": "groq_draft",
  "review_notes": null
}
```

- `product_type`: `"book"` | `"printable"` | `"premium"` — يحدد أرضية الربح الاقتصادية المستخدَمة في الفحص المزدوج (`ADR-020`/`ADR-024`).
- `source`: `"groq_draft"` (لم يُراجَع بعد) أو `"human_claude_review"` (بعد التحسين — نفس القيمة التي يكتبها `generate_book_from_content()` في `result["content_source"]`).
- `chapters[].content` في `queue/`: مسودة Groq خام، مقبولة الجودة لكن ليست بمستوى بيع $97. بعد المراجعة في `approved/`: محتوى مُحسَّن فعلياً، لا نفس النص القديم بمجرد تغيير الحالة.

## خطوات المراجعة (يدوية، من الرئيس عبر Claude Code)

1. اقرأ كل ملف في `queue/`.
2. حسِّن `chapters[].content` (وربما `title`/`subtitle`) فعلياً — لا تكتفِ بنسخه.
3. اكتب النسخة المُحسَّنة في `approved/` بنفس الاسم، احذف الأصل من `queue/`.
4. شغِّل `python scripts/process_approved_drafts.py` — يُكمل الفحص المزدوج + التسجيل + توزيع dry-run تلقائياً لكل ملف في `approved/`، وينقله إلى `completed/` أو `rejected/` حسب النتيجة.

## ملاحظة تشغيلية صادقة

لا آلية اليوم تُنشئ مسودات في `queue/` تلقائياً — هذا خطوة لاحقة موثَّقة في `HIGH_VALUE_EXECUTION_PLAN.md`، ليست جزءاً من بنية اليوم الأساسية. `queue/` فارغ حتى يُملأ يدوياً أو عبر أداة توليد مسودات تُبنى لاحقاً.
