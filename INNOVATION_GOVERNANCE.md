# Galaxy Forge — Innovation Governance

**Date:** 2026-08-08 | ADR-213, Phase 23, Sections 27-29, 35. Real citation over `galaxy_council.py` and `autonomous_operations.py` (Phase 19, ADR-209) — no new authorization system.

---

## Section 27 — AI Council

`ai_council_product_challenge(niche)` reuses `galaxy_council.py::convene_council()` verbatim — 9 real members, `disagreement_detected` is `True` iff 2+ voting members hold genuinely different real stances, **never forced to a fake consensus** (confirmed by direct inspection of `_arbitrate()`'s honest `SPLIT` reporting, the same discipline this session's `executive_brain.py` established).

## Section 28 — Red Team (genuinely new)

`red_team_challenge(niche)` — 8 named adversarial questions, each answered by citing a real, already-computed signal (`validation_gate_status()`, `kill_criteria_check()`) or honestly `NOT_ANSWERED`. **Deliberately not a new LLM call**: a fresh AI-generated critique could hallucinate a plausible-sounding but fabricated objection — worse than an honest gap. Verified by a regression test confirming at least one real question resolves to `NOT_ANSWERED` rather than a manufactured answer.

## Section 29 — Human Decision Gate

`human_decision_gate_check(action_category)` reuses `autonomous_operations.authorize_action()` (Phase 19, ADR-209) directly — the same real Level 5/6 taxonomy already governing every other irreversible action in this factory. Verified live: `evolution_approve_execute` still `REFUSE`s without an explicit founder approval reference; `real_payment_or_transaction` still `REFUSE`s **even when a caller forces `founder_approved: True`** in the context.

## Section 35 — What may/must-not happen autonomously

`autonomous_innovation_boundaries()` cites the real `ACTION_CATEGORY_AUTONOMY` registry directly — `capital_reallocation`/`business_retirement`/`governance_or_permission_change`/`real_payment_or_transaction` are all Level 5/6, unchanged, mapped 1:1 onto this directive's own "must NOT autonomously" list.

---

*See also: `AUTONOMY_LEVELS.md`, `ACTION_AUTHORIZATION_ENGINE.md`.*
