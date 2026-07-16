# Architecture Review Report — Phase 0 Foundation

**التاريخ:** 2026-07-16
**الحالة:** تحليل فقط — صفر تغيير كود. بانتظار موافقة الرئيس قبل أي بناء/ترحيل.
**يُنفِّذ:** "Executive Architecture Directive — Phase 0 Foundation."

---

## 0. العلاقة بـ`ADR-034` (اعتراض مُسجَّل مرة، لا يُكرَّر)

بناء "Company Operating System" رسمي كطبقة تنسيق مركزية يقع تماماً ضمن ما جمّده `ADR-034` (بيع حقيقي / مفتاح API حي / مرشَّح Tier-1 — لم يتحقق أي منها بعد). هذا مُسجَّل هنا مرة فقط. هذا التقرير نفسه تحليل بحت (صفر كود جديد)، فهو لا يخالف التجميد بأي حال. **القرار بشأن بناء COS فعلياً كخطوة تالية متروك للرئيس صراحة في §5 — لن أبدأ بناءه دون تأكيد.**

---

## 1. الملخص التنفيذي

- **البنية الفعلية اليوم متماسكة أكثر مما تبدو:** لا فوضى، لكن لا يوجد منسّق مركزي واحد — `server.js` يُشغِّل 8 مسارات تستدعي subprocesses بايثون بشكل مستقل كل واحد عن الآخر، و`factory_loop.js` يعمل بحلقة منفصلة تماماً بمنطقه الخاص. **بناء COS حقيقي = بناء جديد، لا إعادة تسمية.**
- **تكرار حقيقي مؤكَّد (لا افتراض):** `market_intelligence_engine.py` و`competitor_discovery.py` يحويان دالتَي `_http_get_json` شبه متطابقتين حرفياً — رغم أن الأول يستورد الثاني أصلاً في القمة (`market_intelligence_engine.py:76-77`)، فالتكرار غير ضروري بنيوياً.
- **3 مسجِّلات نيتش مستقلة** (`market_analyzer.py` الثابت، `profit_oracle.py` الحقيقي/المُنتِج، `niche_validator_v2.py` القائم على HTML KDP) — الأول موثَّق ذاتياً في تعليقه الخاص كـ"غير مُدمَج، تغيير أكبر وأخطر". هذا دَين تقني معروف مسبقاً، لا اكتشاف جديد.
- **صفر ثغرة أمنية جديدة** غير ما هو موثَّق أصلاً في `CLAUDE.md` (`POST /chat` بلا مصادقة).
- **عنق زجاجة حقيقي للتوسّع:** ملفات JSON مسطَّحة تُعاد كتابتها كاملة كل تحديث (`golden_opportunities.json` 207KB، `GOLDEN_OPPORTUNITIES.md` 152KB) بلا تدوير؛ كل مسار يُشغِّل subprocess بايثون متزامناً بلا طابور — غير حرج عند صفر تزامن اليوم، لكنه عنق حقيقي فور وجود طلبات متزامنة.

---

## 2. الجرد الحالي (حسب فئات التوجيه المطلوبة)

### المنصة الأساسية (Core platform)
`server.js` (Express، 24 مساراً) + `factory_loop.js` (حلقة يدوية بلا scheduler). **هذان معاً يشكّلان "منصة" فعلياً غير مُنسَّقة رسمياً — لا COS يجمعهما.**

### الخدمات المشتركة (Shared services)
`economics.py` (اقتصاديات الوحدة، يُستورَد من profit_oracle/inspectors/schemas.product)، `safety_filter.py` (بوابة أمان النيتش)، `channels/base_arm.py` + `channels/registry.py` + `channels/ledger.py` (واجهة الأذرع + التوزيع + سجل التدقيق — معزولة جيداً)، `schemas/product.py`، `lib/dashboard_data.js` (تجميع قراءات ملفات بحت)، `knowledge_brain.js` (أداة بحث عبر Brain، مُستخدَمة من مسار `/brain`).

### الوحدات التجارية (Business modules)
`book_generator.py`, `cover_designer_v2.py`, `hive_logbook_generator.py` (standalone صراحة), `seed_english_book.py` (standalone), `audit_seed.py` (standalone، "صفر أثر على المصنع" بتعليقه الخاص), `quality_doctor.py`, `distributor.py`, `channels/{etsy,gumroad,payhip}_arm.py` + `_publisher.py` المرافقة.

### وحدات الذكاء الاصطناعي (AI modules)
`market_intelligence_engine.py`, `competitor_discovery.py`, `profit_oracle.py`, `market_hunter.py`, `niche_validator_v2.py`, `self_awareness.js`, `reality.py`, `market_analyzer.py` (بتحفظ — انظر الدَين التقني أدناه).

### البنية التحتية (Infrastructure)
Express server نفسه (لا build step، لا CI)، `n8n_workflows/` (5 workflows، 2 مُصلَحان حياً)، `venv/`/`node_modules/`، ملفات `.log`/`.jsonl` كحالة تشغيل مسطَّحة، `start_factory.bat`. لا نشر (deployment) موجود إطلاقاً — كل شيء محلي بتصميم واعٍ (`CLAUDE.md` §IDENTITY_ARCHITECTURE).

### الدَين التقني / التكرار / الترابط المُحكَم (Technical debt / Duplicate logic / Tight coupling)
1. **تكرار HTTP-wrapper مؤكَّد:** `market_intelligence_engine.py:99` (`_http_get_json`) يكاد يطابق `competitor_discovery.py:62` (`_http_get_json`) حرفياً — نفس التوقيع، نفس نمط urllib، يختلفان فقط بـUser-Agent. `market_intelligence_engine.py:109-127` (`_query_github_issues`/`_query_hn_discussions`) يُعيد تنفيذ نفس نمط "فشل صامت → قائمة فارغة" الموجود أصلاً في `competitor_discovery.py:71-92`.
2. **3 مسجِّلات نيتش مستقلة** — موثَّقة ذاتياً في `market_analyzer.py:6-19` كمشكلة معروفة غير مُدمَجة عمداً (خطر دمج أكبر مما يستحق حالياً).
3. **لا منسّق مركزي:** `server.js` يُشغِّل subprocesses بايثون من 8 مواقع مستقلة (الأسطر 60، 167، 266، 393، 826، 1044، 1153، 1296)، و`factory_loop.js` يملك نسخته المنفصلة تماماً من منطق القرار. بناء COS هنا بناء جديد فعلي.

### التجريدات المفقودة (Missing abstractions)
- لا وحدة HTTP-fetch مشتركة واحدة (البند 1 أعلاه).
- لا مُوزِّع (dispatcher) واحد يستقبل كل الطلبات ويوجّهها — كل مسار في `server.js` يعرف تفاصيل تشغيل subprocess بنفسه.
- لا طابور عمل (job queue) بين HTTP request وتشغيل Python subprocess.

### المخاطر الأمنية (Security risks)
لا جديد يتجاوز ما وثَّقه `CLAUDE.md` مسبقاً: `POST /chat` (`server.js:424`) يبقى ممراً خاماً بلا مصادقة لـGroq، صفر مستدعين مؤكَّدين. لا مسار آخر غير مُصادَق ومباشر عُثِر عليه.

### عنق الزجاجة للتوسّع (Scalability bottlenecks)
`golden_opportunities.json` (207KB) و`GOLDEN_OPPORTUNITIES.md` (152KB) تُعاد كتابتهما كاملةً عند كل تحديث، بلا تدوير أو حد أقصى. كل مسار توليد/توزيع/استطلاع يُشغِّل subprocess بايثون متزامناً — لا مشكلة عند صفر تزامن اليوم، لكنه عنق حقيقي فور وجود طلبات متزامنة.

---

## 3. الخريطة المقترحة للطبقات السبع

كل وحدة تُخصَّص لطبقة واحدة فقط، حتى الغامضة — القرار موثَّق صراحة، لا تُترَك بلا تصنيف.

| الطبقة | الوحدات | ملاحظة |
|---|---|---|
| **1. Company Constitution** | `CONSTITUTION.md`, `OPENCLAW_OS_CONSTITUTION.md`, `OCTOPUS_ARCHITECTURE.md`, `OpenClaw_Brain/00_Constitution/`, `OpenClaw_Brain/00_Governance/` (كل الـADRs) | وثائق فقط، لا كود — تطابق واضح، صفر غموض. |
| **2. Company Operating System** | *(لا شيء يملك هذا الدور فعلياً اليوم)* | `server.js`+`factory_loop.js` منسّقان بحكم الأمر الواقع فقط، غير رسمي وغير مُوحَّد — هذه الطبقة تحتاج بناءً جديداً، ليست إعادة تصنيف. |
| **3. Shared Services** | `economics.py`, `safety_filter.py`, `channels/base_arm.py`, `channels/registry.py`, `channels/ledger.py`, `schemas/product.py`, `lib/dashboard_data.js`, `knowledge_brain.js` | `lib/dashboard_data.js` غامض بين Shared وGrowth — يُصنَّف Shared لأنه تجميع قراءات بحت يخدم المراقبة، لا التسويق. |
| **4. Intelligence Layer** | `market_intelligence_engine.py`, `competitor_discovery.py`, `profit_oracle.py`, `market_hunter.py`, `niche_validator_v2.py`, `self_awareness.js`, `reality.py`, `market_analyzer.py` | `reality.py` يُصنَّف هنا (لا Shared) ليتّسق مع `self_awareness.js` — كلاهما ينتج إشارات "مدى واقعية/نضج" الأعمال، لا أداة عامة. `market_analyzer.py` يُصنَّف هنا **مع تحذير صريح**: دَين تقني معروف (مسجِّل نيتش ثالث غير مُدمَج)، وضعه في الطبقة لا يعني حل التكرار — التوحيد قرار منفصل. |
| **5. Execution Layer** | `factory_loop.js`, `distributor.py`, `inspectors.py`, `scripts/poll_sales.py`, `scripts/process_approved_drafts.py`, `scripts/readiness_certificate.py` | |
| **6. Product Layer** | `book_generator.py`, `cover_designer_v2.py`, `hive_logbook_generator.py`, `seed_english_book.py`, `audit_seed.py`, `quality_doctor.py` | |
| **7. Growth Layer** | `channels/etsy_arm.py`, `channels/etsy_publisher.py`, `channels/gumroad_arm.py`, `channels/gumroad_publisher.py`, `channels/payhip_arm.py`, `channels/payhip_publisher.py`, `lib/publisher_seo.js` | |

---

## 4. الفجوات — ما لا يوجد بعد

1. **لا COS حقيقي.** الأمر التنفيذي يطلب أن "كل قدرة مستقبلية تتكامل عبر COS" — هذا يتطلب بناء موزِّع/مُنسِّق فعلي جديد فوق `server.js`/`factory_loop.js` الحاليين، وليس مجرد تسمية أحدهما.
2. **توحيد مسجِّلات النيتش الثلاثة** لم يحدث بعد (دَين موثَّق ذاتياً من قبل).
3. **وحدة HTTP-fetch مشتركة واحدة** بدل النسختين شبه المتطابقتين — إصلاح بسيط، صفر خطر سلوكي (كلا الدالتين لهما نفس التوقيع والسلوك بالفعل، فالتوحيد استبدال آلي لا إعادة تصميم).

---

## 5. التوصية — القرار المفتوح للرئيس

**لا أوصي بنقل أي ملف فعلياً الآن.** البنية الفيزيائية الحالية (Core/Engines/Channels، معتمدة في `ADR-034`) أثبتت سلامتها عملياً؛ الخريطة أعلاه توثيقية بحتة — تُرضي شرط "كل وحدة في طبقة واحدة فقط" بجدول واضح، لا بترحيل ملفات لا فائدة قياسية منه (`ADR-034` نفسه: "لا تُعِد كتابة كود يعمل بلا فائدة قابلة للقياس").

قراران فعليان يحتاجان تأكيدك تحديداً قبل أي تنفيذ:

1. **بناء COS حقيقي (طبقة 2)** — بناء جديد فعلي، يقع مباشرة ضمن تجميد `ADR-034`. هل تريد تجاوزاً صريحاً الآن (كما فعلت سابقاً لبناء الشركة)، أم الانتظار حتى محفِّز موضوعي واحد؟
2. **توحيد HTTP-fetch المكرَّر + مسجِّلات النيتش الثلاثة** — هذان تحسينان هندسيان بحتان (صفر علاقة بالتجميد الإداري)، منخفضا الخطر، ويمكن تنفيذهما فوراً إن أردت دون انتظار أي محفِّز.

بانتظار قرارك على الاثنين قبل أي كتابة كود.
