# Galaxy Forge — Outreach Policy

**Date:** 2026-08-08 | ADR-226, Phase 33, Section 8. `outreach_engine.py`.

---

## Confirmed before any code was written

Zero outreach automation exists anywhere in this factory (confirmed by direct grep for email/SMS/CRM-send integrations — none found). This module builds the real, safe half of that gap.

## Default flow — structurally not bypassable

```
GENERATE (draft_outreach_message) -> HUMAN REVIEW (approve_outreach) -> SEND (send_outreach)
```

`send_outreach()` checks `state == "APPROVED"` as its first condition — a `DRAFT` or `REJECTED` message can never reach the send step, verified by test (`test_send_blocked_without_approval`, `test_rejected_draft_cannot_be_sent`).

## Approval requires a real identity

`approve_outreach()` refuses an anonymous approval (`approved_by=None`) — every real approval is attributable to a real person, verified by test.

## Sending is honestly blocked today

`send_outreach()` always returns one of two honest states: `BLOCKED_NO_CREDENTIAL` (no real outbound-send credential exists in `.env` — confirmed via scan, no `SENDGRID`/`TWILIO`/`SMTP`/`OUTREACH`-prefixed variable exists) or `BLOCKED_NO_SEND_ADAPTER` (even with a credential, no real email/SMS provider integration is wired). **No path in this codebase can produce a fabricated "sent" result** — verified by `test_never_fabricates_a_sent_result`.

## No uncontrolled mass outreach

There is no batch-send function anywhere in `outreach_engine.py` — every draft is approved individually. High-value-prospect CEO approval (directive's own explicit ask) is naturally enforced by the same single-approval-per-draft mechanism; no separate "bulk approve" path exists to bypass it.

## Audit trail

Every `DRAFTED`/`APPROVED`/`REJECTED`/`SEND_ATTEMPT_BLOCKED` event is appended to `data/outreach_log.jsonl`, queryable per-draft via `outreach_audit_trail()`.

## Unsubscribe / opt-out

Named as a real state (`OPTED_OUT` in `OUTREACH_STATES`) — no real opt-out has ever occurred (0 real outreach has ever been sent), so no handling code beyond the state's existence was built this round; would be exercised the moment real sending exists.

---

*See also: `COMMERCIAL/COMMISSION_COMMERCE.md`.*
