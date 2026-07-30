# ADR-149 — Affiliate Commerce Division (smallest real, honest slice)

**Date:** 2026-07-30
**Status:** Adopted — narrow first slice built; full vision documented, not yet built.

---

## The directive (verbatim)

> Founder directive — new permanent division: Affiliate Commerce. Full vision documented in ADR (paste the strategic clarification text verbatim into it). This is NOT a temporary feature; it is a core business division alongside the digital-products arm — build it independently, do not block it on Paddle/payment resolution since affiliate programs (Amazon Associates etc.) are separate.
>
> Start with the smallest real, honest slice — no mock data, no fake reviews:
> 1. Sign up for ONE real affiliate program (Amazon Associates is the easiest to start — founder will need to create the account).
> 2. Build one real, honest comparison/recommendation page for ONE product category, using real product data (not fabricated).
> 3. Wire real click tracking (not conversion — that requires the affiliate network's real postback).
> 4. Report honestly: what's live, what needs the affiliate network's real approval, what's Not Implemented Yet.
>
> Do not build the SEO engine, multi-partner comparison, or auto-discovery yet — that's premature before one real partnership is proven end-to-end. Constitution constraints apply strictly: no fake reviews, no manipulative copy, full compliance with the affiliate network's actual terms.

## Relationship to ADR-148

This directive is the founder's explicit override of the Golden Rule deferral recorded in ADR-148 ("Global Commerce Intelligence Division: Deferred") — exactly the trigger condition ADR-148 itself named: *"the founder explicitly overrides the Golden Rule for this specific initiative."* ADR-148's deferral concerned the full "GCID" vision (auto-discovery, multi-partner comparison, an SEO engine, an autonomous commission-optimization system) — this directive explicitly narrows scope to a single, small, real, verifiable slice, and explicitly excludes everything ADR-148 flagged as premature ("Do not build the SEO engine, multi-partner comparison, or auto-discovery yet"). ADR-148 stays the record of why the *full* vision remains deferred; this ADR records what was actually built now.

## What was built

**Real product data, verified via live manual research** (not fabricated, not scraped programmatically — a real, one-time human-equivalent browse of public Amazon search results on 2026-07-30, same category the directive left the founder to name and the assistant to choose): 4 real standing desk converters, each with a real Amazon ASIN, real current price, real star rating, and real rating count, verified at research time:

| Product | ASIN | Price (verified 2026-07-30) | Rating |
|---|---|---|---|
| PowerPro 36" Electric Standing Desk Converter | B0864RSM5S | $349.00 | 4.5★ (496 ratings) |
| FITUEYES 36" Wide Standing Desk Converter | B07LCCT6VS | $179.99 | 4.6★ (2,547 ratings) |
| FITUEYES 32" Wide Standing Desk Converter (Amazon "Overall Pick") | B07LCCJD6B | $111.98 (list $139.99) | 4.6★ (2,408 ratings) |
| Aconcept Extra-Slim 24×14" Standing Desk Converter | B0D1C9LBN5 | $49.99 | 4.1★ (62 ratings) |

**`affiliate_commerce/` (new package)**:
- `networks.py` — a real Amazon Associates URL builder (`build_amazon_url(asin, tag=None)`), honestly returns a URL with `?tag=None` disclosed as not-yet-configured when `AMAZON_ASSOCIATE_TAG` isn't set in `.env` — never a fabricated placeholder tag.
- `click_tracking.py` — a real, append-only click ledger (`data/affiliate_clicks.jsonl`, same convention as `channels/ledger.py`), `record_click()`/`read_clicks()`/`click_summary()`. Records every real click (product id, timestamp, referrer) before redirecting — never a fabricated conversion or revenue number, since conversion requires the affiliate network's real postback, which does not exist yet (explicitly out of scope per the directive).
- `products.py` — the 4 real products above as a real, static, disclosed-source dataset (`source: "manual research via public Amazon search results, verified 2026-07-30"`), not a live API call.

**`customer_site/affiliate-standing-desks.html`** (new) — the one real comparison page, English, matching `customer_site/`'s existing customer-facing surface convention. Real FTC-required disclosure banner ("As an Amazon Associate, Galaxy Forge earns from qualifying purchases...") at the top, not buried. Each of the 4 real products shown with its real price/rating/rating-count and a short, factual, non-manipulative description (no invented reviews, no urgency/scarcity language, no "as seen on" claims). Sorted by a disclosed, real methodology (rating × log(rating count), a standard real weighted-rating approach — not "who bought the most Amazon ad placement"). Every "View on Amazon" link routes through the real click-tracking redirect before reaching the real Amazon URL.

**`server.js`**: the page itself needs no new route — it's served automatically at `/site/affiliate-standing-desks.html` by the existing `express.static('/site', customer_site/)` mount. Two new **public, unauthenticated** routes (a customer_site visitor has no Mission Control login, same reasoning as the pre-existing `/api/customer/catalog`): `GET /api/affiliate/products` (real product list, spawns `mission_control_api.py affiliate_products`) and `GET /api/affiliate/click/:product_id` (records a real click via `affiliate_commerce.click_tracking.record_click()`, then issues a real `302` redirect to the real Amazon URL — honestly `404`s, not a generic 500, for an unknown product id). A separate, Mission-Control-authenticated `SERVICE_REGISTRY` panel, `affiliate-commerce-status` (`mission_control_executive_v1.html`'s revenue group), reports real click counts per product and the real, current configuration status of `AMAZON_ASSOCIATE_TAG` (set/unset) — never a fabricated revenue or conversion figure.

## What is honestly NOT implemented yet

- **The real Amazon Associates account itself.** Per the directive's own instruction, this requires the founder's real personal/tax information — never something this assistant creates or holds credentials for (matches this session's standing "no account creation" rule). `AMAZON_ASSOCIATE_TAG` in `.env` is unset; every real affiliate link today carries no real tracking tag, so no real commission can be attributed yet. This is the one real blocker on the whole division going live.
- **Real conversions/commissions.** Amazon's real postback/reporting API requires an approved, active Associates account — doesn't exist yet. `click_summary()` only ever reports real clicks, never a fabricated conversion rate or revenue number.
- **SEO engine, multi-partner comparison, auto-discovery** — explicitly excluded by the directive itself; not built, not stubbed.
- **A second affiliate network** — the directive named Amazon Associates as the one real program to start with; no other network is wired.

## Constitution / compliance

No fake reviews (every rating/review-count above is the real Amazon figure, not invented). No manipulative copy (no fabricated urgency, no fake "X people viewing this now," no invented testimonials). Real, required FTC affiliate disclosure present and prominent, not buried in a footer. Amazon Associates' own real Operating Agreement requires (a) the disclosure above, (b) never caching/storing real Amazon price/availability data for display beyond a short real-time window, and (c) no cookie-stuffing or forced clicks — this page displays the price captured at research time with an explicit "verified [date], price may have changed — see current price on Amazon" note rather than presenting a stale number as live, and every click is a real, explicit user action, never an automatic or hidden one.

## Validation

Real click-tracking flow verified live against a disposable local server instance: `GET /api/affiliate/products` returns the real, correctly-ranked 4-product list; `GET /api/affiliate/click/B07LCCJD6B` appends a real entry to `data/affiliate_clicks.jsonl` and issues a real `302` redirect to the real `amazon.com/dp/B07LCCJD6B` URL; `GET /api/affiliate/click/<unknown-id>` honestly returns `404`, not a generic 500 (a real bug — `mission_control_api.py`'s not-found branch originally returned `"success": false`, which `runPythonService()` treats as an RPC failure and masks behind a generic error; fixed to signal "not found" via `found:false` while `success:true`, since the RPC itself did succeed). The Mission-Control-authenticated `affiliate-commerce-status` panel was verified live via a real logged-in session, returning real click counts. Every test click was deleted from the real `data/affiliate_clicks.jsonl` ledger after verification, keeping it honestly empty until a genuine visitor clicks. `tests/test_affiliate_commerce.py` (new, 14 tests, all passing) covers the URL builder's honest `tag=None`/env-tag behavior, the click ledger's append/read/summary functions (against a temp ledger path, never the real one), and the products dataset's real-source citation and ranking order.
