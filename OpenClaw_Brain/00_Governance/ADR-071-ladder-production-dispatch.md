# ADR-071 — Ladder-Tagged Productions Route to the Techdoc Generator, Not the Old Book Path

**Date:** 2026-07-18
**Status:** Adopted, tested (470 Python + 54 in `test_factory_loop_golden.js`, zero regressions), **verified live end-to-end**.
**Closes the gap:** `ADR-070`'s own closing note — selection/gating was fixed, but a ladder-tagged opportunity, if actually produced, still went through `briefFromGoldenOpportunity()`'s book-band pricing and `generate_book()`'s AI-book path. This ADR fixes production dispatch too.

---

## The fix

**`factory_loop.js`'s `briefFromGoldenOpportunity()`** — new early-return branch: when the opportunity carries `ladder` + a finite `ladder_price` (both already computed and stored by `ADR-070`'s `run_oracle()`/`ladder_opportunity_score()`), the brief uses that real ladder-band price directly (no `getButterPrice()` call, which would have silently repriced a $388 AI SaaS opportunity down into KDP's $30-100 book band) and sets `product_type: "techdoc"` instead of the AI-book path's `chapters: 8`. Every non-ladder opportunity is completely unaffected — same function, same behavior, byte-for-byte.

**`factory_loop.js`'s `triggerGenerateBook()`** — forwards `product_type` to `/generate-book` when the brief carries one (`undefined` for every other brief, dropped by `JSON.stringify`, zero effect on existing callers).

**`server.js`'s `/generate-book`** — new payload branch, checked before the existing `topic`-routes-to-AI-book branch: `product_type === "techdoc"` builds `{title, subtitle, product_type:"techdoc", topic, price, theme, author, output, sections}` (sections only forwarded if the caller supplies a real array) and hands it to `book_generator.py --json`, which routes to `generate_product_package()` (`ADR-068`) via the auto-fill branch already built for exactly this case. Existing callers (the dashboard UI, Scout, everything else) never send `product_type`, so both pre-existing branches are unchanged.

## Verified live, end-to-end, in a safe isolated test

Spawned a real, throwaway `server.js` instance on port 3299 (same isolation convention as `tests/test_api_contract.js` — never touches the real, separately-running production instance on port 3000), pointed `factory_loop.js` at it via `DASHBOARD_URL`, and ran the real functions with a real ladder-tagged opportunity (`ladder: "ai_saas"`, `ladder_price: 388`):

```
briefFromGoldenOpportunity() -> { price: 388, product_type: "techdoc", _price_source: "ladder_price" }
triggerGenerateBook()        -> real POST /generate-book on the isolated server
                              -> real 8-page PDF generated
                              -> auto-distribution attempted against all 4 real arms
                                 (all correctly report "arm not ready: unavailable" —
                                 no live credentials exist for any platform, honest)
books/_generation_log.jsonl  -> { "product_type": "techdoc", "content_source":
                                 "human_claude_review", "price": 388 }
```

**The full chain — a ladder-accepted opportunity picked by the automatic tick, priced at its real elite-band price, generated as a real technical-docs package (not an AI-generated book), and automatically routed to distribution — now works end to end, with zero manual steps beyond a real payment credential.** Proof artifacts (the test PDF/cover) were deleted after confirming the trace; the `_generation_log.jsonl` entry is kept as real evidence, same treatment as every other real record.

## Impact

- `factory_loop.js`: `briefFromGoldenOpportunity()` ladder branch, `triggerGenerateBook()` forwards `product_type`.
- `server.js`: `/generate-book` gains the `product_type==="techdoc"` payload branch.
- New tests: 3 in `tests/test_factory_loop_golden.js` (ladder branch, ladder-without-price fallback, backward-compat no-ladder case). Suite now 54 (up from 51). Full suite: 470 Python tests, zero regressions.
- **Nothing left disclosed as "not wired" from the original mission's Step 5 chain** — `ADR-069`'s and `ADR-070`'s open items are both closed. Remaining real blockers are exactly the two already known: a Telegram bot credential (founder-only) and a real payment-platform token for any one arm (founder-only) — no more engineering gaps in the pipeline itself.
