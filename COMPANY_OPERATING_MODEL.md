# OpenClaw Company Operating Model

**Date:** 2026-07-17
**Directive:** "Executive Mission 002 — OpenClaw Operating System"
**Method:** describes the real, current mechanics verified this session — not an aspiration. Where the real mechanism differs from what would be ideal, that gap is stated explicitly rather than smoothed over.

---

## How opportunities enter the company
`market_hunter.py`/`profit_oracle.py` score real candidate niches (keyword-based; optionally with real Hacker News/GitHub signal, rarely available for this product category — see `CAPABILITY_MAP.md` M1) into `golden_opportunities.json`. Separately, `POST /api/scout/run` lets a human trigger a real, one-off Groq-brief-driven scan on demand.

## How decisions are made
**Two real, inconsistent paths exist today** (`CAPABILITY_MAP.md` C2/C2b) — only one runs automatically. `factory_loop.js`'s live path: `profit_oracle.opportunity_score()` against a fixed tier4 floor (81.25 raw) — **verified this session to have never once passed, in 121 real checks.** The richer path (`decision_engine`/`orchestrator`, AI-CEO-verdict-based) only runs via a manual Mission Control action. A real, honest gap: this company currently has no live path that has ever produced a real "yes."

## How work is prioritized
`pickTopGoldenOpportunity()` — the single highest `profit_score` among non-SKIP-verdict candidates, evaluated fresh each `factory_loop.js` tick (~every 10 minutes while running).

## How products are built
`book_generator.py`, triggered by `/generate-book` (real Groq calls), gated by a real, unconditional quality gate (`quality_gate()`) before any content generation begins.

## How products are reviewed
`inspectors.py`'s Dual Inspection — technical (PDF/cover integrity) and commercial (`profit_score`, `butter_price` floor, duplicate/rejection checks) — runs unconditionally on every real generation as of this session's fix to the one previously-bypassed legacy branch. A product is never `published: true` unless both pass.

## How products are published
`distributor.py` routes a QA-passed product to a registered channel arm (Gumroad/Etsy/Payhip — all three registered in code; none credentialed today). Every publish attempt is dry-run unless `FACTORY_LIVE_PUBLISH=true` and a real credential exists.

## How revenue is measured
`channels/ledger.py` records every real distribution attempt (dry-run or live); `pollSales()` (every tick) checks each configured channel's real sales API; `finance_data.json` holds the real, currently-$0 totals.

## How knowledge is retained
`OpenClaw_Brain/00_Governance/`'s 64 ADRs (as of this session), `CLAUDE.md` (kept current, spot-checked and corrected this session), `GROWTH_LOG.md` (daily self-awareness), and this session's own new artifacts (`EXECUTIVE_BACKLOG.md`, `ACTIVATION_PLAN.md`, `CAPABILITY_MAP.md`, this document) — all real, checked-in, version-controlled files, not conversation-only knowledge.

## How failures become improvements
A rejected niche is written to `REJECTED_NICHES.md` (a real circuit breaker — a 7-day cooldown before the same niche is tried again); a corrupted/quarantined book goes to `QUARANTINE.md`. `self_awareness.js`'s daily assessment (`GROWTH_LOG.md`) computes a real day-over-day diagnosis. This session added a further layer: every zero-assumption/red-team audit this session ran produced a permanent artifact (a fix, a test, or — when a finding was a business/design question, not a bug — an explicit entry in `EXECUTIVE_BACKLOG.md`'s Founder-only tier) rather than a one-off conversation.

## How the company continuously evolves
`factory_loop.js`'s tick loop is the only "continuous" mechanism that exists — and it only runs while a human has started it (`CLAUDE.md`'s deliberate "no scheduler" principle). Real evolution this session came from a different mechanism: repeated adversarial self-audit (7 independent verification passes across the zero-assumption audit alone) surfacing real defects and gaps, each closed with a permanent fix, test, and documentation entry — not from the automation loop itself, which has been running continuously since 2026-07-15 without producing a single accepted decision.

## The honest summary
Every mechanical stage of this company — intelligence, creation, review, publishing, revenue tracking, observability, recovery — is real, tested, and (as of this session) secured and performant. **The company has never once made a real accept decision**, and the two live blockers (M1: no real-evidence source fits this product category; M2: no distribution credential) are independent of each other and independent of every engineering improvement made this session. This operating model describes a company that is mechanically ready and has not yet, in its real operating history, produced a single accepted opportunity.

---

## Update 2026-07-18 — M1 and M2 both materially changed, one section above is now stale

The founder directed a Strategic Production Priority Ladder pivot (`MASTER_CHARTER.md`, `ADR-065`) the day after this document was written, explicitly firing `ADR-034`'s trigger. This changed the two facts the summary above rests on:

- **"How decisions are made" is now partially superseded.** A new gate, `profit_oracle.ladder_opportunity_score()` (`ADR-066`), was wired into `factory_loop.js`'s live automatic tick (`ADR-070`) — weighting recurring revenue + reusability, not the old fixed tier bar. **Verified live: 5 real opportunities have now been ACCEPTED** — the company's real accept rate is no longer 0%. **However — the OTHER decision surface this document already flagged as inconsistent (C2/C2b, `decision_engine`/`orchestrator`) was NOT updated** — `decision_engine/engine.py` still calls the old `opportunity_score()`. Mission Control's Decision Queue and the automatic tick can now show genuinely different pictures. See `ENGINEERING_ASSESSMENT_20260718.md` Critical Issue C1 — this is the single most important open item as of this update.
- **"How products are published" gained a fourth arm.** `channels/paddle_arm.py` (`ADR-065`/`074`) is registered alongside Gumroad/Etsy/Payhip. Unlike those three, Paddle's account is real, approved, and **live**: real product + price creation confirmed working via the actual API. The remaining blocker (a real checkout link) is Paddle's own account-onboarding gate, not a missing credential or code gap — materially narrower than M2's original "no credential exists at all" framing.
- **A new founder-notification channel is live**, addressing a gap this document didn't have a section for: real Telegram messages (Arabic, per founder instruction) now fire on real accepted opportunities, verified end-to-end through the actual n8n workflow, not just a direct API test.

Everything else in this document (creation, review, revenue tracking, knowledge retention, how failures become improvements) is unaffected and still accurate.
