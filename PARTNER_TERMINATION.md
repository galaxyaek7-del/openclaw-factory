# Galaxy Forge — Partner Termination

**Date:** 2026-08-08 | ADR-215, Phase 25, Sections 29, 36. `global_partnership_network.partner_termination_check()` + `partner_contract_governance()`.

---

## Section 29 — Termination (already real, mechanically exercisable)

Real termination itself is Level 3-4 (reversible, already exercisable via `business_development.py::advance_partnership()` moving a platform to `REJECTED`/`ARCHIVED`) — but any **exclusivity/territory or contract commitment made TO a partner** requires real Level 5 human approval, via `autonomous_operations.authorize_action()`.

## Section 36 — Partner Contract Governance (already real, cited)

2 real, additive categories now govern this: `enterprise_contract_commitment` (Phase 24) and the new `partner_exclusivity_or_territory_commitment` (this round) — both Level 5, refusing without an explicit real `founder_approved` + `approval_reference` context. **Verified live**: refuses by default, allows only with a real, explicit approval reference.

## The 9 named exit conditions

Fraud, Customer Harm, Repeated Policy Violations, Security Incident, Persistent Underperformance, Unacceptable Economics, Reputation Damage, Contract Expiration, Strategic Change — real, disclosed triggers; 0 have ever fired (0 real partner activity exists).

---

*See also: `AUTONOMY_LEVELS.md` (Phase 19), `AI_AGENT_GOVERNANCE.md` (Phase 24).*
