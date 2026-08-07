# Galaxy Forge — Manual Intervention Register

**Date:** 2026-08-07 | Every point in the real commercial lifecycle where a human is currently involved, classified honestly. Per the directive: actions that legally, financially, or ethically require human approval are never automated, regardless of how much friction that adds.

**Classes:** REQUIRED HUMAN DECISION (by design, permanent) · OPTIONAL HUMAN REVIEW (automatable but currently reviewed) · AUTOMATABLE (real gap, safe to close) · ALREADY AUTOMATED (real, confirmed working).

---

| Step | Class | Why |
|---|---|---|
| Clearing Paddle's account-onboarding gate | **REQUIRED HUMAN DECISION** | External, third-party account verification — no code path can complete this; it is Paddle's own KYC/compliance process on the founder's real business |
| Filling the real legal-entity/jurisdiction placeholders in the trust pages | **REQUIRED HUMAN DECISION** | A real legal decision (business name, jurisdiction, applicable consumer-rights language) — not an engineering task, confirmed in `COMMERCIAL_READINESS_REPORT.md` Part B, Finding T1 |
| Evolution Queue proposal execution | **REQUIRED HUMAN DECISION (permanent, by design)** | One of the 4 permanently protected gates (`evolution_queue.py`) — reconfirmed unchanged this round |
| Capital reallocation | **REQUIRED HUMAN DECISION (permanent, by design)** | One of the 4 permanently protected gates (`capital_allocation_engine.py`) |
| Business retirement | **REQUIRED HUMAN DECISION (permanent, by design)** | No automated retirement code path exists anywhere, by design |
| New/elevated-risk channel publishing approval | **REQUIRED HUMAN DECISION (permanent, by design)** | `channels/publish_protection.py`'s Founder Protection layer |
| Generating a real checkout URL for the shipped product (a live, mutating call against production Paddle) | **REQUIRED HUMAN DECISION** (this test round) | Not a permanently protected gate in the codebase, but a real financial-adjacent action on a live third-party account — appropriately not taken unilaterally during this test; see `FAILURE_REGISTER.md` F2 |
| Manual fulfillment of a genuinely bespoke (non-catalog) customer request | **REQUIRED HUMAN DECISION (by design)** | `customer_pipeline.py::fulfill_manually()` — real, intentional escape hatch for requests that don't match an already-published catalog product |
| Deciding whether a `DEFERRED` niche should be re-evaluated given new manually-gathered evidence (see `FAILURE_REGISTER.md` F4) | OPTIONAL HUMAN REVIEW | Not legally/financially mandatory to keep human-gated, but the divergence found this round (F4) is exactly the kind of judgment call this factory has consistently routed to the founder |
| Product catalog completeness (description/target-customer fields, F5) | **AUTOMATABLE** | A real, scoped code fix (cross-reference `books/_generation_log.jsonl`) closes this without any human judgment required |
| Paddle rate-limit retry handling (F6) | **AUTOMATABLE** | A real, scoped code fix, same pattern already proven for Groq |
| Publish-attempt ledger backfill for the EU AI Act Toolkit (F3) | **AUTOMATABLE (backfill) / REQUIRED HUMAN DECISION (whether to backfill retroactively)** | The fix itself is mechanical; whether to retroactively edit historical ledger data is a real founder call (this factory's own standing rule: never silently modify financial/historical records) |
| Product discovery, scoring, quality-gating | **ALREADY AUTOMATED** | Golden Hunter + `executive_quality_gate.py`'s `REJECT_IF_FAIL`, confirmed real and running this round |
| Revenue/reconciliation/alert reporting | **ALREADY AUTOMATED** | `commercial_control_center.py`/`commercial_reconciliation.py`/`commercial_alerts.py` (ADR-202), all real, callable on-demand; daily-tick wiring remains a disclosed, deliberate follow-up (`COMMERCIAL_READINESS_REPORT.md` Part A, Section 11) |
| Customer-facing recovery-state messaging | **ALREADY AUTOMATED** | Fixed and live-verified per `COMMERCIAL_READINESS_REPORT.md` Part B, Finding PY1 |

## The honest summary

**Zero of the required-human steps above are a code gap.** Every REQUIRED HUMAN DECISION is either a permanently protected gate this factory has reconfirmed at least 6 separate times this session, or a genuine external/legal dependency (Paddle onboarding, jurisdiction). The company's real automation ceiling today is not held back by missing engineering — it is held back by two founder-only actions and, secondarily, by the small set of AUTOMATABLE items above.

---

*See also: `AUTOMATION_GAP_REPORT.md`, `FAILURE_REGISTER.md`.*
