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

**No real, persisted, per-department historical score exists anywhere in this factory to compare "today" against "yesterday."** `launch_readiness.py` and `commercial_readiness.py` are both computed fresh, live, every time they're called — neither writes its own result to a dated ledger. Verified directly while writing this document, not assumed: a day-over-day comparison was attempted using the one real per-day trend source that does exist (`data/evidence_ledger.jsonl`'s daily technical-readiness recording, ADR-182) — it currently holds exactly one real day of data (2026-08-07), not enough to show a trend yet.

**Real, partial trend signals that do exist, company-wide (not yet per-department):**
- `health_trend.py` / `resilience_monitor.py` — real, recorded reliability trend over time (this is what caught the real "3 consecutive critical readings" incident found earlier this session)
- `growth_stages.py::growth_stage_history()` — real, recorded company-wide growth-stage snapshots over time
- `data/evidence_ledger.jsonl` — real, daily technical-readiness recording (ADR-182), one real day old as of this writing

**The honest conclusion:** building a fabricated "improvement trend" today, with one real data point, would mean inventing a slope from a single dot — exactly the kind of number `COMPANY_DNA.md`'s evidence-over-assumptions principle forbids. The correct fix is not a document — it is `commercial_readiness.py` and `launch_readiness.py` gaining a real, persisted daily snapshot the same way `growth_stages.py` and the evidence ledger already do, so a real Previous Score and a real Improvement Trend exist to report the next time this document is revisited. Named here as the real, specific next step, not silently deferred without a plan.

## Why this gap is disclosed rather than filled today

Consistent with this session's own established discipline (`COMPANY_DNA.md` §3, "Evidence over assumptions") — a Phase 4 round about *not repeating mistakes* would be an especially poor place to quietly fabricate the one score this directive most explicitly asked to track over time.

---

*See also: `AUTONOMOUS_EVOLUTION_ENGINE.md`, `MONTHLY_EVOLUTION_REPORT.md`, `PRIORITIZATION_ENGINE.md`.*
