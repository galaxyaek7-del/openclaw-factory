# The Simulation That Wrote To Production

**Found:** 2026-08-08, Phase 34 (ADR-227), auditing `data/` for stray files before committing.

## The mistake

`commission_simulation.py::simulate_failure_scenarios()`'s `ai_failure_fallback` scenario called `outreach_engine.draft_outreach_message()` without an isolated `log_path` argument. Every other line in that same function correctly used a `tempfile.TemporaryDirectory()`-scoped path — this one call was missed. Every test run (and every direct interactive check) of the simulation lab silently appended a real-looking `DRAFTED` event to the real, production-default `data/outreach_log.jsonl` — ~20 near-identical entries accumulated across this single session before being noticed.

## How it was found

A routine `git status --short data/` check before committing (this session's own standing discipline, applied consistently after every phase) surfaced `data/outreach_log.jsonl` as an untracked file that shouldn't have existed given 0 real outreach has ever occurred in this factory.

## The fix

Wrapped the one missed call in the same `tempfile.TemporaryDirectory()` pattern every sibling call in the function already used; deleted the polluted file; added a dedicated regression test (`test_never_writes_to_real_default_outreach_log`) asserting the real default path's existence is unchanged before/after a full simulation run.

## The generalizable lesson

A simulation module with N real default-path-writing sibling functions is only as isolated as its *least* isolated line — a single missed override anywhere inside a large "everything is tagged SIMULATION_ONLY" function defeats the whole guarantee for that one code path, silently, with no error or warning at the time. The mechanical defense that actually caught this wasn't code review of the simulation module itself — it was the unrelated, generic `git status` habit of checking for unexpected new files before every commit. Every future simulation/test-lab module in this factory should have one explicit regression test per real default-path file it could plausibly touch, not just one aggregate "never writes to *a* real file" test — this bug specifically would have passed a less granular check, since 6 of 7 default paths in the same function were already correctly isolated.

---

*See also: `OpenClaw_Brain/19_Lessons_Learned/The_Substring_Match_That_Contradicted_Itself.md`, `feedback_diff_data_files_around_test_runs` (session memory).*
