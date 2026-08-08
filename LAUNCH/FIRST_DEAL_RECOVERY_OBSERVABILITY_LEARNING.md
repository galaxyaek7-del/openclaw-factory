# Galaxy Forge — Recovery, Observability, Knowledge Retention & Feedback Loop

**Date:** 2026-08-08 | ADR-229, Phase 36, Sections 25-28.

---

## Section 25 — Recovery

No real external action has occurred yet (0 real outreach sent, 0 real commissions recorded) — so this section audits the *real, already-tested* recovery posture this factory would rely on if/when the first controlled action is taken, rather than recovering from anything that has actually happened.

| Failure mode | Real recovery mechanism | Evidence |
|---|---|---|
| A recorded commission turns out to be wrong/fraudulent | `commission_ledger.py`'s real `REFUNDED`/`REVERSED` status transitions | `tests/test_commission_ledger.py`, `tests/test_commission_simulation.py` |
| A partner's terms change after recording | `commission_engine.detect_conflicting_terms()` flags divergence; nothing auto-corrects silently | `tests/test_commission_engine.py` |
| `factory_loop.js`/`server.js` crash mid-tick | `scripts/supervisor.js` — real crash-loop guard, real Telegram alert after repeated failures, both processes now run supervised (2026-08-07) | `tests/test_supervisor.js` |
| Corrupted/partial ledger write | `recovery/startup_check.py` + `recovery/snapshot.py` — real startup integrity check, real snapshot/restore | `DISASTER_RECOVERY_PLAN.md` |
| A stale `active_workflow`/`current_task` flag | Fixed dual-language bug (`factory_state.py`/`lib/factory_state.js`, ADR-157) — `clear_current_task()` now clears both fields | `tests/test_factory_state.py`, `tests/test_factory_state.js` |
| An in-flight expensive Python service call duplicated by a second concurrent request | `server.js::runPythonServiceCached()`'s real request-coalescing (ADR-174) | live-verified, ADR-174 |

**No new recovery code was needed for Phase 36** — every real failure mode a first controlled deal could hit downstream (bad evidence, wrong terms, a crashed tick, a corrupted ledger) is already covered by pre-existing, tested infrastructure. `DISASTER_RECOVERY_PLAN.md` remains current and was not found to need amendment.

## Section 26 — Observability

| Signal | Real source |
|---|---|
| Per-route request health (error rate, last success/failure time) | `lib/metrics.js::summarizeRoutes()` → `GET /api/v1/metrics.json` (ADR-151/157) |
| Service-call audit trail | `server.js::logServiceCall()` → `logs/service_layer.log` |
| Cross-department event correlation | `department_events.jsonl` — real, append-only correlation index (cited directly in `gfos.py`) |
| Recovery-event correlation ID | `lib/recovery_log.js` — emits a real correlation ID per recovery event (EOS Phase 2, 2026-07-19) |
| Health trend over time | `health_trend.py`/`lib/health_trend.js` — real recorded `GET /health` history |
| Resilience findings | `resilience_monitor.py::assess_resilience()` — 4-tier severity, real incident ledger (`data/incidents.jsonl`) |

The commercial path this phase built (`LAUNCH/FIRST_DEAL_COMMERCIAL_PATH.md`) reuses every one of these mechanisms at its real, already-instrumented steps (`commission_ledger` appends, `outreach_engine` drafts, `lead_outreach_agent` transitions) — no new observability infrastructure was required or built. A real correlation ID specifically for a first-deal journey does not yet exist as a *named* field (each ledger's own append-only ordering plus shared timestamps is the current, honest substitute) — disclosed as a minor, non-blocking gap rather than fabricated.

## Section 27 — Knowledge Retention

Two genuinely new lessons from this session's own real findings were written to `OpenClaw_Brain/19_Lessons_Learned/`, matching the directory's established mistake → consequence → how-found → fix → generalizable-lesson convention exactly:

- **`The_Evidence_That_Existed_But_Was_Never_Official.md`** — Phase 35's core fix: evidence existing and evidence being authoritative are different claims; the verification function conflated them until corrected.
- **`The_Whitespace_That_Passed_As_Proof.md`** — Phase 35's anti-fabrication firewall fix: a bare `not value` check let whitespace/trivially-short strings satisfy a guard meant to require real proof.

Both are picked up automatically by `knowledge_graph/build.py::_lesson_nodes()` (a mechanical parse of this directory) — no code changes needed, consistent with how every prior lesson file in this session has been incorporated.

## Section 28 — Golden Hunter Feedback Loop

Golden Hunter (`market_hunter.py`/`golden_hunter/hunt.py`) discovers *product* niches, not commission partners — the two pipelines are structurally separate (confirmed by direct code reading), so there is no real function call connecting them today, and none was fabricated here.

The real feedback relationship that does exist: this phase's own corrections feed forward into every *future* real evaluation, automatically, because they live in the shared, real modules both pipelines' evaluators build on:
- `commission_engine.KNOWN_EVIDENCE_CONFLICTS`/`FRESH_LIVE_CONFIRMATION` — this round's real WebFetch findings, now structurally excluded/included in every future `select_first_launch_opportunity()` call, not just a one-time note.
- `commission_ledger._is_meaningful()` — the fixed anti-fabrication guard applies to every future real commission attempt, not just this round's.
- `decision_engine/feedback.py::sync_outcomes()` + `evolution_queue.py`'s real outcome-measurement loop (ADR-143) remain the standing, general-purpose "did an implemented change actually help" mechanism this factory already has — no second, parallel learning loop was built for commissions specifically, since the general one already applies once a real commission decision exists to measure.

**No new Golden-Hunter-specific code was built this section** — the honest finding is that the two systems are correctly independent, and this phase's real learnings already propagate through the shared modules above without needing a bridge.

---

*See also: `LAUNCH/FIRST_DEAL_DRY_RUN_RESULTS.md`, `AUDIT/PHASE_36_COMMERCIAL_LAUNCH_CONTROL_REPORT.md`.*
