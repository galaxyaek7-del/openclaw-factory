# ADR-117 — Global CEO Decision Center

**Date:** 2026-07-24
**Status:** Adopted.

---

## The directive

Build the permanent CEO Decision Center — the highest authority of the company. Every hour, evaluate the entire company using verified data only, permanently answering 10 named questions (most profitable opportunity, opportunity to abandon, product deserving investment, country to prioritize, saturating market, strengthening niche, best AI model per department, highest real ROI products, wasted production pipelines, next commercial experiment). Automatically allocate resources across 10 named functions. Every decision includes Evidence/Expected ROI/Risk/Confidence/Priority/Reasoning/Recommended Action. Mission Control must display 8 named fields. "The CEO never sleeps."

## Scope: "never sleeps" is the same standing decision, applied a fourth time; country stays deferred

"Every hour" / "the CEO never sleeps" / "continuously reallocates" restates the live, always-on process question already declined via AskUserQuestion in ADR-107 and reaffirmed in ADR-110/ADR-115. Applied unchanged a fourth time: this module builds the real, callable functions; it starts no process. Question 4 (country priority) and the "China Division" allocation function apply the same standing deferral reaffirmed at every prior mission today.

## What was found and reused — including two real functions never wired into anything until now

Per the directive's own explicit rule ("Do NOT build another production engine... No duplicated logic. Reuse every existing engine"), `ceo_decision_center.py` is orchestration, not new scoring:

- Q1 (most profitable) / Q8 (highest ROI) → `investment_pipeline.py` (ADR-112)
- Q2 (abandon) / Q3 (more investment) / Q10 (next experiment) → `scheduler.py`'s existing cancel/accelerate/run_now buckets (ADR-107/110)
- Q7 (best AI model per department) → `ai_capability.orchestrator.resource_allocation_status()` (ADR-110), reused verbatim
- Q9 (wasted pipelines) → `production_blueprint.build_production_missions_board()`'s QUALITY REVIEW bucket (ADR-114) — a real production attempt that failed Dual Inspection and consumed real generation cost with no sale, the honest definition of "wasted" this factory can actually support
- **Q5 (market becoming saturated) / Q6 (niche becoming stronger) — two real, already-built functions this session had never connected to anything**: `competitor_discovery.py`'s `_score_competitor_saturation()`, `_score_market_concentration()`, `_score_new_entrant_trajectory()`. All three are real, pure, already-documented functions operating on a real competitor snapshot — simply never called from any of today's aggregation layers. Wired here for the first time, using exclusively `competitor_discovery.load_database()` (the real, cached snapshot store) — never `get_or_refresh_competitors()`, which can trigger a real live HN/GitHub network call. A read-only CEO report must never have a live side effect.

## Capital allocation — descriptive, never a fabricated budget

"Automatically allocate resources between" 10 named functions is built as a real, DESCRIPTIVE snapshot of where real opportunities and evidence currently concentrate (real counts per `portfolio_engine.py` class, real market-evidence-backed niche counts) — never a fabricated dollar figure. This factory has no live worker pool or payroll to actually reallocate; the honest analog this ADR ships is reporting where real attention already sits, which the founder can act on. A dedicated test (`test_never_reports_a_fabricated_dollar_amount`) asserts no dollar-shaped field appears anywhere in the snapshot.

## What was built

`ceo_decision_center.py` (new): `_market_saturation_and_strength(niche)` (the new competitor_discovery.py wiring), `answer_ceo_questions()` (all 10, real evidence only), `capital_allocation_snapshot()`, `ceo_dashboard()` (the real 8-field view; `company_health` deliberately not re-derived — referenced from `GET /health`). Confirmed live against this factory's real current data before any isolated unit test was written. Wired into Mission Control: `get-ceo-questions`, `get-capital-allocation-snapshot`, `get-ceo-dashboard`.

## Verification

14 new tests (`tests/test_ceo_decision_center.py` — 11, `tests/test_mission_control_api.py` — 3 new). Full regression: highest-risk suites first, then the full repository (Python + Node), then the API contract test.

## What's deliberately not built

- No live, always-on hourly evaluation process — unchanged standing decision, fourth confirmation today.
- No live competitor network calls from this module — only the real, cached snapshot store.
- No fabricated capital-allocation dollar figures — real counts only.
