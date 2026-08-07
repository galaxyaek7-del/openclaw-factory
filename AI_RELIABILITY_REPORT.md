# Galaxy Forge — AI Reliability Report

**Date:** 2026-08-08 | Phase 14, Section 17. The directive asks for a 5-way epistemic distinction (FACT/OBSERVATION/INFERENCE/PREDICTION/UNKNOWN) in every AI-powered component. Research before writing anything: this factory already has multiple real, working implementations of exactly this discipline under different names — this report maps them, rather than building a 6th, competing vocabulary (the same naming-collision discipline this session has applied repeatedly).

---

## The real, existing mapping

| Directive's term | This factory's real, existing equivalent |
|---|---|
| **FACT** | A directly-observed, live value — e.g. `commercial_control_center.py`'s `ACTUAL` tier, `profit_oracle.py`'s `components_basis` dict tagging a component `"real"` (a live signal actually fed it) |
| **OBSERVATION** | A real measurement over time — e.g. `channels/ledger.py::revenue_trend()`, `health_trend.py`, `resilience_monitor.py`'s findings |
| **INFERENCE** | A derived conclusion from real facts — e.g. `goos.py::goos_score()`, `profit_oracle.py::ladder_opportunity_score()` — each a disclosed, mechanical formula over real inputs, never a black box |
| **PREDICTION** | A forward-looking claim — e.g. `strategic_intelligence_core.py::evaluate_strategic_horizons()`, honestly `"NOT ENOUGH EVIDENCE"` for every real horizon (30d/90d/1y/3y/10y) today — this factory has never fabricated a prediction it can't support |
| **UNKNOWN** | `truth_first.py::CANONICAL_VOCABULARY`'s 9 named terms (`NOT BUILT`/`NOT IMPLEMENTED`/`NOT CONNECTED`/`NOT MEASURED`/`UNKNOWN`/`WAITING FOR REAL DATA`/`SIMULATION`/`REFERENCE IMPLEMENTATION`/`PLANNED`) — the company's real, standing, enforced-in-practice disclosure vocabulary since ADR-160 |

**No new vocabulary was built.** `profit_oracle.py`'s `components_basis` dict (`"real"` vs `"estimated"`) is the closest direct analog to FACT-vs-INFERENCE already in production use, and `truth_first.py`'s vocabulary already covers UNKNOWN more thoroughly (9 named sub-cases) than a single generic term would.

## AI-generated recommendation traceability (the directive's own required 6 fields)

| Required field | Real citation |
|---|---|
| Input | `decision_engine.types.Decision`'s `evaluation_snapshot` |
| Evidence | `market_evidence.py`'s real evidence records; `profit_oracle.py`'s Proof of Payment gate (a real, human-cited source_url + quote, never fabricated) |
| Reasoning summary | `Decision.reasoning` (a real array of citation strings, live-verified this round against the EU AI Act niche's own 20-record history) |
| Confidence | `Decision.confidence`, `executive_decision_memory.py::_confidence_estimate()` (a disclosed heuristic, never a fabricated number) |
| Decision | `Decision.status` (ACCEPTED/DEFERRED/REJECTED) |
| Outcome | `decision_engine/feedback.py::sync_outcomes()`, `evolution_queue.py`'s real IMPROVED/DEGRADED/NO_CHANGE/NOT_ENOUGH_DATA measurement |

**Real, live-verified this round**: `executive_decision_memory.py::explain_decision(decision_id)` was confirmed (Phase 12/13 work) to actually return this full chain for a real decision — not asserted from documentation.

## The one real gap found this round

`decisions.jsonl`'s most recent formal record for the EU AI Act Compliance Toolkit niche (Phase 13 Finding F4) shows the AI decision pipeline concluding `DEFERRED` while a real product was shipped via a separate, human-directed evidence-gathering path. This is not an AI reliability *failure* in the sense of a hallucination or fabrication — the AI's own reasoning was honest and evidence-based at the time it ran (`"PAIN NOT ESTABLISHED"`, a true statement about the evidence available to that automated run). The real gap is a **traceability** one: the formal decision record was never updated to reflect the separately-gathered real evidence that later justified shipping. This is the same class of gap `executive_decision_memory.py::explain_decision()` is designed to close going forward, once a corrective decision record exists to explain.

---

*See also: `FAILURE_REGISTER.md` (F4), `OBSERVABILITY.md`.*
