# Galaxy Forge — Reach Problem Solution

Date: 2026-10-17. Facts are OBSERVED unless marked UNVERIFIED.

## Current state
- **Products:** 79 on Gumroad, 76 published (Gumroad API, read-only, 2026-10-17).
- **Arms that can sell today:** Gumroad only. Paddle checkout is blocked by onboarding; X needs paid API credits; Payhip and Etsy have no credentials; KDP is manual. See `reports/ARMS_STATUS_AR_2026-10-16.md`.
- **Visitors:** unmeasured. The site's page-view beacon has no receiver (GitHub Pages returns 404), and Gumroad listing views live only in the dashboard. "Zero visitors" is not proven; "zero measured" is.
- **Sales:** 0. Every product reports `sales_count = 0`, and `data/sales_ledger.jsonl` has no sale event.

## Root cause
Nothing brings buyers to the listings, and nothing measures whether anyone arrives. Distribution (listing on Gumroad) works; reach and measurement do not.

## Highest-impact actions (ranked)

### 1. Google Search Console (founder, about 30 minutes)
- **Why:** free organic traffic, plus the first real impressions/clicks data the factory has ever had.
- **How:**
  1. Add the property `https://galaxyaek7-del.github.io/openclaw-factory/` and download the HTML verification file.
  2. `python scripts/deploy_gsc_verification.py --file <path> --dry-run`, then the same command without `--dry-run` (it publishes the file).
  3. Click Verify, then submit `sitemap.xml` (61 URLs, validated).

### 2. Cover images on the Gumroad listings (newly found, 2026-10-17)
- **Why:** 75 of 76 published listings have no cover image (`covers`, `thumbnail_url`, `preview_url` all empty). The only listing with a cover is the EU AI Act Toolkit, which is being withdrawn. A listing without an image is weak in Gumroad search and Discover, and in any shared link.
- **Assets:** 32 listings likely have a matching cover already in `books/covers/`, matched by name. Each needs a visual check before upload. 43 need a cover generated (the factory has `cover_designer_v2.py`).
- **Constraint:** Gumroad's API has no cover-upload endpoint (found earlier). Upload is through the dashboard, by the founder, or by browser automation only with the founder's explicit per-action approval.

### 3. Gumroad listing quality (factory can prepare)
- **Source:** `scripts/gumroad_seo_audit.py` → `data/seo/gumroad_seo_audit.json`.
- **Scores:** average 71.2 across published listings. 4 HIGH priority, 40 MEDIUM, 32 LOW.
- **Fixable gaps:**
  - 38 listings have fewer than 5 tags;
  - 7 descriptions are under 500 characters;
  - 6 titles are over 60 characters.
- **Before any change:** these are live listing edits, each needing the founder's approval and going through the existing write gate.
- **Gumroad Discover eligibility rules:** UNVERIFIED.

### 4. One real social signal per week (founder approval per post)
- **Why:** a link from real content helps indexing and can bring direct visitors.
- **Constraint:** every public post is publishing and needs approval. X is off (paid API).

### 5. Affiliate activation (founder outreach)
- **Basis:** the B12-001 affiliate kit exists (`arms/affiliate/b12_001_kit.json`).
- **Constraint:** outreach means sending messages, which is founder-only.

## What NOT to do
- ❌ **Open more arms:** the same products in more places do not create visitors.
- ❌ **Create more products:** 76 are already published and unseen.
- ❌ **Paid ads:** the budget is $0.
- ❌ **X API:** paid (HTTP 402).

## 30-day plan

**Week 1**
- [ ] Search Console verification + sitemap (founder)
- [ ] Withdraw the EU AI Act Toolkit (founder, manual)
- [ ] Cover pack: verify the 32 matched covers and generate the 43 missing ones (factory); upload (founder)

**Week 2**
- [ ] Tag and title fixes for the 44 HIGH/MEDIUM listings, prepared by the factory and applied with approval
- [ ] B12-001 listing, if the founder authorises it (tags ready: `data/seo/b12_001_tags.json`)

**Week 3**
- [ ] First social signal (approved post)
- [ ] Gumroad CSV export, then `src/measurement/gumroad_csv_parser.py`

**Week 4**
- [ ] First real data review: Search Console impressions and clicks, Gumroad views
- [ ] Decide: scale what shows real demand, stop the rest
