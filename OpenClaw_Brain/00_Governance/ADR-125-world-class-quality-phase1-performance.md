# ADR-125 — Galaxy Forge v1.0 "World-Class Quality": Phase 1 (Performance + Auto-Refresh)

**Date:** 2026-07-25
**Status:** Adopted (Phase 1 of 8; remaining phases scoped, not started — see below).

---

## The directive

Founder decision: Galaxy Forge enters a "Product Excellence" phase, with 8 priority areas (Mission Control Excellence, Performance, Reality First, Production Readiness, UX, Revenue Focus, a Linear/Stripe/Vercel/Notion/GitHub quality bar, and a final "digital operating system" objective). "Do NOT add new engines unless absolutely required." "No cosmetic work. Only improvements that increase truth, speed, usability, reliability and business value."

Given the real scale of 8 simultaneous areas, this round executed one concrete, high-confidence phase — Performance — rather than attempting all 8 at once, which would trade the audit-first discipline this factory has used all session for speed of claiming completion. The other 7 areas are honestly mapped below: already-real (cited), or explicitly deferred with a reason, never silently skipped.

## What was audited before writing any code

A read-only audit (no code written) of the "Production Readiness" bucket found it **~85% already real**, not a gap to build from scratch:

- **Health checks** — real and comprehensive. `lib/health_checks.js`: memory, CPU (honestly reports `os.loadavg()` unavailable on Windows), disk (real PowerShell `Get-PSDrive` query), network reachability (real HEAD requests to Groq/Telegram/GitHub), storage integrity (per-line JSON/JSONL validation). `database`/`queue_system`/`worker_pool` explicitly `not_applicable`, never faked.
- **Backup** — real. `recovery/snapshot.py`'s `snapshot_before()` copies 7 real critical files to `.snapshot-{timestamp}.bak` before risky operations, called from `orchestrator/orchestrator.py` and `channels/paddle_arm.py`.
- **Restore** — real and tested. `scripts/restore_file_from_git.js`: dry-run by default, `--apply` backs up the pre-restore file first, logs via `recordRecoveryAction()`.
- **Monitoring** — real, two layers. `scripts/supervisor.js` (opt-in crash-restart, crash-loop guard, real Telegram alerts). `lib/metrics.js` (real Prometheus-text exposition at `/api/v1/metrics`).
- **Logging** — real (already confirmed this session): 5 real operational log files, all tailed by Mission Control's `system-logs` service.
- **Automatic refresh** — the one real, confirmed gap. `dashboard.html` already has `setInterval(load, 60000)`; neither `mission_control.html` nor `mission_control_executive_v1.html` did.

**Reality First** (directive bucket 3 — real evidence, no invented signals, traceable decisions, Unknown stays Unknown) is not new work either: this is exactly what ADR-121 (Proof of Payment doctrine) and ADR-122 (Strategic Doctrine v2) already adopted as permanent, hard-gated scoring policy two rounds ago. Nothing to build here; cited as already-satisfied.

## What was built this round (Performance)

**`runPythonServiceCached()`** (`server.js`) — a generic, opt-in short-TTL (20s) cache wrapper around `runPythonService()`, the one real chokepoint every Python-backed `SERVICE_REGISTRY` read spawns through (`mission_control_api.py`, a fresh subprocess + module import per call). Same real pattern and reasoning already adopted for `runRealityCached()` (adopted specifically because `GET /api/dashboard`'s `reality.py` call cost 3-4 real seconds per request with zero caching).

Applied to the **20 confirmed pure-read `SERVICE_REGISTRY` handlers** (`opportunities`, `opportunity_pipeline`, `decision_history`, `production`, `revenue`, `automation`, `system_configuration`, `recovery`, `production_families`, `commercial_execution`, `ai_capability`, `golden_hunter_status`, `pioneer_status`, `knowledge_graph`, `department_health`, `research_department`, `ai_doctor`, `integration_registry`, `evolution_report`, `market_review`, `strategic_report`, `tool_intelligence`, plus `product_concept_comparison` keyed by its `niche` argument) — every one independently measured this session (Mission Control CEO review, ADR-124) at 1-14 real seconds per call, all pure reads of slow-moving business state, none per-request-sensitive.

**Deliberately NOT applied** to `runPythonService()` itself, nor to every call site: several existing callers are real mutations (`ai_capability_request`, `resolve_recovery`) or route through the separate, already-job-tracked `ACTION_REGISTRY`. Caching a mutation would be a real correctness bug — a repeat call silently not re-executing inside the TTL window — not a performance win, so those stay untouched and uncached, exactly as before.

**Cache-bypass, honored end to end.** `?fresh=1` on any cached `/api/v1/*` GET forces a genuinely fresh real read. Mission Control's own Refresh button now sends it explicitly — a click labelled "Refresh" must never quietly hand back a stale cached value, matching the founder's own "every click should save time" and the Linear/Stripe/Vercel quality bar. Verified live: identical real data on a cache hit (`diff`-confirmed byte-identical payload, only the envelope's own `generated_at` legitimately differs), and a measurably distinct real re-fetch when `?fresh=1` is present.

**Auto-refresh**, closing the one confirmed real Production Readiness gap: `mission_control_executive_v1.html` gained the same real `setInterval` pattern `dashboard.html` already uses (60s), extended with one real improvement neither prior page had — it skips the tick entirely while the browser tab is backgrounded (`document.hidden`), so an idle tab never pays real Python-subprocess cost for a screen nobody is looking at. Auto-refresh reuses the cache (does not force `?fresh=1`) — an unattended tick landing on a cache entry another real caller just populated is exactly the redundant-spawn cost the cache exists to remove.

## A disclosed, bounded tradeoff

The generic `v1Router` GET route stamps `generated_at: new Date().toISOString()` on every response envelope, regardless of whether the underlying `data` came from cache. Verified live: a cache hit's real data payload is byte-identical to the original fetch; only the envelope's `generated_at` differs (by the real request latency, not the cache age). This means a cached response's "Updated: Xs ago" label can under-report real data age by up to the 20s cache TTL — never a lie about the data's contents, only a bounded imprecision in how "how fresh" is labeled. Fixing this fully would require threading real per-key generation timestamps through the generic route dispatch, adding real architectural coupling for a worst-case 20-second display discrepancy — judged disproportionate; disclosed here instead of built around.

## Validation

`node -c server.js`, the jsonl-duplication guard, and `mission_control_executive_v1.html`'s inline-JS syntax check — all clean. Full CI-equivalent JS suite (`test_metrics.js`, `test_dashboard_data.js`, `test_n8n_notify.js`, `test_factory_loop_golden.js`, `test_api_contract.js`) — 159/159 passing, including two new focused regression tests: one proving `runPythonServiceCached()` actually caches (byte-identical repeat payloads, sub-1500ms) and that `?fresh=1` still returns valid real data; one confirming `mission_control_executive_v1.html`'s own auth/serve contract. Live-verified against the real running server via direct API calls (curl) that a cache hit and a `?fresh=1` bypass both behave exactly as designed. Zero Python files touched — Python suite unaffected, not re-run.

## The remaining 7 directive areas — honest status, not silently deferred

| Area | Status |
|---|---|
| 1. Mission Control Excellence | Partially addressed by ADR-124 (visual hierarchy, real bugs) and this round (auto-refresh, real Source/Updated/Confidence on every card — already true since ADR-123). Not yet done: a dedicated mobile-device pass (tooling limitation this session), lazy-loading heavy panels below the fold. |
| 2. Performance | This round: caching + auto-refresh. Not yet done: the four `ACTION_REGISTRY`-based reports (still 3-25s, uncached — a different, job-tracked mechanism, deliberately out of this round's scope). |
| 3. Reality First | Already real — ADR-121/122's Proof of Payment doctrine and 4-condition hierarchy. No new work required. |
| 4. Production Readiness | ~85% already real (see audit above). Auto-refresh closed this round. Not yet done: a "public launch"-grade role-based access review (flagged ADR-124 #5). |
| 5. User Experience | Partially addressed by ADR-124's flattening rewrite ("what should I do next" is now Company Health's literal headline). Not yet done: a dedicated 8-hours-a-day usage-pattern review. |
| 6. Revenue Focus | Already the ladder's real scoring doctrine (recurring revenue, defensibility, market signal are existing weighted components in `profit_oracle.py`, hardened by ADR-121/122). No new work required this round. |
| 7. Quality Standard (Linear/Stripe/Vercel bar) | The Refresh-button honesty fix and dark premium design (ADR-123/124) move toward this; a full design-system pass was not attempted this round. |
| 8. Final Objective | Aspirational/directional — not a discrete, buildable task; each of the 7 areas above is a real step toward it, not a separate deliverable. |

Proposing to take up area 1 (mobile/lazy-load) or area 2's remaining action-layer caching next, founder's call.
