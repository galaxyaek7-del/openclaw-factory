# Galaxy Forge — First Real Dollar Runbook

**Date:** 2026-08-09 | Directive: "Commercial Flight Control & First-Real-Dollar Execution" (Phase 39, ADR-236)

This is the smallest possible controlled experiment this factory can run toward a genuine first commission dollar, given the real, live system state as of this round. It describes stages, not a schedule — no stage here executes automatically; every irreversible step is explicitly human-gated, per the directive's own hard prohibitions.

Two real, structurally different commercial mechanisms exist in the current portfolio, and this factory's own selection logic honestly disagrees on which is the better first bet (see Report Section B). Both are documented below rather than arbitrarily picking one; **the founder decides which to pursue.**

---

## Track A — Outreach Referral (e.g. CO-adobe-affiliate, CO-n8n-affiliate)

| Stage | Automated responsibility | Human responsibility | Evidence required | Failure condition | Rollback condition |
|---|---|---|---|---|---|
| **DISCOVER** | `rank_commission_shortlist()` surfaces the real, ranked opportunity portfolio (already done — 13 real opportunities on file). | None. | Real WebSearch-sourced registry entry (`business_development.py`). | Portfolio empty or all entries STALE. | N/A — read-only. |
| **VERIFY** | `commercial_flight_control_status()` checks verification_status, freshness, known conflicts live. | Founder may request a fresh WebFetch re-check if evidence is aging. | `verification_status == VERIFIED`, `freshness in (FRESH, AGING)`. | STALE/UNVERIFIED/conflict found. | Re-run VERIFY after fresh evidence; do not proceed on stale data. |
| **SCORE** | `score_commission_opportunity()` (13 real dims) + `commission_economics()` if a real deal value exists. | None. | Real commission rate on file. | `commission_value == COMMISSION_UNKNOWN`. | N/A — read-only. |
| **CEO REVIEW** | `commercial_flight_control_status()` presents VERDICT + full blocker list. | Founder reviews the gate output. | The gate's own structured `checks`/`blockers`. | Founder does not review — no stage may be skipped. | N/A. |
| **HUMAN APPROVAL** | `outreach_adapter.prepare_scoped_draft()` prepares a draft (never sends). | Founder supplies a real, exact-scope approval object (11 required fields: `approved_lead_id`, `approved_opportunity_id`, `approved_partner_id`, `approved_channel`, `approved_message_hash`, `maximum_action_scope`, `approval_timestamp`, `expiration_time`, `approved_by`, `approved_at`, `approval_scope`). | `verify_exact_scope_approval()` returns `ok: True`. | Missing field, expired `expiration_time`, or message_hash mismatch (draft changed after approval). | Approval refused — draft re-prepared, new approval required. Never silently honored. |
| **CONTROLLED ACTION** | `SMTPOutreachAdapter.send()`, gated by `MAX_REAL_SENDS=1` and a real, present `OUTREACH_SMTP_*` credential. | Founder configures the real SMTP credential (this system cannot create one). | Real credential present, `real_sends_used < MAX_REAL_SENDS`. | Credential missing (current real state) or cap reached. | Never retried automatically; a failed send does not consume the approval's single-use budget without a human decision. |
| **TRACK** | `pipeline_history()` / `record_pipeline_transition()` record real state changes. | Founder or a real prospect response drives the next transition. | A real logged event. | No response — opportunity stays in OUTREACH indefinitely (honest, not a failure by itself). | N/A. |
| **CONFIRM** | None automatic — a real sale/referral confirmation must come from the partner or the prospect. | Founder confirms the real conversion happened. | A real, dated confirmation (email, dashboard screenshot, partner portal). | No real confirmation exists. | Stay at OUTREACH/RESPONSE; never advance without it. |
| **LEDGER** | `commission_ledger.record_commission(environment="REAL", evidence=..., external_transaction_id=...)`. | Founder supplies the real evidence + real external_transaction_id. | `AntiFabricationError` guard passes (real, non-trivial evidence + txn id). | Evidence too short/missing → `AntiFabricationError`; duplicate txn id → `DuplicateCommissionError` (both real, tested, including under real concurrency — Section 9). | Record never written on failure — nothing to roll back. |
| **PAYOUT VERIFICATION** | `first_real_dollar_status()` recomputes from the real ledger. | Founder confirms the real payout independently (bank/PayPal statement). | `commission_status` reaches `CONFIRMED` or `PAID` with real evidence. | Payout disputed/reversed → `commission_status` set to `DISPUTED`/`REVERSED`, real, honest, excluded from `FIRST_REAL_DOLLAR`. | The reversal is itself a new, real, evidenced ledger event — never a silent edit of the original record. |
| **FIRST_REAL_DOLLAR** | `first_real_dollar_status()` flips `True` the moment a REAL/CONFIRMED-or-PAID record exists. | None — purely derived. | The ledger record itself. | N/A — this is the terminal success state. | N/A. |

**Real, current blockers on this track:** no `OUTREACH_SMTP_*` credential configured; no real qualified lead on file (Phase 37B's only real live discovery run found 0/6 qualified); no approval object has ever been created. All three are real, human-actionable gaps — not code gaps.

---

## Track B — Affiliate Link Publish (CO-amazon-affiliate)

| Stage | Automated responsibility | Human responsibility | Evidence required | Failure condition | Rollback condition |
|---|---|---|---|---|---|
| **DISCOVER** | Same portfolio citation as Track A. | None. | Same. | Same. | N/A. |
| **VERIFY** | Same gate, `AFFILIATE_LINK_PUBLISH` mechanism. Live-reconfirmed 2026-08-08 (this round, Section 3) via a real WebFetch of `affiliate-program.amazon.com`. | Founder may re-verify at account-creation time (terms can change). | Real, dated fetch of the official domain. | Terms page no longer matches recorded evidence. | Re-run VERIFY. |
| **SCORE** | `score_commission_opportunity()` + the real, recorded 5%/10% commission-rate evidence. | None. | Real rate on file. | N/A today — real rate exists. | N/A. |
| **CEO REVIEW** | Same gate presentation. | Founder reviews. | Same. | Same. | N/A. |
| **HUMAN APPROVAL** | None automatic — this mechanism has no message-scope object to approve. | **Founder creates a real Amazon Associates account and configures `AMAZON_ASSOCIATE_TAG`.** This system cannot create the account (standing prohibition, CLAUDE.md). | A real, approved Amazon Associates account + tag. | Account rejected, or founder declines to pursue this track. | N/A — nothing to roll back before the account exists. |
| **CONTROLLED ACTION** | `affiliate_commerce.networks.build_amazon_url()` generates a real tagged link once the tag exists; `click_tracking.record_click()` logs real clicks. | Founder (or a real customer-facing page) publishes the link somewhere with real traffic. | Real tag configured, real published placement. | Tag missing (current real state). | N/A. |
| **TRACK** | `click_tracking.click_summary()` — real click counts. | None. | Real recorded clicks (currently 0). | Zero clicks — honest, not a code failure. | N/A. |
| **CONFIRM** | None — Amazon's own dashboard is the real source of truth for a completed purchase. | Founder checks Amazon Associates Central for a real, confirmed sale. | A real, dated screenshot/export from Amazon's own dashboard. | No real sale within the real 24-hour/90-day cookie window. | N/A. |
| **LEDGER** | Same `record_commission()` guard as Track A. | Founder supplies real evidence. | Same `AntiFabricationError`/`DuplicateCommissionError` protection. | Same. | Same. |
| **PAYOUT VERIFICATION** | Same `first_real_dollar_status()`. | Founder confirms real payout (direct deposit/gift card/check, per Amazon's real, recorded payment methods). | Same. | Same. | Same. |
| **FIRST_REAL_DOLLAR** | Same terminal state. | None. | Same. | N/A. | N/A. |

**Real, current blockers on this track:** `AMAZON_ASSOCIATE_TAG` is unset (confirmed live this round); no real Amazon Associates account exists; zero real clicks have ever been recorded (`data/affiliate_clicks.jsonl` does not exist).

---

## Which track is actually shorter?

Honestly unresolved by this factory's own evidence — disclosed, not guessed:

- **Track A** needs 3 real human actions (SMTP credential, a real qualified lead, a scoped approval) but this factory's own one real live lead-discovery run (Phase 37B) found 0/6 qualified — real prospecting has proven non-trivial.
- **Track B** needs 1 real human action (Amazon account + tag) but then depends on real, unmodeled traffic/conversion with no existing distribution channel to drive it (this factory's `customer_site/` has no measured real visitor volume).

`rank_commission_shortlist()` (verification-tier-first) picks Amazon; `select_first_launch_opportunity()` (recurring-commission-first) picks Adobe (an outreach-referral opportunity) — this is the real, disclosed discrepancy `commercial_flight_control_status()` surfaces on every call. **See Report Section I/J for the founder-facing answer.**
