# Bottleneck Analysis

**Date:** 2026-07-17
**Directive:** "Executive Directive — Phase 10B: Performance Engineering & Production Hardening," objective 2 (deliverable)

---

## Load test results (`scripts/perf_measure.js`, real, live)

| Concurrency | Wall time | Errors | Avg latency | p50 | p95 | p99 |
|---|---|---|---|---|---|---|
| 10 | 2,633ms | 0 | 1,795ms | 1,935ms | 2,629ms | 2,629ms |
| 50 | 14,151ms | 0 | 11,031ms | 12,762ms | 13,378ms | 14,130ms |
| 100 | 27,619ms | 0 | 22,913ms | 26,283ms | 27,567ms | 27,597ms |

## The real bottleneck: no concurrency control on Python subprocess spawning

**Zero errors at every concurrency level tested, up to 100 simultaneous requests.** The system does not crash and does not return 500s under load — but latency degrades roughly linearly with concurrency, because every concurrent request that hits a Python-backed endpoint spawns its own `python` interpreter, and 50–100 concurrent interpreter startups saturate available CPU. This is the single identifiable bottleneck behind every number above.

**Confirmed not a resource leak**: zero orphaned `python.exe` processes remained after the 100-concurrent test (checked directly via `tasklist`) — every spawned subprocess completed and exited cleanly even under heavy contention.

## Why this is not fixed in this phase

A process pool, a request queue, or a persistent long-running Python worker would each be a real architectural change to how `mission_control_api.py` is invoked — explicitly out of scope ("do NOT redesign architecture," "improve only production quality"). It is also not currently a production blocker: today's real usage is a single operator, not 50–100 concurrent users. Recommendation for a **future**, explicitly-scoped phase if real concurrent traffic ever materializes: a small worker pool (2–4 persistent Python processes) sitting behind `runPythonService`/`runPythonActionAsync` would remove the bulk of this latency without changing any endpoint's contract.

## Secondary finding: async action timeout gap (found and fixed this phase)

Before this phase, `runPythonService()`, `runPythonActionAsync()`, and `runFullCycleActionAsync()` had **no timeout** — a genuinely hung subprocess would leave an HTTP request pending forever, or (worse, for the async actions) permanently wedge the single-writer guard on that action until the whole server restarted, since the job would never leave `'running'`. Fixed with a shared `killAfterTimeout()` helper (30s for fast local-file services, 15 minutes for the slow real-network async actions — a hang safety net, not a normal-operation limit). Verified directly: a synthetic 10-second hung process was correctly killed at ~552ms past a 500ms timeout; a fast, clean process was unaffected.

## Not a bottleneck (confirmed by measurement, not assumption)

- Knowledge-base search: 11–23ms across 100 real files.
- Pure-JS endpoints (`alerts`, `market-intelligence`): single-digit-to-low-double-digit milliseconds.
- Memory: stable across the entire session (real production server) and after a synthetic load spike (test server).
