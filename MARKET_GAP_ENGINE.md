# OpenClaw / Galaxy Forge — Market Gap Engine

**Status:** Permanent, part of the Company DNA (`COMPANY_DNA.md`). The directive's 3 named questions ("why does this gap exist," "why hasn't anyone solved it correctly," "can OpenClaw solve it significantly better") checked against real, already-built evaluation dimensions.

---

## The 3 requested questions, mapped

| Requested question | Real mechanism |
|---|---|
| Why does this gap exist? | `goos.py`'s `market_size_tam_sam_som` + `willingness_to_pay` dimensions — a gap with no real evidence of either is honestly flagged `NOT_MEASURABLE`, not assumed to be a real opportunity |
| Why has nobody solved it correctly? | `competitor_discovery.py`'s real per-niche competitor scan + `goos.py`'s `competition_level` dimension — if real competitors exist and are succeeding, this is not an unsolved gap |
| Can OpenClaw solve it significantly better? | `profit_oracle.py`'s Competitive Advantage hard gate (ADR-122) — net-positive real AI-leverage relative to a generic competitor, required, never assumed |

## The real, proven example

The EU AI Act Compliance Toolkit's regulatory-currency correction is this engine's own answer to all three questions, already demonstrated: the gap existed because both real named competitors (`governancedocs.com`, `riskprofs.com`) used vague or stale enforcement-timeline language; nobody had solved it correctly because neither cited the real December 2027 deferral with a source; OpenClaw solved it significantly better by being the only toolkit in the niche with a citation-quality, currently-accurate answer — a real, verified differentiator, not a marketing claim.

## Why most real candidates fail this engine, honestly

`data/decisions.jsonl`'s real current state — 0 ACCEPTED, 46 DEFERRED, 41 REJECTED across 87 real evaluated niches — is this engine (and the gates feeding it) working as designed, not failing. A gap that looks real on the surface but has no real evidence of unmet demand, or where existing competitors are already succeeding, or where this company has no real, cited advantage, is correctly rejected. The Market Gap Engine's job is to reject convincing-sounding ideas that don't actually clear these three questions — and its real, measured track record shows it doing exactly that.

## What would make a gap genuinely count

All three questions answered with real, cited evidence — not two out of three, and never assumed for the third. `goos.py::rank_build_candidates()`'s own `duplicate_check` and `engineering_without_revenue_check` fields are the real, mechanical extension of this discipline once a candidate does clear the bar: even an accepted gap is checked against this company's own existing product family before being treated as genuinely new.

---

## Phase 17 update (2026-08-08, ADR-207) — the 10 named per-gap fields

The founder's "Global Intelligence & Competitive Moat Engine" directive (Section 6) named 10 fields for every identified gap: Problem/Affected Customer/Current Solutions/Solution Weakness/Evidence/Market Size Evidence/Willingness-to-Pay Evidence/Competition/Difficulty/Potential Revenue/Recurring Potential/Strategic Value/Confidence (12, not 10, on direct count). Checked against this document's own real mechanisms, field by field: Problem/Current Solutions/Solution Weakness/Evidence/Competition are real, covered by `competitor_discovery.py` + `goos.py`'s `competition_level`; Market Size Evidence is honestly `NOT_MEASURABLE` (ADR-042/043's standing, twice-confirmed finding — no free real TAM source exists); Willingness-to-Pay Evidence is `profit_oracle.py`'s real Proof of Payment hard gate (ADR-121) — the single strictest, most load-bearing real check in this factory; Potential Revenue/Recurring Potential/Strategic Value/Confidence are `capital_allocation_engine.py::investment_score()`'s real dimensions. **No new module was built** — every field this directive named already has a real, cited answer or an honestly disclosed gap in this factory's existing pipeline.

---

## Phase 23 update (2026-08-08, ADR-213) — Section 6's 10 named questions

The "AUTONOMOUS PRODUCT INNOVATION ENGINE" directive's Section 6 names 10 questions (what solutions exist / who provides them / cost / who buys / complaints / unsolved / workaround / unnecessarily complicated / unnecessarily expensive / missing). `product_innovation_engine.py::market_gap_and_competitive_view(niche)` answers them via a real, thin citation wrapper: `goos.py::evaluate_dimensions()` for the market-size/competition/WTP questions, `competitor_discovery.py::get_or_refresh_competitors()` (the real, cached per-niche competitor scan — never a fresh live call on every dashboard build) for the provider/cost/complaint questions. **No new module was built** — every question already has a real, cited answer or an honestly disclosed `NOT_MEASURABLE` in this factory's existing pipeline, same finding as the Phase 17 update above.

---

*See also: `MARKET_INTELLIGENCE_ENGINE.md`, `CUSTOMER_PAIN_ENGINE.md`, `COMPETITOR_INTELLIGENCE.md`, `DECISION_FILTERS.md`, `MARKET_WHITE_SPACE_MAP.md` (Phase 17), `PRODUCT_INNOVATION_ENGINE.md` (Phase 23).*
