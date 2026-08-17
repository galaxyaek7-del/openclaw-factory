# Distribution OS — Read-Only Architecture Audit

- **Date:** 2026-08-17
- **Scope:** Audit ONLY. No implementation. No new code written. No new packages.
- **Directive:** Map Product → Package → Channel Adapter → Listing → Distribution → Attribution → Learning; classify each capability EXISTS / PARTIAL / MISSING / BLOCKED; identify (1) reusable distribution components, (2) duplicate systems, (3) the missing shared Distribution OS layer, (4) exact external founder blockers, (5) the smallest safe implementation that increases multi-channel production efficiency. Return exact files/modules + prioritized build plan. HARD STOP.
- **Rules honored:** read-only only; no touching payments/financial data/customers/external publishing; real data only; no fabricated listings/sales/customers/revenue; read-only tests re-run where safe.
- **Ground truth used (real, live reads only):**
  - `data/sales_ledger.jsonl` — 44 real `publish_attempt` events, 0 real sales. Outcomes: gumroad dry_run=1 ok=False ×15, dry_run=0 ok=False ×9 (all historical "arm not ready: unavailable", pre-token), gumroad dry_run=1 ok=True ×2; payhip dry_run=1 ok=False ×7; etsy dry_run=1 ok=False ×7; paddle dry_run=1 ok=False ×2 + ok=True ×1, paddle dry_run=0 **ok=True ×1**.
  - `channels/gumroad_arm.py` — the ONE real non-dry-run success is Paddle, not Gumroad: **EU AI Act Compliance Toolkit** (`pro_01kzdzzh4kv6bkpzfhd5r1jnkn`, $155), published `dry_run=False` via `channels/paddle_arm.py::publish()` 2026-08-07. Gumroad's product (`pzTmMb4v8cih3nbWTj5TeA==`, short URL `https://aekraft.gumroad.com/l/iaiyt`, $155) was created 2026-08-14 **out-of-band** (not via distributor) and is a **DRAFT** — `enable_product` blocked until the founder connects a payment method.
  - `.env` — `GUMROAD_ACCESS_TOKEN` set; **`PADDLE_API_KEY` set (69 chars)**; `PADDLE_WEBHOOK_SECRET` absent; `ETSY_ACCESS_TOKEN` absent. (Note: `channels/paddle_arm.py`'s own docstring still says "No PADDLE_API_KEY has ever existed" — **stale**, the key now exists and the arm's `_status_via(paddle_publisher.load_api_key, ...)` would report READY.)
  - `data/paddle_products.json` — 6 real Paddle products, all with real `price_id`s (AI-Powered Compliance $388, AI Customer Support $126, Workflow Automation $327, Inventory Mgmt $327, Autonomous AI Company book $97, EU AI Act Toolkit $155).
  - `config/reality.json` — `published_books: []` (zero real published books on Amazon KDP, ever; only a human can add entries after a real ASIN).
  - `books/_generation_log.jsonl` — 827 real production_ids; 36 `inspection.published: true` (cleared to publish, NOT actually published).
  - `data/seo_pages.json` — 17 real pages; `data/commission_opportunities.jsonl` — 17 real opportunities; `data/affiliate_page_views.jsonl` — 16 lines; `data/affiliate_clicks.jsonl` — 18 real lines; `launch_batches/` — 1 real batch; `data/affiliate_discovery_log.jsonl` — 2 lines.
  - `data/commission_ledger.jsonl` — TEST-environment entry only ($500, environment TEST). No real commissions.
- **Tests re-run (read-only, all green):** 212 Python distribution tests (`tests.test_distributor`, `test_publish_protection`, `test_paddle_arm`, `test_payhip_etsy_arms`, `test_gumroad_publisher`, `test_paddle_webhook`, `test_seo_distribution`, `test_affiliate_commerce`, `test_affiliate_attribution`, `test_affiliate_launch_prep`, `test_affiliate_launch_batch`, `test_affiliate_router`, `test_affiliate_discovery`, `test_affiliate_content_factory`, `test_check_paddle_checkout_status`) — 212/212 OK. 8 JS tests (`test_factory_loop_seo_distribution`, `test_publisher_seo`) — 8/8 pass.

---

## Classification Legend

| Status | Meaning |
|---|---|
| **EXISTS** | Real, live, callable capability with real data/wiring today. |
| **PARTIAL** | Real code exists but has a wiring/data gap disclosed below. |
| **MISSING** | No real module exists anywhere in this factory (verified by search). |
| **BLOCKED** | Code is real but cannot be exercised against real data (external gate / founder-only step / zero real traffic). |

---

## The Seven-Stage Map — Classified

### Stage 1 — Product — EXISTS

| Module | Role |
|---|---|
| `schemas/product.py` | Canonical `Product` translation layer (generation log → channels): `title`, `product_type`, `source_id`, `language` (ar default), `price_usd`. Every channel/publisher consumes this shape. |
| `product_families/manifest.py` + `product_families/families/*.py` | Family manifests with `supported_marketplaces` — the real per-product channel narrowing: `automation_systems`/`digital_toolkits`/`professional_templates` → `["paddle", "gumroad"]`; `kdp_books`/`knowledge_bases` → no manifest (KDP greenfield). |
| `books/_generation_log.jsonl` | 827 real production_ids; `commercial_execution/pipeline.py` reuses a matched catalog artifact for honest fulfillment routing. |
| `data/paddle_products.json` | 6 real Paddle products + prices (the live customer catalog source). |

**Finding:** Product is the strongest stage — real, canonical, already consumed by channels, catalog, and checkout.

### Stage 2 — Package — EXISTS

| Module | Role |
|---|---|
| `product_launch_kit.py` | production_id-keyed launch kit (Build 3, committed `27e7f0b`, this session's Production OS work). |
| `commercial_execution/pipeline.py` | Unified Publish Pipeline: Publishing → Verification → Revenue Registration → Audit Trail → Knowledge Update. |
| `dossier_bundle/build_bundle.py` / `production_factory/dossier.py` | Real per-product dossiers/bundles (pre-existing; cited by pipeline). |
| `affiliate_launch_prep.py` / `affiliate_launch_batch.py` | Per-channel launch content (7 channels incl. short_video/x/facebook/pinterest/linkedin/email/seo; `UTM_SOURCE_BY_CHANNEL`; output to `launch_batches/`). |

### Stage 3 — Channel Adapter — PARTIAL (per-channel, see matrix below)

`channels/registry.py` (arm registry, self-register on import), `channels/base_arm.py` (BaseArm contract + `ArmStatus` READY/UNAVAILABLE/COOLDOWN + `PublishResult`), and one adapter per real platform:

| Arm | Real code | Live state |
|---|---|---|
| `channels/paddle_arm.py` + `channels/paddle_publisher.py` | `create_product`, `create_price`, `create_checkout_transaction`, `get_transactions`, `load_api_key` | **READY (REAL).** `PADDLE_API_KEY` present; 6 real products/prices created; **1 real non-dry-run publish success**. Checkout blocked on Paddle account onboarding (see founder blockers). |
| `channels/gumroad_arm.py` + `channels/gumroad_publisher.py` | `create_product`, `update_product`, `enable_product`, `get_product`, `get_sales`, `list_products`, `load_token` | **PARTIAL.** Token set; 1 real product created 2026-08-14 but DRAFT (payment method not connected). `get_sales()` works. |
| `channels/etsy_arm.py` + `channels/etsy_publisher.py` | `load_credentials`, `create_product` | **BLOCKED.** No `ETSY_ACCESS_TOKEN`; OAuth2 flow not implemented; Etsy restrictive on new dev apps since 2024 (ADR-025). |
| `channels/payhip_arm.py` + `channels/payhip_publisher.py` | `load_token`, `create_product` | **BLOCKED.** Payhip public API has no product-creation endpoint (verified 2026-07-12); live publish always fails safely (`UnsupportedOperationError`). |
| KDP | **none** | **MISSING.** No arm/publisher anywhere (verified by glob). `product_families/families/kdp_books.py` is a family manifest, not a channel. `reality.json` requires a real ASIN entered only by a human. |
| Website/landing (`customer_site/`) | — | **EXISTS as a channel in practice but NOT a registered arm.** Nothing "publishes" a product to the site programmatically — the catalog reads `paddle_products.json` directly. |

### Stage 4 — Listing — PARTIAL

| Module | State |
|---|---|
| `customer_site/eu-ai-act-compliance-toolkit.html` | Real landing page, real Gumroad CTA (`https://aekraft.gumroad.com/l/iaiyt`, $155). EXISTS. |
| `customer_site/index.html` + `/api/customer/catalog` (server.js:6497) | Live catalog from `paddle_products.json`, 6 real products. EXISTS. |
| Instant Checkout (ADR-183) — `/api/customer/checkout/:product_id` (server.js:6523) + `customer_site/index.html` buy button | Real Paddle checkout attempt → real `checkout_unavailable` fallback to the manual request flow. **BLOCKED at the live checkout step** by `transaction_checkout_not_enabled` (re-checked live by `scripts/check_paddle_checkout_status.py`). |
| `global_commercial_operations_engine.py::listing_registry()` | Real per-platform listing registry (metadata/truth tags) — read-side only, not product-keyed orchestration. PARTIAL. |
| `seo_distribution.py` | **The only fully READY distribution channel in the factory.** 17 real pages under `/site/`, registry `data/seo_pages.json`, page-view tracking, daily tick in `factory_loop.js`. EXISTS. |
| Social/video listings | **MISSING** — no publishing infra at all; only generated assets (`validation_assets/FINAL_FACEBOOK_POST.md`, `FINAL_LINKEDIN_POST.md`) and launch-batch content files. Nothing posts. |

### Stage 5 — Distribution — PARTIAL

| Module | Role |
|---|---|
| `distributor.py` | The distribution backbone: fans one Product out to all registered arms, `dry_run=True` default at every layer, records every attempt to `data/sales_ledger.jsonl` via `channels/ledger.py` (`publish_attempt`/`sale` event types). **The single most reusable component in the factory.** |
| `orchestrator/engines/publishing.py` | Engine adapter → `commercial_execution.pipeline.run_publish_pipeline()` → `distributor.distribute()`; `FACTORY_LIVE_PUBLISH` gate; product-family narrowing. |
| `channels/ledger.py` | Unified sales ledger writer + reader (`publish_attempt`/`sale`). |
| `channels/publish_protection.py` | Pre-publish gate: per-arm daily/hourly caps, cooldowns, min spacing, `risk_score`, emergency stop. |
| `server.js` `/api/distribute` (L4503) + `/api/sales/poll` (L4573) | Mission-Control/internal-token gated entry points; `factory_loop.js` calls both every tick. |
| `scripts/poll_sales.py` (ADR-016) | Polls each arm's `get_sales()` → `record_sale` (dedup key platform+raw id). Real, read-only toward Gumroad beyond `GET /sales`. |

**Real distribution outcome to date:** exactly **1 real non-dry-run publish** (Paddle EU AI Act Toolkit). Everything else was dry-run or failed-safe. This is the honest "distribution is mostly wired, barely exercised" state.

### Stage 6 — Attribution — EXISTS (clicks) / PARTIAL (conversion)

| Module | State |
|---|---|
| `affiliate_commerce/click_tracking.py` | Real append-only click ledger `data/affiliate_clicks.jsonl` (18 real lines) + `data/affiliate_page_views.jsonl` (16 lines), `parse_utm_query`, `record_attributed_click`. EXISTS. |
| `affiliate_launch_prep.py` | `LAUNCH_TRACKING` + `affiliate_link_status: NOT_CONFIGURED` until the founder activates a real CJ account + Payoneer. PARTIAL (honestly disclosed). |
| `affiliate_launch_batch.py` | Real `UTM_SOURCE_BY_CHANNEL` per channel. EXISTS (content generation only — nothing delivers it). |
| `affiliate_router.py` / `affiliate_discovery.py` / `affiliate_content_factory.py` | Route niches → real program portfolio (keyword intersection, never fabricated); discovery + content generation. EXISTS. |
| `lib/publisher_seo.js` | Groq SEO metadata generation, `publisher_seo_log.jsonl`. EXISTS. |
| `revenue_intelligence.py` | **The real learning-over-attribution layer:** KEEP/SCALE/RETEST/PAUSE/REMOVE + INSUFFICIENT_DATA over real click/ledger data, never fabricated. EXISTS. |
| Real conversion tracking | **MISSING/BLOCKED** — needs the affiliate network's real postback API (no real account exists yet). |

### Stage 7 — Learning — PARTIAL

| Module | State |
|---|---|
| `revenue_intelligence.py` | Real data-driven decisions over real clicks/publishes. EXISTS. |
| `commercial_execution/pipeline.py` Knowledge Update | Cites the pre-existing `_full_cycle()`/`decision_engine.learning` mechanism — reused, not duplicated. PARTIAL (no real sales/outcomes to learn from yet). |
| `scripts/poll_sales.py` | Polls real sales. EXISTS (0 real sales so far). |
| `channels/paddle_webhook.py` (ADR-223) | Real inbound webhook verifier (signature → validate → idempotency → append-only `data/paddle_webhook_events.jsonl`). **BLOCKED — `PADDLE_WEBHOOK_SECRET` never configured**, so no real inbound event has ever been verified. |
| `global_partnership_network.py::distribution_network_health()` / `global_commercial_operations_engine.py` | Real 10-component distribution health + commercial ops aggregator (order/refund/payout normalization, anomaly, concentration). EXISTS. |

---

## Cross-Cutting Findings

### 1) Reusable distribution components (build the OS ON these, never beside them)
1. `channels/registry.py` — the arm registry (add channel arms by importing them; `all_arms()`).
2. `distributor.py` — fan-out backbone with `dry_run` default and ledger recording built in.
3. `channels/ledger.py` — unified `publish_attempt`/`sale` ledger (append-only, atomic).
4. `channels/publish_protection.py` — per-arm caps/cooldown/emergency-stop (already wired in front of every real publish).
5. `commercial_execution/pipeline.py` — the unified publish pipeline (publish → verify → revenue → audit trail).
6. `schemas/product.py` + `product_families/manifest.py` — canonical product + channel compatibility.
7. `seo_distribution.py` — the only READY distribution channel, already live and tracked.
8. `affiliate_commerce/click_tracking.py` + `revenue_intelligence.py` — real attribution + real-data learning.
9. `scripts/poll_sales.py` + `channels/paddle_webhook.py` — the two real sale-ingestion paths (poll + webhook).

### 2) Duplicate systems (already partially overlapping — do not add a 4th)
- **Three distribution/publish orchestration layers already chain**: `orchestrator/engines/publishing.py` → `commercial_execution/pipeline.py` → `distributor.distribute()`. This is layered, not duplicated — but it means a new Distribution OS must sit ABOVE `distributor.py`, never re-implement it.
- **Three "distribution status" aggregators already exist** and only partially overlap: `commercial_operations.distribution_capability_matrix()` (Phase 9, per-channel CONTENT/PUBLISHING/ANALYTICS automation truth), `global_partnership_network.distribution_network_health()` (Section 38, 10 named components), `global_commercial_operations_engine.build_commercial_operations_dashboard()` (ADR-216, the full 15-section aggregator). Any new read-model must MERGE these, not add a competing one.

### 3) The missing shared Distribution OS layer
There is **no product-keyed, cross-channel read-model** that answers, for any given production_id: what listing state does it have on each channel (Gumroad DRAFT / Paddle live-but-checkout-blocked / SEO page / KDP none), what attribution/click signal each channel produced, and what the real next blocking action is per channel. Each fragment exists (`paddle_products.json`, `sales_ledger.jsonl`, `seo_pages.json`, `affiliate_clicks.jsonl`, `paddle_webhook_events.jsonl`, `launch_batches/`) but nothing joins them per product. That join is the smallest thing that makes multi-channel production *efficient* (a founder currently must hand-cross-reference 5+ ledgers to answer "where does product X stand on every channel?").

### 4) Exact external founder blockers (code is real; these are not code gaps)
1. **Paddle account onboarding** — `transaction_checkout_not_enabled` still active (live-checked this session). Blocks every real checkout; clears via `vendors.paddle.com` (zero further engineering; `scripts/check_paddle_checkout_status.py` + `factory_loop.js` `maybeNotifyPaddleCheckoutReady()` already auto-notify).
2. **Gumroad payment method** — founder must connect one to the account so the real DRAFT product `pzTmMb4v8cih3nbWTj5TeA==` can be `enable_product`-d.
3. **`PADDLE_WEBHOOK_SECRET`** — never configured; the real webhook verifier (`channels/paddle_webhook.py`, ADR-223) stays unexercised until the founder sets it in Paddle dashboard + `.env`.
4. **Etsy OAuth2 app** — founder must create/approve an Etsy dev app and complete OAuth2 (Etsy's post-2024 new-dev-app restrictions); no `ETSY_ACCESS_TOKEN`.
5. **Payhip** — no product-creation API exists; permanent BLOCKED for auto-publish (manual listing only).
6. **Affiliate launch links** — real CJ account + Payoneer required to flip `affiliate_link_status` from NOT_CONFIGURED and produce real Amazon/CJ links.
7. **KDP** — no account integration exists at all; `config/reality.json` requires a human-entered real ASIN after a manual KDP publish.

### 5) The smallest safe implementation that increases multi-channel production efficiency
A **read-only Distribution OS read-model** (one new module, e.g. `distribution_os.py`, mirroring `production_os.py`'s this-session pattern):
- Inputs: existing real ledgers only — `channels/registry.all_arms()`, `sales_ledger.jsonl`, `paddle_products.json`, `seo_pages.json`, `affiliate_clicks.jsonl`, `affiliate_page_views.jsonl`, `paddle_webhook_events.jsonl`, `books/_generation_log.jsonl`, `launch_batches/`, `commission_opportunities.jsonl`.
- Output: **per-production_id Distribution State** — for each channel: listing state (NOT_LISTED / DRAFT / LIVE / CHECKOUT_BLOCKED / SEO_LIVE / MISSING), real publish/sale counts from the ledger, real attribution (clicks/views) per UTM source, and the single real next-blocking-action per channel (citing the founder blockers above).
- Merge (never duplicate) the three existing aggregators above as the per-channel status source where they already cover the question.
- Zero writes, zero new network calls, zero new packages, zero code changes to any channel/publisher/distributor. Mission Control panel (read-only `SERVICE_REGISTRY` entry) following the existing panel pattern.
- This immediately converts "check 5+ ledgers by hand" into "one answer per product per channel," which is the definition of multi-channel production efficiency with zero risk to payments/finance/customers.

---

## Prioritized Build Plan (for later approval — NOT built now)

| # | Item | Type | Rationale / Gate |
|---|---|---|---|
| P0 | `distribution_os.py` per-product read-model + Mission Control panel | read-only | The smallest safe implementation above; zero risk; unblocks founder visibility across all channels immediately. |
| P0 | Founder-only: enable the Gumroad product (connect payment method) | founder action | Turns the real DRAFT into the first live second channel. Not code. |
| P0 | Founder-only: complete Paddle onboarding + set `PADDLE_WEBHOOK_SECRET` | founder action | Unblocks real checkout + makes the real webhook verifier live. Not code. |
| P1 | Register `customer_site` as a real arm (publish product → auto-generate/refresh landing page + catalog entry) | safe additive (dry-run default already built into distributor) | Closes the "website is a channel but not an arm" gap; reuses `seo_distribution.py` + landing template. |
| P1 | Wire `launch_batches/` content delivery readiness into the OS read-model (never auto-posts) | read-only | Attribution chain completeness; delivery stays founder-gated. |
| P2 | Etsy OAuth2 flow (needs founder app approval first) | blocked until #4 | Code is design-ready; blocked on founder. |
| P2 | KDP arm (design only — reality.json human-ASIN gate is permanent by design) | MISSING | Documented as greenfield; not buildable until founder has a KDP account + real ASIN flow. |
| P3 | Real conversion tracking via affiliate postback API | blocked | Needs a real approved affiliate account (CJ) + network postback. |
| P3 | Sales ingestion unification (poll + webhook + ledger) as one named read-path | consolidation | Deferred; three paths already coexist safely, low value to force-merge today. |

**Hard rule carried forward:** never loosen `config/reality.json`'s unfakeable `published_books` gate; never touch `finance_data.json`/ledgers/payments/customers; every new capability uses `dry_run=True`-first and only ever reduces confidence, never terminates evaluation (Real Evidence Provider convention).

---

## HARD STOP — audit complete. No implementation performed.