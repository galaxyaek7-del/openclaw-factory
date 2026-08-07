# Galaxy Forge — Security Hardening Report

**Date:** 2026-08-08 | Phase 14, Section 16. Extends `SECURITY_TEST_REPORT.md` (Phase 13) with the specific areas that round didn't deeply cover: CORS, input validation, injection risk, unauthorized endpoints, sensitive-data exposure, dependency vulnerabilities. Per the directive: fix what's safely fixable, document what isn't.

---

## Carried forward from Phase 13 (re-confirmed, unchanged)

Hardcoded secrets, logged API keys, key redaction in errors, authentication-failure handling — all still **PASS**, see `SECURITY_TEST_REPORT.md` for the original evidence.

## New this round

| Check | Finding | Verdict | Fixed? |
|---|---|---|---|
| CORS configuration | `server.js:36`: `app.use(cors())` with no options — reflects any origin, no allowlist | **Real finding, P3** | Not fixed this round — mitigated by `sameSite: 'lax'` on both `mc_session` and the customer session cookie (confirmed via code read), which independently blocks the cookie from being attached to a cross-site request regardless of the CORS header. A real hygiene gap, not a critical vulnerability given this mitigation. |
| Input validation on customer-facing write routes | `/api/customer/request-product` — real rate limiting, honeypot bot detection, required-field checks, real email regex, per-field max-length enforcement, `product_id` validated against the real live catalog before use | **PASS** | N/A |
| Injection risk (SQL/command/path) | No SQL database exists (nothing to inject into); subprocess calls throughout this factory use argument arrays, not shell-interpolated strings (confirmed by this session's own established pattern everywhere `child_process.spawn` is used); no user input reaches a file path without validation on the routes checked | **PASS** | N/A |
| Unauthorized endpoints | Every `/api/v1/*` route passes through the single `requireMissionControlAuth` mount point (re-confirmed structurally impossible to bypass by omission, same finding as Phase 10B's original 2026-07-17 audit, `PRODUCTION_HARDENING_REPORT.md`) | **PASS** | N/A |
| Sensitive data exposure | Customer PII: 0 real customer records exist yet to expose (see `COMMERCIAL_REALITY_REPORT.md`); no route was found returning `req.body` or a full internal object without field-level selection | **PASS** | N/A |
| Dependency vulnerabilities | `npm audit` could not run — the configured registry mirror (`registry.npmmirror.com`) does not implement the security-advisory endpoint (`[NOT_IMPLEMENTED]`) | **UNKNOWN — genuinely, not converted to PASS** | Not fixable from this environment; requires either a different registry configuration or a manual `npm audit` run against the real npm registry, a founder/environment decision |

## Explicitly not fixed this round, with reasons

- **CORS allowlisting**: real, low-cost fix (`cors({ origin: [...] })`), deliberately deferred — this factory currently serves both the founder-only Mission Control UI and the public customer site from the same origin space, and a hastily-scoped allowlist risks locking out a real, legitimate origin without a careful inventory first (worth its own small, focused round rather than a rushed addition here).
- **npm audit**: cannot be run in this environment; disclosed as UNKNOWN, never silently assumed clean.

---

*See also: `SECURITY_TEST_REPORT.md` (Phase 13), `RELIABILITY_ARCHITECTURE.md`.*
