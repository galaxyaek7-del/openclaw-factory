# Distribution: content standards

Every draft is generated from the offer's own recorded facts and checked by `social_distribution.content.qa()`. A draft with any issue cannot be approved.

## Source of facts

- Copy comes from `content_generation/repurposing_engine.py` (deterministic, no LLM) and the listing's own text. The listing's sentences are approved facts, including its honest disclaimers ("No result is guaranteed") and worked-example amounts.
- Anything the templates add is checked: amounts must equal the offer price; no forbidden claims.
- Free content is labelled free only for guides and blog posts; other pages say "Details".
- A verified live listing is never called a "validation concept"; an unverified one is never presented as available.

## Checks (all automatic)

| Check | Rule |
|---|---|
| Eligibility | the offer must be ELIGIBLE (live destination, no rights/approval/availability block) |
| Platform fit | only platforms suitable for the offer type |
| Length | LinkedIn 3,000; Instagram and TikTok captions 2,200; X 280 with links counted as 23 |
| Tracked link | present, https, the offer's own destination, all four UTM fields, campaign belongs to the offer; in the text for LinkedIn and X |
| Price | every amount the templates add equals the offer price |
| Forbidden claims | testimonials, "trusted by", "best-selling", "#1", "guaranteed", fake urgency ("limited time", "last chance", "act now") and the affiliate banned phrases |
| Residue | no placeholders and no data-gap text such as "UNKNOWN" or "not captured at this granularity" |
| Brand | `brand_dna.validate_customer_facing_text()` (reputation, neutrality, copyright/trademark, fake urgency); a broken checker blocks |
| Visuals | TikTok needs a rendered video with rights CLEARED; Instagram needs rendered JPEG images |
| Synthetic media | drafts that use a generated video are flagged `synthetic_media` for platform disclosure |

## Style

- One problem, one audience, one offer per post; the value first, the link last.
- Different structure per platform: LinkedIn long-form with the listing's own sections; X a sentence-bounded summary; Instagram caption plus slide plan with "Link in bio"; TikTok hook from the listing's first sentence plus scenes.
- No promises of results, traffic, followers or income. No engagement bait, no bulk messages, no automated comments or follows.
- Language: English today (the listings are English). Arabic posts need Arabic listings or a reviewed translation that keeps every fact; not generated automatically.
