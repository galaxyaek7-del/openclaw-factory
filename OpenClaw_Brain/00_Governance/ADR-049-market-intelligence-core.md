# ADR-049 — Market Intelligence Core: خط أنابيب تسجيل قابل للتوسّع، لا دمج ساذج

**التاريخ:** 2026-07-16
**الحالة:** مُنفَّذ ومُختبَر بالكامل (190 اختباراً بايثون + 69 جافاسكريبت، كلها تمر).
**يُنفِّذ:** توجيه الرئيس "Proceed with engineering cleanup, but do not simply merge duplicate code" — بناء Market Intelligence Core دائم، لا دمج ملفات سطحي.

---

## القرار

بُني `market_intelligence_core/` — حزمة بايثون جديدة، مصدر الحقيقة الوحيد لتقييم أي فرصة سوقية مستقبلاً:

```
market_intelligence_core/
  __init__.py       — فارغ عمداً من الاستيراد (يمنع أي دورة استيراد)
  types.py          — Score (raw_data/normalized_score/confidence/explanation) + EvaluationContext + CONFIDENCE_SCALE الموحَّد
  registry.py       — تسجيل Plugin: register_scorer / register_meta_scorer
  http_client.py     — عميل HTTP الكانوني الوحيد (الازدواجية الحقيقية الوحيدة المؤكَّدة)
  pipeline.py        — يُشغِّل كل مُسجِّل مُكتَشَف تلقائياً، ثم كل meta-scorer
  core.py            — evaluate_opportunity() — نقطة الدخول الدائمة الوحيدة
  scoring/
    __init__.py      — اكتشاف تلقائي (pkgutil) لكل ملف في المجلد
    demand.py، competition.py، profit_margin.py، customer_pain.py،
    pricing_power.py، trend_stability.py، risk.py، execution.py (تاسع، للتوافق)،
    confidence.py (meta)
```

## قرار التصميم الأهم: التفاف (adapter)، لا ترحيل منطق

الطلب كان صريحاً: "لا تدمج الكود المكرَّر ببساطة." الخيار الأول المرفوض: نقل منطق `profit_oracle._score_demand/_score_competition/_score_margin/_score_execution/_score_risk` و`market_intelligence_engine.analyze_customer_pain/classify_demand_pattern/ai_ceo_decision` فعلياً إلى الحزمة الجديدة، وجعل الملفات القديمة أغلفة رقيقة تستدعيها.

**رُفض هذا الخيار بعد تجربته فعلياً** — اكتشاف ملموس أثناء البناء: مجموعة الاختبارات الحالية (`tests/test_opportunity_score.py`) تُراقب حالة الوحدة مباشرة (`po.ECONOMICS = None` تعديل مباشر على متغيّر الوحدة) وتتحقق من سلاسل `reasoning` الدقيقة، ومجموعة أخرى (`tests/test_market_intelligence_engine.py`) تُغلِّف (`@patch`) دوال خاصة بأسماء محدَّدة (`_query_hn_discussions`, `_query_github_issues`, `_http_get_json`) بافتراض أنها لا تزال معرَّفة محلياً في نفس الوحدة. نقل المنطق الفعلي كان سيكسر هذا التغليف بصمت (استدعاء دالة منقولة يستخدم مساحة أسماء الوحدة الجديدة، لا القديمة المُغلَّفة) — وهي بالضبط فئة الخطأ التي هذا المصنع يتجنَّبها (لا تغيير سلوك صامت).

**القرار الفعلي:** كل منطق التسجيل الحقيقي **يبقى بلا أي تغيير** في `profit_oracle.py`/`market_intelligence_engine.py` — لا سطر منطق واحد نُقِل أو أُعيد كتابته. كل من الوحدات التسع الجديدة تحت `scoring/` هي **مُلتفّة (adapter)** تستدعي الدالة الأصلية غير المُعدَّلة وتُعيد تغليف ناتجها في عقد `Score` الموحَّد. هذا يعني:
- **صفر خطر انحراف سلوكي** — لا يوجد "منطقان يجب أن يتطابقا"، يوجد منطق واحد فقط، يُستدعى من مكانين.
- **مجموعة الاختبارات الحالية (178 اختباراً) أصبحت هي اختبارات التوصيف (characterization tests) المطلوبة في الشرط #6** — لأن لا شيء تحرَّك، فلا حاجة لإثبات "نفس المخرجات" بشكل منفصل؛ التطابق مضمون بنائياً.
- **لا دورة استيراد:** `market_intelligence_core.core` يستورد `market_intelligence_engine`/`competitor_discovery`/`profit_oracle` (اتجاه واحد فقط)؛ الملفات القديمة لا تستورد شيئاً من `market_intelligence_core` سوى `http_client` (ورقة، صفر اعتماد عكسي).

## الازدواجية الحقيقية الوحيدة المؤكَّدة — وما لم يُدمَج عمداً

مراجعة `ARCHITECTURE_REVIEW_2026-07-16.md` (`ADR-048`) وجدت تكراراً حرفياً واحداً فقط: دالة `_http_get_json` (نفس urllib، يختلف فقط User-Agent) في كل من `market_intelligence_engine.py` و`competitor_discovery.py`. هذا وحده وُحِّد في `market_intelligence_core/http_client.py`. دوال البحث الأعلى مستوى (`_query_hn`/`_query_github` مقابل `_query_github_issues`/`_query_hn_discussions`) **لم تُدمَج** — تستعلم نقاط نهاية مختلفة لأغراض مختلفة (اكتشاف منافسين مقابل تحليل ألم العملاء)؛ دمجها في دالة عامة واحدة كان سيُخفي دلالات مختلفة فعلياً مقابل عدد أسطر أقل — بالضبط المقايضة التي يرفضها `CLAUDE.md` ("لا تُضحِّ بالصحة مقابل عدد ملفات أقل"، الشرط #9 صراحة).

كل من `_http_get_json` القديمتين أصبحت جسماً من سطر واحد يُفوِّض لـ`http_client.http_get_json()` **دون تغيير الاسم المحلي** — بحيث تبقى `@patch("competitor_discovery._http_get_json")`/`@patch("market_intelligence_engine._http_get_json")` الحاليتان تعملان بلا أي تعديل، لأن الدالتين المُستدعيتين (`_query_hn`, `_query_github_issues`، إلخ) لا تزالان تستدعيان الاسم المحلي غير المُعدَّل. تحقَّق ذلك عملياً: **صفر اختبار احتاج تعديلاً.**

## الأبعاد الثمانية + التاسع

| البُعد | المصدر الحقيقي المُلتَف | الحالة |
|---|---|---|
| Demand | `profit_oracle._score_demand()` (ADR-038) | REAL/ESTIMATED حسب توفر `external_signal` |
| Competition | `profit_oracle._score_competition()` + إثراء حقيقي من `competitor_discovery` (ADR-042) | REAL عند وجود منافسين حقيقيين مكتشَفين |
| Profit Margin | `profit_oracle._score_margin()` (ADR-041) | REAL (رسوم + تكلفة Groq حقيقية) عند توفرها |
| Customer Pain | `market_intelligence_engine.analyze_customer_pain()` (ADR-043) | REAL (GitHub Issues + HN)، أو None صريح بلا دليل |
| Pricing Power | **جديد** — تقرير Amazon محفوظ حقيقي عبر `profit_oracle._find_niche_report()`، وإلا DISCOVERY | لا استخلاص أسعار حي (ADR-046: 25% موثوقية فقط) |
| Trend Stability | `market_intelligence_engine.classify_demand_pattern()` (ADR-043) | Seasonal=REAL، Evergreen=DISCOVERY صريح (`normalized_score=None`) |
| Risk | `profit_oracle._score_risk()` (ADR-039) | REAL (safety_filter.py + REJECTED_NICHES.md) |
| Confidence | **meta-scorer جديد** — متوسط ثقة كل الأبعاد الأخرى تلقائياً | يُعمِّم إصلاح تدقيق 2026-07-15 (`PAIN_CONFIDENCE_SCALE`) في مكان واحد دائم |
| Execution (تاسع، إضافي) | `profit_oracle._score_execution()` | يحافظ على تركيبة `profit_score` الحالية (وزن 10%)، ويُثبِت التوسّع عملياً لا نظرياً |

## إثبات شرط التوسّع (رقم 4) عملياً، لا نظرياً

`scoring/__init__.py` يستخدم `pkgutil.iter_modules` لاستيراد كل ملف في المجلد تلقائياً عند الاستيراد — إضافة بُعد تسجيل عاشر تعني: **ملف جديد واحد، لا تعديل على أي ملف موجود.** `tests/test_market_intelligence_core.py::test_adding_a_new_scorer_at_runtime_requires_zero_pipeline_edits` يُسجِّل مُسجِّلاً وهمياً وقت التشغيل (يُحاكي إسقاط ملف عاشر) ويؤكد أن `pipeline.run()` يلتقطه بلا أي تعديل على `pipeline.py`.

## ماذا لم يُلمَس، ولماذا (نطاق مقصود)

- **`profit_oracle.py`:** صفر تغيير. يبقى المسار المتزامن السريع الخالي من الشبكة (القاعدة القائمة من `ADR-041/042/043`) — يُستدعى مباشرة من `book_generator.py`/`inspectors.py`/`factory_loop.js` بلا أي وسيط جديد.
- **`market_analyzer.py`:** خارج النطاق عمداً — ليس "مسجِّل نيتش مكرَّر" بالمعنى المطلوب توحيده؛ هو أداة عرض لوحة تحكم على جدول ثابت من 10 أمثلة، بلا مدخل نيتش أصلاً (توثَّق ذاتياً في تعليقه الخاص كأداة مختلفة الغرض عمداً غير مُدمَجة). إجباره على نفس الأنبوب كان سيُقدِّم بيانات لوحة تحكم كأنها تقييم نيتش حقيقي — تضليل، لا تبسيط.
- **`niche_validator_v2.py`:** أداة تحقق يدوية أوفلاين مستقلة (HTML محفوظ من Amazon) — تبقى مصدر بيانات (عبر `_find_niche_report`) لا "مسجِّلاً" يُلَف بذاته.
- **`market_intelligence_core.evaluate_opportunity()`:** لا يُستدعى من أي مسار حي حالياً (لا `server.js`، لا `factory_loop.js`) — الاستدعاء المباشر لـ`market_intelligence_engine.analyze_opportunity()` (الذي لم يتغيَّر) يبقى نقطة الدخول الحالية لكل مستدعٍ حي؛ الـCore جاهز كنقطة الدخول *المستقبلية* الموصى بها دون فرضها بأثر رجعي.

## الأثر

- ملفات جديدة: 15 ملفاً تحت `market_intelligence_core/` (بما فيها `scoring/`).
- `competitor_discovery.py`/`market_intelligence_engine.py`: سطر استيراد واحد + جسم `_http_get_json` مُستبدَل بتفويض سطر واحد كل منهما — لا شيء آخر تغيَّر.
- `tests/test_market_intelligence_core.py`: 12 اختباراً جديداً (المجموع الآن 190 بايثون).
- **صفر اختبار قديم احتاج تعديلاً.**
