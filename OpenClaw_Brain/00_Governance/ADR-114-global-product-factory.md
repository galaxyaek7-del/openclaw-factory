# ADR-114 — Global Product Factory (Production Blueprint)

**Date:** 2026-07-24
**Status:** Adopted.

---

## The directive

Every approved opportunity automatically generates a complete production blueprint with 15 named components (Product Specification, Product Architecture, Customer Persona, Customer Pain Map, Competitive Analysis, Unique Value Proposition, Pricing Strategy, Brand Position, Complete Production Checklist, Required AI Models, Required Human Review Points, Distribution Channels, Marketing Assets, Sales Funnel, Revenue Projection); each product auto-decides its production pipeline (12 named: SaaS, AI Agent, API, Online Course, Digital Bundle, Notion, Canva, Excel, Ebook, Design Assets, Prompt Pack, Automation Package); every product becomes a Production Mission tracked through 6 named states (READY TO BUILD, BUILDING, QUALITY REVIEW, READY TO SELL, LIVE, LEARNING); finished products automatically enter the Commercial Intelligence Loop.

## What this mission actually is: near-total overlap with the previous two missions

Checked before writing anything: the 12 named production pipelines are, almost 1:1, `portfolio_engine.py`'s 13 portfolio classes — built in the immediately preceding mission (ADR-113), the same session, minutes earlier. The 6 named production states are, near-exactly, a coarser regrouping of `value_engine.classify_lifecycle_stage()`'s 10 real stages — built earlier the same day (ADR-105/107). Re-deriving either as a second, parallel classification system would have been exactly the duplication this entire session has refused throughout. Both are reused directly.

- **`classify_production_pipeline()`** calls `portfolio_engine.classify_portfolio_class()` verbatim, then applies a thin, disclosed remap onto this directive's 12 names. Not a clean 1:1: 2 portfolio classes (Stock Images, Fonts/Icons/SVG Packs) have no target anywhere in this directive's own 12-name list and are reported as "no real match among the 12 named pipelines," never forced into a nearby one. "Templates" splits into Notion/Excel/Canva only when the decision's real, specific `product_family` disambiguates it (`notion_workspaces`→Notion, `spreadsheet_systems`→Excel); a generic `professional_templates` family stays honestly ambiguous — no real Canva-specific family exists in this factory to resolve it further.
- **`classify_production_status()`** calls `value_engine.classify_lifecycle_stage()` verbatim and remaps its real stage-reached booleans onto the 6 named states. One real, additional signal was needed to distinguish BUILDING from QUALITY REVIEW (lifecycle_stage's 10 stages don't separately track "currently under QA"): `inspectors.py`'s own real quarantine record (`_read_quarantined_niches()`, reads `QUARANTINE.md`) — a niche that has failed Dual Inspection and been logged there is reported as QUALITY REVIEW rather than plain BUILDING, using a real, already-existing signal rather than inventing a new one.

## What was found and reused for the 15 blueprint components

10 of 15 already real, reused verbatim: `product_architecture`/`customer_persona`/`pricing_strategy` from `business_dossier.py` (already computed inside `annotate_decision()`'s `business_dossier` field, unchanged since its original build); `customer_pain_map`/`competitive_analysis` from `annotate_decision()`; `unique_value_proposition` from `value_engine.classify_value_proposition()` (ADR-105); `required_ai_models` from `ai_capability.orchestrator.resource_allocation_status()` (ADR-110, real, zero-cost); `distribution_channels` from `growth_engine.evaluate_channel_expansion()` plus `revenue_pipeline.plan.build_production_plan()`'s real `recommended_platform`; `revenue_projection` from `growth_engine.growth_forecast()`, reused directly rather than a second, competing forecast. 2 small new real aggregations: `product_specification` (`factory_orchestrator.build_spec()`, a pure read-only transform, confirmed zero side effects before reuse) and `production_checklist` (names this factory's real, only Dual Inspection stages — `inspect_technical`/`audit_commercial` in `inspectors.py` — described, not executed, since a report has no real generated file to inspect). `required_human_review_points` reuses CLAUDE.md's own already-documented real fact: this factory does not auto-process Human-in-the-Loop approvals (`pending_review/queue/`, `scripts/process_approved_drafts.py` run manually).

2 of 15 have no real source anywhere in this factory today, honestly disclosed rather than fabricated: `brand_position` (no distinct concept separate from `unique_value_proposition`/competitive moat, both already surfaced elsewhere in the same blueprint) and `sales_funnel` (no real conversion/traffic tracking exists — the same gap `market_memory.py`'s own `conversion` field already discloses, ADR-106). `marketing_assets` is real but thin (SEO metadata only), already disclosed in ADR-108, restated here rather than silently re-described as complete.

"Every finished product automatically enters the Commercial Intelligence Loop so future products improve" was not rebuilt — `market_memory.py`'s real evidence accumulation and `knowledge_graph.py`'s `CommercialEvent` nodes (both ADR-106) already are this loop.

## What was built

`production_blueprint.py` (new): `classify_production_pipeline()`, `classify_production_status()`, `build_production_blueprint(niche)` (returns `None`, never fabricated, for a niche with no real decision), `build_production_missions_board()` (Mission Control's real, continuous 6-bucket view over every real ACCEPTED opportunity). Wired into Mission Control: `get-production-blueprint` (per niche), `get-production-missions-board` (whole factory).

## Verification

18 new tests (`tests/test_production_blueprint.py` — 14, `tests/test_mission_control_api.py` — 4 new). Full regression: highest-risk suites first, then the full repository (Python + Node), then the API contract test.

## What's deliberately not built

- No second portfolio-classification or lifecycle-state system — both reused verbatim from ADR-113/ADR-105.
- `brand_position`/`sales_funnel` — no real source, honestly disclosed.
- No live, auto-updating "Production Mission" process — `build_production_missions_board()` is real, on-demand, evidence-based, same on-demand-only decision as every other "continuous" ask today (ADR-107).
