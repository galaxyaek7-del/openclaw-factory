# Distribution: product coverage matrix

Source: `data/distribution_offers.json` (2026-10-23) and a QA run of a draft for every eligible offer on every suitable platform.

## Offers by arm and eligibility

| Arm | Offer types | Total | Eligible | Needs review | Not eligible |
|---|---|---|---|---|---|
| digital_products | 92 Gumroad products, 12 tool pages, 10 product pages | 114 | 100 | 4 | 10 |
| education_content | 29 guides, 6 blog posts | 35 | 35 | 0 | 0 |
| affiliate | 17 programs, 2 affiliate pages | 19 | 2 | 0 | 17 |
| services | 3 service pages | 3 | 0 | 3 | 0 |
| video | 2 rendered pilots | 2 | 0 | 0 | 2 |
| **Total** | | **173** | **137** | **7** | **29** |

Internal tools (Mission Control, scripts) are not offers and are excluded.

## Why offers are not eligible or need review

| Reason | Offers |
|---|---|
| Affiliate program not approved, no approved link | 17 |
| Product page for a product that is not on sale (page says proposed / not yet listed) | 7 |
| Site page not on origin/main | 4 |
| Gumroad listing uploaded but not published | 3 |
| Service: delivery capacity and terms need founder confirmation | 3 |
| Duplicate live title (GR-0fa92aeb1a, GR-ab323215ab) | 2 |
| Video rights unresolved | 2 |
| Product page is stale: says not listed, but the product is live (Meeting Cost & ROI Calculator; GR-41d87224ab) | 2 |

## Drafts passing QA, every eligible offer x suitable platform

| Arm | LinkedIn | X | Instagram | TikTok |
|---|---|---|---|---|
| digital_products | 100/100 | 100/100 | 0/87 (no rendered JPEG images) | 0/87 (no rendered video; 2 with video but rights unresolved) |
| education_content | 22/35 | 22/35 | not suitable | not suitable |
| affiliate (pages) | 2/2 | 2/2 | not suitable | not suitable |

The 13 education failures are all the same public-copy defect: the guide pages themselves say "UNKNOWN -- not captured at this granularity in the source registry" (see the risk register, D-R1).

## Representative campaign (in the job ledger)

| Offer | Arm | LinkedIn | X | Instagram | TikTok |
|---|---|---|---|---|---|
| GR-003d8ce46f Trademark DIY Filing Action Kit | digital_products | QA passed | QA passed | blocked: images | blocked: video |
| GR-04864e2091 EU AI Act Transparency & AI Literacy Quickstart Checklist | digital_products | QA passed | QA passed | blocked: images | blocked: video |
| B14-001 13-Week Cash Flow Forecast | digital_products | QA passed | QA passed | blocked: images | blocked: video rights UNRESOLVED (pilot A exists) |
| B14-002 Rental Property Deal Analyzer | digital_products | QA passed | QA passed | blocked: images | blocked: video rights UNRESOLVED (pilot B exists) |
| SITE-affiliate-program | affiliate | QA passed | QA passed | | |
| SITE-affiliate-standing-desks | affiliate | QA passed | QA passed | | |
| SITE-blog-etsy-appeal-evidence | education_content | QA passed | QA passed | | |
| SITE-blog-etsy-appeal-mistakes | education_content | QA passed | QA passed | | |

16 drafts await approval; none is approved or posted.
