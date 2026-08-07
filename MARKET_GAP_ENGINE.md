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

*See also: `MARKET_INTELLIGENCE_ENGINE.md`, `CUSTOMER_PAIN_ENGINE.md`, `COMPETITOR_INTELLIGENCE.md`, `DECISION_FILTERS.md`.*
