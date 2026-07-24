# ADR-115 — Complete Autonomous Company Master Loop

**Date:** 2026-07-24
**Status:** Adopted.

---

## The directive

"Do NOT create another isolated engine. Audit the entire OpenClaw architecture and identify every existing module already built. Create ONE permanent master execution loop that connects every existing capability into one continuous commercial lifecycle" — 20 named stages, from Global Opportunity Discovery through Automatic Discovery of the Next Opportunity. "Never duplicate existing logic. Reuse every existing module. If an existing module already performs a task, connect it instead of rebuilding it." Mission Control must always know Current Opportunity/Product/Stage/Revenue/Learning/Next Action. "The company must never stop after one completed product."

This directive is explicitly different in kind from the seven that preceded it today — it is a correction, recognizing (correctly) that this session had built a real, growing number of separate modules (`market_memory.py`, `growth_engine.py`, `commercial_intelligence.py`, `investment_pipeline.py`, `portfolio_engine.py`, `production_blueprint.py`, plus `execution_status.py`/`scheduler.py` from a day earlier) with real, if disclosed, overlap between them. This ADR is the audit-and-consolidation response.

## The audit (the directive's own step one)

Rather than re-run another expensive multi-agent research pass, this audit was synthesized directly from this session's own extensive, first-hand work building every one of these modules today, cross-checked against the 2026-07-23 System Integration Audit. The full 20-stage → real-module mapping is documented as executable code in `master_loop.py`'s own module docstring (not just this ADR, so it can never silently drift from the real registry the way ADR-026's supersession did before that earlier audit caught it):

| # | Stage | Real owning module |
|---|---|---|
| 1 | Global Opportunity Discovery | `market_hunter.py` / `golden_hunter/hunt.py` |
| 2 | Market Intelligence | `market_intelligence_engine.py` |
| 3 | Executive Decision | `decision_engine/engine.py` + `executive_board.py` |
| 4 | Portfolio Selection | `portfolio_engine.py` (ADR-113) |
| 5 | Investment Priority | `value_engine.py` / `investment_pipeline.py` (ADR-102/112) |
| 6 | Product Blueprint | `production_blueprint.py` (ADR-114) |
| 7 | Production Pipeline | `production_blueprint.classify_production_pipeline()` |
| 8 | Product Generation | `book_generator.py` / `orchestrator/engines/production.py` |
| 9 | Quality Gate | `inspectors.py` (Dual Inspection) + `executive_quality_gate.py` |
| 10 | Commercial Packaging | `dossier_bundle/build_bundle.py` (`build_product_dossier_bundle()`) |
| 11 | Store Selection | `growth_engine.evaluate_channel_expansion()` / `revenue_pipeline/plan.py` |
| 12 | Automatic Publishing | `distributor.py` / `channels/*` |
| 13 | Marketing Execution | `lib/publisher_seo.js` (real, thin — SEO metadata only, ADR-108) |
| 14 | Sales Monitoring | `scripts/poll_sales.py` / `channels/ledger.py` |
| 15 | Customer Feedback | `production_evidence/record.py` (real, honest gap — no channel) |
| 16 | Knowledge Update | `knowledge_graph/build.py` (ADR-106) |
| 17 | Market Memory Update | `market_memory.py` (ADR-106) |
| 18 | Revenue Engine Update | `revenue_pipeline/pipeline.py` + `channels/ledger.py::reconcile_ledger_to_finance()` |
| 19 | Executive Learning | `decision_engine/learning.py` (real, factory-wide, not niche-specific) |
| 20 | Automatic Discovery of Next Opportunity | `scheduler.py::decide_next_actions()` (real, on-demand recommendation) |

## Scope: "never stop" / "permanent heartbeat" is the same standing decision, applied a third time

"The company must never stop after one completed product" and "the Master Loop becomes the permanent heartbeat" restate the live, always-on process question already declined via AskUserQuestion in ADR-107 and reaffirmed in ADR-110. Applied unchanged: `master_loop.py` builds the real, callable orchestration functions; it starts no process, schedules no re-run, and does not auto-execute production or publishing. Every stage that spends real money or touches a real external platform keeps its existing human-confirmation gate.

## What was built — deliberately almost no new logic

Per the directive's own explicit rule, `master_loop.py` contains close to zero new business logic:

- **`trace_lifecycle(niche)`** — reuses `production_blueprint.build_production_blueprint()` and `value_engine.classify_lifecycle_stage()` directly, remapping their already-computed real evidence onto the 20 named stage labels. Several of the 20 names collapse onto the exact same real underlying signal in this factory today (e.g. stages 8-10 — Product Generation/Quality Gate/Commercial Packaging — all resolve from the same real `premium_production` evidence; stages 14/16/17/18 — Sales Monitoring/Knowledge Update/Market Memory Update/Revenue Engine Update — all resolve from the same real `market_memory` sample-size check) — reported honestly as shared evidence with a stated reason, never split into 20 independently-fabricated booleans this factory cannot actually distinguish yet. Stages 19 and 20 are real but factory-wide, not niche-specific, and are reported as `reached: None` rather than forced into a fabricated per-niche answer.
- **`mission_control_heartbeat()`** — the real 6-field heartbeat, built as a thin reuse of `scheduler.decide_next_actions()`'s real `run_now` pick (Current Opportunity/Next Action), `production_blueprint.build_production_blueprint()` (Current Product/Stage), `mission_control_api._revenue()` (Current Revenue, real defaults, matching that action's own existing convention), and `market_memory.monthly_evolution_report()` + `decision_engine/learning.recalibration_report()` (Current Learning).

Wired into Mission Control: `get-lifecycle-trace` (per niche), `get-mission-control-heartbeat` (whole factory).

## Verification

13 new tests (`tests/test_master_loop.py` — 9, `tests/test_mission_control_api.py` — 4 new). A real, live smoke test against this factory's actual current data confirmed `mission_control_heartbeat()` runs cleanly end-to-end before isolated unit tests were written. Full regression: highest-risk suites first, then the full repository (Python + Node), then the API contract test.

## What's deliberately not built

- No live, always-on "heartbeat" process — unchanged standing decision, third confirmation today.
- No new scoring, evidence, or classification logic anywhere in this module — every real signal is reused, never re-derived.
- No automatic execution of production/publishing from the Master Loop — the same human-confirmation boundary every prior mission today has kept.
