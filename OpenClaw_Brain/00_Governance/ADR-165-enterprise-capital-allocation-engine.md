# ADR-165 — Enterprise Capital Allocation Engine

**Date:** 2026-07-31
**Status:** Adopted. Extends the real, already-live 14-dim Investment Score (ADR-139) — never a second, duplicate engine.

---

## Numbering note

The founder's directive labeled itself "ADR-163" — already allocated (Enterprise Evidence Engine, committed `dac990a`). Real next number: **ADR-165** (ADR-164 was the immediately preceding round, AI Automation Revenue Engine) — same renumbering convention this session has now applied twice today.

## The directive (verbatim, condensed)

> ADR-163 — Enterprise Capital Allocation Engine
>
> The company must always invest its time, compute, automation capacity and development effort into the highest long-term return opportunities. Build Enterprise Capital Allocation Engine — manages every strategic resource, not just money: Founder attention, Development time, AI compute, Automation capacity, Research capacity, Publishing capacity, Marketing effort, Infrastructure, Cash, Human review time.
>
> Every project receives an Investment Score, calculated using only measurable evidence, across: Expected ROI, Strategic importance, Recurring revenue potential, Development effort, Maintenance cost, Automation percentage, Market maturity, Competition, Customer demand, Legal risk, Operational risk, Technical complexity, Scalability, Knowledge reuse, Long-term asset value.
>
> The engine must continuously answer: where to invest next, which projects deserve more resources, which should pause, which should retire, which generate the highest long-term value. Mission Control must display Resource Allocation / Top Investments / Projects Starved of Resources / Projects Overfunded / Expected Long-Term ROI / Company Capacity Utilization.
>
> No fabricated investment scores, no subjective rankings — every recommendation exposes Evidence/Calculation/Confidence/Unknown factors. Truth First Constitution applies — if evidence is insufficient, return `"INSUFFICIENT EVIDENCE"` instead of ranking.

## Research: 12 of 15 named dimensions already directly covered by the real, existing Investment Score (ADR-139)

`capital_allocation_engine.py::investment_score(niche)` (2026-07-29) already computes, per real niche, `{value, source, reason}`-shaped: `recurring_revenue_potential`, `competition_level`, `automation_potential`, `risk`, `strategic_importance`, `long_term_asset_value`, `execution_complexity` (delegated to `strategic_intelligence_core.strategic_score()`) + `expected_revenue`, `customer_impact`, `market_defensibility`, `engineering_cost`, `maintenance_cost`, `knowledge_reuse`, `brand_value` (cited from `value_engine.compute_value_profile()`). 12 of this directive's 15 named dimensions map directly onto these — reused verbatim via injection, never recomputed.

- **2 real signals exist but were never cited**: `value_engine.compute_value_profile()`'s own `board_summary.expected_roi` and `dims.scalability` (from `global_scalability`) — real, already computed elsewhere in the same profile call, simply not previously exposed by `investment_score()`. Zero new computation to add them.
- **3 genuinely new dimensions**: Market maturity (no real per-niche product-lifecycle signal exists anywhere in this factory — `global_opportunity_exchange.market_health()` is real but company-wide marketplace-saturation, a different concept, cited as context only, never substituted); Legal risk (real, per-niche: `executive_quality_gate.check_legal_compliance_risk(niche)`, already-live, never before cited by capital allocation); Operational risk (real but company-wide only: `resilience_monitor.assess_resilience()`'s active alerts, not reliably niche-keyed — same honest limitation `executive_questions.py::_which_division_is_slowing()` already disclosed for a structurally identical signal).

`capital_allocation_engine.py::build_capital_allocation_dashboard()` (ADR-139) already has `top_roi_initiatives` (Top Investments), **`projects_consuming_resources_without_results`** (= "Projects Starved of Resources", same real `stuck_without_production()` concept), `expected_portfolio_return` (Expected Long-Term ROI) — all reused verbatim.

## What was genuinely new this round

1. **`resource_allocation_map()`** — the 10 named strategic resources. Real citations for 6: Founder attention/Human review time (`founder_console.build_founder_queue_partial()`'s real pending-decision queue), AI compute (`ai_capability/registry.py::list_providers()`'s real per-provider stats), Automation capacity (`autonomous_operations_status.py`'s real activity counts), Publishing capacity (`channels/publish_protection.py`'s real per-arm caps), Cash (`channels/ledger.py::revenue_trend()`). Honestly `INSUFFICIENT EVIDENCE` for 4, confirmed by direct search to have zero real tracking anywhere in this factory: Development time, Research capacity, Marketing effort, and Infrastructure (a real live check exists — `infrastructure_bridge.get_infrastructure_status()` — but is expensive/network-dependent and deliberately not called from this passive citation map by default; the real `infrastructure-status` panel is the correct place for that live signal).
2. **`capacity_utilization()`** — a real aggregator over the same resource citations. Never blends the 10 into one fabricated percentage — reports which have a real signal and which honestly don't.
3. **`projects_overfunded()`** — no prior real analog anywhere in this factory. A real, disclosed heuristic: real production-run-count per niche (`books/_generation_log.jsonl`) cross-referenced against real priority-score rank (`value_engine.build_value_engine_report()`) — high real spend + low real rank is surfaced first, cited transparently, never a fabricated verdict. Honestly `INSUFFICIENT EVIDENCE` when no real portfolio or no real production log exists.

## Validation

`python -m unittest tests.test_enterprise_capital_allocation -v` — 12/12 passing: all original 14 dims preserved unchanged through injection (no recomputation); `market_maturity` honestly `INSUFFICIENT EVIDENCE` per niche; all 10 named resources covered, 4 honestly `INSUFFICIENT EVIDENCE`; `capacity_utilization()` never fabricates a single blended percentage; `projects_overfunded()` honestly `INSUFFICIENT EVIDENCE` with no portfolio/production data, cites real data only when it has some; dashboard proven to call `capital_allocation_engine.build_capital_allocation_dashboard()` exactly once (the redundant-computation bug class this session has now guarded against explicitly in 4 separate rounds). Live-verified against real current data: `resource_allocation_map()` correctly returns 6 real signals + 4 `INSUFFICIENT EVIDENCE`. Full test suite re-run.

## A real, disclosed note on today's portfolio state

This round's live verification attempted to test `extended_investment_score()` against a real ACCEPTED niche and found none exist as of this ADR — see ADR-162's own "Addendum 2" (found during this round) for the full account: an earlier audit-tooling incident inadvertently downgraded all 4 of this factory's real ACCEPTED opportunities. This ADR's own logic and tests are unaffected (verified via injected fixtures, not live ACCEPTED data) — disclosed here for continuity, not re-litigated.
