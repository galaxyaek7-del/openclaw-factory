# ADR-055 — Production Evidence Layer: دليل أعمال دائم، لا ذكاء إضافي

**التاريخ:** 2026-07-16
**الحالة:** مُنفَّذ ومُختبَر بالكامل (290 اختباراً بايثون + 69 جافاسكريبت، كلها تمر).
**يُنفِّذ:** "Executive Directive — Phase 3: Production Evidence Foundation" — "The objective is no longer to build more intelligence. The objective is to continuously accumulate trustworthy business evidence."

---

## القرار

حزمة `production_evidence/` جديدة — **لا محرّك جديد، لا وكيل ذكاء اصطناعي جديد، لا بُعد تسجيل جديد، لا تنسيق مكرَّر.** توفِّر سجل أدلة واحد لكل فرصة، بحقول التوجيه التسعة بالضبط، **بلا مخزن بيانات جديد إطلاقاً** — كل سجل دالة نقية على بيانات غير قابلة للتغيير موجودة فعلاً (`orchestrator.timeline`، `decision_engine.store`)، فلا شيء لإعادة كتابته فوق تاريخ سابق.

```
production_evidence/
  record.py     — build_evidence_record(niche) — يستدعي validation_layer.lifecycle.build_lifecycle() مباشرة
  catalog.py      — سجل أدلة لكل نيتش سبق اتخاذ قرار بشأنه
```

## "لا تنسيق مكرَّر" — إعادة استخدام حرفية لآلية مطابقة السجل الزمني الموجودة

`record.build_evidence_record()` **لا يُعيد بناء منطق مطابقة السجل الزمني بالنيتش** — يستدعي `validation_layer.lifecycle.build_lifecycle()` (`ADR-053`) حرفياً، وهي الدالة الوحيدة التي تُطابق سجلات `orchestrator` بنيتش عبر `orchestrator.orchestrator.make_idempotency_key()`. تكرار هذا المنطق هنا كان بالضبط ما يمنعه "no duplicate orchestration" في التوجيه.

## تعديل إضافي واحد صغير، موثَّق بدقة: لا حذف، فقط حقل جديد

`validation_layer/lifecycle.py`'s الدالة الداخلية `_stage_events()` كانت تُجرِّد كل سجل تنفيذ من حقل `output` الخام (تحتفظ فقط بـstatus/الأوقات/المدة/الخطأ) — هذا كان يمنع استخراج "Platform" (من مخرجات مرحلة النشر الحقيقية) بلا تكرار منطق المطابقة. أُضيف مفتاح `"output"` واحد فقط لكل حدث مرحلة — **إضافة بحتة، صفر حقل محذوف أو مُعاد تسميته.** تحقَّق ذلك باختبار مخصَّص (`test_existing_keys_are_all_still_present`) وبإعادة تشغيل مجموعة اختبارات `validation_layer` الكاملة (15 اختباراً) بلا أي تعديل عليها — كلها تمر.

## الحقول التسعة المطلوبة — من أين تُقرَأ فعلياً

| الحقل | المصدر الحقيقي |
|---|---|
| توقيت الاكتشاف | `lifecycle["signal"]["at"]` (مُعاد استخدامه) |
| لقطة الأدلة | `Decision.evaluation_snapshot` المُخزَّنة فعلياً (`ADR-050`) — لا إعادة حساب |
| القرار | `Decision.status`/`ai_ceo_decision`/`reasoning` المُخزَّنة فعلياً |
| حالة التنفيذ | `lifecycle["production"]` (مُعاد استخدامه) |
| حالة النشر | `lifecycle["publishing"]` (مُعاد استخدامه) |
| المنصة | **استخراج جديد بسيط** — من `output.outcomes` الحقيقي لمرحلة النشر |
| أحداث الإيراد | `lifecycle["revenue"]` (مُعاد استخدامه حرفياً) |
| ملاحظات العملاء | **Unknown دائماً اليوم** — لا قناة ملاحظات عملاء حقيقية متصلة بهذا المصنع (تحقَّق: لا وحدة واحدة لهذا الغرض في الكود بأكمله)؛ فحص دفاعي لحقول محتملة (`review`/`rating`/`comment`/`feedback`) في بيانات بيع حقيقية إن وُجدت مستقبلاً |
| النتيجة النهائية | **تصنيف جديد بسيط** — مُشتق من حالة القرار + نجاح الإنتاج/النشر + وجود إيراد حقيقي |

## "وحدات التعلُّم يجب أن تستهلك هذه السجلات بدل الذاكرة المؤقتة" — تحقَّق: مُطبَّق فعلاً بالفعل

راجعتُ `decision_engine.learning.compute_prediction_accuracy()`/`recalibration_report()` مباشرة: كلتاهما تقرآن حصراً عبر `decision_engine.store.latest_decision_per_niche()`/`read_outcomes()` (قراءات ملفات JSONL حقيقية)، **صفر حالة ذاكرة مؤقتة أو تخزين مؤقت داخل العملية.** هذا الشرط **مُحقَّق فعلاً منذ `ADR-050`**، لا يحتاج أي تغيير كود — يُسجَّل هنا كتحقُّق موثَّق، لا ادعاء أعمى.

## تحقُّق ملموس على البيانات الحقيقية اليوم

نيتش لم يُقيَّم بعد → `NOT_YET_EVALUATED`، `discovery_timestamp: None`، `platform` و`customer_feedback` كلاهما Unknown صراحة بسبب محدَّد — كل هذا صحيح فعلياً بلا أي بيانات وهمية.

## الأثر

- ملفات جديدة: 2 تحت `production_evidence/` + هذا الـADR.
- تعديل إضافي واحد فقط (حقل `output` جديد) في `validation_layer/lifecycle.py` — صفر حقل مُزال، صفر اختبار قديم احتاج تعديلاً.
- `tests/test_production_evidence.py`: 11 اختباراً جديداً (المجموع الآن 290 بايثون).
- **صفر مخزن بيانات جديد.** صفر محرّك جديد. صفر تعديل على `orchestrator/`، `decision_engine/`، `market_intelligence_core/`، `executive_intelligence/`، `strategic_intelligence/`، `server.js`، `factory_loop.js`.
