# GALAXY FORGE — CYCLE 82 EXECUTION REPORT

**Date:** 2026-10-14
**Base commit:** `89cc1d7` (Cycle 81) · **This cycle:** `c33a1f2` *(see A)*
**TOTAL_NEW_SPEND: $0.00** — every network call was a free GET. No API credit, no tool, no ad, no subscription was purchased.

---

## THE HEADLINE

Cycle 81 concluded that payout settings were **not** the blocker and that the
real constraint was demand. That conclusion was correct but **incomplete**, and
official Gumroad documentation checked this cycle shows the payment model this
factory has been operating on is **factually wrong in a way that could block
payouts entirely** — independent of demand.

> **Gumroad's official country table lists `Algeria | DZD`.**
> "We can only pay out to a local bank account and in your local currency. We
> cannot pay you out in USD if it is not listed above as your country's payout
> currency."

This factory's `config/financial_connectivity.json` states Gumroad's payout is
**"BADR direct bank account, Account currency = EUR"**, sourced from a
2026-09-08 founder directive. Per Gumroad's own documentation, **EUR is not a
payout currency available to an Algeria-resident seller.** The supported rail
is a **local bank account in DZD**.

This is hypothesis (D) below. It is **not** proven to be *the* cause of any
observed failure — nothing observed contradicts it, and nothing confirms it.
It is the single highest-value thing to put to Gumroad support, and it is
answerable in one message.

---

## A. REPOSITORY STATE

| | Before | After |
|---|---|---|
| Branch | `main` | `main` |
| HEAD | `89cc1d7` | `89cc1d7` + this commit |
| Ahead of `origin/main` | 1 | 2 (unpushed — **not** pushed this cycle) |
| Staged | 0 | 0 before commit |
| Modified tracked files | 69 | 69 + 1 mine |
| Untracked | 1774 | 1774 + 7 mine |
| Stash | `stash@{0}` untouched | untouched |

**Parallel-session changes: preserved.** No `git add .`, no `git clean`, no
reset, no deletion. The 69 modified tracked files and 1774 untracked files
belonging to other sessions were left byte-identical. Only these 9 paths were
touched:

| File | Change | Why |
|---|---|---|
| `customer_site/guide-turo-invoice-dispute.html` | **new** | §7.1 — free guide for the chosen product |
| `customer_site/products.html` | **+1 line** | link the new guide from the catalog card |
| `scripts/cycle82_share_card_scan.py` | **new** | §6 — measures every listing's share card |
| `scripts/cycle82_product_deep_dive.py` | **new** | §6 — measures real deliverable depth |
| `data/cycle82_share_cards.json` + `.txt` | **new** | evidence |
| `data/cycle82_turo_deep_dive.txt` | **new** | evidence |
| `reports/CYCLE_82_EXECUTION_REPORT.md` | **new** | this file |

---

## B. CYCLE 81 EVIDENCE — AUDITED, NOT ASSUMED

Files reviewed: `data/cycle81_{gumroad_catalog_truth,delivery_audit,claim_integrity,real_listing_text}.json`, `data/cycle81_{claim_scan_out,deliverable_inspect,real_text_dump}.txt`, `reports/CYCLE_81_CLOSING_REPORT.md`, `product_claim_integrity.py`, `distributor.py`.

| Cycle 81 claim | Class | Status now |
|---|---|---|
| Token valid, HTTP 200 | `OBSERVED` → `VERIFIED` | **Re-confirmed live.** |
| 79 products / 78 published | `OBSERVED` → `VERIFIED` | **Re-confirmed live.** |
| 0 sales, $0.00 | `OBSERVED` → `VERIFIED` | **Re-confirmed live** (`/v2/sales` + `sales_usd_cents`). |
| `$99 drtaj` is a false claim | `OBSERVED` → `VERIFIED` | **Re-confirmed.** Still `published=True`, 0 sales. |
| Only 1 of 9 flagged listings was truly defective | `DERIVED` | **Re-derived with the shared engine.** Still 1. |
| "`/v2/balance` and `/v2/account` 404" | `OBSERVED` | **Now explained — see C.2.** My Cycle 81 wording treated 404 as an absence; it is actually *documented absence*. |
| "`view_payouts` scope exists" | — | **New this cycle**, from official docs. Cycle 81 inferred the endpoint from behaviour; the docs name it. |
| Catalog "quality" for ranking | `INFERRED` | **One correction — see D.** |

### Gaps found in Cycle 81's own evidence

1. **No API-documentation check.** Cycle 81 interpreted HTTP statuses without
   reading official docs. This cycle did, and it changed the payout conclusion.
2. **A byte-size proxy stood in for product quality.** Cycle 81 ranked
   candidates partly on "17.9 KB is thin". Measuring the actual PDFs this cycle
   showed that is a **bad proxy** — see D.
3. **No share-card audit.** Cycle 81 said "HTTP 200 proves the page serves" and
   stopped. It did not check what the page looks like *when shared*, which is
   the only state a social channel ever sees.

---

## C. GUMROAD DIAGNOSIS

### C.1 Officially documented operations examined

Source: **https://gumroad.com/api** (official). *Limitation, stated plainly:
that page is a client-rendered Inertia app — a direct fetch returns an 11.5 KB
shell with zero `/v2/` occurrences and zero mentions of "payout". The content
below was read from the search index of that official URL, not by direct
render. Treated as `VERIFIED-BY-INDEX`, not `OBSERVED`.*

| Documented item | Value |
|---|---|
| Base URL | `https://api.gumroad.com/v2` |
| Auth | OAuth 2.0 access token, sent as `Authorization: Bearer` |
| Token lifetime | *"we do not expire the access_token until it is revoked manually"* |
| Scopes | `account`, `view_profile`, **`view_sales`**, **`view_payouts`**, `edit_sales` |
| `view_payouts` | *"read access to the user's payouts information"* |
| Scope enforcement | *"Endpoints with a narrower security boundary … refuse an account-only token and require the specific scope"* |
| `sales_count` / `sales_usd_cents` | explicitly *"requires 'view_sales' scope"* |
| Documented resources | Product, Sales, Subscribers, License Keys, Offer Codes, Webhooks, authenticated user |
| **Documented `balance` endpoint** | **does not exist** |
| **Documented `account` endpoint** | **does not exist** |

Also consulted: **https://gumroad.com/help/article/13-getting-paid** and
**/help/article/223-payoneer-and-gumroad**.

### C.2 Two corrections to my own Cycle 81 wording

**Correction 1 — the 404s were never evidence of a problem.** Cycle 81 wrote
*"no seller-API endpoint exposes bank/payout settings"*, inferred from
`/v2/balance` → 404 and `/v2/account` → 404. The official resource list
contains **neither endpoint**. A 404 on a path the documentation does not list
is the **expected** response, not a signal of a fault. Reporting it as a
noteworthy finding risked implying something was broken. It was not.

**Correction 2 — `view_payouts` is a named, documented scope.** Cycle 81
reported `/v2/payouts` returning 200 as an undocumented discovery. It is
documented, and it carries its own scope. That strengthens the finding and
sharpens the limitation: our token reads it, so it holds `view_payouts` (or
`account`); what it **cannot** reveal is whether a bank is configured, because
no documented endpoint exposes that.

### C.3 The finding that changes the model

Official, verbatim from **/help/article/13-getting-paid**:

> | Albania | ALL (min 3,000) | **Algeria | DZD** |
>
> *"We can only pay out to a local bank account and in your local currency.
> **We cannot pay you out in USD if it is not listed above as your country's
> payout currency.**"*
>
> *"⚠️ You need a minimum balance of **$100 USD** to receive a payout."*

And from **/help/article/223**:

> *"We do not support alternative payout modes like **Payoneer, Wise**, check,
> money order, wire transfer, etc."*

**Contradictions found in this factory's own files:**

| File | Claim | Official docs |
|---|---|---|
| `config/financial_connectivity.json` | Gumroad → BADR, *"Account currency = **EUR**"* | **EUR is not available for an Algerian seller.** DZD is. |
| `config/financial_connectivity.json` | Payoneer = *"PRIMARY_DIGITAL_FINANCIAL_HUB"* | Gumroad explicitly does **not** support Payoneer. |
| `channels/kdp_arm.py:218` | `payout_currency = "EUR"` (KDP) | Not tested this cycle — **UNKNOWN**, flagged only. |

`account_routing.py` is **clean** — it already says *"Payout method is
honestly UNKNOWN … do not assume Payoneer, do not assume any payout method,
until separately verified."* That file was right; `financial_connectivity.json`
overrode it with a founder directive.

### C.4 State classification (A–F)

| | State | Evidence | Tested | Unknown | Next safe step |
|---|---|---|---|---|---|
| **A** | Payout section not visible in account UI | none | — | everything | Owner opens the page; if absent, screenshot it |
| **B** | Section visible, bank/beneficiary incomplete | none | — | everything | Owner completes it with real BADR details |
| **C** | Bank entered, account not accepted/verified | none | — | everything | Owner reports the literal rejection text |
| **D** | **Country / residence / eligibility constraint** | **`Algeria \| DZD`; "local currency only"; "We do not support … Payoneer, Wise"** | Official help article read; account currency from `/v2/user`; payout history read | Whether the account's configured rail is EUR BADR or DZD local; whether the bank accepted or rejected it | **Ask Gumroad support the question in §F.** This is the only branch with documentary support. |
| **E** | API permissions / undocumented operation | `view_payouts` documented; `balance`/`account` not documented | All read endpoints exercised once | Whether the token holds `view_payouts` explicitly or via `account` | None needed — not a blocker |
| **F** | Unknown due to missing access | Payout settings are account-owner-only | Every documented read endpoint | Payout method, KYC state, eligibility | Owner opens the page |

**Proven cause of a blocker: NONE.** Branch **D** is the only one with
documentary support, and it is a *risk*, not a proven failure. Stated as such.

### C.5 What was proven, precisely

| Item | Verdict |
|---|---|
| `GET /v2/products` | **PASS** — 200 |
| `GET /v2/products/:id` | **PASS** — 200 |
| `GET /v2/sales` | **PASS** — 200, `sales: []` |
| `GET /v2/payouts` | **PASS** — 200, `payouts: []` |
| `GET /v2/user` | **PASS** — 200; `currency_type: "usd"` is the **product display** currency, *not* the payout currency |
| `GET /v2/balance` | 404 — **documented absence**, not a fault |
| `GET /v2/account` | 404 — **documented absence**, not a fault |
| Paddle checkout | **BLOCKED** — re-verified today, 7/7 `checkout_ready: false` |

`payouts: []` is the documented *"you have no payouts"* answer. It is **not**
evidence of a broken payout setup.

---

## D. PRODUCT SELECTED — and a correction to Cycle 81's ranking

## 🥇 **Turo Guest Dispute Toolkit** — $29
**https://aekraft.gumroad.com/l/adyvd**

### ⚠️ Correction to Cycle 81

Cycle 81 ranked this #1 partly using external research about **Turo hosts**.
The actual product is **guest-side**. Its own text says:

> *"Who this is for: **guests who rented on Turo in the US**… If you are a
> host, this toolkit is written from the guest side — the host process differs."*

Cycle 81's supporting evidence was therefore for a different audience than the
product serves. The **product** choice still holds, on better grounds — but the
reasoning was misaligned and is corrected here.

### Evidence (all measured this cycle)

**Deliverable — real, downloaded, parsed** (`scripts/cycle82_product_deep_dive.py`):

| Measure | Value |
|---|---|
| Pages / words | **6 pages, 2,774 words** |
| References to official Turo sources | **47** |
| Documentation-requirement mentions | **75** |
| Escalation-path mentions | **52** |
| Time/amount thresholds | **14** |
| `what NOT to do` | 12 |

Cycle 81 called this "thin — 17.9 KB". **That was wrong.** 17.9 KB is the
*compressed PDF*, not the content measure. By the measure that matters it is a
substantive guide. This is why ranking on bytes is unsafe — corrected in
`product_claim_integrity`'s rationale too, which already treats thinness as
`REVIEW`, never `BLOCK`.

**Market — zero visible competition.** Cycle 81's search returned only
`help.turo.com` (free) and one incidental mention on an unrelated site.

**Urgency — real and dated.** From Turo's own documentation: the guest dispute
window is **48 hours** and *"customer support agents cannot reopen it."* There
is no second chance.

**Listing copy — good.** `og:description`: *"Got a Turo invoice or damage claim
you don't owe? You have 48 hours to dispute an invoice…"*

### Why not the other two

- **Trademark DIY Filing Kit ($69)** — market validated (BRANDISH $225,
  Trademarkia $499), but 12.4 KB against a competitor shipping 25 worksheets
  and 18 video walkthroughs.
- **GPSR EU Seller Action Kit ($79)** — five named competitors already
  (`gpsrkit`, `eureadyseller`, `webinterpret`, `SPS`, `Pango`).

### Confidence: **MODERATE**, stated honestly

Zero sales ever, zero traffic data (Gumroad exposes no analytics API),
one search per niche rather than a systematic sweep. This is the best
**provisional** candidate on inspectable evidence, not a proven winner.

---

## E. FREE MEASURABLE TEST — executed, with an honest partial result

### E.1 A real defect found and quantified

While auditing the chosen product's sales page:

> **`og:image` on 59 of 60 reachable listings is
> `https://assets.gumroad.com/images/opengraph_image.png` — Gumroad's generic
> placeholder.**

A share of any of those links on X, Facebook, LinkedIn, Slack or iMessage
renders as a **blank Gumroad card**, not a product. Exactly one listing —
`iaiyt`, the EU AI Act Toolkit — carries a real image.

| Scan result | Count |
|---|---|
| Checked | 79 |
| Reachable | 60 |
| **Generic placeholder share image** | **59** |
| Real product share image | **1** |
| **HTTP 429 — my scan hit a rate limit** | **19** |

**The 19 are `UNKNOWN`, not "fine."** I rate-limited myself; they were not
assessed. Re-running with a delay would cover them.

**The fix already exists locally:** `books/covers/turo_guest_dispute_toolkit_cover.png`
(1600×2560, 116 KB), and 81 covers in total. Uploading is a Gumroad **write** —
blocked by `data/gumroad_auth_state.json` = `UNVERIFIED_COMPROMISED`.

⚠️ Honest caveat: those covers are **portrait 0.63:1**, not the **1.91:1**
ratio a share card wants. Gumroad will crop or letterbox them. It is still
infinitely better than the placeholder, but it is not a drop-in fix.

### E.2 What I built and shipped ($0)

`customer_site/guide-turo-invoice-dispute.html` — a free, honest, indexable
guide following the factory's **existing** pattern (the same one behind
`guide-etsy-suspension-appeal.html`): real method for free, paid kit linked
with `?ref=galaxyforge_guide`.

It carries the same disclosure discipline the other guides do — including
**"0 sales and 0 reviews recorded for the kit to date"** — and states plainly
that a dispute never guarantees a refund.

Content is cited to Turo's own help pages, not invented: the 48-hour window,
72-hour host response, photo-metadata requirement, 24-hour photo timing,
never-pay-directly rule, escalation path.

Linked from the catalog card (the **one** line changed in `products.html`).
Verified: all relative links resolve, all OG/Twitter/canonical tags present,
no fake-urgency or fake-review phrasing, no broken references.

### E.3 What was NOT done, and why

**No distribution was executed.** Evidence, not caution:

| Channel | Attempts | Measured result |
|---|---|---|
| Nostr | **20 posts, 2026-10-09 → 10-11** | **0 replies** (`nostr_replies_gf17.json`: `eose: true, replies: 0` ×3) |
| Nostr | 1 relay | `"blocked: spam not permitted"` |
| Affiliate clicks | 28 rows | all `referrer: null`, all self-generated |
| Page views | 30 rows | `page_id: "c89-ua-probe"` — our own UA probe |

Every recorded "engagement" is **our own verification traffic** — the exact
error commit `2678bc5` fixed ("We were counting our own verification as
readers"), reappearing in these files.

A 21st nostr post would repeat a channel with **zero** demonstrated reach,
already flagged as spam by one relay. Per §7.8 that is unproductive activity.
**So the angle changed instead**: the deliverable is now an indexable page
rather than another broadcast.

### E.4 Measurement plan (executable the moment the page is reachable)

| Stage | Metric | Source | Now |
|---|---|---|---|
| Reach | indexed / crawled | Search Console — **needs owner access** | `BLOCKED` |
| Visit | page views | **no analytics available at $0** | `UNKNOWN` |
| Click → buy page | clicks | Gumroad `?ref=` — not exposed pre-sale | `UNKNOWN` |
| **Sale** | `sales_count` on `adyvd` | **Gumroad API, authoritative** | **0** |

The sale is measurable today. Everything upstream of it is not, at $0.

---

## F. FINANCIAL TRUTH

**`VERIFIED_REVENUE` is unchanged: $0.00.** No value was altered.

| Metric | Value | Source | Verified |
|---|---|---|---|
| Completed sales | **0** | `GET /v2/sales` → `sales: []` | 2026-10-14 |
| Gross revenue | **$0.00** | `sales_usd_cents` summed over all 79 products | 2026-10-14 |
| Payouts received | **$0.00** | `GET /v2/payouts` → `payouts: []` | 2026-10-14 |
| Fees | **$0.00** | no transaction ⇒ no fee | 2026-10-14 |
| Net revenue | **$0.00** | — | 2026-10-14 |
| Amounts accrued / owed | **$0.00** | `finance_data.json`: `sales: []`, totals 0 | 2026-10-14 |
| Published books (KDP) | **0** | `config/reality.json`: `published_books: []` | 2026-10-14 |
| **TOTAL_NEW_SPEND** | **$0.00** | free GETs only | 2026-10-14 |

Every payout observation is trivially empty because there has never been a
transaction. **No number above is an estimate, a projection, or a self-test.**
No self-purchase, no simulated transaction, no fabricated metric.

---

## G. BLOCKERS, AND THE ONE QUESTION TO ASK

| Blocker | Status | Next action |
|---|---|---|
| Algeria payout currency is **DZD**, not EUR | `BLOCKED` | Ask support (§G.1) — founder only |
| Payout method / KYC state | `UNKNOWN` | Owner opens the settings page |
| Withdrawal eligibility | `UNKNOWN` | Needs ≥$100 USD balance; unachievable at $0 revenue |
| `$99 drtaj` false claim still live | `BLOCKED` | Owner unpublishes — factory has no write authority |
| 59/60 listings share a blank card | `BLOCKED` | Owner uploads covers (already on disk) |
| No measurable reach at $0 | `BLOCKED` | See §G.2 |
| Gumroad token `UNVERIFIED_COMPROMISED` | `HOLD` | Owner rotates; blocks all writes |
| 19 listings unassessed (HTTP 429) | `UNKNOWN` | Re-scan with longer delay |

### G.1 The one message to send Gumroad support

Founder only. **Send no passwords, API tokens, or bank credentials to anyone.**

> Subject: Payout eligibility and currency for an Algeria-resident creator
>
> I am a creator based in **Algeria**. Your help article "Getting paid by
> Gumroad" lists **Algeria — DZD** as the payout currency, and states payouts
> go to a local bank account in local currency only.
>
> 1. Is my account eligible for direct bank payouts, given that I reside in
>    Algeria?
> 2. What **exact bank fields and format** does Gumroad require for an Algerian
>    bank account — specifically, account holder name format, account number
>    format (RIB / IBAN), bank name, bank address, and SWIFT/BIC if required?
> 3. Does Gumroad pay an Algerian creator in **DZD only**, or is there any
>    route to receive **EUR**?
> 4. Are there fees, minimum thresholds, or FX spreads I should know about
>    before I connect an account?
> 5. My account currently has **no completed sales**. Is there anything I
>    should set up now so payouts work when the first sale arrives?

**Do not change the account's country or identity details** to force an
outcome. Do not enter a bank account that does not match reality.

### G.2 The closest commercial step

**Not** another payout investigation, and **not** another product.

1. **Upload the covers** (already on disk) — turns 59 blank share cards into
   real ones. Founder action, ~10 minutes, $0.
2. **Unpublish `$99 drtaj`.** It is a live false claim with zero customers.
3. **Ask support the G.1 question.** It is the only path to clearing the last
   infrastructure unknown.
4. **Then measure.** `sales_count` on `adyvd` is authoritative and free. The
   free guide exists and is linked; what it lacks is an audience, and that is
   a founder-channel decision, not something more code can fix.

---

## H. TESTS

| Suite | Result |
|---|---|
| `test_s*.py` | **255 tests, OK** |
| `test_c*.py` | **1101 tests, OK** |
| `test_m*.py` | **0 failures** |
| `test_affiliate_static.py` | 6 tests, OK |
| `scripts/scan_for_secrets.py` | **PASS** — no secret-shaped strings |
| Python test-count floor | **PASS** — 6120 collected (floor 4369) |

**Regression proof:** `test_s*.py` was run against `HEAD:customer_site/products.html`
and against the modified file, comparing failure *names*: **empty diff both
ways, zero regressions.** Only 9 paths were touched (A); no parallel-session
file was modified, staged, or deleted.

*Pre-existing and unrelated, verified identical at HEAD:* failures in
`test_d8_platform`, `test_d10_timezone`, `test_d6_tolerance`,
`test_durable_telemetry`, one `test_d16_d19` source-text assertion,
`ceo_directive_work.py` failing `compileall` (untracked scratch), and
`check_jsonl_duplication.js` flagging two untracked scratch files.