# ADR-080 — Enterprise Operating System, Phase 1

**Date:** 2026-07-19
**Status:** Adopted. Phase 1 of a 3-phase rollout (`OpenClaw_Brain/00_Governance/COMPANY_INTEGRATION_MAP.md`'s "Enterprise Operating System" section has the full plan; Phase 2/3 are documented roadmap, not yet built).

---

## Why this exists

The founder asked for 8 layers turning the factory into a *continuously operating company*, explicitly instructing: don't add isolated features, design first, reuse existing architecture, avoid duplication, document every decision. Research (three parallel passes plus a design-validation pass, all against the real repo) found the same pattern as every prior milestone this session: most of what's asked for already exists as real, tested code — just not assembled into one view. A few sub-asks would require fabricating signals this factory doesn't have. Same Track A (wire up) / Track B (build small, honest) / Track C (defer, documented) discipline as the prior "Autonomous Digital Company v1" milestone.

## What Phase 1 built

**Continuous Improvement Engine, now 6/6 weekly reviews** (the founder's Layer 4): `mission_control_api.py::_build_combined_executive_report_markdown()` already assembled Financial (`revenue_pipeline`) + Risk/Architecture-adjacent (`strategic_intelligence`) + Validation. This phase adds the remaining 3:
- **AI**: `ai_capability/registry.py::list_providers()` + a new `render_markdown()` (real provider stats, never fabricated for unconfigured providers — same DISCOVERY-level honesty as before).
- **Infrastructure**: `lib/infrastructure_intelligence.js::getInfrastructureStatus()`, bridged into the Python combiner via a new CLI entry point (`node lib/infrastructure_intelligence.js`) — the first Python-spawns-JS call in this codebase (every other cross-language call goes the other way). Chosen deliberately over reimplementing CPU/memory/disk logic in Python a second time; fails open (honest "couldn't fetch" message) on any subprocess error, never blocking the rest of the report.
- **Market**: new `market_intelligence_core/market_review.py::generate_market_review()` — the one genuinely missing review. Pure aggregation over already-logged history (niches scanned from `data/golden_hunter_events.jsonl`, opportunity-gap/pain-score trend from `data/market_intelligence_analyses.jsonl`) plus a direct reuse of `strategic_intelligence/rejection_patterns.py::most_frequent_rejection_reasons()` for "top rejection reasons" — not reimplemented, since that function already answers exactly this question honestly (categorical `ai_ceo_decision` tally, not free-text clustering).

All three feed the same one combiner used by both the on-demand "Export Executive Report" button and `factory_loop.js`'s weekly cadence — no second wiring point, continuing the precedent that function already established.

**Company Evolution Engine** (Layer 7): new `evolution_engine.py::build_evolution_report()` combines four already-real signals (bottleneck detection, technical debt, high-ROI ranking from `revenue_pipeline`'s real per-opportunity `expected_roi`, tool-integration proposals) with one genuinely new, narrowly-scoped detector: `capability_registry_scanner.py::find_capability_gaps()` — flags every `config/capability_registry.json` entry not yet `REAL`. Deliberately no staleness/age filter: the registry has no per-entry timestamp, and inventing one would fabricate a signal the data doesn't support. Duplicate-work detection beyond the existing `scripts/check_jsonl_duplication.js` was explicitly NOT built — general logic-duplication detection needs AST/semantic analysis, real new capability with real false-positive risk, better justified by a second concrete incident than built speculatively.

**Founder Console** (Layer 8): new `founder_console.py::build_founder_queue_partial()` (blocked channels via `commercial_execution/approval_gates.py`, DEFERRED decisions via `decision_engine/store.py::latest_decision_per_niche()`) merged in `server.js::founderConsoleService()` with two already-real JS-native reads (`lib/dashboard_data.js::readAttentionFlag()/readReviewFlag()`, written by `factory_loop.js`'s real state-transition checks) and a new `BLOCKERS.md` read (same markdown-scrape technique `readNextDollarActions()` already uses on `FACTORY_STATUS.md`). Framed explicitly as "the only tab that means you need to decide something" — every other Mission Control tab stays informational, per the founder's own instruction.

**Trivial**: `system-configuration` (already a registered service, no tab) got a Mission Control tab — everything backing it already existed.

## Duplication risks addressed

- Market Review reuses `rejection_patterns.py` verbatim rather than re-tallying rejection reasons a second way.
- Infrastructure reuses the real JS function via subprocess rather than reimplementing CPU/memory/disk checks in Python.
- High-ROI ranking reuses `revenue_pipeline.pipeline.run_revenue_pipeline()`'s already-computed `expected_roi` per opportunity rather than a second ROI formula.
- AI/Infrastructure/Market/Evolution/Founder-Console all converge on their respective single combiner functions rather than each inventing a new report entry point.

## Deferred, documented (Track C — see `COMPANY_INTEGRATION_MAP.md` for the full table)

Customer knowledge (zero real customers), dynamic OKR auto-generation (the founder's ladder stays hand-owned business strategy), autonomous execution of Evolution Engine recommendations (every autonomous action in this factory is operational, never architectural — `tool_intelligence`'s proposal-only boundary stays intact), a general-purpose pub/sub event bus (Phase 2's formalized JSONL envelope delivers the real ask without a new live-coupling failure mode), general duplicate-work detection beyond the one existing CI check, and risk-tiering beyond `ACTION_REGISTRY`'s `reversible` field — each with a specific unblock condition, not silently dropped.

## Tests

`tests/test_ai_capability.py` (+3, `render_markdown`), `tests/test_mission_control_api.py` (+7: infrastructure bridge honest-failure/real-shape cases, combined-report section assertions), `tests/test_market_review.py` (7, new), `tests/test_capability_registry_scanner.py` (4, new), `tests/test_evolution_engine.py` (5, new), `tests/test_founder_console.py` (3, new). Full suite green throughout (Python + JS). Every new Mission Control service/tab verified live against a real running server instance with real authentication.

## Phase 2/3 (documented roadmap, not built this phase)

Phase 2: Department Events (formalizing the existing JSONL-log pattern into a shared correlation index — NOT a pub/sub bus, see `COMPANY_INTEGRATION_MAP.md`) starting with the 4 simplest departments; Department Health rollup; Unified Priorities view; Knowledge Graph v1. Phase 3: remaining department event emitters; Executive Decisions dashboard reframing; re-evaluate Track C items only if their unblock condition fires.
