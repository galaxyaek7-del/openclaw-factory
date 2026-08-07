# Galaxy Forge — Decision Laws

**Status:** Permanent, part of the Company DNA. Where `OPERATING_PRINCIPLES.md` states the 14 laws and `EXECUTABLE_PRINCIPLES.md` cites what enforces each one, this document answers a narrower, sharper question: **at the moment a real decision is being made — by a human, an AI agent, or an automated tick — which laws actually fire, in what order, and what happens when two of them point in different directions?**

## 1. The decision pipeline every real opportunity already passes through

Not a new pipeline — the real one this factory has run since `decision_engine/` (ADR-050/076):

1. **Evaluate** — `decision_engine.engine` (Principle 1: real signals only, never fabricated); `profit_oracle.py::ladder_opportunity_score()`'s Proof of Payment gate (Principle 1 applied to evidence itself — no niche is ACCEPTED without a real, human-cited quote)
2. **Quality-gate** — `executive_quality_gate.py::REJECT_IF_FAIL` (Principles 1, 2, 4: content-neutrality, copyright/trademark, brand-reputation, fake-urgency, legal-compliance checks — a hard reject, not advisory)
3. **Record with reasoning** — `decision_engine.types.Decision`'s `reasoning`/`alternatives_rejected`/`expected_outcome` fields (Principle 5: no black-box decisions)
4. **Leave evidence** — every step above writes to a real, append-only ledger (Principle 6; see `evidence_engine.py`)
5. **Measure the outcome, later, honestly** — `decision_engine/feedback.py::sync_outcomes()` + `evolution_queue.py`'s real IMPROVED/DEGRADED/NO_CHANGE/NOT_ENOUGH_DATA measurement (Principle 12: the loop that prevents repeating a mistake)

A decision that skips step 2 or 4 is not a faster decision — it is not a real Galaxy Forge decision.

## 2. What outranks what — the real, tested priority order

`executive_brain.py::_arbitrate()` already answers this mechanically for the company's single daily directive: candidates are tagged Tier 1 (System Stability) through Tier 5 (Self Evolution), and the lowest tier wins — a genuine same-tier tie is honestly reported `SPLIT`, never arbitrarily resolved. Applied as a general decision law:

1. **A protected human gate always wins** — no principle above, including Principle 11 ("commercial activity never stops") or Principle 3 ("quality before quantity"), authorizes bypassing the 4 gates in `INTEGRITY_RULES.md`. See `AUTONOMOUS_RULEBOOK.md`.
2. **Truth (Principle 1) outranks convenience, speed, and enterprise value.** A financially attractive decision built on fabricated or unverified evidence is rejected before its ROI is ever considered — this is why `profit_oracle.py`'s Proof of Payment gate runs before, not after, scoring.
3. **Customer trust (Principle 2) outranks short-term company gain.** `brand_dna.py::TRUST_PRINCIPLES` is `REJECT_IF_FAIL`-gated, not advisory — a product cannot ship past it regardless of its projected revenue.
4. **Enterprise value (Principle 7) outranks local/departmental optimization**, but never outranks 1–3 above it. `capital_allocation_engine.py::opportunity_cost()` is the real, working expression of this: resources flowing to a lower-ranked initiative are named explicitly, never left implicit.
5. **Simplicity (Principle 8) is a tiebreaker among otherwise-equal options**, not a veto over a genuinely necessary system — `TECHNICAL_DEBT_REGISTER.md`'s own discipline: flag complexity, don't refuse to build what's actually needed.

## 3. When a decision must stop and ask a human

Not every judgment call needs `AskUserQuestion` — most of this factory's real decisions run through the pipeline above autonomously. A decision escalates to the founder specifically when:

- It would cross one of the 4 protected gates (`AUTONOMOUS_RULEBOOK.md`) — always, no exception, regardless of framing or urgency (reconfirmed explicitly at least 6 times across this session: ADR-107→110→115→133/134/139/142→147→157).
- Two real, already-built systems would otherwise duplicate each other and the founder's own prior words on the topic are ambiguous — the "consolidate vs. build new" question, asked directly when genuinely unresolved (ADR-146, ADR-152, ADR-161), and *not* re-asked once the founder has already answered the identical pattern (ADR-172, ADR-175, ADR-177 all proceeded without re-asking).
- A real technical/factual wall makes the literal ask unachievable, discovered only through verification (the Payhip evaluation, 2026-08-07: automated publishing is not possible via Payhip's API — a factual finding, not a preference, still surfaced for a founder decision on how to proceed).

## 4. What "explainable" (Principle 5) means in practice

`executive_decision_memory.py::explain_decision(decision_id)` is the literal, callable answer: it returns evidence used, missing evidence, unknown assumptions, and a confidence estimate for any real decision, niche-scoped or company-wide. A decision that cannot be run through this function — because no `decision_id` was ever recorded for it — did not follow Decision Law #3 above and should be treated as a process failure, not a one-off.

---

*See also: `OPERATING_PRINCIPLES.md`, `EXECUTABLE_PRINCIPLES.md`, `COMPANY_STANDARDS.md`, `AUTONOMOUS_RULEBOOK.md`, `DECISION_PROTOCOL.md` (Phase 2 — the per-decision 10-field template this document's pipeline produces).*
