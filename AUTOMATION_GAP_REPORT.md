# Galaxy Forge — Automation Gap Report

**Date:** 2026-08-07 | The real, current automation ceiling (Test Scenario 20, cross-referenced with `MANUAL_INTERVENTION_REGISTER.md`).

---

## Recovery capability per real failure class (Test Scenario 20)

| Failure class | Auto-recover? | Safe retry? | Rollback? | Human required? | Evidence preserved? |
|---|---|---|---|---|---|
| Invalid/expired API key | No — correctly fails to `UNAVAILABLE`, never crashes | N/A (a bad key won't succeed on retry) | N/A | Yes — founder must fix the credential | Yes — `ArmStatus.UNAVAILABLE` + real error text, live-verified this round with a genuinely invalid key (real 403 from Paddle, correctly caught, no leaked secret) |
| Timeout | Yes — real retry with backoff (`_request_with_retry`, 3 attempts) | Yes | N/A | No | Yes — wrapped as a real `RuntimeError` with the real underlying cause |
| Rate limit (429) | **No** — treated as a permanent 4xx failure, never retried | **No** (real gap, F6) | N/A | Effectively yes (a legitimate rate-limited call is not distinguished from a real permanent error) | Yes | 
| Unavailable platform | Yes — `ArmStatus.UNAVAILABLE`/`COOLDOWN`, real per-arm circuit breaker (`COOLDOWN_THRESHOLD = 3`) | Yes, after cooldown | N/A | No | Yes |
| Malformed response | Yes, at the real caller-facing boundary (`PaddleArm` catches it) | Yes | N/A | No | Yes, though the raw error message is generic (F8) |
| Duplicate transaction | Yes — real, proven idempotency check (`PaddleArm.publish()`'s `custom_data`/`source_id` dedup, covered by existing passing tests) | Yes | N/A | No | Yes |
| Missing product | Yes — `list_products()` failure degrades to "create fresh," never blocks (existing, passing test: `test_list_products_failure_degrades_to_creating_fresh_never_blocks_publish`) | Yes | N/A | No | Yes |
| Invalid checkout URL | Not applicable — no checkout URL has ever been generated to test against (F2) | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Partial API failure (e.g. product created, price creation fails) | Yes — real, documented behavior: `publish()` still reports `ok=True` with a real partial product ID rather than discarding real progress over a downstream failure | N/A | No real rollback of the partially-created product exists — by design, this factory never auto-deletes a real, live-created artifact | No, unless a human decides the partial state needs manual cleanup | Yes |
| A real completed transaction later needing a refund | **No real path exists at all** | N/A | N/A | Yes, entirely — no refund automation exists anywhere (F confirmed in `PLATFORM_RELIABILITY_REPORT.md`) | UNKNOWN — untested, since 0 real transactions have ever existed to refund |

## Automation already real vs. genuinely missing

**Already automated, confirmed working this round:**
- Product discovery/scoring/quality-gating (Golden Hunter + `executive_quality_gate.py`)
- Product-catalog↔live-Paddle-account consistency (proven 6-for-6 match)
- Revenue/reconciliation/alert computation (all callable on-demand, ADR-202)
- Crash-loop recovery for both `server.js` and `factory_loop.js` (`scripts/supervisor.js`, real, already running under supervision this session)

**Genuinely missing, safe to close (AUTOMATABLE per `MANUAL_INTERVENTION_REGISTER.md`):**
- Paddle rate-limit-aware retry (F6)
- Product Master Catalog field completeness (F5)
- Daily-tick wiring for `commercial_reconciliation.py`/`commercial_alerts.py` (disclosed, deliberate deferral from ADR-202)

**Genuinely missing, NOT safe to automate (crosses a protected or legal boundary):**
- Real checkout-URL generation without explicit authorization (a live financial-adjacent mutation)
- Refund processing (no real transaction has ever existed to build this against — building it now would be speculative, untestable automation)
- The 4 permanently protected gates (unchanged, by standing founder decision)

---

*See also: `MANUAL_INTERVENTION_REGISTER.md`, `FAILURE_REGISTER.md`.*
