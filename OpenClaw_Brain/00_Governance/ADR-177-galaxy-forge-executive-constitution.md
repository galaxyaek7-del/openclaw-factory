# ADR-177 — Galaxy Forge Executive Constitution

**Date:** 2026-08-06
**Status:** Adopted. A navigable governance index, not a new decision engine, not a new constitution superseding `CONSTITUTION.md`/`TRUTH_FIRST_CONSTITUTION.md`.

---

## The three directives (verbatim, condensed)

> **GALAXY FORGE — GLOBAL EXECUTIVE STANDARDS**: 8 named areas — Product Excellence, Customer Trust, Security, Operational Discipline, Financial Discipline, Continuous Innovation, Company Knowledge, Long-Term Value. Do not duplicate existing systems.

> **GALAXY FORGE — GLOBAL DOMINANCE DIRECTIVE**: 10 named value-maximization criteria, a moat framework (8 questions on competitors/assets/defensibility), a per-project "Strategic Impact Score." Integrate permanently without duplicating existing systems.

> **GALAXY FORGE — EXECUTIVE OPERATING SYSTEM**: "Stop thinking in terms of features. Design the permanent Executive Operating System (EOS) of Galaxy Forge — the constitution every future AI agent, department, workflow, and product must obey." 15 named governance domains, each requiring responsibilities / decision authority / required evidence / mandatory reports / measurable KPIs / escalation rules. Do NOT duplicate existing architecture; integrate with the current Executive Brain. This becomes Galaxy Forge's permanent executive constitution.

## Why these three were consolidated into one round

All three arrived in immediate succession and each is, at its core, the same request under a different name: a permanent governing index over an already-mature factory, explicitly instructing "do not duplicate." Research confirmed the instruction was warranted: every one of the ~23 named sub-areas across all three directives already maps to a real, already-built module or an existing constitution document. Building three separate governance documents — each independently re-deriving citations to the same underlying modules — would itself be the duplication all three explicitly forbade. This is the same consolidation judgment this session has applied 6 times before (Executive Brain/ADR-144, GFOS/ADR-147, GOS/ADR-172, Galaxy Evolution Report/ADR-173, Market Domination Engine/ADR-175, Capital Allocation Investment Decisions/ADR-176) — applied directly here without a fresh `AskUserQuestion`, consistent with the standing precedent that re-asking an already-repeatedly-answered question is not genuine deliberation.

## The naming collision, avoided proactively

The Executive Operating System directive self-selects the acronym "EOS." This codebase already uses "EOS" to mean a specific, unrelated 2026-07-19 historical period ("EOS Phase 1/2" — weekly reviews, the first Evolution Engine, Founder Console; documented in `CLAUDE.md`). Adopting "EOS" for this new document would create the exact class of naming collision this session has hit and fixed twice before (`growth_stages.py` vs. `growth_engine.py`; `executive_questions.py` vs. the pre-existing `executive_intelligence/` package, ADR-154). The new document is named **"Galaxy Forge Executive Constitution"** instead — `OpenClaw_Brain/00_Governance/GALAXY_FORGE_EXECUTIVE_CONSTITUTION.md`.

## What the consolidated document is, structurally

Organized around the Executive Operating System directive's 15 governance domains (the most complete structure of the three) — Executive Council, Decision Hierarchy, Risk Management, Strategic Planning Cycle, Product Approval Pipeline, Market Intelligence Workflow, Capital Allocation Workflow, Innovation Workflow, Knowledge Governance, Security Governance, Quality Governance, Revenue Governance, Automation Governance, Crisis Management, Long-Term Company Evolution. Each domain cites its real, already-built enforcement mechanism against all 6 required fields (responsibilities / decision authority / required evidence / mandatory reports / measurable KPIs / escalation rules) — never invents a new one. Global Executive Standards' 8 areas and Global Dominance's moat framework are woven into the relevant domains as cross-referenced content rather than kept as separate parallel sections, per the "one consolidated index" decision above.

## What was genuinely new (the real gaps found during consolidation)

Two structural gaps existed: this factory's report cadences stopped at monthly (`Galaxy Evolution Report`, ADR-173) — no quarterly or annual cadence existed anywhere, though the Strategic Planning Cycle domain clearly calls for both. And no per-project "Strategic Impact Score" existed under that specific name, though the Global Dominance Directive named it explicitly.

1. **Quarterly Architecture Review** — `factory_loop.js::maybeGenerateQuarterlyArchitectureReview()`, this factory's first once-per-calendar-quarter gate. Reuses `enterprise_validation.py::build_enterprise_validation_report()` (ADR-166) verbatim via a new thin renderer, `render_enterprise_validation_report_markdown()`. Writes `reports/ARCHITECTURE_REVIEW_<year>-Q<quarter>.md`. Dispatched via a new `mission_control_api.py` endpoint, `enterprise_validation_report_quarterly` (162nd endpoint).
2. **Annual Strategic Review** — `factory_loop.js::maybeGenerateAnnualStrategicReview()`, this factory's first once-per-calendar-year gate. Reuses `strategic_planning.py::build_strategic_planning_dashboard()` (ADR-159) verbatim via a new thin renderer, `render_strategic_planning_report_markdown()`. Writes `reports/ANNUAL_STRATEGIC_REVIEW_<year>.md`. Dispatched via `strategic_planning_report_annual`.
3. **Strategic Impact Score** — `goos.py::strategic_impact_score(niche)`. A disclosed average of 2 already-real scores (GOOS's own advisory score, ADR-171; Capital Allocation's extended Investment Score, ADR-165/176) — never a 3rd, independent computation. Honestly reports whichever real component is unavailable (e.g. Investment Score requires a real ACCEPTED decision) rather than silently substituting or defaulting to zero.

Both new report functions follow the exact same spawn/parse/timeout pattern every prior `run*Report()` function in `factory_loop.js` already established, and both cadence gates follow the exact same file-existence-check-then-write pattern every prior daily/weekly/monthly gate already established — genuinely new *cadences*, zero new *architecture*.

## The Global Dominance moat framework — answered by citation, not new architecture

What makes Galaxy Forge hard to copy, why customers would choose it, and which activities should never consume engineering time are each answered in the constitution document by citing real per-niche signals (`market_defensibility`/`difficulty_of_copying` in GOOS) and this session's own real, repeatedly-reconfirmed standing deferrals (no country-level market connectors before the first real dollar, no revenue-tile scaffolding before real revenue exists, no repeat of an already-solved "unify the company" governance layer) — never a fabricated new competitive-analysis engine.

## A real incident found and fixed during this round's own verification

Live-verifying the new `enterprise_validation_report_quarterly` endpoint (a routine "does it work" check, the same discipline every round this session applies) triggered a genuine, previously-latent bug: `enterprise_validation.py::build_enterprise_validation_report()` (ADR-166) internally reuses `reality_audit.py::audit_all_endpoints()` (ADR-162), which live-invokes every non-write-flagged endpoint registered in `mission_control_api.py::_ENDPOINTS` — a table that, as of this round, now includes `enterprise_validation_report_quarterly` itself. Live-invoking it caused it to call `build_enterprise_validation_report()` again, which called `audit_all_endpoints()` again, which live-invoked itself again — each level spawning a new background thread via `_call_with_timeout()`'s real, by-design "never kill a timed-out thread" behavior (it exists to avoid interrupting a real in-flight write elsewhere), so every level's leftover thread kept recursing indefinitely rather than being cleaned up. This function had never been reachable through `_ENDPOINTS` before this round (ADR-166 only ever called it directly, never via Mission Control dispatch), so the cycle was structurally impossible until this round created it.

Caught live: the manual CLI verification ran for over 3 hours with continuously climbing CPU time (multiple daemon threads, confirmed via live process inspection) before being killed manually. Fixed with a real, process-wide re-entrancy guard in `reality_audit.py` — a simple depth counter (`_audit_depth`, `threading.Lock`-protected) incremented on entry to `audit_all_endpoints()` and decremented on exit; `classify_endpoint()` gained an `allow_live_invoke` parameter, and any nested audit pass (depth > 1) classifies every endpoint structurally only, with an honest, disclosed `"NOT live-invoked (re-entrancy guard...)"` evidence string — never silently. Re-verified live post-fix: the endpoint now completes normally (98.8% Reality Score, 160/162 REAL, 2/162 SIMULATION, 0 gaps), and 3 new regression tests (`tests/test_reality_audit.py::TestReentrancyGuard`) prove a self-referential endpoint terminates in under 15s (previously: unbounded) while an ordinary top-level audit still live-invokes normally.

## What was explicitly NOT built

No new decision engine, no 4th learning loop, no automated enforcement mechanism (the constitution is a citation index — it does not gate anything itself; every real gate it cites already existed and is unchanged). No Mission Control panel for the constitution document itself (a governance document, not a live-data panel) — the two new report endpoints and `strategic_impact_score()` are separately callable via `mission_control_api.py` but were not wired into `SERVICE_REGISTRY`/`ACTION_REGISTRY` this round; this is a disclosed scope decision, not an oversight, since neither is time-critical for founder-facing display beyond the report files themselves.

## Verification

- `python3 -c "import mission_control_api; print(len(mission_control_api._ENDPOINTS))"` → 162 (was 160 before this round).
- `python mission_control_api.py strategic_planning_report_annual` — real success, 44.8s, correct markdown header confirmed.
- `python mission_control_api.py enterprise_validation_report_quarterly` — first attempt uncovered the real re-entrancy incident above (killed after 3+ hours); post-fix re-run succeeded cleanly, 98.8% Reality Score (160 REAL/2 SIMULATION/0 gaps out of 162).
- `node -c factory_loop.js` → OK. `architectureReviewReportPath`/`annualStrategicReviewReportPath` verified directly: same real quarter/year produces the same path, a different one produces a different path.
- `tests/test_goos.py` — 16/16 pass (13 pre-existing + 3 new `TestStrategicImpactScore` cases: composite averaging, honest fallback on exception, honest `None` when neither component available).
- `tests/test_factory_loop_quarterly_annual_reviews.js` — 6/6 pass (spawn-error/parse-failure paths for both new run functions; the Maybe* gate functions themselves are not called from the automated test since both unconditionally write into the real `reports/` directory, same disclosed limitation every other cadence-gate test file already has).
