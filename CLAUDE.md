# CLAUDE.md

دليل Claude Code لهذا المستودع. النسخة الكاملة السابقة: `CLAUDE.backup.md`. التفاصيل الطويلة موزعة في `docs/claude_md/` (انظر الفهرس في النهاية). اقرأ الملف ذي الصلة قبل لمس الوحدة المعنية.

## الهوية

Galaxy Forge منصة إنتاج رقمي متعددة المنتجات (شركة استثمار رقمي، لا شركة برمجيات). المسار النشط الآن: الكتب والمنتجات الرقمية (Amazon KDP، Gumroad، Etsy). المسارات المخطط لها: قوالب، لوحات فنية، تطبيقات، خدمات رجال أعمال، تجارة دولية.

بنية من 3 طبقات: (1) العقل المشترك: الوكلاء الستة + Groq + الأدوات. (2) محرّكات المنتجات `book_engine` وغيره، كل محرك جديد يتبع واجهة `book_engine`. (3) قنوات النشر `channels/*_arm.py`، إغلاق منصة يوقف قناتها فقط.

## الأولوية الحالية (توجيه المؤسس 2026-11-05)

- الهدف الوحيد الآن: **أول زبون حقيقي يدفع**. المصنع يخدم هذا الهدف فقط، ولا أذرع ولا أفكار جديدة.
- **تجميد المنتجات الجديدة**: `GF_FREEZE_NEW_PRODUCTS=true` في `.env`. لا تعمل أي حلقة تنتج منتجاً رقمياً جديداً أو تنشر قائمة جديدة (توليد الكتب، الصيد الذهبي، سلسلة الوكلاء اليومية، `publish_approved_daily.py`). لا كود محذوف: إلغاء المتغير يستأنف العمل. لا تُرفع إلا بأمر المؤسس.
- **Claude Code هو الوكيل الوحيد العامل على المشروع. OpenCode متوقف.** لا توجد جلسة موازية تعدّل الملفات: لا حاجة لافتراض تعديلات خارجية بين المراجعة والالتزام (ومع ذلك افحص `git diff` قبل كل commit).
- المرحلة 2: ديمو مساعد وكالات العمرة في الجزائر (انظر `PROGRESS.md`).

## القواعد الأساسية

- لا توسع بمنتج جديد قبل أول دولار حقيقي من المنتج الحالي (القاعدة الذهبية). الحقيقة الأصعب: `config/reality.json`، لا `finance_data.json` الخام.
- الأمان: كل شيء محلي، مفاتيح API في `.env` فقط، لا cloud. لا تضع أسراراً في ملفات متتبعة.
- الصدق أولاً (Truth First): لا أرقام أو نتائج أو مراجعات مختلقة. عند غياب الإشارة الحقيقية اكتب صراحة: NOT BUILT / NOT IMPLEMENTED / NOT CONNECTED / NOT MEASURED / UNKNOWN / WAITING FOR REAL DATA / SIMULATION / REFERENCE IMPLEMENTATION / PLANNED، ولا تخترع مصطلحاً عاشراً.
- 4 بوابات بشرية دائمة لا تُرفع دون سؤال المؤسس: تنفيذ مقترحات التطور (`evolution_queue.py`)، إعادة تخصيص رأس المال، إغلاق الأعمال، نشر قناة جديدة أو عالية المخاطر (`channels/publish_protection.py`). التنفيذ التلقائي المستمر (daemon/event bus/queue) رُفض 6 مرات سابقاً (ADR-107/110/115/142/147/157) فلا تعد فتحه.
- أي كتابة حية على منصة تمر عبر `channels/write_gate.py`، وإنشاء قائمة مدفوعة يتطلب تصريحاً (`channels/publication_clearance.py`): موافقة المؤسس للمنتج أو قرار Quality Gate المركزي. لا يوجد override.
- لا نشر حي أو قبول مال أو إنشاء حسابات أو رسائل خارجية دون موافقة صريحة. المستودع عام: لا تُلتزم ملفات المنتجات المدفوعة (`books/`).
- قبل بناء أي شيء: ابحث عن وحدة موجودة تؤدي الغرض نفسه (مراجعات سابقة وجدت تداخلاً شبه كامل في كل مرة) ومدّدها بدل تكرارها. تحقق من تصادم الأسماء (`growth_stages.py` مقابل `growth_engine.py`، `executive_questions.py` مقابل `executive_intelligence/`). مبدأ الاختيار: قيمة مؤسسية طويلة المدى، لا مزيد من الكود.
- لا تشغّل `taskkill /IM node.exe`: `server.js` و`factory_loop.js` قد يعملان. تعديلات JS في `factory_loop.js`/`server.js` لا تسري إلا بعد إعادة التشغيل.
- قبل الالتزام (commit): افحص نطاق `git diff`، ففي المستودع تغييرات محلية قديمة غير ذات صلة. فرّق بين ملفات `data/*.jsonl` قبل وبعد تشغيل الاختبارات. لا تستدعِ أي نقطة تقييم/صيد حي (مثل `run_hunt()`) من مسار قراءة، لأنها تُلحق قرارات حقيقية.
- حساب Google شخصي واحد يربط كل المنصات عن قصد (`OpenClaw_Brain/00_Governance/IDENTITY_ARCHITECTURE.md`، ADR-014): لا تقترح تجزئة حسابات قبل قراءته.

## التشغيل

```powershell
npm install; pip install reportlab      # أول مرة
node server.js                           # http://localhost:3000 (PORT)
node scripts/supervisor.js               # الخادم تحت مراقبة (إعادة تشغيل + تنبيه Telegram)
SUPERVISOR_TARGET=factory_loop.js node scripts/supervisor.js   # حلقة المصنع تحت مراقبة
python scripts/check_doctrine.py         # بوابة العقيدة التشغيلية (للقراءة فقط)
```

الاختبارات: `python -m pytest tests/...` (Python) و`node tests/*.js` (Node). لا يوجد linter. لا تُشغّل الحزمة الكاملة دفعة واحدة (استهلاك ذاكرة عالٍ): شغّل الملفات ذات الصلة.

متغيرات `.env` الأساسية: `GROQ_KEY`، `PORT`، `MISSION_CONTROL_PASSWORD`، `INTERNAL_SERVICE_TOKEN`، `FACTORY_LIVE_PUBLISH`، `GUMROAD_ACCESS_TOKEN`، `N8N_PRODUCTION_WEBHOOK_URL` (اختياري)، `AFFILIATE_MODE`، `AMAZON_ASSOCIATE_TAG`.

## البنية

| الطبقة | التقنية |
|---|---|
| الواجهة | `index.html` (HTML/CSS/JS واحد، RTL عربي، ترميز **UTF-16 LE مع BOM**: حافظ عليه عند التحرير) |
| الخادم | Express 5 في `server.js`، المنفذ 3000 |
| الذكاء | Groq (`llama-3.1-8b-instant`) عبر `POST /api/agent/:name`، والتوجيه متعدد النماذج `ai_capability/orchestrator.generate()` |
| PDF | Python + reportlab (`book_generator.py`) |
| البيانات | ملفات JSON/JSONL محلية (`data/`, `finance_data.json`)؛ لا قاعدة بيانات |

- توليد الكتب: `POST /generate-book` يشغّل `book_generator.py --json` عبر stdin/stdout؛ ينتج PDF في جذر المشروع.
- الوكلاء الستة (`AGENT_PROMPTS` في `server.js`): scout, builder, design, qa, publisher, finance. المسار `/api/agent/:name` ومعظم المسارات محمية بـ`requireMissionControlAuth`؛ الأتمتة الداخلية تستخدم `X-Internal-Token`.
- حلقة المصنع `factory_loop.js`: tick كل ~10 دقائق (ليست مجدولة بنظام التشغيل؛ تعمل تحت المراقب أعلاه). تولّد التقارير اليومية/الأسبوعية (الأحد)/الشهرية/الفصلية/السنوية ولا تعتمد أي موافقة بشرية.
- Mission Control: `mission_control_executive_v1.html` (لوحة تنفيذية) و`mission_control.html` (تفاعلية لكل نيتش)، تُغذّيهما `SERVICE_REGISTRY`/`ACTION_REGISTRY` في `server.js` و`mission_control_api.py::_ENDPOINTS`. اختبر أي مدخل جديد عبر HTTP حي، وقِس زمنه قبل الاعتماد على مهلة 30 ثانية الافتراضية.
- منصة العملاء العامة: `customer_site/` (تُخدم على `/site/`)، خط أنابيب `customer_pipeline.py`، بوابة دفع Paddle (تنتظر إتمام onboarding من المؤسس).
- القنوات: `channels/` (gumroad, payhip, etsy, paddle, x, kdp). `distributor.py::distribute()` يمر عبر Quality Gate ثم `publish_protection` قبل كل نشر حقيقي؛ الوضع الافتراضي dry-run.
- قرارات الفرص: `decision_engine/` (مصدر الحقيقة `data/decisions.jsonl`)، التسجيل `profit_oracle.py` (حد القبول 65/100)، الوعي الاستراتيجي `goos.py` (استشاري فقط).
- لا يوجد scheduler مستقل ولا daemon: كل ما هو تلقائي يعمل من tick الحلقة.

## وحدات مستقلة مهمة

`market_analyzer.py` (تسجيل النيتش)، `cover_designer_v2.py` (الأغلفة)، `niche_validator_v2.py` (التحقق)، `inspectors.py` (الفحص المزدوج، بوابة الجودة الفعلية)، `brand_dna.py` (صوت الشركة وقواعد الثقة)، `truth_first.py`، `reality_audit.py` (تصنيف النقاط الحية؛ حارس إعادة الدخول `_audit_depth` إلزامي قبل ربط أي نقطة جديدة تستدعيه). أدوات يدوية مستقلة: `audit_seed.py`, `hive_logbook_generator.py`, `seed_english_book.py`.

## العقيدة التشغيلية (من الدورة 103)

`OpenClaw_Brain/00_Governance/PERMANENT_OPERATING_DOCTRINE.md` يحدد كيف تُدار الدورة وما يثبتها؛ `MASTER_OPERATING_CONSTITUTION.md` يبقى الدستور. تُنفَّذ بالوحدات: `incident_memory.py`، `doctrine_review.py`، `handoffs.py`، `cycle_metrics.py`، `weak_signals.py`، `business_arms.py`. البوابة: `python scripts/check_doctrine.py`. حالات الإصدار السبع لا تُدمج، و`FIRST_SALE_VERIFIED` هو التعريف الوحيد للنجاح وهو صفر حالياً. سجل المحادثات والملاحظات الختامية: `CLOSING_NOTE.md`.

## فهرس التفاصيل (`docs/claude_md/`)

| الملف | المحتوى |
|---|---|
| `01_identity_and_strategy.md` | المسارات الستة، الفلسفة الاستراتيجية، تأجيل التوسع العالمي وGCID، بروتوكول التطور الذاتي |
| `02_running_and_architecture.md` | التشغيل التفصيلي، تدفق توليد الكتب، الوكلاء، المالية، لوحة التنفيذ و`/health` |
| `03_customer_platform_and_resilience.md` | منصة العملاء، محرك التطور، حماية النشر، المرونة والمراقبة المستمرة |
| `04_executive_layers.md` | Strategic Core، Galaxy Council، Capital Allocation، GOX، ABB، Executive Brain، GF-OS، Affiliate Commerce، Simulation Mode |
| `05_enterprise_programs.md` | Enterprise Ops/Brain/Growth/Planning، Truth First، Digital Twin، Reality Audit، Evidence، Registry، GOOS، Market Domination، SIE (ADR-155..178) |
| `06_execution_mode_and_eos.md` | وضع التنفيذ ومزوّد الأدلة، Commercial Execution Engine، إصلاحات مهمة، CEO Home/Search/Feed، Business Development، Trust Audit |
| `07_utilities_and_doctrine.md` | الأدوات المساعدة، غياب المجدول، ترميز `index.html`، تفاصيل العقيدة التشغيلية |

النسخة الأصلية الكاملة غير المعدّلة: `CLAUDE.backup.md` (200 ألف بايت تقريباً).
