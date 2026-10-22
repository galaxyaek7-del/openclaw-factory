# Affiliate intelligence mandate — checkpoint 1 (2026-10-22)

Overall status: **PARTIAL**. Verified affiliate revenue: **$0** (no click,
conversion, commission or payout evidence exists).

## Stage 1 — what already exists (OBSERVED)

| Layer | Source of truth | Note |
|---|---|---|
| Program registry | `data/commission_opportunities.jsonl` (17 rows), written only by `affiliate_discovery.merge_newly_verified_programs` | Read model: `affiliate/registry.py` |
| Partnership pipeline | `data/partnership_pipeline.jsonl` (5 rows) | 3 leads (baremetrics, hostaway, lemsubs) not in the registry |
| Links | `data/affiliate_links.jsonl` (1 row: systeme.io, `owned-pending`) | |
| Economics ranking | `affiliate/priority.py`, `commission_engine.py` | |
| Algeria payout overlay | `affiliate/portfolio.py` (parallel session, **untracked**, 1,558 lines, 32-row register) | Overlaps the new matrix below; see Reconciliation |
| Ledger guards | `affiliate/ledger_firewall.py`, `affiliate_guard.py` | |

There was no 24-workstream list anywhere in the repo, so the mandate's list is used as the original mapping.

## Defects found and fixed

| # | Defect | Evidence | Fix |
|---|---|---|---|
| D1 | `registry.program_record()` read `geographic_restrictions` / `payout_threshold` / `payout_method`; the data uses `geography` / `payout_minimum` / `payout_methods`, so every program showed UNKNOWN for these | Reproduced in `TestDefectFixes` | Falls back to the stored names |
| D2 | `priority.score_program()` gave full "geographic fit" for any text containing "global" **or "algeria"**, including "PayPal receiving in Algeria is conditional". Masked by D1 until now | Same test | Full points only with an eligibility-matrix verdict; "global" earns 3 points, marked INFERRED |
| D3 | systeme.io is absent from the registry, yet `SYSTEME_AFFILIATE_ID` is configured and the site links to it | `.env` key present (value not read); `data/affiliate_links.jsonl` | Verified record prepared (`affiliate_discovery.SYSTEME_PROGRAM`). **Not merged**: it duplicates a row in the parallel `portfolio.py`. Merged, then reverted within the minute; correction appended to `data/affiliate_discovery_log.jsonl` |

## New (tested, read-only)

- `affiliate/eligibility_matrix.py`: separate eligibility and payout states per program, with Algeria evidence from `data/affiliate_algeria_evidence.json`.
- `affiliate/opportunity_rank.py`: score = economics × eligibility factor × payout factor + account bonus. Every component is exposed, and unknowns are penalised.
- `affiliate/workstreams.py`: WS-01 … WS-24, derived live from the registry.
- `tests/test_affiliate_workstreams_eligibility.py`: 14 tests.

## Current state (VERIFIED from these modules, 17:26 UTC)

- **Eligibility:** 4 programs have eligibility evidence (AWeber, n8n, Brevo, SiteGround, all "no country restriction stated"); 13 are UNKNOWN.
- **Payout:** 0 verified, 4 conditional (all via PayPal, whose Algeria receiving is conditional), 13 unverified.
- **Workstreams:** 7 PAYOUT_HOLD, 5 VERIFYING, 12 NO_CANDIDATE (no program in the registry for that buyer problem).
- **Ranking:** AWeber 46.9, n8n 44.1, Brevo 39.9, SiteGround 39.9, then DigitalOcean 13.1. DigitalOcean has the best economics (82) but unknown Algeria eligibility.

## Best current candidate (INFERRED, needs the founder)

**systeme.io**, which is not ranked only because of D3:

- **Account:** an affiliate ID is already configured, and the program has no application step ("Anyone can join").
- **Terms:** 60% lifetime recurring, lifetime cookie, $30 minimum, paid monthly on the 10th (official page, 2026-10-22).
- **Payout:**
  - PayPal works from Algeria only conditionally.
  - Wire needs an IBAN and an 11-character SWIFT, and is only available after the first sale. Algerian banks use a RIB, so this is unverified.

Under the same formula it would score roughly economics × 1.0 × 0.7 + 10, which puts it first. This is ESTIMATED; it is not computed until the merge happens.

## Blocked on the founder (not done, by rule)

1. **Payout route:** confirm a working way to receive the money in Algeria (a PayPal account that can withdraw, or a bank that accepts systeme.io's IBAN/SWIFT form). Without it, no program can reach PAYOUT_VERIFIED.
2. **Account standing:** confirm that the systeme.io affiliate account is active. The ID rotation flagged earlier is still open.
3. **Reconciliation:** decide whether `affiliate/portfolio.py` (parallel) or the new matrix becomes the Algeria model, and whether systeme.io moves into the main registry.
4. Any application, terms acceptance, publication or outreach.

## Next safe action

Read the systeme.io affiliate agreement (`https://systeme.io/affiliate-agreement`) to capture prohibited methods and disclosure rules. Then prepare one WS-02/WS-18 guide locally, using the existing `affiliate/content_qa.py` checks. Do not publish it.

## Checkpoint 2 — systeme.io agreement and the live guide (same day)

**Affiliate agreement read** (`https://systeme.io/affiliate-agreement`, VERIFIED; no last-updated date is shown):

- **Commission:** 60% per new customer. The rate may be changed via the Affiliate Tool.
- **Attribution:** lead-based and lifetime. It is lost if the lead buys through another affiliate's link on a payment page.
- **Commission is void if** the customer asks for a refund within 30 days, is not retained for 30 days, or is a self-referral.
- **Promotion rules:**
  - No deceptive marketing.
  - Unsolicited-email laws apply.
  - **No competitor trademarks in promotion of systeme.io.**
  - No implied endorsement by systeme.io.
- **Other terms:**
  - The affiliate must be over 18.
  - The affiliate pays all taxes and bank fees.
  - The agreement sets no disclosure rule; we disclose anyway.

Consequence: "X vs Y" comparison content (WS-22) must not be used to promote systeme.io.

**Reuse before new.** `affiliate/assets.py` sets this policy. An English draft (`drafts/affiliate/systeme_free_plan_ceiling_2026-10-20.md`) and a full video package already exist. The draft names no competitors. No new guide was written.

**Live page fixed locally** (`customer_site/guide-systemeio-affiliate.html`, published; not pushed):

| Defect | Fix |
|---|---|
| "معظمرواد" (missing space) and "المهتممين" (typo) | Corrected |
| "APPLICATIONImplementation" (template leftover) inside the disclosure | Removed |
| Disclosure placed after the affiliate link | Moved before it |
| Link marked only `nofollow` | `rel="sponsored nofollow noopener"` |
| Thin page, no usable steps | Added the free-plan limits (official pricing page, April 2026, checked 2026-10-22) and the 6 setup steps from the official help article (`Automations → Rules`, `Funnel step form subscribed` → `Subscribe to campaign`, button action `Submit form`) |

**QA:**

- `affiliate/content_qa.py` gained two checks:
  - `forbidden_terms`, for terms a program's agreement bans.
  - Fused/template tokens.
- The revised page passes, including the "disclosure before link" check.
- A scan of every other `customer_site/*.html` page found no fused tokens.

The affiliate ID in the link stays as-is. It is the existing, allowlisted exposure in `tests/test_no_committed_affiliate_links.py`, and its rotation is still a founder item.

**Publication** happens only on `git push`, and it needs founder approval.

## Checkpoint 3 — hardening cycle (same day)

### Disclosure placement, site-wide (OBSERVED, static scan)

- **Third-party affiliate links:** only one exists on `customer_site/` (systeme.io). Its disclosure comes before it, and it is marked `rel=sponsored`.
- **The Amazon standing-desk page:** its disclosure sits at the top. Links are marked `sponsored` only when an affiliate tag is attached; no tag is configured today.
- **First-party links:** 12 pages link to the founder's own store (`aekraft.gumroad.com`) or own site with `?ref=` source tags. These are not affiliate links and need no disclosure.
- **New test:** `tests/test_affiliate_disclosure_placement.py` now enforces three things:
  - the disclosure comes before every third-party affiliate link;
  - every such link is `rel=sponsored`;
  - systeme.io links never use `www`.

### systeme.io link and attribution

| Check | Finding | Basis |
|---|---|---|
| `SYSTEME_AFFILIATE_ID` set | yes; format `sa` + 40 hex | OBSERVED, value not printed |
| Page link uses the configured ID | yes, 1 of 1 | OBSERVED, compared without printing |
| Link format | `https://systeme.io/?sa=<id>` matches the help center; `www` would break tracking | VERIFIED (help.systeme.io, articles 162/328) |
| Whether a click records a referral | **UNKNOWN**. Per the agreement, a referral exists only after a free signup. Testing it would mean a self-referral or a fake lead, which is prohibited, so it was not attempted. Only the founder's Affiliate Dashboard can show recorded leads | — |

**Documented vs. in-account.** The guide's steps (`Automations → Rules`, `Funnel step form subscribed`, `Subscribe to campaign`) come from help article 284 (documented). No setting was checked inside an actual systeme.io account.

### Payout from Algeria

| Route | Status | Evidence |
|---|---|---|
| PayPal receive | CONDITIONAL | US bank account or Visa card, 30-day initial hold, 4.9% + fixed fee (OBSERVED, `reports/PAYPAL_ALGERIA_EVIDENCE_2026-10-22.md`). Today's re-fetch returned only the page title; the earlier extract stands |
| PayPal to a local bank | CONDITIONAL | via an external provider at 2.0% + $1.50, plus the provider's own fees (OBSERVED, published fee) |
| systeme.io wire | UNKNOWN | requires an IBAN. iban.com lists Algeria only as "Partial IBAN Countries (Experimental)", 24 characters, and another source says 26 (OBSERVED). Whether the form accepts it is untested |
| Stripe (PartnerStack) | BLOCKED | Stripe is not available in Algeria |
| Payoneer (Awin) | UNKNOWN | Awin does not confirm Algeria |
| impact.com wire in DZD | LISTED | the strongest rail found; no candidate program uses it yet |
| Founder's own account | UNKNOWN | founder-only |

### Product pipeline

- **Not done.** No new product was built: `CLAUDE.md`'s golden rule says no new product before the first dollar, there are 0 sales, and the bottleneck is payment and distribution.
- **Done.** `tests/test_listing_copy_residue.py` scans every tracked product listing file (49 found) for:
  - unfilled placeholders;
  - income-guarantee phrases;
  - fused template tokens.

  It found 0 defects. Two real names that look fused, `CAMAudit` and `QUICKFix`, are allowlisted with reasons.

## Tests (2026-10-22)

- **New tests:** 14 passed.
- **Affiliate suite** (47 files that touch the registry or affiliate modules): 599 passed, 6 failed.
- **The 6 failures:**
  - 2 were mine. The registry addition duplicated a row in `portfolio.py`; I fixed this by reverting the addition, and those tests now pass (22/22).
  - 4 come from elsewhere:
    - `test_alert_path` always fails, because its own source contains the word it bans.
    - `test_ledger_firewall` depends on a time window that has expired.
    - `test_phase4_integration` checks a `server.js` hash, and the parallel session has uncommitted edits to `server.js`.
    - `test_prospecting` needs an MCP endpoint that is not running.
