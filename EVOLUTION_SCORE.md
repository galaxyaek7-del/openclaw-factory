# OpenClaw / Galaxy Forge — Evolution Score

**Status:** Permanent, part of the Company DNA (`COMPANY_DNA.md`). The directive's 7 named per-department fields (Current Score / Previous Score / Improvement Trend / Regression Risk / Technical Debt / Commercial Debt / Priority) checked field by field against real, already-existing signals — with one genuine, disclosed gap named directly rather than filled with an invented number.

---

## What's real today

| Requested field | Real coverage |
|---|---|
| Current Score | `launch_readiness.py`'s 8-dimension per-division scorecard + `commercial_readiness.py`'s 6-dimension company-wide score — both real, both computed live |
| Technical Debt | `strategic_intelligence.technical_debt` (`evolution_engine.py`'s own real citation) |
| Commercial Debt | `commercial_readiness.py`'s bottleneck dimension, now a named section in the Galaxy Evolution Report (ADR-187) |
| Priority | `capital_allocation_engine.py`'s Investment Score ranking |
| Regression Risk | **Partial** — `resilience_monitor.py`'s real critical/emergency findings are the closest real signal, but they flag active incidents, not a forward-looking regression *risk* score |

## The one genuine, disclosed gap: Previous Score and Improvement Trend

**Half-closed (ADR-200, 2026-08-07).** `commercial_readiness.py` gained the real, persisted daily snapshot this section named as the correct fix: `record_commercial_readiness_snapshot()` (the one real write path, wired into `factory_loop.js`'s daily tick, never called from the live score function itself), `commercial_readiness_history()`, and `commercial_readiness_trend()` — honestly `NOT_ENOUGH_DATA` until >=2 real snapshots exist, exactly the same discipline `growth_stages.py::growth_stage_history()` already established. `launch_readiness.py` (division-level readiness) still has no persisted snapshot — still computed fresh, live, every call, still no real Previous Score/Improvement Trend for that specific signal.

**Real, partial trend signals that exist today:**
- `health_trend.py` / `resilience_monitor.py` — real, recorded reliability trend over time (this is what caught the real "3 consecutive critical readings" incident found earlier this session)
- `growth_stages.py::growth_stage_history()` — real, recorded company-wide growth-stage snapshots over time
- `commercial_readiness.py::commercial_readiness_history()`/`commercial_readiness_trend()` — real, recorded company-wide commercial-readiness snapshots over time (new, ADR-200)
- `data/evidence_ledger.jsonl` — real, daily technical-readiness recording (ADR-182)

**Remaining honest gap:** `launch_readiness.py` (per-division, not per-company) has no persisted snapshot yet — the same fix pattern applies whenever that specific signal is next revisited; not built today because ADR-200 was scoped to the company-wide score this document named first.

## Why this gap is disclosed rather than filled today

Consistent with this session's own established discipline (`COMPANY_DNA.md` §3, "Evidence over assumptions") — a Phase 4 round about *not repeating mistakes* would be an especially poor place to quietly fabricate the one score this directive most explicitly asked to track over time.

---

*See also: `AUTONOMOUS_EVOLUTION_ENGINE.md`, `MONTHLY_EVOLUTION_REPORT.md`, `PRIORITIZATION_ENGINE.md`.*
