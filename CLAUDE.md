# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## الهوية والرؤية

🏭 OpenClaw Factory ليست مصنع كتب فقط - هي منصة إنتاج رقمي متعددة المنتجات، قابلة للتحول الفوري بين المسارات لضمان الاستمرارية.

### المسارات الستة المخطط لها

| # | المسار | المنصات |
|---|--------|---------|
| 1 | الكتب الرقمية (نشط الآن) | Amazon KDP |
| 2 | القوالب الجاهزة | Etsy, Gumroad |
| 3 | اللوحات الفنية الرقمية | Etsy, Society6, Redbubble |
| 4 | التطبيقات والأدوات الإلكترونية | App stores, Web |
| 5 | خدمات رجال الأعمال | اشتراكات VIP |
| 6 | منصة تسوّق دولي | سيارات، بضائع جملة |

### المبدأ المعماري - 3 طبقات

```
الطبقة 1 — العقل المشترك (Core)
  الوكلاء الستة + Groq + الأدوات
  لا تتغير.

الطبقة 2 — محرّكات المنتجات (Engines)
  book_engine  template_engine  art_engine
  app_engine   service_engine   trade_engine
  مستقلة — قابلة للإضافة/الحذف.

الطبقة 3 — قنوات النشر (Channels)
  kdp_channel  etsy_channel  gumroad_channel
  shopify_channel  direct_channel
  لو منصة أغلقت، نوقف قناتها فقط.
```

### القواعد الذهبية

- لا توسع بمنتج جديد قبل أول دولار من المنتج الحالي
- كل محرك جديد يجب أن يتبع نفس واجهة `book_engine` الموجود
- الأمان: كل شيء محلي، API keys في `.env` فقط، لا cloud
- المحتوى: كل وكيل يجب أن يكون قابل للتحول بسهولة بين المسارات

### ⚠️ قبل اقتراح أي بنية أمنية أو فصل حسابات

كل أداة/منصة في OpenClaw (GitHub، KDP، Gumroad، مستقبلاً Payhip/Etsy/Canva/Pinterest، Groq، Anthropic، n8n) مربوطة اليوم بحساب Google شخصي واحد، بلا استثناء. هذا قرار واعٍ (بساطة + تكلفة صفر لمرحلة مبكرة)، لا سهواً — راجع `OpenClaw_Brain/00_Governance/IDENTITY_ARCHITECTURE.md` والمخاطر الصريحة فيه، و`ADR-014` لمحفّزات إعادة النظر، **قبل** اقتراح أي تجزئة حسابات أو بنية أمنية جديدة.

---

## Running the project

```powershell
# Install Node dependencies (first time)
npm install

# Install Python dependencies (first time)
pip install reportlab

# Start the server
node server.js
# Runs at http://localhost:3000 (or PORT env var)
```

There is no build step, test suite, or linter configured.

## Architecture

**OpenClaw Factory** is an Arabic-language (RTL) dashboard for a self-publishing business selling digital products on KDP, Etsy, and Gumroad.

### Stack

| Layer | Technology |
|---|---|
| Frontend | Single-file vanilla HTML/CSS/JS (`index.html`), Arabic RTL, no framework |
| Backend | Express 5 (`server.js`), port 3000 |
| AI | Groq SDK — `llama-3.1-8b-instant` via `POST /chat` and `POST /api/agent/:name` |
| PDF generation | Python + reportlab (`book_generator.py`) |
| Data | `finance_data.json` (flat JSON, written directly by server) |

### Key flow: book generation

The browser calls `POST /generate-book` → `server.js` spawns a Python subprocess (`book_generator.py --json`) → passes parameters via `stdin` as JSON → reads JSON result from `stdout`. The PDF is written to the project root directory with a filename derived from the book title.

`book_generator.py` is standalone and can be run directly:
```bash
python book_generator.py          # generates demo_cookbook.pdf
```
When invoked with `--json`, it reads a JSON object from stdin:
```json
{"title":"...", "subtitle":"...", "type":"journal", "theme":"blue", "pages":120, "author":"...", "output":"filename.pdf"}
```
Supported `type` values: `journal`, `planner`, `habit`, `gratitude`, `fitness`, `tracker`, `healthy_eating`, `budget`, `mindfulness`, `cookbook`.

### Environment variables (`.env`)

```
GROQ_KEY=<your Groq API key>
PORT=3000
```

### Agent endpoints

`POST /api/agent/:name` — **live Groq calls**, not stubs. Each of the six agents has a dedicated `system` prompt defined in the `AGENT_PROMPTS` object in `server.js` (lines 127–190):

| Agent | Role |
|---|---|
| `scout` | Market analysis — trending niches, pricing, competition level |
| `builder` | Content generation — book structure, sample pages |
| `design` | Cover & interior design ideas for 6×9 inch books |
| `qa` | Quality checklist, common KDP/Etsy rejection reasons |
| `publisher` | SEO-optimised titles, descriptions, keywords, Amazon categories |
| `finance` | Pricing strategy, profit margins per platform, break-even |

Each agent accepts an optional `message` in the request body; if omitted, a default `trigger` prompt fires automatically. `index.html` only wires UI buttons for `builder`/`design`/`publisher`/`qa` — the bare `scout` and `finance` agents above are live and reachable via `POST /api/agent/scout` / `POST /api/agent/finance`, but have no UI trigger (the fuller `/api/scout/run` pipeline below is what the UI's Scout button actually calls).

There is also a separate, more complete Scout pipeline: `POST /api/scout/run` runs a real end-to-end chain — Groq market brief → pricing (`getButterPrice()` in `factory_loop.js`) → niche safety filter (`safety_filter.py`) → `book_generator.py` → auto-distribution (`autoDistributeScoutBook()` → `distributor.py`). This is distinct from the simple `POST /api/agent/scout` text-analysis call above and is what the dashboard's Scout button triggers.

### Finance data

Finance is persisted to `finance_data.json` in the project root. The server reads/writes this file synchronously. Structure:
```json
{"sales": [...], "totalKDP": 0, "totalEtsy": 0, "totalGumroad": 0}
```

### Other Python utilities

- `market_analyzer.py` — Static niche scoring logic; called live via `POST /api/market-analyze` (`server.js`).
- `quality_doctor.py` — QA checker that validates product data (PDF pages, SEO keywords, pricing, description length); called live via `POST /api/qa-check` (`server.js`).
- `cover_designer_v2.py` — The live cover-generation engine, imported by `book_generator.py`, `inspectors.py`, `profit_oracle.py`, and `server.js`. (An older `cover_generator.py` existed as an unwired Day-05 scratch script and was removed 2026-07-13.)
- `niche_validator_v2.py` — The live niche-validation engine (imported as `NICHE_VALIDATOR` by `book_generator.py`/`profit_oracle.py`). (An older `niche_validator.py` v1 existed, claimed a `/analyze-niche` endpoint that no longer exists in `server.js`, and was removed 2026-07-13.)
- `audit_seed.py`, `hive_logbook_generator.py` — standalone CLI tools run manually, by design not imported by any other module ("Zero factory impact" per `audit_seed.py`'s own docstring). `hive_logbook_generator.py` produced the real HiveNotes KDP product (`seeds/hivenotes/`) entirely outside the generic `book_generator.py` pipeline and outside `factory_loop.js`'s awareness.

### No scheduler exists

Nothing in this repo runs anything on a timer: `factory_loop.js` (the Golden Hunter loop) has no cron, no `package.json` script, and no CI workflow — it only runs when invoked manually (`node factory_loop.js`). It also does not auto-process Human-in-the-Loop approvals: it only counts files in `pending_review/queue/` and writes an alert to `NEEDS_REVIEW.md`; a human must run `scripts/process_approved_drafts.py` manually after approving a draft. Confirmed by full-repo audit, 2026-07-13.

### `index.html` encoding

The file is saved as **UTF-16 LE with BOM**. When reading or editing it, ensure your editor preserves this encoding, or the Arabic text and emoji will corrupt.
