# Galaxy Forge — Phase 38: Golden Hunter Opportunity Rotation & Pursue/Abandon Engine Report

**Date:** 2026-08-08 | **ADR:** ADR-233 | **Directive:** "Golden Hunter Opportunity Rotation & Pursue/Abandon Engine"

Not an outreach phase, not a sales activation phase, not a revenue phase. Opportunity-selection and capital-allocation only.

---

## EXECUTIVE_SUMMARY

Built `opportunity_rotation_engine.py` — the real, upstream "should we keep spending discovery attention on this specific opportunity at all" lifecycle, sitting before any existing sales-funnel machinery even begins. Audit before build found most real signal sources already exist (`goos.py::rank_build_candidates()` already ranks every real candidate niche across all 6 product ladders; `commission_engine.py`'s real pipeline-transition pattern was reused verbatim for a new vocabulary) — this round's genuine contribution is the lifecycle state machine, the 14-dimension Golden Hunter Decision Model, PURSUE/WATCH/ABANDON/ROTATE classification, repeated-failure penalty, resurrection rules, and cross-opportunity comparison. Two real internal-consistency bugs were found and fixed *during this round's own live validation run*, not after.

## CURRENT_OPPORTUNITY_STATUS

1 real opportunity under active lifecycle tracking: `CO-n8n-affiliate`, status **WATCH**.

## CO_N8N_AFFILIATE_STATUS

**WATCH / INSUFFICIENT_EVIDENCE.** Real lifecycle recorded: `DISCOVERED → EVIDENCE_CHECK → QUALIFICATION → WATCH`, citing real Phase 37B/37C evidence (2 real live discovery rounds, 3 sources, 0 qualified, all real evidence STALE). Reopen condition: `REOPEN_ONLY_IF_NEW_FRESH_EVIDENCE_APPEARS` (real, recorded). Not deleted, not abandoned — all Phase 37 evidence preserved in its real, append-only lifecycle history (`opportunity_rotation_engine.opportunity_memory("CO-n8n-affiliate")`).

## NEW_OPPORTUNITIES

Real, passive discovery via `goos.py::rank_build_candidates()` (not constrained to n8n/automation, per Section 12): **98 total real candidates** across all 6 product ladders, 10 in the real `build_next` bucket, 0 never-evaluated (every real seed candidate has already been evaluated at least once via `decision_engine`), 0 real ACCEPTED portfolio company-wide.

## TOP_10_RANKING

By real `goos_advisory_score` (an already-real, already-cited score from `profit_oracle`'s ladder scoring, not computed by this round):

| # | Score | Prior Status | Candidate |
|---|---|---|---|
| 1 | 72.8 | DEFERRED | Printable monthly planner, back-to-school (Arabic) |
| 2 | 72.8 | DEFERRED | Printable monthly planner, back-to-school (English) |
| 3 | 72.8 | DEFERRED | **AI-powered compliance automation subscription system for accounting firms** |
| 4 | 72.2 | DEFERRED | Cuttable SVG design templates, back-to-school (Arabic) |
| 5 | 72.2 | DEFERRED | Cuttable SVG design templates, back-to-school (English) |
| 6 | 71.8 | DEFERRED | EU AI Act Compliance Document and Template Toolkit (`reusable_assets` ladder — this factory's one real shipped product) |
| 7-10 | 71.4 | DEFERRED | 4 more printable-planner variants (women/kids/teens) |

**Honest disclosure**: the raw top-1 is a low-value printable template — exactly what Section 12's own strategic doctrine says to deprioritize ("Books and low-value templates remain secondary"). It only wins the raw score tie-break by stable-sort order, not by genuine superiority. #3 (a real, recurring, defensible B2B subscription opportunity) is tied at the same real score and is the doctrine-aligned pick.

## TOP_3

1. Printable monthly planner (template, Lane A-adjacent, low strategic value)
2. Printable monthly planner, alternate phrasing (same real candidate, different query match)
3. **AI-powered compliance automation subscription system for accounting firms** (Lane B, recurring, higher strategic value)

## CURRENT_BEST_OPPORTUNITY

By the fixed, real ranking mechanism (`real_composite_score` as primary criterion): the printable planner template, tied with the subscription system at 72.8. **Doctrine-adjusted recommendation: the AI-powered compliance automation subscription system** — same real score, but recurring revenue, higher defensibility, more expensive real problem (accounting-firm compliance), matching Section 12/14's explicit strategic doctrine over a template.

## WHY_IT_WINS

Real, tied `goos_advisory_score` (72.8) with the raw top-1, **plus**: recurring subscription model (vs. one-time template sale), a genuinely harder-to-copy B2B compliance workflow (vs. a copyable printable design), and direct alignment with this factory's own real, already-shipped precedent in the same problem space (the EU AI Act Compliance Toolkit, #6, `reusable_assets` ladder, real revenue-generating product this factory has already built).

## WHY_OTHER_OPPORTUNITIES_LOSE

- **Printable planners/SVG templates (#1,2,4,5,7-10)**: real score is comparable, but explicitly deprioritized by the founder's own strategic doctrine (low value, easily copied, one-time revenue) — never disqualified outright, just correctly ranked below a doctrine-aligned peer at the same score.
- **CO-n8n-affiliate**: real, verified partner terms, but 0/6 and 0/1 real qualified leads across 2 real live discovery rounds — every real candidate's evidence was STALE. Not weak economics; weak *current* evidence freshness, a real, time-bound gap, not a permanent one.

## EVIDENCE_CHAIN

CO-n8n-affiliate: `AUDIT/PHASE_36_COMMERCIAL_LAUNCH_CONTROL_REPORT.md` → `AUDIT/PHASE_37B_LIVE_DISCOVERY_REPORT.md` → `AUDIT/PHASE_37C_FRESH_EVIDENCE_REPORT.md` → this round's real `WATCH` transition. Product candidates: `decision_engine.store`'s real evaluation snapshots (all DEFERRED, real dates) → `goos.py::evaluate_dimensions()`'s real per-dimension citations → `goos.py::rank_build_candidates()`'s real score.

## EVIDENCE_FRESHNESS

CO-n8n-affiliate: **STALE** (0 FRESH, 1 STALE out of 1 real new candidate this round; 0 FRESH across all of Phase 37B/37C). Product candidates: **no real lead-discovery evidence exists for any of them** — their `goos_advisory_score` is a real, evidence-cited signal from `decision_engine`'s own evaluation snapshot, but none has ever been run through `lead_discovery.py`'s live customer-evidence pipeline. This is the real, honest gap the CEO decision below addresses directly.

## COMMERCIAL_SCORE

CO-n8n-affiliate: 30% recurring commission for 12 months, real, verified terms (unchanged). Subscription-system candidate: real `profitability` dimension cited via `goos.evaluate_dimensions()`, not independently re-scored this round.

## RECURRENCE_SCORE

CO-n8n-affiliate: real, recurring (12-month commission). Subscription-system candidate: real, recurring by its own named business model (subscription) — the strongest recurrence signal among all evaluated candidates this round.

## COMPETITION_SCORE

CO-n8n-affiliate: `NOT_MEASURED` — no real competition signal captured at this opportunity granularity (an honest, disclosed gap, not computed this round). Product candidates: cited via `goos.evaluate_dimensions()`'s real `competition_level` field where a real evaluation snapshot exists.

## TIME_TO_REVENUE

`NOT_MEASURABLE` for every real opportunity evaluated this round — no real historical per-opportunity time-to-first-revenue signal exists anywhere in this factory (the same disclosed gap class `goos.py`'s own `time_to_mvp` dimension already carries).

## RISK

CO-n8n-affiliate: `Low` (real, cited from the commission portfolio record). Product candidates: cited via `goos.evaluate_dimensions()`'s real `risk_level` field per candidate.

## GOLDEN_HUNTER_REASONING

Full real per-dimension citations for every evaluated opportunity: `data/phase38_rotation_validation_result.json`. Every dimension is either a real citation of an existing function's output or an honest gap — confirmed by regression test that no dimension is ever a mysterious collapsed number.

## ROTATION_DECISIONS

`CO-n8n-affiliate`: **WATCH** (real evidence freshness gate not met, 0 repeated-failure penalty yet — this is its first WATCH cycle, not yet at the 2-failure `ABANDON` ceiling). No `ROTATE` decision was triggered this round — the comparison found the top product candidate is *tied*, not *materially stronger*, so the real rotation-trigger bar (Section 5's "materially stronger expected value") was not conclusively met given the product candidates' own unvalidated real-evidence gap.

## WATCH_LIST

`CO-n8n-affiliate`.

## ABANDON_LIST

Empty — no opportunity has reached the real 2-failure repeated-failure threshold yet.

## RESURRECTION_RULES

`CO-n8n-affiliate` reopens (`check_resurrection()`) only when a real, live discovery run finds genuinely `FRESH` evidence (≤45 days old) — `STALE`/`UNKNOWN` new evidence never triggers resurrection (regression-tested).

## MISSION_CONTROL_STATUS

**Real, live-verified.** New `golden-hunter-rotation-status` panel: real PURSUE/WATCH/ABANDON/ROTATE buckets, top-2 comparison with a real cited reason, live-verified via a temporary server instance on a separate port (the live supervised process was never touched).

## OUTREACH_STATUS

**Unchanged, inactive.** `state=NO_CREDENTIAL`. No credential activated this phase.

## FINANCIAL_TRUTH

Unchanged throughout. `commission_ledger.py::real_commission_summary()`'s `real_commission_records` confirmed identical (0) before and after every real script run this phase.

## SECURITY_STATUS

**Clean.** 3 new prompt-injection regression tests confirm malicious text in a `reason`/`evidence`/commission-record field can never forge a new lifecycle state, escalate a recommendation past what real evidence supports, or be interpreted as an instruction. `opportunity_rotation_engine.py` regression-tested to have zero import of `outreach_adapter`/`outreach_engine`/`commission_ledger` and zero `.send(` call anywhere — structurally incapable of sending outreach or writing financial data.

## TEST_RESULTS

**413/413 passing, 0 failures** (full targeted regression across every module touched in Phases 33-38, including 36 new tests this round covering lifecycle transitions, score explainability, cross-opportunity comparison, repeated-failure penalty, resurrection, authority boundaries, and prompt-injection resistance).

## REAL_REVENUE

**$0.**

## REAL_COMMISSION

**$0** (`real_commission_records: 0`, identical before/after).

## REAL_CUSTOMERS

**0.**

## REAL_DEALS

**0.**

## REAL_PAYOUTS

**0.**

## CEO_DECISION_REQUIRED

> ### B — WATCH AND GATHER MORE EVIDENCE

**Specific missing evidence**: (1) For `CO-n8n-affiliate`: genuinely fresh (≤45-day), on-topic customer-pain evidence — the exact, disclosed gap Phase 37B/37C already identified, unchanged. (2) For the doctrine-aligned best candidate (the AI-powered compliance automation subscription system for accounting firms) and the runner-up template candidates: **zero real lead-discovery evidence has ever been run against any of them** — their real `goos_advisory_score` reflects `decision_engine`'s own internal evaluation model, not a live customer-evidence check via `lead_discovery.py`. Before recommending a PURSUE-level commitment to any of these, the same real, disclosed discovery process Phase 37B/37C already proved out for commission opportunities should be run against this subscription-system candidate specifically.

This is **not** A — no opportunity has real, fresh, customer-validated evidence clearing a genuine PURSUE bar yet. This is **not** C — real signals exist across multiple opportunities (a real, tied-score subscription-system candidate with strong recurrence/defensibility characteristics; CO-n8n-affiliate's own real, verified partner terms) that argue against wholesale abandonment. The company should keep both watching CO-n8n-affiliate for fresh evidence and, as the next real validation step, run `lead_discovery.py` against the compliance-subscription candidate before elevating it further.

---

*Full structured data: `data/phase38_rotation_validation_result.json`. Modules: `opportunity_rotation_engine.py`. Script: `scripts/phase38_rotation_validation.py`. See also: `AUDIT/PHASE_37C_FRESH_EVIDENCE_REPORT.md`.*
