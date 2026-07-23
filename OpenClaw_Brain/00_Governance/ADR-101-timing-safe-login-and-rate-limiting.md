# ADR-101 — Timing-Safe Login Comparison + Rate Limiting

**Date:** 2026-07-23
**Status:** Adopted. Closes Security Mission Tracker finding 2.3 (Low).

---

## The finding

"Mission Control password check is not timing-safe; no brute-force/rate-limit protection on login" — `POST /api/mission-control/login` compared the submitted password with a plain `!==`, and nothing bounded repeated login attempts at all.

## What was built

`server.js`'s login route now:
- Compares the password with `timingSafeEqualStrings()` — the exact same helper `requireMissionControlOrInternalToken()` already uses for the internal-token comparison (ADR from finding 2.1), reused rather than reimplemented.
- Enforces a real, in-memory rate limit: `MISSION_CONTROL_LOGIN_MAX_ATTEMPTS` (default 5) failures within `MISSION_CONTROL_LOGIN_WINDOW_MS` (default 15 minutes) — both real, overridable env vars. The same bounded-sliding-window-of-real-timestamps pattern `scripts/supervisor.js`'s own crash-loop guard already established (ADR from finding 1.1), applied here rather than a new mechanism. A successful login resets the counter; the window is a real sliding window (pruned on every attempt), not a fixed calendar bucket.

**Deliberately global, not per-IP:** this factory is single-tenant (`BIND_HOST=127.0.0.1`, one real founder account, confirmed by `tests/test_api_contract.js`'s own "server binds to loopback only" test) — an IP-keyed limiter would add real complexity for a threat model this deployment doesn't actually have. Documented directly in the code so this choice isn't silently assumed later.

## Verification

New `tests/test_login_security.js` (5 tests, its own dedicated spawned server process — deliberately isolated from `tests/test_api_contract.js`'s shared instance so the real in-memory failure counter can be exhausted without polluting other tests): a correct password still succeeds (no regression from the timing-safe rewrite), a wrong-length password is still correctly rejected (a real edge case specific to `timingSafeEqualStrings()`'s equal-length requirement), the real limiter trips at exactly `MAX_ATTEMPTS` failures and returns 429 even for the correct password, the real window genuinely expires and access is restored, and a real success genuinely resets the counter (a stale residual count from an earlier test in the same file was found and fixed mid-build — the fix itself is correct, the first draft of the test just didn't reset shared state between cases).

Full regression: `tests/test_api_contract.js` + `tests/test_login_security.js` together (28/28), full JS suite (272/272 real tests, up from 267).

## What's next

Per the Security Mission Tracker's own stated order: 2.11 (server-side logout revocation) and 2.12 (CSRF token) remain — both Low severity.
