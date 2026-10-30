# Accessibility quick-check (productized automation demonstration)

Status: DEMONSTRATION. Not offered, not sold. Automated rules plus a human summary; no AI model is used.

## Buyer
Small online shops and service sites, in the US or selling to EU consumers, that have never had any accessibility review and want a first, inexpensive fix list.

## Problem, with evidence
- **US lawsuits:** 3,117 federal website-accessibility suits were filed in 2025, up from 2,452 in 2024 (Seyfarth Shaw's count, via [beaccessible.com](https://beaccessible.com/?p=8297); OBSERVED secondary). Estimates put online retail at roughly 69–77% of cases (INFERRED, vendor sources).
- **EU obligation:** the European Accessibility Act has applied since 28 June 2025, including to e-commerce services offered to EU consumers. Micro-enterprises providing services are exempt (OBSERVED: [BCLP](https://www.bclplaw.com/en-US/events-insights-news/what-is-the-european-accessibility-act-and-what-impact-will-it-have-on-your-business.html), [Davis Wright Tremaine](https://www.dwt.com/insights/2025/07/european-accessibility-act-digital-products)). Penalties: see the research sample `data_products/releases/eaa-penalty-register/`.
- **Cautionary precedent:** the US FTC ordered accessiBe to pay $1M over claims that its automated tool made sites WCAG-compliant ([TechCrunch](https://techcrunch.com/2025/01/03/ftc-orders-ai-accessibility-startup-accessibe-to-pay-1m-for-misleading-advertising)). An honest offer must not claim compliance.
- **Paid alternatives (OBSERVED, Fiverr listings, 2026-10-29):** from about $50 for a single page to $600–$800 for a 21-page WCAG 2.2 audit ([example](https://fiverr.com/victortools/run-ada-wcag-website-accessibility-compliance-audit-report)).
- **Free alternatives:** browser tools such as axe and WAVE.

## How this differs
- **For whom:** a non-technical owner gets a ranked fix list per page, with the WCAG 2.2 criterion for each finding and the line where it occurs.
- **Honest scope:** a fixed "not checked, needs a person" section in every report.
- **No compliance claim:** the report never states compliance.
- **Limit:** free tools find the same machine-checkable issues. The value tested here is the summary and the price, not unique detection.

## Reproducible example
```
python services/accessibility_check/build_demo.py
```
- **Synthetic page:** `demo_package/synthetic_page.html` is an invented shop page carrying each fault. Report: 7 errors, 4 warnings, all 11 faults found.
- **Real sample on our own site:** `demo_package/own_site_report.md` covers Galaxy Forge's own 118 public pages, the only real site we may scan without asking.
  - **Result:** 0 errors and 22 warnings: 11 form fields labelled only by placeholder text, 5 hidden spam-trap fields still announced to screen readers, 3 pages with no h1, 3 skipped heading levels.
  - **Status:** these are real fixes for our own pages, not yet applied.

The code is `check.py`, with tests in `tests/test_phase3_demonstrations.py`.

## Scope and exclusions
- **In scope:** up to 10 pages given by the client, a ranked fix list, and one re-check.
- **Excluded:**
  - keyboard and focus testing;
  - colour contrast;
  - screen-reader testing;
  - whether alt text is meaningful;
  - captions;
  - content rendered by scripts;
  - fixing the site;
  - legal advice;
  - any statement of WCAG, ADA or EAA compliance.

## Pricing hypothesis (UNKNOWN until a buyer answers)
- **Price:** $39 for up to 10 pages.
- **Reasoning:** near the low end of observed listings, because coverage is limited to automated checks.
- **Confidence:** low. The free tools are a strong substitute.

## $0 validation
1. Publish our own fixes first. A public before/after on our own site is evidence, not a claim.
2. Offer a free 3-page check through the inquiry queue once a receiver exists.
3. **Feedback:** "Which findings did you fix?" (count), recorded as a review event.

## Continue, modify, stop
- **Continue:** at least 2 of the first 10 free checks lead the owner to fix at least one finding, and at least 1 asks about the paid scope.
- **Modify:** owners ask for the fixes to be made. Price a fix service, or pair with the micro-B2B arm.
- **Stop:** no free-check request within 60 days of a measured offer page, or owners say a free browser tool already gave them the same list.
