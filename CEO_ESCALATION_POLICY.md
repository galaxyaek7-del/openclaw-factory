# Galaxy Forge — CEO Escalation Policy

**Date:** 2026-08-08 | ADR-209, Phase 19, Section 25. Real citation over already-wired Telegram alerting — no new notification infrastructure built.

---

## What already, really escalates to the founder today

| Trigger | Real mechanism |
|---|---|
| Critical/emergency resilience finding | `newIncidentTelegramReasons()` + `telegramDirect.sendTelegramMessage()` (this session's "Real operational fix" entry) — every tick, deduped |
| Paddle checkout-ready state flip | `maybeNotifyPaddleCheckoutReady()` (this session) — every tick |
| Real crash-loop (too many restarts) | `scripts/supervisor.js`'s real Telegram alert |
| Evolution proposal awaiting approval | Surfaced in `founder_console.py`'s real pending-decision count, read on demand (not push) |

## Real, disclosed gap against Section 25's full named list

Not all 9 named trigger categories have a real, automatic push notification today. Confirmed:

| Named trigger | Status |
|---|---|
| Critical security events | Partial — `resilience_monitor.py`'s security-area findings push; a dedicated "security incident" category does not exist separately |
| Major financial discrepancy | **Not automatically pushed** — `contradiction_engine.py`'s price-contradiction check is real but on-demand (Mission Control panel), not tick-wired to Telegram |
| Customer trust incident | **Not automatically pushed** — `trust_audit.py` is real but on-demand |
| Unauthorized action attempt | N/A — no code path in this factory can attempt an unauthorized action to begin with (see `ACTION_AUTHORIZATION_ENGINE.md`) |
| P0/P1 failure | Covered via the critical/emergency resilience path |
| Major platform shutdown | Covered via the critical/emergency resilience path (a platform-area finding) |
| Legal/compliance concern | **Not automatically pushed** — `executive_quality_gate.py`'s checks are real but run per-generation, not tick-aggregated to Telegram |
| Large irreversible decision | Covered — every Level 5/6 action requires a real, human-initiated approval to begin with, so there is nothing to "catch" after the fact |
| Unexpected catastrophic behavior | Covered via the crash-loop/resilience paths |

## Deliberately not built this round

Wiring the 3 remaining real, on-demand checks (financial discrepancy, customer trust, legal/compliance) into the automatic tick would mean 3 more real Telegram-triggering code paths added inside an already-large round — a real, safe, well-scoped follow-up, not attempted here to avoid retrofitting `factory_loop.js`'s tested tick sequence 3 more times in one pass.

**"Do not overwhelm the CEO with low-priority notifications"**: already honored — every real push today is deduped (an already-open incident is never re-pushed) and gated to critical/emergency severity only.

---

*See also: `AUTONOMOUS_INCIDENT_RESPONSE.md`.*
