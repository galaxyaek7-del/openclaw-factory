# ADR-086 — Night Session: Product Quality, Pipeline Depth, Full Paddle Readiness, Fifth Product

**Date:** 2026-07-22
**Status:** Adopted. Four real workstreams, run in parallel while Paddle payout waits on the founder's card delivery. Continues ADR-084 (discovery experiment approval) and ADR-085 (first Paddle→Telegram wiring) from the same night.

---

## What this covers

The founder asked for four things in parallel: (1) discovery-experiment prep — already delivered as the Field Kit artifact, no rework needed; (2) a real quality pass on the $388 techdoc; (3) running `market_hunter.py` fresh and producing 3 more real, QA-passed techdoc packages; (4) wiring the 3 remaining Arabic Telegram categories — recorded separately as ADR-085. Mid-session, the founder approved a fifth product. This ADR is the honest record of (2), (3), and the fifth product + the Paddle-registry extension that followed from it.

## 1. Product quality pass — the $388 techdoc was not "needs polish," it was unwritten

Reading the actual live file (`books/proof_ai_compliance_automation_package.pdf`) found every chapter reading `[Placeholder — ... not yet written. Replace before real publication.]` — a real, paid, Paddle-listed product with no real content, shipped before this session started. This was not visible from any prior ADR because none had opened the file itself.

**Root cause, found live:** `ai_generate_techdoc_content()`'s strict `##SECTION N TITLE/CONTENT##` marker parser assumed the model would echo the literal tag text. `llama-3.1-8b-instant` doesn't — it writes real, substantive content under its own invented headers (`##PRODUCT OVERVIEW##`, `##GETTING STARTED GUIDE##`). The parser found zero matches and silently fell through to `"Content for X."` placeholder-grade text, with no error surfaced anywhere. Fixed with the same resilience-over-strictness pattern `_parse_sectioned_book()` already established: when the strict pass finds nothing, recover the model's real content positionally from any header-line pattern, not the literal requested wording. The identical bug existed in `dossier_bundle._parse_marketing_copy()` (sales-copy headline/description silently empty) and was fixed the same way.

**A second, more serious finding, even after the parsing fix:** the model's real, correctly-parsed content for a fresh test generation described a fictional hosted SaaS platform — "our platform," a sales team, 24/7 dedicated support, a sign-up flow, an XML export format — none of which exist. Confident, fluent, and factually false. This is not a formatting bug; it is a content-honesty risk in every AI SaaS/B2B techdoc this factory could generate. **Decision: do not ship AI-generated narrative content for these products.** All chapter content for the $388 techdoc (regenerated as `books/ai_compliance_automation_for_accounting_firms_v2.pdf`) and every product produced later this session was hand-written, framed honestly as an implementation blueprint using tools the buyer already controls — never as installed or hosted OpenClaw software.

**A third finding, not yet acted on:** the commercial QA gate's `market_realism` check flagged $388 as not credible for an 8-page document and reported it would be silently repriced to $80 at distribution — a page-count-based heuristic built for consumer ebooks, mismatched against a B2B blueprint's real value driver (specificity and buyer budget, not page count). Flagged for the founder; not changed unasked, since it could affect other real products' pricing.

New cover generated with a deliberate `indigo` theme (more premium/tech-appropriate than the original generic blue). 4 new regression tests; 903 Python tests green at this point.

## 2. Pipeline depth — 3 new real, QA-passed products

`market_hunter.py --run`: 23 scanned, 19 skipped, 4 ladder-accepted. Produced real techdoc packages for the top 3 by score:

| Product | Price | Ladder | QA |
|---|---|---|---|
| AI Customer Support Automation Platform for E-Commerce Businesses | $126 | ai_saas | technical pass; commercial flagged duplicate (self-inflicted, see below) |
| Workflow Automation System for Logistics Companies | $327 | b2b_systems | full pass, published |
| Inventory Management System for Wholesale Distributors | $327 | b2b_systems | full pass, published |

**Real structural finding along the way:** `revenue_pipeline.pipeline.process_opportunity(decision, execute=True)` — the "deliberate, explicitly-authorized" production trigger — re-runs a separate, stricter tier-based full evaluation via `orchestrator.run_cycle()`, not the ladder gate that actually accepted these opportunities. The first real attempt (AI customer support automation) came back `DEFERRED` (`opportunity_score 48.7/100, raw 60.9 < 81.2 floor`) with zero file produced, despite the ladder gate having accepted it at 79.6/100 the same night. This is the already-documented `ladder_fast_gate` vs. `ai_ceo_full_evaluation` divergence (`opportunity_pipeline.py`'s own module docstring), now confirmed to also block real execution, not just differ in reporting. Worked around tonight by generating directly through the proven `book_generator.generate_book_from_content()` path rather than reconciling the two gates — a larger, separate decision.

**A real regression this caused, found and fixed:** `tests/test_unified_pipeline_e2e.py` hardcoded `"workflow automation system for logistics companies"` as a permanently-unproduced example niche. Tonight's real, legitimate production made that assumption false the moment the real product shipped. Swapped to another real, still-unproduced `SEED_CATEGORIES` entry (`"automated invoice processing toolkit for small businesses"`) rather than leaving the suite broken by the night's own real work.

## 3. Fifth product, founder-approved mid-session

**"How I Built an Autonomous AI Company Solo — The Complete Blueprint"** ($97), sourced from the real ADR history and build timeline. Hand-written (not AI-generated, per §1's finding), anonymized per the founder's explicit instruction — no real name, email, Telegram chat ID, or API key fragment anywhere in the text; the company itself is referred to generically ("the factory") rather than by its real public name. Honest about real failures found across this entire engagement (the 0-of-42-opportunities investigation and its real root cause, tonight's ladder-vs-tier divergence, the placeholder-content bug, the AI-content-honesty bug) and explicit that revenue is currently zero and checkout is still blocked — no revenue number is promised or implied anywhere in the product. Generated through the standard techdoc pipeline; full Dual Inspection pass (technical + commercial) on the first real attempt.

## 4. Paddle checkout-readiness extended from 1 product to 5

Real Paddle products+prices created for all 4 new items tonight, alongside the existing $388 product — 5 total. `scripts/check_paddle_checkout_status.py` (ADR-085) previously hardcoded one product/price pair; refactored to iterate a real registry (`data/paddle_products.json`), since one Paddle account has one onboarding gate and all 5 need checking together the moment it clears, not just the first one ever registered. Live-verified against the real account: all 5 correctly report still-blocked, zero Telegram spam, `check-paddle-checkout-status` in Mission Control now checks and can notify for all 5 in one action.

## Verification

- Full Python suite: 906 tests green (up from 888 at session start), zero regressions after all four workstreams.
- Every new product live-generated (not mocked) through the real pipeline, with real Dual Inspection results reported honestly above, including the one self-inflicted "duplicate" QA flag (from re-generating the same niche twice during tonight's own debugging — a real testing artifact, not a real product defect).
- `data/paddle_products.json`/`data/paddle_checkout_notifications.json`: real state, checked live against the real Paddle API tonight.

## Impact

- `book_generator.py`, `dossier_bundle/build_bundle.py`: two real parser fixes.
- `books/`: 5 real, QA-passed products now on disk (the original $388 techdoc regenerated with real content, 3 new products from the fresh hunt, 1 founder-approved fifth product).
- `data/paddle_products.json` (new), `scripts/check_paddle_checkout_status.py`, `mission_control_api.py`: checkout-readiness tracking extended to all 5.
- `tests/test_unified_pipeline_e2e.py`: one real regression fixed.
- **Founder-only next step, unchanged:** finish the pending Paddle onboarding step. The moment it clears, `check-paddle-checkout-status` sends all 5 real checkout links to Telegram in Arabic, one message per product, already tested live.
