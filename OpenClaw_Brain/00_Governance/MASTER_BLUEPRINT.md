# MASTER_BLUEPRINT.md — Engineering Skeleton, Opportunity → Founder Notification

**Date:** 2026-07-17
**Status:** Adopted (`ADR-065`).
**Scope:** Maps the one-cycle chain the mission asks to prove — Opportunity → Decision → Product → QA → Publish-ready package → Founder notification — onto real files that exist today, and what changes under the `MASTER_CHARTER.md` ladder.

This is a map of what runs, not a new system. Every box below is a real file already in this repo unless marked **(new, Step 4/5)**.

---

## 2026-07-18 update note (`ADR-077`, Product Generation Pipeline) — corrections and completion

This document predates several real changes since 2026-07-17 — read the sections below alongside, not instead of, the original blueprint:

- **§4 "Channels" is stale on two facts, corrected here:** `channels/gumroad_arm.py` was never archived (it is live in `channels/`, self-registers on import, used by the real Finance Ledger reconciliation this phase added). `channels/paddle_arm.py` is no longer skeleton-only — a real `PADDLE_API_KEY` exists (`ADR-074`), `PaddleArm.status()` returns `READY`, and it can create real products/prices/checkout transactions.
- **§1's chain now continues past "Notification"** — `ADR-077` closes the gap this blueprint's original scope stopped short of: `book_generator.py` (Packaging) → `inspectors.py` (QA) → `schemas/product.py` (Metadata) → `channels/paddle_arm.py` (Paddle Product Creation) → `channels/ledger.py` `record_publish_attempt()` (Publishing Queue) → `channels/ledger.reconcile_ledger_to_finance()` **(new)** → `finance_data.json` (Finance Ledger) → `03_Production_Notify.prepared.json`'s real Telegram-sending nodes **(new this phase — previously only logged the event, never told the founder)** → the founder's phone (Telegram Founder Report).
- **One identifier now threads the whole chain** (previously two disconnected IDs: the dossier's `production_id` and the generated file's own timestamp-based log identity). `production_factory/dossier.py`'s `make_production_id()` (`f"PROD-{decision_id}"`, unchanged formula) is now passed into `book_generator.py`'s generation call, stored in its log entry, and preferred by `schemas/product.py`'s `Product.source_id` — so the dossier, the generated PDF's own record, the publish-queue event, and the Telegram message all carry the same ID. See `ADR-077-product-generation-pipeline.md` for the full account.
- **Finance Ledger reconciliation is new** — before this phase, `channels/ledger.py` recorded real sales but nothing ever carried them into `finance_data.json` (confirmed gap, `COMPANY_INTEGRATION_AUDIT_20260718.md`). `reconcile_ledger_to_finance()` closes it, wired to fire on every `scripts/poll_sales.py` tick (the same tick `POST /api/sales/poll` already runs) — idempotent, never double-counts, never invents an amount for a sale shape it doesn't recognize.
- **Still a founder-gated manual step, not a code gap:** activating `03_Production_Notify` (now telegram-capable) and `04_Telegram_Notify` in the live n8n instance both require the UI **Active** toggle — confirmed platform limitation (`n8n import:workflow --activeState=fromJson` fails outside queue/multi-main mode), not an effort gap. See `n8n_workflows/README.md`.

---

## 1. The chain, stage by stage

```
Opportunity          Decision              Product               QA                    Publish package        Notification
------------         ------------          ------------          ------------          ------------------      -------------------
market_hunter.py      profit_oracle.py      book_generator.py     inspectors.py         channels/*_publisher.py lib/n8n_notify.js
  SEED_CATEGORIES  →   opportunity_score() →  (KDP track, live)  →  Dual Inspection   →   gumroad/etsy/payhip  →  n8n webhook →
  → GOLDEN_          MIN_OPPORTUNITY_        or new track          runQualityGate()      (+ paddle_arm.py       Telegram
    OPPORTUNITIES.    SCORE=65 gate           engine (Steps 4-5)                          new, Step 4)
    json              (factory_loop.js
                       huntGolden())
```

Real logs at each stage: `data/golden_hunter_events.jsonl` (opportunity discovery), `data/decisions.jsonl` (accept/reject with reason), `data/market_intelligence_analyses.jsonl` (AI CEO layer, `checkPendingAiCeoDecision()`), `finance_data.json` (post-sale). Nothing here invents a new log format — the ladder pivot changes *inputs and thresholds*, not the pipe itself.

## 2. What "Product" means per ladder rank

The pipeline's Decision → Product step currently has exactly one real engine: `book_engine` (`book_generator.py`, `cover_designer_v2.py`, `niche_validator_v2.py`). Per `PRINCIPAL_ARCHITECT_CHARTER.md`'s Open/Closed principle, new tracks get new engines beside it, not a rewrite:

| Rank | Track | Product engine today | Status |
|---|---|---|---|
| 1 | AI SaaS | none | Not built. First candidate must clear the opportunity gate before an engine is justified (§3, `MASTER_CHARTER.md` §4.3). |
| 2 | B2B Systems | none | Same as above. |
| 3 | Automation Tools | none | Same as above. |
| 4 | Reusable Assets | `book_generator.py` generalizes toward this (Step 4: technical-docs/product-package generator) | Partial — being extended, not replaced |
| 5 | Educational | `book_generator.py`'s existing `journal`/`planner`/etc. types already cover this loosely | Exists, unranked until now |
| 6 | KDP Books | `book_generator.py` (full pipeline, live, 4 products QA'd) | Fully built, deprioritized for *new* effort only |

**Consequence:** Steps 4–5 of this mission do not build a full AI-SaaS or B2B engine from scratch in one pass — that would repeat the exact "ceremony ahead of evidence" pattern `ADR-034` warns against, just relabeled as an engine instead of a department. Instead: `market_hunter.py` is retooled to *surface* real professional-business-problem opportunities (Step 4), and `book_generator.py` is generalized toward reusable technical-docs/product packages (Step 4) — both are extensions of what exists. A dedicated SaaS/B2B engine gets built the first time a real opportunity for one clears the gate, per `MASTER_CHARTER.md` §4.3.

## 3. Decision gate

`profit_oracle.py`'s `opportunity_score()` (`ADR-026`) is the single mandatory gate `factory_loop.js`'s `huntGolden()` calls before any brief is built. `ADR-065` (Step 2 of this mission) reweights it: recurring-revenue and reusability factors now dominate the formula, and a hard **$97 profit-potential floor** is enforced before the weighted score is even computed — see `ADR-065` §3 for the exact formula and `data/decisions.jsonl` rejection-reason analysis that motivated it.

## 4. Channels

| Channel | State |
|---|---|
| `channels/gumroad_arm.py` | Archived (Step 4) — moved to `channels/_archive/`, never deleted, never activated live (`GUMROAD_ACCESS_TOKEN` was always missing) |
| `channels/etsy_arm.py`, `channels/payhip_arm.py` | Unchanged |
| `channels/paddle_arm.py` **(new, Step 4)** | Skeleton only — `PADDLE_API_KEY` read from env, graceful "not configured" state per the fail-safe-on-missing-secrets principle, same `BaseArm` contract as the others |

## 5. Notification

`lib/n8n_notify.js` (`notifyN8nProductionEvent`, `ADR-061`) already fire-and-forget POSTs a production dossier to `N8N_PRODUCTION_WEBHOOK_URL` if set. Step 3(a) of this mission wires a Telegram-specific prepared workflow on the n8n side and confirms the founder can see a real message land — n8n itself is login-blocked for this session (`project_n8n_credentials_blocker_20260715` memory), so activation is a manual step handed to the founder, not something built silently around the blocker.

## 6. What doesn't change

Product schema (`schemas/product.py`), `sales_ledger.jsonl` format, `BaseArm` contract, `dry_run` defaults, and the single-Google-account identity constraint are all untouched by this blueprint. This is a reprioritization and two new/extended components (`paddle_arm.py`, generalized `book_generator.py`, retooled `market_hunter.py`), not an architecture rewrite.
