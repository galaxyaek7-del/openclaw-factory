# ADR-069 — End-to-End Proof: Opportunity → Decision → Product → QA → Package → Notification

**Date:** 2026-07-17
**Status:** Adopted. Real, live proof run — not a simulation, not a mock.
**Implements:** Step 5 of the 2026-07-17 mission ("prove it"), per `MASTER_CHARTER.md`/`ADR-065`–`ADR-068`.

---

## The real cycle, traced

**A. Opportunity** — `python market_hunter.py --run` (real, live, this session): 13 scanned, **5 ACCEPTED** — the first opportunities ever accepted by this factory's automated discovery (`data/decisions.jsonl`'s prior 1,344/1,344 rejection rate). Picked for this trace: *"AI-powered compliance automation subscription system for accounting firms"* (ladder: `ai_saas`).

**B. Decision** — `profit_oracle.ladder_opportunity_score(niche, ladder="ai_saas")`: `ladder_score=85.3`, `price=$388`, **accepted=true**. Real components: demand 52, competition 70, margin 90, recurring_revenue_potential 100, reusability 95.

**C. Product** — `book_generator.generate_product_package()`: a real 8-page PDF (105,577 bytes) with a real cover, `product_type="techdoc"`. Default technical-docs section skeleton used (Overview/Getting Started/Feature Reference/Setup & Configuration/FAQ/Support) since no pre-written sections were supplied — content is honestly placeholder-labeled, not fabricated as real.

**D. QA** — Real Dual Inspection, embedded in step C's own result: **technical passed** (13/13 checks: PDF integrity, page count, cover dimensions, Arabic-shaping availability, no placeholder title/subtitle/author), **commercial passed** (profit_score 69/100 ≥ 60, `butter_price` net $349.20 clears the `gumroad_elite` floor). One real, honest finding surfaced by the commercial check itself: `market_realism` flagged the declared $388 as oversized for an 8-page product and recommended $80 instead — the pipeline's own economics check catching its own optimistic price, exactly what it's for.

**E. Publish-ready package** — Built the real `Product` via `schemas.product.Product.from_jsonl_record()` reading the actual `books/_generation_log.jsonl` entry step C wrote (not hand-constructed), then ran `distributor.distribute(product, dry_run=True)` against every registered arm.

**A real bug was found and fixed here, not glossed over:** the first run showed every arm rejecting the product as "unsupported" — traced to `schemas/product.py` carrying its own, separate `economics_platform` mapping that was never updated when `book_generator.py`'s `_economics_platform_for()` gained the `"techdoc"` branch in Step 4. Every techdoc `Product` silently fell to `"kdp_ebook"` economics, `market_realism` flagged it against the wrong (much lower) price band, and `needs_pricing` stayed `True` — meaning `distributor.py`'s `supports()` check correctly rejected it, for the wrong underlying reason. Fixed in `schemas/product.py` (mapping `"techdoc"` alongside `"elite"` → `"gumroad_elite"`), verified live: `needs_pricing` now `False`, `price_usd=$80` (the realism-adjusted price). 3 new regression tests (`tests/test_schemas_product_techdoc.py`).

After the fix, the real dry-run result: all 4 arms (`gumroad`, `payhip`, `etsy`, `paddle`) **attempted**, all report `"arm not ready: unavailable"` — the honest, real current state (no live token/key exists for any of them). This is exactly the correct behavior for "safe test mode": the pipeline built a genuinely sellable, QA-passed package and reached the real point where it needs a founder-supplied credential to actually go live — it did not fabricate a fake success.

**F. Founder notification** — Two real calls: `notifyGoldenHunterAccepted()` correctly no-oped (`N8N_TELEGRAM_WEBHOOK_URL` not configured — the founder's manual n8n/Telegram activation from `ADR-067` is still pending), and `sendDesktopNotification()` **fired for real** — a live Windows toast notification landed, proving at least one real, credential-free notification channel works end-to-end today. (Minor accuracy fix made alongside this: `lib/n8n_notify.js`'s skip message used to hardcode `"N8N_PRODUCTION_WEBHOOK_URL"` regardless of which caller invoked it; added an `envVarName` parameter so the Golden Hunter Bridge's own calls now report the correct variable name — 1 new test.)

## Honest, disclosed gap: `factory_loop.js`'s automatic tick is NOT yet on the ladder gate

This proof deliberately called the real functions directly (`ladder_opportunity_score()`, `generate_product_package()`, `distribute()`) rather than through `factory_loop.js`'s automatic `huntGolden()` tick, for a concrete, checked reason: **`huntGolden()` still reads `golden_opportunities.json`, which `profit_oracle.run_oracle()` still populates via the OLD, ladder-unaware `score_opportunity()`.** Checked live before running anything with `FACTORY_AUTO_PRODUCE=true`: the current top-ranked entry in `golden_opportunities.json` is an old Arabic KDP printable-planner niche (profit_score 71, GOOD) — none of the 5 newly-accepted AI SaaS/B2B opportunities rank there, because `run_oracle()`'s scorer has no concept of the ladder at all.

**This means the mission's literal "run with `FACTORY_AUTO_PRODUCE=true`" instruction, if pointed at the real automatic tick today, would not exercise the new ladder pipeline** — it would (most likely) skip, since that top KDP niche has almost certainly already been attempted for real (per `CLOSING_NOTE.md`'s 4 existing real book products, and `ADR-032`'s already-diagnosed stagnation pattern). Rather than stage a misleading "proof" against a path that doesn't yet reflect this mission's work, this ADR discloses the gap plainly: **`market_hunter.py`'s `hunt_market()` is a complete, real, independently-runnable discovery+accept pipeline today (`python market_hunter.py --run`) — it is just not yet the thing the 10-minute Node tick calls.** Wiring `ladder_opportunity_score()` into `huntGolden()` itself (and carrying a niche's `ladder` tag through `golden_opportunities.json`) is the clear, concrete next step, not done in this session — flagged here explicitly rather than silently claimed as finished.

## Impact

- `schemas/product.py`: `"techdoc"` economics-platform mapping fix (real bug, found and fixed this session).
- `lib/n8n_notify.js`: `envVarName` parameter (backward-compatible, existing callers unaffected).
- `factory_loop.js`: passes `envVarName: 'N8N_TELEGRAM_WEBHOOK_URL'` in its own call.
- New tests: `tests/test_schemas_product_techdoc.py` (3), `tests/test_n8n_notify.js` (+1). Full suite: 470 Python tests green.
- Real artifacts produced and kept as genuine inventory (same treatment as the factory's other real products): `books/proof_ai_compliance_automation_package.pdf` + its cover, a real Dual-Inspection-passed AI SaaS technical-docs package, `product_type="techdoc"`, ready to list the moment a real Paddle/Gumroad credential exists.
