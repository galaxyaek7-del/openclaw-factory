# ADR-059 — Multi-Source Market Intelligence: 3 مصادر حقيقية من 10، صفر اختلاق

**التاريخ:** 2026-07-16
**الحالة:** مُنفَّذ ومُختبَر بالكامل (333 اختباراً بايثون + 69 جافاسكريبت، كلها تمر).
**يُنفِّذ:** "Executive Directive – Phase 6: Multi-Source Market Intelligence" — "Success is measured only by increasing verified evidence, reducing UNKNOWN values."

---

## القرار

حزمة `multi_source_intelligence/` — عشرة مُوصِّلات (connectors) مستقلة، واحد لكل مصدر مطلوب، بعقد موحَّد (`source`/`timestamp`/`availability`/`raw_data`/`parsed_data`/`confidence`/`evidence_quality`/`verification_status`). **صفر محرِّك قرار جديد، صفر تعديل على عتبة القبول، صفر ثقة مُختلَقة** — لا هذه الحزمة ولا `aggregator.py`/`coverage.py` يستوردان `orchestrator.orchestrator` أو `decision_engine.engine` (ضُمِن آلياً باختبار بنيوي يقرأ الكود المصدري، لا وعداً نصياً فقط).

```
multi_source_intelligence/
  types.py       — عقد ConnectorResult + SOURCES العشرة
  registry.py      — تسجيل Plugin (نفس نمط market_intelligence_core/orchestrator)
  connectors/
    __init__.py      — اكتشاف تلقائي
    hacker_news.py, github.py, stack_overflow.py    (حقيقية، تعمل فعلياً)
    amazon.py, gumroad.py, etsy.py, product_hunt.py, reddit.py, google_trends.py, public_search.py   (Unknown صادق بسبب حقيقي محدَّد)
  coverage.py       — Evidence Coverage Score (البند 6)
  aggregator.py       — تجميع مستقل، غير مربوط بأي قرار (البند 5، بأمان)
```

## النتيجة الحقيقية: 3 من 10 مصادر تعمل فعلياً اليوم

**تحقَّق مباشرة قبل كتابة أي كود:**
- **Hacker News**: حقيقي منذ `ADR-042` — مُعاد استخدام مباشر لـ`competitor_discovery._query_hn()`.
- **GitHub**: حقيقي منذ `ADR-042` — مُعاد استخدام مباشر لـ`competitor_discovery._query_github()`.
- **Stack Overflow**: **جديد فعلياً** — واجهة Stack Exchange API مجانية وبلا مفتاح، **تحقَّقت الوصولية بطلب حقيقي حي قبل كتابة أي سطر** (نجح، الحصة المتبقية 299/300 يومياً). بيانات حقيقية مُتحقَّق منها: عناوين أسئلة، `view_count`، `answer_count` فعلية.

**7 من 10 مصادر Unknown صادق، كل واحد بسبب حقيقي محدَّد ومُوثَّق سابقاً في هذا المصنع:**
- **Amazon**: يُعيد استخدام `real_market_evidence.evidence_collector` (`ADR-058`) — **صفر استخراج حي من Amazon يُبنى هنا**، يخالف شروط الاستخدام، حد معماري واعٍ لا يُتجاوَز.
- **Gumroad**: يفحص حالة الذراع **الحقيقية** (`channels/registry.py`) لا قيمة ثابتة — `UNAVAILABLE` فعلياً اليوم (لا `GUMROAD_ACCESS_TOKEN`، `BLOCKERS.md` #2). حتى لو توفَّر المفتاح، Gumroad لا يملك واجهة بحث منتجات منافسين علنية أصلاً.
- **Etsy**: نفس الفحص الحقيقي لحالة الذراع — `UNAVAILABLE` (لا بيانات اعتماد Etsy في `.env`)، بالإضافة لغياب أي مُوصِّل بحث سوق مبني حتى لو توفَّرت.
- **Product Hunt، Reddit، Google Trends**: نفس الأسباب الحقيقية الموثَّقة مسبقاً منذ `ADR-042/043` حرفياً (تواصل رسمي مطلوب، بيانات اعتماد غير متوفرة، n8n غير مُفعَّل) — لا سبب جديد مُخترَع.
- **محركات البحث العامة**: لا مفتاح API مدفوع (Google/Bing)؛ بديل مجاني (DuckDuckGo Instant Answer) **رُفِض عمداً** — يُنتج بيانات infobox، لا بيانات سوق ذات معنى؛ استخدامه كان سيكون اختلاقاً بثوب "حقيقي".

## تغطية الأدلة الحقيقية (اختبار فعلي، لا افتراضي)

تشغيل `evidence_coverage_score("gratitude journal daily")` فعلياً: **`checked: 10`، `succeeded: 3` (hacker_news/github/stack_overflow)، `failed: 0`، `unknown: 7`، `coverage_pct: 30.0%`** — بيانات Stack Overflow/HN حقيقية ومُتحقَّق منها ظهرت في النتيجة الفعلية (عناوين أسئلة/منشورات حقيقية).

## العزل — مُختبَر، لا مُفترَض

اختبار مخصَّص (`test_a_connector_raising_an_uncaught_exception_is_tallied_as_failed_not_crashing_the_score`) يجعل مُوصِّلاً واحداً يُطلِق استثناءً غير مُمسوك عمداً، ويؤكِّد أن الـ9 الباقين يُفحَصون بلا انقطاع — البند 4 ("if one source fails, the factory must continue operating normally") مُثبَت، لا موثَّق فقط.

## إعادة التقييم الكامل (كما طُلِب) — نتيجة مطابقة تماماً، والسبب مُثبَت

بما أن `aggregator.py`/`coverage.py` **لا يستوردان** `orchestrator.orchestrator` أو `decision_engine.engine` (مُثبَت بنيوياً)، إعادة تشغيل `real_world_mode.operating_mode.run_real_world_cycle()` على نفس الـ111 إشارة تُنتج **نتائج مطابقة تماماً** لتشغيل `ADR-057` (أعلى درجة 56.9/100، صفر مقبول) — لا تغيير، لأن هذه الطبقة لا تُغذِّي التسجيل إطلاقاً بتصميم. هذا متوقَّع تماماً، ومطابق حرفياً للبند: **"Success is NOT measured by accepting more opportunities."**

## الأثر

- ملفات جديدة: 13 تحت `multi_source_intelligence/` + هذا الـADR.
- `tests/test_multi_source_intelligence.py`: 18 اختباراً جديداً (المجموع الآن 333 بايثون).
- صفر تغيير على `profit_oracle.py`، `decision_engine/`، `orchestrator/`، `market_intelligence_core/`.
