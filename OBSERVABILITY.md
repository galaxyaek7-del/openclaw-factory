# Galaxy Forge — Observability

**Date:** 2026-08-08 | Phase 14, Sections 10-12. Real, evidence-based coverage of health/metrics/alerting across the 9 named health domains and 13 named metrics.

---

## Production health coverage (Section 10)

| Domain | Real coverage |
|---|---|
| System health | `computeHealthStatus()` (`server.js`/`lib/health_checks.js`) — memory, CPU (honestly `Unknown` on Windows), disk space, `storage_integrity` |
| API health | `GET /api/v1/metrics.json` (`lib/metrics.js::summarizeRoutes()`) — real per-route request counts, error rates, last success/failure timestamps |
| Marketplace health | `commercial_control_center.py`, `channels/*_arm.py::health_check()` (real, live, added ADR-202) |
| Worker health | Real crash-loop detection in `scripts/supervisor.js` |
| Queue health | NOT APPLICABLE — no queue exists |
| Database health | NOT APPLICABLE — no database exists; `storage_integrity` is the real analog |
| AI health | Real network-reachability check to Groq in `computeHealthStatus()`; real per-call cost/latency logging in `data/ai_cost_log.jsonl` |
| Commercial health | `commercial_control_center.py::global_commercial_score()`, `commercial_alerts.py` (both real, ADR-202) |
| Automation health | `autonomous_operations_status.py`, `resilience_monitor.py::assess_resilience()` |
| Security events | `resilience_monitor.py`'s real `security_drift` findings (dependency-pinning check); no dedicated security-event log exists beyond this |

## Traceability and correlation IDs

**Real, domain-specific IDs exist and DO link related events within their own domain:** `decision_id` (decisions → evaluations → outcomes), `product_source_id`/`custom_data.production_id` (a production run → its real Paddle product), `request_id` (a customer's full pipeline journey). **No single, unified `correlation_id` traces one real transaction across all domains** — confirmed by direct search, 0 matches for `correlation_id`/`trace_id` anywhere in the repository (Phase 13 Finding F9, P3). At 0 real transaction volume, manually following the 3 domain-specific IDs is not yet a real operational burden; this becomes worth closing once real transaction volume exists to make cross-domain tracing genuinely painful.

## Metrics (Section 11) — measured only where reliably measurable

| Named metric | Real status |
|---|---|
| Uptime | **REAL** — `process.uptime()`, exposed via `galaxy_forge_uptime_seconds` (Prometheus format) and JSON |
| Error Rate | **REAL**, per-route — `summarizeRoutes()`'s `error_rate_pct` |
| API Failure Rate | **REAL** — same mechanism, per external-call site where instrumented (Paddle/Groq calls are not yet individually counted in `METRICS_REGISTRY` — only inbound HTTP routes are; a real, disclosed gap) |
| Job Failure Rate | **PARTIAL** — real per-action `error` field exists (Phase 10B), but no aggregate "job failure rate" metric is computed from it |
| Retry Rate | **NOT MEASURED** — retries happen (Groq, now Paddle) but are not counted into a metric, only logged inline |
| Recovery Rate | **NOT MEASURED** — recoveries happen (supervisor restarts, circuit-breaker resets) but aren't aggregated into a rate |
| Mean Time To Detection | **NOT MEASURABLE** — would require a real incident-timestamp history long enough to average; `data/incidents.jsonl` exists (`resilience_monitor.py`) but has too few real entries to compute a meaningful MTTD yet |
| Mean Time To Recovery | **NOT MEASURABLE** — same reason |
| Synchronization Delay | **NOT MEASURABLE** — no real, recurring sync job exists yet whose delay could be measured (the only real sync, `reconcile_ledger_to_finance()`, runs on-demand, not on a schedule) |
| Webhook Processing Delay | NOT APPLICABLE — no webhooks |
| Commercial Data Accuracy | **REAL** — `commercial_reconciliation.py`'s real, live discrepancy count (0 today, proven exact-match) is the honest measurement of this |
| Manual Intervention Rate | **REAL, qualitative** — `MANUAL_INTERVENTION_REGISTER.md`'s real classification; not yet expressed as a single numeric rate (would require a real count of total operations to divide by, which barely exists at 0 real transaction volume) |
| Automation Success Rate | **PARTIAL** — real per-arm publish success/failure is in the ledger; not yet aggregated into one company-wide percentage |

**Per the directive's own rule ("do not create metrics that cannot be measured reliably"): MTTD, MTTR, Synchronization Delay, and Webhook Processing Delay are honestly left unmeasured/not-applicable rather than backed into a number from too little real data.**

## Alerting (Section 12)

`commercial_alerts.py` (ADR-202, built one phase earlier) already implements exactly the directive's own required shape: a real severity classification (`informational`/`warning`/`critical`/`emergency`, matching `resilience_monitor.py`'s established vocabulary), and every finding carries `area`/`severity`/`detail`/`evidence`/`data_available` — a direct match for the directive's "what happened / component / impact / evidence" requirement. What/when/automatic-action-taken/recommended-human-action are present in the `detail` and `recommended_action` fields of `commercial_daily_brief()`. **Alert fatigue avoidance is real and structural**: 6 of 11 named commercial triggers have a real check and only fire above `informational` when a real condition is met — confirmed live this round, 0 active alerts under current (healthy, $0-revenue) conditions.

---

*See also: `RELIABILITY_ARCHITECTURE.md`, `AI_RELIABILITY_REPORT.md`.*
