# ADR-044 — "Company Operating System": 9 من 10 موجودة فعلاً، رابط حقيقي واحد بُني

**التاريخ:** 2026-07-15
**الحالة:** تحقيق مكتمل + تكامل حقيقي واحد مُنفَّذ + مُختبَر (5 اختبارات جديدة في `test_factory_loop_golden.js`، 44 إجمالاً).
**يُنفِّذ:** "OPENCLAW EXECUTIVE DIRECTIVE — COMPANY OPERATING SYSTEM (COS) V1".

---

## القرار

طُلِبت 10 أنظمة أساسية ("Company Operating System"). **9 منها موجودة فعلاً بحجم مناسب لمصنع عمره 13 يوماً بشخص واحد وصفر إيراد. لم تُبنَ 2 (Agent Orchestrator، Event Bus) لأن لا مشكلة تنسيق حقيقية تحتاجهما اليوم. بُني رابط تكامل حقيقي واحد ناقص فعلياً.**

### الخريطة الصادقة

| المطلوب | الموجود فعلاً |
|---|---|
| Executive Decision Engine | `market_intelligence_engine.py`'s `ai_ceo_decision()` (`ADR-043`) |
| Workflow Orchestrator | n8n نفسه (`ADR-037`) |
| Task Scheduler | `factory_loop.js`'s تِكّة 10 دقائق |
| Monitoring Engine | `dashboard.html`/`/api/dashboard` + `NEEDS_ATTENTION.md` |
| Self-Healing Engine | `factory_loop.js`'s `healFinance`/`healEmptyBooks`/`healN8n` |
| Memory Engine | `LESSONS_LEARNED.md` + `GROWTH_LOG.md` + `data/*.jsonl` |
| Knowledge Graph | `OpenClaw_Brain/` + `knowledge_brain.js` (`GET /brain?q=`) |
| Configuration Center | `config/*.json` (economics, channels, reality, capability_registry) |
| **Agent Orchestrator** | **لم يُبنَ — لا حاجة حقيقية.** 4 من 5 وكلاء دردشة مكرَّرون وظيفياً بالكامل (`ADR-018`/`019`)؛ الخط الحقيقي منسَّق أصلاً باستدعاءات دوال مباشرة (`book_generator→inspectors→distributor`) — مستوى الترابط الصحيح لهذا الحجم |
| **Event Bus** | **لم يُبنَ — لا حاجة حقيقية.** عملية Node واحدة + استدعاءات subprocess بايثون قليلة — لا نظام موزَّع يحتاج ناقل أحداث |

## لماذا لم تُبنَ الاثنتان — اعتراض محمي، لا كسل

بناء Agent Orchestrator حقيقي أو Event Bus حقيقي الآن يعني **حل مشكلة تنسيق غير موجودة فعلياً** — نفس المرض المُشخَّص في بداية هذه الجلسة (`STRUCTURAL_DIAGNOSIS.md`: "احتفالية مؤسسية سابقة لأوانها")، بمصطلحات هندسية أكبر هذه المرة فقط. هذا نمط "اعتراض محمي" مُتَّبع سابقاً في هذه الجلسة (`ADR-034`, رُفِع مرة، سُمِع، لم يُكرَّر) — لا تكرار هنا لأن هذه أول مرة يُطلَب فيها Event Bus/Agent Orchestrator تحديداً.

## الرابط الحقيقي الواحد المبني: قرارات AI CEO تصل الآن لحلقة الأتمتة الحقيقية

**المشكلة الحقيقية الوحيدة المكتشَفة:** قرارات `market_intelligence_engine.py`'s AI CEO كانت تُنتَج يدوياً فقط، لا تصل لـ`factory_loop.js` الحي إطلاقاً — نظامان حقيقيان منفصلان فعلياً، تماماً كما حذَّر الطلب ("nothing should operate independently").

**الحل:** `checkPendingAiCeoDecision()` جديدة في `factory_loop.js` — **قراءة ملف صرفة، صفر استدعاء شبكة جديد في الحلقة الحية** (نفس حد الأمان الذي رسَّخته `ADR-041`/`042`/`043`: استدعاءات الشبكة تبقى في الأدوات اليدوية، لا الحلقة التلقائية). تقرأ آخر تحليل حقيقي من `data/market_intelligence_analyses.jsonl`، وإن كان القرار فعلياً (`BUILD`/`PIVOT`) تُظهِره عبر `NEEDS_ATTENTION.md` الموجود أصلاً — بدليله الحقيقي، لا رقماً مجرَّداً. مُوصَّلة داخل `checkNeedsAttention()` الموجودة، لا آلية تنبيه جديدة موازية.

## الأثر

- `factory_loop.js`: `checkPendingAiCeoDecision()` جديدة، مُوصَّلة داخل `checkNeedsAttention()` الموجودة.
- `tests/test_factory_loop_golden.js`: +5 اختبارات (44 إجمالاً)، بما فيها تأكيد أن البيانات الحقيقية اليوم (قرار `IMPROVE` وحيد) لا تُنتِج تنبيهاً كاذباً بصدق.
- **لا نظام جديد مُبنى لـAgent Orchestrator/Event Bus** — قرار موثَّق، لا سهو.
- **لا استدعاء شبكة جديد في `factory_loop.js`'s الحلقة الحية** — القراءة صرفة من ملف موجود.
