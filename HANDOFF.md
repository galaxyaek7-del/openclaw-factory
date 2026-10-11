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