# Cycle 103: integrity, containment and release manifest (2026-10-18)

Evidence classes: OBSERVED / DERIVED / INFERRED / UNKNOWN.
Completion states: PREPARED / LOCALLY VERIFIED / COMMITTED / PUSHED / DEPLOYED / EXTERNALLY VERIFIED.

## Release manifest

**Repository state (OBSERVED):**
- Branch `main`, remote `origin` = github.com/galaxyaek7-del/openclaw-factory.
- 10 commits ahead of `origin/main` and 0 behind. **Not pushed.**
- The "8 vs 7" discrepancy: the 8th was `d5ae032`, the Cycle 99 report itself, committed after it listed the other 7.
- This cycle added `883196f` and `7d93921`.

| Hash | Content | State |
|---|---|---|
| 3bffa02 | Reports only (parallel session) | COMMITTED |
| 641ee2d | products.html: 3 cards removed, unclosed card fixed; one stale link removed | COMMITTED |
| 19cb415 | n8n exposure audit, tests, review | COMMITTED |
| b0269c6 | Founder alerts: direct path first | COMMITTED |
| b9e7973 | Paddle retry budget; .gitignore for 2 rejected files | COMMITTED |
| 7f26b4d | healFinance re-check before reset | COMMITTED |
| 9f59ae6 | Paddle / sales-poll tests | COMMITTED |
| d5ae032 | Cycle 99 report | COMMITTED |
| 883196f | Site metadata audit tool; 3 live tag defects fixed | COMMITTED |
| 7d93921 | Ledger reconcile: no overwrite of an unreadable file; concurrent entries kept | COMMITTED |

**Contents checks:**
- 24 files changed; 4 of them under `customer_site/`.
- Secret scan: 0 hits.
- No `.env`, ledgers, finance or reality files, or customer records.
- `factory_loop.js` carries only these hunks. The parallel session's uncommitted edits stay unstaged: 77 lines in `factory_loop.js`, 55 modified site pages, 9 new draft pages.

**GitHub Pages:**
- OBSERVED: the live site serves `origin/main` (live `products.html` is byte-identical to it).
- DERIVED: a push would deploy 4 site files: `products.html`, `service-verified-lead-lists.html`, `eu-ai-act-compliance-toolkit.html`, `turo-guest-dispute-toolkit.html`.

## Public site: what is live today (OBSERVED)

- **Dead-end links:** `products.html` and `service-verified-lead-lists.html` link to `drtaj` ($99) and `lrmgml` ($327). The Gumroad API reports both as `published=False`, and their pages show no Buy button. Fixed in `641ee2d`, not deployed.
- **Wrong canonical:** `turo-guest-dispute-toolkit.html` has its canonical pointing at the Gumroad listing, which tells search engines to index Gumroad instead of our page. Fixed in `883196f`.
- **Empty tags:** `eu-ai-act-compliance-toolkit.html` has an empty canonical and an empty `og:url`. Fixed in `883196f`.
- **Duplicate OG tags:** origin/main has 113 duplicate OG tags across 66 pages. The uncommitted parallel-session edits remove all of them; they are not part of this release.
- **Sitemap gaps:** 10 indexable pages are absent from `sitemap.xml`: 9 new, untracked draft B12 pages and `affiliate-program.html`.
  - Recommendation: give the draft pages `noindex` rather than listing them.

**Reproduce:** `python scripts/site_metadata_audit.py --unlisted drtaj,lrmgml,owtmpe`

## Financial data integrity

**Fixed this cycle (`7d93921`):** `channels/ledger.py::reconcile_ledger_to_finance()` had two defects.
1. **Unreadable file overwritten.** When `finance_data.json` existed but could not be read or parsed, it started from an empty structure and wrote that over the real file. Manual `/finance/add` entries, which are not in the ledger and cannot be re-derived, would have been lost.
2. **Lost updates.** A `server.js` `saveFin()` write landing between its read and `os.replace()` was lost.

**The fix:**
- An unreadable or invalid file is reported, not written.
- The file is re-read just before the replace; if the bytes changed, the merge retries (3 attempts), then reports and leaves the file alone.
- There is no cross-language lock, so a very small window remains: the re-read and the replace are not atomic together (INFERRED, documented in code).
- 4 new tests; `test_ledger` passes 25/25.

**Other findings:**
- **The 11 failing `test_backup_*` tests** (untracked, parallel session) are **stale assumptions with an unsafe dependency on live data**. They pin sha256 values of the live `finance_data.json` / `sales_ledger.jsonl` / `reality.json`, which change normally (pinned `cd297d2f…`, current `2e0c0c6c…`). They read the live files and don't modify them. Not regressions.
- **The live files** were compared byte-for-byte before and after every test run: **unchanged**.

## Paddle (OBSERVED, one read-only request each)

- Cycle 99 saw Cloudflare 429s.
- Today, both `/transactions` and `/products` return **403 `forbidden`**: "You aren't permitted to perform this request."
- So the key is now refused, not rate-limited. Cause UNKNOWN: revoked or rotated key, a permission change, or the account state.
- The poll already reports Paddle's error without blocking Gumroad (`test_sales_poll`: a Gumroad sale is recorded during a Paddle failure).

## n8n demos: still exposed (HOLD)

- **OBSERVED again this cycle:** RE_Broker / Umrah_Agency / Dental_Clinic `_Assistant_Demo` return 200 from the internet through the tunnel. They are public, unauthenticated, and run a Groq model on the founder's credential, with memory and no tools.
- **Not contained:** no authorization has been given, and no n8n API key exists.

## B12-001

- **Workbook (OBSERVED):**
  - sha256 `aee8fc0b…092d` matches the packet;
  - no macros, no external links, `fullCalcOnLoad=1`;
  - 10 formulas;
  - the worked example reproduces: $104.60 / $120.29;
  - README steps match the sheets;
  - no mojibake.
  - INFERRED: viewers without a calculation engine (for example phone previews) may show blank results until the file is opened in Excel, LibreOffice or Sheets.
- **Price:** the directive says $29. The recorded founder decision (2026-10-17, `price_basis: FOUNDER_DECISION_BELOW_COMPARABLE`) is **$14.99**, and $29 is the *previous* price that decision replaced.
  - The market gate scores 70 / PASS at both prices; the only missing check is proof of payment.
  - $29 is above the closest direct comparable ($19, more content).
  - Every listing file and the site page use $14.99. **Not changed.**
- **Listing:**
  - OBSERVED: no Gumroad listing exists (read-only query).
  - The draft must be created manually (`reports/B12-001/DRAFT_NOW_CYCLE95.md`).
  - Copy, tags and measurement plan are consistent: no guarantees, no scarcity.

## Tests (OBSERVED, clean `git archive HEAD` extract)

- **Python, 8 CI groups: 5,247 tests.**
  - `test_audit_requirements` and `test_snapshot` need `.git`; they pass in the real repo.
  - `test_phase4_integration` pins an old `server.js` hash. It is pre-existing; this branch does not touch `server.js`.
- **JS: 460 pass across all CI groups, 1 failing test.**
  - `test_restore_file_from_git` needs `.git`; it passes 8/8 in the real repo.
  - `test_api_contract`, run alone: 32/33. One heavy endpoint misses its time budget, and which one varies between runs (`strategic-planning-dashboard` this time, `commercial-control-center` before). UNKNOWN whether CI sees the same.
  - An earlier run overlapped with a second copy of the same suite on port 3199 and timed out; that result is discarded. Its orphaned server (PID 4400, port 3199) was stopped by exact PID; production (PID 14608, port 3000) was not touched.
