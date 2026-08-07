# Launch Checklist — First Real Digital Product

**Companion to `PRODUCTION_READINESS.md`.** This is the concrete, step-by-step operations sequence — not a repeat of that report's audit, just what to actually do, in order.

---

## ⚠️ First: a decision point, not a step

A real Paddle product already exists in the live account: `pro_01kxtd3xzaz0nmfgphk55brhn7`, **"AI-Powered Compliance Automation System for Accounting Firms"**, status `active`. It was created during earlier engineering verification (ADR-077 dispatch proof), not as a deliberate launch decision, and has **zero real transactions** against it.

Before anything else, decide:
- **(A)** Use this existing product as the real first launch (it's already live — no re-creation needed, just confirm the price/description are what you want and finish the checkout-enablement step below), or
- **(B)** Treat it as a test artifact — deactivate/archive it in the Paddle dashboard, and launch a fresh product from one of the other 14 real, Dual-Inspection-passed candidates already sitting in `books/`.

Nothing in this checklist assumes which — pick one before Step 1.

---

## Step 1 — Founder pre-flight (do these once, in any order)

- [ ] **Gumroad**: obtain a real access token, add `GUMROAD_ACCESS_TOKEN=...` to `.env`. No restart needed beyond the next server/CLI invocation reading it fresh.
- [ ] **Paddle**: log into the Paddle dashboard, confirm account onboarding is fully complete and checkout/transactions are enabled (the account has never completed a real transaction — verify this isn't still gated).
- [ ] **n8n**: log into `localhost:5678`, toggle **Active** on `Openclaw_Sensing_Engine` and `02_Sales_Poll`.
- [ ] **Google account security**: enable 2FA on `galaxyaek7@gmail.com`, write a one-page recovery plan (recovery phone/email, one emergency contact).
- [ ] **GitHub**: open the repo's Actions tab, confirm the most recent CI run is green.

None of these need engineering — see `PRODUCTION_READINESS.md` §3 for why each one matters.

## Step 2 — Engineering pre-flight (already verified this session — nothing to run)

- [x] Full test suite green: 661 Python + 170 JS.
- [x] Real orchestrator dry-run cycle executed end-to-end (`market_intelligence`→`decision`→`learning` all `SUCCESS`; `production`/`publishing` correctly skipped under `dry_run`).
- [x] Mission Control's `production-families`, `commercial-execution`, and `recovery` endpoints confirmed accurate against live state.
- [x] Real Groq connectivity confirmed (including a real rate-limit correctly caught by the retry queue).
- [x] Real, read-only Paddle API check confirmed the account/key are live.

If re-verifying before the actual launch day, re-run:
```powershell
python -m unittest discover -s tests -p "test_*.py"
node --test tests/*.js
```
Both must be green before Step 4.

## Step 3 — Choose and confirm the product

If **(B)** from the decision point above: pick one real candidate from `books/` (all already Dual-Inspection-passed). Confirm its title, price, and description read the way you want them to appear publicly — this is the last point where a typo is cheap to fix.

## Step 4 — Dry-run the actual publish path (zero public artifact, safe every time)

Run the real orchestrator with `execute_production=False` (the default) for the chosen niche/product to re-confirm wiring immediately before the real run:

```python
from orchestrator.orchestrator import run_cycle
run_cycle("<the exact niche text>", tier="tier4", ladder="<its real ladder rank>", execute_production=False)
```

Confirm `market_intelligence`/`decision` succeed and `production`/`publishing` report `SKIPPED_NOT_APPLICABLE` — this proves the wiring without spending anything or creating anything public.

## Step 5 — The real publish

**Important correction, verified directly against the code before writing this:** `orchestrator.run_cycle()`'s `execute_production` flag is the **only** dry-run/live switch on this path — `context["dry_run"] = not execute_production` (`orchestrator/orchestrator.py`), applied to *both* the `production` and `publishing` stages together. There is no separate "generate for real but publish as a dry run" toggle in `run_cycle()`'s own interface. Treat `execute_production=True` as the one real go-live switch — this is exactly why Steps 1-4 above exist: everything should already be confirmed *before* this flag is ever set to `True`.

(Separately, `server.js`'s older Scout-button path — `autoDistributeScoutBook()` → `distributor.distribute()` — has its *own*, different gate: the `FACTORY_LIVE_PUBLISH` environment variable. If launching via the Scout button instead of `run_cycle()` directly, that env var is the real switch to check instead, not `execute_production`.)

Only after Steps 1-4 are all checked off:

1. Run the same cycle with `execute_production=True`. This spends a real (tiny) Groq call if content isn't already generated, runs Dual Inspection for real, and — if `decision.status == "ACCEPTED"` — reaches the real `publishing` stage and actually attempts a live marketplace listing.
2. Confirm the returned `PublishRecord` (`commercial_execution.pipeline.build_publish_record()`'s shape, available as `publishing_result.output["publish_record"]` on the returned `ExecutionResult`) shows `publish_status: "ok"` for the intended marketplace(s), and that `marketplace_id` is a real platform ID.

## Step 6 — Post-publish verification

- [ ] Check `commercial-execution`'s Mission Control view — the new product should appear in `recent_publish_attempts` with `ok: true`.
- [ ] Visit the real listing URL (from the `PublishRecord`'s `url` field) in a browser — confirm it looks right to a real buyer.
- [ ] Confirm `data/sales_ledger.jsonl` has a new real `publish_attempt` event for this product.
- [ ] Leave it — do not touch `data/factory_state.json`/`sales_ledger.jsonl` manually; let the real recovery/reconciliation mechanisms run on their own schedule.

## If something goes wrong

- **A publish fails with a real error**: check `commercial-execution`'s `approval_gates` — most failures are a missing/expired credential (`UNAVAILABLE`) or a tripped circuit breaker (`COOLDOWN`, clears itself after a success). The `PublishRecord`'s `recovery_token` traces directly to a real entry in `factory_state.json`'s `pending_retries` if the failure was transient (network/timeout) — it will be retried automatically; no manual replay needed.
- **A duplicate publish is attempted** (e.g. a retried cycle): Paddle's own arm searches for an existing product by `production_id` before creating a new one — it will not create a second real listing for the same product.
- **Power loss / crash mid-publish**: on the next start, `recovery/startup_check.py` classifies the interruption and Mission Control's `recovery` view will show it honestly — check there first, not the raw files.
