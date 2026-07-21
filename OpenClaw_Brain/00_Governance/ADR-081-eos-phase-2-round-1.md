# ADR-081 — Enterprise Operating System, Phase 2, Round 1

**Date:** 2026-07-19
**Status:** Adopted. Round 1 of a multi-round rollout — Round 2/3 remain a documented roadmap, not built this round.

---

## Why this exists

Following Phase 1 (`ADR-080`), the founder's Phase 2 ask covered 12 sections: Mission Control V2 (15 named tabs), Golden Hunter/Pioneer evolution, a Research Department, an "AI Doctor" engineering-health system, Knowledge Graph v1, Department Health, an already-built AI Capability Registry, Autonomous Recommendations, ~30 named future-integration extension points, and Production Safety guarantees. Mandatory principles: preserve everything, no breaking changes, reuse before building, every capability integrates with Mission Control, every decision traceable, every autonomous action reversible, extend don't replace, document every decision.

Two research passes surfaced two load-bearing warnings that shaped this round directly:

1. **`quality_doctor.py` is confirmed still fake** (`CLAUDE.md` already documents its fabricated `fixes_applied` and bare `100 - len(issues)*15` health score, zero real callers besides its own disclosed endpoint). The new "AI Doctor" ask is exactly the kind of request that could repeat this mistake — so it doesn't: AI Doctor is built almost entirely from Phase 1's already-real signals, plus one genuinely new check that fails honestly rather than fabricating.
2. **"Researchers" is an existing, deliberate, founder-gated non-build** (`HIGH_VALUE_STRATEGY.md`: *"لم يُنفَّذ بحث فعلي اليوم — يحتاج طلباً صريحاً من الرئيس"*). The new "Research Department" ask is satisfied by assembling real analysis under named categories — the deep, per-product web research itself stays exactly as manual and founder-gated as it already was.

## What Round 1 built

- **`integration_registry.py`** — the ~30-vendor extension-point catalog, generalizing `ai_capability/registry.py`'s catalog+report pattern (confirmed the best fit over `channels/registry.py`'s live-arm-only registry and `tool_intelligence/proposals.py`'s recommendation-log shape). AI providers and commerce channels with a real registry are **referenced from it, never re-derived** — the anti-duplication rule this ADR treats as non-negotiable. n8n and Telegram are honestly `configured: True` (both real, live in this factory today); every other new-to-any-registry vendor uses a real env-var presence check only, never a live test-connection call.
- **`ai_doctor.py`** — combines `evolution_engine.build_evolution_report()` and `infrastructure_bridge.get_infrastructure_status()` (extracted from `mission_control_api.py` into its own shared module this round, so `ai_doctor.py` doesn't need to import the CLI dispatcher as a library) unchanged, plus one new, narrowly-scoped dependency-risk check: real `requirements.txt`/`package.json` pinning status (instant, static, no network) and a real `npm audit --json` attempt that surfaces its actual failure reason (this environment's registry mirror returns 404/NOT_IMPLEMENTED for the audit endpoint, confirmed directly) rather than a fabricated score. `pip`-based staleness checking was deliberately NOT attempted — a real, measured `pip list --outdated` call in this environment took ~54 seconds and checks the whole Python environment, not just this project's pinned dependencies, disproportionately slow and poorly scoped for a report section.
- **`research_department.py`** — 7 named categories, zero new analysis logic. Market/Competitor/Pricing/Publishing/Automation each reuse an already-real, already-cached signal (crucially: none of these trigger a fresh live network call — `analyze_customer_pain()`/`classify_demand_pattern()`/`get_or_refresh_competitors()` are all per-niche, live-capable functions that would either need a specific niche or risk an unwanted live call, so this module reads their already-saved real output instead). Technology and Customer research are honestly `Unknown`.
- **`department_health.py`** — pure assembly of already-computed real health signals per named department. Researchers and Customer Intelligence are honestly `data_source: "none"` — never a fabricated score for a department with nothing real behind it.
- **`revenue_pipeline/plan.py::estimate_pre_acceptance_roi()`** — the one real, missing Golden Hunter signal: ROI was only ever computed *after* acceptance. `estimate_production_cost()` already produces a real, usable-pre-production cost estimate, so combining it with `estimate_roi()` at scoring time needed no new profit formula. Surfaced as informational-only on the new Golden Hunter tab — never changes the real accept/reject gate.
- **`knowledge_graph/build.py`** — real nodes (`Niche`, `Decision`, `MarketAnalysis`, `ProductionRun`, `PublishChannel`, `AIProvider`) and edges from 4 real JSONL sources, no graph database (same "plain Python/JSON over new dependencies" choice `knowledge_brain.js` already made against embeddings). The `Decision→produced→ProductionRun` edge is real, not always approximate as originally planned: `production_factory/dossier.py::make_production_id()`'s `PROD-{decision_id}` convention gives an **exact** match whenever it holds; a best-effort niche-text match is the `approximate` fallback only when it doesn't. Live data today produces **zero** `produced`/`cost_incurred_from` edges — confirmed as an honest finding (the real sales ledger's entries are all legacy/test artifacts predating the modern pipeline; the real AI cost log's niches are this session's own test values, never matched to a real recorded decision), not a bug — verified by controlled-fixture tests proving the matching logic itself works correctly.
- **Daily Autonomous Recommendations cadence** — `factory_loop.js::maybeGenerateDailyEvolutionReport()`, same once-per-calendar-day file-existence gate as `maybeGenerateWeeklyReport()`, generating `reports/EVOLUTION_<date>.md` via `evolution_engine.build_evolution_report()`. No new scheduler.
- **6 new Mission Control tabs**: Golden Hunter, Pioneer, Research Department, AI Doctor, Knowledge Graph, Department Health — each verified live against a real running server instance with real authentication.

## Duplication avoided

- `ai_doctor.py` does not re-implement infrastructure/evolution logic — it imports both real modules unchanged. Extracting `infrastructure_bridge.py` out of `mission_control_api.py` was necessary specifically to avoid `ai_doctor.py` depending on the CLI dispatcher as a library.
- `integration_registry.py` references `ai_capability/registry.py` and `channels/registry.py` rather than re-deriving `configured` status for vendors they already cover.
- `department_health.py`'s `recent_activity_count()` (renamed from a private helper this round specifically because a second module, `golden_hunter_status()`, now needs it too) is the one shared window-counting utility, not reimplemented twice.
- `research_department.py`'s Automation category reuses `evolution_engine`'s bottleneck/ROI output directly rather than recomputing it.

## Deferred, documented (Track C)

Deep per-product founder-requested web research (unchanged, already a standing decision), Technology/Customer Research, architecture drift detection, deep error-log analysis, live test-connection checks for new integration-registry entries, autonomous execution of any recommendation engine's output, and a general rollback/undo mechanism for already-existing destructive actions (only pre-op snapshots + "reversible because non-destructive" exist today — a real, confirmed gap, but retrofitting true rollback for existing actions is a separate, larger undertaking than this round's new-capability scope). Full table with unblock conditions in the plan file / `COMPANY_INTEGRATION_MAP.md`.

## Tests

`tests/test_integration_registry.py` (7), `tests/test_ai_doctor.py` (10), `tests/test_research_department.py` (9), `tests/test_department_health.py` (7), `tests/test_knowledge_graph.py` (13), `tests/test_factory_loop_daily_evolution_report.js` (3), plus extensions to `tests/test_revenue_pipeline.py` (+3) and `tests/test_mission_control_api.py` (+2). Full suite green throughout (Python + JS). Every new service/tab verified live.

## Round 2/3 (documented roadmap, not built this round)

Round 2: Department Events (formalizing the existing JSONL-log pattern into a shared correlation index for the departments with the simplest, most isolated write points — Golden Hunter, Pioneer, AI Capability Manager, Recovery) + Unified Priorities view. Round 3: remaining department event emitters, Executive Decisions dashboard reframing, re-evaluate Track C items only if their unblock condition fires.
