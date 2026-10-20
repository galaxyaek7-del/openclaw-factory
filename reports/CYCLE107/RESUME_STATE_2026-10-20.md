# Resume State - Cycle 107

Date: 2026-10-20
Purpose: the next session should be able to continue without re-deriving what
was already verified, and without mistaking a plan for a result.

## Where the repository is

| Item | Value |
|---|---|
| Branch | `main` |
| HEAD | `2509aad` "Repair the discovery gate: reject before scoring" |
| Remote | `origin/main` = `2509aad` |
| Prior commits | `94c9bde` B13-001 fix, `a174268` affiliate verification, `b992cfd` gate at $15, `c0ca6dc` cycle verdict |
| Uncommitted parallel work | Present and untouched; do not stage it wholesale |

## What is true now

- B13-001 is locally ready at $15.00 and unauthorized. 416 formulas, Excel QA
  PASS, independent check 17/17, guide 15 pages with a disclaimer.
- The discovery gate rejects before scoring. Cycle 107 replays 3/3 rejected;
  EUDR fails only on the free-alternative advantage and evidence gates.
- One incident is recorded (`INC-454a108bcdd3`) with the intake tests as its
  preventive control.
- The affiliate asset renders to a gitignored file with a validated link and a
  reader-facing disclosure. It is not published and has no traffic.
- Real affiliate revenue is $0.00, with 0 REAL commission records and 29 clicks
  that carry no referrer or source.
- Safety flags are still off: `FACTORY_LIVE_PUBLISH=false`,
  `PRODUCTION_AUTHORIZED=false`, `AUTO_PUBLISH_MODE=DISABLED`.

## What is not true

- The test suite is not green. Known pre-existing failures are listed in the
  TODO closure register.
- "189 tests" and "23 technical checks" from earlier cycles are not
  reproducible and remain UNKNOWN.
- No affiliate conversion or commission has occurred.
- No B13-001 listing exists on Gumroad that this session can see.

## First three actions next session

1. Read `reports/CYCLE107/VERIFICATION_REPORT_2026-10-20.md` and run
   `python scripts/check_doctrine.py` before changing anything.
2. If the founder has answered FQ-01, follow the publication checklist for
   B13-001 at $15.00 and record the real result, including a failure.
3. If not, do not build more infrastructure. Start the zero-cost campaign
   experiment only after a publication destination exists; before that, the
   honest next step is the founder decision, not code.

## Traps that cost time last cycle

- PowerShell `Get-Content -Raw` / `Set-Content` round-trips corrupt UTF-8
  source (em dash and division sign became mojibake). Use the edit tool or
  `[System.IO.File]::WriteAllText` with a UTF-8 no-BOM encoding.
- `Set-Content -Encoding UTF8` adds a BOM. Strip it before `git commit -F`.
- `excel_recalc_probe.ps1` needs `-Root C:\openclaw-dasgboard`; its
  `$PSScriptRoot` default is empty under `-File`.
- Commit with `git -c core.autocrlf=false -c core.whitespace=cr-at-eol`, and
  verify with `git ls-remote`.
- Never print, log, or commit the systeme.io tracked URL. The renderer is the
  only path that writes it, and only into the ignored directory.

## Definition of done for this mission

`FIRST_SALE_VERIFIED`: one real sale, verified from the platform's own record,
with the amount and date recorded. Everything in this cycle is preparation for
that event. None of it is the event.
