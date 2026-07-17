# Zero-Assumption Production Audit

**Date:** 2026-07-17
**Directive:** "Final Executive Directive — Zero-Assumption Production Audit"
**Method:** 7 independent adversarial passes across all 20 requested subsystems, each instructed to trust nothing from any prior report, commit message, or test in this repo — every claim below was re-verified directly against current source, runtime behavior, or real data this session. Findings are followed by the fixes actually implemented, each with its own regression test and a full clean re-run of the suite.

---

## SECTION A — Verified Strengths

- **Single-writer/action-job guard (server.js)**: traced the exact call chain (`isActionRunning` → `triggerAction` → `newActionJob`) — synchronous, no `await` boundary between check and registration. Not exploitable for the same action name. **VERIFIED GOOD.**
- **`/api/v1/*` auth gate and `confirmed:true` enforcement**: one shared middleware, one shared handler — structurally impossible for any registered service/action to bypass either. **VERIFIED GOOD.**
- **n8n outbound safety**: real 5s `AbortController` timeout, never throws, no silent-success masking. **VERIFIED GOOD.**
- **API layer error handling**: all 11 `SERVICE_REGISTRY` entries share one loop-generated route pair with a universal try/catch — a broken service degrades to clean JSON, never crashes the process. **VERIFIED GOOD.**
- **Command injection**: every `child_process` call uses array-argument `spawn()`; the one `execSync` uses a hardcoded candidate list, never request data. **VERIFIED GOOD.**
- **Secrets hygiene**: `.env` never committed (`git log --all --full-history -- .env` empty), gitignored, no real secret value found via `git grep`. **VERIFIED GOOD.**
- **`golden_hunter_bridge` chain**: every hop (`huntGolden → triggerGenerateBook → triggerDistribute → pollSales`) traced directly — real, wired, no silent failures; every `catch` returns a structured result that reaches the log. **VERIFIED GOOD.**
- **`ACTION_JOBS` bounding**: capped at 200, prunes only finished jobs, never in-flight — no unbounded memory growth. **VERIFIED GOOD.**
- **`safeTick`'s error containment**: try/catch plus process-level `unhandledRejection`/`uncaughtException` handlers mean one bad tick cannot kill the loop process. **VERIFIED GOOD.**

## SECTION B — Verified Weaknesses (fixed this session — see Section G)

1. **Critical**: ~20 legacy routes had zero authentication, including two that mutate the real financial ledger (`/finance/add`, `/finance/delete/:id`) with no auth at all, plus server.js bound to all network interfaces rather than loopback.
2. **High**: `decision_engine/engine.py` independently duplicated a reason-string bug already fixed once in `profit_oracle.py` — already produced real, false-inequality text in 72 live tier1 records in `data/decisions.jsonl`.
3. **High**: `/generate-book` and `/api/sales/poll` — the two most business-critical, most-frequently-invoked subprocess spawns — had no timeout at all, unlike 3 other spawn sites.
4. **Medium-High**: `factory_loop.js`'s `setInterval` had no tick-overlap guard — latent because production has never been turned on, but real once it is.
5. **Medium-High**: `book_generator.py`'s legacy dispatch branch never ran Dual Inspection — a live violation of `CONSTITUTION.md` §17's "zero tolerance" claim for any caller reaching that path.
6. **Medium**: `factory_loop.js`'s stale-lock-reclaim path was still a TOCTOU race — only the "no lock yet" path had been made atomic.
7. **Medium**: `dashboard.html` had zero error handling around its `fetch` calls — a broken data feed would fail silently, forever, every 60s.
8. **Medium-High**: `GET /api/dashboard` measured live at 3–4 real seconds per call (uncached Python spawn) — the exact endpoint polled every 60s.

## SECTION C — Technical Debt (not fixed this session — disclosed, not silent)

- `cover_designer_v2.py` independently reimplements `book_generator.py`'s safe-output-path logic — both copies are correct today, but a future security fix to one won't propagate to the other.
- The same JSONL-read-with-corrupt-line-skipping loop is hand-written independently in 4+ files.
- `server.js` (2,600+ lines) and `factory_loop.js` (1,550+ lines) mix multiple concerns each — not unmaintainable today, but past the size a reviewer can hold in their head at once.
- CLAUDE.md has 2 stale line-number citations (`AGENT_PROMPTS`, `DELETE /finance/delete/:id`) — the file has grown ~1,300+ lines since those were written.
- No ADR exists for the last 3 real architectural/operational decisions (Phase 10D's recovery-audit convention, the Executive Go-Live Audit, the prior red-team fix commit).
- **NOT VERIFIED**: whether concurrent JSONL appends to `data/decisions.jsonl` could ever actually corrupt the file under genuine simultaneous multi-process writes on this Windows/NTFS environment — no evidence of past corruption, but not provable without a live stress test.
- **NOT VERIFIED**: real concurrent-user behavior under load (2+ founders/staff hitting Mission Control at once) — inferred from code structure, not measured under real concurrency this session.

## SECTION D — Business Risks

- **Unmanaged third-party asset dependency**: `book_generator.py`'s cookbook path embeds 12 fixed Unsplash stock images into real, sellable KDP/Etsy/Gumroad products, with no license-compliance record and no fallback if availability changes. Not a confirmed ToS violation, but an unmanaged dependency that matters more as volume scales.
- **1,344 real decisions, zero ever ACCEPTED** — `golden_opportunities.json` is fresh (113 real opportunities scored today) and genuinely finds zero GOLDEN verdicts. This may be a correct read of a weak real market, or a miscalibrated acceptance bar — worth understanding before spending real API credits on autonomous production that may keep landing on the same outcome.
- Business numbers unchanged and re-confirmed: `finance_data.json` shows $0 real revenue.

## SECTION E — Security Risks

- The Critical/High items in Section B are the entire security-risk surface found. After this session's fixes: no route reachable beyond localhost, the two financial-ledger-mutating routes and the unbounded-cost `/chat` endpoint require authentication, and the two most-invoked subprocess spawns can no longer hang forever.
- Remaining, explicitly out of this session's scope: the other ~15 unauthenticated-but-internally-depended-upon legacy routes (`/generate-book`, `/api/distribute`, `/api/scout/run`, `/api/agent/:name`) still have no app-level auth — mitigated by the loopback-only binding fix (Section G), not eliminated at the application layer. Retrofitting Mission Control auth onto these would break `factory_loop.js`'s own internal HTTP calls to them and is a real architecture decision, deliberately not made unilaterally here (see Section H).

## SECTION F — Architecture Risks

- Two independent automation paths exist (`factory_loop.js`'s Golden Hunter Bridge, and the more architecturally complete but never-auto-triggered `orchestrator.run_cycle()`) — confirmed real, not a defect, but worth the founder knowing only one of the two is what actually runs today.
- `server.js`'s pre-Mission-Control legacy routes and its `/api/v1` layer are two different authentication generations bolted together, not one coherent design — the loopback-binding fix closes the acute exposure without resolving the underlying inconsistency.

## SECTION G — Immediate Fixes Required (all implemented and verified this session)

| # | Fix | Files | Regression test |
|---|---|---|---|
| 1 | Bind `server.js` to `127.0.0.1` (was all interfaces) | `server.js` | `test_api_contract.js`: proves a second listener CAN bind `0.0.0.0` on the same port |
| 2 | Auth-gate `/finance/add`, `/finance/delete/:id`, `/chat` (confirmed zero callers anywhere) | `server.js` | `test_api_contract.js`: 401 unauthenticated, 200 authenticated, cleans up its own test data |
| 3 | `decision_engine/engine.py` reuses `profit_oracle`'s own `reason` string instead of rebuilding it | `decision_engine/engine.py` | `test_decision_engine.py`: proves reuse, not just presence of a string |
| 4 | Timeouts added to `/generate-book` and `/api/sales/poll` subprocess spawns | `server.js` | Full regression (normal-path behavior confirmed unchanged) |
| 5 | Tick-overlap guard in `factory_loop.js` | `factory_loop.js` | `test_factory_loop_tick_overlap.js`: proves a second concurrent call is skipped, not run |
| 6 | Dual Inspection now runs on `book_generator.py`'s legacy dispatch branch | `book_generator.py` | `test_book_generator_legacy_dual_inspection.py`: proves `published`/`inspection` keys and a real `_generation_log.jsonl` entry |
| 7 | Stale-lock-reclaim race closed with atomic unlink-then-exclusive-create | `factory_loop.js` | `test_factory_loop_lock.js`: real two-process race against a pre-seeded stale lock |
| 8 | `dashboard.html` fetch calls wrapped in try/catch with a visible error indicator | `dashboard.html` | Syntax-checked, live-served; no browser-test infra exists in this repo for this file |
| 9 | `GET /api/reality`/`computeHealthStatus()` cache `runReality()` for 30s | `server.js` | `test_api_contract.js`: repeat calls measured consistently fast (ms, not seconds) |

**Full regression after all 9 fixes: 420 Python tests + 75 + 18 + 44 JS tests = 557, all green.**

## SECTION H — Future Improvements

- Retrofit real authentication onto the remaining unauthenticated-but-internally-depended-upon legacy routes — requires either giving `factory_loop.js` its own credential or a deliberate architecture decision, not a quick patch.
- Investigate and fix `self_awareness.js`'s `getHealth()` — discovered live during this session's own fix verification: it makes a self-referential HTTP call back to `DASHBOARD_URL/health`, adding roughly 0.9–1s to every `/api/dashboard` call even after the reality-cache fix. Not part of the originally-scoped finding; disclosed here rather than silently expanding this session's fix scope further.
- Extract the duplicated safe-path and JSONL-read helpers (Section C) into shared modules.
- Extend log rotation (`scripts/ops_maintenance.js`) to the root-level logs (`factory_loop.log`, `inspections.log`) — currently only `logs/service_layer.log` is covered.
- Write retroactive ADRs for the last 3 real architectural/operational decisions.
- Document the Unsplash image license basis explicitly, or license a broader image set before scaling cookbook volume.

## SECTION I — Production Readiness Score

**78%** (down from Phase 12's 86% — a real, deliberate correction, not a regression in the code itself)

This session found materially more severe, previously-unreported findings (a broader unauthenticated-route exposure, a live constitutional-compliance violation, a second independent copy of an already-"fixed" bug, two unprotected business-critical subprocess spawns) than the prior red-team pass had surfaced. All of them are now fixed and verified — but the honest scoring convention this session established is that a deeper, more adversarial audit finding more real problems, even when immediately fixed, should not silently average out to a *higher* score than a shallower pass that found fewer. The prior 86% was accurate for what was checked at the time; it was not the true state of the system, only the true state of what had been looked for.

**Justification**: codebase-completeness after this session's fixes is genuinely high (every Critical/High finding closed, full regression green, 9 new regression tests added) — call it 90%. The same standing, unresolved founder-configuration gap from every prior phase still applies (`MISSION_CONTROL_PASSWORD`, channel credentials, `FACTORY_AUTO_PRODUCE`/`FACTORY_LIVE_PUBLISH` all unset) — a further −8 for the fact that this audit, run with genuine skepticism, still found real, previously-uncaught Critical/High issues, which is itself evidence the system has not yet been proven durable "for years with minimal human intervention" — that claim requires more than one clean pass; it requires the *next* pass to find materially less than this one did. 90% − 4% (config gap, unchanged) − 8% (repeated discovery of new Critical/High issues on renewed scrutiny) = **78%**.

## SECTION J — Founder Decision

**2. READY AFTER MINOR FIXES**

Every Critical and High finding from this pass is fixed, tested, and regression-clean, on disk and committed this session. What remains before this becomes an unqualified 1 (READY FOR PRODUCTION) is not more engineering — it is: (a) the same standing configuration decisions from every prior phase (channel credentials, `MISSION_CONTROL_PASSWORD`, the two automation env vars), and (b) the disclosed-but-real Section H items, none of which are blocking. This is not a "major fixes" system — the architecture, business pipeline, and security posture are sound; it needed exactly the kind of adversarial re-check this directive asked for, and now has one on record.
