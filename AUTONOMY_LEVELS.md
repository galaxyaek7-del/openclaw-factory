# Galaxy Forge — Autonomy Levels

**Date:** 2026-08-08 | ADR-209, Phase 19, Section 2. Real, queryable classification — `autonomous_operations.AUTONOMY_LEVELS`.

---

| Level | Name | Real meaning | Example |
|---|---|---|---|
| 0 | OBSERVE ONLY | Reads real state, produces no recommendation | `resilience_monitor.assess_resilience()`, `knowledge_decay.assess_all_known_knowledge()` |
| 1 | ANALYZE | Computes a real derived judgment, no action item | `executive_questions.answer_strategic_questions()` |
| 2 | RECOMMEND | Surfaces a real, evidence-cited candidate for a human to consider | `executive_brain.build_executive_directive()`, `evolution_queue.simulate_proposal()`/`decide_proposal()` |
| 3 | EXECUTE REVERSIBLE LOW-RISK ACTIONS | Real, already-automatic actions touching only this factory's own disposable internal state | `factory_loop.js`'s daily/weekly/monthly report generation, health-snapshot recording |
| 4 | EXECUTE CONTROLLED BUSINESS OPERATIONS | Real, already-automatic external actions, live-gated at execution time | `distributor.py::distribute()` for a proven arm, gated by `check_publish_allowed()` |
| 5 | HUMAN APPROVAL REQUIRED | A human can authorize this through a real, explicit mechanism; the system never initiates it | `evolution_queue.approve_proposal()`, `approve_first_publish()`, capital reallocation, business retirement |
| 6 | NEVER AUTOMATE | No context or override authorizes this, permanently | Real payment/transaction execution, self-permission-granting, account creation, credential entry |

## The 4 permanently protected human-gates map to Level 5, unchanged

Evolution Queue execution, capital reallocation, business retirement, and elevated-risk/new-channel publishing — the 4 gates reconfirmed unchanged by the founder 6+ times this session (ADR-133/134/139/142/144/147/157) — are classified **Level 5** here. This classification does not create, loosen, or duplicate their real enforcement; it makes an already-real fact machine-queryable.

## Real, verified guarantee

`authorize_action("real_payment_or_transaction", context={"founder_approved": True, "approval_reference": "anything", "override": True})` **still returns `REFUSE`** — proven by `tests/test_autonomous_operations.py::test_level_6_never_authorizes_even_with_explicit_approval`. No context can move a Level 6 category to ALLOW through this module.

---

*See also: `ACTION_AUTHORIZATION_ENGINE.md`.*
