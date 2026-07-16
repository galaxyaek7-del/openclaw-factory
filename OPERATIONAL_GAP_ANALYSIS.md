# Operational Gap Analysis

**Date:** 2026-07-16
**Directive:** "Executive Directive — End-to-End Company Validation"

---

## 1. Manual-vs-automated audit

Objective: confirm no manual step exists **where automation is intended**. This requires distinguishing *intentional* manual control (a documented design choice) from an *unintentional* gap (automation was meant to exist and doesn't).

Every manual step found in this system was cross-checked against its documented intent:

| Manual step | Intentional, and why | Evidence |
|---|---|---|
| Starting `factory_loop.js` | Yes — this factory deliberately has no scheduler/cron/CI timer at all, by design (cost/safety: a human must consciously start it) | `CLAUDE.md` "No scheduler exists" section, confirmed unchanged since 2026-07-13 |
| `factory_loop.js` not auto-processing `pending_review/queue/` | Yes — same section explicitly documents this; a human must run `scripts/process_approved_drafts.py` after approving a draft | `CLAUDE.md`, confirmed the script still exists, queue currently empty (0 items) |
| n8n workflow activation | Yes, but for a *platform* reason, not a design choice — `n8n import:workflow --activeState=fromJson` errors outside queue/multi-main mode; this deployment doesn't run either | `BLOCKERS.md` #1, `ADR-045`, re-confirmed this session (REST API still returns 401) |
| Gmail/n8n OAuth connection | Yes — Google's own OAuth consent flow requires the account owner's browser action; no API/CLI path exists around it by design | `BLOCKERS.md` #1b |
| Mission Control's action triggers (rerun-market-analysis, trigger-opportunity-evaluation, start-production-pipeline, etc.) | Yes — several touch paid APIs (Groq) or would fire real evaluation cycles; requiring an explicit, confirmed human trigger is a deliberate cost/safety control, consistent with "no scheduler" | `ACTION_REGISTRY` in `server.js`, confirmed every action requires `{"confirmed": true}` |
| Live platform publishing (Gumroad/Payhip/Etsy) | Yes — blocked on a real API credential only the founder can obtain | `BLOCKERS.md` #2 |

**Conclusion: no unintentional manual step was found.** Every manual step traces to either (a) this factory's deliberate "no scheduler, human-in-the-loop for cost/safety" architecture, or (b) a platform/credential constraint outside engineering control. This is a consistent, previously-documented design pattern, not something this validation is flagging as new.

## 2. Documentation drift found and corrected

Two real instances of stale documentation misrepresenting actual system state were found this session (one during the earlier n8n gap-fix work, one during this validation):

1. **`FACTORY_STATUS.md` §6** (found and fixed during the n8n gap-fix directive) claimed the Sensing Engine's HTTP node was missing and `OPPORTUNITIES.md` "stays empty" — both false; real evidence in `OPPORTUNITIES.md` itself proved the pipeline had already fired successfully.
2. **`BLOCKERS.md` #4** (found and fixed during this validation) claimed `competition` and `profit_potential` (margin) scoring "still need the same treatment" as the real-signal fix `demand` received — false; `ADR-041` (2026-07-15) already applied the identical real-signal philosophy to both, confirmed directly in `profit_oracle.py`'s source (`_score_competition()`/`_score_margin()` both call `_find_niche_report()`).

**Pattern:** this factory's hand-maintained "what's blocking us" documents can silently go stale once the underlying code changes, and nothing currently re-validates them against real evidence. See recommendation in the Final Executive Recommendations for how to reduce this recurring risk without building new architecture.

## 3. Remaining operational gaps (ranked by what would move a real dollar closest)

| # | Gap | Category | Blocked on |
|---|---|---|---|
| 1 | Zero ACCEPTED opportunities | Business data, not engineering | Real evidence needs to accumulate (time) or a real new candidate source (n8n Sensing Engine activation would help, `ADR-028`'s never-built real candidate source would help more) |
| 2 | n8n workflows never activated | Platform/credential | Founder's browser login at `localhost:5678` (`BLOCKERS.md` #1) |
| 3 | No live sales channel | Credential | A real Gumroad/Payhip/Etsy API token (`BLOCKERS.md` #2) |
| 4 | Production Factory never run against real data | Consequence of #1 | Same as #1 |
| 5 | `niche_reports/` real competitor pricing data — empty all session | Evidence gap | Manual research per candidate (already the documented, deliberate manual process — automating it reliably failed a real test at 25% success rate, `ADR-046`) |
| 6 | Mission Control never opened in a real browser | Verification gap | A human should click through it once; every check this session was API-level |
| 7 | Gmail/email notifications | Credential | Founder's OAuth consent (`BLOCKERS.md` #1b) |

None of these require new architecture or new features to close — every one is either a credential/business-data wait, or (for #6) a five-minute human action.
