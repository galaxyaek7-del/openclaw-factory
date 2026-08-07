# Galaxy Forge — Automation Gap Report

**Date:** 2026-08-07 (Phase 13), updated 2026-08-08 (Phase 14, ADR-204) | The real, current automation ceiling (Test Scenario 20, cross-referenced with `MANUAL_INTERVENTION_REGISTER.md`).

**Update note (2026-08-08):** the rate-limit row and the "genuinely missing" lists below described F6/F5 as open gaps — both are now fixed and regression-tested (see `PRODUCTION_HARDENING_REPORT.md`'s Phase 14 section and `FAILURE_REGISTER.md`). The original table is left below verbatim as the honest historical record of the Phase 13 finding it was written against; corrected current status follows in the new "Phase 14 update" section at the end of this document.

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

## Phase 14 update (2026-08-08, ADR-204)

Per Section 23's own instruction ("review the Manual Intervention Register, automate what's safe, document why not otherwise"):

| Item | Status as of Phase 14 |
|---|---|
| F6 — Paddle rate-limit retry | **FIXED** — real `Retry-After`-aware retry now in `channels/paddle_publisher.py`, 6 new regression tests |
| F5 — Product Master Catalog field completeness | **FIXED** — real cross-reference against `books/_generation_log.jsonl`, 4 new regression tests |
| F8 — malformed-response ValueError leak | **FIXED** — a real, additional finding closed alongside F6, 3 new regression tests |
| F3 — missing ledger event for the real EU AI Act Toolkit publish | **FIXED** — disclosed, auditable backfill (`backfilled: true`), the underlying `record_publish_attempt()` capability extended, never a silent correction |
| Daily-tick wiring for `commercial_reconciliation.py`/`commercial_alerts.py` | Still open — genuinely AUTOMATABLE, deliberately deferred again this round in favor of the higher-priority P1/P2 fixes above (Section 2's own priority-order instruction) |
| Real checkout-URL generation | Still `REQUIRED HUMAN DECISION` — unchanged; see `MANUAL_INTERVENTION_REGISTER.md` |
| Refund processing | Still not built — correctly so; 0 real transactions exist to build tested automation against |
| Automated restore function (`recovery/snapshot.py`) | **New finding this round** — real, safe, low-cost `restore_from_snapshot()` gap; see `BACKUP_AND_RESTORE.md`. Not built this round (a real data-recovery code path deserves its own focused, reviewed round, not a rushed addition inside an already-large hardening pass) |

---

*See also: `MANUAL_INTERVENTION_REGISTER.md`, `FAILURE_REGISTER.md`, `PRODUCTION_HARDENING_REPORT.md`.*
