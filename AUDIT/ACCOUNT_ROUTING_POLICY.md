# Galaxy Forge — Account Routing & Payment Identity Policy

**Date:** 2026-08-09 | Mode: Implementation + verification. No accounts registered, no existing accounts changed, no credentials requested/exposed, no external transaction performed. This document records the real, authoritative account-routing configuration built this round (`account_routing.py`), its wiring into Mission Control, its test coverage, and its current honest status.

---

## Authoritative Account Map

| Identity | Value | Used for |
|---|---|---|
| **Primary commercial identity** | `galaxyaek7@gmail.com` | Gumroad, affiliate platforms, commercial platforms other than Amazon/KDP, digital-product marketplaces |
| **Amazon/KDP identity** | `aekgalaxy47@gmail.com` | Amazon, Amazon KDP, Amazon-related publishing/account operations only |
| **Payoneer identity** | `aekgalaxy47@gmail.com` | Payoneer, Amazon/KDP payout infrastructure, and only any future platform the founder explicitly confirms uses this account |

This is a real, disclosed update to this factory's own governance record: `OpenClaw_Brain/00_Governance/IDENTITY_ARCHITECTURE.md` (2026-07-11, ADR-014/ADR-015) previously stated "no documented exception to date" to a single-account model for every tool and platform. A cross-reference note was added to that document's §1 (this round) acknowledging the real, founder-disclosed Amazon/KDP + Payoneer exception, without altering that document's own, still-accurate, separate finding about infrastructure tools (GitHub, Groq, Anthropic, n8n-as-automation-tool), which remain unchanged on the single `galaxyaek7@gmail.com` account.

---

## What Was Built

**New module, `account_routing.py`** (repo root, matching the flat-module convention every sibling engine uses): a pure, side-effect-free, authoritative platform → commercial_identity → payout_identity → status lookup table.

- `route_platform(platform_id)` — returns the real routing record for one platform, or an honest `BLOCKED` record for any platform not explicitly classified. No fuzzy or substring matching exists anywhere — a platform whose name merely contains "amazon" is not routed to the Amazon identity unless it is explicitly listed.
- `account_routing_table()` — the full table, used identically by both the Mission Control panel and this audit document (never recomputed differently in two places).
- Zero imports capable of network, subprocess, or file I/O — proven structurally (a real AST-based test, not just an absence-of-a-call-site observation), so this module cannot register an account, connect a payment method, or trigger any transaction by construction, not merely by convention.

**Mission Control wiring** (read-only):
- `mission_control_api.py::_account_routing_status()` — thin wrapper, registered in `_ENDPOINTS["account_routing_status"]`.
- `server.js` — new `account-routing-status` `SERVICE_REGISTRY` entry, same pattern as every sibling read-only panel.
- **Live-verified this round**: a real temporary server instance (port 3106, PID-verified before and after termination) confirmed `GET /api/v1/services/account-routing-status` correctly returns **401 unauthenticated** — this panel is exposed only inside Mission Control, never publicly, matching the directive's own "never expose internal infrastructure to customers" rule.
- **Live-verified this round**: the underlying dispatch (`mission_control_api._ENDPOINTS["account_routing_status"]()`) was called directly and returns the correct real routing table.

**Tests, `tests/test_account_routing.py`** (21 tests, all passing, re-run this round): covers all 8 requirements the directive named explicitly (see Test Coverage below).

**Governance cross-reference**: `IDENTITY_ARCHITECTURE.md` §1 updated with a short, honest correction note (not a rewrite — the document's own separate infrastructure-tool finding is untouched).

---

## Platforms Currently Mapped

| Category | Platforms | Commercial identity | Payout | Status |
|---|---|---|---|---|
| **amazon_kdp** | `amazon`, `amazon_kdp`, `kdp`, `amazon_associates`, `CO-amazon-affiliate` | `aekgalaxy47@gmail.com` | `aekgalaxy47@gmail.com` (Payoneer) | **VERIFIED** |
| **non_amazon_commercial** | `gumroad`, `paddle`, `etsy`, `creative_market`, `envato`, `adobe`, `google`, `canva`, `zapier`, `n8n` (and their real `CO-*` opportunity IDs), plus `nordvpn`, `nordpass`, `kinsta`, `systeme_io`, `hubspot`, `cloudways`, `pipedrive` | `galaxyaek7@gmail.com` | UNKNOWN (never assumed) | **UNKNOWN** |
| **payment_infrastructure** | `payoneer` | N/A | `aekgalaxy47@gmail.com` | **VERIFIED** |

Live-computed this round via `account_routing_table()`: **34 total explicitly-classified platform identifiers**, of which the `amazon_kdp` and `payment_infrastructure` categories are fully `VERIFIED` and every `non_amazon_commercial` entry is honestly `UNKNOWN` on the payout dimension — exactly matching the founder's own explicit instruction not to assume Payoneer or any payout method for non-Amazon platforms.

## Platforms Still UNKNOWN / Not Yet Classified

Any real platform this factory might discover in the future (via Golden Hunter or otherwise) that is **not** in the three lists above is honestly `BLOCKED` by `route_platform()` — never silently assigned an identity. This is the intended, safe default, not a gap to close: per the directive's own design principle, a new platform must be explicitly added by a human following explicit founder instruction, never inferred from opportunity data.

## Conflicts Detected

**None.** No platform appears in more than one category, no platform's classification contradicts the founder's stated policy, and the live re-check of `commission_engine.py`'s real 13-opportunity portfolio confirmed every one of its real `CO-*` opportunity IDs maps to exactly the identity the policy specifies (Amazon → `aekgalaxy47@gmail.com`, all 12 others → `galaxyaek7@gmail.com`).

---

## Test Coverage (all 8 directive requirements, 21 tests, all passing)

1. Amazon routes to `aekgalaxy47@gmail.com` — `TestAmazonKdpRouting` (3 tests).
2. KDP routes to `aekgalaxy47@gmail.com` — same class.
3. Payoneer routes to `aekgalaxy47@gmail.com` — `TestPayoneerRouting` (2 tests).
4. Gumroad routes to `galaxyaek7@gmail.com` — `TestGumroadRouting` (2 tests).
5. Generic non-Amazon commercial platforms default to `galaxyaek7@gmail.com` **only** where explicitly classified — `TestNonAmazonDefaultOnlyWhenExplicit` (3 tests), including a direct proof that a platform string merely *containing* "amazon" is **not** inferred into the Amazon identity.
6. Unknown/conflicting platforms are blocked rather than guessed — `TestUnknownPlatformsAreBlockedNotGuessed` (3 tests).
7. No secret values are persisted or logged — `TestNoSecretsPersistedOrLogged` (3 tests), including a precise runtime check that every module-level string constant is either a real email or a known non-secret status label (not a naive text scan, which produced one real false positive on the module's own docstring during this round's own test-writing — caught and fixed before being reported here).
8. Account routing cannot trigger outreach or financial transactions — `TestCannotTriggerExternalActions` (3 tests): a real AST-based check that the module imports nothing capable of network/subprocess/file I/O, a check that no function name reads as action-triggering, and a purity/repeatability check.

---

## No Credentials, No External Actions

Confirmed, this round: no account was registered, no existing account was modified, no credential was requested or exposed anywhere in this module, its tests, its Mission Control wiring, or this document. `account_routing.py` holds exactly three non-secret email-address constants (already disclosed by the founder in this same conversation) and a static classification table — nothing else.

---

## What Was Already Present

Nothing. Confirmed by direct search before writing any code: no existing module, configuration file, or documentation anywhere in this factory previously modeled account-identity routing for commercial platforms. `IDENTITY_ARCHITECTURE.md` (2026-07-11) covered infrastructure-tool identity only, and explicitly stated no exception existed at that time.

## What Remains UNKNOWN

- The real payout method for every `non_amazon_commercial` platform (Gumroad, Paddle, Etsy, and the rest) — genuinely unverified, per the founder's own explicit instruction not to assume Payoneer.
- Whether any platform outside the three explicit lists above should exist in this policy at all — deliberately left `BLOCKED` rather than guessed.
- Deeper wiring of this routing table into the *internal decision logic* of the other 7 named consumer systems (Opportunity Engine, Affiliate/Commission Engine, Revenue Ledger, Commercial Flight Control, Publishing/Platform adapters, Payment-readiness checks, other Audit/Compliance reports) — this round built the authoritative source of truth and its Mission Control visibility, per the directive's own explicit sequencing ("First implement/verify the routing policy, tests, and read-only visibility"). None of those 7 systems' own code was modified to actively *call* `account_routing.py` yet — a disclosed, deliberate scope boundary, not an oversight, consistent with this session's established discipline of not rewriting multiple live systems under one directive without being asked to.

---

## FINAL OUTPUT

- **What was changed**: new `account_routing.py`; new `tests/test_account_routing.py` (21 tests); new Mission Control panel (`account-routing-status`, read-only, 401-gated, live-verified); one cross-reference correction note added to `IDENTITY_ARCHITECTURE.md` §1; this audit document.
- **What was already present**: nothing — this is genuinely new configuration and code.
- **What remains UNKNOWN**: real payout methods for every non-Amazon platform; any platform not yet explicitly classified; deeper integration into the other 7 named consumer systems' own decision logic (deliberately deferred, disclosed above).
- **Commit hash**: recorded below once committed.

---

## HARD STOP

No affiliate registration started. No payment credentials connected. No platform accounts changed. No outreach sent. Nothing published externally.
