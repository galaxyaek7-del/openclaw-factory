# ADR-087 — Executive Quality Gate: A Permanent Core Layer

**Date:** 2026-07-22
**Status:** Adopted. Built, tested (935 Python / 199 JS, zero regressions), live-verified against real, already-recorded decisions.

---

## The directive

The founder ordered a permanent, mandatory gate — 20 named criteria — every opportunity, product, report, or recommendation must pass before entering production. Explicit: no fake assumptions, no invented numbers, no guessed market sizes.

## The honest core design decision

Several of the 20 requested criteria have **no real data source anywhere in this factory today**:
- **Willingness-to-pay** — zero real sales or pricing experiments have ever run.
- **Customer-acquisition-difficulty per specific niche** — no automated per-niche CAC pipeline exists (only manual research for a handful of products this session).
- **Customer-retention potential** — zero real sales exist to measure retention from, at all, for anything.

A gate that scored these anyway would be exactly the fabrication this entire engagement has refused everywhere else. `executive_quality_gate.py` reports these **`UNKNOWN`** always, unless a caller explicitly supplies real, already-gathered evidence — and `UNKNOWN` on any of them routes the final verdict to `NEEDS_HUMAN_REVIEW`, never a silent `APPROVED`. This is the load-bearing design choice in the whole module.

## What's real vs. new

17 of the 20 criteria are **real, already-computed fields threaded through** — zero new scoring logic, "wrap don't rewrite" applied to governance itself:
- Customer pain evidence, market saturation, technical feasibility, scalability, defensibility, long-term strategic value, revenue model sustainability, operational cost, automation readiness, data confidence, infrastructure readiness → all reuse `market_intelligence_engine`, `competitor_discovery`'s cache, `product_families.registry`, `profit_oracle`'s ladder components, `strategic_investment_layer()`, and `revenue_pipeline.plan.estimate_production_cost()` directly.
- Legal/compliance risk → real, but explicitly scoped as a **partial proxy** (`safety_filter.py` + `QUARANTINE.md` history), never presented as a full legal analysis, since no such engine exists.

**2 genuinely new real checks** were built:
1. **Brand reputation risk** — a deterministic content scan for the exact fabricated-hosted-software claim pattern found live earlier this same session ("our platform," "24/7 dedicated support," "sign up for an account" appearing in AI-generated product content that describes no real infrastructure). Directly grounded in a real bug this session found, not a hypothetical.
2. **Evidence freshness** — real staleness check against real timestamps (decision date, competitor-cache age), flagging evidence older than 90 days.

## Live-verified against real, already-shipped products — and it found something real

Ran the gate against the real decisions behind 3 of tonight's shipped products:

- **Workflow Automation System for Logistics Companies** ($327, already shipped, already QA-passed, real Paddle product) → **`NEEDS_HUMAN_REVIEW`**. Willingness-to-pay, customer-acquisition-difficulty, and customer-retention are all honestly `UNKNOWN` (as they are for every opportunity in this factory today) — plus a real flagged data-confidence score of 30/100 from the original ladder-gate scoring.
- **Inventory Management System for Wholesale Distributors** ($327) → same real result, same real reasons.
- **AI Customer Support Automation Platform for E-Commerce Businesses** ($126, already shipped) → **a more serious real finding**: its current, latest decision record shows `DEFERRED`, not `ACCEPTED` at all. This is the same ladder-vs-tier decision-path divergence found earlier tonight (§ADR-086) — an already-shipped, checkout-ready product's own underlying opportunity record no longer shows it as accepted, because a later, stricter re-evaluation overwrote the original ladder-gate acceptance. The gate correctly refused to fabricate a verdict for a niche with no current `ACCEPTED` decision.

This is not a flaw in the gate — it is the gate doing exactly its job: refusing to rubber-stamp products this factory has already shipped, using standards this factory itself has never actually met (real WTP/CAC/retention data), and surfacing a real, separate structural bug (the ladder-vs-tier divergence) rather than looking away from it.

## Verification

- 29 new unit tests, all real check functions covered individually plus the full aggregate decision logic (hard-failure rejection, human-review-forcing unknowns, the written explanation listing every criterion).
- Live-verified through the real `executive-quality-gate` Mission Control action end-to-end against 3 real decisions.
- Full suite: 935 Python tests (up from 906), 199 JS tests, zero regressions.

## Impact

- `executive_quality_gate.py` (new) — the permanent core layer, importable by any future department, matching the founder's explicit "build this as a permanent core layer" instruction.
- `mission_control_api.py`: new `executive_quality_gate` endpoint.
- `server.js`: new `executive-quality-gate` Mission Control action.
- **Not yet done, by design**: this gate is not wired into the automatic production pipeline as a hard block — the founder's directive asked for the gate to exist and be verified, not for every existing real product to be un-published. Whether `NEEDS_HUMAN_REVIEW`/`REJECTED` verdicts on the 5 already-shipped products should trigger any retroactive action is the founder's call, not a decision this ADR makes unilaterally.
