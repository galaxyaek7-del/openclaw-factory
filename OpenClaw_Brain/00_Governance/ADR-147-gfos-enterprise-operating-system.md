# ADR-147 — GF-OS: Galaxy Forge Enterprise Operating System

**Date:** 2026-07-30
**Status:** Adopted.

---

## The directive

"EXECUTIVE DIRECTIVE — GALAXY FORGE ENTERPRISE OPERATING SYSTEM (GF-OS)." A permanent operating layer above every subsystem: "Every department must communicate only through GF-OS. No department operates independently." Departments register Identity/Responsibilities/Capabilities/Dependencies/Current workload/Health/Performance/Confidence. A Global Mission Queue every AI department pulls work from, "no duplicated execution, no conflicting execution." An 8-stage mission lifecycle (Created→Validated→Scheduled→Executing→Waiting→Completed→Measured→Archived). An Enterprise Timeline where "nothing is lost." 8 continuously-measured dimensions. Pre-mission verification across 7 criteria.

## Two real conflicts, surfaced via `AskUserQuestion` before any code was written

1. **"No department operates independently"** reads as mandatory single-gateway routing — every one of this factory's ~60 top-level modules would have to stop calling each other directly. This would have to formally supersede a founder-authored design principle from the day before, quoted verbatim in `safe_mode.py`'s own docstring (Global Trust & Resilience Layer, ADR-135, 2026-07-29): *"stop only the affected subsystem, keep the rest running, never allow cascading failures."* A mandatory gateway is architecturally the opposite of deliberate per-subsystem independence.

2. **"Global Mission Queue — every AI department pulls work from it"** implies new, always-on, pull-based worker infrastructure. This exact question — should Galaxy Forge operate as a centralized, always-on autonomous operating system — has been asked and explicitly declined at least four times before today: ADR-107 (`AskUserQuestion`, "on-demand only... matches CLAUDE.md's current architecture exactly"), **ADR-110 ("Global Autonomous Business Operating System," 2026-07-24 — nearly this exact directive under a different name six days earlier**, which itself re-declined the same "repeat forever" ask citing ADR-107), ADR-115, and ADR-142 (`master_loop.py`'s always-on-daemon proposal, reaffirmed as recently as the day before this one). This factory has zero real message-queue/worker-pool infrastructure today (`lib/health_checks.js`'s own real, permanent `not_applicable` classification, confirmed repeatedly this session).

**The founder's answers, both matching the recommended option**: GF-OS is a coordination/citation layer, not a mandatory gateway — Safe Mode's independence stays untouched. The "Mission Queue" is a real citation of already-real scheduling/orchestration infrastructure — no new queue infrastructure is built.

## What research found already real, before any code was written

Virtually every named GF-OS responsibility already maps to a real, built module: Company orchestration → `orchestrator/orchestrator.py` (the real, live, dependency-inverted production-cycle coordinator, ADR-051). Executive planning → `executive_brain.py` (ADR-144, the day before). Resource allocation → `capital_allocation_engine.py`. Mission scheduling → `scheduler.py`. Conflict resolution → `executive_decision_memory.py`'s `detect_conflicts()` (ADR-145, the day before). Knowledge synchronization → `knowledge_graph/`. Global monitoring → `resilience_monitor.py`. Continuous optimization/company evolution → `evolution_queue.py` (ADR-133/143). The 8 named continuously-measured dimensions → `executive_score.py`'s real sub-scores. "Mission Control as the visual interface" → literally the round immediately before this one (ADR-146). Pre-mission verification (strategic alignment/business value/technical feasibility/risk/ROI) → `executive_quality_gate.py`'s already-real 20-criteria gate + `capital_allocation_engine.py`'s `investment_score()`.

`department_health.py` (Executive Intelligence Core, Round 4, 2026-07-29) already reports real per-department health across the exact real 12-department roster `department_events.py`'s own `VALID_DEPARTMENTS` defines (`executive`, `market_intelligence`, `golden_hunter`, `pioneer`, `researchers`, `production`, `publishing`, `finance`, `customer_intelligence`, `infrastructure`, `recovery`, `ai_capability_manager`) — the correct, real, canonical department list to reuse, never a second invented one. `orchestrator/registry.py` already implements the exact dependency-inversion/plugin-registration pattern (an adapter registers itself, the coordinator depends only on the abstract shape) that is the architecturally correct foundation for loose coupling — cited as evidence for why a mandatory gateway isn't the right model here, not duplicated.

## What was built

**`gfos.py`** (new), four functions, each a pure citation/merge — zero new judgment, zero new state:

- `department_registry()` — the one genuinely new capability: every field the directive asked for, per department, each a real citation of an already-real signal. Reuses `department_health.build_department_health()` verbatim for Capabilities/Health (never a second health computation), `department_events.py`'s own real per-department event counts for Workload, and a real, deliberately narrow (single-primary-module) citation of `dependency_graph.py` for Dependencies — disclosed as narrow, not a full per-department dependency audit.
- `mission_lifecycle_summary()` — the real "Global Mission Queue," per the founder's confirmed answer: a pure citation of `scheduler.py`'s already-real 5 buckets and `orchestrator.types.EXECUTION_ORDER`'s already-real 5 stages, mapped onto the directive's 8 named lifecycle words via a disclosed heuristic. 4 of the 8 stages (Created/Executing/Completed/Measured) honestly report `None` with a citation to where the real signal actually lives (`decisions.jsonl`, `orchestrator/timeline.py`, `production_blueprint.py`, `decision_engine.feedback.sync_outcomes()`) rather than a fabricated count.
- `enterprise_timeline()` — the second genuinely new capability: a real merge of `decisions.jsonl` + `department_events.jsonl` + `evolution_queue_state.json`'s stage_history + `executive_directives.jsonl` + `council_recommendations.jsonl`, most recent first. Zero new logging call sites — every entry already existed in its own real file before this function was written.
- `gfos_status()` — the single real aggregate for Mission Control: cites (never recomputes) the latest Executive Directive, the full department registry, the mission lifecycle citation, and the 10 most recent Enterprise Timeline entries.

**A real bug found and fixed during implementation**: the first draft of `enterprise_timeline()` hardcoded `department_events.jsonl`'s path instead of accepting it as a parameter (unlike every other ledger path in the same function), making it impossible to isolate in tests or override for any real caller — caught by a test that expected an empty timeline against temp paths and got 10 real production events back. Fixed by adding the missing `department_events_path` parameter, matching every sibling parameter's own convention.

## What stays exactly as it was

Every one of the ~60 modules cited above is still called directly by every other real caller, exactly as before this ADR. `gfos.py` introduces zero new execute-capable code path — every function is read-only. `safe_mode.py`'s per-subsystem independence (ADR-135) is untouched. No new queue, no new worker pool, no new always-on process.

## Mission Control

`mission_control_api.py` gained `gfos_status` (~13s, `department_health.build_department_health()` touches multiple real subsystems) and `gfos_enterprise_timeline` (~0.2s). `server.js`'s `SERVICE_REGISTRY` gained `gfos-status` (40s timeout) and `gfos-enterprise-timeline`. `mission_control_executive_v1.html` gained two panels, placed first in the existing "Executive Overview" group (no new top-level group invented — per this same session's own Architecture Health Report, panel/group proliferation is this factory's clearest maintainability risk; GF-OS is the unifying citation layer the directive itself frames it as, not a 12th parallel section).

## Validation

`tests/test_gfos.py` (new, 12 tests, all passing): the real 12-department roster is reused exactly (never a second list), every department carries all 8 named fields, confidence is derived from real `data_source` never fabricated, every mission-lifecycle count traces back to a real scheduler bucket, lifecycle stages with no real signal are honestly `None` (not a fabricated zero), the Enterprise Timeline is chronologically sorted and every entry cites its real source file, and the regression test for the path-parameter bug found above. Verified live against real factory data (12 real departments, real lifecycle buckets, 1,516 real timeline events merged in 0.2s) and via a real logged-in browser session — both new panels render correctly as the first two cards in Executive Overview, zero console errors. 142 existing tests across `test_gfos`/`test_executive_brain`/`test_executive_decision_memory`/`test_evolution_queue`/`test_knowledge_graph`/`test_scheduler`/`test_department_health` all pass unchanged. `data/*.jsonl` confirmed byte-unchanged by this session's testing.
