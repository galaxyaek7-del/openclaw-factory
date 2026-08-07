# OpenClaw / Galaxy Forge — Decision Protocol

**Status:** Permanent, part of the Company DNA (`COMPANY_DNA.md`). The directive's 10 required fields per strategic decision are checked here against `decision_engine/types.py::Decision` — this company's real, already-existing decision record — field by field, not assumed to match.

---

## The 10 required fields, checked against the real record

| # | Required field | Real coverage |
|---|---|---|
| 1 | Objective | `Decision.niche` + `Decision.ai_ceo_decision` (BUILD/IMPROVE/WAIT/REJECT/PIVOT) |
| 2 | Supporting evidence | `Decision.reasoning` (explicit, human-readable, never a bare status) + `Decision.evaluation_snapshot` (the full real evaluation output, for reproducibility) |
| 3 | Commercial impact | `Decision.opportunity_score` (`profit_oracle`'s tier-aware composite, ADR-026, or the ladder-fast-gate score, ADR-066 — always on the same 0–100 scale) |
| 4 | Technical impact | **Real, partial gap** — `evaluation_snapshot` carries real technical-readiness signal where the evaluation path produced one; not a named, separate field on every decision |
| 5 | Financial impact | `capital_allocation_engine.py::investment_score()`'s `expected_revenue` (real closed-sale revenue to date — never a forecast, honestly) |
| 6 | Customer impact | `capital_allocation_engine.py::investment_score()`'s `customer_impact` (`value_engine.compute_value_profile()`'s `expected_customer_value`) |
| 7 | Risk analysis | `strategic_intelligence_core.strategic_score()`'s `risk` dimension, threaded through `investment_score()` |
| 8 | Opportunity cost | `capital_allocation_engine.py::opportunity_cost()` — real, named: which higher-ranked real opportunity this decision's resources are effectively going to instead |
| 9 | Expected ROI | `Decision.expected_outcome` (added ADR-143) + `investment_score()`'s composite |
| 10 | Long-term alignment with Company DNA | `Decision.alternatives_rejected` (added ADR-143) + direct citation of `DECISION_FILTERS.md`'s 6 filters, which every real decision has already been run through before it reaches this record |

**8 of 10 fields already have real, direct coverage. 1 (Technical impact) is a partial, disclosed gap — evaluated only when the evaluation path itself produced a technical signal, not guaranteed on every record.**

## Real, permanent evidence: `alternatives_rejected` and `expected_outcome`

These two fields (`decision_engine/types.py::Decision`, added in the Autonomous Company Evolution Engine round, ADR-133/143) are the real, structural answer to "no recommendation without evidence" applied specifically to *why not the alternative* — a decision record that only states what was chosen, never what was rejected and why, is an incomplete decision by this company's own standard.

## Outcome tracking — closing the loop

A Decision Protocol that never checks whether its own predictions came true is not a real protocol. `decision_engine/feedback.py::sync_outcomes()` (already real) matches real sales events back to the decisions that predicted them, real, not assumed — `data/decision_outcomes.jsonl` is that real record. `decision_engine/learning.py::recalibration_report()` computes real per-dimension historical-evidence statistics from it — deliberately never auto-applied (a real, disclosed gap: it "needs a separate decision to apply it," never silently adjusting scoring on its own).

## No recommendation without evidence — enforced, not just written down

Every field above traces to a real, cited source or is honestly marked as a partial/known gap. This document adds zero new fields to the real `Decision` record — its only job is proving, field by field, that the directive's own requirement was already being met before this document existed to say so.

---

*See also: `EXECUTIVE_BRAIN.md`, `EXECUTIVE_COUNCIL.md` (who reviews these decisions), `EXECUTIVE_MEMORY.md` (where they're permanently kept), `INTEGRITY_RULES.md`.*
