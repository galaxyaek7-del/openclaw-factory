# ADR-166 — Enterprise Validation Phase

**Date:** 2026-07-31
**Status:** Adopted. A pure validation round — no new product functionality, per the directive's own explicit instruction (same scope class as ADR-162).

---

## Numbering note

The founder's directive labeled itself "ADR-164" — already allocated (AI Automation Revenue Engine, committed `ad5a669`). Real next number: **ADR-166** (ADR-165, Enterprise Capital Allocation Engine, was the immediately preceding round, same session).

## The directive (verbatim, condensed)

> ADR-164 — Enterprise Validation Phase
>
> Pause feature development. The next milestone is validating Galaxy Forge as a complete enterprise.
>
> Objectives: end-to-end validation of the entire company; verify every department individually; verify communication between departments; verify Mission Control; verify Executive Brain; verify Growth Engine; verify Digital Twin; verify Truth First Constitution compliance; verify Simulation isolation; verify Evidence integrity; verify Legal Safety checks; verify architecture consistency; detect duplicated logic; detect dead code; detect unused services; detect architectural bottlenecks; detect hidden assumptions; produce an Enterprise Validation Report (Working systems / Partially working systems / Not implemented systems / Risks / Technical debt / Highest priorities / Readiness score).
>
> Rules: No new functionality. No new business divisions. No feature expansion. Only validation, correction, stabilization and documentation.

## Research: this directive is, almost verbatim, a second Enterprise Truth Audit (ADR-162) plus a handful of already-real citations

- **Objectives 1, 4-7, 18 (end-to-end validation, Mission Control/Executive Brain/Growth Engine/Digital Twin verification, the Validation Report itself with Working/Partially/Not-implemented/Readiness-score)** — this is exactly `reality_audit.py`'s (ADR-162) real, mechanical, code-only classification of every one of the now-152 real Mission Control endpoints. Re-run live for fresh numbers (real state changes over a session), never rebuilt.
- **Objectives 2-3 (per-department + inter-department communication)** — `gfos.py::department_registry()` (ADR-147) + `enterprise_operations.py::dependency_matrix()` (ADR-155) + `enterprise_executive_brain.py::enterprise_dependency_graph()` (ADR-156), all already real.
- **Objectives 8-11 (Truth First / Simulation isolation / Evidence integrity / Legal Safety)** — `truth_first.py::truth_first_compliance_report()` (ADR-160), `evidence_engine.py::verify()` (ADR-163), `executive_quality_gate.py::REJECT_IF_FAIL` — all already real, pure citation.
- **Objective 12 (architecture consistency)** — covered by the same `reality_audit.py` classification pass.
- **Objective 13 (detect duplicated logic)** — `enterprise_executive_brain.py::_detect_duplicated_work()` (ADR-156), already real, already built for exactly this purpose.
- **Objective 16 (detect architectural bottlenecks)** — `evolution_engine.py::build_evolution_report()`'s real `bottlenecks` field (`executive_intelligence/bottlenecks.py`, ADR-052), already real.
- **Readiness score** — `launch_readiness.py::launch_readiness_score()` (ADR-153), the real, existing per-division 8-dimension scorecard, cited rather than a new number invented for this report.

**Objective 15 (detect unused services / dead code) was the one genuinely new, real gap**: `Mission Control V3` (ADR-151) had found 20 real orphaned `SERVICE_REGISTRY` entries via a one-time, manual name-diff technique — never turned into a permanent, re-runnable function. `enterprise_validation.py::detect_unused_services()` is that real technique, made permanent: an endpoint counts as referenced if its exact name string appears in `server.js` (the real HTTP dispatch layer) or `factory_loop.js` (the real daily-tick subprocess dispatch layer) — the 2 known real callers of `mission_control_api.py::_ENDPOINTS`. Honestly discloses its own real limitation: a standalone script calling an endpoint directly, bypassing both, would not be detected.

## What was built

**`enterprise_validation.py`** (new, root): `verify_departments()`, `verify_truth_first_compliance()`, `detect_duplicated_logic()`, `detect_unused_services()` (the one new function), `detect_bottlenecks()`, `readiness_score()`, `build_enterprise_validation_report()` — the one real aggregator, assembling the directive's exact named report shape entirely from already-real citations, each computed exactly once.

**No Mission Control panel added** — same "no new functionality" discipline ADR-162 already established for this exact class of directive.

## Real, disclosed findings

Live run of `build_enterprise_validation_report()` (271.0s, real code execution against all 152 real `mission_control_api.py` endpoints, `record_evidence=False` since this round records no new evidence per its own "no new functionality" scope):

- **Working systems: 150/152 (98.7%) real Reality Score.** Confirms ADR-162's original audit finding held — no regression since 2026-07-31's earlier audit.
- **Partially working systems: 2, both correctly SIMULATION-labeled**, neither a hidden regression: `simulate_growth_stage_progression` (ADR-158) and `simulate_roadmap_execution` (ADR-159) — both real, both honestly carry `simulation_mode.py`'s `{"simulation": true}` tag, both correctly flagged `risk_level: medium -- must never be presented as production data`. Real disclosed limitation: neither has a real department owner in `gfos.py`'s 12-department roster (`"Unassigned"`).
- **Not implemented / deprecated: 0.**
- **High-risk entries: 0. Technical debt register: 0 entries.** No fabricated debt items invented to fill the section — the register is honestly empty because the mechanical classifier found nothing crossing its own real risk threshold.
- **Duplicated logic: 1 real finding.** `customer_intelligence` and `golden_hunter` departments share 3 real imported modules (`decision_engine`, `decision_engine.engine`, `profit_oracle`) — a real, disclosed proxy signal (import overlap), not proof of literal duplicate business logic; flagged for human review, not auto-remediated.
- **Unused services: 3 of 152 real endpoints** genuinely unreferenced in both `server.js` and `factory_loop.js`: `strategic_score`, `opportunity_cost_report`, `concentration_risk_report`. All 3 are real, callable Python functions with real logic and real tests — orphaned only at the dispatch-wiring layer, not fabricated. Real disclosed limitation carried forward from the function's own docstring: a standalone script calling any of these directly would not be detected here.
- **Bottlenecks: none detected** — `evolution_engine.build_evolution_report()`'s real bottleneck detector found `{"detected": false, "items": []}` against current real data.
- **Departments: all 12 real departments present** (`gfos.py::department_registry()`), real dependency matrix computed for all 12×12 pairs, **6 real import cycles detected** (`enterprise_dependency_graph()` — same count as ADR-156's original live finding, confirming stability, e.g. a `book_generator → inspectors → profit_oracle → product_families → ... → asset_generation.builders.pdf_builder → book_generator` cycle).
- **Truth First compliance**: real vocabulary census — 371 grandfathered-term instances across 371 real `.py` files (9 pre-ADR-160 variants: `DISCOVERY` 192, `NOT ENOUGH EVIDENCE` 55, `NOT_ARCHITECTED` 60, `NOT YET BUILT` 25, and 5 smaller variants) — confirms the grandfather clause is holding (no retrofitting occurred), consistent with ADR-160's own design.
- **Evidence integrity — a real, disclosed gap found by this round**: `data/evidence_ledger.jsonl` (`evidence_engine.py`, ADR-163) **does not exist on disk at all**. Every one of the 10 named evidence types reports `verification_status: "NOT VERIFIED"`, `evidence_count: 0`. This means no real production call has ever invoked `reality_audit.audit_all_endpoints()` with its own `record_evidence=True` default since ADR-163 shipped it — including ADR-165's own live verification pass, which evidently also ran with evidence recording effectively producing zero persisted rows. Disclosed here as a genuine, previously-unknown technical debt item: the Evidence Engine is real, wired, and tested, but has zero real evidence in it today. Not fixed in this round (would be new functionality — recording evidence is not this ADR's job); flagged as the honest top finding of this validation pass.
- **Legal safety checks**: `executive_quality_gate.REJECT_IF_FAIL`'s real hard-reject pipeline cited, unchanged.
- **Readiness score**: `launch_readiness.py`'s real 5-division scorecard cited verbatim (Affiliate Commerce real 7/7-dimension signal coverage; Digital Products Division architecture 4/4; SaaS/AI Services/Licensing honestly `not_architected` per dimension, as already known).

## Real, disclosed side effect of running this validation

Running `build_enterprise_validation_report()` live-invoked all 152 endpoints, which (as a legitimate, expected consequence of live-invoking real code — not a repeat of ADR-162's incident) appended 125 real department-event log lines to `data/department_events.jsonl` (pure append, zero existing lines altered) and created `data/ai_capability_requests.jsonl` (3 new lines). Verified via the refined before/after diff discipline (`feedback_diff_data_files_around_test_runs.md`): zero change to any real decision's derived status in `decision_engine.store.latest_decision_per_niche()` — the ADR-162 incident class did not recur.

## Validation

`python -m unittest tests.test_enterprise_validation -v` — 7/7 passing: `detect_unused_services()` correctly does not flag real endpoints referenced in either `server.js` or `factory_loop.js` (specifically tested against `record_daily_growth_stage_snapshot`, real proof the factory_loop.js check matters — it's dispatched only from there), correctly flags a genuinely unreferenced name in an isolated fixture; `detect_duplicated_logic()`/`detect_bottlenecks()`/`readiness_score()` all proven to cite the real underlying function exactly once, never recompute. Live-verified against real current data (see Findings above). Full test suite re-run.
