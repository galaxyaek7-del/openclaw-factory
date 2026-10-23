# Distribution: repair log

| # | Defect | Found by | Fix | Proof |
|---|---|---|---|---|
| R1 | `x_post` declared 280 characters but did not enforce it: 4 of 92 live products produced posts up to 302 | measuring the real catalog | budget computed with X's 23-character link weight; sentence-bounded | all 92 within 280; regression test |
| R2 | LinkedIn copy always said "validation concept, not a launched product", false for 89 verified live listings | review | `Asset.status`/`url`; "live" listings show price and link | regression test |
| R3 | "while" treated as a pain marker produced hooks like "Stop payroll lands..." | review | marker removed (no test depended on it) | regression test |
| R4 | HTML lists collapsed into one run-on paragraph | review | `offers.plain()` keeps paragraphs and list items as lines | regression test |
| R5 | X text cut mid-word | review | `_fit_sentences()` keeps whole sentences | sample output |
| R6 | QA blocked honest copy: 24 listings' disclaimers ("No result is guaranteed") and worked-example amounts ("$1,000") | full QA tally | claim and amount checks apply only to text the templates added | tally; regression tests; mutation check |
| R7 | 9 product pages for products not on sale ("proposed", "not yet listed") were counted eligible: the engine would have advertised unavailable products | QA amount check on real drafts | b12 pages eligible only when matched to a verified live product; stale pages need review | regression test |
| R8 | Descriptions hard-cut at 1,200 characters ("rental_property_dea") | reading a real draft | no hard cut; LinkedIn uses whole lines with the title on top | sample output |
| R9 | Site titles carried "\| Galaxy Forge" | reading a real draft | stripped | regression test |
| R10 | Nested fields checked as `str(dict)`, hiding verbatim listing text | failing new test | fields flattened to their strings | regression test |
| R11 | Dashboard split QA reasons that themselves contain "; " | dashboard output | reasons stored as a list | regression test |
| R12 | Product pages matched to a live product had no price, so their price looked contradictory | QA tally | page offers carry the linked product's price and id | regression test |
| R13 | Engine change broke `product_launch_kit` (9 channels instead of its promised 8) | existing tests | the kit names its 8 channels explicitly | `test_product_launch_kit` OK |
| R14 | Ellipsis-cut listing text after the title not recognized | QA tally | longest listing-contained tail matched | regression test |
| R15 | Shell heredocs turned `\n` and `\b` into control characters in two edits | parse/grep check | rewritten with the editor and byte replacement | files parse; tests pass |
| R16 | (previous task) listing-copy residue test flagged base64 product ids in `data/listing_page_checks.json` | CI-equivalent run | file excluded by name with a reason | test passes; CI green |

Found and not fixed here (owned elsewhere): D-R1 to D-R4 in the risk register.
