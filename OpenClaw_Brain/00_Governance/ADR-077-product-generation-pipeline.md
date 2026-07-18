# ADR-077 — Product Generation Pipeline: One Connected, Autonomous Flow

**Date:** 2026-07-18
**Status:** Adopted, tested (516 Python tests green, zero regressions; 137/138 JS tests green — the one failure is a pre-existing, unrelated environment flake, see "What was verified" below).
**Mission:** Complete the first production-grade Product Generation Pipeline — Market Intelligence → Opportunity Selection → Product Specification → AI Content Generation → Packaging → QA → Metadata → Paddle Product Creation → Publishing Queue → Finance Ledger → Telegram Founder Report, as one autonomous flow, using the shortest real path between already-built pieces.

---

## The problem

Before this phase, every stage up through "a real technical-docs PDF exists" was real (`ADR-065`–`ADR-076`), but four concrete things were still placeholders or disconnected:

1. **AI Content Generation for the techdoc/product-package track was placeholder text**, not a real Groq call — `book_generator.py`'s `generate_product_package()` filled sections with static filler.
2. **The deliberate/manual orchestration path (`orchestrator/engines/production.py`) diverged from the automatic tick** — it always built the old AI-book payload regardless of a decision's Strategic Production Priority Ladder tag, silently ignoring `ADR-071`'s ladder-aware routing that `factory_loop.js` already had.
3. **Finance Ledger never reconciled** — `channels/ledger.py` recorded real sales, but nothing ever carried them into `finance_data.json`, the file the founder's actual revenue figure reads from (confirmed gap, `COMPANY_INTEGRATION_AUDIT_20260718.md`).
4. **No unique ID connected the stages.** `production_factory/dossier.py` computed a real `production_id` (`f"PROD-{decision_id}"`) for planning, but the actual generated file, its `Product` record, its ledger entry, and any Telegram report each had no way to trace back to the same decision — two silently disconnected identities.

## The fix

**Requirement #1 — real content, not placeholders.**
`book_generator.py` gained `ai_generate_techdoc_content()` / `_parse_sectioned_techdoc()` / `_fallback_techdoc_content()` — the same real-Groq-call-with-honest-fallback discipline `ai_generate_book_content()` already used for books, applied to the techdoc/product-package track. `generate_product_package()` now calls it for every plain-string section title, falling back to a clearly-labeled "AI content generation was unavailable" placeholder only on a real Groq failure — never silently claiming AI-generated content that isn't.

**Requirement #2/#3 — structured JSON, no duplicated logic.**
`orchestrator/engines/production.py` now reads `decision.get("ladder")` from its own context (already present via `ADR-076`'s unification) and branches: a ladder-tagged decision routes to `product_type="techdoc"` with the real ladder price, reusing the exact routing `factory_loop.js`'s `briefFromGoldenOpportunity()` already established (`ADR-071`) rather than inventing a second rule. `revenue_pipeline/plan.py`, `production_factory/dossier.py`, and `revenue_pipeline/pipeline.py` were updated to route ROI/quality economics against a real, already-configured platform band (`gumroad_elite`) via a new `economics_platform` field, distinct from the `recommended_platform` distribution-channel recommendation (`"paddle"` has no `config/economics.json` entry — conflating the two would have raised `ValueError("unknown platform: paddle")`).

**Requirement #4 — every failure logged and recoverable.**
No change needed here — `orchestrator/retry.py` and the immutable timeline (`orchestrator/timeline.py`) already give every stage retry + an append-only failure record; this phase only added stages that inherit that same guarantee (Finance Ledger reconciliation logs `skipped_unrecognized` rather than guessing an amount at $0).

**Requirement #5 — one unique ID, threaded end to end.**
`production_factory.dossier.make_production_id()` (unchanged formula) is now:
- computed by `orchestrator/engines/production.py` for the ladder-tagged path and sent as `production_id` in the payload to `book_generator.py`;
- accepted as an optional, purely additive parameter by `generate_product_package()` / `generate_book_from_content()`, stored in the generation's own log entry (`books/_generation_log.jsonl`) when given, omitted entirely (not defaulted) when not — every existing caller reproduces byte-identical output;
- preferred by `schemas/product.py`'s `Product.from_jsonl_record()` for `source_id` (`record.get("production_id") or record.get("timestamp")`) — a record generated before this field existed still falls back to the timestamp exactly as before.

The result: the dossier, the generated file's own log record, the `Product` object, the `publish_attempt` ledger event, and the Telegram Founder Report payload all carry the same string.

**Finance Ledger stage (new).**
`channels/ledger.py` gained `reconcile_ledger_to_finance()` — reads real `sale` events, extracts a real per-platform amount (Gumroad's `price` field; Paddle's `details.totals.grand_total` cents), and writes into `finance_data.json` using the exact same shape/atomic-write convention `server.js`'s `loadFin()`/`saveFin()` already use. Idempotent via a `source_ledger_key` field per sale — re-running never double-counts. An unrecognized platform sale shape is skipped and reported (`skipped_unrecognized`), never guessed at $0. Wired to fire automatically inside `scripts/poll_sales.py`'s existing `--json` CLI path — the same subprocess tick `POST /api/sales/poll` already runs every cycle, so a real sale is never invisible to the founder's actual revenue figure without any new scheduler or server.js change.

**Telegram Founder Report stage (new).**
`n8n_workflows/03_Production_Notify.prepared.json` previously only logged a received production event inside the n8n workflow run — it never told the founder. It now builds and sends a real Arabic Telegram message (same 3-node shape as the already-live `04_Telegram_Notify`: `Webhook` → `Set` → `HTTP Request` straight to Telegram's Bot API via `$env.TELEGRAM_BOT_TOKEN`/`$env.OPENCLAW_TELEGRAM_CHAT_ID`), including the real `production_id`, niche, recommended price, and pre-production check status.

## What was deliberately NOT changed

- **The legacy KDP book path (`generate_book()`, the non-ladder branch of `orchestrator/engines/production.py`) was left untouched** — its existing timestamp-based `source_id` is already real and unique; threading `production_id` through it too was not required by this phase's mission (real AI SaaS/B2B products via Paddle) and would have been optimization beyond what was asked.
- **No `custom_data`/passthrough was added to Paddle's own product/checkout API calls.** `production_id` traces through this codebase's own records (dossier → generation log → `Product.source_id` → ledger); it is not embedded inside Paddle's own transaction metadata. A real sale's platform-side identity is still the Paddle transaction ID, matched to the ledger by `channels/ledger.py`'s existing `(platform, raw_id)` dedup key — extending traceability into Paddle's own metadata is a real, separate future step, not done here.
- **Activating the two Telegram-capable n8n workflows in the live instance was not done.** Both `03_Production_Notify` and `04_Telegram_Notify` need a UI **Active** toggle — a confirmed n8n platform limitation (`--activeState=fromJson` fails outside queue/multi-main mode), and touching the live n8n database requires the founder's explicit go-ahead each time (this factory's standing governance around the one shared n8n instance), not a standing authorization.

## What was verified

- `tests/test_ledger.py` (new, 6 tests) — Finance Ledger reconciliation: real per-platform amount extraction, idempotent re-run, unrecognized-platform honesty, additive merge with existing `finance_data.json`.
- `tests/test_product_package.py` — extended with real-Groq-call tests for `ai_generate_techdoc_content()`/fallback, plus `production_id` threading (present when given, entirely absent when not).
- `tests/test_orchestrator.py` — extended with ladder-tagged production routing + `production_id` threading tests.
- `tests/test_schemas_product_techdoc.py` — extended with `source_id` preference (production_id over timestamp, with backward-compatible fallback).
- `tests/test_unified_pipeline_e2e.py` — new `TestFullProductGenerationPipelineEndToEnd`: one real, connected proof carrying a single real `production_id` through Market Intelligence → Opportunity Selection → Product Specification → AI Content Generation/Packaging/QA (book_generator.py's own Groq-costly subprocess mocked; the real content-generation call itself is separately proven live by `test_product_package.py`) → Metadata → the real, registered `PaddleArm` (`dry_run=True` — no real money spent in a test, this repo's standing rule) → Publishing Queue (real ledger write) → Finance Ledger (real reconciliation) → Telegram Founder Report (real `lib/n8n_notify.js` call via subprocess, no mocking).
- Full suite: 516 Python tests green, zero regressions. 137/138 JS tests green — the one failure (`sendDesktopNotification`) is a pre-existing, environment-only flake (real Windows toast notifications under the test runner's concurrent-file execution; passes 4/4 in isolation) in a file untouched by this phase.

## Impact

- `book_generator.py`: `ai_generate_techdoc_content()`, `_parse_sectioned_techdoc()`, `_fallback_techdoc_content()` (new); `generate_product_package()`/`generate_book_from_content()` gain optional `production_id`.
- `orchestrator/engines/production.py`: ladder-aware payload routing + `production_id` computation via `production_factory.dossier.make_production_id()`.
- `orchestrator/orchestrator.py`, `orchestrator/engines/decision.py`: `ladder` threaded through `run_cycle()`'s context (both already had `ladder`-adjacent plumbing from `ADR-076`; this phase completed the production-side half).
- `revenue_pipeline/plan.py`, `production_factory/dossier.py`, `revenue_pipeline/pipeline.py`: new `economics_platform` field, distinct from `recommended_platform`.
- `schemas/product.py`: `source_id` prefers `production_id`.
- `channels/ledger.py`: new `reconcile_ledger_to_finance()`.
- `scripts/poll_sales.py`: calls the new reconciliation on every tick; also now imports `channels.paddle_arm` (was missing — Paddle's real sales were never being polled by this script at all before this fix).
- `n8n_workflows/03_Production_Notify.prepared.json`: now sends a real Telegram message, not just a log entry.
- `PROJECT.md`, `OpenClaw_Brain/00_Governance/MASTER_BLUEPRINT.md`: updated with the final 11-stage architecture and pointers to this ADR.
- New/extended tests: `tests/test_ledger.py` (new), `tests/test_product_package.py`, `tests/test_orchestrator.py`, `tests/test_schemas_product_techdoc.py`, `tests/test_unified_pipeline_e2e.py`.
