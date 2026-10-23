# Distribution: tracking and attribution

## Links

Every draft links to its offer's own destination with four parameters:

| Parameter | Value |
|---|---|
| `utm_source` | `linkedin`, `tiktok`, `instagram` or `x` |
| `utm_medium` | `social_organic` |
| `utm_campaign` | `gf-<offer id>-<YYYYMM>`, e.g. `gf-b14-001-202610` |
| `utm_content` | the draft id, e.g. `b14-001-x-v1` |

QA rejects a draft whose link is missing a parameter, points elsewhere, carries another platform's source, or belongs to another offer's campaign.

## Metrics ledger

`tracking.record_metric()` writes one row per observation to `data/social_distribution_metrics.jsonl` (REAL) or `*.simulation.jsonl` (SIMULATION); the function refuses to cross them. Each row has environment, campaign, platform, metric, value, evidence class, source, evidence, method and limitations.

| Class | Meaning | Rule |
|---|---|---|
| OBSERVED | reported by the platform, Gumroad or a network | REAL rows need a source and evidence |
| DERIVED | calculated from recorded rows | same |
| INFERRED | plausible, unproven | never shown as fact |
| UNKNOWN | not established | carries no value |

Metrics: content created/approved, scheduled, published, failures, impressions, reach, video views, watch time, engagements, outbound clicks, landing sessions, product-page visits, leads, checkout starts, purchases, affiliate clicks, commissions, refunds, net revenue.

## What can be measured today

| Signal | Source | State |
|---|---|---|
| Drafts, approvals, posts | job ledger | OBSERVED (0 posts) |
| Impressions, reach, engagement, clicks on platforms | platform analytics | UNKNOWN: no platform access |
| Visits to site pages | none | UNKNOWN: GitHub Pages has no beacon receiver |
| Gumroad purchases and their referrer | Gumroad sales API | available when a sale happens; 0 sales today |
| Gumroad page views by UTM | Gumroad dashboard | UNKNOWN whether exposed by API; not used |
| Affiliate commissions | network statements | 0 approved programs |

## Attribution rules

- A purchase is attributed to a campaign only if its own recorded referrer or UTM names it; otherwise it stays unattributed.
- Each purchase is counted once, across all platforms.
- A post followed by a sale is correlation; the report says so.
- Simulated events never enter the real ledger or the dashboard's commercial section.

## How verified revenue will be measured

Net verified revenue = Gumroad sales (and, later, network-confirmed commissions) minus refunds, each row OBSERVED with its transaction id, attributed to a campaign only by its own referrer/UTM. Today: $0.00.
