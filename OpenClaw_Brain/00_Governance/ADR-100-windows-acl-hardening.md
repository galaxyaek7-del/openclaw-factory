# ADR-100 — Windows ACL Hardening on Sensitive Files

**Date:** 2026-07-23
**Status:** Adopted and **applied live** to the real files on this machine. Closes Security Mission Tracker finding 2.8 (Medium).

---

## The finding

`.env`/`data/decisions.jsonl`/`finance_data.json` carried permissive, inherited default Windows ACLs — readable by the built-in `Users` group, writable by `Authenticated Users`. Low real risk at the time (single enabled account on this machine, per CLAUDE.md's own Identity Architecture note) but no owner-only restriction existed.

## What was built

`scripts/harden_file_acls.js` (new, opt-in, explicit — nothing runs it automatically): disables ACL inheritance and grants Full control to only the real current user + SYSTEM + the built-in Administrators group, removing the broad `Users`/`Authenticated Users` grants entirely. Supports `--dry-run` (reports what would change without touching anything) and `--files` (target a custom list).

## Two real bugs found while building this — both would have caused a live outage or a silent partial-fix if shipped untested

1. **`whoami` resolves to a different binary depending on the invoking shell.** The real Windows `whoami.exe` returns `COMPUTERNAME\username` (the form `icacls` needs); Git Bash/MSYS2's own `whoami` on PATH returns a bare `username` with no domain prefix. A file "hardened" with the bare name silently ended up with a broken grant — read/write still worked, but `icacls`'s ACE for that malformed principal was unreliable and a real `fs.rmSync` delete failed with `EPERM` in testing. Fixed by reading `process.env.USERDOMAIN`/`USERNAME` directly instead of shelling out at all — real OS-level environment variables, identical regardless of which shell launched the process.
2. **This machine's Windows install is French-localized.** Hardcoding the English display names `"SYSTEM"`/`"Administrators"` failed outright with a real `icacls` error ("Le mappage entre les noms de compte et les ID de sécurité n'a pas été effectué" — "the mapping between account names and security IDs could not be done") the moment the fix was tested against a real file, because this machine's real built-in-group display names are `AUTORITE NT\Système`/`BUILTIN\Administrateurs`. Fixed with locale-independent well-known SIDs (`*S-1-5-18` for SYSTEM, `*S-1-5-32-544` for Administrators) — `icacls`'s own `*SID` syntax resolves them correctly on any language edition of Windows, confirmed directly against the real localized output.

Neither bug was found by inspection — both were found by actually running the tool against a real file and reading the real error, exactly the discipline this whole mission has followed throughout.

## Verification

7 tests in `tests/test_harden_file_acls.js`, every one against a real, throwaway temp file (never the real sensitive files) — missing-file handling, `--dry-run` genuinely making zero changes, a real broad-grant-removed check (locale-independent: counts 3 real principals with Full control rather than asserting on any English name), idempotency (running twice never throws), and a hard requirement that the file remains real-read/write-able by its own owner immediately after hardening (a fix that locks out its own owner would be worse than the finding it closes).

**Applied live, with explicit founder confirmation before running against real files** (this changes real filesystem security state on a live, running factory — outside what should ever happen without asking): dry-run first, confirmed all 3 files were still permissive; applied for real; then a live end-to-end check with the real server running — `GET /health` 200 (real `.env` read succeeded), `POST /api/mission-control/login` 200, `GET /finance` 200 (real `finance_data.json` read), `POST /finance/add` 200 (real `finance_data.json` write succeeded), and a direct shell read of `data/decisions.jsonl` confirmed still accessible. The one real side effect of this live check (a $1 test sale entry) was removed from `finance_data.json` and totals honestly recomputed immediately after.

Full JS suite: 267/267 real tests (up from 260).

## What's next

Per the Security Mission Tracker's own stated order: 2.3 (timing-safe login + rate limiting), 2.11 (server-side logout revocation), 2.12 (CSRF token) remain — all Low severity, none yet started.
