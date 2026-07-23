# Enterprise Upgrade Roadmap

**Source of truth:** Enterprise Readiness Certification, 2026-07-23 (score 27/100). This document maps every finding from that certification into 7 execution phases and tracks real, evidenced progress against each — not aspirational status.

**Rules of engagement (founder directive, 2026-07-23), binding for every phase below:**
1. Work strictly from the certification's findings — no new, uncited weaknesses invented, no real ones ignored.
2. Sort by business impact and dependency within each phase.
3. One improvement at a time — implement, test, verify, document, commit before starting the next.
4. Never mark a finding fixed without repository evidence (a commit, a passing test, a diff).
5. Never skip prerequisites.
6. Never introduce regressions — full test suite must stay green after every change.
7. The goal is a genuinely stronger company, not a higher number. The certification gets regenerated and compared honestly after each phase, inflated or not.

**Status legend:** ☐ Not started · ◐ In progress · ☑ Complete (with evidence link) · ⊘ Deferred (with reason)

---

## Phase 1 — Critical blockers

*Selection logic: these are the two findings that are prerequisites to trusting any later phase's work. If the process can silently die with no restart and no alert, there is no way to know whether a Phase 2+ security fix, a Phase 4 reliability fix, or anything else is actually running. Everything else critical (auth, compliance, revenue, scale) has its own dedicated phase below and is deliberately NOT duplicated here.*

| # | Finding | Severity | Status |
|---|---|---|---|
| 1.1 | No process supervisor — an unhandled exception silently kills the entire factory, nothing restarts it | Critical | ☑ commit `[pending]` |
| 1.2 | No uptime monitoring or general-failure alerting — MTTD is unbounded | Critical | ⊘ Paused — founder redirected to the Enterprise Security & Cyber Defense Mission (2026-07-23) before 1.2 started. Not abandoned; resumes after the security mission's Phase 1 (audit) lands. |

## Phase 2 — Security

**Superseded in scope, 2026-07-23, by the founder's own "Enterprise Security & Cyber Defense Mission"** — a far more detailed 5-phase program than this section originally sketched. The certification findings below (2.1–2.5) remain the real, cited starting evidence; the mission's own Phase 1 (Security Audit) re-verifies and extends them against a much larger checklist (session mgmt, file permissions, path traversal, CSRF, SQLi, prompt injection, dependency/supply-chain, unsafe Python/JS, RCE) before any new module gets built. See the **Security Mission Tracker** below this table for the live, detailed breakdown — that tracker is now the operative one for this phase, not the table alone.

| # | Finding | Severity | Status |
|---|---|---|---|
| 2.1 | Most API routes have zero authentication (~15+ routes, including real LLM spend and financial data) | Critical | ☐ |
| 2.2 | CORS fully open, no origin allowlist | High (compounds 2.1) | ☐ |
| 2.3 | Mission Control password check is not timing-safe; no brute-force/rate-limit protection on login | Low | ☐ |
| 2.4 | No TLS/HTTPS anywhere (acceptable while `BIND_HOST=127.0.0.1`, real gap the moment that changes) | Medium (conditional) | ☐ |
| 2.5 | `npm audit` / dependency CVE status not verifiable in this environment — real status unknown, not confirmed clean | Unknown — needs verification | ☐ |

### Security Mission Tracker (founder directive, 2026-07-23)

Rules, binding: no simulation, no fake security, no fake certificates/compliance/pentest claims, every finding cited with real evidence, explicitly state whatever can't be verified rather than guess, never inflate a score.

| Sub-phase | Scope | Status |
|---|---|---|
| Security Audit | Secrets, API keys, env vars, tokens, auth, authz, session mgmt, file permissions, dangerous subprocess use, command injection, path traversal, XSS, CSRF, SQLi, prompt injection, dependency/package/supply-chain risk, unsafe Python, unsafe JS, RCE risk — every finding with severity, impact, evidence, file, root cause, repair | ◐ In progress |
| Security Architecture | Security Engine, Secret Manager, Permission Manager, Identity Manager, Access Controller, Security Policy Engine, Audit Logger, Incident Response, Security Dashboard, Threat Intelligence — real modules, only for gaps the audit actually proves exist | ☐ Blocked on Audit |
| Hardening | Rate limiting, input validation, output sanitization, secure defaults, least privilege, token expiration, encrypted secrets, secure config, dependency verification, automatic vuln scanning | ☐ Blocked on Architecture |
| Attack Simulation | Controlled, real attempts against API/Mission Control/Publishing/Automation/Executive Board/Discovery/Revenue/Market Hunter — a real pass/fail report | ☐ Blocked on Hardening |
| Continuous Security | Security/Threat/Dependency/Supply-chain/Code review gates every future feature must pass before production | ☐ Blocked on Attack Simulation |

## Phase 3 — Compliance & Privacy

| # | Finding | Severity | Status |
|---|---|---|---|
| 3.1 | Zero compliance documentation — no ToS, no Privacy Policy anywhere | Critical | ☐ |
| 3.2 | No data classification scheme (public/internal/confidential) | Low (no real PII exists yet) | ☐ |
| 3.3 | No write-time integrity/tamper detection on `data/decisions.jsonl` beyond git history | Low | ☐ |

## Phase 4 — Reliability & Operations

| # | Finding | Severity | Status |
|---|---|---|---|
| 4.1 | No structured logging anywhere — 8 `console.log` calls in all of `server.js`, ad hoc `print()` on the Python side | High | ☐ |
| 4.2 | `orchestrator/retry.py` fires retries with zero real backoff by default despite its own docstring | Medium | ☐ |
| 4.3 | CI exists but does not gate merges — every commit goes directly to `main`, no branch protection confirmed | High | ☐ |
| 4.4 | `CLAUDE.md`'s "no build step, test suite, or linter configured" claim is stale — a real CI + ~1,040-test suite exists | High (trust-in-docs issue) | ☐ |
| 4.5 | One real module import cycle: `product_families ↔ asset_generation` via `pdf_builder.py` (non-fatal today, confirmed by direct import) | Medium | ☐ |
| 4.6 | No CD pipeline; deployment is a manual, tested script; no environment separation | High | ☐ |

## Phase 5 — Commercial Readiness

| # | Finding | Severity | Status |
|---|---|---|---|
| 5.1 | Zero completed live transactions on any channel — Gumroad has no working token, Paddle blocked on its own onboarding gate | Critical | ☐ |
| 5.2 | No customer trust signals anywhere — no SLA, `security.txt`, responsible-disclosure policy, or status page | Critical | ☐ |
| 5.3 | No support channel or refund policy documented | High | ☐ |
| 5.4 | No bookkeeping/financial system (triggers the moment a first real sale closes) | Critical, but gated on 5.1 | ☐ |
| 5.5 | Market intelligence runs on ~4–6 of 11 intended real data sources | High | ☐ |
| 5.6 | Single-vendor, single-model LLM dependency with no fallback; two divergent LLM call implementations | High | ☐ |

## Phase 6 — Enterprise Scale

| # | Finding | Severity | Status |
|---|---|---|---|
| 6.1 | No infrastructure layer — single process, single machine, no containers/orchestration/queue/cache | Critical (gated on real load) | ☐ |
| 6.2 | No horizontal scalability path; synchronous file I/O blocks the event loop | Critical (gated on real load) | ☐ |
| 6.3 | Flat JSON/JSONL files as the datastore — no transactional guarantees for critical paths (finance, decisions) | High (gated on real load) | ☐ |

## Phase 7 — Global Production

| # | Finding | Severity | Status |
|---|---|---|---|
| 7.1 | No SOC2 Type II / ISO27001 certification | Critical (gated on real enterprise pipeline) | ☐ |
| 7.2 | No multi-region / HA deployment | Critical (gated on real scale) | ☐ |
| 7.3 | No formal incident response or on-call rotation (requires a team) | High (gated on team growth) | ☐ |
| 7.4 | No enterprise SSO/RBAC | High (gated on real enterprise customer) | ☐ |
| 7.5 | No factual-accuracy gate on AI-generated content for accuracy-sensitive product lines | High | ☐ |
| 7.6 | Solo bus factor — no succession plan, no second-engineer onboarding doc beyond `CLAUDE.md` | Critical (gated on team growth) | ☐ |

---

## Execution log

*Appended after every completed improvement, in order, each with real evidence — never marked complete without it.*

### 1.1 — Process supervisor + crash resilience (2026-07-23)

**Implemented:**
- `server.js`: real `uncaughtException`/`unhandledRejection` handlers — log full error+stack to `server_crashes.log` (gitignored, same flat convention as `factory_loop.log`), best-effort Telegram alert reusing the already-tested `lib/telegram_direct.js` (never a new alert channel), exit non-zero.
- `server.js`: real `SIGINT`/`SIGTERM` handlers — clean exit 0, distinguishable from a crash.
- `scripts/supervisor.js` (new): opt-in wrapper (`node scripts/supervisor.js` instead of `node server.js`) — restarts the child on a real crash with backoff, a crash-loop guard (default: gives up after 5 restarts in 60s and alerts via Telegram instead of looping forever), forwards shutdown signals to the child.
- **Real bug found and fixed along the way, not planned:** `factory_loop.js`'s own `SIGINT`/`SIGTERM`/`uncaughtException`/`unhandledRejection` handlers were registered unconditionally at module load time, not gated behind `require.main === module` the way its `main()` already was. Since `server.js` requires `factory_loop.js` for two unrelated functions, it silently inherited factory_loop's signal handling — meaning stopping `server.js` could release *factory_loop's own PID lockfile* from a process that isn't factory_loop, and factory_loop's handler (registered first) pre-empted server.js's own new handler entirely, running before it ever got a chance to fire. Fixed by gating those registrations behind the same `require.main === module` check.

**Tested:** `tests/test_server_crash_handlers.js` (4 tests — real `uncaughtException`, real `unhandledRejection`, real `SIGINT`, real `SIGTERM`, each spawning the actual `server.js` with a test-only fault-injection env var, never reimplementing the handler logic) and `tests/test_supervisor.js` (2 tests — real restart-then-succeed, real crash-loop-guard cap) — all 6 passing. One real, documented Windows platform limitation found and worked around correctly: `child_process.kill()` on Windows hard-terminates rather than delivering a graceful signal `process.on()` can intercept, so shutdown-handler correctness is tested via a real `process.emit()` test hook instead of an OS-level kill, decoupling "does my handler logic work" from "does this specific OS deliver signals gracefully."

**Verified:** Full JS suite (205 tests) and full Python suite (1040 tests) both green after the change. Live manual smoke test: `node scripts/supervisor.js` supervising the real `server.js` — real boot, real `/health` 200, real crash-and-restart cycle observed in `supervisor.log`. One real regression caught and fixed mid-flight: a stdout-flush-before-`process.exit()` race (well-known Node pitfall) that silently dropped the shutdown log line on piped/non-TTY stdout — fixed via the documented `write()`-with-callback pattern. One false-positive regression (`test_factory_loop_lock.js`'s concurrency test failed once in a combined run, passed 4/4 times afterward including in isolation) correctly identified as pre-existing test flakiness, not caused by this change, before being dismissed.

**Documented:** `CLAUDE.md`'s "Running the project" section now describes the supervised-start option alongside the unchanged manual one.

**Commit:** pending (this entry written just before commit).

---

*(Phase 1.2 — uptime monitoring — paused here per founder redirect to the Enterprise Security & Cyber Defense Mission. Resumes after that mission's Phase 1 audit lands.)*
