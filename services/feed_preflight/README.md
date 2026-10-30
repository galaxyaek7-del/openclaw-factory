# Merchant Center feed preflight (Micro-B2B demonstration)

Status: DEMONSTRATION. Not offered, not sold, no customer has seen it.

## Buyer
Small online sellers (Shopify, WooCommerce, Etsy-to-Google exports) who list products in Google Shopping and free listings and manage their own feed, without an agency.

## Problem, with evidence
- Disapproved items are removed from Shopping ads and free listings until fixed and re-reviewed. Common item-level causes include an invalid or missing GTIN, a wrong price format and a missing required attribute (OBSERVED: [Channable](https://www.channable.com/blog/google-merchant-center-disapproved-products), [DataFeedWatch](https://datafeedwatch.com/blog/google-merchant-center-disapproved-products); vendor blogs, not Google).
- People pay to have this fixed (OBSERVED, 2026-10-29):
  - [masterkey313](https://fiverr.com/masterkey313/fix-google-merchant-center-disapproved-products-and-feed-errors): $40 for up to 5 products, $100 for a full-feed audit, $250 with 30 days of monitoring.
  - [hasan713](https://fiverr.com/hasan713/fix-google-merchant-center-feed-error-and-item-issue): $30 for 70 product errors; 597 orders completed, 25 reviews; listed past orders range from up to $50 to $100–$200.
- Those sellers fix errors after Google has already disapproved the items, and they need access to the merchant's account.

## How this differs
- **Before upload:** it runs on the exported file before the feed is uploaded.
- **No account access:** it needs no Merchant Center access.
- **Cited:** each finding cites the Google rule page it comes from ([product data specification](https://support.google.com/merchants/answer/7052112), [GTIN](https://support.google.com/merchants/answer/6324461)).
- **No guessed codes:** it never invents a GTIN.
- **Scope stated:** what Google only decides at review is listed as not checked.

## Reproducible example
```
python services/feed_preflight/build_demo.py
```
Inputs and outputs:
- **Input:** `demo_package/input_feed.csv`, 12 synthetic products from an invented store. GTINs are generated with correct or deliberately wrong check digits.
- **Output:** `demo_package/report.json` and `report.md`. 10 errors and 3 warnings; 8 rows have an error, 4 have none.

The faults it finds:
- comma decimal price;
- wrong GTIN check digit;
- "In Stock" instead of `in_stock` (a warning: a spelling variant of the listed value);
- duplicate id;
- link without a scheme;
- restricted GS1 range;
- title over 150 characters;
- empty image link;
- sale price not below price;
- zero price;
- `identifier_exists=no` with a GTIN.

The code is `preflight.py`. It reuses `services/spreadsheet_normalization/engine.py` for header and cell normalisation and its credential scan, and refuses files carrying secrets.

## Scope and exclusions
- **In scope:** one feed file (CSV, TSV, or RSS/Atom XML; XML with a DOCTYPE or entity declarations is refused), a row-by-row fix list, and one re-check after the seller's fixes.
- **Excluded:**
  - landing-page price matching;
  - policy and image review;
  - category-specific attributes;
  - account suspensions;
  - shipping and tax settings;
  - editing the feed or the store;
  - any promise of approval.

## Pricing hypothesis (UNKNOWN until a buyer answers)
- **Price:** $29 per feed up to 500 rows; $59 up to 5,000 rows.
- **Reasoning:** below the $40–$100 entry points above, because the deliverable is a report, not hands-on fixing.
- **Confidence:** low. Whether sellers pay for a report rather than a fix is the main open question.

## $0 validation
1. **Free check offer:** send the founder a feed (no account access), get the report.
2. **Intake:** runs through `inquiry_intake.py`, once a public receiver exists. Until then the founder can run it on a file a contact sends privately.
3. **Feedback:** one question after delivery: "Did this find a problem Google later flagged, or that you fixed?" (yes / no / partly). It is recorded as a review event in the inquiry queue.

## Continue, modify, stop
- **Continue:** at least 3 of the first 10 free reports find an error the seller confirms and fixes, and at least 1 seller asks for a second run.
- **Modify:** sellers want the fixes done, not a list. Move to a done-for-you offer, or drop it.
- **Stop:** no feed is submitted within 60 days of a live, measured offer page, or the report finds nothing sellers did not already know.
