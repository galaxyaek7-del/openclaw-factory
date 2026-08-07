# Galaxy Forge — Operating Principles

**Status:** Permanent, part of the Company DNA (`COMPANY_DNA.md`). Phase 11 of the strategic architecture (2026-08-07) — the founder's own framing: "not documentation. Executable operating laws." This document is the single canonical statement of the 14 named principles. It does not re-explain each one from scratch — for every principle, `EXECUTABLE_PRINCIPLES.md` names the real, already-running mechanism that enforces it today, or honestly discloses that none exists yet.

**Read this together with, never instead of:** `COMPANY_DNA.md` (mission/vision), `DECISION_FILTERS.md`/`DECISION_PROTOCOL.md` (how a single decision gets made), `INTEGRITY_RULES.md` (the 4 permanently human-gated actions), `TRUTH_FIRST_CONSTITUTION.md` (ADR-160, the company's highest law), `brand_dna.py` (customer-facing trust enforcement). Where a principle below restates something those documents already say, it cites rather than duplicates.

---

## The 14 Operating Principles

1. **Truth before convenience.** Never manipulate data. Never fabricate success. Never hide failure.
2. **Customer success before company ego.** If a decision benefits Galaxy Forge but harms customer trust, reject it.
3. **Quality before quantity.** One exceptional product beats fifty average ones.
4. **Automation must increase quality, never reduce it.**
5. **Every important decision must be explainable.** No black-box decisions.
6. **Everything must leave evidence.** Every action, deployment, publication, commercial decision — traceable.
7. **Never optimize local success. Optimize enterprise value.**
8. **Complexity is technical debt.** Simplify whenever possible.
9. **Every subsystem must justify its existence.** Recommend removal if it creates little value.
10. **Never become platform-dependent.** Always design for Amazon, Payhip, Gumroad, Paddle, Lemon Squeezy, Shopify, and future marketplaces.
11. **Commercial activity never stops.** If one platform fails, another continues.
12. **Knowledge is a permanent asset.** Never lose lessons. Never repeat mistakes.
13. **Every department exists to increase Customer Value, Enterprise Value, and Long-term Sustainability.**
14. **Whenever two choices exist, choose the one that will still be correct ten years from now.**

## Why these were not built as 14 new systems

A direct check against this factory's own real, already-running code — done before writing a single word of this document, per Principle 1 itself — found that **all 14 principles already have at least a partial real enforcement mechanism**, most of them built across earlier sessions under different names. Building 14 new modules to re-implement rules the codebase already lives by would itself violate Principle 8 (complexity is technical debt) and Principle 9 (every subsystem must justify its existence) in the same breath as writing them. See `EXECUTABLE_PRINCIPLES.md` for the full, function-level citation of each one, including the handful of genuine, disclosed gaps.

## The two principles that are the founder's own words restated

- **Principle 14 (the ten-year test)** is, almost verbatim, `CLAUDE.md`'s own ADR-187 standing instruction (2026-08-07, same day this phase arrived): *"عند وجود خيارين، يُختار ما سيهم بعد خمس سنوات، لا ما يهم خلال خمسة أيام."* Widened here from five years to ten at the founder's own new wording — the same principle, a longer horizon, not a new rule.
- **Principle 11 (commercial activity never stops)** is `safe_mode.py`'s own real, already-coded design principle from ADR-135 (2026-07-29): *"stop only the affected subsystem, keep the rest running, never allow cascading failures."* Already enforced in code, not just stated here.

## Enforcement authority

These are operating laws, not suggestions — but per `INTEGRITY_RULES.md` §3, no principle here authorizes bypassing the 4 permanently human-gated actions (Evolution Queue execution, capital reallocation, business retirement, elevated-risk publishing). A principle that appears to conflict with a protected gate loses — see `AUTONOMOUS_RULEBOOK.md`.

---

*See also: `EXECUTABLE_PRINCIPLES.md`, `DECISION_LAWS.md`, `COMPANY_STANDARDS.md`, `AUTONOMOUS_RULEBOOK.md`.*
