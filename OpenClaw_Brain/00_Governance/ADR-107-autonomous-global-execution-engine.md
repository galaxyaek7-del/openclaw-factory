# ADR-107 — Autonomous Global Execution Engine (Execution Status, Scheduler, Resource Allocation, Mission Control Unification)

**Date:** 2026-07-23
**Status:** Adopted.

---

## The directive

"Transform OpenClaw from an intelligent factory into a continuously operating autonomous company... every verified opportunity must be capable of moving through the complete company lifecycle with minimal human intervention... the factory must execute, the founder supervises." A full 15-stage execution chain, real per-opportunity Execution Status (phase, owner, completion %, blocking issue, business value, estimated revenue/effort, confidence, priority, expected completion), an autonomous scheduler that continuously decides what runs/waits/stops/accelerates/cancels, continuous multi-model resource allocation across 9 named task categories, and Mission Control as the single operational window.

## Scope alignment (confirmed with the founder before building)

This mission runs directly into two things this factory's own architecture and this session's own prior audit had already settled:

1. **CLAUDE.md's own architecture doc is explicit**: *"Nothing in this repo runs anything on a timer... it only runs when invoked manually."* A "continuously operating" scheduler is a literal architectural change, not an extension.
2. **`factory_orchestrator.run_master_cycle()`'s own real verdict is advisory-only by deliberate design** (confirmed in the 2026-07-23 system integration audit, roadmap item #6, explicitly flagged there as a founder policy decision, not a build task) — production spend and publishing to real Paddle/Gumroad listings do not happen without a human (or `enforce_board=true`) today.

Confirmed via AskUserQuestion before any code was written:
1. **Scheduler mode**: on-demand only — real decision logic exposed as a Mission Control action/function, no standing live process. No architectural change to CLAUDE.md's "no scheduler exists" fact.
2. **Autonomy boundary**: analysis/decision stages (Market Intelligence → Opportunity Queue → Executive Board → Investment Decision → Research) can run and re-rank continuously with zero real-world risk; Production (real Groq spend) and Publishing (real live listings) stay human-confirmed, exactly matching `run_master_cycle()`'s existing advisory-only design. Nothing in this ADR changes that gate.

## What was built

**`execution_status.py` (new)** — `build_execution_status(niche)` / `build_execution_status_report()`. Pure aggregation, zero new computation: reuses `value_engine.compute_value_profile()` for lifecycle stage, at-risk flag, and board summary (Priority Score, Strategic Value, cost/lifetime-value estimates), and `opportunity_pipeline.annotate_decision()` for the real `confidence` field already recorded on the decision. `current_owner` is a real, static mapping from each of the 10 real lifecycle stages (ADR-105) to the real subsystem that owns it — the 4 stages with no real capability in this factory today (customer testing, localization, global expansion, long-term maintenance) honestly report no owner, never a fabricated one. `expected_completion` is always honest `Unknown` — no historical per-stage duration tracking exists anywhere in this factory to compute a real estimate from, and inventing one would be exactly the fabrication this whole engagement refuses.

**`scheduler.py` (new)** — `decide_next_actions()`, the real, on-demand, evidence-gated 5-bucket classifier the directive asked for (run_now / wait / accelerate / stop / cancel). Every bucket has one explicit, documented rule, never a black-box "AI decides": `cancel` for a real REJECTED decision or a real Executive Board NOT_APPROVED verdict; `stop` for an at-risk flag from any other cause (an active Critical/High market alert, a negative real decision re-open) — a temporary signal, not a permanent verdict; `accelerate` for `market_memory.recommend_actions()`'s real, evidence-gated `increase_investment` recommendation; `run_now` for the single highest real-Priority-Score clean opportunity; `wait` for everything else real and accepted with no active signal. Does not execute anything itself — it is a real decision surface a human or an external trigger (Mission Control action, n8n) invokes.

**Resource allocation — `ai_capability/orchestrator.py`** gained `RESOURCE_ALLOCATION_TASK_TYPES` (the 9 named categories: research, writing, coding, design, video, translation, analysis, localization, customer_support) and `resource_allocation_status()` — a real, zero-cost, read-only view of which real provider `select_provider()` currently resolves each category to. No new dispatch logic was needed: `select_provider()`/`generate()` already dispatch on any `task_type` string generically (ADR-104); this just gives the 9 founder-named categories a canonical vocabulary so real future usage data accumulates under consistent labels. Honest by construction — with exactly one real, credentialed provider today, every category resolves to `"groq"` via the same real fallback path used everywhere else, not a hardcoded binding.

**Mission Control unification — `mission_control_api.py::_get_global_execution_view()`** (new action, `get-global-execution-view`) assembles execution status, scheduler buckets, revenue (`_revenue()`, reused verbatim), production (`_production()`, reused verbatim), market learning (`market_memory.monthly_evolution_report()`), commercial recommendations, and AI utilization (`ai_capability.registry.list_providers()` + `resource_allocation_status()`) into one payload — every field sourced from an already-real, already-tested function, zero new computation. `server.js`'s registry entry merges in the real, already-live `computeHealthStatus()` synchronously. Health and Security are deliberately **not** re-derived here — `GET /health` and the existing `risk-intelligence-scan`/`enterprise-readiness-gate` actions remain the real views for those; duplicating them would be exactly the second-competing-computation pattern this factory's own discipline refuses.

## Verification

25 new tests (`tests/test_execution_status.py` — 9, `tests/test_scheduler.py` — 7, `tests/test_ai_orchestrator.py` — 3 new, `tests/test_mission_control_api.py` — 2 new). Full regression: highest-risk suites first (execution_status, scheduler, ai_orchestrator, mission_control_api, value_engine, ai_capability, market_memory, decision_engine — 200 tests), then the full repository (Python + Node), then the API contract test (23/23) to confirm the new server.js action registers correctly.

## What's deliberately not built

- **No live scheduler process.** Confirmed via AskUserQuestion — on-demand only, matching CLAUDE.md's current architecture exactly.
- **No autonomous production/publishing execution.** Every stage that spends real money or touches a real external platform keeps its existing human-confirmation gate; this ADR adds visibility and evidence-based recommendation, never autonomous action on either.
- **No new AI provider integrations.** `resource_allocation_status()` reports real selection for 9 named categories using the exact same one real provider (Groq) every other real call site in this factory uses — adding real second-provider credentials remains out of scope, unchanged from ADR-104.
- **No re-derivation of Health/Security.** Referenced from their existing real sources, not recomputed.
