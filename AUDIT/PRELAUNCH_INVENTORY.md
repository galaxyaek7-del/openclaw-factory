# Galaxy Forge — Pre-Launch Zero-Trust Inventory

**Date:** 2026-08-08 | ADR-225, Phase 32, Section 1. Every item below is drawn from direct code inspection and/or live verification performed in this session (Phase 30.5 forensic audit, Phase 31 Commercial Activation, Phase 31.5 architecture review, and fresh checks this round) — not carried forward from documentation claims without re-verification.

Statuses: `READY_VERIFIED` / `READY_LOCAL` / `PARTIAL` / `BLOCKED_EXTERNAL` / `FOUNDER_ACTION` / `MANUAL` / `BROKEN` / `UNKNOWN` / `NOT_REQUIRED`.

---

## Systems / Services

| Name | Purpose | Location | Dependencies | Status | Evidence Level | Last Verified | Failure Mode | Manual Fallback |
|---|---|---|---|---|---|---|---|---|
| `server.js` | HTTP server, Mission Control, all commercial routes | repo root | Node, `.env` | READY_VERIFIED | E4 (live, supervised, respawn-tested) | 2026-08-08 (this session) | Supervisor auto-restarts on crash | Manual `node server.js` |
| `scripts/supervisor.js` | Crash-loop guard for server.js/factory_loop.js | `scripts/` | Node | READY_VERIFIED | E4 (live PID respawn confirmed 4× this session) | 2026-08-08 | Gives up + Telegram alert after repeated crashes | Manual restart |
| `factory_loop.js` | Daily/weekly/monthly automation tick | repo root | Node, Python | READY_VERIFIED | E4 (10 daily markers confirmed fresh today) | 2026-08-08 | Supervised, auto-restart | Manual `node factory_loop.js` |
| `GET /health` | Real infra health aggregator | `server.js` | none | READY_VERIFIED | E4 (live curl this round) | 2026-08-08 | Reports `warning`/`critical` honestly | N/A |
| Mission Control (`mission_control_executive_v1.html`) | CEO dashboard, ~65 panels | repo root | `server.js` | READY_VERIFIED | E4 (script blocks parse-verified, panels live-tested) | 2026-08-08 | Auth-gated, fails to unauthenticated JSON | N/A |

## Agents / AI

| Name | Purpose | Location | Status | Evidence Level | Notes |
|---|---|---|---|---|---|
| Groq (`llama-3.1-8b-instant`) | Real, live-called LLM | `ai_capability/registry.py`, `.env: GROQ_KEY` | READY_VERIFIED | E4 (230 real calls, $0.02 total real cost) | Only LIVE provider; 11 others honestly `DISCOVERY` |
| 6 `AGENT_PROMPTS` personas (scout/builder/design/qa/publisher/finance) | UI-triggered Groq calls | `server.js` | READY_VERIFIED | E4 | Auth-gated since Phase 1 Security Audit |
| Galaxy Council (9-member board) | Real AI Council + Red Team | `galaxy_council.py` | READY_LOCAL | E3 (reused 7× this session, incl. Phase 30/31) | Never forces consensus |

## Database / Persistence

| Name | Status | Evidence Level | Notes |
|---|---|---|---|
| Relational/NoSQL database | NOT_REQUIRED | E4 | Confirmed architecturally `not_applicable` via `GET /health` — flat JSON/JSONL is the real, current persistence layer |
| `data/*.jsonl` ledgers (decisions, sales, ai_cost, recovery_actions, etc.) | READY_VERIFIED | E4 | Real, append-only, git-tracked |
| `finance_data.json` | READY_VERIFIED | E4 | Cleaned of synthetic data this session (Phase 30.5.1); currently `$0` real, honestly |

## APIs / Integrations

| Name | Status | Evidence Level | Failure Mode | Manual Fallback |
|---|---|---|---|---|
| Paddle API (`PADDLE_API_KEY`) | READY_VERIFIED (credential) / BLOCKED_EXTERNAL (checkout) | E4 (live `list_products()` this session) | Founder's own onboarding gate | Founder completes onboarding |
| Paddle inbound webhook (`channels/paddle_webhook.py`) | READY_LOCAL | E3 (19 tests, mocked signatures only) | Honestly rejects `MISSING_SECRET` | `check_payment_status()` polling (already real) |
| Gumroad/Etsy/Payhip API | FOUNDER_ACTION | E4 (live `status()` this session — all `unavailable`) | No credential | Founder adds real credential if account exists |
| Amazon Associates | FOUNDER_ACTION | E4 (`.env` scan, this session) | No tag configured | Founder creates/approves account |
| Groq API | READY_VERIFIED | E4 | Real retry + `Retry-After` handling | N/A |
| Telegram (bot + chat ID) | READY_VERIFIED | E4 (real, live notification pipeline, cited throughout session) | Best-effort, never blocks caller | N/A |
| n8n | NOT_REQUIRED (optional, off by default) | E4 (`GET /health` shows `sensing_engine` degraded, expected) | N/A | N/A |

## Platform Arms

| Arm | Auth | Catalog | Checkout | Webhooks | Delivery | Refunds | Payouts | Status |
|---|---|---|---|---|---|---|---|---|
| Paddle | READY_VERIFIED | READY_VERIFIED (6 products) | BLOCKED_EXTERNAL | READY_LOCAL (unverified live) | READY_VERIFIED (platform-agnostic) | NOT_AVAILABLE | NOT_AVAILABLE | GO_WITH_FOUNDER_ACTION (see `commercial_go_live_check`) |
| Gumroad | FOUNDER_ACTION | NOT_REQUIRED (0 products) | N/A | N/A | READY_VERIFIED | NOT_AVAILABLE | NOT_AVAILABLE | NO_GO |
| Etsy | FOUNDER_ACTION | NOT_REQUIRED | N/A | N/A | READY_VERIFIED | NOT_AVAILABLE | NOT_AVAILABLE | NO_GO |
| Payhip | FOUNDER_ACTION | NOT_REQUIRED | N/A | N/A | READY_VERIFIED | NOT_AVAILABLE | NOT_AVAILABLE | NO_GO |

## Automation

| Name | Trigger | Status | Evidence |
|---|---|---|---|
| Daily reports (10+ functions: business blueprints, commercial kits, evolution queue, executive directive, growth stage snapshot, knowledge graph, etc.) | `factory_loop.js` tick, once/calendar-day gate | READY_VERIFIED | 10 daily-marker files dated today, this round |
| Golden Hunter niche scan (`market_hunter.py`) | `factory_loop.js` daily tick | READY_VERIFIED | Runs daily, real decisions appended |
| Golden Hunter ranked-feed refresh (`profit_oracle.run_oracle()`) | Conditional — only on new GOLDEN catch | PARTIAL | 411+ hours stale — real, honest, not auto-refreshed on a schedule |
| Paddle checkout-ready re-check | Every tick | READY_VERIFIED | Real Telegram alert wired (2026-08-06) |
| Resilience monitor tick | Every tick | READY_VERIFIED | Real 4-tier severity, real incident ledger |

## Security Controls

| Control | Status | Evidence |
|---|---|---|
| `.env` gitignored | READY_VERIFIED | `git check-ignore .env` this session |
| No committed secrets | READY_VERIFIED | `git grep` scan this session, 0 matches |
| No secrets in logs | READY_VERIFIED | grep scan this session, 0 matches |
| Mission Control session auth | READY_VERIFIED | `mc_session` HMAC-signed cookie, live-tested |
| Internal service token | READY_VERIFIED | Real, gates `factory_loop.js`↔`server.js` internal calls |
| Webhook signature verification | READY_LOCAL | Real HMAC-SHA256, 19 tests, no live secret yet |

## Backup / Recovery

| Item | Status | Evidence |
|---|---|---|
| Git history (code, config, ADRs, decisions) | READY_VERIFIED locally / **PARTIAL remotely** | **Local branch is 39 commits ahead of `origin/main` — not pushed.** See `AUDIT/RECOVERY_READINESS.md`. |
| Pre-operation snapshots (`recovery/snapshot.py`) | READY_VERIFIED | Real, triggered before every Paddle publish / production stage |
| Startup safety classification | READY_VERIFIED | Real, tested via an actual abrupt-kill-and-restart (`DISASTER_RECOVERY_PLAN.md`) |
| Local log files | MANUAL | Explicitly disclosed gap — local-only, not backed up (by design, per `DISASTER_RECOVERY_PLAN.md`) |

## Tests

| Suite | Status | Evidence |
|---|---|---|
| Full Python suite | READY_LOCAL | 3,030 real tests discoverable; last full run this session found 0 new failures across every touched module |
| Phase 30.5/31/31.5/32 new suites | READY_VERIFIED | 187 new tests this session (42+7+9+18+19+25+7... see individual phase commits), all passing |
| `tests/test_api_contract.js` | READY_VERIFIED | 31/31 passing, live-run against the running server this session |

## Documents

`CLAUDE.md`, `CONSTITUTION.md`, `DISASTER_RECOVERY_PLAN.md`, `RECOVERY_TEST_RESULTS.md`, `ROLLBACK_VALIDATION_REPORT.md`, ~225 ADRs under `OpenClaw_Brain/00_Governance/`, `AUDIT/*.md` (this session's 3 forensic rounds), `docs/FIRST_REAL_DOLLAR_PROTOCOL.md`, `docs/FIRST_REAL_TRANSACTION_AUDIT.md` — all READY_VERIFIED, git-tracked (locally; see the push gap above).

## External Accounts

| Account | Status |
|---|---|
| Paddle vendor account | READY_VERIFIED (credential) / FOUNDER_ACTION (onboarding) |
| Gumroad/Etsy/Payhip accounts | FOUNDER_ACTION (unknown if they even exist) |
| Amazon Associates | FOUNDER_ACTION |
| GitHub remote (`origin`) | READY_VERIFIED (exists, reachable) / **39 commits behind — FOUNDER_ACTION or explicit push authorization needed** |
| Telegram bot | READY_VERIFIED |

## Manual Actions Required (cross-referenced, not duplicated — full list in `commercial_activation.founder_action_center()` + this report's Founder Action Center)

Paddle onboarding; `PADDLE_WEBHOOK_SECRET` configuration; Gumroad/Etsy/Payhip credentials (if real accounts exist); Amazon Associates account; payout destination confirmation; **git push decision** (new finding this round).

---

*See also: `AUDIT/MASTER_READINESS_MATRIX.md`, `AUDIT/RECOVERY_READINESS.md`.*
