# Galaxy Forge — Partner Due Diligence

**Date:** 2026-08-08 | ADR-215, Phase 25, Sections 14-15. `global_partnership_network.partner_due_diligence()` + `partner_trust_status()`.

---

## Section 14 — Due Diligence

Reuses `PLATFORM_REGISTRY`'s real, WebSearch-sourced evidence directly (2026-08-07) — **never relies solely on a partner's own claim**, per the directive's own explicit rule. This registry's evidence predates and is independent of any partner's own marketing claims. Fraud indicators and unusual claims are honestly `NOT_CHECKED` — no real fraud-signal source exists for a platform this factory has never transacted with.

## Section 15 — Trust & Reputation (already real, cited)

`partner_trust_status()` reuses `trust_audit.py` (Phase 22, ADR-189) directly — a partner that generates revenue but damages customer trust must be downgraded/terminated, the same real principle `trust_audit.py` already enforces for this factory's own products.

---

*See also: `PARTNER_QUALIFICATION_ENGINE.md`, `PARTNER_FRAUD_ENGINE.md`.*
