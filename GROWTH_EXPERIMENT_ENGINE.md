# Galaxy Forge — Growth Experiment Engine

**Date:** 2026-08-08 | ADR-218, Phase 28, Sections 16, 38. `global_growth_engine.growth_experiment_memory()` — reuses `commercial_experiments.py` verbatim, never a second experiment system.

---

## The 10 named test dimensions

Headline, Offer, Price, CTA, Creative, Audience, Channel, Landing Page, Email, Product Positioning — real, controllable via `commercial_experiments.py`'s existing generic `experiment_type` field.

## Section 38 — Experiment Memory

Every real experiment already stores Hypothesis/Result/Confidence/Lesson (`commercial_experiments.py`'s real schema) — 0 real growth experiments have been created yet.

---

*See also: `CAMPAIGN_ENGINE.md`, `COMMERCIAL_EXPERIMENT_ENGINE.md` (Phase 26).*
