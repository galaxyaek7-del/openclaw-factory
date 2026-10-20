# Affiliate Asset Status

Date: 2026-10-20
Asset: "systeme.io free plan: what it covers, and the three limits that force an upgrade"

## Where it stands

| Field | Value |
|---|---|
| Source | `drafts/affiliate/systeme_free_plan_ceiling_2026-10-20.md` |
| Body words | 1,032 (target was 900) |
| Placeholders in source | 2: one in front matter, one in the reader-facing CTA |
| Rendered output | `drafts/affiliate/rendered/systeme_free_plan_ceiling_2026-10-20.md` |
| Rendered size | 6,475 bytes |
| Rendered link domain | systeme.io |
| Disclosure | Present at the top, reader-facing: "I'm an affiliate for systeme.io..." |
| Real link in git | No. The rendered directory is ignored; `git check-ignore` exits 0 |
| Publication | NOT_PUBLISHED. `publication_authorized: false` |
| Impressions | 0 |
| Clicks on this asset | 0 |
| Commissions | 0 |
| Verification of claims | Pricing and affiliate terms read 2026-10-20 |

## What the article claims, and what backs it

Every number in the article comes from the pricing table read on 2026-10-20:
2,000 contacts, 3 funnels, 1 course, 1 blog, 1 custom domain, 1 automation
rule, 1 email campaign, unlimited emails, 0% transaction fees, and the three
paid tiers at $17, $47 and $97.

Three items are explicitly not verified in the article itself: pro-rata refunds,
whether limits changed since April 2026, and multi-user limits.

## The honest weakness of this asset

It has no distribution. A rendered file is not a campaign. Until it is placed
somewhere a reader can arrive from, its expected clicks are zero, and this
document does not pretend otherwise. The zero-cost plan in
`ZERO_COST_CAMPAIGN_PLAN_2026-10-20.md` names the options and the stop rules.

The article also has no conversion measurement. A click can be counted through
`affiliate_commerce/click_tracking.py`, but a sale cannot: systeme.io does not
provide this factory a postback. Any commission claim before a real partner
dashboard line exists is unsupported.

## Rendering rules (enforced in code)

1. The source keeps `[TRACKED LINK ...]`; the real URL is substituted only at
   render time.
2. Output must be inside `drafts/affiliate/rendered/` and must be ignored by
   git. Both are checked before a byte is written.
3. `affiliate_guard.check_link` must approve the domain and find the disclosure.
4. At least two placeholders are required, so the body always carries a link.
5. The renderer prints the domain and counts, never the URL or the id.

Verified by `tests/test_render_and_attribution_integrity.py` (16 tests).

## Next action that changes the numbers

The founder authorizes a publishing destination, not this session. After that,
one real click from a real reader is the first measurable event.
