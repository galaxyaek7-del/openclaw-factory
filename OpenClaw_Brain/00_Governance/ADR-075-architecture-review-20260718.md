# ADR-075 — Full Architecture Review (Planning Phase, 2026-07-18)

**Date:** 2026-07-18
**Status:** Adopted. Planning-phase deliverable, per the founder's explicit directive not to implement new business features during this phase.

---

## What was done

Founder directed a full CTO-level architectural review: identify every subsystem, detect gaps/duplication/dead code/incomplete workflows/weak coupling/missing docs/reliability risks/scalability bottlenecks, produce a prioritized Engineering Report, update `PROJECT.md` and architecture documentation, align every recommendation with `MASTER_CHARTER.md`.

**Method:** rather than re-audit the whole codebase from zero, first located and read the excellent, still-substantially-valid prior audit cycle from 2026-07-17 (`CAPABILITY_MAP.md`, `ENTERPRISE_GAP_ANALYSIS.md` — 20 confirmed gaps, prioritized — `EXECUTIVE_BACKLOG.md`, `COMPANY_OPERATING_MODEL.md`, `ACTIVATION_PLAN.md`). That cycle predates the Strategic Production Priority Ladder pivot (`ADR-065`, fired the next day) entirely. Two parallel fresh audits (forked, research-only) then covered: (1) core pipeline modules not touched by this session's own ladder-pivot work, (2) the 13-directory intelligence/orchestration layer built under `ADR-048`–`064`. Findings cross-referenced against the prior cycle rather than duplicating it.

## Real findings, not speculative

- **Critical:** the ladder pivot's live decision gate (`ladder_opportunity_score()`, wired into `factory_loop.js`'s automatic tick via `ADR-070`) was never propagated to `decision_engine`/`mission_control_api.py` — Mission Control's Decision Queue still reflects the old gate. Two live decision surfaces now genuinely disagree.
- **Critical:** `requirements.txt` was missing `requests`, a real, unguarded dependency of `gumroad_publisher.py`/`paddle_publisher.py` — would fail a clean-environment CI run. Never caught because CI has never actually executed on GitHub's infrastructure (pre-existing, documented gap).
- **Critical:** a real, reproducible test-isolation bug in `tests/test_production_factory.py` — passed standalone, failed in full-suite order, because `channels.registry`'s global mutable state leaked `paddle`'s registration across test files.
- **Critical (structural, not a single bug):** 6 of 13 intelligence-layer subsystems (`executive_intelligence`, `multi_source_intelligence`, `strategic_intelligence`, `production_evidence`, `real_market_evidence`, transitively others) are real, tested, non-duplicated — and unreachable from any automatic entry point. Same pattern `STRUCTURAL_DIAGNOSIS.md` already flagged once before, recurring at larger scale.
- **Medium:** `config/channels.json` had no `paddle` entry (real drift from this session's own work); 5 core QA/economics/safety modules have zero direct unit tests; Paddle's checkout blocker remains founder-only.
- **Low:** several pre-existing, already-documented gaps (no ADR index, `FACTORY_STATUS.md` frozen since 2026-07-09, no single test-runner command) remain accurate, unchanged, correctly still low priority.

## What was fixed vs. what was only documented

Per the founder's explicit instruction ("do NOT implement new features... unless required to complete or stabilize the architecture"), only three small, safe stabilization fixes were made — all verified via the full test suite (479 Python tests green):

1. `requirements.txt` — added the missing `requests==2.34.2`.
2. `config/channels.json` — added the missing `paddle` entry with its real, current status.
3. `tests/test_production_factory.py` — fixed the test-isolation bug (`registry.clear()` before re-registering the 3 arms under test).

Everything else identified — including the highest-priority finding (C1, the two divergent decision surfaces) — was deliberately **not** touched, and is instead proposed as the next implementation phase, per the directive to propose before writing major code.

## Documents produced/updated

- New: `OpenClaw_Brain/00_Governance/ENGINEERING_ASSESSMENT_20260718.md` — the full Engineering Report (architecture overview, strengths, critical/medium/low findings, execution order, Master Charter alignment, proposed next phase).
- New: `PROJECT.md` (repo root) — a pointer document orienting a new reader to the constellation of living docs, not a duplicate of any of them.
- Updated: `COMPANY_OPERATING_MODEL.md`, `CAPABILITY_MAP.md` — dated "Update 2026-07-18" sections reconciling both with the ladder pivot, following this repo's own established convention (append a correction, don't silently rewrite history).
- This ADR.

## Proposed next phase (not started)

"Decision Surface Reconciliation + CI Hardening" — reconcile `decision_engine`/Mission Control with the ladder-aware gate (C1), and fix CI's missing JS test-file coverage + trigger a real GitHub-infrastructure CI run to validate today's `requirements.txt` fix independently. Full justification in `ENGINEERING_ASSESSMENT_20260718.md`'s closing section. Awaiting founder confirmation before any code is written against it.
