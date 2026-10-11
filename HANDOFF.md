# HANDOFF — Galaxy Forge commercial ops (2026-10-11, post-C88)

## C88 OUTCOME
- **Content loop stopped.** No new Telegraph/Nostr volume beyond ONE
  hypothesis-driven article. No new products.
- **Hero offer verified end-to-end:** $59 Diminished Value Claim Kit.
- **New professional covers built and ready** (upload is the only blocker).
- **Reddit = hard boundary.** Not bypassed. Buyer questions found anyway via
  public web search.
- Orders 0 | revenue $0 | spend $0. CI 30/30. `cf2da83` + `1346b9e` pushed.

## THE ONE FOUNDER ACTION THAT MATTERS MOST
**Upload 3 cover images in the Gumroad dashboard.** Everything else is ready:
| File | Product | URL |
|---|---|---|
| `books/covers/diminished_value_claim_kit_cover_v2.png` | Diminished Value $59 | `/l/dyjavs` |
| `books/covers/gcc_contractor_payment_cover_v2.png` | GCC Contractor $399 | `/l/uwyfje` |
| `books/covers/verified_b2b_leads_cover_v2.png` | B2B Lead Lists $99 | `/l/drtaj` |

Steps: open the product -> Cover -> upload the PNG -> Save. That is all.
**Why:** 74 of 75 listings currently serve Gumroad's generic placeholder
(`assets.gumroad.com/images/opengraph_image.png`). This is the single largest
remaining conversion drag and it is NOT API-fixable — probed, all 404.

## ALSO STILL FOUNDER-ONLY
- `$155 EU AI Act Toolkit` (`/l/iaiyt`) — attach the PDF (mitigated, still live).
- `$1 "API TEST - DO NOT BUY - DELETE ME"` (`/l/dxfwlu`) — unpublish/delete.
- A Reddit account. Reddit returns 403 on `www` and serves a **login wall** on
  `old.reddit.com` (HTTP 200 but no data). This is where the target buyer for
  the hero offer demonstrably asks their question.

## C88 EXPERIMENT (window closes 2026-10-18)
`data/c88_experiment_baseline.json`, id `C88-DV-001`.
- Hypothesis: a DV claimant cannot judge the carrier's offer without their own figure.
- Telegraph article (grounded in NAIC's own 2023 Journal of Insurance Regulation):
  https://telegra.ph/Repaired-Your-Car-Before-You-Accept-the-Carriers-Diminished-Value-Offer-Work-Out-What-to-Ask-For-Free-10-11
- Storefront hero card, `utm_campaign=dv-hero-1011` (live, verified).
- Baseline at open: orders 0, revenue $0, article views **0**.
- Success = >=1 completed order or >=1 qualified inquiry.

## LIVE BUYER QUESTIONS FOUND (for the founder's Reddit account)
All asking "what number is fair / how do I push back":
- r/Insurance `1vyb4s0` — "How does this process work and what can I expect?"
- r/InsuranceClaims `1ukopa3` — "Progressive offered $350 — is that fair?"
- r/InsuranceClaims `1v3sw30` — 17c gave $732, counter at $1465, "any advice?"
- r/Insurance `1vonv4c` — "Is it worth proceeding?" (minor damage, <$3,000)

## HARD FACTS TO CARRY FORWARD
- Gumroad API: `description`/`name`/`price` persist (verify by re-read).
  `published` is silently filtered. **No binary upload endpoint exists.**
- Telegraph: pace requests (~1.4s) or you get false `PAGE_NOT_FOUND`.
- Nostr: writes accepted (`["OK",id,true]`), reads return 0 for us even on an
  unfiltered control — impressions/replies are UNKNOWN, never zero.
- Reddit: 403 / login wall. Do not attempt to circumvent.

---

# HANDOFF — Galaxy Forge commercial ops (2026-10-11, post-C87)

## C87 IN ONE LINE
Focused on ONE wedge (**$59 DTC Returns Abuse Playbook** -> small DTC/ecommerce
operators), published 3 distinct Nostr actions to that single buyer, and stopped
adding catalog breadth. Orders 0, revenue $0, spend $0. CI 30/30, `2494f02` pushed.

## CHANNEL REALITY MAP (measured, don't re-derive)
| Channel | Write | Read | Note |
|---|---|---|---|
| **Nostr** | **ACCEPTED** (`["OK",id,true]`) | **BLOCKED** | every REQ shape returns 0 events incl. an unfiltered control |
| Gumroad listing copy | accepted (verified by re-read) | yes | `published` field is filtered; covers upload not scriptable |
| Telegraph | accepted | yes (paced!) | unpaced loops = false `PAGE_NOT_FOUND`; ~2 views/page |
| Storefront (GH Pages) | accepted | yes | CI + Pages deploy ~2-4 min |
| Reddit | n/a | **403** | blocked; do not attempt to bypass |
| Stack Exchange | n/a | **400** | no account, no posting surface |

**Only owned channels can publish.** Impressions/replies on Nostr are **UNKNOWN**,
never "zero" - the read path is blocked to us, so absence of data is not absence
of audience.

## NEW DEFECT (C87) — FOUNDER ACTION
**74 of 75 listings have NO cover image.** Buyer-facing `/l/mrecoe` serves
`og:image=assets.gumroad.com/images/opengraph_image.png` (generic placeholder).
Only the $155 EU AI Act toolkit has 3 covers. This is a trust/conversion drag on
the entire catalog and needs a dashboard upload - the same class of blocker as the
$155 missing PDF.

## STILL BLOCKED ON FOUNDER (dashboard, ~5 min total)
1. `$155 EU AI Act Toolkit` (`/l/iaiyt`) - attach `books/eu_ai_act_compliance_toolkit.pdf`.
2. `$1 "API TEST - DO NOT BUY - DELETE ME"` (`/l/dxfwlu`) - unpublish/delete.
3. **NEW: cover images for the 74 coverless listings** (start with the $59 wedge).
API cannot set `published`; `covers` accepts writes but no upload path exists.

## C87 EXPERIMENT (window closes 2026-10-18)
`data/c87_experiment_baseline.json`. 4 channels live: 3 Nostr actions + 1 Telegraph.
UTMs: `nostr-returns-1011`, `nostr-returns-cost-1011`, `returns-abuse-1011`.
Success criterion: **>=1 completed order OR >=1 qualified buyer reply**.
Baseline: orders 0, revenue $0, replies 0.
Note IDs: `nostr:n1ux8fzz...`, `nostr:n19gl03h...`, `nostr:n17pwx2g...`

## WHAT TO DO NEXT (evidence-led, not a checklist)
1. Re-poll `/v2/sales` + the 3 note IDs at the next cycle. First non-zero wins.
2. Do NOT publish more articles - Telegraph is saturated at ~2 views/page
   (57 articles -> 142 views -> 0 sales). Volume is not the constraint.
3. The real constraint is audience reach on a channel that allows anonymous
   posting. Reddit is the obvious candidate and is 403 to us. **Founder action:
   a Reddit account** is the single highest-leverage unblock.

---

# HANDOFF — Galaxy Forge commercial ops (2026-10-11, post-C86)

## C86 OUTCOME
- **Buyer protection done for both hazards** (neither fully resolvable via API — see below).
- **Storefront repaired**: 53/75 -> **74/74 offers linked**, each new card with
  `utm_source=storefront&utm_medium=catalog&utm_campaign=<shortlink>`. All 71 gumroad
  links return 200. Live-verified: footer reads "74 products", 21 UTM links.
- **CI 30/30 green**, Pages deploy success, commit `363125a` pushed, 0/0 sync.
- Sales 0 | revenue $0 | spend $0.

## C86 CRITICAL CORRECTION TO C85
**C85's claim "the Gumroad token is read-only" was WRONG.** The token DOES write —
`PUT description` verifiably persists (verified by re-read: 2933 -> 3254 chars).
Only the `published` field is filtered and silently ignores writes.

Root cause of my own error: a verification used `desc.endswith(MARK)` against a
trailing-newline string, so a **successful** write was misread as a failed one.
That bug then left a `[GF-SELF-TEST-PROBE-1011]` marker live on a buyer-facing
Gumroad page. **It has been removed and verified gone.**
Lesson: verify writes by re-reading, and never trust a single fragile string check.

## STILL BLOCKED ON FOUNDER (2 dashboard actions, ~3 min each)
1. **$155 EU AI Act Toolkit** (`/l/iaiyt`, id `pzTmMb4v8cih3nbWTj5TeA==`) —
   attach `books/eu_ai_act_compliance_toolkit.pdf` (139,121 bytes, 31pp, SHA256
   `c22671a6...`). Verified good: valid PDF, matches every listing claim.
   Until then it is **still purchasable with no auto-download** — mitigated by a
   description banner (email for delivery + full refund) and a storefront warning,
   but the actual file needs a dashboard upload.
2. **$1 "GALAXY FORGE API TEST — DO NOT BUY — DELETE ME"** (`/l/dxfwlu`, id
   `20tVUV_UF9NOUf6aJ-GDRA==`) — still **live and publicly purchasable**. Cannot
   unpublish via API. Description now says it is not a real product + refund
   instruction. Founder should unpublish/delete it.

## MEASUREMENT (reconciled C86)
- **142 gross views / 56 pages** (paced `getPage`, jittered ~1.4s).
- C85's "137/53" and "127/57" were **not comparable** — 53 = local JSON records,
  57 = claimed articles, and gross was mixed with net. True gross over the 56
  known-live pages is 142. Own-fetch pollution ~10 (ESTIMATED).
- Unique visitors / outbound clicks / checkout starts = **UNKNOWN** (no backend).
- **Telegraph throttles**: unpaced loops return `PAGE_NOT_FOUND` for every page
  including verified-live ones. Always pace requests. Pages are never deleted.

---

# HANDOFF — Galaxy Forge commercial ops (2026-10-11, post-C85)

## RESOLVED THIS CYCLE (C85)
- **Telegraph auth: RECOVERED.** Token was never missing. It is NOT `TELEGRAPH_TOKEN`
  and NOT in `.env`/env scope. It lives in **gitignored `data/telegraph.json`**
  (`access_token`, 60 chars). `getAccountInfo` returns ok=true.
  The earlier "BLOCKED_AUTH" belief was a wrong-variable-name lookup.
  Correct call shape = **JSON body** (`Content-Type: application/json`).
  Form-encoded POSTs fail with `CONTENT_FORMAT_INVALID` — that was my own probe bug,
  not a service fault.
- **Network: healthy.** DNS/TLS/HTTP verified to api.telegra.ph, api.gumroad.com,
  api.github.com. The reported "Unable to connect" did NOT reproduce here; every
  endpoint answered (gumroad returned a clean 401 when unauthenticated = reachable).

## NEW DEFECT — FOUNDER ACTION REQUIRED (not fixable via API)
- `EU AI Act Compliance Toolkit` **$155** is PUBLISHED with `file_info: {}` —
  a buyer can pay $155 and download nothing. Deliverable exists locally:
  `books/eu_ai_act_compliance_toolkit.pdf` (139,121 bytes).
- Attempted `PUT published=false` (form **and** JSON). Both returned
  `success: true` but a re-read shows `published=True` — **Gumroad silently
  ignores the field via API.** It is the only no-file product of 75.
- Fix: founder attaches the PDF in the Gumroad dashboard (product id
  `pzTmMb4v8cih3nbWTj5TeA==`, url `https://aekraft.gumroad.com/l/iaiyt`).
  Until then it stays a live liability.

## PUBLISHED THIS CYCLE (all 3 fetched + content/CTA verified)
| campaign | offer | URL |
|---|---|---|
| eudr-1011 | $69 EUDR Due Diligence Starter | https://telegra.ph/EUDR-Deadline-Passed-Coffee-Cocoa-and-Wood-Shipments-Need-Different-Paperwork-Free-10-11 |
| section8-1011 | $59 Section 8 Notice Validity System (England) | https://telegra.ph/Section-8-Notice-Served-by-Email-Validity-Turns-on-Three-Things-Free-10-11 |
| leasacam-1011 | $59 Commercial Lease CAM & Operating-Expense Audit Kit | https://telegra.ph/Commercial-Lease-CAM-Charges-Look-Wrong-Audit-Them-Before-You-Pay-or-Dispute-Free-10-11 |

Each CTA carries `utm_source=telegraph&utm_medium=article&utm_campaign=<campaign>`.
Records: `data/telegraph_<campaign>.json`, `data/distro_1011_published.json`.

## LEFTOVER / HONEST CAVEATS
- Capability probe page **could not be deleted** (Telegraph `deletePage` ->
  `UNKNOWN_METHOD`). Still live, no offer inside:
  `https://telegra.ph/GF-Publishing-Capability-Probe-Temporary-10-11`.
  Founder can remove it manually. Do not claim it was cleaned up.
- Storefront `products.html` says "53 products"; Gumroad API has **75**.
  Count is stale (cosmetic, real).
- API pagination uses **`next_page_url` (relative)** — `?page=N` silently returns
  page 1 only. Always prefix `https://api.gumroad.com`.

## REAL STATE (live API, 2026-10-11)
- Products 75 | published 74 | no-file 1 (above)
- **Sales 0 | revenue $0 | spend $0** (`/v2/sales` empty, all `sales_count`=0)
- Telegraph: 53 pre-existing pages, **137 gross views**, ~10 own-loads
  (ESTIMATED) -> **~127 net external, ~2.4/page**. No page exceeds 8 views.
- Storefront live and public. Site visits: last recorded real view 2026-10-08.

## BIGGEST BLOCKER (measured, not assumed)
Distribution volume is NOT the bottleneck. 57 articles x ~127 net views with
**zero** sales means the funnel has never produced a buyer. Each new article
adds ~2 views. The gap is a reachable audience, not more articles.
Best free lever remains founder-side: attach the $155 file, and post the
First-Buyer-Free offer where real people already are (Nostr relay replies have
been checked repeatedly = 0; Reddit/GSC still founder-gated).

## Useful commands (no secrets printed)
- Sales: `python %TEMP%/opencode/gumcheck.py`
- Full product walk (paginates correctly): `sales_all_1011.py`
- Telegraph read: token from `data/telegraph.json`, JSON body, `getPage`/`getViews`

## Standing rules (unchanged)
- No fake buyers/reviews/sales; no spam; no scraping; $0 spend.
- Never print/export the Telegraph token; it stays in gitignored `data/telegraph.json`.
- No test-submits to lead forms. Never kill healthy workers.
- No new broadcast without a new variable + an observable counter.