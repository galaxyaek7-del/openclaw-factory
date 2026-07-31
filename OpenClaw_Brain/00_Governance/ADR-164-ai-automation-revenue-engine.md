# ADR-164 — AI Automation Revenue Engine (Truth-First)

**Date:** 2026-07-31
**Status:** Adopted. Real opportunity discovery/scoring engine built — zero product-generation code, per the directive's own explicit instruction.

---

## Numbering note

The founder's directive labeled itself "ADR-162" — that number is already allocated (Enterprise Truth Audit & Reality Certification, committed `0b80df8`/`8818935`). This round is the real next number, **ADR-164** — the same renumbering convention `CONSTITUTION.md`'s own amendment history already established for a prior misnumbered ask ("the task that built `inspectors.py` asked for it as 'Principle 23'... added as the actual next number, 17, instead of leaving an unexplained gap").

## The directive (verbatim, condensed)

> ADR-162 — AI AUTOMATION REVENUE ENGINE (TRUTH-FIRST)
>
> Build the company's first real revenue automation division. Non-negotiable rules: never fabricate capabilities/simulate non-existent integrations/invent customers/invent revenue/create fake analytics; every feature must state REAL/NOT IMPLEMENTED/FUTURE; every external integration must fail safely; every workflow must be auditable; every automation must be reversible; human approval remains mandatory for all production actions.
>
> Objective: create an Automation Revenue Division that discovers repetitive business work which can become premium AI automation products (workflow systems, n8n templates, business process/CRM/email/lead/support/reporting/knowledge/document/invoice/HR/sales/operations automation, internal AI copilots).
>
> **Do NOT build products. Build the ENGINE that finds opportunities.** Detect opportunities; score by market demand/competition/price potential/development cost/MRR potential/difficulty/AI feasibility/automation percentage; rank; recommend only high-value; reject saturated markets; detect B2B before B2C; prefer recurring revenue; explain WHY each opportunity was selected.
>
> Outputs (real infrastructure only): `automation_intelligence.py`, `automation_opportunity_scanner.py`, `automation_scoring.py`, `automation_catalog.py`, `automation_dashboard.py`. Do NOT generate fake opportunities — if no evidence exists, return `"NO VERIFIED OPPORTUNITY FOUND"`.
>
> Quality Gate: every recommendation must include Evidence Source/Confidence Score/Known Risks/Estimated Build Time/Estimated Selling Price/Potential Monthly Revenue Range/Reason for Recommendation. Never guess — if evidence is missing, say `"UNKNOWN"`.

## Research: this factory's real opportunity-discovery/scoring pipeline already covers most of what's asked

- **`product_families/mapping.py`** already has a real, registered `"automation_systems"` family, with real ladder→family mappings (`b2b_systems`, `automation_tools` → `automation_systems`) from the 2026-07-24 "Real World Commercial Expansion" round.
- **`market_hunter.py::SEED_CATEGORIES`** already includes 6 real automation-product candidate niches tagged with real ladders (`workflow automation system for logistics companies` / `b2b_systems`; `automated invoice processing toolkit for small businesses` / `automation_tools`; `AI customer support automation platform for e-commerce businesses` / `ai_saas`; and more).
- **`profit_oracle.py::ladder_opportunity_score(niche, ladder=...)`** (ADR-065/121/122/126) is already a real, comprehensive, ladder-aware composite scorer — real `market_demand`, `competition_favorability`, `profit_potential`, `recurring_revenue_potential` (by ladder), `reusability`, `automation_potential` (by ladder), `payment_evidence`, `confidence`, `risk`, and **9 real hard gates** (proof of payment, pain severity, competition floor, defensibility, price floor, recurring-revenue floor, AI-leverage, profit-margin floor, weighted-score floor) — effectively the real scoring engine this directive asks for, already built. Reused verbatim, never re-implemented.
- **`profit_oracle.py::AUTOMATION_POTENTIAL_BY_LADDER`**'s own real, documented finding: `ai_saas`/`b2b_systems` score LOW (40) real automation potential today — "need real hosting/user-DB/subscription-billing/ongoing-support infrastructure that does not exist in this factory today" — while `automation_tools` scores HIGH (90), since it already runs end-to-end on the real, existing `book_generator.py`/`product_families` pipeline. Cited honestly, never smoothed over.
- **`executive_quality_gate.py::check_market_saturation()`** — the real, existing "reject saturated markets" check, reused directly.
- **`revenue_pipeline.plan.estimate_production_cost()`** and **`profit_oracle.butter_price()`** — real sources considered for "Estimated Build Time"/"Estimated Selling Price"; see the honest gap disclosed below for build time specifically.

**Conclusion**: this round's real job is a themed citation/filter layer over this already-real pipeline, scoped to the automation-product category — not a new scoring algorithm, not a new discovery mechanism.

## A real design correction made proactively, informed by ADR-162's own addendum

`golden_hunter/hunt.py::run_hunt()` — the obvious first choice for "discover new opportunities" — was found, on direct inspection, to call `orchestrator.run_cycle(execute_production=False, ...)`. The `execute_production=False` flag only gates real PRODUCTION/PUBLISH, **not real decision recording** — `run_hunt()` genuinely appends new real decisions to `data/decisions.jsonl` every time it runs. This is exactly the class of bug ADR-162's own addendum disclosed (a real side effect from live-invoking a function that "looked" read-only). Rather than discover this the hard way a second time, `automation_opportunity_scanner.py` was designed from the start to **never call `run_hunt()`** — it uses only two real, passive sources: `market_hunter.py::SEED_CATEGORIES` (a real, static, deterministic list) and already-recorded real decisions (`decision_engine.ranking.rank_all()`, a pure read). A regression test (`test_never_calls_run_hunt`) enforces this permanently.

## What was built

- **`automation_catalog.py`** — the 15 named categories mapped to 3 real, already-live ladders (`ai_saas`/`b2b_systems`/`automation_tools`); every category maps cleanly, none needed a `NOT_IMPLEMENTED` fallback.
- **`automation_intelligence.py`** — `is_b2b()` (real ladder-tag + disclosed phrase-match heuristic), `reject_saturated()` (pure citation of `check_market_saturation()`), `automation_percentage()` (pure citation of `AUTOMATION_POTENTIAL_BY_LADDER`).
- **`automation_opportunity_scanner.py`** — `scan_candidates()`, the passive-only real scanner described above; honestly returns `NO VERIFIED OPPORTUNITY FOUND` when nothing matches.
- **`automation_scoring.py`** — `score_opportunity()`, relabels `ladder_opportunity_score()`'s real output onto the directive's named Quality Gate fields. **Estimated Build Time is honestly `UNKNOWN`** — this factory tracks real per-call AI *cost*, never real per-product build *duration* (a different unit; conflating them would be exactly the "optimistic description unsupported by code" this directive forbids). **Potential Monthly Revenue Range is honestly `UNKNOWN`** for the same reason: `recurring_revenue_potential` is a real, ladder-grounded 0–100 potential score, not a customer-volume forecast — multiplying it by an assumed customer count to produce a dollar range would be a fabricated number, explicitly forbidden; the real score itself is cited instead.
- **`automation_dashboard.py`** — `build_automation_dashboard()`, the one real aggregator: scans → scores → real B2B-first / ladder-score-descending sort → ranked list, or honestly `NO VERIFIED OPPORTUNITY FOUND` when every candidate fails a real hard gate.
- **Mission Control**: `automation-revenue-dashboard` (`SERVICE_REGISTRY`, no-input) + one panel in the existing Executive Overview group.

## Real, disclosed current finding

Live-verified against real current data: all 6 real automation-tagged seed candidates were scanned and scored; **all 6 honestly rejected** — every one fails `ladder_opportunity_score()`'s first real hard gate, "UNPROVEN — no real payment evidence recorded (Proof of Payment doctrine, ADR-121)." `build_automation_dashboard()` correctly returns `"NO VERIFIED OPPORTUNITY FOUND"` — the directive's own literal required string, not a failure of this engine but the honest, correct reflection of this factory's real current state (zero real payment evidence exists for any automation-product candidate today).

## Golden Rule check

CLAUDE.md's Golden Rule ("no expansion by a new product before the first real dollar from the current product") does not apply here the way it did to GCID (ADR-148, fully deferred) — this round builds a discovery/analysis **engine**, never a shipped product, the same precedent `Global Opportunity Exchange` (ADR-140) and `Capital Allocation Engine` (ADR-139) already established. "Do NOT build products" was honored literally: zero product-generation code, zero n8n template files, zero CRM automation code anywhere in this round.

## Validation

`python -m unittest tests.test_automation_revenue_engine -v` — 17/17 passing: catalog covers all 15 named categories, each mapped to a real ladder; `is_b2b()` correctly tags known B2B/B2C examples; `automation_percentage()` cites real constants, honestly `UNKNOWN` for an unrecognized ladder; scanner honestly returns `NO VERIFIED OPPORTUNITY FOUND` when mocked empty, and is proven to **never call `run_hunt()`**; scoring never fabricates build time or a monthly-revenue dollar range; dashboard proven to never call `run_hunt()`/`distributor.distribute()`; B2B-first ranking confirmed. Live-verified against real current data (see finding above). Full test suite re-run.
