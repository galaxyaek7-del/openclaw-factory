# Affiliate intelligence mandate — checkpoint 1 (2026-10-22)

Overall status: **PARTIAL**. Verified affiliate revenue: **$0** (no click,
conversion, commission or payout evidence exists).

## Stage 1 — what already exists (OBSERVED)

| Layer | Source of truth | Note |
|---|---|---|
| Program registry | `data/commission_opportunities.jsonl` (17 rows), written only by `affiliate_discovery.merge_newly_verified_programs` | Read model: `affiliate/registry.py` |
| Partnership pipeline | `data/partnership_pipeline.jsonl` (5 rows) | 3 leads (baremetrics, hostaway, lemsubs) not in the registry |
| Links | `data/affiliate_links.jsonl` (1 row: systeme.io, `owned-pending`) | |
| Economics ranking | `affiliate/priority.py`, `commission_engine.py` | |
| Algeria payout overlay | `affiliate/portfolio.py` (parallel session, **untracked**, 1,558 lines, 32-row register) | Overlaps the new matrix below; see Reconciliation |
| Ledger guards | `affiliate/ledger_firewall.py`, `affiliate_guard.py` | |

There was no 24-workstream list anywhere in the repo, so the mandate's list is used as the original mapping.

## Defects found and fixed

| # | Defect | Evidence | Fix |
|---|---|---|---|
| D1 | `registry.program_record()` read `geographic_restrictions` / `payout_threshold` / `payout_method`; the data uses `geography` / `payout_minimum` / `payout_methods`, so every program showed UNKNOWN for these | Reproduced in `TestDefectFixes` | Falls back to the stored names |
| D2 | `priority.score_program()` gave full "geographic fit" for any text containing "global" **or "algeria"**, including "PayPal receiving in Algeria is conditional". Masked by D1 until now | Same test | Full points only with an eligibility-matrix verdict; "global" earns 3 points, marked INFERRED |
| D3 | systeme.io is absent from the registry, yet `SYSTEME_AFFILIATE_ID` is configured and the site links to it | `.env` key present (value not read); `data/affiliate_links.jsonl` | Verified record prepared (`affiliate_discovery.SYSTEME_PROGRAM`). **Not merged**: it duplicates a row in the parallel `portfolio.py`. Merged, then reverted within the minute; correction appended to `data/affiliate_discovery_log.jsonl` |

## New (tested, read-only)

- `affiliate/eligibility_matrix.py`: separate eligibility and payout states per program, with Algeria evidence from `data/affiliate_algeria_evidence.json`.
- `affiliate/opportunity_rank.py`: score = economics × eligibility factor × payout factor + account bonus. Every component is exposed, and unknowns are penalised.
- `affiliate/workstreams.py`: WS-01 … WS-24, derived live from the registry.
- `tests/test_affiliate_workstreams_eligibility.py`: 14 tests.

## Current state (VERIFIED from these modules, 17:26 UTC)

- **Eligibility:** 4 programs have eligibility evidence (AWeber, n8n, Brevo, SiteGround, all "no country restriction stated"); 13 are UNKNOWN.
- **Payout:** 0 verified, 4 conditional (all via PayPal, whose Algeria receiving is conditional), 13 unverified.
- **Workstreams:** 7 PAYOUT_HOLD, 5 VERIFYING, 12 NO_CANDIDATE (no program in the registry for that buyer problem).
- **Ranking:** AWeber 46.9, n8n 44.1, Brevo 39.9, SiteGround 39.9, then DigitalOcean 13.1. DigitalOcean has the best economics (82) but unknown Algeria eligibility.

## Best current candidate (INFERRED, needs the founder)

**systeme.io**, which is not ranked only because of D3:

- **Account:** an affiliate ID is already configured, and the program has no application step ("Anyone can join").
- **Terms:** 60% lifetime recurring, lifetime cookie, $30 minimum, paid monthly on the 10th (official page, 2026-10-22).
- **Payout:**
  - PayPal works from Algeria only conditionally.
  - Wire needs an IBAN and an 11-character SWIFT, and is only available after the first sale. Algerian banks use a RIB, so this is unverified.

Under the same formula it would score roughly economics × 1.0 × 0.7 + 10, which puts it first. This is ESTIMATED; it is not computed until the merge happens.

## Blocked on the founder (not done, by rule)

1. **Payout route:** confirm a working way to receive the money in Algeria (a PayPal account that can withdraw, or a bank that accepts systeme.io's IBAN/SWIFT form). Without it, no program can reach PAYOUT_VERIFIED.
2. **Account standing:** confirm that the systeme.io affiliate account is active. The ID rotation flagged earlier is still open.
3. **Reconciliation:** decide whether `affiliate/portfolio.py` (parallel) or the new matrix becomes the Algeria model, and whether systeme.io moves into the main registry.
4. Any application, terms acceptance, publication or outreach.

## Next safe action

Read the systeme.io affiliate agreement (`https://systeme.io/affiliate-agreement`) to capture prohibited methods and disclosure rules. Then prepare one WS-02/WS-18 guide locally, using the existing `affiliate/content_qa.py` checks. Do not publish it.

## Tests (2026-10-22)

- **New tests:** 14 passed.
- **Affiliate suite** (47 files that touch the registry or affiliate modules): 599 passed, 6 failed.
- **The 6 failures:**
  - 2 were mine. The registry addition duplicated a row in `portfolio.py`; I fixed this by reverting the addition, and those tests now pass (22/22).
  - 4 come from elsewhere:
    - `test_alert_path` always fails, because its own source contains the word it bans.
    - `test_ledger_firewall` depends on a time window that has expired.
    - `test_phase4_integration` checks a `server.js` hash, and the parallel session has uncommitted edits to `server.js`.
    - `test_prospecting` needs an MCP endpoint that is not running.
