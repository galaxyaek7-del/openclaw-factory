# ADR-171 — Galaxy Opportunity Operating System (GOOS)

**Date:** 2026-08-05
**Status:** Adopted. A consolidation/citation layer over already-real evaluation systems — never a second decision engine, never a production gate.

---

## The directive (verbatim, condensed)

> GALAXY FORGE — FIRST EXECUTIVE MISSION
>
> Design and build the Galaxy Opportunity Operating System (GOOS). GOOS becomes the highest decision-making system inside Galaxy Forge. No digital product may enter production until GOOS has evaluated and approved it. Evaluate every opportunity across 20 named dimensions (real customer pain, TAM/SAM/SOM, willingness to pay, competition, difficulty of copying, scalability, recurring revenue, automation potential, global demand, AI leverage, development complexity, time to MVP, strategic fit, brand fit, long-term asset value, profitability, CLV, risk, legal risk, operational complexity). Produce a 15-section Opportunity Intelligence Report. Weighted score 0–100, minimum production threshold 85, below rejects with explanation. Self-improve from successful/failed launches, customer behaviour, market changes. Before writing code: design the architecture, challenge your own assumptions, identify weaknesses, propose improvements — only then implement.

## Two real conflicts flagged before any code (`AskUserQuestion`)

The directive's own instruction to "challenge your own assumptions... identify weaknesses" was honored literally, before implementation, matching this session's established precedent (ADR-147/157/161/169 all flagged real conflicts the same way).

**Conflict 1 — near-total duplication.** Research found GOOS's 20 named dimensions and 15-section report map onto real, already-built systems: `profit_oracle.py::ladder_opportunity_score()` (9 real hard gates + weighted score), `executive_quality_gate.py` (23 real checks — customer pain, willingness-to-pay, market saturation, technical feasibility, legal risk, defensibility, scalability, CAC, retention, infrastructure/automation readiness, and more), `strategic_intelligence_core.py::strategic_score()` (11 real dims), `capital_allocation_engine.py`/`enterprise_capital_allocation.py` (14/15-dim Investment Score), and `business_dossier.py`/`production_blueprint.py`/`autonomous_business_builder.py` (the real report sections — competitor map, risk assessment, ROI, pricing). Only **TAM/SAM/SOM** has zero real data source anywhere (`profit_oracle.py`'s own disclosed limitation: "No free real TAM data source exists... No guessed TAM"). Building a second, independent evaluation engine would be exactly the duplication this session has declined in every prior "unify everything" round (Executive Brain, GFOS, Executive Intelligence Layer, Enterprise Executive Brain).

**Conflict 2 — the 85/100 threshold is stricter than the real, currently-enforced gate.** `profit_oracle.py::MIN_OPPORTUNITY_SCORE = 65`; the tier-adjusted real acceptance floor is `65 / TIER_WEIGHTS["tier4"]` = 81.25 raw for tier4 (the loosest tier), stricter for tier1-3. GOOS's own 85/100 line is meaningfully tighter. Silently encoding a stricter real gate would be a substantive business-policy decision — with 0 real ACCEPTED opportunities existing today (the still-unresolved ADR-162 incident), a stricter bar makes that harder to ever clear, directly working against the "shortest path to revenue" priority set earlier this session.

**Founder's answers, both recommended:**
1. GOOS is a **consolidation layer**, not a parallel engine.
2. GOOS's own score is **advisory only** — it does not replace or tighten the real 65/100 weighted floor.

## What was built

**`goos.py`** (new, root):

- `DIMENSION_SOURCES` — all 20 named dimensions, each mapped to its real, already-existing source. TAM/SAM/SOM is `NOT_MEASURABLE`, disclosed with its real reason, never estimated.
- `evaluate_dimensions(niche)` — real, per-niche citation over `decision_engine.store`'s own real evaluation snapshot (the same record that already produced the niche's real ACCEPT/REJECT/DEFER verdict) — never a second evaluation. A niche with no real decision record returns `NOT_YET_EVALUATED`, never a guessed score.
- `goos_score(niche)` — a disclosed, additive advisory 0–100 score over only the dimensions with a real numeric value at evaluation time (typically 5 of 20 pre-acceptance: pain, competition, automation, strategic fit, profitability — market size, pre-acceptance scalability/revenue/global-demand/long-term-value, time-to-mvp, and brand fit are honestly excluded, not blended in as a guess). `meets_advisory_85_threshold` is informational only; `real_production_gate` explicitly states the real gate is unchanged.
- `build_opportunity_intelligence_report(niche)` — the one real aggregator producing all 15 named sections. Post-acceptance sections (Business Model, Revenue Potential, Estimated ROI, Competitor Analysis, Weaknesses) are only populated for a real ACCEPTED opportunity (`value_engine.compute_value_profile()`/`capital_allocation_engine.investment_score()`/`autonomous_business_builder.competitor_map()`/`risk_assessment()` all require one) — honestly `NOT_AVAILABLE` otherwise, computed exactly once each, never re-derived.
- `self_improvement_sources()` — pure citation of the 3 real learning mechanisms this factory already has (`decision_engine/learning.py::recalibration_report()`, `evolution_queue.py`'s real outcome measurement, `competitor_discovery.py`/`market_hunter.py`'s real live signal ingestion) plus `brand_dna.py`'s honest `FUTURE_INSTRUMENTATION` disclosure for real customer-question intake — never a 4th, competing learning loop.

**Mission Control:** `goos-evaluate-opportunity` (`ACTION_REGISTRY`, per-niche async, matches `strategic-score`'s exact shape) + command-palette entry. No `SERVICE_REGISTRY` panel — GOOS is inherently per-niche, not a no-input dashboard tile, same reasoning `investment-score`/`strategic-score` already established.

## What is explicitly NOT built

- No second scoring computation duplicating `profit_oracle.ladder_opportunity_score()` — every numeric dimension GOOS reports is read directly from the real snapshot that function already produced.
- No fabricated TAM/SAM/SOM, time-to-mvp, or brand-fit score — all three are honestly `NOT_MEASURABLE`/`NOT_EVALUATED`, confirmed to have zero real data source anywhere in this factory.
- No gating code path — `goos.py` never calls `decision_engine.store.append_decision()`, never touches `orchestrator`/`distributor`. "No product may enter production until GOOS approves" is honored as: GOOS's own `real_production_gate` field cites the exact same real gate that already exists, it does not add a second one.
- No real dollar CLV figure — `customer_lifetime_value` cites `executive_quality_gate.check_customer_retention_potential()`, disclosed explicitly as a proxy, since no real CLV computation exists anywhere in this factory.

## Validation

`python -m unittest tests.test_goos -v` — 13/13 passing: all 20 named dimensions present and correctly sourced; a never-evaluated niche returns `NOT_YET_EVALUATED` honestly; a missing snapshot field returns `None`, never a fabricated 0; the advisory score never claims to gate anything and only averages real numeric dimensions; the post-acceptance branch is proven to compute `value_engine.compute_value_profile()`/`capital_allocation_engine.investment_score()` exactly once each via mock call-count assertions; `self_improvement_sources()` proven to cite the 3 real existing mechanisms, never a 4th. Live-verified end-to-end: `POST /api/v1/actions/goos-evaluate-opportunity` against a real, currently-REJECTED niche via a disposable server — real advisory score 63.2/100 (correctly below both the 85 advisory line and the real 65 floor, consistent with the real REJECTED verdict), real 15-section report with honest `NOT_AVAILABLE`/`NOT_MEASURABLE` markers throughout. Zero new side effects (read-only against `decision_engine.store`, confirmed via the standing diff discipline).
