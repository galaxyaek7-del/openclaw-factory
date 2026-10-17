# B12-001 — Post-Publish Measurement Plan

## Day 1 After Publishing
□ Confirm listing live on Gumroad (open URL, $14.99 rendered)
□ Test purchase flow: BUYING YOUR OWN PRODUCT COSTS A REAL $14.99
  (plus Gumroad fees; refund reverses it but touches real money).
  This is a FOUNDER-ONLY financial action — not routine QA.
  Skip it unless explicitly authorized; the listing preview check
  below covers the essentials for free.
□ Free alternative: verify price/file/cover render in the listing
  preview + confirm the listing URL resolves (no purchase needed).
□ Tracking on our pages: nothing to activate — page-view beacons are
  already inline on site pages (page_id only, fail-safe). NOTE: they
  cannot run on Gumroad-hosted pages at all, so post-publish
  measurement is the Gumroad dashboard ONLY. `gf_tracker.js` does not
  exist; do not list it as a step.
□ Record baseline: 0 sales, 0 views (dashboard read by founder).

## Week 1 Metrics to Watch
(Check Gumroad dashboard manually — founder reads.)

Daily:
- Views on listing
- Conversion rate (views → purchases)
- Traffic sources

Record in:
data/measurement/week1_log.json
{
  "day_1": {"views": 0, "sales": 0},
  "day_2": {"views": 0, "sales": 0},
  ...
}
(Create the directory on first write. Zeros are starting values to
overwrite with dashboard readings, never claims.)

## Week 2: Distribution Start
□ Share UTM link (affiliate channel, once it exists)
□ Share on 1 platform (best fit, rules confirmed first)
□ Record which source sends traffic

## Month 1 Review
□ Total views
□ Total sales
□ Revenue: $[actual]
□ Conversion rate: [actual]%
□ Best traffic source: [actual]
□ Decision: Scale / Iterate / Hold / Kill

## Evidence Gate for Scaling
Cannot activate second product until:
□ B12-001 has at least 1 real sale OR
□ 30 days of data collected with analysis OR
□ Founder explicit directive to advance
