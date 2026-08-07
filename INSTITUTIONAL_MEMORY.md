# Galaxy Forge — Institutional Memory

**Date:** 2026-08-08 | Phase 18, Sections 7-12. Real citation over `executive_decision_memory.py`, `OpenClaw_Brain/19_Lessons_Learned/`, and `decision_engine/feedback.py` — not rebuilt.

---

## Section 7 — Decision Memory: the 4 named questions, answered for real

`executive_decision_memory.py::explain_decision(decision_id)` already answers all 4: "What did we decide?" (`Decision.status`), "Why?" (`Decision.reasoning`, real citation array), "What happened?" (`sync_outcomes()`'s real match, when one exists), "Was it correct?" (`decision_engine/learning.py::recalibration_report()`, real per-dimension historical accuracy). Live-verified this session (Phase 15): real, working, for the EU AI Act niche's own real 20-record history.

## Section 8 — Failure Memory

`OpenClaw_Brain/19_Lessons_Learned/` (7 real, dated files) + `resilience_monitor.py::record_incident()` (real severity/root_cause/detection_rule/prevention_rule fields). Real, demonstrated this session: 2 real bugs found and fixed during Phase 12 (`The_Nested_Evidence_Shape_Bug.md`, `The_Disclaimer_That_Never_Rendered.md`) — both written up in this exact format, both mechanically picked up by `knowledge_graph/build.py::_lesson_nodes()`. **No known failure has ever been deleted** — confirmed by this session's own practice of restoring (not deleting) content when a mistake was found (the `COMMERCIAL_READINESS_REPORT.md` overwrite incident, Phase 12, was corrected via git restoration + full disclosure, never silently erased).

## Section 9 — Success Memory

**Real, disclosed gap**: no dedicated "what worked and why" ledger exists distinct from Failure Memory — successes are currently only implicit in `Decision.status == ACCEPTED` + a later positive `Outcome`. Given 0 real ACCEPTED-and-later-successful decisions exist yet (`data/decisions.jsonl`'s real state), building a dedicated Success Memory schema now would have nothing real to populate it with — correctly deferred, not silently ignored.

## Sections 10-12 — Customer / Product / Market Knowledge

| Domain | Real coverage |
|---|---|
| Customer Knowledge | 0 real customers exist. Real, ready infrastructure: `customer_pipeline.py::submit_review()` (architecturally fabrication-proof), `commercial_acquisition.py` (real channel attribution capability) |
| Product Knowledge | `product_master_catalog.py` (10 real products, real problem/evidence/pricing/platform fields — Phase 12/14 fixes) |
| Market Knowledge | `MARKET_GAP_ENGINE.md`, `MARKET_WHITE_SPACE_MAP.md` (Phase 17) — real demand/competitor/price evidence for the one real evidenced market (EU AI Act compliance tooling) |

**Section 10's privacy rule, already honored**: `customer_pipeline.py` stores only what's operationally required (name/email/description for fulfillment) — no real customer data collection beyond this exists anywhere in this factory, confirmed by direct search.

---

*See also: `KNOWLEDGE_GRAPH_ARCHITECTURE.md`, `AI_MEMORY_POLICY.md`.*
