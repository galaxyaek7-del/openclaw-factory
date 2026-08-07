# OpenClaw / Galaxy Forge — Rollback Protocol

**Status:** Permanent, part of the Company DNA (`COMPANY_DNA.md`). "If serious degradation occurs, automatically recommend rollback" checked against two real, already-built citation systems — `autonomous_business_builder.py::execution_phases()`'s real per-stage `rollback_plan` and `resilience_monitor.py::_rollback_guidance()`'s real per-incident-area guidance. Neither is rebuilt here.

---

## The real, existing rollback citations

`autonomous_business_builder.py`'s 5 real pipeline stages each carry a real, deterministic rollback description — never a fabricated business task. Examples, verbatim from the real code: a discovery-stage decision has "no rollback needed — its only output is a real, later-reviewable discovery decision"; a real Dual Inspection failure "stops publishing and is logged in `QUARANTINE.md` via `inspectors.py::_log_quarantine()` — never a partial publish"; the real, available rollback for a live channel is `channels/publish_protection.py::trigger_emergency_stop()` — an explicit, founder-gated human action, not an automatic reversal.

`resilience_monitor.py::_rollback_guidance(area)` is the real, per-incident-area lookup already wired into every real incident record (`record_incident()`'s own Learn fields, `EXECUTIVE_MEMORY.md`) — real guidance for a real, matched area, `None` honestly when no specific guidance exists for a novel area rather than a generic placeholder.

## "Automatically recommend" — real, but never "automatically execute"

Both mechanisms **recommend**, cited directly in real incident/decision records. Neither calls `trigger_emergency_stop()`, `approve-first-publish`, or any other real reversal action itself — that stays exactly as human-gated as every other irreversible action in this company (`INTEGRITY_RULES.md` §3). A real emergency stop is one real, explicit `POST /api/v1/actions/publish-emergency-stop` call away, always founder-triggered.

## Why this has never been exercised for real

Rollback presumes something is live to roll back. `config/reality.json`: `published_books: []`. Every rollback citation above has been tested against real *hypothetical* pipeline stages and real *internal* incidents (the health-trend finding) — never against a real live product experiencing real degradation, because no real product has been live long enough, or at all, to degrade.

## The one real, concrete rollback already proven this session

Not hypothetical: the EU AI Act toolkit's own real price correction ($310 → $155) *was* a real rollback of a real, already-decided commercial position — caught and reversed before it reached a real customer, using exactly this discipline (real evidence, `economics.market_realism_check()`, a real, documented reason) rather than an automated trigger. The mechanism this document describes is not new; it is the same one that already worked once, for real, this session.

---

*See also: `GLOBAL_LAUNCH_PROTOCOL.md`, `POST_LAUNCH_MONITORING.md`, `INTEGRITY_RULES.md` §3.*
