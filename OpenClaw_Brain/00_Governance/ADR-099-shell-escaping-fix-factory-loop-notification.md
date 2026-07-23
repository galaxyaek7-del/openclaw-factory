# ADR-099 — Shell-Escaping Fix: factory_loop.js's sendDesktopNotification()

**Date:** 2026-07-23
**Status:** Adopted. Closes Security Mission Tracker finding 2.9 (Medium).

---

## The finding

"`factory_loop.js`'s `sendDesktopNotification()` has an incomplete shell-escaping boundary (escapes single quotes, embedded in a double-quoted PowerShell argument) — real defect, full exploit-chain not traced" (Phase 1 Security Audit).

The real defect, confirmed: `title`/`message` had their single quotes doubled for the *inner* PowerShell single-quoted string (`'${escapedTitle}'`), but that whole script was then concatenated into an *outer* double-quoted shell argument (`execSync(\`powershell -NoProfile -Command "${script}"\`)`). A literal `"` character in `title`/`message` was never escaped for that outer boundary — it would terminate the double-quoted `-Command` argument early, letting the remainder be reparsed as additional shell/PowerShell tokens. Both call sites pass externally-influenced text (`attentionReasons`, which can include Scout/Pioneer's Hacker-News-sourced niche titles, the same real class of input ADR-098's XSS fix addressed for `index.html`).

## What was tried, and what a real test found

The first fix attempt removed all string interpolation of untrusted data from the script text and passed `title`/`message` as trailing arguments to `powershell.exe -EncodedCommand <base64 script> title message`, with the script itself reading them via a `param()` block. This is a real, commonly-recommended pattern for exactly this problem — but a real test against a title containing a literal `"` character (`x" ; echo INJECTED ; "`) immediately failed with a genuine PowerShell parser error: *"Cannot process the command, because a command is already specified with -Command or -EncodedCommand."* PowerShell.exe's own trailing-argument handling after `-EncodedCommand` turned out to still reinterpret embedded quote characters in ways its own documentation doesn't fully specify — this was found, not assumed, before it shipped.

## The real fix

`sendDesktopNotification()` now writes a fixed, static PowerShell script (never containing `title`/`message`) to a real temp `.ps1` file, and invokes it via `execFileSync('powershell.exe', ['-NoProfile', '-NonInteractive', '-File', scriptPath, title, message], ...)`. PowerShell's own documented contract for `-File` is unambiguous: everything after the script path is a literal script parameter, bound to the script's own `param()` block, never re-parsed as PowerShell or shell syntax. `execFileSync` (not `execSync`) never spawns an intermediate shell to parse a command string at all. Verified directly: a title/message containing `"`, `` ` ``, `$(...)`, `;`, and `|` together reaches the script as inert literal text with zero execution — not assumed safe by construction, actually tested with a real marker-file check (see Verification).

The temp `.ps1` file is deleted in a `finally` block immediately after the (synchronous) PowerShell process exits — never left behind, verified directly.

## Verification

4 new tests in `tests/test_factory_loop_notification.js` (all running the real function on the real machine — a Windows toast notification can't be meaningfully mocked, matching this file's own pre-existing testing philosophy):
- A real injection attempt (`x" ; Add-Content -Path "<marker>" ...`) reaches the script as literal text; the marker file that would exist if the injection had actually executed is confirmed absent.
- A literal `"` alone in both title and message is handled cleanly.
- The real temp `.ps1` script is confirmed deleted after every call, never orphaned.
- (Plus the 3 pre-existing tests, unaffected, still passing.)

Full regression run: `tests/test_factory_loop_notification.js` (7/7), the 7 other real `factory_loop.js`-dependent test files (`test_factory_loop_daily_evolution_report.js`, `test_factory_loop_golden.js`, `test_factory_loop_lock.js`, `test_factory_loop_tick_overlap.js`, `test_factory_loop_weekly_executive_report.js`, `test_pending_review.js`, `test_process_pending_retries.js` — all green, no regressions from the new `os` import or the changed function), full JS suite (260/260 real tests, up from 249), full Python suite (1141/1141, unaffected — this is a pure Node-side fix).

## What's next

Per the Security Mission Tracker's own stated order: 2.8 (Windows ACL hardening on `.env`/`data/decisions.jsonl`/`finance_data.json`), 2.3 (timing-safe login + rate limiting), 2.11 (server-side logout revocation), 2.12 (CSRF token) remain — all Low/Medium severity, none yet started.
