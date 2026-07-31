# ADR-161 — Enterprise Digital Twin

**Date:** 2026-07-31
**Status:** Adopted. Advisory-only preview/simulate/estimate/rollback layer built — never a production gate. Zero new products, departments, or external connections, per the directive's own opening prohibitions.

---

## The directive (verbatim)

> NEXT PHASE — ENTERPRISE DIGITAL TWIN
>
> Do not build new products. Do not add new departments. Do not connect external services.
>
> The next milestone is to build the Enterprise Digital Twin. The Digital Twin must become the brain's internal simulation world.
>
> Everything must exist twice: 1. REAL STATE 2. DIGITAL TWIN
>
> Every decision must first execute inside the Digital Twin. Only after successful simulation may it reach production.
>
> The Digital Twin must model: company state, departments, products, affiliate networks, marketplaces, customers, workflows, AI agents, financial flows, costs, expected revenue, inventory, publishing pipeline, legal compliance, risks, failures, recovery.
>
> Every production action must support: PREVIEW, SIMULATE, ESTIMATE IMPACT, ROLLBACK PLAN.
>
> The Twin must answer "What happens if...": Amazon changes policy? Affiliate network closes? Costs increase? AI provider fails? Product launch fails? Marketing doubles? Sales drop? New department appears?
>
> The Twin must calculate consequences before execution. No guessing. No fabricated numbers.
>
> Every simulation must clearly display: SIMULATION, ASSUMPTIONS, CONFIDENCE, UNKNOWNS.
>
> The Twin becomes the mandatory approval layer before production.
>
> Truth First Constitution remains the highest authority.

## Two real conflicts, resolved via AskUserQuestion before any code

**1. "Mandatory approval layer" vs. the standing human-gated-execution model.** "Every decision must first execute inside the Digital Twin. Only after successful simulation may it reach production" and "The Twin becomes the mandatory approval layer before production" read as an automated gate deciding whether real execution happens. This directly collides with the 4 founder-protected human-gates (evolution execute — ADR-133; capital reallocation — ADR-139; business retirement — ADR-134; new-channel/elevated-risk publishing — ADR-134/135) reconfirmed unchanged in ADR-142/144/147/157, and with the fact that every simulation this session has built (`growth_stages.py`, `strategic_planning.py`, `affiliate_commerce/simulation.py`, `enterprise_executive_brain.py::executive_scenario_simulator()`) is advisory-only — none of them blocks or authorizes anything.

**Founder's answer: advisory preview only.** `digital_twin.py` computes real PREVIEW/SIMULATE/ESTIMATE IMPACT/ROLLBACK PLAN citations for a human to review before they decide. It never itself calls a real approve/reject/publish/reallocate function, and no other module in this factory is wired to require its output before executing. This is stated as a hardcoded architectural fact in the module's own top docstring, in every dashboard response (`advisory_only: True`), and proven by a real regression test (`tests/test_digital_twin.py::TestAdvisoryOnlyArchitecture`, mocks `evolution_queue.approve_proposal`/`channels.publish_protection.check_publish_allowed` and asserts neither is ever called by the dashboard).

**2. Comprehensive 17-domain modeling vs. "no fabricated numbers."** This factory has $0 real revenue and thin real signal in several named domains — `enterprise_executive_brain.py::executive_scenario_simulator()` (ADR-156) had already found, the round before this one, that several adjacent what-if scenarios have no honest baseline to simulate from.

**Founder's answer: domains with real data only, rest honestly gapped.** Every gap in `digital_twin.py` uses exclusively `truth_first.CANONICAL_VOCABULARY`'s 9 named terms (ADR-160) — enforced by a real, mechanical assertion inside the module's own `_gap()` helper (`assert term in CANONICAL_VOCABULARY`) and re-verified end-to-end by a real test walking the module's actual output.

## What already existed — this round is mostly citation, not new subsystems

- **ROLLBACK PLAN**: `autonomous_business_builder.py::execution_phases()` (ADR-141) already has real, deterministic, company-wide per-stage `rollback_plan` strings (5 real stages matching `orchestrator.types.EXECUTION_ORDER`) — reused verbatim for the `publish` action type's `publishing` stage.
- **SIMULATE**: 3 real, already-built, overridable simulation functions — `growth_stages.simulate_stage_progression()` (ADR-158), `strategic_planning.simulate_roadmap_execution()` (ADR-159), `affiliate_commerce.simulation.run_simulation_cycle()` (ADR-153) — dispatched to by name, never re-implemented.
- **What-if scenarios**: `executive_scenario_simulator()` (ADR-156) already answers "costs increase" (`ai_cost_increase`) and "sales drop" (`revenue_growth`'s inverse framing) for real, and its own disclosed `NOT_ARCHITECTED` reasoning for `affiliate_expansion`/`traffic_spikes` was reused directly for "affiliate network closes"/"marketing doubles." `global_opportunity_exchange.ai_provider_concentration()` (ADR-140) is the real citation for "AI provider fails" — Groq is ~100% of real AI spend today, a real disclosed concentration finding, not a fabricated failure simulation.

## What was built

`digital_twin.py` (new, root) — the first module written after ADR-160, using the canonical vocabulary exclusively:

- `TWIN_DOMAINS` (17 named domains) + `_domain_real_state()` — real citation per domain; `inventory` is honestly `not_applicable` (a digital-products factory, no physical inventory concept exists or is claimed anywhere in this factory's real architecture).
- `twin_state_snapshot()` — Objective "everything must exist twice": `{real_state, digital_twin_state}` per domain. 3 domains (`company_state`, `affiliate_networks`, `workflows`) have a genuinely distinct, overridable twin state (`simulation_available: True`); the other 14 honestly mirror real state with `NOT IMPLEMENTED`.
- `PREVIEW_ACTIONS` (5 real, named production action types) + `preview_action(action_type, **params)` — dispatches to the real building blocks above; every hypothetical field tagged `SIMULATION`, every real gap tagged with the appropriate canonical term.
- `what_if_scenarios()` — the 8 named questions, real citations or honest gaps as above.
- `build_digital_twin_dashboard()` — the one real aggregator, `advisory_only: True` always.

**Mission Control**: `digital-twin-dashboard` (`SERVICE_REGISTRY`, 60s timeout, measured live ~39s) + `preview-production-action` (`ACTION_REGISTRY`, async, parameterized by `action_type`) + one panel in the existing Executive Overview group.

## What is explicitly NOT built

No automated production gate of any kind — the 4 protected human-gates and every other approval point in this factory are completely untouched. No new product, department, or external service connection (the directive's own opening prohibitions, honored literally). No fabricated model for `inventory` or for any what-if scenario with no real baseline.

## Validation

`python -m unittest tests.test_digital_twin -v` — 13/13 passing (199s, several real live calls): all 17 domains covered, `inventory` honestly `not_applicable`, the 3 simulation-capable domains correctly marked, every gap proven to use only the 9 canonical terms end-to-end, all 5 action types dispatchable, `capital_reallocation`'s preview/simulate/rollback proven honestly gapped while still calling the one real function it does have (`opportunity_cost()`), the advisory-only architecture proven via mock-and-assert-not-called on the real risky entry points. Live-verified against real current data: `twin_state_snapshot()` ~37s, `what_if_scenarios()` ~10s, all 5 `preview_action()` types return all 4 named fields. Full test suite re-run.
