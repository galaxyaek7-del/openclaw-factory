# ADR-050 — Opportunity Decision Engine: العقل القراري الدائم لـOpenClaw

**التاريخ:** 2026-07-16
**الحالة:** مُنفَّذ ومُختبَر بالكامل (215 اختباراً بايثون + 69 جافاسكريبت، كلها تمر).
**يُنفِّذ:** توجيه الرئيس — "The scorer is now only one component inside a larger autonomous decision system. Build the Opportunity Decision Engine."

---

## القرار

بُنيت حزمة `decision_engine/` جديدة ومنفصلة تماماً عن `market_intelligence_core/` (لم تُلمَس الأخيرة إطلاقاً، طبقاً للتوجيه الصريح "do not continue polishing"). الحلقة الكاملة:

```
Signal → Evaluation → Decision → Execution → Feedback → Learning
  نيتش    evaluate_       engine.        book_generator.py/   feedback.py     learning.py
  مُقترَح  opportunity()    evaluate_       distributor.py       (مبيعات حقيقية)  (دقة + معايرة حقيقية)
           (بلا تغيير)      and_decide()    (خارج النطاق، لم يُمَس)
```

```
decision_engine/
  types.py       — Decision / Outcome + make_decision_id() الحتمي
  store.py        — JSONL إلحاقي فقط (data/decisions.jsonl، data/decision_outcomes.jsonl) — لا كتابة فوق التاريخ أبداً
  engine.py        — evaluate_and_decide(): يستهلك evaluate_opportunity() + profit_oracle.opportunity_score()
  ranking.py        — rank_all() (كل الفرص) + rank_queue() (طابور القرار الفعلي: ACCEPTED بلا نتيجة مبيعات بعد)
  feedback.py        — يقرأ data/sales_ledger.jsonl الحقيقي، يُطابق مبيعات حقيقية بقرارات، بصدق
  learning.py         — دقة تنبؤ حقيقية + تقرير إعادة معايرة حقيقي، لا محاكاة
```

## القرار المعماري: بوابتان مستقلتان يجب أن تتفقا، لا بوابة واحدة تُقرِّر

`evaluate_and_decide()` لا يُعيد اختراع القرار — يستهلك بوابتين حقيقيتين موجودتين مسبقاً ومُختبَرتين:
1. **AI CEO** (`market_intelligence_core.evaluate_opportunity()`'s `ai_ceo.decision`: BUILD/IMPROVE/WAIT/REJECT/PIVOT) — قائم على أدلة حقيقية (ألم عملاء، فجوة فرصة، مخاطرة).
2. **Opportunity Score** (`profit_oracle.opportunity_score()`, `ADR-026`) — المقياس المركّب الموزون حسب الطبقة، وعتبته `MIN_OPPORTUNITY_SCORE`.

**القبول (`ACCEPTED`) يتطلب اتفاق الاثنين معاً.** عند تعارضهما (AI CEO يوصي بالبناء لكن Opportunity Score دون العتبة) القرار `DEFERRED` صراحةً — لا حسم أحادي الجانب. هذا يمنع فئة خطأ محتملة: بوابة واحدة "متساهلة" تُمرِّر فرصة ضعيفة الأدلة فعلياً.

`opportunity_score()` تُحسَب مباشرة (استدعاء إضافي رخيص ومتزامن) لأن `analyze_opportunity()`'s الحالي يحسبها داخلياً لكن لا يُعيدها في القاموس المُرجَع (يحتفظ فقط بالمكوّنات) — استدعاؤها مرة أخرى هنا أرخص وأصح من إعادة اشتقاق صيغتها، وأيضاً **لا يتطلب أي تعديل على `market_intelligence_core`**، محافظاً على توجيه "لا تُواصل تحسين المُسجِّل."

## القابلية للاستنساخ (Reproducibility) — تُفهَم حرفياً، لا مجازاً

بما أن `evaluate_opportunity()` يستدعي شبكات حقيقية (HN/GitHub)، إعادة التشغيل الفعلي لا يضمن نفس النتيجة حرفياً بمرور الوقت (الشبكة تتغيَّر). **"قابل للاستنساخ" هنا يعني: كل قرار يحمل معه اللقطة الكاملة للأدلة التي أنتجته** (`evaluation_snapshot` — كامل مخرج `evaluate_opportunity()` بما فيه كل `dimension_scores`) — لا حاجة لإعادة أي شيء لفهم *لماذا* اتُّخِذ القرار؛ كل الدليل محفوظ حرفياً، إلى الأبد، في نفس السجل. `decision_id` نفسه حتمي (`sha256(niche|tier|analyzed_at)`) — نفس المدخلات تُنتج نفس المعرِّف دائماً.

## سجل إلحاقي فقط — لا كتابة فوق التاريخ أبداً

`store.py` يتبع نفس انضباط `channels/ledger.py` الموجود (سطر JSON واحد لكل حدث، إلحاق فقط). قرار مرفوض اليوم لنيتش قد يُعاد تقييمه لاحقاً — **كل سجلاته التاريخية تبقى، `find_decisions_by_niche()` تُعيدها جميعاً**، لا آخر واحد فقط. "كل فرصة مرفوضة تبقى قابلة للبحث" مضمونة بنائياً، لا بميزة إضافية.

## التغذية الراجعة (Feedback) — مطابقة واقعية، لا افتراضية

`feedback.py` يقرأ `data/sales_ledger.jsonl` الحقيقي (نفس الملف الذي يكتبه `scripts/poll_sales.py` من `get_sales()` الحي). **حالة اليوم الحقيقية (تحقَّق منها مباشرة، 2026-07-16): 23 سطراً، كلها `publish_attempt` من اختبارات دخان — صفر حدث `sale` حقيقي واحد** (لا مفتاح Gumroad حي بعد، `BLOCKERS.md` #2). هذا متوقَّع وصادق، ليس خللاً.

المطابقة (بيع حقيقي ← قرار) بالضرورة اجتهادية: عنوان الكتاب المُولَّد بواسطة Groq ليس بالضرورة نص النيتش حرفياً. لذا: مطابقة عبر `product_id` الحقيقي (بيع ← محاولة نشر) ثم بحث نص النيتش داخل عنوان المنتج الفعلي المُسجَّل. **عند فشل المطابقة، البيع يُسجَّل صراحةً كـ"غير مُطابَق" — لا يُسقَط أبداً بصمت، ولا يُخمَّن قرار له.**

## التعلّم (Learning) — إحصاء حقيقي، لا ذكاء اصطناعي وهمي

- `compute_prediction_accuracy()`: نسبة نجاح حقيقية بين قرارات `ACCEPTED` ذات نتيجة مبيعات حقيقية مطابقة. **بصفر قرارات/نتائج، تُعيد `accuracy: None` مع سبب صريح — لا رقم مُختلَق.**
- `recalibration_report()`: الفرق الحقيقي بين متوسط `normalized_score` لكل بُعد تسجيل بين النيتشات المقبولة التي بيعت فعلياً مقابل التي لم تُبَع بعد. **يتطلب 3 عينات حقيقية مطابَقة على الأقل** قبل إنتاج أي تقرير (`MIN_SAMPLES_FOR_RECALIBRATION`) — دون ذلك: `recalibrated: False` وسبب صريح. **هذا تقرير قرار بشري، لا يُعدِّل تلقائياً منطق `market_intelligence_core` الحي** — تطبيقه فعلياً على التسجيل الحي قرار منفصل يحتاج بيانات حقيقية كافية أولاً لتبريره (نفس انضباط `ADR-034` المُشترَط بمحفِّزات موضوعية).

## ماذا لم يُبنَ عمداً، ولماذا

- **لا ربط تلقائي بـ`server.js`/`factory_loop.js`.** نفس اتفاقية الأدوات المستقلة القائمة (`market_hunter.py`/`competitor_discovery.py`/`market_intelligence_engine.py`): يُشغَّل عمداً، لا يدخل الحلقة الحية التلقائية بلا خطوة موافقة منفصلة.
- **لا "دقة تنبؤ" بمعنى حقيقي حتى تتراكم بيانات حقيقية.** الحالة الحالية (صفر مبيعات) صادقة تماماً — أي رقم آخر كان سيكون اختلاقاً.
- **لا إعادة معايرة تلقائية للتسجيل الحي.** التقرير حقيقي ومُختبَر؛ تطبيقه قرار لاحق منفصل.

## الأثر

- ملفات جديدة: 6 تحت `decision_engine/` + هذا الـADR.
- `tests/test_decision_engine.py`: 25 اختباراً جديداً (المجموع الآن 215 بايثون).
- صفر تغيير على `market_intelligence_core/`، `profit_oracle.py`، `server.js`، `factory_loop.js`.
- بيانات جديدة عند أول استخدام حقيقي: `data/decisions.jsonl`، `data/decision_outcomes.jsonl` (لا شيء منهما موجود بعد — لم يُشغَّل المحرك على بيانات حقيقية بعد هذه الجلسة).
