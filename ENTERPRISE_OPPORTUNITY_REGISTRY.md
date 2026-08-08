# Galaxy Forge — Enterprise Opportunity Registry & Sales Pipeline

**Date:** 2026-08-08 | ADR-220, Phase 30, Sections 2-3, 11-13, 36. `enterprise_sales_engine.enterprise_opportunity_registry()` + `enterprise_sales_pipeline_view()` + `account_registry()` + `stakeholder_map()` + `enterprise_pipeline_priority()`.

---

## Section 2-3 — Opportunity Discovery + Registry (already real, cited)

`enterprise_opportunity_registry()` reuses `enterprise_transformation_engine.py::enterprise_problem_registry()` (Phase 24) directly — no 2nd registry was built. Real, current state: 0 real enterprise-sourced problems, since 0 real enterprise customers exist yet to source them from.

## Section 11 — Enterprise Sales Pipeline (real relabeling, 3rd this session)

`ENTERPRISE_PIPELINE_STAGES` — TARGET → DISCOVER → QUALIFY → DIAGNOSE → DESIGN → PILOT → PROPOSE → NEGOTIATE → CLOSE → IMPLEMENT → SUCCESS → RENEW → EXPAND (13 named stages). `enterprise_sales_pipeline_view()` maps `business_development.py`'s real 9-stage pipeline state (`SALES_STAGE_MAPPING`) onto this vocabulary — a 3rd relabeling this session of the same real underlying pipeline (after Phase 25's 11-stage `LIFECYCLE_MAPPING`), never a 4th competing pipeline. Live-verified: `amazon` (real stage `PREPARATION`) maps to `DIAGNOSE`; `paddle` (real stage `ACTIVE`) maps to `SUCCESS`. DIAGNOSE/DESIGN/PROPOSE/CLOSE/RENEW are honestly disclosed as having no real distinct signal in the underlying 9-stage pipeline — compressed, never forced.

## Section 12 — Account Registry (real schema, 0 real accounts)

`account_registry()` — 18 required fields (account_id, organization, industry, country, size, contacts, decision_maker, opportunity, products, contracts, revenue, recurring_revenue, health, risk, last_activity, next_action, owner, evidence). **0 real enterprise accounts exist** — confirmed via `business_development.py`'s real pipeline: every real platform is at `DISCOVERY` except Paddle (payment infrastructure) and Amazon (affiliate infrastructure), neither a real enterprise account.

## Section 13 — Stakeholder Map (real schema, never fabricates identity)

`stakeholder_map()` — 9 named roles (economic buyer, technical buyer, operational owner, end users, influencers, procurement, legal, security, executive sponsor), each honestly `UNKNOWN` until a real named contact exists. Same discipline `enterprise_transformation_engine.py::decision_maker_intelligence()` (Phase 24) already established — never assumes identity or authority without evidence.

## Section 36 — Enterprise Pipeline Priority

`enterprise_pipeline_priority()` tags each real account NOW/NEXT/NURTURE/STRATEGIC/BLOCKED/REJECTED from its real sales stage — CLOSE/IMPLEMENT → `NOW`, NEGOTIATE/PROPOSE → `NEXT`, everything else honestly `NURTURE`. Live-verified: both real tracked accounts (`amazon`, `paddle`) land at `NURTURE` — neither is a real enterprise sales relationship, disclosed rather than force-fit.

---

*See also: `ENTERPRISE_TRANSFORMATION_ENGINE.md`, `IDEAL_ENTERPRISE_CUSTOMER.md`.*
