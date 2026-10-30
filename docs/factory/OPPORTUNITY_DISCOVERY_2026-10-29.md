# Opportunity discovery cycle: 2026-10-29

Evidence classes: OBSERVED (read at the source this session), DERIVED (computed from observed data), INFERRED (judgement), UNKNOWN.
Nothing here is validated demand. No customer was contacted; all research was read-only web access.

## Method
For each business model:
1. Look for a buyer problem with a traceable source.
2. Record the alternatives and the prices observed.
3. Ask whether a $0 test exists that does not depend on Gumroad.
4. Take the strongest candidate per model to a working demonstration, reusing existing code.

## Candidates

| # | Model | Candidate | Buyer | Evidence of the problem | Alternatives and prices | Reach | Restrictions | Decision |
|---|---|---|---|---|---|---|---|---|
| 1 | Micro-B2B | Merchant Center feed preflight | Small sellers in Google Shopping | Disapprovals remove items until fixed (vendor guides, OBSERVED) | Fiverr: $30 / $40–$250 per fix job, one seller with 597 orders (OBSERVED) | Seller forums, own guide pages; needs intake | Google's rules change; no approval promise | **Demonstrated** (`services/feed_preflight/`) |
| 2 | Productized automation | Accessibility quick-check | Small shops, US or EU-selling | 3,117 US federal suits in 2025 (secondary, OBSERVED); EAA in force since 28 June 2025 | Fiverr ~$50 to $600–$800; free axe/WAVE | Own site before/after as proof; needs intake | Must never claim compliance (FTC accessiBe order) | **Demonstrated** (`services/accessibility_check/`) |
| 3 | Research / data | EAA penalty register | EU-selling sellers and their advisers | Published penalty tables conflict; one contradicts the statute it cites (OBSERVED: BFSG s. 37 vs. Deque) | Free vendor tables (Deque, others), no verification status | Free sample, change alerts; needs intake | Not legal advice; several languages | **Demonstrated** (`data_products/eaa_penalty_register.py`) |
| 4 | Micro-B2B (existing) | Catalogue clean-up | Small teams with messy exports | Fiverr $10–$50 (OBSERVED, phase 2) | Many low-price gigs | Same as 1 | | Continue; shares the engine with 1 |
| 5 | Data (existing) | USPTO fee table with change history | Trademark DIY filers | USPTO page (OBSERVED, phase 2) | Free on USPTO and law-firm sites | Free sample | | Continue as a free asset, weak paid case |
| 6 | AI operations (existing) | n8n automation audit | Operators of fragile automations | Own incident history (OBSERVED internally); external demand UNKNOWN | Agencies, n8n's own UI | Needs intake | API key handling | Hold at demonstration |
| 7 | Content-supported | Guides feeding offers 1–3 (feed errors, accessibility basics, EAA penalties) | Same buyers | Search interest UNKNOWN (no keyword tool) | Many vendor blogs | Site + Telegraph | Visit measurement missing | Prepare only after a receiver exists |
| 8 | Original media / licensing | Licensing kids episodes to Arabic educational platforms | Platforms, schools | UNKNOWN: no buyer evidence found or searched in depth | | | Native-language review and voice route still open | Hold |
| 9 | Affiliate | (existing arm) | | Payout route unverified | | | | Hold (unchanged) |

## Why these three
- **Different buyers and channels:** a seller's data file (1), a site's markup (2), and a legal-information need (3). None needs a marketplace listing to be tested.
- **Reuse:**
  - 1 reuses the spreadsheet engine;
  - 2 reuses nothing but runs on our own pages;
  - 3 reuses the data-card validator used for the USPTO release.
- **Complementary:** 2 and 3 cover the same buyer at two price points, so one inquiry channel serves both.

## Shared blocker
- All three need a working public intake (see `inquiry_intake.py` readiness), and visit measurement to read any page-level result.
- None of the demonstrations depends on Gumroad, affiliate approval, LinkedIn, or kids narration.

## Unknowns that decide continuation
1. Willingness to pay for a report rather than a done-for-you fix (1, 2).
2. Whether a statute-verified register is worth paying for when vendor tables are free (3).
3. Search or community demand volume: no keyword data source exists in this factory ($0 constraint).

## Sources
- Feed preflight:
  - [Google product data specification](https://support.google.com/merchants/answer/7052112)
  - [Google GTIN rules](https://support.google.com/merchants/answer/6324461)
  - [Fiverr masterkey313](https://fiverr.com/masterkey313/fix-google-merchant-center-disapproved-products-and-feed-errors)
  - [Fiverr hasan713](https://fiverr.com/hasan713/fix-google-merchant-center-feed-error-and-item-issue)
  - [Channable](https://www.channable.com/blog/google-merchant-center-disapproved-products)
- Accessibility quick-check:
  - [Seyfarth count via beaccessible](https://beaccessible.com/?p=8297)
  - [FTC / accessiBe (TechCrunch)](https://techcrunch.com/2025/01/03/ftc-orders-ai-accessibility-startup-accessibe-to-pay-1m-for-misleading-advertising)
  - [Fiverr accessibility audit example](https://fiverr.com/victortools/run-ada-wcag-website-accessibility-compliance-audit-report)
- EAA penalty register:
  - [BFSG s. 37](https://www.gesetze-im-internet.de/bfsg/__37.html)
  - [S.I. 636/2023](https://www.irishstatutebook.ie/eli/2023/si/636/made/en/print)
  - [Deque EAA country data](https://www.deque.com/european-accessibility-act-eaa-compliance/country-compliance-data/)
  - [BCLP on the EAA](https://www.bclplaw.com/en-US/events-insights-news/what-is-the-european-accessibility-act-and-what-impact-will-it-have-on-your-business.html)
