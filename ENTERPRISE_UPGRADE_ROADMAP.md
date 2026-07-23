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
| 1.1 | No process supervisor — an unhandled exception silently kills the entire factory, nothing restarts it | Critical | ☑ commit `96ee731` |
| 1.2 | No uptime monitoring or general-failure alerting — MTTD is unbounded | Critical | ☑ commit `8d32ad0` |

## Phase 2 — Security

**Superseded in scope, 2026-07-23, by the founder's own "Enterprise Security & Cyber Defense Mission"** — a far more detailed 5-phase program than this section originally sketched. The certification findings below (2.1–2.5) remain the real, cited starting evidence; the mission's own Phase 1 (Security Audit) re-verifies and extends them against a much larger checklist (session mgmt, file permissions, path traversal, CSRF, SQLi, prompt injection, dependency/supply-chain, unsafe Python/JS, RCE) before any new module gets built. See the **Security Mission Tracker** below this table for the live, detailed breakdown — that tracker is now the operative one for this phase, not the table alone.

| # | Finding | Severity | Status |
|---|---|---|---|
| 2.1 | Most API routes have zero authentication (~15+ routes, including real LLM spend and financial data) — `POST /api/agent/:name` specifically confirmed as an unauthenticated, unmetered direct proxy to the founder's paid Groq API key | Critical | ☑ commit `489c4bd` |
| 2.2 | CORS fully open, no origin allowlist | High (compounds 2.1) | ☐ |
| 2.3 | Mission Control password check is not timing-safe; no brute-force/rate-limit protection on login | Low | ☐ |
| 2.4 | No TLS/HTTPS anywhere (acceptable while `BIND_HOST=127.0.0.1`, real gap the moment that changes) | Medium (conditional) | ☐ |
| 2.5 | `npm audit`/dependency CVE status | Resolved | ☑ 0 CVEs across 94 real prod dependencies, verified against the real public registry (the earlier failure was the configured mirror not serving the audit endpoint) |
| 2.6 | Pillow 12.2.0 has 10 real, published CVEs (found in Phase 1 Security Audit) | High | ☑ commit `14190a4` |
| 2.7 | Real, confirmed XSS: `index.html:685` interpolates `${b.title}` into `innerHTML` with zero escaping — reachable via the manual book-title form field (self-contained) and via Scout/Pioneer's externally-sourced niche titles (Hacker News, attacker-postable) | High | ☑ commit `780f856` |
| 2.8 | `.env`/`data/decisions.jsonl`/`finance_data.json` carry permissive, inherited default Windows ACLs (readable by `Users`, writable by `Authenticated Users`) — low real risk today (single enabled account on this machine) but no owner-only restriction exists | Medium | ☑ commit `[pending]` — applied live, founder-confirmed |
| 2.9 | `factory_loop.js`'s `sendDesktopNotification()` has an incomplete shell-escaping boundary (escapes single quotes, embedded in a double-quoted PowerShell argument) — real defect, full exploit-chain not traced | Medium | ☑ commit `04664a2` |
| 2.10 | LLM prompt construction interpolates niche/title text with no delimiter between instruction and data, repeated across 4 `groq_chat()` call sites — bounded by strict output-format parsing + Dual Inspection | Medium | ☐ |
| 2.11 | Logout doesn't revoke sessions server-side (stateless tokens valid until natural 12h expiry or a server restart) | Low | ☐ |
| 2.12 | No explicit CSRF token — protection is entirely implicit (SameSite=Lax + confirmed absence of any state-mutating GET route), real and sufficient today but no dedicated layer to catch a future mistake | Low | ☐ |
| 2.13 | Unused, confusingly-named npm package `groq` (unrelated Sanity.io package, zero real call sites, distinct from the real `groq-sdk`) | Low | ☑ commit `14190a4` |

**Full Phase 1 Security Audit report:** https://claude.ai/code/artifact/7cf11021-9fb4-4d3f-8c4c-36eb7e896872 — 2 Critical, 3 High, 4 Medium, 4 Low findings, 14 verified-clean results (no SQLi surface exists at all, zero RCE patterns anywhere in ~40k lines of Python, no command injection, path traversal genuinely defended, 0 npm CVEs, zero install-time script risk, dotenv's earlier supply-chain flag confirmed genuinely isolated), 2 explicitly-flagged not-verifiable items. Recommended repair order in the report: 2.6 and 2.13 first (free, zero-risk one-line fixes), then 2.1 (route auth) before any Security Architecture module gets built, then 2.7/2.9 (contained code fixes), then 2.8/2.3/2.11/2.12.

### Security Mission Tracker (founder directive, 2026-07-23)

Rules, binding: no simulation, no fake security, no fake certificates/compliance/pentest claims, every finding cited with real evidence, explicitly state whatever can't be verified rather than guess, never inflate a score.

| Sub-phase | Scope | Status |
|---|---|---|
| Security Audit | Secrets, API keys, env vars, tokens, auth, authz, session mgmt, file permissions, dangerous subprocess use, command injection, path traversal, XSS, CSRF, SQLi, prompt injection, dependency/package/supply-chain risk, unsafe Python, unsafe JS, RCE risk — every finding with severity, impact, evidence, file, root cause, repair | ☑ Complete — [report](https://claude.ai/code/artifact/7cf11021-9fb4-4d3f-8c4c-36eb7e896872), findings 2.1, 2.6–2.13 above |
| Security Architecture | Security Engine, Secret Manager, Permission Manager, Identity Manager, Access Controller, Security Policy Engine, Audit Logger, Incident Response, Security Dashboard, Threat Intelligence — real modules, only for gaps the audit actually proves exist | ◐ 2.1, 2.6, 2.13, 2.7, 2.9, 2.8 done — 2.3/2.11/2.12 next |
| Hardening | Rate limiting, input validation, output sanitization, secure defaults, least privilege, token expiration, encrypted secrets, secure config, dependency verification, automatic vuln scanning | ☐ Blocked on Architecture |
| Attack Simulation | Controlled, real attempts against API/Mission Control/Publishing/Automation/Executive Board/Discovery/Revenue/Market Hunter — a real pass/fail report | ☐ Blocked on Hardening |
| Continuous Security | Security/Threat/Dependency/Supply-chain/Code review gates every future feature must pass before production | ☐ Blocked on Attack Simulation |

## Phase 3 — Compliance & Privacy

| # | Finding | Severity | Status |
|---|---|---|---|
| 3.1 | Zero compliance documentation — no ToS, no Privacy Policy anywhere | Critical | ◐ Draft ToS/Privacy Policy/Refund Policy built (`eb5f7b4`, `trust/`) — explicitly labeled drafts, real lawyer review still required before they're final |
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

### Infrastructure & HA Mission Tracker (founder directive, 2026-07-23)

Rules, binding: everything based on the real repository, never fake uptime/monitoring, never invent infrastructure that doesn't exist, build only what actually exists, real tests, commit only after verification, zero regressions.

A real audit (not guessed) found this mission overlaps heavily with work already done: Objective 1 (Service Supervisor) is largely built already (Phase 1.1, `scripts/supervisor.js`). Objective 3 (Automatic Recovery) and Objective 7 (DR Validation) are **substantially more real than assumed** — a full "Unified Recovery System" already exists (`factory_state.py`, `recovery/snapshot.py`, `DISASTER_RECOVERY_PLAN.md`) with real exponential backoff, a real tested rollback path (`scripts/rollback_simulate.js`), and real *executed* crash/corruption/data-loss tests, not simulated theory.

| Objective | Real status | Plan |
|---|---|---|
| 1. Service Supervisor | ☑ Built (Phase 1.1, `96ee731`) — restarts on crash, crash-loop guard, structured JSON event log | ◐ Gap: event log ≠ periodic health *report* — small addition |
| 2. Health Checks | ☑ Real memory/CPU/disk/network/storage-integrity checks built, `f050414` — database/queue/worker honestly reported `not_applicable` | Done — see 4.7 |
| 3. Automatic Recovery | ☑ Substantially built (Unified Recovery System, 2026-07-18) — real backoff, rollback, corrupted-state recovery, all tested | ◐ One disclosed gap: failed Groq/publish retries are counted, not yet auto-replayed |
| 4. High Availability ("no single point of failure") | ⊘ Not buildable honestly at this stage — one Windows machine, one process, no redundant infrastructure exists or is appropriate pre-revenue | Document + modestly extend real graceful-degradation patterns already in place (Groq unreachable → honest `Unknown`, n8n down → real Telegram-direct fallback); true multi-machine HA stays gated on real scale (Phase 6/7) |
| 5. Central Monitoring Dashboard | ◐ `dashboard.html` already shows real business health | Extend with new health-check + supervisor signals once built; "Queue/Worker status" reported honestly as N/A — neither exists |
| 6. Unified Logging | ☐ Real gap, already tracked as 4.1 above | Same item — no duplicate tracking |
| 7. Disaster Recovery Validation | ☑ Substantially done — real executed crash/corruption/data-loss tests, `DISASTER_RECOVERY_PLAN.md` | ◐ Gap: no real network-interruption simulation yet |

**Explicitly declined as fabrication, not silently skipped:** a "Database" health check (no database exists — flat JSON/JSONL files), a "Queue system" health check (no message queue exists anywhere in this repo), a "Worker" health check (no worker pool exists — one Express process). These will be reported as real, honest "N/A" states wherever the mission's dashboard/health-report surfaces them, never faked as green.

| # | Finding | Severity | Status |
|---|---|---|---|
| 4.7 | No health checks beyond basic API liveness — no memory/CPU/disk/network monitoring anywhere | High | ☑ commit `f050414` |
| 4.8 | Supervisor produces crash/restart events, not a periodic structured health report | Low | ☐ |
| 4.9 | No real network-interruption disaster-recovery simulation | Medium | ☐ |
| 4.10 | Failed Groq/publish retries are counted and reported but not auto-replayed (disclosed scope limit from the 2026-07-18 Unified Recovery System) | Low | ☐ |

## Phase 5 — Commercial Readiness

| # | Finding | Severity | Status |
|---|---|---|---|
| 5.1 | Zero completed live transactions on any channel — Gumroad has no working token, Paddle blocked on its own onboarding gate | Critical | ☐ |
| 5.2 | No customer trust signals anywhere — no SLA, `security.txt`, responsible-disclosure policy, or status page | Critical | ◐ Trust Center + Security/Responsible AI/Incident Disclosure policies + real contact point built, `eb5f7b4` — no SLA/status page yet (premature at zero real customers) |
| 5.3 | No support channel or refund policy documented | High | ◐ Real contact point + a Refund Policy **draft** built, `eb5f7b4` — needs lawyer review before being final |
| 5.4 | No bookkeeping/financial system (triggers the moment a first real sale closes) | Critical, but gated on 5.1 | ☐ |
| 5.5 | Market intelligence runs on ~4–6 of 11 intended real data sources | High | ☐ |
| 5.6 | Single-vendor, single-model LLM dependency with no fallback; two divergent LLM call implementations | High | ☐ |

### Global Commercial Readiness Mission Tracker (founder directive, 2026-07-23)

Rules, binding: search/verify/integrate before building anything new, never duplicate existing functionality, production-grade code only, commit only after verification.

A real search before building anything found two direct duplication risks and one business-model mismatch, all raised to the founder before writing any code:

| Requested item | Real finding | Decision |
|---|---|---|
| Product Catalog | `product_families/` (a real, mature family/registry/manifest system) already exists | Declined to rebuild — a catalog *view* over the existing real data is the right scope, queued separately, not built this round |
| Pricing Engine | `config/economics.json` already exists — real per-platform royalty tiers, profit floors, delivery costs | Declined to rebuild — same reasoning |
| Invoice generation | Paddle and Gumroad, as the actual payment processors, already generate real, compliant receipts/invoices for every transaction | Declined — a hand-rolled system would duplicate (and likely be less compliant than) what they already provide |
| Enterprise Sales Layer (Demo Mode, ROI Calculator, Enterprise Presentation, sales decks) | `channels/paddle_publisher.py`'s own code comment explicitly notes this factory is *not* built for "invoiced B2B" sales — it sells consumer digital products at $19–200 price points on Etsy/Gumroad/KDP/Paddle | Declined — building this would fabricate a sales motion this business doesn't have |
| Licensing System, Subscription Support, Enterprise Pricing | No real subscription/enterprise customer exists to justify this infrastructure | Declined, same "premature infrastructure" reasoning as Phase 6/7's HA gating |
| Customer Success Layer (onboarding, support workflows, FAQ, tutorials, knowledge base) | Zero real customers exist today — no real support history to document, no real onboarding flow to build for | Declined for now — real triggers to revisit: first real sale, first real support request |
| Legal documents (ToS, Privacy Policy, Refund Policy) | Not a duplication risk, but a real capability limit: an AI-generated legal document presented as final, binding protection would be a real liability, not a real fix | Built as clearly-labeled **drafts** pending real lawyer review, not published as final |

**What was actually built, real subset, founder-approved before starting:** a Trust Center (`trust/index.html`) linking a Security Policy, Responsible AI Policy, and Incident Disclosure Policy (honest engineering disclosures, written from real findings already established this session — no legal review needed, no legal claims made) plus draft Privacy Policy / Terms of Service / Refund Policy (clearly marked, `[FOUNDER: fill in]`-style placeholders for anything requiring real legal/jurisdictional facts this session doesn't have), and a real contact point.

| # | Finding | Severity | Status |
|---|---|---|---|
| 5.7 | Trust Center + 6 real policy pages built (3 honest disclosures, 3 lawyer-review-pending drafts) | — | ☑ commit `eb5f7b4` |
| 5.8 | Product Catalog / Pricing Engine — a real view over existing `product_families`/`economics.json` data, not a rebuild | — | ☐ Queued next |

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

**Commit:** `96ee731`.

---

### 1.2 — Health monitor + real-time crash alerting (2026-07-23)

Resumed after being paused for the Enterprise Security & Cyber Defense Mission, then the Live Competitive Intelligence mission (ADR-093–096) — picked as the next highest-priority *unblocked* engineering task once that mission closed, per the roadmap's own severity ranking (every other open Critical finding in Phases 5–7 is explicitly gated on real load/sales/team growth).

**Implemented:**
- `scripts/supervisor.js`: new `alertCrashRestart()` — every real crash now alerts via Telegram immediately, not just when the supervisor eventually gives up (the real, previously-silent gap this finding named). Bounded by the same pre-existing crash-loop guard.
- `scripts/health_monitor.js` (new): opt-in, explicitly-started long-running process (same pattern as `supervisor.js`) that polls the real `GET /health` endpoint on an interval and alerts via Telegram only on a real status transition — never spams on an unchanged status.

**Real scoping finding:** uptime tracking (`process.uptime()`) and the underlying health checks (`buildHealthReport()`, finding 4.7) already existed — the actual gap was narrow: nothing ever proactively read the health report or alerted on a bad result, and a single isolated supervisor restart was silent.

**Tested:** 23 new tests (`tests/test_health_monitor.js`, 15; `tests/test_supervisor.js`, +1) — see `ADR-097` for the full breakdown.

**Verified:** full JS suite 249/249 real tests green (up from 233), full Python suite reconfirmed 1141/1141 green (unaffected, this piece is JS-only).

**Documented:** `ADR-097`.

**Commit:** `8d32ad0`.

---

### 2.6 + 2.13 — Pillow CVE fix + unused package removal (2026-07-23)

**Implemented:**
- `requirements.txt`: `Pillow==12.2.0` → `12.3.0`.
- `package.json`: removed the unused `groq` dependency (unrelated Sanity.io package, confused with the real `groq-sdk`, zero real call sites).

**Tested/Verified:**
- `python -m pip_audit -r requirements.txt` after the real install: `No known vulnerabilities found` (was 10 real advisories against 12.2.0 before).
- Full Python suite: 1040/1040 passing with Pillow 12.3.0 actually installed, not just pinned on paper.
- `grep -rn "require(['\"]groq['\"])"` confirmed zero real call sites before removal; `npm uninstall groq` run for real; `node_modules/groq` confirmed gone; full JS suite: 205/205 passing.

**Documented:** inline comment in `requirements.txt` explaining the CVE list and why the bump happened.

**Commit:** `14190a4`.

---

### 2.1 — Route authentication (2026-07-23)

**Implemented:**
- `server.js`: new `INTERNAL_SERVICE_TOKEN` (`.env`, generated once, a real random 32-byte hex value — not committed, `.env` is gitignored) and `requireMissionControlOrInternalToken` middleware — accepts either a real Mission Control session or a timing-safe-compared `X-Internal-Token` header. Fails **closed**: if `INTERNAL_SERVICE_TOKEN` is ever unset, these routes require a real session, never a silent unauthenticated fallback.
- Classified every one of the 32 real routes in `server.js` before touching any of them: 4 have a real, working, non-browser caller with no session available (`factory_loop.js`'s own automated pipeline calling `/api/distribute`, `/api/sales/poll`, `/generate-book`; the `01_Market_Scout` n8n workflow calling `/api/scout/run`) — these got `requireMissionControlOrInternalToken`. 14 others (`/api/safety/check`, `/api/agent/:name`, `/api/trends`, `/api/market-analyze`, `/api/qa-check`, `/api/reality`, `/factory-loop/status`, `/good-morning`, `/oracle`, `/inspections`, `/brain`, `/hunter`, `/awareness`, `GET /finance`) have no internal caller at all — plain `requireMissionControlAuth`. Left deliberately public, matching already-established design: the auth gateway itself (`login`/`logout`/`session`), `/health`, `/api/dashboard` (matches `dashboard.html`'s own already-public design, not something this fix unilaterally reversed), and the static SPA shell/login page routes (must be loadable before authentication exists).
- `factory_loop.js`: its 3 real calls to the now-protected routes now send `X-Internal-Token`, read from the same `.env` both processes already load.
- `n8n_workflows/01_Market_Scout.fixed.json`: its `HTTP Request` node now sends `X-Internal-Token: ={{ $env.INTERNAL_SERVICE_TOKEN }}`. **Not yet live** — editing this file doesn't change the running n8n instance; `n8n_workflows/README.md` documents the 2 real manual steps left (make the token available to n8n's own `$env`, re-import the workflow), neither of which this session can do without n8n's own login (the same blocker `BLOCKERS.md` #1 already documents).

**Real UX consequence, not a bug — documented in `CLAUDE.md`:** `index.html` (the main dashboard) has no login flow of its own; it already required having logged in once via `mission_control_login.html` for `/finance/add`/`/finance/delete` (pre-existing, before this fix) because cookies are domain-wide by default. This fix extends the exact same, already-established requirement to more buttons (Generate Book, Scout, etc.) — not a new pattern, the intended effect of actually closing the gap.

**Tested:** `tests/test_api_contract.js` — 3 new tests (a representative plain-auth route via `/oracle`, `/api/agent/:name`'s unauthenticated path specifically — deliberately never exercising its authenticated path in an automated test, since that would make a real, billed Groq call on every run — and the full session-OR-token matrix via `/api/sales/poll`: no auth → 401, wrong token → 401, real token → 200, real session → 200). One real test bug caught and fixed before it could hide behind a false pass: the `/oracle` test initially asserted 401, but a non-`/api/` GET route actually redirects (302) and `fetch()` follows redirects by default, so the test was silently checking the public login page's own 200 instead of the real auth behavior — fixed with `redirect: 'manual'`.

**Verified:** Full JS suite (208 tests, +3 new) and full Python suite (1040 tests) both green. Live, real end-to-end check with the actual `.env` token (not a test double): unauthenticated `POST /api/sales/poll` → 401; with the real token → 200.

**Documented:** `CLAUDE.md` (the `/api/agent/:name` section, the env-var footnote); `n8n_workflows/README.md` (the 2 real remaining manual steps); this entry.

**Commit:** `489c4bd`.

---

### 2.7 — XSS fix: index.html's updateBooksList() (2026-07-23)

Picked up after the Live Competitive Intelligence mission closed (ADR-096) and roadmap 1.2 (ADR-097) — the next-highest-severity unblocked finding, per the Security Mission Tracker's own stated repair order.

**Implemented:** `index.html` gained `escapeHtml()` (identical implementation already shipped in `dashboard.html`/`mission_control.html`, reused verbatim rather than duplicated-with-drift). `updateBooksList()`'s `innerHTML` template now escapes all 5 interpolated fields (`title`, `type`, `theme`, `pages`, `time`) — the audit named `title` specifically, but `theme` for Scout-sourced books (`d.brief.topic`) is equally externally-influenced, so the fix covers the whole template defensively rather than just the one named field. `clearLog()`'s unrelated, always-literal `innerHTML = ''` was confirmed real and left untouched.

**Tested:** `tests/test_index_html_xss_fix.js` (new, 8 tests) — extracts and directly executes the actual shipped `escapeHtml()` function against real `<script>`/`<img onerror>`/quote-breakout payloads, confirming each is neutralized; confirms ordinary titles render unchanged; confirms `clearLog()` untouched.

**Verified:** full regression run — `tests/test_index_html_xss_fix.js` (8/8), `tests/test_trust_center.js` + `tests/test_check_jsonl_duplication.js` (10/10), `tests/test_api_contract.js` (23/23), full Python suite (1141/1141, unaffected). **Honestly incomplete:** live-browser DOM confirmation was attempted 3 times but could not complete — the Claude-in-Chrome extension was not connected in this environment. The executable test above proves the real escaping logic, not browser-DOM rendering semantics specifically; a manual live check is recommended before/shortly after this ships.

**Documented:** `ADR-098`.

**Commit:** `780f856`.

---

### 2.9 — Shell-escaping fix: factory_loop.js's sendDesktopNotification() (2026-07-23)

**Implemented:** replaced the vulnerable single-quote-only escaping + outer-double-quoted `-Command` shell string with a real temp `.ps1` script (never containing `title`/`message`) invoked via `execFileSync(..., ['-File', scriptPath, title, message], ...)` — PowerShell's own documented `-File` contract treats trailing arguments as literal script parameters, never re-parsed as shell/PowerShell syntax. Temp script deleted in a `finally` block after every call.

**Real finding mid-fix:** the first attempt (`-EncodedCommand` + trailing args) failed a real test against a title containing a literal `"` — PowerShell.exe's own trailing-argument parsing after `-EncodedCommand` still misinterprets embedded quotes in ways not fully documented. Found by testing, not assumed; switched to `-File`, which a real test with the same malicious input confirmed handles it as inert literal text.

**Tested:** 4 new tests in `tests/test_factory_loop_notification.js` (real injection attempt with a marker-file check proving no execution occurred, literal-double-quote handling, temp-file cleanup confirmed) — all running the real function on the real machine, matching this file's existing testing philosophy (a Windows toast can't be meaningfully mocked).

**Verified:** `tests/test_factory_loop_notification.js` (7/7), all 7 other real `factory_loop.js`-dependent test files (56+ tests, unaffected), full JS suite (260/260, up from 249), full Python suite (1141/1141, unaffected).

**Documented:** `ADR-099`.

**Commit:** `04664a2`.

---

### 2.8 — Windows ACL hardening (2026-07-23)

**Implemented:** new `scripts/harden_file_acls.js` (opt-in, explicit) — disables ACL inheritance and grants Full control to only the real current user + SYSTEM + Administrators on `.env`/`data/decisions.jsonl`/`finance_data.json`, removing the broad `Users`/`Authenticated Users` grants.

**2 real bugs found and fixed before this shipped** (neither found by inspection — both from actually running the tool against a real file): (1) `whoami` resolves to a different binary depending on invoking shell (Git Bash's own `whoami` silently produced a malformed principal) — fixed by reading `USERDOMAIN`/`USERNAME` env vars directly instead of shelling out; (2) this machine's Windows install is French-localized, so the hardcoded English `"SYSTEM"`/`"Administrators"` names failed outright — fixed with locale-independent well-known SIDs (`*S-1-5-18`, `*S-1-5-32-544`).

**Tested:** 7 tests (`tests/test_harden_file_acls.js`), all against real throwaway temp files — dry-run makes zero changes, broad grant genuinely removed (locale-independent assertion), idempotent, and the file's own owner retains real read/write/delete immediately after hardening.

**Applied live, founder-confirmed** (a real filesystem-permission change on the live factory's own sensitive files, correctly treated as requiring explicit confirmation before acting): dry-run first, then applied for real, then a full live end-to-end check with the real server — `/health` 200, real login 200, real `GET /finance` 200, real `POST /finance/add` 200, real `data/decisions.jsonl` read confirmed. The one real side effect (a $1 test sale) was removed and totals honestly recomputed immediately after.

**Verified:** full JS suite 267/267 (up from 260).

**Documented:** `ADR-100`.

**Commit:** `[pending]`.

---

*(Phase 2 continues from here — 2.3/2.11/2.12 remain, all Low severity, none yet started.)*

### 4.7 — Real infrastructure health checks (2026-07-23)

**Implemented:**
- `lib/health_checks.js` (new): `checkMemory()` (real process + system memory), `checkCpu()` (core count, honestly reports `os.loadavg()` as meaningless on Windows rather than faking `[0,0,0]` as a real number), `checkDiskSpace()` (real Windows `Get-PSDrive` shell-out, explicitly scoped as Windows-only since no POSIX deployment exists to build/verify a cross-platform check against), `checkNetworkReachability()` (real reachability to this factory's actual external dependencies — Groq required, Telegram/GitHub only checked when actually configured/relevant), `checkStorageIntegrity()` (real per-line JSON/JSONL validation — the honest analog to "database health" for an architecture with no database), `notApplicableChecks()` (explicit, honest `not_applicable` for database/queue/worker — none exist, never faked as green).
- Wired into `server.js`'s existing `computeHealthStatus()` (extends the established `checks` object pattern, doesn't replace it) — `GET /health` now returns all of the above alongside the pre-existing checks. Fixed the aggregation logic so `not_applicable` (`ok: null`) entries never count as failing (`!null` is `true` — would have wrongly dragged overall status down for infrastructure this factory was never supposed to have).

**Tested:** `tests/test_health_checks.js`, 16 tests — real values from `checkMemory()`/`checkCpu()` (no mocking, these are cheap and deterministic-enough to assert real shape/bounds on), injectable `run`/`fetchImpl` for the two I/O-bound checks (disk shell-out, network fetch) so failure paths are tested without real flakiness, real temp-file corruption scenarios for `checkStorageIntegrity()` (missing file, valid JSON, corrupt JSON, JSONL with one corrupt trailing line — precisely counted, not treated as fully broken), and an explicit assertion that `not_applicable` checks never fabricate `ok: true`.

**Verified:** every check also run for real (unmocked) against this actual machine — real disk space (155.3GB free of 255GB), real memory/CPU, real network reachability to Groq/GitHub/Telegram (all genuinely up), and `storage_integrity` correctly validated the real `data/decisions.jsonl` (1356 valid lines — the exact clean count from earlier in this session's ledger-pollution cleanup). Live-booted the real server and confirmed `GET /health` returns the full extended shape correctly, with `not_applicable` checks confirmed not affecting overall status. Full JS suite: 224/224 (+16 new). Full Python suite: 1040/1040 green (unrelated to this JS-only change, run for full regression discipline regardless).

**Documented:** `CLAUDE.md`'s Executive Dashboard section now describes the extended `/health` shape and the honest `not_applicable` discipline.

**Commit:** `f050414`.

---

## Global Opportunity Intelligence Mission (founder directive, 2026-07-23)

Full findings and decisions: `ADR-092`. Founder-confirmed before building: extend the existing real opportunity pipeline (`market_hunter.py` → `market_intelligence_core/` → `profit_oracle.py` → `decision_engine/` → `executive_board.py`), not a new parallel "GOIS" system — real search found this mission overlaps substantially with `ADR-026`/`050`/`060`/`066` and prior sessions' "Strategic Investment Layer"/"Business Dossier" work. Discovery domain scope kept to what real data connectors and real execution capability can serve (Developer Tools, Vertical AI, tech-adjacent Professional Services/Education) — the other 14 requested domains (Healthcare, Finance, Government, Insurance, Energy, Construction, Real Estate, Agriculture, etc.) explicitly out of scope, not silently dropped or fabricated.

### 4.11 — Three genuinely new opportunity-scoring dimensions (2026-07-23)

**Implemented:** `profit_oracle.py` gained `_score_time_to_market()` (reuses `product_families.registry`'s real registration state — never re-derives it), `_score_urgency()` (reuses real customer-pain evidence passed via `external_signal`, never a live query from inside scoring), `_score_barrier_to_entry()` (deliberately distinct from `_score_defensibility()` — technical replication difficulty, not competitive intensity). All 3 additive-only, matching the existing `risk`/`confidence`/`defensibility`/`market_signal`/`ai_leverage` pattern exactly — never blended into `profit_score`/`ladder_score`/`accepted`.

**Tested:** `tests/test_opportunity_score.py` (`TestUrgency`, `TestBarrierToEntry` — 7 tests) + `tests/test_ladder_opportunity_score.py` (`TestTimeToMarket` — 4 tests). One real test bug found and fixed before it could hide a false pass: a pre-existing, unrelated quirk in `_score_demand()` (branches on whether `external_signal` is truthy at all, not on which keys it has) confounded an initial "never changes profit_score" assertion — fixed by holding a baseline signal key constant across the comparison.

**Verified:** full Python regression suite, run in full after the change given how widely `profit_oracle.py` is used (`market_hunter.py`, `decision_engine`, `mission_control_api.py`, `orchestrator`, and more).

**Documented:** `ADR-092`.

**Commit:** `c6cfbf6`.

---

## Live Competitive Intelligence Mission (founder directive, 2026-07-23)

Full findings and decisions: `ADR-093`. Founder-confirmed before building: extend `competitor_discovery.py`/`executive_board.py` (never a parallel system) — real search found `competitor_discovery.py` already covers 4 of 6 requested competitor types, and `executive_board.py`'s `analyze_as_cmio()` already has the exact real hook point (`risk_intel["pricing_changes"]`, already honestly disclosed as `Unknown` pending "repeated real runs to compare"). Of 11 requested live-tracking event types, only competitor-appearance and real metric growth (GitHub stars/HN points) have a real data source — the other 9 (funding, acquisitions, hiring, security incidents, regulatory, etc.) get a real evidence-recording path, never auto-detection or fabrication. Of the Threat Engine's 8 dimensions, only 3 are honestly derivable from real data today.

### 4.12 — Historical competitor tracking foundation (2026-07-23)

**Implemented:** `competitor_discovery.py` gained `COMPETITOR_HISTORY_FILE` (real, append-only snapshot preservation on every real refresh), `diff_competitor_snapshots()` (pure, real new/disappeared/growth-signal comparison, never fabricates a trend from one data point), and `is_open_source` per-competitor tagging (a real fact from API source, not a heuristic). `get_or_refresh_competitors()` now attaches a real `changes` key to every fresh result. Isolation (`history_file`) threaded through the full real call chain (`orchestrator.py` → `revenue_pipeline/pipeline.py` → `factory_orchestrator.py`), matching this session's own established `competitor_db_file`/`ledger_path` convention.

**Real bug caught mid-verification, fixed before it shipped:** 2 pre-existing tests in `tests/test_competitor_discovery.py` were about to leak real history writes into the live default file the moment this landed — the same bug class this session already found twice before (`market_hunter.py`'s `decisions_path`, `competitor_db_file` itself). Fixed by threading isolation through those tests too, before running anything for real.

**Tested:** 12 new tests (`tests/test_competitor_discovery.py`) — pure diff-function tests, real history-file integration tests, open-source tagging.

**Verified:** highest-risk existing test files run first given the signature changes, then the full suite. Real `data/competitor_database.json` diffed byte-for-byte clean; `data/competitor_history.jsonl` confirmed never created outside test runs.

**Documented:** `ADR-093`.

**Commit:** `6d30438`.

### 4.13 — Threat Engine: 3 real dimensions, 5 honest Unknowns (2026-07-23)

**Implemented:** `competitor_discovery.py` gained `compute_threat_assessment(snapshot)` — a pure function (no I/O, no network) returning all 8 originally-requested dimensions. 3 are real: `_score_competitor_saturation()` (derived from the real competitor count `discover_competitors()` already found), `_score_market_concentration()` (a real Herfindahl-Hirschman Index computed over each competitor's real GitHub-stars/HN-points weight — honest `Unknown` when no competitor carries either real metric), `_score_new_entrant_trajectory()` (reuses `diff_competitor_snapshots()`'s real `changes` key — honest `Unknown` until a real second refresh exists for a niche, never a trend from one data point). The other 5 (`funding_pressure`, `pricing_pressure`, `technology_disruption`, `regulatory_threat`, `talent_competition`) always return an explicit `Unknown` with the exact real reason (no connector exists for any of them). `get_or_refresh_competitors()` now attaches `threat_assessment` on both the cache-hit and fresh-refresh paths — cheap and pure, so cached results are never left with a stale or missing assessment, and no new network call is added.

**Tested:** 12 new tests (`tests/test_competitor_discovery.py`, `TestThreatAssessment` + `TestGetOrRefreshCompetitorsAttachesThreatAssessment`) — bucket boundaries for saturation, HHI concentration (even distribution vs. one dominant competitor vs. no real metric at all), trajectory rising/declining/stable/unknown, and the full 8-dimension shape.

**Verified:** `tests/test_competitor_discovery.py` (48 tests) green; highest-risk existing suites (`test_orchestrator.py`, `test_master_cycle_production_e2e.py`, `test_decision_engine.py`, 83 tests) green; full Python suite (1074 tests, up from 1062) green; full Node suite (231 real tests) green — the 2 apparent failures were `tests/fixtures/always_crash.js`/`crash_n_times.js`, deliberately-crashing helper scripts for `test_supervisor.js` incidentally matched by an ad-hoc glob, not real test regressions. `data/competitor_database.json`/`data/competitor_history.jsonl` confirmed untouched by the test run.

**Documented:** `ADR-093` (updated).

**Commit:** `f05c33d`.

### 4.14 — Executive Board Integration: 6 lenses, 6-field decisions, 6 connected systems (2026-07-23)

**Implemented:** `executive_board.py` gained `build_strategic_brief()` (Threat Assessment, Opportunity Assessment, Market Intelligence, Financial Impact, Technical Risk, Customer Trust Impact — all reused from already-computed evidence, zero new narrative) and `build_decision_summary()` (Decision, Confidence, Evidence, Risks, Recommended Actions, Follow-up Tasks — mechanically derived from the 10 executives' own real outputs). `convene_board()`'s `include_risk_intelligence` now defaults `True` (was `False`) so this happens automatically, and every meeting now carries both new fields. `enterprise_readiness.run_risk_intelligence_scan()` gained a real `threat_assessment` key reusing ADR-093's Threat Engine. New `get_latest_board_brief()` is the read-only connection point every other system now uses (never convenes a new meeting). Connected to Mission Control (new `get-board-brief` action), Executive Dashboard (`lib/dashboard_data.js`'s new `readLatestBoardMeetingSummary()`), Opportunity Queue (`opportunity_pipeline.py`'s `_annotate()` gained `board_brief`), and Revenue Engine (`revenue_pipeline.pipeline.process_opportunity()` gained `board_brief`, informational only per founder decision — board verdict stays advisory, matching `factory_orchestrator.py`'s existing `advisory_only=True` default). Market Intelligence and Decision Engine were already structurally connected; no new code needed there beyond the lenses/lookup above.

**Real bug caught before commit:** the dashboard reader's first draft hand-rolled its own JSONL parse loop — the repo's own `scripts/check_jsonl_duplication.js` safeguard (Engineering Evolution Mode) caught it as a 3rd duplicate of an already-extracted idiom before commit; fixed to reuse `lib/jsonl.js`'s `readJsonlEntries()`.

**Tested:** 12 new tests across `tests/test_executive_board.py` (+7), `tests/test_enterprise_readiness.py` (+2), `tests/test_opportunity_pipeline.py` (+2, plus isolation added to the whole test class via a new `board_path` fixture — the same isolation-gap bug class this session already found 3 times, caught proactively here before it shipped), `tests/test_revenue_pipeline.py` (+1, plus isolation added to 3 existing calls), `tests/test_dashboard_data.js` (+2).

**Verified:** highest-risk existing suites run first (`test_executive_board.py`, `test_enterprise_readiness.py`, `test_opportunity_pipeline.py`, `test_revenue_pipeline.py`, `test_master_cycle_production_e2e.py`, `test_orchestrator.py`, `test_api_contract.js`, `test_dashboard_data.js`), then the full repository: Python 1084/1084 (up from 1074), Node 233/233 real tests (up from 231). `data/competitor_database.json`/`competitor_history.jsonl`/`board_meetings.jsonl`/`decisions.jsonl` confirmed untouched.

**Documented:** `ADR-094`.

**Commit:** `74866d3`.

### 4.15 — Market Evidence & Alerting layer (2026-07-23)

**Implemented:** `market_evidence.py` gained `COMPETITOR_EVENT_TYPES` (the 9 non-auto-detectable competitor event categories named in ADR-093 — funding, acquisition, hiring spike, security incident, partnership, regulatory change, customer migration, feature release, pricing change), a real citation-required gate in `record_evidence()` scoped only to these 9 types (a real `competitor` name + a real `source_url` are required, or it raises — this factory cannot independently fact-check a third-party claim), `get_competitor_events()`, and an additive `competitor_landscape_events` key in `summarize_niche()`. New `market_alerts.py` module: `detect_auto_alerts()` (reuses `competitor_discovery.py`'s already-computed `changes` diff, zero new computation), `detect_manual_alerts()` (reuses the new competitor evidence categories), `scan_market_alerts()` (the one real write path — dedupes via a stable key, "no alert spam"), `get_active_alerts()` (the one real read path, grouped by severity). Severity/confidence/recommended-action are all deterministic — a new competitor's severity comes from its real `classify_competitor()` category, a growth signal's severity from a real computed percentage change, never a freely-generated judgment.

**Connected to the 4 named systems**, all via the same read-only `get_active_alerts()` pattern `get_latest_board_brief()` (ADR-094) already established: Executive Board (`build_strategic_brief()`'s Threat Assessment lens gains `active_alerts`), Mission Control (new `scan-market-alerts`/`get-market-alerts` actions), Revenue Engine (`process_opportunity()` gains `active_alerts`, informational only), Opportunity Queue (`_annotate()` gains `active_alerts`).

**Tested:** 54 new tests across `tests/test_market_evidence.py` (+8), `tests/test_market_alerts.py` (new, 21), `tests/test_executive_board.py` (+2), `tests/test_opportunity_pipeline.py` (+2), `tests/test_revenue_pipeline.py` (+1 plus isolation added everywhere), `tests/test_master_cycle_production_e2e.py` (isolation added).

**Verified:** highest-risk existing suites run first, then the full repository: Python 1117/1117 (up from 1084), Node 233/233 real tests (unchanged — Python-only piece). All 6 live data files (`competitor_database.json`, `competitor_history.jsonl`, `board_meetings.jsonl`, `decisions.jsonl`, `market_evidence.jsonl`, `market_alerts.jsonl`) confirmed untouched by the test run.

**Documented:** `ADR-095`.

**Commit:** `20f525e`.

### 4.16 — Decision Re-open Trigger (2026-07-23)

**Implemented:** New `decision_reopen.py`: `check_for_reopen_trigger()` (read-only, deterministic materiality rule — 1+ real Critical alert or 2+ real High alerts since the last board meeting, both from `market_alerts.py`, ADR-095), `execute_reopen()` (the only function that re-convenes the board — reuses `executive_board.convene_board()` directly, records one permanent event with timestamp/reason/previous decision/new evidence/confidence delta/new board outcome to `data/decision_reopens.jsonl`), `scan_and_maybe_reopen()` (the one real on-demand entrypoint), `get_reopen_history()` (read-only audit trail). `factory_orchestrator._build_spec()` made public (`build_spec()`) so this module reuses the exact same real decision→spec mapping rather than risking a second, diverging copy.

**Real scoping finding:** a search into "connect to Decision Engine" found `decision_engine`'s `decision_outcomes.jsonl`/`Outcome` type is scoped specifically to real sales matched against decisions (`feedback.py`/`learning.py`'s prediction-accuracy math) — writing a "board reopened" event into that shape would misuse an already well-scoped structure and risk corrupting sale-outcome accuracy. The correct connection is read-only (`factory_orchestrator.find_decision()`/`build_spec()`), not a write.

**Connected to the 5 named systems:** Executive Board (direct reuse of `convene_board()`), Mission Control (3 new actions: `check-decision-reopen-trigger`, `scan-and-maybe-reopen-decision`, `get-decision-reopen-history`), Decision Engine (read-only, see above), Opportunity Queue (`_annotate()` gains `reopen_history`), Revenue Engine (`process_opportunity()` gains `reopen_history`, informational only).

**Audit trail / rollback, scoped honestly:** every reopen event is append-only; the previous board meeting is never mutated (verified byte-for-byte in the test suite). "Rollback" means the prior decision stays fully intact and readable — not undoing an already-executed real production/publish action, which this factory has no mechanism for and none was fabricated.

**Tested:** 54 new tests — `tests/test_decision_reopen.py` (new, 21 tests), `tests/test_opportunity_pipeline.py` (+2), `tests/test_revenue_pipeline.py` (+1 plus isolation everywhere), `tests/test_master_cycle_production_e2e.py` (isolation added).

**Verified:** highest-risk existing suites run first, then the full repository: Python 1141/1141 (up from 1117), Node 233/233 real tests (unchanged). All 7 live data files confirmed untouched.

**Documented:** `ADR-096`.

**Commit:** `2b6f434`.

**This closes the Live Competitive Intelligence mission (ADR-093) in full.** No further pieces are currently queued for this mission.
