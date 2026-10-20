# The Two Ceilings That Hide a Price

## The mistake

For several cycles this factory carried a written "conflict" between a $19 price and a suggested $7, and
treated it as an unresolved disagreement between two systems or, at worst, as a gate defect to be worked
around. It was neither. `economics.evaluate()` returns two independent facts, and the conflict only existed
because they were read as one:

- `approved` — does the unit clear the platform's net-profit floor. For `gumroad_digital` that floor is
  $2.50; for `gumroad_premium` it is $25.00.
- `market_realistic` — does the price look credible for the amount of product. This is advisory. It never
  changes `approved`, and nothing refuses to publish on it.

The $7 was neither a rejection nor a rival verdict. It was `market_realism`'s *suggestion*, derived from a
page-based policy that cannot see a 9-sheet workbook and only counts PDF pages.

## The consequence

Two real costs, neither of them a wrong number in a report.

The first was decision paralysis. The price could not be settled because the two figures were treated as
contradicting each other, so the question stayed open across cycles while the product sat unlisted.

The second was worse, and only became visible when the policy was actually probed rather than reasoned about.
The page policy has **two** rules, not one: a per-page ceiling ($1/page on the digital tier, $5/page on
premium) *and* an absolute cap of $15 for anything under 30 pages. The second rule dominates, and it is not
proportional. Growing the guide from 7 pages to 15 changes nothing about whether $19 works, and growing it to
29 changes nothing either. The threshold is 30, and any effort spent below it is spent for no price benefit.

That meant the guide had been expanded for the wrong reason in earlier thinking: "more pages will help"
was true only in a step function nobody had read.

## How it was found

Not by reading the docs, which described the policy in prose. By calling the function with a matrix of prices
and page counts and writing the results down:

| price | pages | approved | realistic |
|---|---|---|---|
| $19 | 7 | yes | no |
| $19 | 15 | yes | no |
| $19 | 29 | yes | no |
| $19 | 30 | yes | yes |
| $15 | 15 | yes | yes |
| $16 | 16 | yes | no |

The last two rows are the ones that teach the rule. $15 at 15 pages passes; $16 at 16 pages fails. So the
binding constraint is the absolute cap, not the ratio.

## The fix

Not a code change. A decision was made executable instead of argued about. The guide was expanded from 7 to
15 pages and 8,237 gate-words with eleven substantive sections, which made **$15.00** clear both checks for
the first time. $19 was left flagged on purpose, with the reason stated: it needs 30 pages, and pretending
otherwise would be the exact dishonesty the price policy exists to prevent. $27.99 on premium remains the
other honest route.

Nothing was repriced without authorization, and every claim that quoted the old page count was corrected in
place: the listing copy, the payload matrix, the gate evidence, and dated addenda on the two reports that
described the earlier build state.

## The lesson

When two numbers appear to disagree, find out whether they are answers to the same question. In this factory
they were not: one was a floor, the other an advisory suggestion, and the "conflict" dissolved once each was
named. And when a policy uses a threshold, probe the threshold rather than assuming the relationship is
linear — a step at 30 pages makes 29 pages worth exactly nothing, and no amount of plausible reasoning about
"more content is better" would have revealed it. Two minutes of calling the function with a matrix beat days
of interpretation.
