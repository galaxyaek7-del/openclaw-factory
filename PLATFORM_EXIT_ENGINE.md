# Galaxy Forge — Platform Exit Engine

**Date:** 2026-08-08 | ADR-216, Phase 26, Section 30. `global_commercial_operations_engine.platform_exit_check()`.

---

## Real, evidence-based recommendation

A platform is recommended for exit only when its real current stage is not `ACTIVE`/`OPTIMIZATION` **and** its real opportunity score is 0. **Never keeps a platform merely because of past revenue** — the directive's own inverse rule ("do not keep a platform merely because it generated some historical revenue") is honored by the same logic in reverse: this factory has $0 historical revenue on every real platform, so the check is evidence-neutral today, never biased by sunk-cost reasoning in either direction.

## The 9 named exit triggers

Negative Contribution, Poor Customer Quality, Excessive Refunds, Payout Problems, High Operational Burden, Account Risk, Security Risk, Policy Risk, Weak Strategic Value — 0 have fired for any real platform (0 real activity to trigger them).

---

*See also: `PLATFORM_EXPANSION_ENGINE.md`, `PARTNER_TERMINATION.md` (Phase 25).*
