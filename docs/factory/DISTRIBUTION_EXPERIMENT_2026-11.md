# Multi-arm distribution experiment (prepared 2026-10-29, for founder review)

Nothing below has been posted, scheduled or sent. Every item is PENDING founder approval.
Period, once approved: 4 weeks from the first post. Evidence classes: OBSERVED, DERIVED, INFERRED, UNKNOWN.

## What the existing numbers mean

| Number | What it is | What it is not |
|---|---|---|
| 131 views on 8 Telegraph articles (2026-10-29 17:11Z) | Telegraph's own `getViews` counter per article since publication (OBSERVED) | unique people, humans (bots count), or clicks; ~10 are the factory's own loads (ESTIMATED, `data/telegraph_own_loads.json`) |
| 0 sales | Gumroad `/v2/sales` (OBSERVED) | evidence that nobody clicked; clicks are not measured |
| site page views | UNKNOWN: 70 of 118 pages carry the beacon, 0 point at a receiver | |

Click measurement that can be added without an account: tracked links (UTM) whose arrivals the
destination reports. For Gumroad that is not established (only a third-party vendor's docs
describe UTM capture, and only at checkout). For a platform's own analytics (LinkedIn,
Pinterest) the post's link clicks are reported to the founder (OBSERVED once posted).

## Channel choice per offer

| Offer (arm) | Buyer | Channel | Why | Runnable now? |
|---|---|---|---|---|
| Freelance Project Profitability Tracker (digital) | freelancers on fixed fees | LinkedIn, founder's account | professional audience, free, link-click analytics | yes (EXP-B16-007-LI-01) |
| Catalogue merge clean-up (micro-B2B) | small online sellers | seller communities where self-promotion is allowed; LinkedIn | sellers ask about messy exports there (INFERRED) | no: no recorded intake |
| USPTO fee CSV and brief (research/data) | template sellers, legal-tech builders | LinkedIn; GitHub-hosted CSV page | developers find data on GitHub (INFERRED) | no: sign-up needs intake |
| n8n automation audit (AI operations) | small n8n operators | n8n community forum (check its promotion rules first); the silent-failures guide | the failure class is discussed there (INFERRED) | no: no recorded intake |
| Not used | Pinterest | board missing; suits printables, not these offers | | |
| Not used | X | posting is spend-blocked | | |
| Not used | TikTok / Instagram | no rendered visual assets for these offers | | |

## Drafts

### D1. LinkedIn, digital product (EXP-B16-007-LI-01)

Variant A: generated listing copy, job `SJ-72586ec7a01c`. Variant B: problem-led post. Full texts,
tracked links and decision rule: `docs/factory/EXPERIMENT_EXP-B16-007-LI-01.md`.

### D2. LinkedIn, micro-B2B (after intake exists)

> Merging a supplier price list with your own shop exports? Three things a "clean" file can hide:
> a date like 03-04-2026 (3 April or 4 March?), dollars and euros in one price column, and the same
> SKU three times with different prices. I built a clean-up that fixes the formatting and reports
> those three instead of guessing. Example with invented data, before and after: [page]
> (Illustrative data, not a customer.)

Link: `.../catalogue-cleanup.html?utm_source=linkedin&utm_medium=social_organic&utm_campaign=gf-micro-b2b-202611&utm_content=d2`

### D3. LinkedIn, research/data (after intake exists)

> The USPTO trademark fees in one table: electronic and paper, with fee codes, from the official
> schedule (effective 19 January 2025, revised 14 August 2026). Free CSV: [page]. A common mistake
> it prevents: paying for a statement of use at the paper rate of $250 when the online rate is $150.

Link: `...?utm_source=linkedin&utm_medium=social_organic&utm_campaign=gf-research-202611&utm_content=d3`

### D4. n8n community (after intake exists, and only if its rules allow it)

> An n8n instance can look healthy while workflows fail: the port answers, the last run errored.
> I wrote a read-only audit that uses only the public API (no database, no credentials) and lists
> each workflow as OK, FAILING, STALE or UNKNOWN. Example with invented workflows: [page]. Happy to
> run it free for a few instances in exchange for feedback.

## Approval register

| ID | Arm | Channel | Destination live? | Intake needed? | State |
|---|---|---|---|---|---|
| EXP-B16-007-LI-01 | digital | LinkedIn | yes (Gumroad listing) | no | PENDING_APPROVAL |
| D2 | micro-B2B | LinkedIn | no (draft page) | yes | BLOCKED (intake) |
| D3 | research/data | LinkedIn | no | yes | BLOCKED (intake) |
| D4 | AI operations | n8n community | no | yes | BLOCKED (intake; forum rules UNKNOWN) |

## Decision rules (per item, after 4 weeks)

- No verdict below 30 link clicks per item (or per variant in D1); below that the result is
  INSUFFICIENT DATA, which still bounds the channel.
- Continue an offer when it produces at least one in-scope inquiry or sale; modify the framing when
  clicks arrive without inquiries; stop a channel that produced no measurable response.
