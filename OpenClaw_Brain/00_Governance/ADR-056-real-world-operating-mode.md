# ADR-056 — Real World Operating Mode: توصيل الإشارات الحقيقية بخط الأنابيب الموجود

**التاريخ:** 2026-07-16
**الحالة:** مُنفَّذ ومُختبَر بالكامل (302 اختباراً بايثون + 69 جافاسكريبت، كلها تمر). **لم يُشغَّل بـ`execute_production=True` على بيانات حقيقية بعد — قرار معلَّق على إذن الرئيس صراحة (انظر §القرار المفتوح أدناه).**
**يُنفِّذ:** "Executive Directive — Phase 4: Real World Operating Mode."

---

## القرار

حزمة `real_world_mode/` — **ليست محرّكاً جديداً، ليست وكيلاً جديداً، ليست إعادة تصميم.** البنية التحتية الحالية (`orchestrator.orchestrator.run_cycle()`, `ADR-051`) تُطبِّق فعلياً Signal→Analysis→Decision→[Production→Publishing]→Learning بالكامل. الفجوة الوحيدة الحقيقية: **لا آلية تربط "إشارة خارجية حقيقية موجودة في هذا المصنع" بـ"خط الأنابيب الموجود رآها فعلاً."** هذا كل ما بُني:

```
real_world_mode/
  signal_intake.py     — يقرأ مصدرين حقيقيَين موجودين فعلاً، يُشكِّلهما بصيغة external_signal الموجودة أصلاً
  operating_mode.py       — يستدعي orchestrator.run_cycle() مرة لكل إشارة حقيقية — صفر منطق قرار جديد
```

## مصدرا الإشارة — موجودان فعلياً، لا اختراع

- **`OPPORTUNITIES.md`**: يُقرَأ عبر `profit_oracle._read_opportunities()` **مباشرة** (نفس المُحلِّل الحقيقي الذي يستخدمه `run_oracle()` نفسه) — لا تحليل ثانٍ لتنسيق أسطره.
- **`tier1_intake/candidates/*.json`**: ملفات بحث Tier-1 حقيقية موجودة فعلاً (`ADR-035/036`)، كل منها يحمل كتلة `source` حقيقية (نجوم GitHub / نقاط HN) — تُحوَّل مباشرة لنفس صيغة `external_signal` التي يقبلها `profit_oracle.opportunity_score()` أصلاً (`ADR-038`)، لا صيغة جديدة.

**تحقُّق فعلي (2026-07-16):** `signal_intake.collect_all_real_signals()` وجد **111 إشارة حقيقية** من هذين المصدرين مجتمعين.

## `operating_mode.py` — استدعاء بحت، صفر منطق جديد

`run_real_world_cycle()` يستدعي `orchestrator.orchestrator.run_cycle()` **دون أي تعديل عليه** لكل إشارة. لا مخزن جديد، لا تسجيل محرّك جديد، لا مسار تنفيذ جديد. `execute_production` افتراضه `False` — نفس اتفاقية `run_cycle()` نفسها.

## "كل نتيجة منصة يجب أن تُحدِّث سجل Production Evidence" — مُحقَّق بنائياً، لا كود جديد

`production_evidence` (`ADR-055`) دالة نقية على بيانات غير قابلة للتغيير — **لا تحتاج "تحديثاً"**، تعكس أي قرار/تنفيذ جديد لحظة استدعائها. **تحقَّق فعلياً** (`test_production_evidence_history_reflects_the_cycle_automatically`): تشغيل دورة واحدة عبر `run_real_world_cycle()` ثم استدعاء `production_evidence.catalog.list_all_evidence_records()` يُظهِر النيتش الجديد فوراً — بلا أي كود ربط إضافي.

**تحقُّق أوسع على الإشارات الحقيقية الفعلية (شبكة مُموَّهة، تخزين معزول):** تشغيل الـ111 إشارة الحقيقية عبر `run_real_world_cycle(execute_production=False)` أنتج 111 قراراً حقيقياً في مرحلتَي Analysis/Decision، و**كتالوج Production Evidence عكس تلقائياً 39 نيتشاً مميَّزاً** (OPPORTUNITIES.md يحوي تكرارات كثيرة لنفس النيتش بمتغيّرات طفيفة — `latest_decision_per_niche()` يُصفِّيها بشكل صحيح).

## القرار المفتوح — لم يُنفَّذ فعلياً، بانتظار إذن صريح

**التنفيذ الفعلي (`execute_production=True`) لم يُشغَّل في هذه الجلسة على أي إشارة حقيقية.** هذا يعني: صفر استدعاء حقيقي لـ`book_generator.py` (تكلفة Groq حقيقية)، صفر محاولة نشر حقيقية. الأسلاك جاهزة ومُختبَرة بالكامل — لكن تفعيلها الفعلي على دفعة من إشارات حقيقية (إنفاق تلقائي متكرر لكل إشارة تُقبَل) يقع ضمن فئة "الخدمات المدفوعة" التي تتطلب إذناً صريحاً حسب صلاحية التنفيذ القائمة لهذه الجلسة — لم يُتَّخَذ هذا القرار بالنيابة عن الرئيس، يبقى معلَّقاً صراحةً حتى تعليمات إضافية.

## ماذا لم يُبنَ عمداً

- **لا مُجدوِل (scheduler) جديد.** "لا مُجدوِل موجود" حقيقة معمارية واعية لهذا المصنع (مؤكَّدة عدة مرات هذه الجلسة) — `run_real_world_cycle()` دالة تُستدعى عمداً (يدوياً أو عبر أداة جدولة خارجية لاحقاً، قرار نشر منفصل عن نطاق الكود)، لا حلقة تشغيل ذاتية جديدة.
- **لا تخزين جديد.** كل نتائج `run_real_world_cycle()` تمر عبر `orchestrator.timeline`/`decision_engine.store` الموجودين حرفياً، بلا نسخة ثانية.

## الأثر

- ملفات جديدة: 2 تحت `real_world_mode/` + هذا الـADR.
- `tests/test_real_world_mode.py`: 12 اختباراً جديداً (المجموع الآن 302 بايثون).
- صفر تغيير على `orchestrator/`، `decision_engine/`، `market_intelligence_core/`، `executive_intelligence/`، `strategic_intelligence/`، `validation_layer/`، `production_evidence/`، `server.js`، `factory_loop.js`.
