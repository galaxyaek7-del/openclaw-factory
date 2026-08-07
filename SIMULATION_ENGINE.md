# OpenClaw / Galaxy Forge — Simulation Engine

**Status:** Permanent, part of the Company DNA (`COMPANY_DNA.md`). "Before implementing major decisions, simulate them" is checked here against `digital_twin.py` (ADR-161, 2026-07-31) and `enterprise_executive_brain.py::executive_scenario_simulator()` (ADR-156) — both real, both already advisory-only, verified by real regression tests to never execute an irreversible action themselves.

---

## The 6 requested simulation types, checked against real coverage

| Requested | Real coverage |
|---|---|
| New pricing | `pricing_review.py` (ADR-182) — real, evidence-gated readiness check for a tier change; the actual price *evaluation* itself is `economics.evaluate()`/`economics.market_realism_check()`, both real and already caught one real pricing error this session (the EU AI Act toolkit's $310→$155 correction) |
| New market | `market_domination_engine.py` — honestly `NOT_MEASURABLE` for every market outside global English-language platforms (the founder's own standing 2026-07-23 deferral); real for the domains that are covered |
| New product | `digital_twin.py`'s `SIMULATE` dispatch + `goos.py::rank_build_candidates()` (`GOLDEN_HUNTER_ENGINE.md`) |
| New partnership | `business_development.py` (ADR-188) — real, WebSearch-verified opportunity evaluation before any real partnership pipeline stage advances |
| New subscription | `growth_stages.py::simulate_stage_progression()` — one of `digital_twin.py`'s 3 real overridable simulation functions |
| New automation | `strategic_planning.py::simulate_roadmap_execution()` — the second of the 3 |

**All 6 requested simulation types map to a real, already-built mechanism.** None was invented for this document.

## The 6 requested estimate fields

| Requested | Real coverage |
|---|---|
| Risk | `resilience_monitor.py`'s real severity classification, cited wherever relevant |
| Revenue | `expected_revenue` — real closed-sale revenue only, **never a forecast** (`capital_allocation_engine.py`'s own explicit design choice — this company's real `expected_revenue` field is retrospective by construction, so it cannot be multiplied into a projection without fabricating one) |
| ROI | `expected_roi` — a real 0–100 score (`goos.py`), never a dollar figure pre-acceptance |
| Time | **Honest, repeated gap** — no real historical per-task duration data exists anywhere in this factory, confirmed independently by `execution_status.py`, `gfos.py`, `strategic_planning.py`, and `PRIORITIZATION_ENGINE.md` |
| Resources | `enterprise_capital_allocation.py::resource_allocation_map()` — real for 6 of 10 named strategic resources, honestly `INSUFFICIENT EVIDENCE` for the other 4 |
| Confidence | `confidence_score` — real, honest `low`/`medium`/`high`, never omitted |

## Why this is advisory-only, permanently

`digital_twin.py`'s own founding conflict, resolved directly by the founder via `AskUserQuestion` before any code was written: "every decision must first execute inside the Digital Twin" read as a mandatory approval gate, colliding with the same four permanently human-gated actions this document's own Company DNA protects (`INTEGRITY_RULES.md` §3). **The founder's answer: advisory preview only.** Proven, not just documented — a real regression test mocks `evolution_queue.approve_proposal` and `channels.publish_protection.check_publish_allowed` and asserts neither is ever called by any simulation path.

## What simulation has already changed, for real

Not hypothetical. `pricing_review.py`'s underlying evaluation logic (`economics.market_realism_check()`) is what caught the real $310 pricing error this session, before a single real customer saw the wrong number — the literal, already-proven value of "simulate before implementing," not an aspiration for this document to introduce.

---

*See also: `AUTONOMOUS_EVOLUTION_ENGINE.md`, `EVOLUTION_SCORE.md`, `DECISION_PROTOCOL.md`.*
