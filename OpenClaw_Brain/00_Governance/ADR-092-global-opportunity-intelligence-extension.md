# ADR-092 — Global Opportunity Intelligence: Extension, Not a New System

**Date:** 2026-07-23
**Status:** Adopted. 3 new real scoring dimensions added, tested, verified against the full regression suite.

---

## The directive

The founder's "PHASE 4 — GLOBAL OPPORTUNITY INTELLIGENCE SYSTEM" mission asked for a new "Global Opportunity Intelligence System" (GOIS) — the factory's "permanent strategic brain" — continuously discovering opportunities across 17 industries (Enterprise Software, Vertical AI, Healthcare, Finance, Government, Insurance, Energy, Construction, Real Estate, Agriculture, and others), scored against 12 named criteria (Customer Pain, Urgency, Market Size, Competition, Pricing Power, Recurring Revenue, Technical Difficulty, Barrier to Entry, Time to Market, Strategic Fit, AI Advantage, Long-term Defensibility), outputting a ranked "Global Opportunity Portfolio."

## What a real search found before building anything

Per the directive's own rule 8 (search, verify, integrate before creating) — carried forward from the prior mission's rule 7 ("never duplicate existing functionality") — a real search found this factory already has almost exactly this system, built across multiple prior sessions under different names:

- `market_intelligence_core/scoring/`: real, live scoring for `customer_pain`, `competition`, `pricing_power`, `demand`, `execution`, `risk`, `trend_stability`, `profit_margin`, `confidence`.
- `profit_oracle.py`'s `strategic_investment_layer()` (2026-07-22): a real, documented "evaluate every opportunity as if OpenClaw were acquiring a company" synthesis — 7 real yes/no/uncertain questions over already-computed evidence, never fabricated.
- `profit_oracle.py`'s `_score_defensibility()` (2026-07-22): a real, cached-competitor-data-driven moat signal.
- `ai_leverage` and `recurring_revenue_potential`: already real, scored dimensions (`_score_ai_leverage()`, `RECURRING_REVENUE_BY_LADDER`).
- 4 real, prior ADRs already document this exact evolutionary arc: `ADR-026` (opportunity score), `ADR-050` (decision engine), `ADR-060` (Golden Opportunity Hunter), `ADR-066` (ladder opportunity score).
- Per memory of prior sessions: this is not a new mission direction either — "Strategic Phase 3 mission reframe, 2026-07-22" already established "primary mission now discovering/creating high-value businesses, not volume" as the operative direction.

**Founder decision, asked directly and confirmed: extend the existing pipeline, do not build a parallel system.**

## The real domain mismatch, raised and resolved

The requested 17 search domains (Healthcare, Finance, Manufacturing, Legal Tech, Government, Insurance, Energy, Construction, Real Estate, Agriculture, Professional Services, and others) are almost entirely outside what this factory's real data connectors can credibly serve — all 11 real connectors (`multi_source_intelligence/connectors/`: `hacker_news`, `github`, `arxiv`, `stack_overflow`, `product_hunt`, `reddit`, `etsy`, `amazon`, `gumroad`, `google_trends`, `public_search`) are developer/tech/consumer-marketplace-adjacent. Beyond data availability, this factory has no real execution capability for those sectors today — a solo founder with an AI content-generation pipeline has no regulatory, industry-expert, or enterprise-sales infrastructure to act on a real Healthcare or Government opportunity even if one were genuinely discovered.

**Founder decision, asked directly and confirmed:** discovery scope stays real — Developer Tools, Vertical AI, and tech-adjacent Professional Services/Education, where real data and real execution capability both exist. The other domains are not silently dropped; they're explicitly out of scope until this factory's real data sources or real execution capability change, which is a decision to revisit deliberately, not a gap to paper over.

## What was actually built: 3 real, genuinely new dimensions

A real gap analysis (not assumed) against the requested 12 criteria found 9 already real and scored, and 3 genuinely missing as their own named dimension:

1. **`_score_time_to_market(ladder)`** (`profit_oracle.py`) — real and deterministic: does a working production pipeline already exist for this ladder's default product family? Reuses `product_families.registry`'s own real registration state directly — the same state `production_factory/dossier.py`'s existing `_product_type_capability()` already relies on, never a second, independently-derived answer to the same question. Never a guessed day/week estimate (no real evidence exists to support one). Wired into `ladder_opportunity_score()`, which has `ladder` in scope.
2. **`_score_urgency(niche, external_signal)`** (`profit_oracle.py`) — real, evidence-only: reads `willingness_to_pay_hits`/`pain_language_hits` when a caller has already computed real customer-pain evidence and passed it in via `external_signal` (the same enrich-before-scoring pattern `orchestrator.py`'s `_enrich_with_real_competition()` already established for competitor data). Never triggers a live query itself — the same cache/pass-in-only discipline `_score_defensibility()` already documents. Honest `Unknown` when no evidence has been computed yet.
3. **`_score_barrier_to_entry(niche)`** (`profit_oracle.py`) — deliberately distinct from `_score_defensibility()` (current competitive intensity): answers "how technically hard would a new entrant find replicating this," derived from the real, already-computed execution-complexity score, inverted. Verified in its own test (`test_is_the_inverse_of_execution_score_not_a_copy_of_defensibility`) to never silently alias `defensibility`'s value.

All 3 follow the exact same discipline as every existing informational dimension (`risk`, `confidence`, `defensibility`, `market_signal`, `ai_leverage`): additive only, never blended into `profit_score`'s own weighted formula or `ladder_score`'s acceptance gate — changing either of those was not asked for and would have been a much larger, riskier change to already-tested, load-bearing ranking behavior than adding 3 new informational fields.

## A real test bug found and fixed while verifying this

`_score_demand()` (pre-existing, unrelated to this change) branches on whether `external_signal` is truthy *at all*, not on which specific keys it contains — so a test comparing "with customer-pain data" against "no external_signal" was confounded by this pre-existing behavior, showing a 1-point `profit_score` difference that had nothing to do with the new `urgency` dimension. Fixed by holding a baseline signal key constant across both comparison calls, isolating the actual variable under test.

## Verification

`tests/test_opportunity_score.py` (`TestUrgency`, `TestBarrierToEntry`, 7 new tests) and `tests/test_ladder_opportunity_score.py` (`TestTimeToMarket`, 4 new tests) — real evidence-based behavior, honest-`Unknown` paths, and an explicit "never changes `profit_score`/`ladder_score`/`accepted`" assertion per dimension, matching every existing informational-dimension test in this file. Full regression suite run after the change, per this mission's own "zero regressions" rule.
