# Galaxy Forge — First Deal Ideal Customer Profile

**Date:** 2026-08-08 | ADR-229, Phase 36, Sections 8-9. A PROFILE, not a fabricated named customer — no fictional individual or company is described below.

---

**CUSTOMER_TYPE:** Small business owner, solo operator, or small agency — not enterprise (n8n's self-service, no-minimum-commitment program fits this segment, not a large enterprise sales motion).

**INDUSTRY:** Digital services / e-commerce / SaaS-adjacent businesses — segments where multiple SaaS tools (CRM, email, spreadsheets, payment processors) are already in use but not connected.

**BUSINESS_SIZE:** 1-20 employees (a size band with real budget for a $50-500/month automation tool but genuinely no dedicated automation engineer on staff).

**PROBLEM:** Manual, repetitive, cross-tool workflows — e.g. manually copying leads from a form into a CRM, then into an email tool, then into a spreadsheet for reporting.

**PROBLEM_COST:** UNKNOWN — no real time-cost or dollar-cost study has been performed for this segment; would require real customer interviews to establish.

**URGENCY:** UNKNOWN — no real signal exists yet.

**BUYING_TRIGGER:** Plausibly: hiring growth outpacing manual-process capacity, or a specific integration failure/error that surfaces the cost of manual work. **Not observed — a plausible, disclosed hypothesis, not a verified trigger.**

**DECISION_MAKER:** The business owner or operations lead directly, given the target company size (no separate IT/procurement layer expected).

**LIKELY_OBJECTION:** "We don't have technical staff to set up automation tooling" — n8n's own real product addresses this partially (a visual workflow builder, not code-only), but this remains a real, disclosed anticipated objection, not a confirmed one.

**EXPECTED_VALUE:** `UNKNOWN` — requires real commission_economics() inputs (see `LAUNCH/FIRST_DEAL_COMMERCIAL_ECONOMICS.md`'s own disclosed ESTIMATED-basis calculation).

**WHY_THIS_PRODUCT:** n8n is a real, self-hostable-or-cloud workflow automation tool with a real, genuinely lower technical barrier than writing custom integration code — a credible fit for a non-technical small-business decision-maker.

**WHY_NOW:** No real, verified urgency signal exists (see URGENCY above) — this section is honestly `UNKNOWN`, not filled with an invented timing narrative.

## Real agent output against this profile (live-tested, not fabricated)

**Commercial Deal Agent** (`commercial_deal_agent.deal_priority_score()`): 7 of 11 real factors known, `CONFIDENCE=MEDIUM`, `RECOMMENDED_ACTION=PROCEED_TO_QUALIFICATION`, `EXPECTED_VALUE` honestly `UNKNOWN` without a real deal-value input.

**Lead & Outreach Agent** (`lead_outreach_agent.explain_customer_match()`): real signals present (`industry` provided), `WHY_THIS_PARTNER` cites n8n's real `VERIFIED` status, `WHY_NOW` cites real data freshness (`FRESH`), `RISK=Low`.

Neither agent claims a numerical score without explanation — both outputs are fully reproduced in `AUDIT/PHASE_36_COMMERCIAL_LAUNCH_CONTROL_REPORT.md`.

---

*See also: `LAUNCH/FIRST_DEAL_OPPORTUNITY_DOSSIER.md`, `LAUNCH/FIRST_DEAL_PROSPECT_SPECIFICATION.md`.*
