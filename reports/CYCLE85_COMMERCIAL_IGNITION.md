# Cycle 85 — Commercial Ignition: diagnosis and zero-spend plan

Generated: 2026-10-14 · Spend this cycle: **$0.00** · Live writes: **0**

Evidence classes used throughout: `OBSERVED` (read from the real source this
cycle), `DERIVED` (computed from observed values), `INFERRED` (reasoned, labelled
as such), `UNKNOWN` (not knowable with what is actually available).

---

## 1. Baseline, re-verified

Re-read from the live API, not carried forward from the previous report.
`scripts/cycle85_baseline.py` → `data/cycle85_baseline.json`.

| Measure | Value | Class |
|---|---|---|
| Total listings | 79 | OBSERVED |
| Published | 76 | OBSERVED |
| Unpublished | 3 | OBSERVED |
| `/v2/sales` entries | 0 | OBSERVED |
| Verified revenue | $0.00 | OBSERVED |
| Writes performed | 0 | OBSERVED |
| Cost | $0.00 | OBSERVED |

Reference commit `6acad2d`; this cycle ends at `948a125`.

The three unpublished listings are the same three as before: *Verified B2B Lead
Lists*, *GALAXY FORGE API TEST*, *Automated Contract Review System*.

Two bugs in my own baseline script were caught before they produced a false
number, and are worth recording because both would have silently reported
success:

- It assumed a 20-item page size and reported **10** listings instead of 79.
- Rewritten to loop until an empty page, `/v2/products` never terminated,
  because it ignores `page` past the first request.

It now calls `list_products()`, the single pagination path the rest of the
factory already trusts. One pagination truth, not two.

---

## 2. Commercial diagnosis: what is actually wrong

The directive asks that absent sales **not** be attributed to product quality,
and that three distinct problems be separated: no traffic, weak conversion, or
a broken purchase path. They have genuinely different fixes.

### 2.1 The purchase path is NOT broken — PASS

Checked as a visitor, with no purchase performed
(`scripts/cycle85_buyer_path.py` → `data/cycle85_buyer_path.json`):

| Listing | Page | Price shown | Matches catalog | Checkout |
|---|---|---|---|---|
| `/l/bfhpzl` Etsy Bundle | HTTP 200 | 79.0 | yes | reachable |
| `/l/fgruzn` Etsy Appeal Kit | HTTP 200 | 29.0 | yes | reachable |
| `/l/wteork` FBA Workbook | HTTP 200 | 49.0 | yes | reachable |

Every candidate resolves, shows the right price, and exposes a purchase
control. **Checkout is not the bottleneck.**

Two measurement errors of my own are worth recording, because each produced a
confident false reading of a live page:

- A price regex requiring two decimal places reported "no price shown" on a page
  that plainly has one.
- Loosened, it reported **$49 on a $79 product** — because the description copy
  mentions the *competitor's* $49 suspension fee. Scraping `$<n>` out of body
  text measures marketing prose, not the price.

The canonical field is the Open Graph `product:price:amount` meta tag, which is
what the script now reads.

### 2.2 Traffic cannot be measured at all — UNKNOWN, and this is the real blocker

Probed live this cycle:

| Endpoint | Result |
|---|---|
| `/v2/analytics` | HTTP 404 |
| `/v2/visits` | HTTP 404 |
| `/v2/products/analytics` | HTTP 200, `"product was not found"` |
| `/v2/products/:id/analytics` | HTTP 404 |

**Gumroad exposes no analytics API.** Views, referrers and per-listing
conversion exist only inside a dashboard session.

This is the single most consequential finding of the cycle. The factory has 79
published listings, a live site, working checkout, and UTM-tagged links — and
**cannot tell whether a single person has ever arrived.** Every downstream
question ("is the page persuasive?", "is the price wrong?", "which channel
works?") is unanswerable until that one number is read.

It is not being overlooked. `data/analytics_boundary.json` already recorded
"Gumroad Analytics — requires account session"; this cycle confirms it is still
true and that no programmatic substitute exists.

### 2.3 The public surface exists and is reachable — PASS

- GitHub Pages deployment is **live**: the homepage and product pages return
  HTTP 200 with real content.
- `sitemap.xml` lists 61 URLs.
- Substantial free content already exists: 5 Etsy blog posts
  (`blog-etsy-first-24-hours.html`, `blog-etsy-appeal-mistakes.html`,
  `blog-etsy-temp-vs-permanent.html`, `blog-etsy-write-clear-appeal.html`,
  `blog-etsy-appeal-evidence.html`) plus `guide-etsy-suspension-appeal.html`.
- Content pages already carry UTM-tagged links to the paid listings
  (`utm_source=etsy_seo_cta&utm_medium=site&utm_campaign=etsy_suspension_cluster`).

So the "publish content" half of the plan is largely **already done**. The gap is
not content volume.

### 2.4 Structural linking defects — OBSERVED

`scripts/cycle85_link_graph.py`:

- **14 of 64 pages have zero inbound internal links** (true orphans):
  `blog-etsy-appeal-evidence.html`, `etsy-kit-getting-started.html`,
  `affiliate-program.html`, `saas-portal.html`, `trial.html`, and 8 more.
- **`index.html` links directly to zero products.** A visitor landing on the
  homepage must reach the catalogue through one more click (`products.html`,
  which does carry 81 Gumroad links).

The path exists, so this is friction rather than a wall — but the single
highest-authority page on the site offers no direct route to anything for sale.

### 2.5 The catalogue advertises products this factory has itself placed on HOLD — OBSERVED, needs a decision

`products.html` actively links two products that failed this factory's own
quality gate:

- `/l/iaiyt` — EU AI Act Compliance Toolkit. `HOLD`: 11 critical legal defects,
  including fabricated Annex III categories and a false prohibition on
  high-risk GPAI models.
- `/l/wteork` — "Amazon FBA Workbook", listed at $49. `HOLD`: it is a one-page,
  331-word PDF, not a workbook, with empty tables and unsupported outcome claims.

Driving traffic to a product known to be legally defective is a trust and
liability problem, not merely a conversion one. Removing those links is a
commercial decision and is **not** taken unilaterally here.

### 2.6 Verdict

**The bottleneck is top-of-funnel, and its size is UNKNOWN.**

- Broken purchase path: ruled out (OBSERVED).
- Weak conversion: untestable without arrivals.
- No traffic: the leading hypothesis, consistent with 0 sales across 79
  listings — but labelled INFERRED, not proven, because the measurement does not
  exist.

---

## 3. The description repair (/l/bfhpzl)

`scripts/cycle85_description_patch.py` → `data/cycle85_description_patch.json`.

### 3.1 The unit was derived, not assumed

The page uses decimal KB. This was not guessed — the page's own two `36 KB`
claims settle it: 36,302 B rounds to 36 under 1 KB = 1000 B, but to 35 under
1024 B.

| File | Bytes | Page claims | Correct (decimal) |
|---|---|---|---|
| `etsy_suspension_appeal_kit.pdf` | 138,923 | 122 KB | **139 KB** |
| `etsy_appeal_evidence_tracker.xlsx` | 15,011 | 6 KB | **15 KB** |

### 3.2 A naive replace would have corrupted the page

The description contains `36 KB` **twice**, and `6 KB` is a substring of both —
so `6 KB` matches three times, and two of those belong to a *different file's*
size claim. `html.replace("6 KB", "15 KB")` would have rewritten them to
`315 KB`.

This was caught because the first draft of the script asserted anchor
uniqueness and the assert fired.

The replacement is anchored on the filename and rewrites only the numeric token.
Verified: the diff touches exactly two regions (`'22'→'39'`, `'6'→'15'`), and
restoring those two reproduces the original byte-for-byte. The patch provably
cannot reach anything else.

### 3.3 Out of scope, surfaced not fixed

The zip's own size is claimed as `173 KB`; the real file is 176,766 B = **177
KB**. The approval covers exactly two numbers, so this is left alone and
reported. It needs a separate decision.

### 3.4 Status

**Prepared, not executed. BLOCKED on founder authorization.**

A safe path now exists and is tested: `update_product_description_scoped()`
consumes a single-use, payload-bound authorization and enforces a single field,
so the repair cannot move price, title, attachments or publication state. No
scope has been minted and no live write has been attempted.

---

## 4. Zero-spend distribution plan

Ordered by expected value per unit of effort. Nothing here costs money, and
nothing involves mass messaging, automated comments, fake visits, fabricated
reviews, or unproven claims.

### Tier 0 — unblocks measurement (founder action, ~2 minutes)

1. **Open Gumroad Analytics and export views + referrers per listing.**
   This is the only way to learn whether anyone is arriving, and every other
   decision below depends on it. Until then, `INFERRED` is the best available
   label for "we have traffic problems".

### Tier 1 — safe, autonomous, pure upside

2. **Link the flagship products from `index.html`.** The homepage currently
   links to no product at all. Adding the two Etsy listings costs nothing and
   removes a hop from the highest-authority page.
3. **Un-orphan the Etsy blog cluster.** Link the two orphaned pages
   (`blog-etsy-appeal-evidence.html`, `etsy-kit-getting-started.html`) from the
   guide that already has 8 inbound links, so the cluster becomes internally
   navigable rather than sitemap-only.
4. **Keep every content→product link UTM-tagged.** Already true; preserved so
   that when Analytics is finally opened, referrer data is attributable.

### Tier 2 — trust repair (founder decision, recommended)

5. **Stop promoting `/l/iaiyt` and `/l/wteork` in `products.html`** while both
   are on HOLD. This is a judgement about selling known-defective products and
   is deliberately not taken unilaterally.

### Tier 3 — reach (founder account required, zero spend)

6. **Post in communities that permit it** — r/EtsySellers and similar. Requires
   a human account, and per-channel adaptation: genuinely useful answers to a
   real question, never a dropped link. `data/analytics_boundary.json` already
   flags this as account-gated.
7. **Submit/refresh `sitemap.xml` in Google Search Console.** The sitemap is
   correct and the site is live; this is free but needs an account.

### Explicitly rejected

- Paying for traffic, credits, or subscriptions — `TOTAL_NEW_SPEND=$0`.
- Fabricated reviews, fake scarcity, automated comments, mass DMs.
- Cross-posting identical content to every channel; each channel gets its own
  adaptation or it does not get posted.

---

## 5. Product selection

| Criterion | Etsy Bundle `/l/bfhpzl` | Etsy Appeal Kit `/l/fgruzn` | FBA `/l/wteork` |
|---|---|---|---|
| Problem clarity | Clear (suspension → two steps) | Clear | Weak |
| Deliverable quality | 6 files, CRC pass, 215 formulas | 5 files, CRC pass | **1-page PDF sold as workbook** |
| Claim accuracy | **2 wrong sizes** | Size never stated | Misdescribed product |
| Reachable free audience | Has a 5-post content cluster | Shares that cluster | None |
| Checkout ready | Yes | Yes | Yes |
| Support burden | Low (digital) | Low | Low |

**Selected for acquisition: `/l/bfhpzl`, the Etsy Suspension Triage + Appeal
Bundle, $79.**

Reasons: it is the only candidate that is simultaneously live, high-quality,
backed by an existing content cluster, and honest apart from two numbers that
are already fixed and waiting for authorization. `/l/fgruzn` at $29 is the
retained alternative — lower price, same audience, smaller file.

`/l/wteork` is excluded on product grounds, not commercial ones.

---

## 6. What the factory does next, automatically

- Re-run `cycle85_baseline.py` and `cycle85_buyer_path.py` daily; both are
  read-only and cost nothing.
- Keep the manifest gate and the buyer-path claim check running so a page can
  never again drift from the file it sells.
- Re-verify every commit's CI status through `cycle85_ci_status.py` rather than
  assuming it passed.

---

## 7. Known unresolved issues carried forward

1. **CI on `main` is failing**, including on the reference commit `6acad2d`.
   Precisely: **32 of 33 jobs succeed**; the single failing job is `test`, and
   within it the single failing step is `Python tests (a)`. The same job and
   step fail identically on `6acad2d`, `43acf18` and `6b7f48b` — so this
   predates this cycle's commits.
   Cause not established. Logs require authentication (HTTP 403). A clean
   tracked-files checkout of HEAD passes that group locally (417 tests, OK), so
   the failure is environment-specific rather than caused by these commits.
   An audit for the usual causes came back clean: no missing dependency
   declarations, no OS-sensitive assertions, no untracked data-file
   dependencies in the tracked `test_a*` files. Tracked tests elsewhere do
   reference source APIs that do not exist
   (`list_safe_mode_status(circuit_breaker_state_path=...)`,
   `decision_engine.engine._get_economics`, `economics.platform_for_product_type`),
   but those are in other CI groups.
   **Resolving this needs authenticated access to the CI log.**
2. **21 untracked `test_a*.py` files** in the working tree (written by other
   sessions) fail locally and inflate any local run of the same CI group. They
   are not deleted, per the instruction to preserve other sessions' work.
3. `/l/iaiyt` and `/l/wteork` remain live and promoted while on HOLD.
4. The zip-size claim (173 KB vs 177 KB) awaits a separate decision.