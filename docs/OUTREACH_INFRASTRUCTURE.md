# Galaxy Forge — Lead Discovery & Outreach Infrastructure

**ADR-230, Phase 37A, 2026-08-08.** Operational reference for `lead_discovery.py` and `outreach_adapter.py`. See `AUDIT/PHASE_37A_LEAD_DISCOVERY_OUTREACH_REPORT.md` for the phase's executive status.

---

## Lead discovery source policy

Only real, public, keyless APIs are queried:

- **Hacker News** — HN Algolia story search, via `market_intelligence_engine.py::_query_hn_discussions()` (reused, not duplicated).
- **GitHub Issues** — GitHub Search API, via `market_intelligence_engine.py::_query_github_issues()`.

Both are the same real functions `analyze_customer_pain()` already uses for niche-level pain evidence — this module repurposes them one level down, from "does a pain signal exist" to "who publicly posted it."

**Never:** scraping, login/auth bypass, purchased or leaked data, private personal data, email harvesting. A `contact_channel` is always a public profile URL (`github.com/<login>` or `news.ycombinator.com/user?id=<author>`), never an email address.

## Lead qualification

`lead_discovery.qualify_lead()` computes a real, decomposable `LEAD_SCORE` (`N/5 real factors known`) with a `LEAD_SCORE_REASON` list — never an opaque number. A lead only `qualifies` when it has **all** of: a real problem-signal keyword match, fresh (`SUPPORTED`) evidence, and a real public contact channel. Evidence states: `VERIFIED, SUPPORTED, THIRD_PARTY_ONLY, STALE, CONFLICTING, UNKNOWN` — this module only ever assigns `SUPPORTED`/`STALE`/`UNKNOWN` (a single public post can never honestly earn `VERIFIED` or `CONFLICTING`, a disclosed, tested scope boundary).

## Outreach adapter

`outreach_adapter.OutreachAdapter` is the abstract interface (`validate_credentials`, `validate_destination`, `prepare_message`, `send`, `get_delivery_status`, `handle_bounce`, `handle_reply`, `handle_unsubscribe`). `SMTPOutreachAdapter` is the one concrete, real implementation — generic SMTP, provider-agnostic. See `outreach_adapter.CHANNEL_DOCUMENTATION` for the full Section 13 field set (channel, provider, method, auth, rate limit, delivery status, bounce handling, unsubscribe, retry policy).

## Credential setup

Real environment variables (none configured today — `CREDENTIAL_STATUS=MISSING`):

| Variable | Purpose |
|---|---|
| `OUTREACH_SMTP_HOST` | SMTP server hostname |
| `OUTREACH_SMTP_PORT` | SMTP port (defaults to 587/STARTTLS if unset) |
| `OUTREACH_SMTP_USERNAME` | SMTP AUTH username |
| `OUTREACH_SMTP_PASSWORD` | SMTP AUTH password |
| `OUTREACH_FROM_ADDRESS` | Real sending address |

Values are **never** logged, returned, or exposed anywhere — only presence/absence per field (`validate_credentials()`'s `CREDENTIAL_PRESENT`/`missing_fields`).

## CEO approval

A generic `CEO_APPROVAL=true` is **not sufficient**. `outreach_adapter.verify_exact_scope_approval()` requires an approval record with all 7 fields (`approved_lead_id`, `approved_opportunity_id`, `approved_partner_id`, `approved_channel`, `approved_message_hash`, `approval_timestamp`, `approval_scope`), every one matching the *specific* draft being sent — plus the underlying `autonomous_operations.py` Level 5 gate (`high_value_commercial_outreach`) must independently `ALLOW`. A message edited after approval fails the hash check automatically.

## Dry-run mode

`outreach_adapter.run_full_dry_run(opportunity, lead)` simulates the complete chain (discover → qualify → draft → approve → send → deliver → reply → unsubscribe → a failure case) using `mode="SIMULATION"` throughout. `REAL_OUTREACH`/`REAL_CUSTOMERS`/`REAL_DEALS`/`REAL_REVENUE`/`REAL_COMMISSION`/`REAL_PAYOUT` are structurally zero — no function in the dry run ever sets `mode="REAL"` or touches `commission_ledger.py`.

## Real-send activation

To ever enable a real send: (1) configure all 5 `OUTREACH_SMTP_*`/`OUTREACH_FROM_ADDRESS` variables with real values; (2) obtain a real, exact-scope-matched CEO approval record; (3) call `SMTPOutreachAdapter.send(draft, destination, mode="REAL")`. `MAX_REAL_SENDS=1` (`outreach_adapter.MAX_REAL_SENDS`) blocks any further real send until this constant is deliberately changed by a future, separately-approved directive.

## Failure handling

Every SMTP exception is classified via `_classify_smtp_failure()` (`INVALID_OR_EXPIRED_CREDENTIAL`, `NETWORK_FAILURE`, `INVALID_DESTINATION`, `PROVIDER_REJECTION`, `PROVIDER_TIMEOUT`, `ADAPTER_FAILURE` fallback) — never a silent generic catch, never a fabricated success, **zero automatic retries** (a failed send requires a new, separately-approved attempt).

## Audit events

`data/outreach_adapter_events.jsonl` (adapter-level: `SEND_ATTEMPT_RESULT`/`SEND_ATTEMPT_BLOCKED`/`SEND_SIMULATED`/`BOUNCE_RECEIVED`/`REPLY_RECEIVED`/`UNSUBSCRIBE_RECEIVED`), `data/lead_discovery_events.jsonl` (`LEAD_QUALIFIED`/`LEAD_REJECTED`/`DUPLICATE_LEAD`), `data/outreach_log.jsonl` (message-level `DRAFTED`/`APPROVED`/`REJECTED`, `outreach_engine.py`'s pre-existing ledger). All append-only, all real.
