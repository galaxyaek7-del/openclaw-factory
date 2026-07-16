# ADR-051 — Executive Orchestrator (Factory OS): المُنسِّق الوحيد للشركة

**التاريخ:** 2026-07-16
**الحالة:** مُنفَّذ ومُختبَر بالكامل (232 اختباراً بايثون + 69 جافاسكريبت، كلها تمر).
**يُنفِّذ:** توجيه الرئيس المباشر — "This is not another feature. This is the operating system of the autonomous company."

---

## تحديث حاكم: تجاوز صريح موثَّق لتجميد `ADR-034`، لا نقض صامت

بناء منسّق تشغيلي واحد لكل الشركة هو بالضبط فئة العمل التي جمَّدها `ADR-034` §3 خلف محفِّز موضوعي واحد (بيع حقيقي / مفتاح API حي / مرشَّح Tier-1 حقيقي) — **لم يتحقق أي منها بعد.** هذا التوتر أُثير صراحة مرة واحدة بالفعل في `ADR-048` (تقرير المراجعة المعمارية، 2026-07-16 سابقاً اليوم)، حيث طُرِح سؤال مباشر على الرئيس: "هل تريد تجاوزاً صريحاً الآن، أم الانتظار حتى محفِّز موضوعي؟"

الرئيس أجاب بتوجيه تفصيلي كامل يبني بالضبط هذا النظام، مُصرِّحاً بوعي: *"This is not another feature. This is the operating system of the autonomous company."* هذا **يُسجَّل هنا كتجاوز صريح موثَّق**، بنفس نمط `ADR-034` نفسه في تحديثه الخاص بتاريخ 2026-07-15 ("تجاوز صريح من الرئيس") — لا اعتراض يُكرَّر بعد إثارته مرة وسماعه (نفس مبدأ "الاعتراض المحمي" المُتَّبع طوال هذه الجلسة).

**ما لا يتغيَّر رغم التجاوز:** الانضباط نفسه — كل جزء من هذا النظام يُعيد استخدام محرّكات حقيقية موجودة فعلاً (`market_intelligence_core`، `decision_engine`، `book_generator.py`، `distributor.py`)، صفر بيانات مُختلَقة، صفر "ذكاء اصطناعي وهمي"، وأمان `dry_run=True` افتراضي عند أي أثر جانبي حقيقي (بالضبط كما طلب الرئيس نفسه في التوجيهات السابقة لهذه الجلسة).

---

## القرار: حزمة `orchestrator/` جديدة، منفصلة تماماً

```
orchestrator/
  types.py       — ExecutionResult + EXECUTION_ORDER (بيانات، لا بنية كود ضمنية) + DUPLICATE_SENSITIVE_STAGES
  registry.py     — تسجيل Plugin لكل محرّك (نفس نمط market_intelligence_core/decision_engine)
  timeline.py      — سجل تنفيذ إلحاقي غير قابل للتغيير (data/orchestrator_timeline.jsonl)
  retry.py          — إعادة محاولة حقيقية عند فشل عابر
  engines/
    __init__.py      — اكتشاف تلقائي (pkgutil)
    market_intelligence.py، decision.py، production.py، publishing.py، learning.py
  orchestrator.py    — run_cycle() + prioritize_queue()
```

**كل محرّك أداة/ملتفّة (adapter) رقيقة** — الحقيقة الحسابية تبقى بالكامل في `market_intelligence_core`/`decision_engine`/`book_generator.py`/`distributor.py`، بلا تغيير (باستثناء إضافة صغيرة إضافية واحدة موثَّقة أدناه). هذا يُطبِّق مبدأ عكس التبعية (dependency inversion) حرفياً: `orchestrator.py` لا يستورد أي محرّك مباشرة، فقط الواجهة المجرَّدة `run(context) -> dict` عبر السجلّ.

## إضافة صغيرة واحدة مبرَّرة إلى `decision_engine` (لا "استمرار تلميع")

`decision_engine.engine.evaluate_and_decide()` كانت تُعيد تشغيل `evaluate_opportunity()` بالكامل داخلياً حتى لو كان المنسّق قد شغَّلها للتو لنفس النيتش في نفس الدورة — استدعاء شبكة حي مكرَّر حقيقي وحقيقي التكلفة (بلا فائدة). أُضيف معامل اختياري واحد `precomputed_analysis=None` — أي مستدعٍ حالي بلا هذا المعامل يحصل على **نفس السلوك تماماً بلا تغيير** (تحقَّق بتشغيل كل اختبارات `decision_engine`/`market_intelligence_core` الموجودة، 56 اختباراً، كلها تمر بلا تعديل). هذا تكامل ضروري حقيقي لهذا النظام الجديد، لا تحسيناً غير مطلوب.

## ترتيب التنفيذ كبيانات، لا بنية كود ضمنية

`EXECUTION_ORDER = ("market_intelligence", "decision", "production", "publishing", "learning")` — صراحة قابلة للفحص، تُطبِّق حرفياً شرط "الأورو كسترا تُدير ترتيب التنفيذ."

## منع الازدواجية — نطاق مقصود، لا شامل

**نطاق منع التنفيذ المكرَّر يقتصر على `production`/`publishing` فقط** (`DUPLICATE_SENSITIVE_STAGES`) — الأثر الجانبي الحقيقي المكلف/غير القابل للتراجع الوحيد. `market_intelligence`/`decision`/`learning` **تُعاد دائماً** عند إعادة الاستدعاء — لأن هذا المصنع يملك بالفعل آلياته الخاصة لإعادة التقييم (نافذة تحديث `competitor_discovery.py`، سجل القرارات الإلحاقي في `decision_engine`) — منع إعادة تشغيلها بعد نجاح واحد إلى الأبد كان سيجعل النظام عاجزاً عن إعادة تقييم أي نيتش مجدداً، وهو خطأ واضح. أُثبِت هذا التمييز باختبار مباشر (`test_market_intelligence_and_decision_never_skip_as_duplicate_on_rerun`).

## أمان `execute_production=False` الافتراضي

`run_cycle()` الافتراضي **لا ينفِّذ الإنتاج أو النشر إطلاقاً** — بالضبط نفس اتفاقية `distributor.py`'s `dry_run=True` الافتراضية المُطبَّقة أصلاً في كل مكان له أثر حقيقي. محرّك `production.py` (يستدعي `book_generator.py` عبر subprocess، نفس بروتوكول CLI الموثَّق فعلاً في `CLAUDE.md`) لا يُشغِّل subprocess حقيقياً أبداً ما لم يُمرَّر `execute_production=True` صراحةً — **لم يُشغَّل هذا الوضع في هذه الجلسة إطلاقاً**، لا إنفاق Groq حقيقي حدث.

## التعافي (Recovery) — نتيجة طبيعية للسجل الدائم، لا كود إضافي

`timeline.has_succeeded()` يقرأ السجل الإلحاقي الكامل من القرص — منسّق مُعاد تشغيله بعد توقف/عطل يعرف تلقائياً ماذا نجح فعلاً دون الحاجة لحالة ذاكرة مؤقتة، لأن نفس آلية "منع التكرار" هي بالضبط آلية "التعافي."

## التوازي المستقبلي — الجاهزية دون البناء الفعلي

كل مرحلة دالة نقية `context -> result`، بلا حالة مشتركة متبدِّلة (الإلحاق للسجل آمن حتى مع كتابات متزامنة). هذا يعني: مُنفِّذ متزامن مستقبلي (asyncio/ThreadPoolExecutor) يُشغِّل دورات نيتشات مختلفة بالتوازي هو تغيير إضافي بسيط، لا إعادة تصميم — **لم يُبنَ فعلياً** لأن لا حِمل حقيقي متزامن يبرِّره اليوم (نفس انضباط "لا تصمِّم لمتطلبات مستقبلية افتراضية" المُتَّبع طوال هذه الجلسة).

## ثغرة عزل اختبارات حقيقية اكتُشِفت وأُصلِحت أثناء البناء

بناء `test_orchestrator.py` كشف مشكلة حقيقية أعمق من نطاق هذه الجلسة فقط: `competitor_discovery.get_or_refresh_competitors()` يكتب دائماً إلى `data/competitor_database.json` الحقيقي عبر ثابت وحدة (`COMPETITOR_DB_FILE`) — حتى عندما يكون استعلام الشبكة نفسه مُموَّهاً (mocked) في الاختبار. **تأكَّد فعلياً** بإيجاد نصوص نيتشات هذه الاختبارات نفسها داخل الملف الحقيقي — بما فيها اختبارات `test_market_intelligence_engine.py`/`test_market_intelligence_core.py` الموجودة مسبقاً من قبل هذه الجلسة (`ADR-043`/`ADR-049`)، لا فقط اختبارات اليوم. كذلك `orchestrator.run_cycle()` نفسه لم يكن يُمرِّر أي مسار بديل لـ`decisions.jsonl`/`market_intelligence_analyses.jsonl` — عيب تصميم حقيقي، لا مجرد نظافة اختبار.

**الإصلاح:**
1. `orchestrator.run_cycle()` أصبح يقبل `decisions_path`/`analysis_db_file`/`outcomes_path` صراحة، يُمرَّرها عبر `context` لكل محرّك.
2. اختبارات `test_orchestrator.py`/`test_decision_engine.py`/`test_market_intelligence_core.py`/`test_market_intelligence_engine.py` المتأثرة تُموِّه (`patch`) ثابت `competitor_discovery.COMPETITOR_DB_FILE` مباشرة لكل حالة اختبار تصل لهذا المسار.
3. **تنظيف فعلي للملفات الحقيقية الملوَّثة سابقاً:** `data/competitor_database.json` نُظِّف من 12 نيتشاً اختبارياً مُختلَقاً (أُبقيَ فقط على 3 نيتشات حقيقية من بحث Golden Hunter السابق لهذه الجلسة)، `data/market_intelligence_analyses.jsonl` نُظِّف من 14 سطراً اختبارياً، `data/decisions.jsonl` (كان بأكمله اختبارياً) حُذِف بالكامل.
4. **تحقُّق:** تشغيل كامل مجموعة الاختبارات (232) مرتين متتاليتين مع مقارنة hash MD5 لكلا الملفَّين قبل وبعد — **متطابق تماماً بت لبت**، يثبت أن الإصلاح يمنع التلوث فعلياً، لا مجرد تنظيف لمرة واحدة.

## ماذا لم يُلمَس

- `market_intelligence_core/` — صفر تغيير (كما طُلِب صراحة).
- `server.js`، `factory_loop.js` — صفر ربط تلقائي. نفس اتفاقية "أداة مستقلة تُشغَّل عمداً" المُتَّبعة لكل أداة جديدة هذه الجلسة، ومباشرة طبقاً لتعليمات الرئيس: "Do not wire the Opportunity Decision Engine directly into factory_loop.js."
- `book_generator.py`، `distributor.py` — صفر تغيير، فقط استدعاء عبر الواجهات الموجودة أصلاً.

## الأثر

- ملفات جديدة: 10 تحت `orchestrator/` (بما فيها `engines/`) + هذا الـADR.
- `decision_engine/engine.py`: معامل اختياري واحد جديد (`precomputed_analysis`)، صفر تغيير سلوكي على أي مستدعٍ حالي.
- `tests/test_orchestrator.py`: 17 اختباراً جديداً (المجموع الآن 232 بايثون).
- بيانات جديدة عند أول استخدام حقيقي: `data/orchestrator_timeline.jsonl` (غير موجود بعد — لم يُشغَّل المنسّق على بيانات حقيقية بعد هذه الجلسة).
