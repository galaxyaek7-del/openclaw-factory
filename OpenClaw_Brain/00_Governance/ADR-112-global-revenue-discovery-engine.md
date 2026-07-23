# ADR-112 — Global Revenue Discovery Engine (Investment Pipeline)

**Date:** 2026-07-24
**Status:** Adopted.

---

## The directive

"The company must stop thinking like a software factory. It must think like an investment company." Continuously discover opportunities (expensive problems, underserved markets, premium customers, recurring revenue, enterprise, AI, automation, educational, digital asset opportunities) across every country, rank them using 10 named dimensions (Market Size, Competition, Urgency, Willingness To Pay, Production Difficulty, Long-Term Strategic Value, Defensibility, Recurring Revenue Potential, Global Scalability, AI Leverage), give every opportunity 12 named fields (Research, Commercial Score, Business Model, Estimated Revenue, Estimated Profit, Risk Analysis, Country Priority, Customer Profile, Recommended Product, Recommended Price, Recommended Distribution, Recommended Marketing), search globally including 8 named regions, output a permanent Investment Pipeline.

## Scope: the same regional ask, applied unchanged for the fifth time today

This is the fifth time the identical country/region search has appeared in a mission today (ADR-103 original; reaffirmed ADR-106, ADR-108, ADR-110; explicitly scoped out via AskUserQuestion minutes earlier in ADR-111, given a real, mission-text-internal conflict — Priority 2's named Chinese platform integrations are impossible without real credentials this factory doesn't have, directly contradicting that same mission's own "no fake data" rule). Nothing changed between ADR-111 and this directive to reopen that question, so `country_priority` is applied as an always-deferred field, unchanged, without a fresh AskUserQuestion.

## What was found before building

The 10 named ranking dimensions and 12 named per-opportunity fields were checked field-by-field against this factory's real, already-built intelligence before writing anything:

- **9 of 10 ranking dimensions already real**, reused verbatim from `opportunity_pipeline.annotate_decision()`: market_size, competition, willingness_to_pay (`market_evidence.py`), production_difficulty (technical_complexity), long_term_strategic_value (`strategic_investment.becomes_more_valuable_over_time`), defensibility, recurring_revenue_potential, global_scalability, ai_leverage.
- **1 genuinely new: urgency.** No dedicated real signal exists anywhere in this factory. Built as a disclosed, evidence-grounded proxy — real active `market_alerts.py` severity/count (an active Critical alert is a genuine time-sensitivity signal) — never a fabricated general urgency score, matching the same "real proxy, not a guessed absolute" discipline `market_size`'s own docstring already uses for discussion volume.
- **11 of 12 per-opportunity fields already real**: commercial_score (`opportunity_score`), business_model (customer_type ladder proxy), estimated_revenue/estimated_profit (`revenue_pipeline.plan.estimate_roi()`), risk_analysis (annotate_decision's risk field), customer_profile (`business_dossier.py`'s already-computed real evidence-count profile), recommended_product (`growth_engine.evaluate_product_multiplication()`), recommended_price/recommended_distribution (`revenue_pipeline.plan.build_production_plan()`, which already returns a real `recommended_platform` — "paddle" for ladder-tagged decisions, "gumroad_digital" otherwise — this factory's real distribution routing, unchanged since ADR-077), recommended_marketing (thin but real, `lib/publisher_seo.js`, already disclosed in ADR-108). "Research" was deliberately not built as a separate per-niche call: `research_department.build_research_report()` is a whole-factory trends aggregator, not niche-scoped, and every real research signal this directive could mean for a single niche (market/competitor/pain evidence) is already present in the same entry's other fields — a separate redundant field would have been exactly the duplication this session refuses.
- **1 deferred**: country_priority, for the unchanged reason above.

## What was built

**`investment_pipeline.py` (new)** — `build_investment_pipeline_entry(niche)` (returns `None`, never fabricated, for a niche with no real decision at all — a deliberately wider scope than `value_engine`'s ACCEPTED-only view, since discovery-stage opportunities are real investment candidates too) and `build_investment_pipeline()` (the whole-factory ranked view, reusing `decision_engine.ranking.rank_all()`'s own real order — cheap, no per-niche profile computation needed just to sort). Gained the same real, disclosed `limit=N` scale valve as `value_engine.build_value_engine_report()` (ADR-109). Wired into Mission Control: `get-investment-pipeline-entry` (per niche), `get-investment-pipeline` (whole factory, optional `{"limit": N}`).

## Verification

24 new tests (`tests/test_investment_pipeline.py` — 14, `tests/test_mission_control_api.py` — 4 new). Full regression: highest-risk suites first, then the full repository (Python + Node), then the API contract test.

## What's deliberately not built

- Country-specific search/profiles for any of the 8 named regions — unchanged reason, fifth occurrence today.
- A separate per-niche "Research" report call — already covered by this same entry's other real fields; would have duplicated existing intelligence.
