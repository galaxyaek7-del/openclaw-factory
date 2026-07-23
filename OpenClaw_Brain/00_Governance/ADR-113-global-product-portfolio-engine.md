# ADR-113 — Global Product Portfolio Engine

**Date:** 2026-07-24
**Status:** Adopted.

---

## The directive

Classify every opportunity into one of 13 named portfolio classes (Premium SaaS, AI Agents, AI APIs, Enterprise Automation, Premium Digital Products, Online Courses, Bundles, Templates, AI Prompt Packs, Design Assets, Stock Images, Fonts/Icons/SVG Packs, Books); compute 15 named metrics per opportunity; classify every opportunity into NOW/NEXT/LATER/REJECT following explicit priority rules (recurring > one-time, enterprise > consumer, AI software > templates, courses support software, books lowest priority); the portfolio stays dynamic and updates automatically; the Executive Board sees Top 100 worldwide, Top 50 China, Top 25 enterprise, Top 25 recurring revenue.

## Scope: the China/country ask, applied unchanged for the sixth time today

"Top 50 China" and "China suitability" restate the identical ask deferred five times already today (ADR-103, reaffirmed ADR-106/108/110/111/112). Applied unchanged, without a fresh AskUserQuestion — nothing changed to reopen it.

## What was found and reused before building

**13 portfolio classes checked against the real 11-family Universal Production Engine taxonomy** (`product_families.registry`): 7 map to a real family with real adapter status (Premium SaaS→ai_saas, AI APIs→api_products, Enterprise Automation→automation_systems, Premium Digital Products→digital_toolkits, Templates→professional_templates/notion_workspaces/spreadsheet_systems all three, AI Prompt Packs→prompt_libraries, Books→kdp_books); Online Courses maps only approximately to knowledge_bases, the same real-but-imperfect call this session already made for "Professional Courses" in ADR-111; 5 have no distinct real family (AI Agents, Bundles, Design Assets, Stock Images, Fonts/Icons/SVG Packs) and say so honestly.

**Class priority order is real, explicit founder policy, not invented scoring.** This directive's own literal rules ("premium recurring businesses always have priority," "enterprise ranks above consumer," "AI software ranks above templates," "courses support software," "books lowest") were encoded verbatim as a real, deterministic ordering constant — the same category of real business-policy constant `profit_oracle.LADDER_RANKS`/`LADDER_PRICE_BAND` already are, not a new evidence claim.

**NOW/NEXT/LATER/REJECT reuses `scheduler.py`'s existing real 5-bucket classification directly** (`run_now`/`accelerate` → NOW, `wait` → NEXT, `stop` → LATER, `cancel` → REJECT) — no second classifier built. Within each real bucket, entries sort by (class priority, real Priority Score), a real deterministic tie-break, never a new evidence claim.

**15 named metrics**: 12 reused verbatim via `investment_pipeline.build_investment_pipeline_entry()` (already covers market size, competition, defensibility, recurring revenue potential, and more from ADR-112); `development_cost` reused from `estimate_production_cost()`; `reusability_inside_company` read directly from the decision's own real, already-recorded `evaluation_snapshot.components.reusability`; `portfolio_diversification_impact` newly built as a real, evidence-based signal (inversely related to how many other real ACCEPTED opportunities already share the same class); `b2b_b2c` built as a real, coarse categorical proxy from the ladder rank (the same underlying classification `business_dossier.py`'s `_customer_profile()` already uses), never a fabricated numeric score. Two fields honestly disclosed as having no real source: `expected_monthly_recurring_revenue` (always `0` — zero real subscription sale has ever happened in this factory, though the structural capability is real, per ADR-108) and `time_to_market` (no historical duration-tracking model exists). `expected_annual_revenue` reuses `market_memory`'s real revenue-to-date, explicitly labeled as realized revenue, never an annual projection — the same honesty discipline `growth_engine.growth_forecast()` already established.

## What was built

`portfolio_engine.py` (new): `classify_portfolio_class()`, `class_family_status()`, `build_portfolio_entry(niche)` (reuses `investment_pipeline.build_investment_pipeline_entry()` for every already-real field), `build_portfolio_report()` (whole-factory view: Top 100 worldwide, Top 25 enterprise, Top 25 recurring revenue, Top 50 China always honestly empty). Wired into Mission Control: `get-portfolio-entry`, `get-portfolio-report`.

## Verification

24 new tests (`tests/test_portfolio_engine.py` — 20, `tests/test_mission_control_api.py` — 4 new). Full regression: highest-risk suites first, then the full repository (Python + Node), then the API contract test.

## What's deliberately not built

- Country priority / China suitability with real data — unchanged reason, sixth occurrence today.
- No live "dynamic" auto-updating process — the portfolio report is real, on-demand, evidence-based; making it update itself automatically would be the same live-scheduler question already declined in ADR-107, unchanged here.
