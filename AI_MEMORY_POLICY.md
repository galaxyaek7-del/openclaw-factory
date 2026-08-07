# Galaxy Forge — AI Memory Policy

**Date:** 2026-08-08 | Phase 18, Sections 18-23. Real citation over `global_search.py` (ADR-185), `executive_brain.py`, and `ai_capability/orchestrator.py` — not rebuilt.

---

## Section 18 — Search: the 7 named example queries

`global_search.py::search()` (ADR-185, extended into Mission Control's Ctrl+K command bar) is a real substring search over the 4,523-node Knowledge Graph, competitors, and generated products. Checked against the 7 example queries: real, structural queries like "What products have we tried?" (Product/ProductionRun nodes) and "Why did we reject this opportunity?" (Decision.reasoning) work today. Free-text semantic queries ("What do we know about this customer problem?") work only as literal substring matches — **no real semantic/embedding search exists** (confirmed by direct search; this factory has no vector database or embedding pipeline anywhere).

## Section 19 — Executive Memory in Mission Control

| Requested | Real panel |
|---|---|
| Recent Lessons | `OpenClaw_Brain/19_Lessons_Learned/` — not yet a dedicated panel, real files exist |
| Important Decisions | `decision-memory` (ADR-145) |
| Major Failures / Successes | `resilience-incidents`, `trust-audit-report` |
| Knowledge Gaps | `truth-first-compliance`, every Phase 12-18 document's own disclosed gaps |
| Contradictions | **`contradiction-report` — new this round** |
| Stale Knowledge | **`knowledge-staleness-report` — new this round** |
| New Strategic Insights | `executive-brief`, `eos-decision-feed` |

## Section 20 — AI Memory Safety

Already this factory's standing architecture: `executive_decision_memory.py::explain_decision()` returns real `Source`/`Timestamp`/`Verification`/`Confidence` alongside every retrieved decision — never a bare conclusion. `anti_bias_check.py` (Phase 16) mechanically re-checks retrieved evidence for staleness/small-sample/single-source weakness before any recommendation is finalized — the real, enforced version of "AI must reason over evidence rather than blindly repeat previous conclusions."

## Sections 21-23 — AI Council / Executive Brain / Commercial Engine integration

`executive_brain.py::build_executive_directive()` already computes real Historical Context (via `gfos.enterprise_timeline()`), Evidence, Previous Decisions/Outcomes, and Recommended Action in one real, arbitrated pass — confirmed live throughout Phases 12-17. **New this round**: `contradiction_engine.py` and `knowledge_decay.py` are real, callable, but **not yet wired into `executive_brain.py`'s own candidate-arbitration pass** — a real, scoped, disclosed follow-up (adding a Tier-N candidate citing an unresolved contradiction), not built this round to avoid re-touching `executive_brain.py`'s own tested arbitration logic inside an already-large round.

---

*See also: `KNOWLEDGE_EVIDENCE_MODEL.md`, `CONTRADICTION_ENGINE.md`, `KNOWLEDGE_DECAY.md`.*
