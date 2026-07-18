# PROJECT.md — OpenClaw Factory, Current State

**Last updated:** 2026-07-18. **This is a pointer document, not a duplicate** — it orients a new reader to where the real, living state actually lives, and states the current one-paragraph truth. Don't hand-maintain the details here; update the documents it points to instead.

## What this is

OpenClaw Factory is an AI-first digital-product company: a real, automated pipeline (opportunity discovery → decision → product generation → QA → distribution → revenue tracking → notification) with a human founder overseeing it, not running it by hand. See `CLAUDE.md` for the technical stack and `OpenClaw_Brain/00_Governance/PRINCIPAL_ARCHITECT_CHARTER.md` for how engineering decisions get made here.

## Current priorities (governing document)

`OpenClaw_Brain/00_Governance/MASTER_CHARTER.md` — the Strategic Production Priority Ladder: **AI SaaS > B2B Systems > Automation Tools > Reusable Assets > Educational > KDP Books (last, supporting only)**. Adopted 2026-07-17 (`ADR-065`), a deliberate reversal of the earlier "books first" era — see that ADR for why, and `MASTER_BLUEPRINT.md` for how the ladder maps onto real code.

## The one-paragraph current truth

The automated pipeline fired end-to-end for the first time in this company's history on 2026-07-17/18: a real opportunity was discovered, scored, accepted, produced as a real technical-docs product, quality-checked, and reached a real distribution attempt — with zero manual intervention beyond starting the process. Telegram notifications are live (in Arabic, per the founder's own instruction). A real, approved Paddle account can create real products and prices; the last mile (a working checkout link) is blocked by Paddle's own account-onboarding step, not by this codebase. **As of 2026-07-18, there is one single source of truth for every accepted opportunity** (`data/decisions.jsonl`, unified across every decision surface — see below); no real dollar has been earned yet. See `OpenClaw_Brain/00_Governance/ENGINEERING_ASSESSMENT_20260718.md` for the full, current, evidence-based picture — architecture, strengths, and prioritized gaps — and `COMPANY_OPERATING_MODEL.md` / `CAPABILITY_MAP.md` for the mechanics (both carry 2026-07-18 update notes reconciling them with the ladder pivot).

## The Product Generation Pipeline (final architecture, `ADR-077`)

As of 2026-07-18, every stage from a discovered opportunity to the founder's own phone is real code, connected, structured-JSON in/out at every boundary, and proven together by one end-to-end test (`tests/test_unified_pipeline_e2e.py`'s `TestFullProductGenerationPipelineEndToEnd`):

```
Market Intelligence → Opportunity Selection → Product Specification (dossier,
production_id = f"PROD-{decision_id}") → AI Content Generation (real Groq,
honest fallback) → Packaging (book_generator.py) → QA (inspectors.py Dual
Inspection) → Metadata (schemas/product.py, source_id = production_id) →
Paddle Product Creation (channels/paddle_arm.py, real account) →
Publishing Queue (channels/ledger.py publish_attempt events) →
Finance Ledger (channels/ledger.reconcile_ledger_to_finance() →
finance_data.json) → Telegram Founder Report (n8n → Telegram, Arabic)
```

The same `production_id`, computed once by `production_factory/dossier.py`'s `make_production_id()`, now threads through every one of those stages (previously, the generated file's own log identity and the dossier's identity were two disconnected IDs — closed this phase). See `OpenClaw_Brain/00_Governance/ADR-077-product-generation-pipeline.md` for the full account of what was built, what's mocked in tests and why (real Groq/Paddle cost is never spent on a routine test run), and what's still a founder-gated manual step (activating the two remaining n8n workflows).

## The Universal Production Engine (`UNIVERSAL_PRODUCTION_ENGINE.md`)

As of 2026-07-18 (Roadmap Step 2), `automation_systems` is the first product family built end-to-end on the new swappable Content Generation / Asset Generation / Packaging / Dossier Bundle registries — the reference template every future family (Prompt Libraries, SaaS, Templates, etc.) now follows by configuration, not a rewrite. See `UNIVERSAL_PRODUCTION_ENGINE.md` for the full architecture, what's real vs. still a template, and the integration evidence.

## The unified decision pipeline (final architecture, `ADR-076`)

Before 2026-07-18, two real decision-making surfaces silently disagreed (`ENGINEERING_ASSESSMENT_20260718.md`'s Critical Issue C1). **This is now closed.** One scoring function, one recording function, one file:

```
                    profit_oracle.ladder_opportunity_score()   <- the ONE scoring function
                              │            │
              ┌───────────────┘            └───────────────┐
              ▼                                             ▼
  market_hunter.py (Golden Hunter,               decision_engine/engine.py
  discovery-time, every real candidate,          (manual/deliberate review,
  accepted or not)                               adds a real AI-CEO verdict
              │                                  on top of the same score)
              ▼                                             │
   decision_engine.engine.record_ladder_decision() ◄────────┘
              │
              ▼
   data/decisions.jsonl   ← THE single source of truth for every accepted
              │              (or rejected) opportunity, regardless of
              │              which path produced it (see each record's
              │              own "decision_path" field: "ladder_fast_gate"
              │              or "ai_ceo_full_evaluation")
              │
    ┌─────────┼─────────────────────────────┐
    ▼         ▼                             ▼
Mission    factory_loop.js's huntGolden()   (any future reader —
Control    (re-validates the SAME real      one file, one shape,
(reads      gate before production;         no second source to
this file   does not need to re-write,      keep in sync)
directly,   since market_hunter already
unchanged   recorded it moments earlier
by this     in the same daily cycle)
ADR)              │
                   ▼
        n8n → Telegram (Arabic) + the production brief
        Paddle's price ultimately comes from — both read
        the SAME real ladder_score/price, never a second
        derivation
```

**Verified live** (`tests/test_unified_pipeline_e2e.py`, 5 stages, zero mocking of the scoring itself): one real discovered opportunity produces the identical score, price, and ladder rank at every single stage above — Golden Hunter, the single-source-of-truth store, Mission Control's real read path, factory_loop's automatic gate, and the notification/production-brief payloads.

## Where to look for what

| Question | Document |
|---|---|
| What are we prioritizing and why? | `OpenClaw_Brain/00_Governance/MASTER_CHARTER.md` |
| How does the pipeline actually work, file by file? | `OpenClaw_Brain/00_Governance/MASTER_BLUEPRINT.md` |
| What's the current architecture, what's strong, what's broken, in priority order? | `OpenClaw_Brain/00_Governance/ENGINEERING_ASSESSMENT_20260718.md` (this review) |
| How was the decision-surface duplication actually fixed? | `OpenClaw_Brain/00_Governance/ADR-076-decision-surface-reconciliation.md` |
| How does a product go from ACCEPTED decision to a Telegram message in the founder's pocket? | `OpenClaw_Brain/00_Governance/ADR-077-product-generation-pipeline.md` |
| What happens if the power/internet goes out mid-cycle — does it lose work or double-publish? | `DISASTER_RECOVERY_PLAN.md`'s "Unified Recovery System (2026-07-18)" section |
| How does a product family actually get built, and what does a future family need to add? | `UNIVERSAL_PRODUCTION_ENGINE.md` |
| Is every stage (discovery → sale → reporting) actually connected, and what's the shortest path to full autonomy? | `OpenClaw_Brain/00_Governance/COMPANY_INTEGRATION_AUDIT_20260718.md` |
| How does the company mechanically operate, stage by stage? | `COMPANY_OPERATING_MODEL.md` (+ 2026-07-18 update note) |
| What capabilities exist, what's missing, what's the dependency graph? | `CAPABILITY_MAP.md` (+ 2026-07-18 update note) |
| What's blocked on the founder specifically, right now? | `BLOCKERS.md` |
| Why was a specific technical decision made? | `OpenClaw_Brain/00_Governance/ADR-*.md` (74+ and counting — no index yet, a known small gap) |
| What can I do without asking first? | `OpenClaw_Brain/00_Governance/PRINCIPAL_ARCHITECT_CHARTER.md` §1, §5 (Protected Right to Object) |

## Rule for future sessions maintaining this file

Don't restate detail that already lives in one of the documents above — if you're tempted to write more than a sentence about something, that sentence belongs in the specific document, with a pointer added here if the pointer table above doesn't already cover it. This file's only job is: orient a reader in under two minutes, then send them to the real source.
