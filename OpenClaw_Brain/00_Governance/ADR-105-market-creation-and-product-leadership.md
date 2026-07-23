# ADR-105 — Market Creation & Product Leadership: Value Proposition Gate + Product Lifecycle Tracker

**Date:** 2026-07-23
**Status:** Adopted.

---

## The directive

"OpenClaw does not wait for markets. OpenClaw creates markets." Every product must satisfy at least one of 6 named conditions (creates a new market, solves an expensive problem better, automates manual work, saves significant time/money, increases customer revenue, becomes an indispensable business asset). Every product lifecycle includes 10 named stages (global opportunity discovery → evidence-based validation → prototype → customer testing → premium production → commercial launch → continuous improvement → localization → global expansion → long-term maintenance). Success is measured by paying customers, customer transformation, recurring revenue, company valuation, digital asset value, and strategic competitive advantage — never by product count, commit count, model count, or vanity metrics.

## What this is, structurally

Most of this directive — "creates markets, doesn't wait for them," "continuously searches for emerging technologies/untapped industries/underserved niches," "every department thinks like an investor" — restates or extends doctrine already covered by the Global Opportunity Intelligence mission (ADR-092), the Live Competitive Intelligence mission (ADR-093–096), and the Strategic Investment Philosophy (ADR-103, which already explicitly deferred "untapped industries"/"underserved niches" beyond what real data connectors support). It is not re-litigated here. Two genuinely new, concrete, evidence-buildable pieces were identified: the 6-condition value proposition check, and the 10-stage lifecycle tracker.

## The 6-condition value proposition check

Added `value_engine.classify_value_proposition()`. **Informational only** — the same additive discipline every dimension in `value_engine.py` already follows; never a new accept/reject gate, never blended into `profit_score`/`ladder_score`/`accepted`. Reuses fields already computed elsewhere in the same profile, never a new measurement:

- `solves_expensive_problem_better` — real evidence from `pain_level` (customer-pain evidence, when the `ai_ceo_full_evaluation` decision path collected it) + `competitors_can_copy_it_easily` (from `strategic_investment_layer()`).
- `automates_manual_work` / `saves_time_or_money` — real evidence from the already-computed `automation_potential` dimension (≥60 threshold).
- `becomes_indispensable_business_asset` — real evidence from `strategic_investment_layer()`'s `can_evolve_into_software_business`/`can_create_a_product_ecosystem`.
- `creates_new_market` / `increases_customer_revenue` — **always honestly unsatisfied**, with the exact real reason: no real market-creation validation methodology and zero real customer-revenue-impact data exist anywhere in this factory today. Forcing either into a yes would be exactly the fabrication this whole engagement refuses.

`meets_minimum_bar` (satisfied_count ≥ 1) is reported transparently rather than silently enforced — a human reading the profile sees the real basis for every satisfied/unsatisfied condition, never a bare pass/fail.

## The 10-stage product lifecycle tracker

Added `value_engine.classify_lifecycle_stage()`. A real search found this didn't need new evidence-gathering at all: `production_evidence.record.build_evidence_record()` (already shipped, `validation_layer.lifecycle.build_lifecycle()`, ADR-053) already reconstructs Signal → Analysis → Decision → Queue → Production → Publishing → Revenue → Learning for any real niche purely from already-recorded sources. `classify_lifecycle_stage()` reuses it directly and maps its real fields onto the 10 named stages:

| Stage | Real evidence reused |
|---|---|
| Global opportunity discovery | `discovery_timestamp` (real orchestrator-timeline `market_intelligence` stage event) |
| Evidence-based validation | `decision.status` (real `decision_engine` record) |
| Prototype | `execution_status` (any real production attempt) |
| Premium production | `execution_status` with a real `SUCCESS` (Dual Inspection passed) |
| Commercial launch | `platform.succeeded` (a real successful publish attempt) |
| Continuous improvement | `enterprise_readiness.get_audit_trail()`'s real `changelog_entries` count |
| Customer testing | `customer_feedback` — **always honestly "not reached"**: `_extract_customer_feedback()` itself already discloses this factory has no connected review/feedback channel of any kind |
| Localization | **always honestly "not reached"** — no real localized data connector exists (ADR-103's own disclosed, deferred gap) |
| Global expansion | **always honestly "not reached"** — same ADR-103 deferral |
| Long-term maintenance | **always honestly "not reached"** — no real post-launch maintenance-cost tracking exists (ADR-102's own disclosed gap) |

`current_stage` reports the furthest real stage reached (in the fixed real order above), and `final_outcome` reuses `build_evidence_record()`'s own already-computed classification (`NOT_YET_EVALUATED` / `REJECTED` / `ACCEPTED` / `PRODUCED_NOT_YET_PUBLISHED` / `PRODUCED_AND_PUBLISHED_NOT_YET_SOLD` / `SOLD`) verbatim.

## Both fields flow automatically through every existing integration

`compute_value_profile()`'s return shape gained exactly two new top-level keys (`value_proposition`, `lifecycle_stage`) — no new wiring was needed anywhere. Every surface that already reuses `compute_value_profile()` (Executive Board's `value_assessment` lens, Revenue Engine's `value_profile` field, Mission Control's `get-value-profile`/`get-value-engine-report` actions) automatically carries both new fields the moment this shipped.

## "Success is measured by X, never by Y"

Documented as standing doctrine (this ADR); no dashboard/report currently presents product count, commit count, or model count as a headline "success" metric to begin with — the existing operational counts (`books_folder` count, etc.) are already framed as operational state, not success claims, so no code change was needed to comply.

## Verification

12 new tests (`tests/test_value_engine.py`, extending the existing 36) — `classify_value_proposition()`'s honest handling of the 2 no-real-source conditions, a real high-automation case satisfying 2 conditions, `classify_lifecycle_stage()`'s all-10-stages presence, a fresh accepted decision correctly reaching `evidence_based_validation` but not yet `prototype`/`premium_production`/`commercial_launch`, and the 4 no-real-source lifecycle stages always honestly unreached. One test's own initial assumption was found and fixed mid-build: `global_opportunity_discovery` requires a real orchestrator-timeline event (not just a decision record), which the test fixture (built via `record_ladder_decision()` alone, matching this whole session's own established isolated-unit-test convention) doesn't create — the test's expectation was corrected, not the source code.

Full regression: highest-risk existing suites first (`test_executive_board.py`, `test_opportunity_pipeline.py`, `test_revenue_pipeline.py`, `test_orchestrator.py`, `test_master_cycle_production_e2e.py`, `test_enterprise_readiness.py` — 163 tests), then the full repository.

## What's deliberately not built

No new "product lifecycle" state machine or enforcement mechanism — `classify_lifecycle_stage()` is a real, read-only classification over already-recorded evidence, not a new system that tracks or gates transitions. "Every department must think like an investor" etc. is pure doctrine, documented, not code.
