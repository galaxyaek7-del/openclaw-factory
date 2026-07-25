# ADR-129 — Galaxy Forge Customer Platform, Phase 1

**Date:** 2026-07-25
**Status:** Adopted (Phase 1 only — Phase 2 explicitly deferred, see below).

---

## The directive

Founder decision: Galaxy Forge is no longer just an internal AI factory — build the first production-ready customer platform, looking and behaving like a premium AI software company. Twelve named modules requested: Landing Page, Company Presentation, Services Catalog, Request a Custom Product, AI Consultation, Customer Dashboard, Order Tracking, Secure Payment, Product Delivery Center, Support Center, Knowledge Base, Customer Notifications — plus a full internal automation pipeline (Request → Qualification → Opportunity Evaluation → Price Generation → Proposal → Approval → Payment → Production → QA → Packaging → Delivery → Follow-up) supervised end-to-end by Mission Control. Hard constraints carried over unchanged from this session's standing policy: no fake data anywhere, no placeholders, every number shown must come from real factory data.

## The real constraint that shaped this ADR

Two audited facts made building all twelve modules today impossible without violating the directive's own "no fake data / no placeholders" rule:

1. **Zero completed real sales exist on any channel.** There is no real order, no real payment, no real fulfilled delivery anywhere in this factory's data. A Customer Dashboard, Order Tracking view, or Delivery Center built today would have nothing real to show — exactly the kind of fabricated-looking-real UI the Quality Supremacy Directive explicitly forbids ("never fabricate evidence, research, customer data or market validation").
2. **Paddle's own account-onboarding gate blocks checkout**, confirmed live via `scripts/check_paddle_checkout_status.py` against all 5 real products: every one returns `checkout_ready: false`, reason `transaction_checkout_not_enabled`. This is an account-level gate only the founder can clear at vendors.paddle.com — not a code defect, and not something engineering can route around.

Building Secure Payment, Customer Dashboard, Order Tracking, Delivery Center, or a real end-to-end pipeline execution on top of either a blocked payment gate or zero real orders would mean fabricating the exact "fake success" this session's standing policy prohibits.

## What was built (Phase 1 — 100% real data, no placeholders)

A new customer-facing site, `customer_site/index.html`, mounted at `/site/` in `server.js`:

```js
app.use('/site', express.static(path.join(__dirname, 'customer_site')));
```

placed immediately after the existing `/trust` static mount, deliberately mirroring its scoping rationale — a dedicated subdirectory mount, never a bare repo-root `express.static()`, given this factory's own documented CRITICAL-finding history of exactly that mistake once exposing `finance_data.json` and product PDFs.

**Landing Page + Company Presentation + Services Catalog + Knowledge Base + Request a Custom Product** are built as sections of one single page rather than five separate files — a deliberate scope decision, not yet separately confirmed with the founder, made to avoid duplicating shared chrome (header/footer/design system) across five near-empty files before there is enough distinct content per section to justify the split. Flagged here explicitly per this session's "disclose design choices" discipline.

**Real backend, two new routes in `server.js`:**
- `GET /api/customer/catalog` — reads `data/paddle_products.json` (the same real Paddle product data already used elsewhere in this factory) and returns it as-is. No synthetic products, no placeholder pricing.
- `POST /api/customer/request-product` — validated (required name/email/description, email-format check, per-field max length), honeypot-protected (a hidden `website` field — filled means bot, request silently accepted but never persisted), rate-limited (5 requests / 10 minutes / IP, in-memory), persists to `data/customer_requests.jsonl`, and fires a real Telegram notification via the existing `telegramDirect.sendTelegramMessage()` (best-effort, non-blocking — a Telegram failure never fails the request).

**Real content on the page:**
- Hero states three real, verifiable facts about this factory's own doctrine (10 named acceptance conditions — ADR-126; 4 evidence states — ADR-127; 100% decision logging — the existing `decisions.jsonl` ledger), not invented marketing metrics.
- The Services Catalog section fetches `/api/customer/catalog` live client-side and renders whatever real products exist — verified live in-browser to render exactly 5 real cards with real titles, real prices ($388, $126, $327, $327, $97), and real `product_id` values pulled straight from Paddle.
- Knowledge Base links point to the real, already-existing `/trust/*.html` policy pages (privacy, terms, refund, security, responsible-AI, incident-disclosure) — not new fabricated policy text.

## Real bugs found and fixed during the build

1. **Wrong Knowledge Base link filenames.** Initial links guessed short names (`/trust/privacy.html`); the real files (confirmed via `ls trust/`) are suffixed (`privacy-policy.html`, `terms-of-service.html`, etc.). Fixed via exact-string replacement across all 6 links, verified by grep.
2. **Dead mobile navigation CSS.** The page originally referenced `#menuToggle{display:inline-flex}` at the ≤760px breakpoint — a hamburger button/JS handler that was never built. Left as-is, mobile users would have had zero way to reach the nav links (Approach/Services/Knowledge Base/Trust Center) below that width. Found by direct code review, fixed by removing the dead reference and redesigning the breakpoints: at ≤760px the nav only tightens spacing; only at ≤600px do the nav links fully hide, and even then the brand and primary "Request a Product" CTA remain visible — every hidden nav link is a same-page anchor still reachable by scrolling. Verified live: forcing the ≤600px rule in-browser confirms `nav-links` hides while brand and CTA both stay visible (`brandVisible: true, ctaVisible: true`).
3. **Apparent UTF-8 corruption, investigated and ruled a false alarm.** A curl test with an inline en-dash character persisted as a replacement character. Isolated by re-testing the identical payload via a real UTF-8 file + `curl --data-binary @file` instead of an inline shell argument — the en-dash round-tripped correctly. Root cause: Windows/git-bash's own encoding of inline command-line arguments, not a bug in Express's JSON body parsing or `fs.appendFileSync`. A real browser's native `fetch()`/`JSON.stringify()` never hits this path, so real users are unaffected. No code changed for this one; documented so a future session doesn't waste time rediscovering it.

## Validation (real, live — not code-review-only)

- `node -c server.js` — clean.
- Live curl round-trip: valid submission persists correctly; missing-fields submission correctly rejected (400); honeypot-filled submission silently accepted with no persistence and no tell to the bot.
- Live browser verification (Chrome, real render, not just curl): hero/approach/catalog/request-form/knowledge-base sections all render correctly; `read_console_messages` — zero console errors; live DOM check confirmed `#catalogGrid` populated with exactly 5 real product cards matching the live `/api/customer/catalog` response; a real end-to-end form submission via actual DOM interaction (not curl) persisted correctly to `data/customer_requests.jsonl`, and the form correctly cleared all three fields after a successful submit; clicking a catalog card's "Request access" button correctly pre-filled the request form's description field with that product's real title; the honeypot field's computed style confirmed visually hidden (`left: -9999px`) rather than merely `display:none` (avoids some bot heuristics that skip `display:none` fields); the ≤600px responsive nav rule verified by direct CSS-rule inspection and forced-application, confirming brand + CTA remain visible when nav links hide.
- All test data (`data/customer_requests.jsonl`) deleted after every verification pass — nothing fabricated is left staged or committed.

## What's deliberately NOT built this round (Phase 2 — explicitly deferred)

Per the directive's own "Do not build placeholders" rule, these six of the twelve requested modules are not started, because building them today would require either a working payment gate that doesn't exist yet, or real order/delivery data that doesn't exist yet:

- **Secure Payment** — blocked on the real Paddle `transaction_checkout_not_enabled` account gate (evidence above). Founder action required at vendors.paddle.com; no code fix exists.
- **Customer Dashboard**, **Order Tracking**, **Product Delivery Center** — all require at least one real completed order to show anything real. Zero exist today.
- **Support Center**, **Customer Notifications** (post-purchase) — same dependency: nothing real to support or notify about yet.
- **AI Consultation** — not blocked by Paddle, but requires new engineering: a real translation layer from an unstructured customer request into this factory's internal scoreable-niche format (feeding `evidence_completeness`/`ladder_opportunity_score`), which does not exist anywhere in this factory yet. Deliberately scoped out of Phase 1 rather than half-built.
- **The full 11-stage internal automation pipeline** (Qualification → Opportunity Evaluation → Price Generation → Proposal → Approval → Payment Verification → Production → QA → Packaging → Delivery → Follow-up) — Phase 1 only builds the very first stage (Request intake, persisted and Telegram-notified). The remaining ten stages have no real trigger to chain from yet (no real qualification logic, no real proposal-generation, no real payment-verification callback), and building them against nothing real would be exactly the "no placeholders" violation the directive forbids.

**Reassessed when:** (a) the founder clears the Paddle onboarding gate, unblocking real checkout end-to-end, or (b) dedicated engineering builds the request-to-niche translation layer for AI Consultation — whichever comes first, matching this factory's existing "revisit on real trigger" pattern (e.g. the China program deferral in `CLAUDE.md`).
