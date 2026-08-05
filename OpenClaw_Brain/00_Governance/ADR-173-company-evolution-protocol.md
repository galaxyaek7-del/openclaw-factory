# ADR-173 — Company Evolution Protocol V1 (Galaxy Evolution Report)

**Date:** 2026-08-05
**Status:** Adopted. Extends `evolution_engine.py` — no new judgment engine, no new module.

---

## The directive (verbatim, condensed)

> GALAXY FORGE — COMPANY EVOLUTION PROTOCOL V1
>
> Monthly Strategic Review: evaluate departments, workflows, production, opportunity engine, pricing, customer experience, security, automation. Identify bottlenecks, wasted effort, duplicated systems, missing opportunities. Continuously study world-class companies — extract their principles, adapt them. Create an internal executive report called GALAXY EVOLUTION REPORT: current strengths, weaknesses, critical risks, hidden opportunities, recommended improvements, high priority actions, expected long-term impact, potential monthly revenue impact, estimated implementation effort — rank everything by ROI.

## Research finding: near-total overlap with an already-real, already-named module

`evolution_engine.py`'s existing `build_evolution_report()` (EOS Phase 1, 2026-07-19) already combines real bottleneck detection, technical debt, high-ROI opportunity ranking, capability gaps, and tool proposals — the large majority of this directive's ask, under this exact module name ("Evolution Engine"). `gfos.py::if_i_were_the_ceo_report()` (built the round immediately before this one, same session) already answers a near-identical 7-question CEO-mode ask on a weekly cadence. This round's real job was narrower than "build a new evolution system": relabel and extend the existing report onto the directive's exact 10 named sections, add real ROI ranking (from `capital_allocation_engine.py`, not previously threaded through `build_evolution_report()`), and add the one genuinely new element — a **monthly** cadence, distinct from this factory's existing daily/weekly report gates.

## Two real, disclosed gaps — honored, never fabricated

1. **"Potential Monthly Revenue Impact" and "Estimated Implementation Effort," per recommendation.** Zero real signal exists for either anywhere in this factory — confirmed repeatedly this session (`channels/ledger.py`'s real revenue is $0; `execution_status.py`/`gfos.py`/`strategic_planning.py` all already disclose `estimated_completion: Unknown` for the identical reason — no real historical per-task duration data has ever been recorded). Both fields report `NOT_MEASURABLE` with their real reason, never a guessed number.
2. **"Global Benchmark — continuously study world-class companies."** No real, re-runnable internal capability does this. `competitor_discovery.py` researches real per-niche *product* competitors — a narrower, different concept. Building a live external company-research pipeline was not attempted; the gap is reported as `NOT_BUILT`, not silently skipped or faked with a static list of generic "best practices."

## What was built

**`evolution_engine.py`** gained two real, additive functions:

- **`build_galaxy_evolution_report()`** — computes `build_evolution_report()` and `capital_allocation_engine.build_capital_allocation_dashboard()` exactly once each, maps them onto the directive's 10 named sections. `high_priority_actions_ranked_by_roi` cites `capital_allocation_engine.py`'s real `top_roi_initiatives` — the one real numeric ROI signal this factory has, never a second ranking algorithm.
- **`render_galaxy_evolution_report_markdown()`** — real markdown rendering of the above.

**`mission_control_api.py`** gained `_galaxy_evolution_report()`, registered as `galaxy_evolution_report`. **`server.js`** gained the `galaxy-evolution-report` `SERVICE_REGISTRY` entry + a panel in the existing Executive Overview group.

**`factory_loop.js`** gained `runGalaxyEvolutionReport()` and `maybeGenerateMonthlyGalaxyEvolutionReport()` — the directive's own explicit "monthly" cadence, genuinely new: this factory's first once-per-calendar-month report gate, using the identical file-existence-check technique as every existing daily/weekly gate, just widened to a month (`GALAXY_EVOLUTION_<year>-<month>.md`). Wired into `runTick()` immediately after the existing daily evolution-report step.

## What is explicitly NOT built

- No new judgment/decision engine — every section of the Galaxy Evolution Report cites an already-real function.
- No fabricated revenue-impact or effort-estimate numbers per recommendation.
- No fake "world-class company benchmarking" — honestly disclosed as `NOT_BUILT`, not simulated with static, made-up "best practices" text.
- No change to any of the 4 standing founder-protected gates.

## Validation

`python -m unittest tests.test_evolution_engine -v` — 14/14 passing (5 pre-existing + 9 new): proven the new function never recomputes `build_evolution_report()` (injectable `base_report`); revenue impact/effort are proven `NOT_MEASURABLE`; Global Benchmark is proven `NOT_BUILT`; ROI ranking proven to cite real `capital_allocation_engine.py` data via mock assertions; a real, unmocked call against live data never throws. `node tests/test_factory_loop_monthly_galaxy_evolution_report.js` — 4/4 passing: the monthly path-building function proven to produce the *same* path for two different days in the same real calendar month, and a *different* path for a different real month. Live-verified end-to-end: `python mission_control_api.py galaxy_evolution_report` (real success), `GET /api/v1/galaxy-evolution-report` via a disposable server (real success). Full test suite green.
