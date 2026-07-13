# 🔍 FACTORY AUDIT — Ground Truth Report

**تاريخ الفحص:** 2026-07-11
**المفتّش:** لا تجميل، لا دفاع عن الكود، الحقيقة الأرضية فقط.

---

## 1. ASSETS INVENTORY (الحسابات الموجودة)

**`.env` — المفاتيح الموجودة (الاسم فقط):**
- `GROQ_KEY` — هذا هو المفتاح الوحيد الموجود فعلياً في `.env`.
- لا يوجد `GUMROAD_ACCESS_TOKEN`، ولا أي مفتاح KDP/Etsy/Payhip. `channels/gumroad_publisher.py` يقرأ `GUMROAD_ACCESS_TOKEN` من البيئة أو من `.env`، لكنه **غير موجود** حالياً — أي محاولة تشغيل السكربت ستفشل فوراً بـ `ConfigError`.

**ذِكر المنصات في الكود والتوثيق:**
- `gumroad`: مذكور في 15 ملف `.md` (بما فيها `CLAUDE.md`, `THE_MOAT.md`, `GOLDEN_OPPORTUNITIES.md`) و12 ملف `.py`/كود (`channels/gumroad_publisher.py`, `hive_logbook_generator.py` [تلميحاً عبر config]، `market_hunter.py`، `profit_oracle.py`، إلخ) — لكن **الكود الفعلي القابل للتنفيذ لنشر Gumroad ملف واحد فقط**: `channels/gumroad_publisher.py`.
- `etsy`: مذكور كثيراً في التوثيق الاستراتيجي، وفي `config/channels.json` كقناة `manual` بدون API (Etsy أغلقت الـ API الجديدة منذ 2024).
- `kdp`: مذكور بكثافة، لكن `config/channels.json` يصنّفها `automation: "manual"`, `api_available: false` — لا يوجد ولن يوجد نشر آلي لـ KDP.
- `payhip`: مذكور في `config/channels.json` فقط كقناة مُخطَّطة (`api_available: true` نظرياً) — **لا يوجد أي كود تنفيذي لها**.
- `redbubble`: لا يوجد أي كود تنفيذي — ذِكر استراتيجي فقط في `CLAUDE.md` (المسار #3 المستقبلي).

**ملفات بيانات حسابات:**
- `accounts.json` — **غير موجود**.
- `credentials.md` أو أي شكل منه — **غير موجود**.
- أقرب شيء هو `config/reality.json`: سجل "حقيقة أرضية" بحقل `published_books: []` (فارغ) مع ملاحظة صريحة مكتوبة في الملف نفسه: *"A book is PUBLISHED only when it has a real ASIN from Amazon. A PDF on disk is NOT published. Only a human can add entries here after publishing on KDP."*

**❓ سؤال مباشر لك:** أي من هذه المنصات — Amazon KDP، Gumroad، Etsy، Payhip — لديك عليها حساب فعلي مسجَّل الآن (بريد إلكتروني/طرق دفع مفعّلة)، وأيها لا يوجد له حساب بعد؟

---

## 2. HIVENOTES STATUS (كتاب الخلية)

**ملفات تبدأ بـ `hive_`:**
- `hive_logbook_generator.py` — 39,476 بايت — آخر تعديل 2026-07-10 09:11.
- `seeds/hivenotes/hive_logbook_v1.pdf` — 207,306 بايت (140 صفحة PDF جاهز لـ KDP) — أُنتِج 2026-07-10 09:11.
- `config/book_hivenotes_v1.json` — 972 بايت — إعدادات المحتوى، 2026-07-10 09:08.
- `seeds/hivenotes/gumroad_spec.json` — 785 بايت — مواصفات نشر Gumroad (عنوان "The Beekeeper's Hive Inspection Logbook"، السعر **$6.99**، `cover_image_path: null`) — 2026-07-10 14:05.

**`hive_logbook_generator.py`:** توليد PDF محلي بالكامل عبر `reportlab` — **صفر استدعاء Groq، صفر AI**. مدفوع بالكامل بـ `config/book_hivenotes_v1.json`. آخر إنتاج فعلي: 2026-07-10.

**`factory_loop.log` (كل الـ 178 سجل، بحث كامل عن "hive"):** **صفر ذِكر**. الحلقة الذاتية (`factory_loop.js`) لا تعرف بوجود HiveNotes إطلاقاً — هذا مسار منفصل تماماً يعمل يدوياً خارج الحلقة.

**`finance_data.json`:** `sales: []`, كل الحقول (`totalKDP`, `totalEtsy`, `totalGumroad`, `totalSales`) = `0` → **null/0 → لا مبيعة فعلية**، لا لـ HiveNotes ولا لأي منتج آخر.

**`FACTORY_STATUS.md` و`GROWTH_LOG.md` عن hive:** لا ذِكر مباشر لـ "hive" في `GROWTH_LOG.md` (آخر سطر فيه بتاريخ 2026-07-10 يتحدث عن حالة عامة `critical`، 28 ملف معرفة، 42 فرصة ذهبية، 25% نسبة اجتياز فحص مزدوج). كتاب HiveNotes وُلِد **بعد** آخر إدخال في `GROWTH_LOG.md` وخارج نظام التتبع اليومي بالكامل.

**خلاصة القسم:** الكتاب موجود كملف PDF فعلي وجاهز فنياً، ومعه ملف مواصفات نشر Gumroad بسعر $6.99 — لكن **لم يُرفَع فعلياً إلى Gumroad** (لا يوجد `GUMROAD_ACCESS_TOKEN`، ولا سجل تنفيذ لـ `gumroad_publisher.py` في أي ملف `.log` في المشروع بحث كامل). هذا كتاب جالس على القرص، لا في السوق.

---

## 3. FACTORY LOOP HEALTH

**آخر 50 سطر من `factory_loop.log`:** الحلقة تعمل كل 10 دقائق تقريباً (بعض الفجوات أطول، من 8 دقائق إلى عدة ساعات — ليست دقيقة 10:00 صارمة). آخر سجل بتاريخ 2026-07-10T22:09:04Z، الحالة `critical` بسبب:
```
"sensing_engine":{"ok":false,"severity":"degraded","detail":"n8n غير متاح: fetch failed"}
```
n8n (محرك الاستشعار) متوقف/غير متصل في آخر تشغيلات مسجَّلة. الحلقة تتابع العمل بدونه (fallback إلى Groq مباشرة لـ Scout) لكن الحالة العامة تُصنَّف `critical` بسبب هذا فقط — لا شيء آخر معطوب في آخر تشغيل (`book_generator`, `finance`, `books_folder` كلها `ok: true`).

**`.factory_loop.lock`:** المحتوى = `24176` (رقم PID لعملية واحدة). القفل يعمل كما صُمِّم (تعليق في الكود يذكر أن نسختين كانتا تعملان بالتوازي سابقاً وسبَّبتا ازدواج كتابة السجلات — تم إصلاحه بهذا القفل).

**`factory_loop.js` — الدورة:**
- **كل 10 دقائق** (`INTERVAL_MS = 10 * 60 * 1000`).
- كل دورة تفحص: `heal_finance` (سلامة `finance_data.json`)، `heal_books_empty` (هل `books/` فارغ)، `heal_n8n` (هل n8n يستجيب)، `hunt` (هل آخر نيتش مؤهَّل له كتاب مُولَّد فعلاً — وإن لم يكن، تولِّده عبر `/generate-book`)، `weekly_report` (يوم الأحد فقط)، `golden_hunter` و`self_awareness` (مرة واحدة يومياً لكل منهما).
- آلية Circuit Breaker: أي فشل فحص مزدوج (Dual Inspection) يُسجَّل في `REJECTED_NICHES.md` بفترة تهدئة 7 أيام كي لا يُعاد توليد نفس النيتش المرفوض ويُهدَر استدعاء Groq.

**`inspections.log` (آخر إدخالات، 35 سجل إجمالي):** كل الفحوصات الفنية (PDF، غلاف، تشكيل عربي) **نجحت 100%** في كل السجلات المفحوصة. الفحص التجاري (`commercial`) هو الحلقة الضعيفة: **30 من 35 فحصاً فشلوا في الشق التجاري**، فقط **5 نجحوا ووصلوا `"published": true"`** (كلها بأسعار ≥ $30 حسب مبدأ "الزبدة" Butter Principle).

---

## 4. GOLDEN OPPORTUNITIES (الفرص المصطادة)

**`golden_opportunities.json`:** `count: 42` فرصة (وُلِّدت 2026-07-10T05:33). أعلى 5 حسب `profit_score`:

| السعر المقترح | Score | المنصة | الفكرة |
|---|---|---|---|
| $39 | 71 | KDP + Etsy + Gumroad | قوالب تصميم SVG قابلة للقص — العودة للمدارس |
| $39 | 71 | KDP + Etsy + Gumroad | قوالب تصميم SVG قابلة للقص — العودة للمدارس (مكرر) |
| $39 | 71 | KDP + Etsy + Gumroad | قوالب تصميم SVG قابلة للقص — العودة للمدارس (مكرر) |
| $39 | 71 | KDP + Etsy + Gumroad | قوالب تصميم SVG قابلة للقص — العودة للمدارس (مكرر) |
| $39 | 69 | KDP + Etsy + Gumroad | قوالب تصميم SVG قابلة للقص — للرجال |

ملاحظة صادقة: 4 من أعلى 5 هي **نفس الفكرة مكررة حرفياً** — الصياد (Golden Hunter) يُعيد اكتشاف نفس النيتش بلا تنويع كافٍ. هذه فرص "مكتشَفة" فقط — **لا يوجد أي منها تحوَّل إلى منتج فعلي أو نشر**.

**`REJECTED_NICHES.md`:** رُفض واحد فقط مسجَّل هنا (نيتش "أبحاث التوجيه الذكي"، `profit_score: 58 < 60`، بتاريخ 2026-07-09). هذا الملف يُستخدم فقط لفشل ما قبل التوليد (Circuit Breaker) — أغلب الرفض الفعلي يحدث بعد توليد الكتاب ويُسجَّل في `QUARANTINE.md` بدلاً من هنا (فجوة معمارية موثَّقة في `LESSONS_LEARNED.md`: منطق التسجيل غير موحَّد بين المسارين).

**`QUARANTINE.md`:** **23 إدخال حجز**. الغالبية الساحقة (17 من 23) لنفس الفكرة "النصوص الساحرة: مهارات الكتابة الرهيئة" — الحلقة كانت تعيد توليد نفس الكتاب المرفوض تكراراً كل 10 دقائق قبل أن يُصلَح الـ Circuit Breaker. الأسباب الشائعة للحجز: `butter_price` (السعر أقل من $30) و`not_duplicate` (تطابق كتاب سابق).

---

## 5. ARMS READINESS (جاهزية الأذرع)

- مجلد `arms/` — **غير موجود**.
- ملفات بنمط `*_arm.py` — **غير موجودة**.
- `distributor.py`, `publisher.py`, `uploader.py` (بالاسم المضبوط في الجذر) — **غير موجودة**.
- **الاستثناء الوحيد الحقيقي:** `channels/gumroad_publisher.py` — سكربت CLI مستقل (list/create/sales عبر Gumroad REST API)، مكتوب بعناية (لا يُسرّب التوكن في رسائل الخطأ)، لكنه **لم يُنفَّذ أبداً**: بحث كامل في كل ملفات `.log` في المشروع عن `gumroad_publisher` أو `GUMROAD_ACCESS_TOKEN` — **صفر نتيجة**.
- `puppeteer`, `playwright`, `selenium` — بحث في كل ملفات `.py` و`package.json` — **صفر نتيجة**. لا يوجد أي أتمتة متصفح للنشر اليدوي (KDP وEtsy يتطلبان رفعاً يدوياً بالمتصفح ولا يوجد أي كود يحاول أتمتة ذلك).
- محاولات نشر آلي سابقة في اللوغات — **صفر**. لم يحدث نشر آلي واحد، لأي منتج، على أي منصة، حتى الآن.

**خلاصة القسم:** يوجد ذراع واحدة مكتوبة وجاهزة تقنياً (Gumroad)، لكنها معطَّلة بغياب مفتاح API واحد فقط، ولم تُختبر ولو مرة.

---

## 6. SERVER ENDPOINTS الفعلية

قائمة كاملة من `server.js` (20 مساراً):

| Method | Path | الوظيفة |
|---|---|---|
| POST | `/api/safety/check` | بوابة أمان النيتش قبل التوليد — تستدعي `safety_filter.py`؛ أي فشل تقني (spawn/timeout/exit) = رفض إجباري، لا يمر شيء بدون فحص. |
| POST | `/generate-book` | توليد كتاب فعلي عبر `book_generator.py` (subprocess عبر stdin JSON)؛ المسار الأساسي لإنتاج PDF. |
| POST | `/chat` | محادثة عامة مع Groq (`message` + `agent` اختياري). |
| GET | `/finance` | قراءة `finance_data.json`. |
| POST | `/finance/add` | إضافة عملية بيع (منصة/مبلغ/منتج/تاريخ) — كتابة ذرية (temp file + rename). |
| DELETE | `/finance/delete/:id` | حذف عملية بيع بالمعرّف. |
| POST | `/api/agent/:name` | استدعاء أحد الوكلاء الستة (scout/builder/design/qa/publisher/finance) عبر Groq حي، مع `system prompt` مخصص لكل وكيل. |
| POST | `/api/scout/run` | خط إنتاج Scout الكامل: تحفيز n8n → اختيار نيتش عبر Groq → توليد كتاب حقيقي → تسجيل التشغيل. |
| POST | `/api/trends` | نقطة استقبال من n8n (Sensing Engine) — أي اتجاه يمر عبر `quality_gate()` ويُسجَّل في `OPPORTUNITIES.md` إن مرّ. يرد 200 دائماً لـ n8n بغض النظر عن النتيجة الداخلية. |
| POST | `/api/market-analyze` | **stub ثابت** (مذكور صراحة في `CLAUDE.md`) — غير متصل فعلياً بـ `market_analyzer.py`. |
| POST | `/api/qa-check` | فحص جودة منتج (checklist). |
| GET | `/api/reality` | يشغّل `runReality()` — تقرير الحقيقة الأرضية (يقرأ `config/reality.json` على الأرجح). |
| GET | `/health` | فحص صحة عام للمصنع (`computeHealthStatus()`). |
| GET | `/factory-loop/status` | يقرأ ذيل `factory_loop.log` ويعرضه. |
| GET | `/good-morning` | ملخص صباحي مجمَّع (حالة المصنع + الفرص + إجراءات الليلة الماضية + Next Dollar + الوعي الذاتي). |
| GET | `/oracle` | يقرأ `golden_opportunities.json` ويعرضه. |
| GET | `/inspections` | يقرأ `inspections.log` ويعرضه. |
| GET | `/brain` | يعرض حالة "العقل" (على الأرجح `knowledge_brain.js`). |
| GET | `/hunter` | يقرأ `market_hunter_runs.log` ويعرضه. |
| GET | `/awareness` | يشغّل ويعرض تقييم `self_awareness.js`. |
| GET | `/{*path}` | Fallback — يرسل `index.html` لأي مسار غير معروف (SPA catch-all). |

---

## 7. QUALITY DOCTOR

- **`quality_doctor.py`** — يحوي `class QualityDoctor` — **غير متصل بأي endpoint في `server.js`** (مؤكَّد أيضاً في `CLAUDE.md` صراحة: "Not yet wired to any HTTP endpoint"). كود ميت عملياً من منظور دورة الإنتاج الحية.
- **`inspectors.py`** — هذا هو الفاحص الحقيقي المستخدَم فعلياً (Dual Inspection، `CONSTITUTION.md §17`). يفحص:
  - **تقني (`inspect_technical`):** حجم ملف PDF، عدم تلف الـ PDF (`pypdf`)، عدد الصفحات (حد أدنى)، أبعاد الصفحة منطقية، لا صفحات فارغة (بايت/صفحة كحد أدنى)، الغلاف يُفتح عبر Pillow، أبعاد الغلاف (1600×2560)، منطقة العنوان عند ~70% من الارتفاع، العنوان أكبر من اسم المؤلف، تشكيل عربي حقيقي متوفر (`arabic_reshaper` + `python-bidi`)، لا نص Placeholder في العنوان/العنوان الفرعي/المؤلف.
  - **تجاري (`audit_commercial`):** `profit_score` (حد أدنى 60/100 عبر `profit_oracle.py`)، `butter_price` (السعر ≥ $30)، `not_duplicate` (لا تطابق نيتش سابق مُنتَج)، `not_previously_rejected` (لم يُرفض من قبل في `QUARANTINE.md`).
- **`safety_filter.py`** — قوائم حظر (`risk_level: "blocked"`) لمحتوى ذي علامة تجارية مسمومة، مالي، طبي، وبالغين — بوابة أمان منفصلة تماماً عن الفحص التجاري/التقني، تعمل **قبل** التوليد.

**نتائج `inspections.log` (35 فحصاً مسجَّلاً):**
- **الفحص التقني: 35/35 نجح (100%)** — لم يفشل كتاب واحد تقنياً.
- **الفحص التجاري: 5/35 نجح فقط (~14%)** — 30 فشلوا، أغلبهم بسبب `butter_price` (سعر أقل من $30) و`not_duplicate`/`not_previously_rejected` (نفس النيتش المرفوض يتكرر توليده).

---

## 8. HONEST ONE-LINERS

- **ماذا يعمل المصنع اليوم فعلاً:** توليد كتب PDF عربية عالية الجودة فنياً (غلاف + تشكيل عربي + تخطيط سليم) تلقائياً كل 10 دقائق، بلا أي بيع فعلي واحد — مصنع محتوى يعمل، بلا سوق يستقبله.
- **آخر شيء أنتجه ولمن:** كتاب "الرجل الناجح: 30 يومًا لتميزك الشخصي" (12 صفحة) في 2026-07-09T09:39 — نجح الفحص المزدوج ووُسِم `"published": true"` **داخل نظام الفحص فقط** — لم يُرفع فعلياً لأي منصة بيع حقيقية (لا حساب KDP مُثبَت، لا `ASIN` في `config/reality.json`). "منشور" هنا يعني "اجتاز الفحص"، لا "يُباع الآن".
- **لماذا لم يبع بعد (السبب التقني الحقيقي):** لا يوجد أي كود ينفّذ خطوة الرفع الفعلي لمنصة بيع حقيقية بشكل تلقائي أو حتى موثَّق يدوياً — `gumroad_publisher.py` موجود وجاهز لكنه لم يُشغَّل مرة واحدة (لا `GUMROAD_ACCESS_TOKEN`)، وKDP/Etsy يتطلبان رفعاً يدوياً بالمتصفح لا يوجد له سجل حدوث واحد. الإنتاج توقف عند حافة "الملف على القرص" ولم يعبر إلى "الملف على المنصة".
- **أضعف حلقة في الطريق من `.py` إلى $1:** الفجوة بين `books/*.pdf` (أو `seeds/hivenotes/*.pdf`) وبين ضغطة "Publish" الفعلية على منصة حقيقية — كل ما قبلها (توليد، فحص جودة، فحص أمان، فحص تسعير) مؤتمت ويعمل؛ كل ما بعدها (الرفع الفعلي، الحساب، أول عملية بيع) **لم يبدأ بعد إطلاقاً**.

---

## أسئلة تحتاج إجابتك (المصنع لا يعرفها ولا يمكنه معرفتها بنفسه)

1. **الحسابات:** أي من KDP / Gumroad / Etsy / Payhip لديك عليها حساب فعلي مسجَّل الآن؟ (مطلوب لإكمال القسم 1)
2. **مفتاح Gumroad:** هل تريد إنشاء `GUMROAD_ACCESS_TOKEN` الآن لتفعيل `channels/gumroad_publisher.py` ونشر كتاب HiveNotes الجاهز فعلياً ($6.99)، أم لا يزال هذا القرار مبكراً؟
3. **n8n:** آخر تشغيلات الحلقة تُظهر `n8n غير متاح: fetch failed` — هل n8n متوقف عن قصد، أم عطل غير مقصود يحتاج إصلاحاً؟
4. **غلاف HiveNotes:** `seeds/hivenotes/gumroad_spec.json` يحوي `"cover_image_path": null` — هل يوجد غلاف مُصمَّم لهذا الكتاب في مكان آخر، أم ما زال مفقوداً فعلياً؟
5. **أولوية النشر اليدوي:** بما أن KDP وEtsy يتطلبان رفعاً يدوياً بلا أي بديل آلي، هل أنت مستعد لتخصيص وقتك لرفع أول كتاب يدوياً كتجربة، أم الأولوية هي إكمال المسار الآلي (Gumroad) أولاً؟
