# Galaxy Forge — Partner Qualification Engine

**Date:** 2026-08-08 | ADR-215, Phase 25, Sections 4-6. `global_partnership_network.partner_qualification()` + `partner_score()`.

---

## Section 4 — Qualification (9 named levels)

Real, deterministic mapping from `business_development.py`'s real `evaluate_platform()` score (0-5) + real pipeline stage: 0 → `UNQUALIFIED`; 1-2 → `RESEARCH`; 3 → `PROSPECT`; 4 → `QUALIFIED`; 5 → `HIGH_VALUE`; real `ACTIVE` stage → `ACTIVE`; real `REJECTED`/`ARCHIVED` → `EXIT`. **`STRATEGIC`/`PAUSED` are never auto-assigned** — verified by a dedicated regression test — both require a real founder judgment call.

## Section 5 — Partner Score (already real, cited)

`_opportunity_score()`'s real 3-axis heuristic (program confirmed / joinable by small business / strategic fit, each 0/1/2, summed) already IS this section's own explicit rule ("never use an unexplained score, every score must show its components") — cited directly, never a second scoring computation. Verified by a regression test confirming every score carries its 3 named components.

## Section 6 — Partner Types (13 named)

`PARTNER_TYPES` — real taxonomy; `business_development.py`'s real `OPPORTUNITY_TYPES` (7 named) covers the commercially-distinct subset this factory has real infrastructure for.

---

*See also: `PARTNER_REGISTRY.md`, `PARTNER_DUE_DILIGENCE.md`.*
