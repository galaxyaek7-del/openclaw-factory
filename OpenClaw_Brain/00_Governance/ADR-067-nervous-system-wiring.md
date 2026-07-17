# ADR-067 — Nervous System Wiring: n8n/Telegram, Sensing→Hunter Link, Finance 4-Layer

**Date:** 2026-07-17
**Status:** Adopted, tested (all additions covered by new tests; zero regressions in 445 Python + JS suites — one pre-existing, reproducible-in-isolation flaky test unrelated to this change, see §(a) note).
**Implements:** Step 3 of the 2026-07-17 mission ("nervous system"), per `MASTER_CHARTER.md`/`ADR-065`.

---

## (a) factory_loop → n8n webhook → Telegram

`factory_loop.js`'s Golden Hunter Bridge (`huntGolden()`) now calls a new `notifyGoldenHunterAccepted(niche, opportunityScore)` the moment `opportunity_score()` accepts a real candidate — fire-and-forget, never awaited, never able to delay or fail a tick. It reuses `lib/n8n_notify.js`'s existing generic `notifyN8nProductionEvent()` sender (the same one `server.js`'s production pipeline already uses) via a new `buildGoldenHunterNotifyPayload()` — no second HTTP-call implementation. Points at a new, separate env var `N8N_TELEGRAM_WEBHOOK_URL` (distinct from `N8N_PRODUCTION_WEBHOOK_URL`'s own payload contract), unset by default, same fail-safe-if-unconfigured discipline.

`n8n_workflows/04_Telegram_Notify.prepared.json` is the receiving side: `Webhook` → `Set` (builds the message text) → `Telegram` node. **Not activated in this session** — a Telegram bot token is an external credential (standing execution-authority boundary item #5), which this factory cannot create or hold for itself. `n8n_workflows/README.md` now documents the exact 8 manual steps (create bot via BotFather, get chat id, add n8n Telegram credential, import workflow, set env vars, activate, restart `factory_loop.js`) needed for a real message to land. This was raised and confirmed with the founder before starting Step 3 (`AskUserQuestion`, "Build what I can, hand you the manual step").

**Honest status: built and tested, not yet proven live** — no real Telegram message has been sent this session, because the credential step cannot be done by an AI agent. This is the same category as `03_Production_Notify`'s own still-open activation.

## (b) Sensing Engine output → market_hunter input

Before this fix, `market_hunter.py` only ever *wrote* to `OPPORTUNITIES.md` (`_append_to_opportunities()`); the n8n Sensing Engine workflow (`Openclaw_Sensing_Engine` → `server.js`'s `/api/trends` → `quality_gate()`) already wrote real signals into that same shared file, but `market_hunter.py`'s own hunt never read them back in — `profit_oracle.run_oracle()` scored them later, separately, but `hunt_market()` itself never used them as candidates.

New `_read_sensing_engine_niches()` reads `OPPORTUNITIES.md` entries not carrying market_hunter's own `"market_hunter:"` reason prefix (i.e., anything else — Sensing Engine today) and feeds them into `hunt_market()` alongside the existing seed-category candidates. Each scanned entry is now labeled `"source": "seed"` or `"source": "sensing_engine"`, and the hunt result reports a new `sensing_engine_linked_count` field — real, inspectable evidence the link fired, not just a claim. 6 new tests (`tests/test_market_hunter_sensing_link.py`).

## (c) `/finance` — the 4-layer plan

Interpreted concretely (no prior doc defined this term, so the interpretation is recorded explicitly here rather than assumed silently): finance now reports at **4 layers** —

1. **Per-sale record** (`data.sales`, unchanged).
2. **Per-platform totals** — `totalKDP`/`totalEtsy`/`totalGumroad`, now joined by `totalPaddle` (Step 4's `paddle_arm.py`).
3. **Per-ladder-rank rollup** — new `byLadder` field, summing each sale's `ladder` tag (one of `LADDER_RANKS`, mirrored from `profit_oracle.py`) into the Strategic Production Priority Ladder rank its revenue belongs to. Sales with no `ladder` tag (every sale recorded before this fix) roll up honestly under `kdp_books` — the factory's only real live product line today — never a guessed different rank.
4. **One overall total** — `totalSales` (unchanged in spirit, now includes Paddle).

`POST /finance/add` accepts an optional `ladder` field (defaults to `kdp_books` if omitted or unrecognized, never rejects the request over it). `loadFin()` self-heals a pre-existing `finance_data.json` (saved before this fix) by recomputing `byLadder` from its real sales on first read — same self-healing discipline as the existing corrupt-JSON quarantine path. 4 new tests in `tests/test_api_contract.js` (Paddle + ladder round-trip, unknown-ladder default).

## Impact

- `factory_loop.js`: `notifyGoldenHunterAccepted()`, `N8N_TELEGRAM_WEBHOOK_URL`, wired into `huntGolden()`'s accepted branch.
- `lib/n8n_notify.js`: new `buildGoldenHunterNotifyPayload()`.
- `n8n_workflows/04_Telegram_Notify.prepared.json` (new), `n8n_workflows/README.md` (activation steps documented).
- `market_hunter.py`: `_read_sensing_engine_niches()`, `hunt_market()` now combines seed + sensing-engine candidates, result reports `sensing_engine_linked_count` and per-entry `source`.
- `server.js`: `FINANCE_PLATFORMS` gains `Paddle`, `LADDER_RANKS` constant, `financeDefault()`/`loadFin()`/`saveFin()`/`recomputeFinTotals()` all extended for `totalPaddle`/`byLadder`, `/finance/add` accepts `ladder`.
- New/extended tests: `tests/test_n8n_notify.js` (+1), `tests/test_market_hunter_sensing_link.py` (new, 6), `tests/test_api_contract.js` (+2). Full suite: 445 Python tests green, JS suite green except one desktop-notification test confirmed flaky under full-suite parallel load (passes standalone both before and after this change — a pre-existing environmental issue, not a regression introduced here).
