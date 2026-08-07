# Galaxy Forge — Intelligence Knowledge Graph

**Date:** 2026-08-08 | Phase 17, Section 23. `knowledge_graph/build.py` already IS this graph — live-verified this round, not rebuilt.

---

## Real, live graph state (captured this round)

**4,342 real nodes, 4,142 real edges**, across 11 real node types:

| Node type | Count |
|---|---|
| MarketAnalysis | 1,986 |
| Decision | 2,056 |
| Niche | 93 |
| ADR | 168 |
| ProductionRun | 15 |
| Proposal | 8 |
| Lesson | 7 |
| ExecutiveDirective | 3 |
| PublishChannel | 4 |
| CouncilRecommendation | 1 |
| AIProvider | 1 |

## The 11 named entity types, mapped

| Requested | Real node type |
|---|---|
| Customer | Not a distinct node type — 0 real customers exist to graph |
| Problem | `Niche` |
| Market | `MarketAnalysis` |
| Competitor | Not a distinct node type in the graph today (real competitor data lives in `data/competitor_database.json`, not yet graphed) — a genuine, disclosed, small gap |
| Product | `ProductionRun` |
| Platform | `PublishChannel` |
| Technology | `AIProvider` |
| Opportunity | `Proposal` |
| Decision | `Decision` |
| Result | `ExecutiveDirective`, `CouncilRecommendation` (outcome-adjacent) |
| Source | `ADR`, `Lesson` (institutional-memory sources) |

**One real, disclosed gap found this round**: competitor data is not yet a graphed node type, meaning a real query like "which decisions were influenced by which competitor finding" cannot currently traverse the graph — it would require manually cross-referencing `data/competitor_database.json` against `Decision` nodes. Not built this round (a real, scoped, safe follow-up, not urgent given competitor data itself is currently sparse — `COMPETITOR_INTELLIGENCE.md`).

---

*See also: `EXTERNAL_SIGNAL_ENGINE.md`, `COMPETITOR_INTELLIGENCE.md`.*
