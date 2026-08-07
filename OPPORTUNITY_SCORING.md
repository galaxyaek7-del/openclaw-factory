# OpenClaw / Galaxy Forge — Opportunity Scoring

**Status:** Permanent, part of the Company DNA (`COMPANY_DNA.md`). The directive's 9 named ranking factors checked against `profit_oracle.py` and `goos.py`'s real, already-built scoring dimensions field by field.

---

## The 9 requested factors, mapped to real scoring

| Requested factor | Real dimension |
|---|---|
| Market Pain | `goos.py`'s `real_customer_pain` dimension (`market_demand` score) + `executive_quality_gate.check_customer_pain_evidence()` |
| Buying Power | `willingness_to_pay` — `executive_quality_gate.check_willingness_to_pay()`'s real per-niche market evidence |
| Competition | `competition_level` — `competition_favorability` score + `executive_quality_gate.check_market_saturation()` |
| Defensibility | `difficulty_of_copying` — `value_engine.py`'s real `defensibility` scoring |
| Automation Potential | `automation_potential` — `strategic_intelligence_core.strategic_score()`'s automation dimension |
| Long-term Value | `long_term_asset_value` — `strategic_intelligence_core.strategic_score()`'s long-term-value dimension, plus `profit_oracle.py`'s Long-Term Strategic Asset hard gate (ADR-122/126) |
| Enterprise Value | `strategic_importance` — `strategic_intelligence_core.strategic_score()`'s strategic-value dimension |
| Recurring Revenue | `recurring_revenue_potential` — `NOT_MEASURABLE_PRE_ACCEPTANCE` until a real ACCEPTED decision exists (honestly disclosed, never estimated pre-acceptance) |
| Global Scalability | `scalability` — same `NOT_MEASURABLE_PRE_ACCEPTANCE` disclosure, plus `market_domination_engine.py`'s real, mostly-`NOT_MEASURABLE` regional-coverage citation (the founder's own standing 2026-07-23 deferral) |

**All 9 requested factors map to a real, named dimension.** Two (Recurring Revenue, Global Scalability) are honestly `NOT_MEASURABLE` before real acceptance — not because the scoring system is incomplete, but because scoring a hypothesis about revenue that doesn't exist yet would be exactly the fabrication `COMPANY_DNA.md` forbids.

## The real hard gates — where "never" actually means never

Four of `profit_oracle.py`'s real gates (ADR-121/122/126) are not scored on a sliding scale at all — they are pass/fail, and a fail ends evaluation regardless of how well everything else scores:

1. **Proof of Payment** — real, human-cited evidence someone is already paying to solve this exact problem. The single gate this company's own real history has never once relaxed.
2. **Pain Severity** — real customer-pain evidence at "high" or "medium" severity.
3. **Competitive Advantage** — net-positive real AI-leverage relative to a generic competitor.
4. **Long-Term Strategic Asset** — real, cited reason the opportunity compounds rather than being a one-time sale.

## "Never prioritize trends. Prioritize durable businesses." — the real, mechanical enforcement

This is not a stated preference — it is what the Long-Term Strategic Asset gate and the `recurring_revenue_potential`/`scalability` dimensions structurally reward over a trend-chasing, one-time-sale opportunity, even one with a higher raw `market_demand` score. `goos.py::rank_build_candidates()` (ADR-178) applies this same real, disclosed ranking to every currently-open candidate — see `GALAXY_FORGE_GOLDEN_HUNTER.md` for how the CEO sees the result.

---

*See also: `GOLDEN_HUNTER_ENGINE.md`, `OPPORTUNITY_PIPELINE.md`, `DECISION_FILTERS.md`, `PRIORITIZATION_ENGINE.md`.*
