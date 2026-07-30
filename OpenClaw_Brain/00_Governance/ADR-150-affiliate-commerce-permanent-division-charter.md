# ADR-150 — Affiliate Commerce: Permanent Division Charter & Long-Term Roadmap

**Date:** 2026-07-30
**Status:** Adopted (documentation round — no new code). Phase 1 already built (ADR-149). Phases 2-4 are a disclosed roadmap, each gated on real validation evidence, not a build authorization.

---

## The directive (verbatim)

> Founder directive — establish Affiliate Commerce as a permanent business division.
>
> Create an ADR documenting the complete long-term strategic vision exactly as approved.
>
> Affiliate Commerce is NOT a temporary feature.
>
> It is a permanent core business division alongside the Digital Products division.
>
> Develop it independently.
>
> Do NOT block it on Paddle or direct payment processing because affiliate partnerships operate independently.
>
> Follow a "Proof Before Scale" strategy.
>
> Phase 1:
>
> 1. Select ONE real affiliate partner (Amazon Associates or another trusted affiliate program chosen according to business opportunity and regional suitability).
> 2. Build ONE honest comparison/recommendation page using only real product information.
> 3. Implement real outbound click tracking.
> 4. Produce a transparent implementation report showing:
> - What is already live.
> - What depends on affiliate approval.
> - What is intentionally postponed.
> - What must be validated before scaling.
>
> Do NOT build:
> - SEO automation
> - Multi-partner engine
> - Automatic product discovery
> - Autonomous campaign scaling
>
> until one complete end-to-end affiliate workflow has been successfully validated.
>
> Galaxy Forge Constitution applies without exception:
> - No fake reviews.
> - No fabricated ratings.
> - No deceptive marketing.
> - No policy violations.
> - Full compliance with each affiliate network's official terms.
>
> The objective of Phase 1 is validation, not scale.
>
> After successful validation, prepare the roadmap for the Global Commerce Intelligence Division (GCID).

## Relationship to ADR-148 and ADR-149

This directive formalizes and extends, rather than replaces, two prior real decisions in this same thread:

- **ADR-148** (2026-07-30, same day) deferred the full "Global Commerce Intelligence Division" vision entirely — zero code — because the factory had zero real dollars, directly violating `CLAUDE.md`'s Golden Rule ("لا توسع بمنتج جديد قبل أول دولار من المنتج الحالي"). ADR-148 itself named its own re-trigger condition: "(b) the founder explicitly overrides the Golden Rule for this specific initiative."
- **ADR-149** (2026-07-30, same day) recorded exactly that override for one narrow initiative — Affiliate Commerce Phase 1 — and built it: `affiliate_commerce/` package, the real standing-desk-converter comparison page, real click tracking, and an honest status report.
- **This ADR (150)** is the founder's follow-up, received after ADR-149's Phase 1 build was already complete and live-verified. It does three new things ADR-149 did not: (1) formally declares Affiliate Commerce a **permanent division**, not a one-off experiment; (2) documents the **complete long-term phased roadmap**, not just Phase 1; (3) asks for the **GCID roadmap to be prepared** (planning only) as the eventual Phase 4 of this same division, superseding ADR-148's "fully deferred, no roadmap" posture with "deferred, but the roadmap now exists on paper, gated behind real validation evidence."

No conflict was found between this directive and any standing architectural decision — every constraint it names (independent of Paddle, Proof Before Scale, explicit non-build list, Constitution compliance) is already exactly how ADR-149 was built. No `AskUserQuestion` was needed for this round.

## Why Amazon Associates remains the Phase 1 partner

The directive leaves the specific network open ("Amazon Associates or another trusted affiliate program chosen according to business opportunity and regional suitability"). Amazon Associates was already selected and built in ADR-149, before this directive arrived, for reasons that still hold and are recorded here honestly (a disclosed judgment call, not a data-backed comparison — no other network was evaluated with real data):

- Largest real product catalog of any consumer affiliate program, minimizing the risk of picking a category with too few real products to compare honestly.
- Well-established, low-friction signup process relative to the "founder must create the account" constraint both ADR-149 and this directive repeat.
- `customer_site/` is English-language and USD-priced today — Amazon.com aligns with that existing surface without new localization work.
- No real comparative data exists in this factory for any other network (ShareASale, CJ, Awin, regional programs) — selecting one of those instead would have been a guess dressed as a decision. This is disclosed as a gap, not resolved by fabricating a comparison.

This is not a permanent commitment to Amazon-only — Phase 3 below explicitly reopens the network question once Phase 1 is validated.

## The complete long-term roadmap

**Phase 1 — Proof (ADR-149, already built, live-verified 2026-07-30).** One partner (Amazon Associates), one category (standing desk converters, `customer_site/affiliate-standing-desks.html`), real click tracking (`data/affiliate_clicks.jsonl`), zero fabricated data. Objective: validation, not scale — matches this directive's own stated Phase 1 objective verbatim.

**Phase 2 — Scale within the validated partner (not started; gated).** If and only if Phase 1's validation criteria (below) are met: expand from 1 category to a small number of additional real categories under the *same* Amazon Associates account, reusing `affiliate_commerce/products.py`'s exact static-dataset-with-disclosed-source pattern per new category (still no auto-discovery — each new category's product list is still a real, disclosed, manually-verified snapshot, per the directive's own standing "no automatic product discovery" prohibition until full validation). No new infrastructure required beyond adding rows to the existing pattern.

**Phase 3 — Multi-partner expansion (not started; gated).** Reopens the network question ADR-149 deliberately left narrow: evaluate a second real affiliate network (candidates: ShareASale, CJ Affiliate, or a regional program if a real non-US market signal emerges) using real comparative data gathered *during* Phase 1/2 (real click-through rates, real category performance) rather than the disclosed guess this ADR made above. `affiliate_commerce/networks.py` already has a clean per-network seam (`amazon_associate_tag_configured()`/`build_amazon_url()`) a second `networks.py` function can sit beside without restructuring the module.

**Phase 4 — Global Commerce Intelligence Division (GCID), roadmap only, not built.** Per this directive's explicit final instruction ("after successful validation, prepare the roadmap"), the GCID vision from ADR-148 is restated below as a phase of this division rather than a separate initiative — the roadmap section immediately below is the deliverable for this instruction. **No GCID code is authorized by this ADR.** ADR-148's real conflict (zero real dollars, Golden Rule) is unchanged today — `config/reality.json` still shows `published_books: []` and Affiliate Commerce itself has zero real clicks and zero real revenue at the time of this writing (the real ledger was intentionally cleaned of test data after ADR-149's live verification). Advancing to Phase 4 requires the same real evidence Phase 2/3 require, at a higher bar (see validation gates below).

## Validation gates — disclosed criteria, not fabricated milestones

Real, checkable conditions gate every phase transition — never a date-based or vibes-based "we've done enough" call:

| Gate | Required before |
|---|---|
| Real `AMAZON_ASSOCIATE_TAG` configured (founder's own real account, approved by Amazon) | Any real commission can be earned at all — currently unmet |
| At least one real completed conversion, confirmed via Amazon's real postback/reporting (not this factory's own click count) | Phase 2 |
| Real click-through data from Phase 1 showing the comparison-page format itself works (a real, non-zero click rate sustained over a real multi-week window, not a single test click) | Phase 2 |
| A second phase-1-equivalent category successfully proven under Phase 2 (real clicks + real conversions, not just added to the dataset) | Phase 3 |
| A real, live business reason to add a second network (e.g. Phase 2 category has no good Amazon match, or a real non-US customer segment emerges) | Phase 3 |
| The Golden Rule's own condition — a real first dollar from *any* Galaxy Forge product (digital or affiliate), verified against `config/reality.json`, matching ADR-148's own re-trigger condition — **and** Phase 3 substantially proven | Phase 4 (GCID) |

Each gate is independently checkable against real, already-existing data sources this factory already trusts (`data/affiliate_clicks.jsonl`, `config/reality.json`, Amazon's own real reporting once an account exists) — no new fabricated scoring system is introduced to decide phase transitions.

## GCID roadmap sketch (planning artifact only, per this directive's final instruction)

Restated from ADR-148, now scoped as this division's eventual Phase 4 rather than an independent divisional ask:

- Multiple real affiliate/marketplace partnerships, evaluated on real commission rate, real conversion rate, real market demand, and real partner reputation (each field sourced from that partner's own real reporting once integrated — never estimated).
- A generalized comparison-page generator, built by lifting the real, working pattern `customer_site/affiliate-standing-desks.html` + `affiliate_commerce/products.py` already prove, once a second and third real category/partner combination has independently validated the pattern (avoids over-generalizing from a sample of one).
- Conversion/commission monitoring across partners, once each partner's real postback exists — the same honest-dependency this ADR's validation gates already require per-partner.
- A Mission Control "Affiliate Portfolio" view aggregating real per-partner/per-category performance — modeled on `global_opportunity_exchange.py`'s existing real portfolio-concentration pattern (>40% one partner, >30% one category thresholds) rather than inventing a new aggregation approach.
- Explicitly still excluded at Phase 4 entry, pending its own future validation: automatic product discovery, autonomous campaign scaling, and any AI-driven offer-ranking system — each carries its own real risk (stale/incorrect product data presented as live, policy violations from unreviewed auto-generated copy) that a human-reviewed Phase 1-3 workflow does not.

## What this ADR does NOT authorize

No new code. No new affiliate network integration. No new product category. No auto-discovery, SEO automation, multi-partner engine, or autonomous scaling — every one of these stays exactly as blocked as ADR-149 and this directive both state, until their specific real validation gate above is met. This ADR's only deliverable is the roadmap and permanent-division declaration themselves.

## Constitution / compliance

Unchanged from ADR-149: no fake reviews, no fabricated ratings, no deceptive marketing, full compliance with each affiliate network's official terms — restated here as a standing constraint on every future phase, not just Phase 1.
