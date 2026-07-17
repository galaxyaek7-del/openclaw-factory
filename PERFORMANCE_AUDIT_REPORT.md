# Performance Audit Report

**Date:** 2026-07-17
**Directive:** "Executive Directive — Phase 10B: Performance Engineering & Production Hardening," objectives 1–2
**Tool:** `scripts/perf_measure.js` (new, standalone, native `fetch` only — no new dependency), run against a throwaway server instance; the real, all-session-long-running server was never load-tested directly (only its idle memory was sampled, safely, as an additional real data point).

---

## Startup time

**676ms** from process start to the server's own ready log line — measured directly, not estimated.

## API latency (5 sequential requests per endpoint)

| Endpoint | Avg | Min | Max | Backing |
|---|---|---|---|---|
| `/api/v1/alerts` | 2.9ms | 2.5ms | 4.1ms | Pure JS, local file reads |
| `/api/v1/market-intelligence` | 39.6ms | 36.4ms | 43.7ms | Pure JS |
| `/api/v1/automation-status` | 461.8ms | 440.4ms | 486.8ms | Python subprocess |
| `/api/v1/company-health` | 564.6ms | 555.4ms | 575.2ms | JS + real health checks (incl. an n8n ping) |
| `/api/v1/system-configuration` | 695.0ms | 673.8ms | 719.0ms | Python subprocess |
| `/api/v1/decision-history` | 741.1ms | 709.1ms | 789.8ms | Python subprocess, 555+ real records |
| `/api/v1/opportunity-queue` | 894.0ms | 836.6ms | 965.5ms | Python subprocess |
| `/api/v1/production-queue` | 1099.1ms | 1059.0ms | 1157.8ms | Python subprocess |

## The one clear, well-evidenced bottleneck

**Every Python-backed endpoint pays a ~400–1100ms tax per request, dominated by subprocess spawn + interpreter startup + module import — not the actual computation.** The pure-JS endpoints (`alerts`, `market-intelligence`) respond in single-digit-to-low-double-digit milliseconds doing comparable real file-read work. `runPythonService()` spawns a brand-new `python` process for every single call — there is no process reuse or pooling.

**This is disclosed, not fixed.** A persistent Python worker (or a process pool) would be a real architectural change — explicitly out of scope ("do NOT redesign architecture"). At today's real usage pattern (a single operator checking Mission Control occasionally), sub-second latency is not a production blocker. It becomes worth revisiting if real concurrent multi-user traffic ever materializes — see `EXECUTIVE_GAP_ANALYSIS`-style reasoning in the Bottleneck Analysis.

## Memory usage

- Fresh server, immediately after startup: **67,324 KB** (~65.7MB).
- **The real, already-running production server (PID 13528, alive for this entire multi-hour session, handling dozens of real requests across 12+ phases): 69,560 KB** — only ~2.2MB of growth over an entire session's real operation. This is the strongest real evidence available against a memory leak, because it's the actual production process, not a synthetic proxy.
- A fresh test server's memory after the 10+50+100-concurrent load test (160 total requests, many spawning Python subprocesses): grew to 191,652 KB, then **held flat** across 5 further idle requests — consistent with normal buffer/GC behavior under a load spike, not unbounded growth.

## CPU usage

Not measured with a dedicated profiler (none exists in this stack, and adding one would be new infrastructure). Indirect evidence: the load tests below show latency degrading gracefully under concurrency rather than the process becoming unresponsive or crashing — consistent with CPU contention from concurrent Python subprocess spawns, not a runaway/pegged CPU condition.

## Disk I/O

Not measured with OS-level tooling (none exists in this stack). Indirect evidence: `/api/v1/decision-history` (555+ real records, the heaviest real file read tested) adds only ~250-350ms over the lighter Python-backed endpoints — most of its latency is still the subprocess tax, not the file read itself.

## Large knowledge-base performance

`OpenClaw_Brain/` — 100 real markdown files, 868KB total. Real measured search latency: **11–23ms** per query (`GET /api/v1/knowledge-base?q=...`), scanning every file's every line. Not a bottleneck at this scale; the linear-scan approach (`knowledge_brain.js`'s `searchBrain()`) would need revisiting only if the Brain grows by roughly two orders of magnitude — not a concern today.
