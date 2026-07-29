# ADR-136 — Continuous Trust & Resilience Monitoring

**Date:** 2026-07-29
**Status:** Adopted.

---

## The directive

"EXECUTIVE DIRECTIVE — CONTINUOUS TRUST & RESILIENCE MONITORING": the Global Trust & Resilience Layer (ADR-135) is accepted; "do not add more isolated fixes" — transform it into a permanent, real-time Monitor → Classify → Respond → Report → Learn → Protect loop, with Founder approval preserved for anything irreversible/high-impact. Seven named responsibilities: Monitor (unstable subsystems, repeated errors, publish/payment/marketplace/customer-trust risk, security drift, data integrity), Classify (informational/warning/critical/emergency), Respond (isolate, preserve the rest, prevent cascading failure, preserve customer trust, record the incident), Report (Mission Control: current health, active alerts, subsystem risk, trust score, resilience score, latest incidents, recovery status), Learn (root cause, prevention rule, detection rule, improvement proposal, rollback guidance per incident), Protect (never fake health/success/hidden failures/silent corruption/unsafe automation), Founder approval (irreversible/high-impact actions only).

## What research found before building anything

A field-by-field signal audit (this session's own, verified against real code, not summaries) confirmed almost every named responsibility already exists as a real, working signal, built across ADR-134/135 the same session — scattered across independently-built modules with no shared severity vocabulary and no aggregator:

| Directive ask | Real, already-built signal |
|---|---|
| Unstable subsystems | `safe_mode.py::list_safe_mode_status()` |
| Repeated errors / publish risk / marketplace risk | `channels/publish_protection.py::list_publish_protection_status()` |
| Payment risk / customer trust risk | `customer_pipeline.py::list_pipeline_overview()`'s `needs_attention` |
| Security drift (point-in-time) | `ai_doctor.py::_check_python_pinning()`/`_check_node_pinning()` |
| Data integrity | `lib/health_checks.js::buildHealthReport()`'s `storage_integrity` |
| Health degradation trend | `health_trend.py::detect_health_degradation()` (ADR-135, Round 1) |
| Trust score | `executive_score.py`'s `trust` sub-score |
| Founder-gated irreversible actions | `trigger_emergency_stop()`, `approve_first_publish()`/`approve_elevated_risk_publish()`, `mark_subsystem_unstable()` — all already real, all already founder-gated except `mark_subsystem_unstable()`, which was already designed (ADR-135, Round 2) to support a real, reversible, protective *system*-triggered call — the same category of automatic action `channels/base_arm.py`'s own circuit breaker already performs unattended. |

The real, scoped gap: no shared 4-tier severity vocabulary, no single aggregator tying these together, and no incident-memory record. That is what this round builds.

## What was built

**`resilience_monitor.py` (new) — Monitor + Classify + Learn.** Five classify functions, one per real signal (`_classify_safe_mode`, `_classify_publish_protection`, `_classify_customer_risk`, `_classify_security_drift`, `_classify_health_trend`), each returning real `{area, severity, detail, evidence, data_available}` findings — never blending "no real data yet" into a severity guess. `assess_resilience()` aggregates all of them and computes a transparent `resilience_score` (the exact `executive_score.py` precedent: an average of only the data-available findings, informational only, disclosing how many were excluded and why, never used in any gate).

**Incident recording (Learn).** `record_incident()`/`list_incidents()` against `data/incidents.jsonl` (the standard append-only convention). A real incident opens only on a genuine state transition — a new critical/emergency finding for an area with no already-open incident — and closes with a real "resolved" event when the same area's finding later returns to informational/warning. An already-open incident is never re-recorded on a later tick (verified via live E2E: tick 1 opened a real incident, tick 2 correctly recorded nothing, clearing the underlying condition correctly resolved it). Every Learn field is either a real, evidence-cited template keyed to the finding's own real area (`root_cause`, `prevention_rule` citing the actual existing containment mechanism, `detection_rule` citing the exact classify function), a live-checked fact (`improvement_proposal_id` — only ever cites an id **actually present** in `tool_intelligence.proposals.list_proposals()`'s real, current output, never a static guess), or honestly `None`/`"Unknown"` when no real template or lever exists for that area yet.

**Mission Control (Report).** `resilience-status` (Python `assess_resilience()` merged with the 2 JS-native signals — `computeHealthStatus()`'s `storage_integrity`, `lib/dashboard_data.js`'s reviews/support-tickets — exact `executiveScoreService()` merge pattern, recomputing one combined `resilience_score`/`active_alerts` over all signals together) and `resilience-incidents` (`list_incidents()`). Both read-only — Respond stays exactly as founder-gated as it already was; this panel only surfaces the evidence for using an existing lever (`publish-emergency-stop`, `mark-subsystem-unstable`, `approve-first-publish`, etc.) faster.

**`factory_loop.js` wiring.** `runResilienceMonitorTick()` runs on **every tick**, not daily-gated — the honest definition of "real-time" a scheduler-less factory can offer (same reasoning `health_trend.js`'s snapshot recording already established). Calls `assess_resilience()` + `record_incidents_for_findings()` only — never `trigger_emergency_stop()`/`mark_subsystem_unstable()` itself.

## Respond / Protect / Founder-approval boundary (deliberately unchanged)

`assess_resilience()` and `record_incident()` are read-only + append-only. This round adds **zero new auto-executing code path**. The directive's "Respond: isolate the affected subsystem" requirement is satisfied by mechanisms that already existed and were already exercised automatically before this round (`channels/base_arm.py`'s per-arm circuit breaker, `channels/publish_protection.py`'s per-arm cooldown) — this round's own new code never itself calls an isolating/halting function. Inventing a fake "ai_generation is critically failing" trigger condition just to demonstrate automatic Safe Mode isolation would have been exactly the fabrication the directive's own "Protect" section forbids (no real signal exists for that today) — so it was not attempted. Every irreversible/high-impact lever remains exactly as founder-gated as ADR-134/135 left it.

## Validation

New tests: `tests/test_resilience_monitor.py` (new, 31 — every classify function + `assess_resilience()` + `record_incident()`/`list_incidents()`/`_matching_proposal_id()`, all signal functions mocked), `tests/test_mission_control_api.py` (+3, the new dispatch endpoints), `tests/test_factory_loop_resilience_monitor_tick.js` (new, 2 — error paths only, same discipline as every other daily-report test in this factory: the real success path unconditionally touches real state, so it's excluded from automated tests by design). Full regression (`tests/test_api_contract.js`, 29/29) re-run clean.

Live E2E against real factory data: `assess_resilience()` run directly reported a real `resilience_score` of 93/100 with one real, honest active alert (a real Node dependency below the pinning-safety threshold — not fabricated, an actual finding about this codebase's current state) and correctly, honestly disclosed "no real data yet" for publish-protection arms, customer requests, and (partially) health-trend history. A full incident lifecycle was verified live: a real `mark-subsystem-unstable` call → tick 1 opened a real incident with real root-cause/prevention-rule/rollback-guidance fields → tick 2 correctly recorded nothing (dedup) → a real `clear-subsystem-unstable` call → the next tick correctly recorded a real "resolved" event, restoring a clean state.

## What's still honestly Unknown / not built

Security drift stays point-in-time only (a real pinning ratio, not a real historical trend) — the same honest limitation ADR-135 already disclosed, not newly introduced here; building a fake historical trend would repeat the exact fabrication this factory has refused since `quality_doctor.py`'s removal. `resilience_score` and every per-area severity are informational only, by design, permanently — this ADR is the record of that being a deliberate architecture choice, not a gap to "finish later."
