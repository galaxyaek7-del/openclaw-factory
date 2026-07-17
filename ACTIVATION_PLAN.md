# OpenClaw Activation Plan

**Date:** 2026-07-17
**Directive:** "Executive Decision — Business Activation Mode"
**Premise, verified not assumed:** the automated pipeline (Market Intelligence → Decision → Product → QA → Distribution → Revenue) is already built, wired, and tested — confirmed independently three separate times this session. Nothing here proposes new engineering. Every item below is either a founder decision, a credential, a configuration change, or a validation step.

---

## 1. Blocking prerequisites (real operation is impossible until these are resolved)

| # | Prerequisite | Current state (verified) |
|---|---|---|
| 1 | A real distribution channel credential | `GUMROAD_ACCESS_TOKEN` unset — confirmed live: `channels.gumroad_publisher.load_token()` raises `ConfigError` right now |
| 2 | Mission Control authentication | `MISSION_CONTROL_PASSWORD` unset — no way to observe or intervene once automation is live |
| 3 | Both automation switches | `FACTORY_AUTO_PRODUCE` and `FACTORY_LIVE_PUBLISH` both unset — the pipeline runs dry-run-only until both are `true` |
| 4 | The live server is running stale code | Real server (PID 1520) still running commit `97362bd` — the Phase 11 dashboard KPIs and every fix since are on disk, not deployed |
| 5 | An unexplained 100% deferral rate | 1,344 real decisions logged, **zero ever ACCEPTED**. `golden_opportunities.json` is fresh (113 opportunities scored today) and genuinely finds zero GOLDEN verdicts. This could mean the market hasn't produced a strong enough niche yet, or the acceptance bar needs a look — flipping the switches without checking risks spending real Groq credits to rediscover the same "no accept" outcome repeatedly |

## 2. Required founder decisions

1. **Which channel to launch with first.** Recommendation: **Gumroad** — it's the most production-ready arm in the codebase (retry-hardened in an earlier phase; no OAuth flow required, just an access token). Etsy requires a manual one-time OAuth authorization and is independently documented as slow/restrictive about approving new developer apps — defer it.
2. **Whether to investigate the 100%-deferral signal before going live**, or accept the current bar and proceed anyway. My recommendation: spend 15 minutes checking this first (see Operational Validation, item 3) — it's cheap, and the alternative is potentially burning real API spend on autonomous cycles that keep landing on the same result.
3. **How closely to supervise the first live cycle.** Recommendation: watch the first real cycle through Mission Control rather than walking away immediately after flipping the switches — not because the code is unproven (it is proven, repeatedly, this session) but because it's the first time it runs against real money and a real external platform.
4. **Accept the existing, already-disclosed business risks as-is**: the Unsplash stock-image license basis (documented, not re-litigated), KDP/Etsy content-ToS exposure (already disclosed, no new information). No new engineering needed here — just founder sign-off that these are known and acceptable at current volume.

## 3. Required credentials and external accounts (founder-only — cannot be created by an engineering session)

| Credential | Source | Needed for |
|---|---|---|
| `GUMROAD_ACCESS_TOKEN` | gumroad.com/settings/advanced (founder's own Gumroad account) | Real distribution |
| `MISSION_CONTROL_PASSWORD` | Founder picks any real value | Authenticated Mission Control / `/api/v1/*` access |
| *(Optional, not blocking)* `N8N_PRODUCTION_WEBHOOK_URL` | Founder's own n8n instance | Production-completion notifications only — code already handles it being unset |

## 4. Configuration tasks (mechanical, once credentials exist)

1. Add `GUMROAD_ACCESS_TOKEN` and `MISSION_CONTROL_PASSWORD` to `.env`.
2. Set `FACTORY_AUTO_PRODUCE=true` and `FACTORY_LIVE_PUBLISH=true`.
3. Redeploy `server.js` (`node scripts/deploy_production.js --confirm`) — picks up the new `.env` values and every fix from Phases 10-12 that isn't live yet.
4. Restart `factory_loop.js` — it's a separate process from `server.js` and reads `process.env` at its own startup; it will not see the new automation-switch values until it's restarted too.

## 5. Operational validation (before trusting the first real cycle)

1. Confirm Mission Control login succeeds with the new password.
2. Confirm `GET /api/v1/docs` and friends now return real authenticated data (not `401`) against the real instance — previously only verifiable against a throwaway instance.
3. **Recommended diagnostic** (cheap, ~15 min, addresses founder decision #2 above): inspect a handful of real, recent, rejected decisions in `data/decisions.jsonl` alongside `profit_oracle.py`'s actual thresholds to see whether the deferrals are a reasonable reflection of weak real opportunities, or whether a specific component is silently near-zero across the board (a wiring issue, not a market reality). I can run this now if you want it before proceeding — it's read-only, no config changes.
4. Confirm `channels.gumroad_publisher.load_token()` actually succeeds with the real token (a real, low-stakes credential check) before relying on it for a real listing attempt.
5. Confirm the recovery-audit log (`data/recovery_actions.jsonl`) captured the redeploy action for real.

## 6. First real production workflow (what "first cycle" means concretely)

`factory_loop.js`'s next tick (once switches are on) → `huntGolden()` picks the current top-scoring real opportunity from `golden_opportunities.json` → `triggerGenerateBook()` calls `/generate-book` for real (real Groq spend) → Dual Inspection runs inside that call — if it fails, the cycle stops there, honestly, and is recorded in `REJECTED_NICHES.md`/`books/_generation_log.jsonl`, which is itself a valid, informative first real cycle → if it passes, `triggerDistribute()` fires automatically, attempting a real Gumroad listing.

## 7. First revenue-generating workflow

Same chain as above, continued: a real Gumroad listing exists → `pollSales()` (every tick) checks Gumroad's real sales API → the moment a real customer buys, `finance_data.json`'s `totalSales` moves off zero for the first time. Worth being explicit: everything up to "a real listing exists" is fully within this system's control and already proven; the last step (a real customer actually buying) depends on real market demand, which no amount of further engineering controls.

## 8. Success criteria proving OpenClaw is operating in the real world

| Criterion | Proves |
|---|---|
| Mission Control authenticates and shows real data | The system is observable, not just running |
| `reality.py`'s `total_published` > 0 | A real product exists on a real channel, not just on disk |
| One full automated cycle completes with no manual intervention (decision → product → QA → distribution attempt) | The pipeline is genuinely autonomous, not just theoretically wired |
| `finance_data.json`'s `totalSales` > 0 | The company has made its first real dollar — CLAUDE.md's own stated golden rule |

---

## Work separation

**Founder work (only the founder can do these):**
- Create/obtain `GUMROAD_ACCESS_TOKEN` from a real Gumroad account.
- Choose `MISSION_CONTROL_PASSWORD`.
- Make founder decisions #1-4 in Section 2.
- Give the explicit go-ahead for the redeploy and for flipping the automation switches — both are standing "requires explicit per-instance approval" actions, not something this session does unilaterally.

**Business work:**
- The channel choice, the deferral-rate question, and the supervision-level decision (Section 2) are business judgment calls, not engineering ones — I can inform them with evidence but shouldn't decide them.

**Operational work (mechanical, I can do this once credentials/go-ahead exist):**
- Add the two `.env` values, flip the two switches, redeploy, restart `factory_loop.js`, run the validation checks in Section 5.

**Engineering work (only where it removes an actual blocker):**
- None is required to reach activation. The one candidate — investigating the 100%-deferral signal (Section 5, item 3) — is a read-only diagnostic, not new code, and only worth doing if you want it before flipping the switches.

---

## Nothing has been implemented yet, per the directive. Waiting on:
1. Your decisions from Section 2.
2. The two real credentials from Section 3.
3. Your go-ahead to run the diagnostic in Section 5.3, and separately, your go-ahead for the redeploy + switch-flip itself.
