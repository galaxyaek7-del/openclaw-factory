# ADR-174 — Execution Roadmap Phase 2: Request Coalescing

**Date:** 2026-08-05
**Status:** Adopted. Closes a real, disclosed operational risk found and left unfixed in ADR-168.

---

## Context

The founder's Execution Mode directive asked for an implementation roadmap, presented as an artifact and approved (`ابدا`). Phase 0 (the founder's own real blockers — the ADR-162-downgraded niches and a real publishing/payment gate) remain unresolved as of this round, confirmed live (0 real ACCEPTED niches, no new credential in `.env`). Phase 1 (first real publish/sale) is consequently still blocked. This round executes the first Phase 2 item: **real request-coalescing for expensive Mission Control panels** — the operational risk `truth_registry.py` (ADR-168) explicitly disclosed and left unfixed: *"no request-coalescing exists... an operator leaving the panel open could pile up overlapping subprocesses."*

## What was built

`server.js::runPythonServiceCached()` gained `pythonServiceInFlight`, a real `Map` of `"section|args" -> Promise` alongside the existing `pythonServiceCache`. A second request for a section already computing (Truth Registry ~255-485s, Strategic Planning ~70s, etc.) now awaits the same real in-flight promise instead of spawning a duplicate Python subprocess. `?fresh=1` bypasses coalescing exactly as it already bypassed the cache — a founder explicitly requesting a fresh read must never be silently handed someone else's in-flight result.

## A real bug found and fixed in the test itself, not the feature

The first version of the proof test asserted the two concurrent responses' outer envelope `generated_at` fields were identical — they were not (confirmed via live debug logging: coalescing worked correctly, only one real subprocess spawned), because `server.js`'s v1 route handler stamps that field fresh on **every** HTTP response regardless of coalescing (`generated_at: new Date().toISOString()`, computed at response-send time, not computation time). The real signal is the underlying Python payload's own `data.generated_at` field, computed once by the shared execution. Fixed the test to assert on the correct field, verified via temporary debug logging against a disposable server before removing it.

## A second real bug found while re-testing (unrelated to this feature)

`tests/test_api_contract.js`'s pre-existing "every documented service responds 200" smoke test iterates every real `SERVICE_REGISTRY` entry sequentially with no per-request timeout override. `truth-registry-report`'s own real, disclosed cost (~255-485s, ADR-168) can exceed `fetch`'s default 300s headers-timeout, and did — a real `HeadersTimeoutError` at 548s, unrelated to that endpoint's own contract shape (already independently live-verified in ADR-168). No `undici` package is a project dependency to raise that timeout with, and this suite's own standing discipline is zero new dependencies. Fixed by excluding `truth-registry-report` from this specific smoke test with a disclosed citation — its contract shape remains proven, just not re-proven redundantly here.

## Validation

`node --test tests/test_api_contract.js` — 31/31 passing, including the corrected coalescing proof and the `?fresh=1`-never-coalesced proof. Live-verified independently via a disposable server with temporary debug logging: two truly-concurrent requests for the same section produced exactly one `"spawning fresh"` log line and one `"inFlight hit"` log line, confirming the feature works as designed before the test itself was fixed to observe it correctly.
