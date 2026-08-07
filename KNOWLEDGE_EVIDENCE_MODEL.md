# Galaxy Forge — Knowledge Evidence Model

**Date:** 2026-08-08 | Phase 18, Sections 4-6. Real citation over `evidence_engine.py` (ADR-163), `truth_first.py` (ADR-160), and `multi_source_intelligence/types.py`'s `ConnectorResult` — not rebuilt.

---

## Section 4 — The 11 named per-item fields

| Requested | Real coverage |
|---|---|
| Knowledge ID | `evidence_engine.py`'s deterministic IDs (reuses `decision_engine.types.make_decision_id()`'s hashing precedent) |
| Type | `evidence_engine.py`'s 10 named types (EXECUTION/TEST/PUBLICATION/MARKET_RESEARCH/AI_DECISION/AUTOMATION/FINANCIAL/CUSTOMER/SYSTEM/SECURITY) |
| Content | The real ledger record itself |
| Source / Source URL | `ConnectorResult.source`, real URLs where the connector's own API returns one |
| Timestamp | Real, on every ledger event |
| Created By | **Partial** — no explicit "created by (human/AI/system)" tag exists uniformly; inferable from which module wrote the record |
| Confidence | `ConnectorResult.confidence`, `Decision.confidence` |
| Verification Status | `ConnectorResult.verification_status` (`VERIFIED`/`UNKNOWN`/`BLOCKED`/`NOT_ARCHITECTED`) |
| Related Entities | Knowledge Graph edges (`KNOWLEDGE_GRAPH_ARCHITECTURE.md`) |
| Last Updated | Real, per-event timestamp (append-only — "updated" means a new event, never an edit) |

**"Do not allow anonymous critical knowledge"**: already true architecturally — every real ledger write in this factory carries a real, non-anonymous source function/module (confirmed throughout this session's own append-only-ledger discipline).

## Section 5 — Evidence classification: 6 named states, mapped

| Requested | Real equivalent |
|---|---|
| VERIFIED | `multi_source_intelligence`'s `VERIFIED` |
| SUPPORTED | Real, partial — `profit_oracle.py`'s multi-signal-agreement gates are the closest real analog (2+ independent real signals must agree) |
| INFERRED | `goos.py`'s disclosed heuristic scores (real formula over real inputs) |
| PREDICTED | `strategic_intelligence_core.py::evaluate_strategic_horizons()`, honestly `"NOT ENOUGH EVIDENCE"` for every real horizon today |
| UNKNOWN | `truth_first.py`'s 9-term vocabulary |
| **CONTRADICTED** | **Real, new this round** — `contradiction_engine.py` (ADR-208) is the first real mechanism in this factory to produce this exact state |

**"Never allow an inference to silently become a verified fact"**: enforced structurally — `profit_oracle.py`'s Proof of Payment gate requires a real, human-cited source+quote before a niche can be ACCEPTED; an inferred score alone (however high) cannot cross this gate.

## Section 6 — Confidence, qualitative not manufactured

Already this factory's standing discipline: `capital_allocation_engine.py`'s `confidence` fields are real strings ("low"/"medium"/"high"), never a fabricated decimal. `anti_bias_check.py` (Phase 16) is the real, mechanical enforcement of "consider source quality/independent sources/recency/consistency/contradictory evidence" — 7 real checks, composed into every Phase 16-18 recommendation.

---

*See also: `evidence_engine.py`, `CONTRADICTION_ENGINE.md`, `AI_MEMORY_POLICY.md`.*
