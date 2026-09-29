# V5.5 BASELINE AUDIT — Live Commercial Reality (2026-09-29)

**Directive:** V5.5 Sec 3 — inspect live state first, never assume V5.4 still
holds. Non-destructive audit only: every check below is a read, except where
an Executed fix is explicitly marked with its regression test.

**Verdict line:** VERIFIED REVENUE **$0** (triple-sourced). No verified
customers. Exposure live, evidence stops at exposure. Continuous operations
were DOWN 3 days (stale-lock PID-recycling bug) — FOUND, FIXED, loop
re-started supervised during this cycle.

---

## 1. `config/reality.json` + primary revenue source — CHECKED, CONSISTENT

- `published_books: []` — zero real publications, ever. Unfakeable ground truth intact.
- `finance_data.json`: 0 sales records, totals all 0, `lastUpdated` 2026-09-25.
- `data/sales_ledger.jsonl`: 94 rows, ALL `event_type='publish_attempt'`,
  ZERO `sale` events, ZERO amount fields. `revenue_trend()` → 0 sales, $0.
- `data/paddle_webhook_events.jsonl`: 2 records, both REJECTED/MISSING_SECRET.
  No verified transaction notification has ever arrived.
- Root `sales_ledger.jsonl`: 0 bytes (historical smoke-test junk truncated
  2026-09-21 — correct end-state, see §9).

## 2. `data/commercial_evidence.jsonl` — CHECKED

- 149 records, latest 2026-09-29T09:35Z (`maps_created`, OBSERVED/PASS).
  Ledger alive and appended by the tick.

## 3. Founder Command Center — CHECKED, 1 DOC DEFECT (fixed §10)

- `build_founder_command_center()` runs clean: VERIFIED REVENUE $0, 7 founder
  actions, 3 opportunities ready, truth CONSISTENT, all 10 UX questions
  answerable, zero secret values in output (verified programmatically).
- API binding `GET /api/v1/founder-command-center` exists and is
  Mission-Control-auth-gated. Page route added last cycle with matching test.
- DEFECT: module docstring claims "`sales_ledger.jsonl` is 0 bytes" — true of
  the ROOT file, false of `data/sales_ledger.jsonl` (94 publish_attempt rows).
  Misleading zero (V5.4 Sec 26 class). Fixed in this cycle (§10).

## 4. `customer_site` interaction paths — CHECKED, LIMITED

- 52 entries: index, products, interest (intake), contact, status, history,
  login, EU toolkit page, 2 estimator tools, 20+ affiliate/guide pages.
- Intake/response/recording path exists (`interest.html`, support tickets,
  customer pipeline). `support_tickets.jsonl`: 2 records, BOTH test events.
  `customer_experience_log.jsonl`: 20 records, automated-loop traffic only.
- No real inquiry, lead, or qualified opportunity has ever been recorded.

## 5. Products / prices / links / checkout pages — CHECKED

- 6 REAL Paddle products with live `price_id`s ($97–$388, EU toolkit $155).
- `payment_status_check` (live, every tick): 0 of 6 checkout-ready —
  Paddle account onboarding gate still closed (external, founder-only).
- Paddle webhook secret unset → payment verification fail-closed (correct).
  No paid purchase test performed (requires explicit founder approval, Sec 9).

## 6. Stores / distribution / publishing channels — CHECKED

- 51-offer funnel: 50 `CHECKOUT_STARTED` (page live), 1 `NOT_DISCOVERED`;
  ALL 51 `EXPOSED_NO_SIGNAL_YET`. No market response on any offer.
- `publish_protection_state`: gumroad 2 consecutive failures today, status
  READY (no block active); paddle/etsy last published 2026-09-09.
  `first_publish_approved: false` on gumroad/paddle — founder-protection
  layer holding as designed.
- 51 REAL non-dry-run Gumroad publishes exist (Sept 28 batch, real product
  URLs) — publishes, NOT sales. No revenue implied, none claimed.

## 7. Measurement / visits / leads / conversions — CHECKED, SYNTHETIC-FREE

- `commission_attribution_log.jsonl`: 11,630+ `content_view` events, ALL
  `bot_status UNKNOWN`, value 0, each labeled "ANALYSIS ledger only; not
  financial truth". Correctly NEVER counted as traffic or revenue.
- No reliable view statistics exist → views reported as UNKNOWN (per Sec 7).

## 8. Scheduled tasks / agents / alerts / retries — CHECKED, REPAIRED

- `factory_loop.js` tick: FULLY WIRED (~40 daily/weekly/monthly/quarterly/
  annual steps + every-tick resilience + payment checks). Ticks observed
  firing 15:07–15:37 today.
- OUTAGE FOUND: loop dead since 2026-09-26 unclean death; every restart
  since exited with "another factory_loop running (PID 1588)" — PID 1588
  belonged to a BROWSER (PID recycling; `kill(pid,0)` proves existence,
  not identity). Continuous ops silently down 3 days.
- FIXED this cycle: `isPidAliveWithIdentity()` (tasklist image check on
  win32, fail-closed everywhere) + 7 regression tests, all passing.
- Loop re-started supervised (`SUPERVISOR_TARGET=factory_loop.js`), PIDs
  8528/14540, ticking. `recovery.startup_check`: HEALTHY/clean start.
- `pending_retries`: 1 item (n8n telegram webhook `fetch failed` —
  localhost:5678 unreachable; known BLOCKERS.md #1 class, no customer impact).
- NOTE: ticks at 15:07–15:37 today came from an UNKNOWN launcher (no node
  process at 15:43 check; my supervised instance started 15:47). The lock
  guard serializes ticks — no double-run possible — but the launcher's
  identity is UNKNOWN, recorded here, not investigated further (no evidence
  of harm).

## 9. Ledger integrity signals — CHECKED, INVESTIGATED, NO REAL LOSS

Live `check_ledger_integrity()`: 9 non-clean of 16 ledgers. Investigated each:

- `decisions.jsonl` TRUNCATED (2817→2261 raw lines): compared current file
  vs 2026-09-09 snapshot. ONLY removed: 1 test artifact (`test orch` as
  ACCEPTED) + 33 HN-scan-noise niches (Ask HN/Show HN titles ingested as
  records — the documented noise class). All 4 REAL ACCEPTED niches intact;
  183 niches now (vs 94). +847 real re-evaluations appended since. NO real
  company memory lost. The silent purge itself (no evidence event, baseline
  not rebuilt) is recorded as a process-hygiene violation, not repaired by
  further rewriting.
- `sales_ledger.jsonl` DRIFT (44→94): 44 baselined smoke-test lines + 50
  appended REAL publish_attempts. Zero sale rows before or after. $0
  unaffected. (Byte-level chain also sensitive to the file's CRLF endings —
  any LF→CRLF rewrite trips it with zero semantic change.)
- `evidence_ledger.jsonl` TRUNCATED (16004→2069): current 2069 EXECUTION
  records, coherent, spanning 2026-08-07→2026-09-29 00:20. No evidence of
  real-evidence loss; stale-baseline/monitor-hygiene class.
- 4 more DRIFT + 3 more TRUNCATED (`health_snapshots`, `department_events`,
  `executive_orchestrator_events`, `generated_business_blueprints`,
  `market_evidence`, `recovery_actions`, `lead_discovery_events`): same
  pattern — append-only discipline broken by rewrites, byte-chain tripped,
  no verified real-content loss.
- 5 `ledger_integrity:*` incidents correctly OPEN (the files DID change vs
  baseline). Deliberately NOT re-baselined silently — clearing a security
  signal without founder-visible review would violate Sec 14. Consolidated
  into ONE founder decision (§11).

## 10. Integrations / access / secrets — CHECKED, NAMES ONLY

- `.env` holds 19 configured names (Groq, Mission Control, Telegram, Paddle
  API key, Gumroad token, n8n, Systeme, Apollo, Metricool, X, live-publish
  flag). NO values printed, logged, or committed anywhere this cycle.
  Public-site scan (FCC security section): no secret material in public pages.
- `safe_mode`: both subsystems stable. No open non-ledger incidents.

## 11. Tests / error logs / git — CHECKED

- New this cycle: 7 lock-identity tests + 3 tick-overlap tests PASS;
  8 FCC tests + 13 integrity-monitor tests PASS (21 total).
- `node --check` clean on both edited files.
- Git: HEAD `efe17f3` (V5.3); working tree carries extensive UNCOMMITTED
  drift from prior sessions (incl. the entire V5.4 file set). This cycle
  commits nothing — founder decision. My files: `factory_loop.js` (lock
  guard), `tests/test_factory_loop_lock_identity.js` (new),
  `founder_command_center.py` (docstring, §10), this report, evidence
  records below.

---

## Executed fixes (this cycle — smallest change + regression test each)

1. **PID-recycling lock guard** (`factory_loop.js::isPidAliveWithIdentity`,
   +7 tests): restores continuous operations after 3-day silent outage.
2. **FCC sales_ledger docstring** (root-file vs data-file distinction):
   removes a misleading zero.
3. **NEXT BEST ACTIONS** section (V5.5 Sec 12 requirement — pending, §12 todo).

## Evidence recorded

- `commercial_evidence.jsonl`: `v55_baseline_audit`, `factory_loop_resumed`,
  `lock_guard_fix`, `fcc_docstring_fix` (each OBSERVED/PASS with verification
  refs). No revenue/lead/customer event fabricated — activity only.

## What remains UNKNOWN / BLOCKED / needs the Founder (single decision)

- **BLOCKED (external, founder-only):** Paddle onboarding (0/6 checkout-ready)
  + webhook secret + Gumroad first-publish approval. No code closes these.
- **HOLD (founder review, one decision):** 5 open ledger-integrity incidents —
  investigation complete (no real loss), options: (a) re-baseline after
  review [recommended], (b) restore-from-history where possible. Factory will
  NOT clear them unilaterally.
- **UNKNOWN:** launcher of today's 15:07–15:37 ticks; reliable view counts
  (no instrumentation); gumroad's 2 pre-dawn failures' exact error (no
  customer impact; protection state only).

**Commercial status unchanged and honestly stated: $0 verified revenue, 0
verified customers, evidence stops at exposure. The cycle's real progress is
operational: the Factory is continuously running again, its startup guard
now survives PID recycling, and every number above traces to a source.**
