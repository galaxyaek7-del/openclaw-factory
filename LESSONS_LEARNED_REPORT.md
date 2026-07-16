# Lessons Learned Report

**Date:** 2026-07-16
**Directive:** "Executive Directive — Phase 11: Autonomous Production Launch," objective 8 (learn from every completed cycle)

---

Real lessons from building and running this session's work, not a generic checklist.

## 1. "Continuous"/"automatic" and "no scheduler" were on a collision course — worth naming explicitly, not building around silently

When a directive's language implies unattended, recurring execution and the codebase has a deliberate, documented "never build a scheduler" rule, the right move was to surface the conflict once with a concrete alternative rather than either (a) silently building the scheduler anyway, or (b) silently building something narrower without saying so. Naming it got a clear, fast answer and avoided guessing wrong on a decision that would have been expensive to reverse (a live, paid-API-calling background loop is not something to quietly walk back).

## 2. Documentation drift is real and recurring — found three times this session

`FACTORY_STATUS.md` §6 (n8n gap fix), `BLOCKERS.md` #4 (end-to-end validation), and this session's own memory files all needed a correction against real evidence at some point. The pattern: an ADR ships a real fix, and the "what's blocking us" doc that described the old state never gets touched again. This isn't a one-time cleanup — it will recur unless the habit changes (see Continuous Improvement Report).

## 3. Graceful degradation is worth testing at two levels, not one

`run-full-cycle`'s Python stages each degrade independently (tested with a mocked failure), and the JS-side `company_health_monitoring` addition is *also* independently wrapped so a JS-side failure can't discard already-completed Python results. Testing only one level would have left the other unverified — the two-level design was deliberate specifically because the orchestration spans two runtimes (Python subprocess + Node).

## 4. A single-writer guard was a real gap, not a hypothetical one

Phase 9 shipped 8 actions with no protection against triggering the same one twice concurrently. It wasn't caught by review — it surfaced naturally while validating Phase 11's new action, and the fix (reject a duplicate trigger with 409 while one is already running) was cheap once identified. Concurrency gaps in this kind of system tend to hide until something exercises the action layer hard enough to hit them.

## 5. Real evidence can falsify an assumption immediately — use it

Three separate times this session, a single grep or a single real log entry settled a question that would otherwise have been guesswork: the exact reason-string signature proved the n8n pipeline had fired for real; `profit_oracle.py`'s source proved `BLOCKERS.md` #4 was stale; and `checkGoldenStagnation()` returning `null` against the live file proved the flaky test's premise had already stopped being true. Checking the real file/log/source before writing a conclusion down was faster and more reliable than reasoning from memory or from a doc that might itself be stale.

## 6. Zero-ACCEPTED is not a bug to route around — it's the real, current, honest state

Every phase this session that touched the decision queue found the same thing: real candidates score 86–90+ but never clear the confidence gate. The system correctly reports this every time, including inside `run-full-cycle`'s own quality-validation stage. The temptation to "make the demo work" by loosening a gate was never acted on — the discipline held across every phase, including this one.
