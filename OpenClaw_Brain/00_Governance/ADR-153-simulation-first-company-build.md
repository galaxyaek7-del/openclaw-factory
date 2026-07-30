# ADR-153 — Simulation-First Company Build

**Date:** 2026-07-30
**Status:** Adopted and built (scoped). One full reference implementation (Affiliate Commerce), not all five named divisions — see "Scope decision" below.

---

## The directive (verbatim)

> Founder Strategic Directive — Simulation-First Company Build
>
> Galaxy Forge is not optimizing for the first real dollar.
>
> Galaxy Forge is optimizing for launch readiness.
>
> From now on, every business division shall be developed to production quality using realistic simulation before public activation.
>
> Core principle: Build → Simulate → Validate → Integrate → Launch
>
> Requirements:
>
> 1. Every commercial division (Affiliate Commerce, Digital Products, SaaS, AI Services, Licensing, etc.) must support a Simulation Mode.
>
> 2. Simulation Mode must use: Real products where legally possible. Real marketplaces. Real prices. Real APIs whenever read-only access is available. Simulated purchases, commissions, payouts and customer flows. Never fabricate real revenue.
>
> 3. Every workflow must be executable end-to-end without requiring live money.
>
> 4. Mission Control shall expose a global Launch Readiness Score for every division: Architecture, Automation, Testing, Compliance, Monitoring, Documentation, Integration, Operational readiness.
>
> 5. Every division must be capable of switching from Simulation Mode to Production Mode through configuration only, without architectural redesign.
>
> 6. Every connector must define: Simulation implementation, Production implementation, Validation checklist, Rollback procedure.
>
> 7. Continue expanding all business divisions in parallel until the company reaches production-grade operational completeness.
>
> Architecture first. Simulation second. Production activation only after the complete system is validated.

## What this directive actually resolves

ADR-152 (the immediately preceding round, same day) flagged a real, unresolved tension: a connector can't be honestly "production-ready" without real credentials, so it concluded "a connector is either fully real... or does not exist as code at all" — a hard binary that left no way to build and exercise an architecture ahead of a real account existing. This directive supplies exactly the missing middle category: **Simulation Mode** — real product data, real prices, real read-only APIs where available, but explicitly and permanently labeled *simulated* purchases/commissions/payouts, never presented as real revenue. This is a genuine, coherent resolution, not a reopening of the Golden Rule fight — item 2's own "never fabricate real revenue" and the directive's closing line ("production activation only after the complete system is validated") both keep ADR-150's real gates fully intact; this directive only adds a way to exercise the pipeline *before* those gates clear.

## The real, already-proven pattern this generalizes

Research before writing any code found this factory already has exactly this discipline, just not under this name:

- `channels/base_arm.py`'s `PublishResult` already carries a real `dry_run: bool` field. `distributor.py` defaults `dry_run=True` at every layer — a real platform push requires an explicit `dry_run: false` in the caller's own JSON.
- `reality.py` (this factory's own "cannot fake these numbers" ground-truth ledger) already explicitly filters: `if event.get("dry_run") is not False: continue` (line 141) — only `dry_run=False` events count as real evidence a product is live.

"Simulation Mode" is this same real mechanism, generalized from "don't really publish" to "don't really transact," given a company-wide name and config switch. No new safety pattern was invented.

## Scope decision for this round

Item 1 names 5 divisions (Affiliate Commerce, Digital Products, SaaS, AI Services, Licensing) and item 7 asks to "continue expanding all business divisions in parallel." Three of the five — **SaaS, AI Services, Licensing** — have zero real code or even a real product concept anywhere in this factory today; `CLAUDE.md`'s own six-track vision doesn't name any of them. Building "Simulation Mode" for a division with no real architecture yet would mean inventing business logic from nothing, which isn't what "Build → Simulate" describes.

This round built: (1) the general Simulation Mode framework, (2) one full reference implementation — **Affiliate Commerce**, the only division with real, mature connector code today — and (3) the Launch Readiness Score, computed honestly for every division with enough real signal (Affiliate Commerce, Digital Products/KDP), with SaaS/AI Services/Licensing shown as real, honest `not_architected` rows. This is a narrower slice than "all divisions in parallel," surfaced explicitly in the plan reviewed with the founder before building (via `EnterPlanMode`), not silently done.

## What was built

**`simulation_mode.py`** (new, repo root — not `lib/`, which is exclusively JS in this codebase): `is_simulation_mode(division)` (per-division env var, e.g. `AFFILIATE_MODE`, defaulting to `"simulation"` when unset — matching the directive's own "simulation second, production only after validation" ordering) and `tag_simulated(record)` (a pure, non-mutating merge of `{"simulation": True}`). One flag per division, never a single global switch — matches `safe_mode.py`'s own real "per-subsystem independence" principle (ADR-135), so flipping one division to production can never silently affect another.

**`affiliate_commerce/simulation.py`** (new) — the reference implementation:
- `simulate_conversion(product_id, ...)` — one real, labeled simulated conversion for a real product from the real catalog (`products.py`), guarded by `is_simulation_mode()` (raises `RuntimeError` if called under `AFFILIATE_MODE=production` — verified live).
- `run_simulation_cycle(...)` — walks the **real** click ledger (`click_tracking.read_clicks()`, ADR-149) and, for each real click, simulates a conversion with a disclosed `ASSUMED_CONVERSION_RATE = 0.02` (a commonly cited affiliate-industry baseline, explicitly labeled as an assumption — this factory has zero real conversions to measure its own rate from). Ties simulation to real recorded activity rather than generating synthetic data independent of it.
- Commission uses a disclosed `ASSUMED_COMMISSION_RATE = 0.03` (Amazon's own long-published baseline "Home" category rate — also explicitly labeled `ASSUMED`, not confirmed against a real account, since none exists).
- Every event writes to its **own, separate** ledger, `data/affiliate_simulation_events.jsonl` — never the real `data/affiliate_clicks.jsonl`, never `finance_data.json`, never `config/reality.json`. `networks.py`/`click_tracking.py`/`products.py` (ADR-149's real production code) are completely untouched — simulation is strictly additive.
- `simulation_funnel_report()` — every field explicitly labeled `"SIMULATED -- not real revenue, not counted in any real financial ledger"`.

**Validation checklist + rollback procedure (item 6), for the Amazon connector specifically** — the one connector real enough to define this for:
- *Simulation implementation*: `affiliate_commerce/simulation.py` (above), `AFFILIATE_MODE` unset or `"simulation"`.
- *Production implementation*: `affiliate_commerce/networks.py`/`click_tracking.py` (ADR-149), already real and live today independent of this ADR.
- *Validation checklist before `AFFILIATE_MODE=production`*: real `AMAZON_ASSOCIATE_TAG` configured (founder's own real account) + at least one real confirmed conversion via Amazon's real postback + sustained real click-through data over a real multi-week window — this is **exactly** ADR-150's own Phase 2 gate, unchanged by this directive.
- *Rollback procedure*: unset/revert `AFFILIATE_MODE` to `"simulation"` — a pure config change, no code deploy, no data migration; the real production code paths were never modified to support simulation, so there is nothing to roll back in them.

**`launch_readiness.py`** (new) — the per-division 8-dimension scorecard, distinct from `executive_score.py`'s own company-wide score. Every dimension is a real, mechanical, disclosed-heuristic check (never a semantic quality judgment): Architecture (real file/module existence), Automation (cites `executive_score.py::_automation()`'s real company-wide signal, honestly labeled as not-yet-per-division), Testing (real `def test_` count in the division's own test files — count only, not a live pass/fail run), Compliance/Documentation/Integration/Monitoring (real text-marker presence checks against `server.js`/`CLAUDE.md`/`mission_control_executive_v1.html`), Operational readiness (a real composite, only when all 7 other dimensions have a real signal — otherwise honestly `not_architected`). SaaS/AI Services/Licensing report every dimension as `not_architected` with the same real reason: no code exists.

**Mission Control**: two new `SERVICE_REGISTRY` entries (`affiliate-simulation-report` — deliberately uncached, since each call should trigger a fresh real simulation cycle; `launch-readiness-score` — cached, a cheap mechanical scan) and corresponding panels in `mission_control_executive_v1.html` (the simulation report titled with a `⚠` prefix, explicitly distinct from the real `affiliate-commerce-status` panel directly above it).

## What is explicitly NOT done this round

No SaaS/AI Services/Licensing code (no real architecture exists for any of them — disclosed, not invented). No change to any real production code path (Amazon connector, distributor arms, real ledgers). No change to ADR-150's real Phase 2/3 gates — Simulation Mode exercises the pipeline *before* those gates clear, never a way around them.

## Validation

`simulate_conversion()`/`run_simulation_cycle()` verified live to raise `RuntimeError` under `AFFILIATE_MODE=production` (the guard actually blocks execution, not just documentation). Verified that a real click ledger with 300 real clicks and a fixed random seed produces real, non-zero simulated conversions, each correctly tagged `simulation: true`, written only to the separate simulation ledger — the real click ledger (`data/affiliate_clicks.jsonl`) and `config/reality.json` untouched in every test run. `launch_readiness_score()` verified live: Affiliate Commerce and Digital Products both return real, non-`not_architected` values across all 8 dimensions; SaaS/AI Services/Licensing return `not_architected` for all 8, with the same honest, real reason. 32 new/extended tests (`tests/test_simulation_mode.py`, `tests/test_launch_readiness.py`, `tests/test_affiliate_commerce.py`'s new `TestSimulation` class) all pass. Full existing test suite re-run, zero regressions.
