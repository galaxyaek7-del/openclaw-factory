# Galaxy Forge — Knowledge Graph Architecture

**Date:** 2026-08-08 | Phase 18, Sections 2-3 (ADR-208). `knowledge_graph/build.py` already IS this architecture — extended, not rebuilt.

---

## Real, live graph state (this round)

**4,523 real nodes, 4,323 real edges**, across 12 real node types (up from 11 — this round added `Competitor`):

| Node type | Count | Directive's closest named entity |
|---|---|---|
| Decision | 2,056 | Decision |
| MarketAnalysis | 1,986 | Market |
| Competitor | **181 (new this round)** | Competitor |
| Niche | 93 | Problem |
| ADR | 168 | Source |
| ProductionRun | 15 | Product |
| Proposal | 8 | Opportunity |
| Lesson | 7 | Lesson |
| ExecutiveDirective | 3 | Decision (executive-level) |
| PublishChannel | 4 | Platform |
| CouncilRecommendation | 1 | Decision (council-level) |
| AIProvider | 1 | AI Model |

## The 22 named entity types, mapped

| Requested | Real coverage |
|---|---|
| Customer, Customer Segment | **Not graphed** — 0 real customers exist |
| Problem | `Niche` |
| Market | `MarketAnalysis` |
| Country | **Not graphed** — no real country-level data exists (standing deferral) |
| Competitor | **`Competitor` — new this round** |
| Product | `ProductionRun` |
| Platform | `PublishChannel` |
| Technology, AI Model | `AIProvider` |
| Opportunity | `Proposal` |
| Partnership, Affiliate Program | **Not graphed** — real data exists (`business_development.py`, `affiliate_commerce/`) but not yet as graph nodes; a real, scoped, disclosed follow-up |
| Decision | `Decision`, `ExecutiveDirective`, `CouncilRecommendation` |
| Experiment | **Not graphed** — `commercial_experiments.py` (ADR-202) has 0 real experiments to graph yet |
| Transaction, Revenue Event | **Not graphed** — 0 real transactions exist |
| Failure, Risk | **Not graphed** — `resilience_monitor.py`'s real incidents exist but aren't yet nodes |
| Lesson | `Lesson` |
| Source | `ADR` |
| Evidence | Embedded as node attributes (e.g. `Competitor.category_reason`), not a distinct node type |
| Department | **Not graphed** — `gfos.py::department_registry()` has real data, not yet nodes |
| Agent | **Not graphed** — no real per-agent node type exists |

## The 17 named relationship types, mapped

| Requested | Real coverage |
|---|---|
| COMPETITOR_SOLVES_PROBLEM | **Real, new this round** |
| DECISION_BASED_ON_EVIDENCE | `cites` |
| DECISION_PRODUCED_RESULT / RESULT_GENERATED_LESSON | `resulted_in` (Decision→Outcome) |
| PRODUCT_SOLD_ON_PLATFORM | `sold_as`, `published_via` |
| OPPORTUNITY_DISCOVERED_FROM_SIGNAL | `analyzed_by` |
| TECHNOLOGY_ENABLES_PRODUCT | Partial — `AIProvider` nodes exist, no explicit edge to `ProductionRun` yet |
| The other 11 named relations | **Not yet real** — no underlying data exists to create them honestly (0 real customers/transactions/partnerships as graphed entities) |

## What was deliberately not built this round

Per "do not create another isolated knowledge-base feature": no Customer/Transaction/Partnership/Department/Agent node types were added, because building them today would mean either graphing 0 real records (pointless) or graphing real data that already exists elsewhere without yet being connected (Partnership/Department) — real, scoped, disclosed follow-ups, not built speculatively in this already-large round.

---

*See also: `INSTITUTIONAL_MEMORY.md`, `KNOWLEDGE_EVIDENCE_MODEL.md`.*
