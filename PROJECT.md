# PROJECT.md — OpenClaw Factory, Current State

**Last updated:** 2026-07-22 (Opportunity Intelligence Round 2). **This is a pointer document, not a duplicate** — it orients a new reader to where the real, living state actually lives, and states the current one-paragraph truth. Don't hand-maintain the details here; update the documents it points to instead.

**Opportunity Intelligence Round 2, 2026-07-22**: a real, ranked Opportunity Pipeline (`opportunity_pipeline.py`, Mission Control's `opportunity-pipeline` service/tab) — every currently-scored opportunity annotated with 10 real fields (market size, customer type, pain level, competition, price, recurring revenue, technical complexity, time to MVP, defensibility, global scalability), real data where it exists, honestly `Unknown` where it doesn't (no real TAM or dev-time-estimation model exists anywhere in this factory). Product Laboratory = decisions already `ACCEPTED` by the real existing gate; no new invented threshold. Found and fixed 2 real "computed then silently discarded" bugs on the way: `decision_engine/engine.py::record_ladder_decision()` and `market_intelligence_engine.py::analyze_opportunity()` both computed `defensibility` (and the ladder path also `risk`/`confidence`) but never persisted them. Real, honest finding surfaced by the pipeline itself: **zero opportunities are currently `ACCEPTED`** in `data/decisions.jsonl` (42 unique niches, all `DEFERRED`/`REJECTED`) — Product Laboratory is empty today, not a bug in the new code.

**Strategic Phase, 2026-07-19** (`COMPANY_INTEGRATION_MAP.md`): the factory is now a single, continuously-operable company, not two disconnected dispatch paths. `orchestrator.run_cycle()` gained a real, gated CLI trigger that `factory_loop.js`'s existing tick can call for a ladder-tagged golden opportunity — reusing the already-documented `FACTORY_AUTO_PRODUCE` safety gate, no new review process — and a real safeguard (`existing_decision=`) that makes this safe: it reuses the decision Golden Hunter already recorded instead of re-evaluating it, so it can never record a second decision (and therefore a second `production_id`) for the same real opportunity. Also shipped: **Pioneer** (`golden_hunter/pioneer.py`), real novel-candidate discovery upstream of Golden Hunter's fixed seed list; Mission Control's new Commercial Execution tab (approval gates + Product Definition Registry visibility, both previously invisible); and an honest resolution of `quality_doctor.py`'s fabricated QA endpoint.

**Autonomous Digital Company v1, 2026-07-19** (`COMPANY_INTEGRATION_MAP.md`'s own dedicated section): connected `executive_intelligence`/`strategic_intelligence`'s real reports into the executive report and the weekly cadence; shipped real Infrastructure Intelligence (CPU/memory/disk + a real AI cost-rate trend, now including real per-call latency); a real AI Capability Registry (`ai_capability/`) comparing named providers on measurable metrics only — Groq is the one real, measured entry, every other provider (Claude/GPT/Gemini/Grok/DeepSeek/Qwen/Mistral/local) is honestly unmeasured until a credential exists; and real, evidence-cited software/AI-tool integration proposals (`tool_intelligence/`, "(مقترَح، لا تنفيذ)"). Mission Control gained three new tabs (Infrastructure, AI Models, Strategic Recommendations). Customer Intelligence and sales-based forecasting were deliberately deferred, documented, not silently dropped — this factory still has zero real customers and zero real sales.

**Enterprise Operating System, Phase 1, 2026-07-19** (`ADR-080`, `COMPANY_INTEGRATION_MAP.md`'s "Enterprise Operating System" section): the Continuous Improvement Engine's weekly executive report is now 6/6 reviews (added AI, Infrastructure, and a new Market Review — the last one reusing `strategic_intelligence`'s rejection-pattern analysis verbatim, not reimplemented). A new Company Evolution Engine combines bottleneck/tech-debt/ROI/tool-proposal signals with a new capability-gap scanner. A new Founder Console is the one Mission Control tab framed as "you need to decide something" — everything else stays informational.

**Enterprise Operating System, Phase 2 Round 1, 2026-07-19** (`ADR-081`): a real, adapter-based Integration Registry (~30 named future vendors, referencing not duplicating `ai_capability`/`channels` registries); `ai_doctor.py` — the real, non-fabricated replacement for `quality_doctor.py`'s confirmed-fake pattern; a Research Department assembling real analysis under 7 named categories; Department Health per named department; a real pre-acceptance ROI signal for Golden Hunter; Knowledge Graph v1 (real nodes/edges, honest `exact`/`approximate` edge confidence); a daily Autonomous Recommendations cadence; 6 new Mission Control tabs. Round 2/3 (Department Events, Unified Priorities view) remain a documented roadmap, not yet built.

**Enterprise Operating System, Phase 2 Round 2, 2026-07-19** (`ADR-082`): closed a real production-safety asymmetry — `FACTORY_LIVE_PUBLISH` now actually gates the modern ladder pipeline's real publish attempts, restoring the founder's own pre-existing "three independent barriers" design (`AUTO_PRODUCE_ACTIVATION_CHECKLIST.md`, `ADR-009` §9.2). Shipped Department Events (`data/department_events.jsonl`, an envelope-only correlation index wired at Golden Hunter/Recovery/AI Capability Manager's real existing write points — a test-isolation gap found and fixed mid-round), the Unified Priorities Engine (Next Dollar Actions + ranked opportunity queue + `MASTER_CHARTER.md`'s Priority Ladder shown side by side, never merged into one score — closing Opportunity Intelligence's real 4-tabs gap), and a real revenue trend over time in the existing Revenue tab (`channels/ledger.py::revenue_trend()` — honestly zero today, no real sales yet). Research found Commercial Intelligence and Evolution Engine already complete; no rebuild.

**Strategic Phase 3, Round 1, 2026-07-22** (`STRATEGIC_PHASE_3.md`, `ADR-083`): the founder's newest mission reframe — infrastructure-building is over, primary mission is now discovering/creating rare, high-value, hard-to-copy digital businesses. Research found this philosophy already 9 days old (`ELITE_ASSET_DOCTRINE.md`, 2026-07-13) and much of the named "Opportunity Intelligence Engine" already built (`multi_source_intelligence/`, `ADR-059`) — no rebuild. Shipped: a real `defensibility` scoring signal from `competitor_discovery.py`'s cached data (Golden Hunter Evolution); `decision_path` transparency in Mission Control, surfacing that today's automatic accept path is honestly single-signal while the deliberate path is multi-signal (Market Validation); a real `arxiv` connector, `multi_source_intelligence`'s 11th source (Opportunity Intelligence Engine); a founder-triggered "Go Deep" evidence action combining 3 real independent signals for one opportunity (Market Validation); and a real per-ladder product-concept comparison tool using existing scoring/ROI functions, never auto-selecting a winner (Product Laboratory). Continuous Evolution's real feedback loop stays deferred — zero real sales/feedback channel still exist. Round 2/3 (deeper Opportunity Intelligence wiring, real AI SaaS/B2B software adapters) remain a documented roadmap.

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

## The Universal Production Engine (`UNIVERSAL_PRODUCTION_ENGINE.md`) + Commercial Execution Layer (`COMMERCIAL_EXECUTION.md`)

As of 2026-07-19 (Roadmap Step 3), a Product Definition Registry (`product_families/manifest.py`) replaces family-specific routing: 3 families (`automation_systems`, `professional_templates`, `digital_toolkits`) are pure `ProductManifest` configuration with zero bespoke adapter code, and a brand-new family that reuses existing generators needs only one manifest to work — proven with a throwaway demo family, not just asserted. Roadmap Step 4 (same day) unified the publish side into one Commercial Execution Layer: publishing now respects a family's manifest-declared marketplaces (`commercial_execution/pipeline.py`), every publish produces one explicit, auditable `PublishRecord`, and a real, computed founder-approval-gate view (`commercial_execution/approval_gates.py`) shows exactly which marketplaces are autonomous vs. need founder action right now. See `UNIVERSAL_PRODUCTION_ENGINE.md` and `COMMERCIAL_EXECUTION.md` for the full architecture and integration/recovery evidence.

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
| How does a generated product actually get published, tracked, and recovered — and what needs founder action first? | `COMMERCIAL_EXECUTION.md` |
| Is every subsystem actually connected end-to-end, and what's the real remaining gap list? | `COMPANY_INTEGRATION_MAP.md` |
| Is every stage (discovery → sale → reporting) actually connected, and what's the shortest path to full autonomy? | `OpenClaw_Brain/00_Governance/COMPANY_INTEGRATION_AUDIT_20260718.md` |
| How does the company mechanically operate, stage by stage? | `COMPANY_OPERATING_MODEL.md` (+ 2026-07-18 update note) |
| What capabilities exist, what's missing, what's the dependency graph? | `CAPABILITY_MAP.md` (+ 2026-07-18 update note) |
| What's blocked on the founder specifically, right now? | `BLOCKERS.md` |
| Why was a specific technical decision made? | `OpenClaw_Brain/00_Governance/ADR-*.md` (74+ and counting — no index yet, a known small gap) |
| What can I do without asking first? | `OpenClaw_Brain/00_Governance/PRINCIPAL_ARCHITECT_CHARTER.md` §1, §5 (Protected Right to Object) |

## Rule for future sessions maintaining this file

Don't restate detail that already lives in one of the documents above — if you're tempted to write more than a sentence about something, that sentence belongs in the specific document, with a pointer added here if the pointer table above doesn't already cover it. This file's only job is: orient a reader in under two minutes, then send them to the real source.
