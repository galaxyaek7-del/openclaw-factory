# ADR-040 — إطار نضج القدرات: REAL / ESTIMATED / DISCOVERY

**التاريخ:** 2026-07-15
**الحالة:** مُنفَّذ + مُختبَر (23 اختباراً في `tests/test_dashboard_data.js`، 3 جديدة).
**يُنفِّذ:** "CEO Directive – Build the Intelligence Layer" — تصنيف كل مقياس إلى مستوى نضج واحد من ثلاثة، بدل قبول/رفض ثنائي.

---

## القرار

بدل التصنيف الثنائي السابق (`ADR-039`: "مُنفَّذ" أو "مرفوض") — **كل مقياس يُصنَّف الآن صراحة إلى واحد من ثلاثة**:

- **REAL** — محسوب من بيانات مُتحقَّق منها فعلاً (5 مقاييس: Risk Score، Automation Potential، Long-Term Value، Butter Price Floor، Confidence Score نفسه).
- **ESTIMATED** — نموذج قابل للتفسير فوق دليل متاح، **يجب أن يعرض `confidence`/`assumptions`/`missing_evidence` صراحة** (6 مقاييس: Demand بنوعيه، Competition بنوعيه، Margin، Execution Fit).
- **DISCOVERY** — غير قابل للحساب اليوم، **بدل اختراع رقم، خطة عمل دقيقة تصف ما هو مطلوب فعلياً** (17 مقياساً — نفس الـ26 المرفوضة في `ADR-039`، بعد دمج المكرَّرة منها مع مقاييس موجودة).

كل هذا في `config/capability_registry.json` — سجلّ واحد، لا كود مُشتَّت. `lib/dashboard_data.js`'s `readCapabilityMaturity()` يقرأه ويُلخِّصه، `dashboard.html` يعرضه ببطاقة عدّ + قسم "خارطة طريق الاكتشاف" يسرد كل خطة فتح حرفياً.

## لماذا هذا أفضل من `ADR-039`'s القبول/الرفض الثنائي

الرفض وحده ("لا بيانات، لن أبنيه") صحيح لكنه غير مكتمل — لا يقول **متى ولماذا** قد يصبح ممكناً. كل بند DISCOVERY الآن يحمل خطة فتح حقيقية ومحدَّدة، مثال: "Search Trend" ليست "مستحيلة" — خطتها: "`n8n Sensing Engine` مبني فعلاً وسليم بنيوياً (`ADR-037`)، الفتح الوحيد المطلوب هو تفعيله، لا هندسة جديدة." هذا تمييز مهم بين "يحتاج بناءً جديداً" و"يحتاج فقط تفعيل ما بُني بالفعل".

## عينة من التصنيف (القائمة الكاملة في `config/capability_registry.json`)

| المقياس | المستوى | لماذا |
|---|---|---|
| Risk Score | REAL | `safety_filter.py` + `REJECTED_NICHES.md` حقيقيان |
| Demand (بإشارة حقيقية) | ESTIMATED | معايرة أولى حقيقية، بلا بيانات تحويل مبيعات لتأكيدها بعد |
| Search Trend | DISCOVERY | `n8n Sensing Engine` مبني، يحتاج تفعيلاً فقط (`BLOCKERS.md` #1) |
| Customer Lifetime Value | DISCOVERY | يحتاج عملاء حقيقيين أولاً — صفر عملاء اليوم |
| Market Saturation | DISCOVERY | مختلف عن `competition_score` الموجود — يحتاج حجم سوق حقيقي، لا نتائج بحث Amazon |

## الأثر

- ملف جديد: `config/capability_registry.json` (28 مقياساً مُصنَّفاً بالكامل).
- `lib/dashboard_data.js`: +`readCapabilityMaturity()`.
- `dashboard.html`: بطاقة "نضج القدرات" + قسم "خارطة طريق الاكتشاف" (يسرد كل خطة فتح DISCOVERY حرفياً من السجلّ).
- `tests/test_dashboard_data.js`: +3 اختبارات (23 إجمالاً)، تتحقَّق أن العدّ لا يخترع قدرة غير موجودة في الملف.
- **متى ينتقل مقياس من DISCOVERY→ESTIMATED→REAL:** يُسجَّل بتحديث `capability_registry.json` + ADR جديد يوثِّق الانتقال (نفس ما حدث فعلياً اليوم لـ"Demand": DISCOVERY ضمنياً قبل `ADR-036`، ESTIMATED بعد `ADR-038`).
