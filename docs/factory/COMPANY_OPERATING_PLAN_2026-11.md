# Galaxy Forge: operating plan toward an automated, earning digital company (2026-11)

Written 2026-10-31 on the founder's instruction: a fully automated digital company, high-value
products, real income, an advanced protection system. Facts below are OBSERVED in this repository
and its live accounts on that date unless marked otherwise.

## Where the company stands

- 112 listings live on Gumroad, 0 sales, $0 revenue (registry and sales poll).
- Production, QA, publishing (after a per-product approval), sales polling, delivery audits,
  site pages, Pinterest pins, offers and drafts, backups and audits all run in the loop without a
  person. Automation is not the missing piece.
- Visits are not measured (no analytics receiver), and no channel posts on its own: Pinterest
  has no board, Instagram and LinkedIn have no credentials, X needs paid credits, every social
  draft waits for an approval. The 8 Telegraph articles show 134 platform-counted views in total.
- Conclusion (DERIVED): the binding constraint is demand reaching the products, then evidence of
  which products buyers value. Producing more listings first would add more zero-sale listings.

## Order of work

1. **Reach buyers (unlocks everything else).** Founder steps, each a few minutes:
   create the Pinterest board "Small Business Finance Tools" (pin images exist for 109 products; the queue was last built with 99);
   install the free analytics token (`FOUNDER_ACTIONS.md` section 6); approve the 6 QA-passed
   drafts. After that the loop prepares one scheduled pin a day for your one-click review in Metricool,
   and visits are measured.
2. **Measure, then raise value from evidence.** Once visits and clicks are recorded, the
   factory ranks products by visits, conversion and refunds; it expands only listings with
   demand (the thin-listing plan's trigger) and builds new products in the categories that
   convert. Price follows delivered substance (thin-listing plan, rule to decide).
3. **Automate the remaining gates only with evidence.** Auto-publish of approved products is on.
   Removing the per-product approval, or the per-post review on Pinterest, is a founder decision;
   the recommended trigger is a first verified sale plus 30 days without a delivery defect.
4. **Protection, continuously (below).**

## Protection system

In place (OBSERVED): one write gate for every live platform write; per-product approvals bound to
the exact file, price and currency, with expiry; holds that block promotion; a delivery audit
that blocks promotion of broken promises; a secrets scan of every tracked file in CI; a guard
that keeps paid product files out of the public repository; daily restore-checked backups of
git-ignored business records; retry-on-outage for every daily check; CI on every push.

Added 2026-10-31: `scripts/company_protection_check.py`, one daily read-only check that gathers
these signals and puts any failure in the founder's decision queue (see its docstring).

Open, founder decisions: an off-machine copy of the backups (today everything sits on one disk,
2.4 GB free); the opencode database clean-up that frees about 140 GB; unpublishing the three
"$0+" listings that can take money for withdrawn or missing content.

## What success means here

The doctrine's definition stands: FIRST_SALE_VERIFIED, then repeat sales without refunds. No
revenue figure is promised in this plan; each step above is chosen because it is what currently
stops a sale from being possible to observe.
