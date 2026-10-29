# Experiment EXP-B16-007-LI-01: problem-led vs. product-description post on LinkedIn

Status: **PENDING_APPROVAL** (recorded in `data/commercial_experiments.jsonl`, 2026-10-29). Nothing has been posted.

## Why this product and channel

| Fact | Value | Class |
|---|---|---|
| Product | B16-007 Freelance Project Profitability & Effective Hourly Rate Tracker, $12, https://aekraft.gumroad.com/l/xiimbr | OBSERVED (live, cover and public page verified 2026-10-29 12:2xZ) |
| Paid demand for the same job | Etsy listing 4360973845 at $9.64; a Gumroad freelancer income tracker at $5 | OBSERVED (web-search index, 2026-10-29); prices only, sales volume UNKNOWN |
| Our sales / views today | 0 sales on any of 112 Gumroad products; product views UNKNOWN (no analytics receiver, B6) | OBSERVED (Gumroad `/v2/sales`, 2026-10-29 16:02Z) |
| Audience | freelancers, consultants, small agencies on fixed fees | INFERRED from the product's purpose |
| Channel | LinkedIn, posted by hand from the founder's own account | INFERRED fit; LinkedIn API is not connected (B26), so manual posting is the only free route |

Why not Pinterest or X: Pinterest needs a board the founder has not created (B18); X posting is spend-blocked (B26). Instagram and TikTok drafts fail QA (no rendered image or video).

## Design

One variable: the framing of the post. Same product, price, account, weekday and time.

| | Variant A (baseline) | Variant B (change) |
|---|---|---|
| Framing | product description (generated listing copy) | problem-led, built on the product's own illustrative example |
| Source | job `SJ-72586ec7a01c`, QA passed | written 2026-10-29, brand check passed |
| Tracked link | `...?utm_source=linkedin&utm_medium=social_organic&utm_campaign=gf-b16-007-202610&utm_content=b16-007-linkedin-v1` | `...&utm_content=b16-007-linkedin-v2` |

Schedule: A on a Tuesday at 09:00 founder local time; B one week later, same weekday and time. Each post is observed for 7 days.

### Variant B text

```
A fixed fee hides your real hourly rate.

Example: a brand identity project quoted at $3,000 for 30 hours looks like $100 an hour. It took 52 hours and $200 of software and contractor costs. The real rate: $53.85 an hour.

Three numbers tell you whether a project paid: the fee minus direct costs, the actual hours, and your target rate. Log them after every project and two different problems show up:
- underpriced work: the hours matched the estimate, the fee was too low
- underestimated work: the fee was fine, the hours ran over

They need different fixes: raise the price, or pad the estimate.

I made a small Excel tracker that does this for every project ($12): https://aekraft.gumroad.com/l/xiimbr?utm_source=linkedin&utm_medium=social_organic&utm_campaign=gf-b16-007-202610&utm_content=b16-007-linkedin-v2

(The figures above are an illustrative example, not a client.)
```

Variant A text is the `fields.text` of job `SJ-72586ec7a01c` in `data/social_campaign_jobs.jsonl`.

## Measurement

| Stage | Source | Who records | Evidence class |
|---|---|---|---|
| Impressions, link clicks per post | LinkedIn post analytics | founder reads; recorded with `social_distribution.tracking.record_metric(environment="REAL", ...)` | OBSERVED |
| Product views by referrer | Gumroad dashboard analytics; whether it breaks views down by UTM is not yet observed here | founder reads | OBSERVED if shown, else UNKNOWN |
| Purchases | Gumroad `/v2/sales` (loop polls every cycle); attributed by referrer/UTM via `tracking.attribute_purchases` | automatic | OBSERVED |
| Site visits | not measurable (B6) | - | UNKNOWN |

## Decision rule

- Primary metric: link clicks per 1,000 impressions.
- No decision below 30 link clicks per variant (`commercial_experiments.MIN_SAMPLE_SIZE_FOR_DECISION`). Below that the honest result is INSUFFICIENT DATA, whatever the ratio looks like.
- At or above the floor: adopt B for future posts if its rate is higher; otherwise keep A. A sale is reported separately and never extrapolated.

## Limitations

- The two posts run a week apart, so timing differs; audience growth between weeks is uncontrolled.
- A small LinkedIn following may never reach 30 clicks per variant; the experiment then ends as INSUFFICIENT DATA, which is still a result (it bounds the channel's reach).
- Gumroad view counts are platform counters, not verified human visits.

## Founder action required

1. Approve or reject the experiment.
2. If approved: post A, then B a week later, from your LinkedIn account, and send the post analytics after 7 days each.
3. Record the move to RUNNING: `commercial_experiments.update_experiment_status("EXP-B16-007-LI-01", "RUNNING", "APPROVED", "<date posted>")`.
