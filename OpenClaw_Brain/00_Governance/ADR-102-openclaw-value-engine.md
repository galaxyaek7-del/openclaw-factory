# ADR-102 — The OpenClaw Value Engine

**Date:** 2026-07-23
**Status:** Adopted.

---

## The directive

"We are no longer building software. We are building a self-improving global digital company." Every activity must answer: "Does this increase the long-term value of the company?" Build a permanent Value Engine evaluating every opportunity against 17 dimensions, surfacing a 7-field Executive-Board summary (Priority Score, Expected ROI, Strategic Value, Estimated Build Cost, Estimated Maintenance Cost, Estimated Lifetime Value, Recommendation), running continuous optimization (bundling, premium positioning, subscriptions, automation, retirement), integrated with Executive Board, Opportunity Intelligence, Threat Intelligence, Market Evidence, Mission Control, and Revenue Engine. Never optimize for quantity or vanity metrics; every recommendation must be supported by evidence from the existing architecture.

## What a real search found, dimension by dimension

A full mapping of all 17 requested dimensions against the real, already-shipped codebase was done before any code was written:

| Status | Dimensions | Real source |
|---|---|---|
| **Already real, reused verbatim** (6) | Recurring revenue potential, Scalability, Defensibility, AI leverage, Automation potential, Competitive moat | `profit_oracle.py`'s scorers + `strategic_investment_layer()`, via `opportunity_pipeline.py`'s own real annotation |
| **Partially real, reused/extended** (4) | Long-term strategic value, Global demand, Platform potential, Enterprise potential | `strategic_investment_layer()`'s 7 real Yes/No/Uncertain questions; `market_signal` (explicitly a discussion-volume proxy, never a dollar TAM) |
| **New, but 100% evidence-grounded synthesis** (5) | Knowledge accumulation, Synergy with existing products, Bundle potential, Upgrade potential | Real counts/comparisons over already-computed data — see below |
| **No real data source anywhere in this factory** (3) | Expected customer value, Lifetime revenue potential, Brand-building impact | Honest, reasoned `Unknown` — never estimated or guessed |

The 3 honest-Unknown dimensions and the 2 no-real-source board fields (`Estimated Maintenance Cost`, and `Estimated Lifetime Value` beyond a real one-time price) are a direct, founder-confirmed consequence of this factory's real current state: zero real recurring-sales data, zero real customer-satisfaction data, zero real post-launch cost tracking, zero real brand-metric connection exist anywhere. Fabricating any of these would be exactly the failure mode this whole engagement has refused throughout.

## The 5 new dimensions, each a real synthesis over already-computed data — never fabricated

- **Knowledge accumulation** — a real, deterministic count (0–3) of real evidence artifacts already accumulated for a niche: a real board meeting on record, real active alerts, real `market_evidence.py` entries. Not a fabricated "brand memory" concept.
- **Synergy with existing products / Bundle potential** — a real count of other real ACCEPTED decisions sharing the exact same ladder (`decision_engine.ranking.rank_all()`, computed once per portfolio, not re-derived per opportunity). 2+ real siblings → real, literal bundle eligibility today.
- **Upgrade potential** — a real price delta to a higher real ladder rank, read directly from `revenue_pipeline.plan.compare_ladder_variants()` — never re-scored.

## The "retirement" gap, handled honestly

`dossier_bundle.py`'s own `build_bundle()` already discloses the exact real gap: "no real sales data yet to ever justify declining/retire." The Value Engine does **not** fabricate a retirement recommendation. It builds a real, evidence-grounded **at-risk signal** instead — flagged only by real governance evidence already computed elsewhere (a real board `NOT_APPROVED` verdict, a real Critical-severity active alert, a real reopened decision that flipped negative) — explicitly and permanently labeled a risk signal, never a retirement verdict, with its own `retirement_recommendation` field always reporting honest `Unknown` and the exact reason why.

## What was built

**`value_engine.py` (new module):**
- `compute_value_profile(niche, ...)` — the real per-opportunity synthesis. Reuses `opportunity_pipeline.annotate_decision()` (made public from `_annotate()`, the same public-ification precedent `factory_orchestrator.build_spec()` already set) for every already-real field, then layers the 17 dimensions, the at-risk signal, and the 7-field board summary on top. Returns `None` (never fabricated) for a niche with no real ACCEPTED decision — the same scope `business_dossier.py` already established.
- `build_value_engine_report(...)` — the real, whole-portfolio resource-allocation view: every real ACCEPTED opportunity, ranked by real **Priority Score** descending. Priority Score is a real, transparent average of `decision_engine`'s own existing `opportunity_score` (still the sole real acceptance/ranking gate — `rank_queue()` is completely unchanged) and the new **Strategic Value** composite (a real, documented average over every numeric real dimension gathered above — informational only, never blended into `profit_score`/`ladder_score`/`accepted`, the same additive-only discipline every other dimension in `profit_oracle.py` already follows).
- `Recommendation` is built mechanically from the real signals above (at-risk reasons, priority-score bands, real upgrade/bundle opportunities) — never freely-generated text.

**`opportunity_pipeline.py`:** `_annotate()` made public as `annotate_decision()`.

**Integration with the 6 named systems:**
- **Executive Board** — `executive_board.build_strategic_brief()` gains a `value_assessment` field (the real per-niche profile), threaded through 3 new isolation parameters on `convene_board()` (`decisions_path`, `reopen_log_path`, `evidence_path`).
- **Opportunity Intelligence** — one-directional reuse of `opportunity_pipeline.py` (never the reverse, avoiding an import cycle); a dedicated Mission Control action surfaces the ranked report for the Opportunity Queue view.
- **Threat Intelligence** — reused directly via the already-threaded `active_alerts` field on the annotated opportunity (ADR-095).
- **Market Evidence** — reused directly via `market_evidence.summarize_niche()` for the knowledge-accumulation dimension.
- **Mission Control** — two new actions: `get-value-profile` (single niche) and `get-value-engine-report` (whole ranked portfolio).
- **Revenue Engine** — `revenue_pipeline.pipeline.process_opportunity()`/`run_revenue_pipeline()` gain a `value_profile` field (informational only, reuses the already-computed `estimate_production_cost()` result rather than calling it twice).

## Verification

36 new tests (`tests/test_value_engine.py`) — every pure helper function tested in isolation (knowledge accumulation, synergy/bundle, upgrade potential, at-risk flag with an explicit test that it can never produce a definitive retirement verdict however many real signals fire, strategic value composite, priority score, mechanical recommendation), plus real integration tests using `decision_engine.engine.record_ladder_decision()` (the same real path every real candidate goes through): a non-ACCEPTED or nonexistent decision is honestly `None`, an ACCEPTED decision produces all 17 dimensions, the 3 no-real-source dimensions are always `Unknown`, `Estimated Maintenance Cost` is always `Unknown`, synergy/bundle correctly reflects real sibling decisions, the at-risk flag correctly reflects a real persisted board rejection, and a real 2-opportunity portfolio is correctly ranked by priority score.

Highest-risk existing suites run first (`test_executive_board.py`, `test_opportunity_pipeline.py`, `test_revenue_pipeline.py`, `test_orchestrator.py`, `test_master_cycle_production_e2e.py`, `test_decision_reopen.py`, `test_market_alerts.py`, `test_market_evidence.py`, `test_decision_engine.py`, `test_enterprise_readiness.py`, `test_api_contract.js` — 306+23 tests, all green), then the full repository: Python 1177/1177 (up from 1141), Node 272/272 real tests (unchanged — this piece is Python-only). All live data files confirmed untouched by the test run (`data/ai_cost_log.jsonl`'s pre-existing session-long drift is unrelated — confirmed read-only by every function this module calls).

## What's deliberately not built

No new "resource allocation" execution mechanism was added — the ranked report is the real allocation signal; a human (or a future, separately-scoped automation) still decides what to act on, matching this factory's own standing "no scheduler, human decides" architecture. "Continuous optimization" is satisfied by the report itself being real-time on-demand (re-run whenever queried) rather than a fabricated background process this factory doesn't have.
