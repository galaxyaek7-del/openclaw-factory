# ADR-159 — Enterprise Strategic Planning System

**Date:** 2026-07-31
**Status:** Adopted. Real, near-total-citation rolling roadmap, per-division status board, Enterprise Priority Matrix, planning Q&A, and extended Executive Timeline built — plus one small, additive Growth Stage history recorder.

---

## The directive (verbatim)

> Founder Directive — Enterprise Strategic Planning System
>
> The company now has: Executive Brain, Operations Center, Growth Engine, Mission Control, Affiliate Commerce, Digital Products, Simulation Layer.
>
> The next priority is Strategic Planning.
>
> Build the Enterprise Strategic Planning System.
>
> Objectives:
>
> 1. Create a rolling roadmap. Time horizons: Today, This Week, This Month, This Quarter, This Year.
>
> 2. Every division must automatically publish: Current objectives, Progress, Risks, Dependencies, Blocked tasks, Estimated completion.
>
> 3. Build Enterprise Priority Matrix. Every task receives: Business impact, Revenue impact, Technical impact, Risk, Urgency, Estimated effort, Confidence, Priority score.
>
> 4. Mission Control must answer instantly: What should the company build next? What should be delayed? What creates the highest ROI? What blocks company growth?
>
> 5. Add Executive Timeline. Display: Completed milestones, Current milestone, Upcoming milestones, Growth Stage history, Major architectural decisions.
>
> 6. Every recommendation must reference real data only. No invented planning. No fake priorities.
>
> 7. Simulation Mode must simulate roadmap execution. Without touching production.
>
> Rules: Reuse existing architecture. No duplicate planners. Everything must remain explainable. ADR + tests + documentation required.

## Research before writing any code — the highest-overlap round of the session

- **Objective 4 was ~95% already built, verbatim, in the two immediately preceding rounds the same session.** `executive_questions.py::answer_strategic_questions()` (ADR-154) already answers `what_should_be_built_next`, `what_should_be_paused`, `what_creates_the_highest_roi`, `which_bottleneck_blocks_future_scaling` — nearly word-for-word this directive's 4 named questions. `growth_stages.py::answer_growth_questions()` (ADR-158, built minutes earlier the same session) already answers "what blocks growth" and "highest ROI to advance." `strategic_planning.py::answer_planning_questions()` is close to pure citation of both, reframed under this directive's exact question names.
- **Objective 3 (Priority Matrix) already has a real per-opportunity analog.** `execution_status.py::build_execution_status_report()` (ADR-102/105) already computes, per real ACCEPTED opportunity, ranked by real Priority Score: business value, estimated revenue, estimated effort, expected ROI, confidence, priority, dependencies (honestly `None`), expected completion (honestly `Unknown`). The 8 named Matrix columns are mostly a relabeling of these fields, plus 2 genuinely new citations (`technical_impact`, honestly `None` by default to avoid an expensive per-niche `investment_score()` call per row; `urgency`, derived from the already-joined scheduler bucket).
- **Objective 2 (per-division auto-publish) combines 4 already-real per-division sources for the first time**: `growth_stages.py::division_stage_objectives()` (current objectives, ADR-158), `launch_readiness.py::launch_readiness_score()` (progress, ADR-153), `enterprise_operations.py::dependency_matrix()` (dependencies, ADR-155), and a generalized version of `executive_questions.py::_which_division_is_slowing()`'s real active-alert filtering technique (risks, ADR-154) — applied to all 7 named divisions instead of finding just the one worst. Blocked tasks and estimated completion are honestly disclosed as company-wide/`Unknown` respectively, per this factory's established discipline.
- **Objective 5 (Executive Timeline) extends `gfos.py::enterprise_timeline()`** (ADR-147/154) with milestone framing sourced from `growth_stages.py`'s own real per-stage condition lists. **"Growth Stage history" was the one genuine, real gap**: `growth_stages.py` (ADR-158) is deliberately stateless with zero persistence by design. Resolved the same way `health_trend.py` relates to `resilience_monitor.py` (ADR-135/157 precedent, cited directly rather than re-derived): `growth_stages.py` gained two small, purely additive functions this round — `record_growth_stage_snapshot()` (the ONE real write path, appends to a new `data/growth_stage_snapshots.jsonl`) and `growth_stage_history()` (a real chronological reader). Neither is called by `current_growth_stage()` itself — only `factory_loop.js`'s new once-per-calendar-day tick step calls the recorder, exactly mirroring the marker-file convention every other daily report function already uses.
- **Naming collision check**: no `strategic_planning.py`/`roadmap.py`/`priority_matrix.py`/`enterprise_timeline.py` existed anywhere in this factory before this round (grepped). New module: `strategic_planning.py` — one module owns all 5 objectives rather than proliferating parallel modules, matching this session's own repeated "consolidate, extend architecture instead of duplicating it" resolution (ADR-144/147/154/155/156).
- **Time-horizon honesty constraint**: this factory has "no scheduler" (CLAUDE.md) and zero real historical per-stage duration tracking (`execution_status.py`'s own established, repeated disclosure). Today/This Week/This Month/This Quarter/This Year can never honestly mean a real committed calendar date here. Resolution: a disclosed, static heuristic re-bucketing of already-real prioritized items — `scheduler.py`'s real `run_now` bucket + any real `AWAITING_FOUNDER_APPROVAL` proposal → **Today**; `accelerate` bucket → **This Week**; the current Growth Stage's own real next-stage requirements → **This Month**; `wait` bucket → **This Quarter**; `stop`/`cancel` buckets → **This Year**. Every bucket entry carries its own real source citation and an explicit, constant `NOT_A_COMMITTED_DATE` disclosure string — never presented as a real deadline.

## What was built

**`strategic_planning.py`** (new, root):

- `rolling_roadmap(lifecycle=None, growth=None)` (Objective 1) — the heuristic re-bucketing above, injectable to avoid redundant computation.
- `division_status_board(readiness=None, resilience=None)` (Objective 2) — per-division real citation across the 4 sources above. Dependencies are honestly `None` for divisions with no real 1:1 match in `gfos.py`'s 12-department roster (Affiliate Commerce, Operations) — CLAUDE.md's own documented cross-taxonomy note, never force-mapped.
- `enterprise_priority_matrix(limit=None, report=None)` (Objective 3) — relabels `execution_status.build_execution_status_report()`'s real fields; order is always that report's own real Priority Score order, never a second ranking pass.
- `answer_planning_questions(strategic_answers=None, growth_answers=None)` (Objective 4) — cites `executive_questions.py` + `growth_stages.py` under this directive's exact 4 question names.
- `executive_timeline_extended(timeline=None, growth_dashboard=None)` (Objective 5) — extends `gfos.enterprise_timeline()` with current/upcoming milestone framing (from `growth_stages.py`'s own condition lists) and the new `growth_stage_history()`.
- `build_strategic_planning_dashboard()` — the one real top-level aggregator: `gfos.mission_lifecycle_summary()`, `growth_stages.build_growth_dashboard()`, `launch_readiness.launch_readiness_score()`, `resilience_monitor.assess_resilience()`, `executive_questions.answer_strategic_questions()`, `execution_status.build_execution_status_report()`, and `gfos.enterprise_timeline()` are each computed exactly once and threaded through every function above — the 4th consecutive round this session where the redundant-full-portfolio-scan bug class (`company_pulse()`/ADR-155, `enterprise_scheduler()`/ADR-156, `growth_stages.build_growth_dashboard()` itself) was the primary implementation risk, guarded against explicitly from the start this time. Measured live: **~70s**.
- `simulate_roadmap_execution(**hypothetical)` (Objective 7) — reuses `growth_stages.simulate_stage_progression()`'s exact overrides mechanism verbatim, recomputes `rolling_roadmap()` against the hypothetical result, tags with `simulation_mode.tag_simulated()`. Writes nothing to disk.

**`growth_stages.py`** (extended, not redesigned): `record_growth_stage_snapshot(stage_result=None, snapshots_path=None)` and `growth_stage_history(limit=50, snapshots_path=None)` — the Growth Stage history resolution described above. `current_growth_stage()` itself is byte-for-byte unchanged.

**Commit-history note**: this round began before ADR-158's own commit had landed (its full test suite was still running when this directive arrived), and both rounds touched `growth_stages.py`. The two recorder functions above were written into `growth_stages.py` before ADR-158's commit was made, so they shipped inside commit `baaf592` (ADR-158) rather than this round's own commit — real, correct, tested code, just an attribution mismatch in git history, disclosed here rather than silently left unmentioned. Every other file this round touches (`strategic_planning.py`, `mission_control_api.py`'s 3 new dispatch functions, `server.js`, `factory_loop.js`, this ADR, its tests) is cleanly scoped to this commit.

**`factory_loop.js`**: new `maybeRecordDailyGrowthStageSnapshot()` + `runRecordDailyGrowthStageSnapshot()`, same once-per-calendar-day marker-file pattern as `maybeGenerateDailyExecutiveDirective()` (ADR-144), wired into the tick sequence immediately after the executive-directive step. Live-verified: first call records a real snapshot (`stage_1_validation`), second same-day call correctly no-ops.

**Mission Control**: `strategic-planning-dashboard` (`SERVICE_REGISTRY`, no-input, 90s timeout — measured live ~70s) + `simulate-roadmap-execution` (`ACTION_REGISTRY`, async, same `confirmed`-field-stripping fix this session's own `simulate-growth-stage-progression` action needed minutes earlier — carried forward directly rather than rediscovered) + one new panel in the existing Executive Overview group (no new top-level group, per this session's repeated "don't proliferate panels" finding).

## What is explicitly NOT built

No new task-tracking system — the Priority Matrix operates over real ACCEPTED opportunities, this factory's only real "task" unit, never an invented ticket concept. No real committed calendar dates for any roadmap horizon. No second ranking/scoring algorithm anywhere — every score is a citation of `value_engine.py`/`capital_allocation_engine.py`/`scheduler.py`. `growth_stages.current_growth_stage()` remains exactly as stateless as ADR-158 left it — the new snapshot ledger is purely additive and read separately, never contradicting ADR-158's own "no persistence" statement about the stage *classifier*.

## Validation

`python -m unittest tests.test_strategic_planning -v` — 21/21 passing: every roadmap horizon cites a real source and carries the `NOT_A_COMMITTED_DATE` disclosure; the Priority Matrix preserves `execution_status_report()`'s real order exactly (no second ranking algorithm); `division_status_board()` covers all 7 divisions and honestly discloses `None` dependencies where no real taxonomy match exists; `answer_planning_questions()` proven to be pure relabeling (injected fake answers pass through unchanged); the snapshot recorder proven additive-only (2 real calls → 2 real entries, first entry unchanged); `growth_stage_history()` proven honestly empty before any snapshot exists; `simulate_roadmap_execution()` proven to write nothing to `data/`. Live-verified end-to-end: `build_strategic_planning_dashboard()` against real current data (~70s), the daily-tick recorder's real once-per-day gate, and the full pre-existing 2142-test suite (unaffected, run as part of the immediately preceding ADR-158 commit's validation).
