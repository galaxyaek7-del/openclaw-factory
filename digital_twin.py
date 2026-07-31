#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Enterprise Digital Twin (ADR-161, 2026-07-31).

The founder's "NEXT PHASE — ENTERPRISE DIGITAL TWIN" directive, resolved
via two AskUserQuestion clarifications before any code was written:

1. "Every decision must first execute inside the Digital Twin... The
   Twin becomes the mandatory approval layer before production" read as
   an automated execution gate -- directly colliding with this factory's
   4 standing founder-protected human-gates (evolution execute, capital
   reallocation, business retirement, new-channel/elevated-risk
   publishing -- ADR-133/134/139/142, reconfirmed ADR-144/147/157) and
   every simulation this session has built being advisory-only.
   **Founder's answer: advisory preview only.** Nothing in this module
   ever calls a real approve/reject/publish/reallocate function, and no
   other module in this factory is wired to require this module's
   output before executing. This is a hardcoded architectural fact, not
   a policy note -- see build_digital_twin_dashboard()'s own docstring.

2. The directive names 17 domains to model with an explicit "no
   fabricated numbers" rule, against a factory with $0 real revenue and
   thin real signal in several domains. **Founder's answer: real data
   only, rest honestly gapped.** Every gap uses ONLY truth_first.
   CANONICAL_VOCABULARY's 9 named terms (ADR-160, ratified the round
   immediately before this one, "Truth First Constitution remains the
   highest authority" per this directive's own closing line) -- this is
   the first module written after that ratification and uses the
   canonical vocabulary exclusively, never a 10th ad-hoc synonym.

This factory already has substantial, real, partial "digital twin"
infrastructure -- this module's real job is unifying citation, not
building 17 new subsystems: SIMULATE reuses growth_stages.py (ADR-158),
strategic_planning.py (ADR-159), affiliate_commerce/simulation.py
(ADR-153) directly; ROLLBACK PLAN reuses autonomous_business_builder.py
::execution_phases()'s already-real per-stage rollback_plan citations
(ADR-141); the 8 named "what if" scenarios mostly cite enterprise_
executive_brain.py::executive_scenario_simulator() (ADR-156) and
global_opportunity_exchange.py::ai_provider_concentration() (ADR-140)
directly.
"""

from datetime import datetime, timezone

from truth_first import CANONICAL_VOCABULARY

NOT_BUILT = "NOT BUILT"
NOT_IMPLEMENTED = "NOT IMPLEMENTED"
NOT_CONNECTED = "NOT CONNECTED"
NOT_MEASURED = "NOT MEASURED"
UNKNOWN = "UNKNOWN"
WAITING_FOR_REAL_DATA = "WAITING FOR REAL DATA"
SIMULATION = "SIMULATION"
REFERENCE_IMPLEMENTATION = "REFERENCE IMPLEMENTATION"
PLANNED = "PLANNED"


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _gap(term, reason):
    assert term in CANONICAL_VOCABULARY, f"{term!r} is not one of the 9 canonical Truth First terms"
    return {"value": term, "reason": reason}


# The 17 founder-named domains -> the real function that answers each,
# or an honest, canonical-vocabulary gap. `inventory` is not a gap --
# this is a digital-products factory with no physical inventory concept
# anywhere in its real architecture, disclosed as such rather than
# force-fit into a fabricated stock-tracking model.
TWIN_DOMAINS = (
    "company_state", "departments", "products", "affiliate_networks", "marketplaces",
    "customers", "workflows", "ai_agents", "financial_flows", "costs", "expected_revenue",
    "inventory", "publishing_pipeline", "legal_compliance", "risks", "failures", "recovery",
)


def _domain_real_state(domain):
    if domain == "company_state":
        from company_runtime import company_state
        return {"answer": company_state(), "source": "company_runtime.py::company_state() (ADR-157)."}
    if domain == "departments":
        import gfos
        return {"answer": gfos.department_registry(), "source": "gfos.py::department_registry() (ADR-147)."}
    if domain == "products":
        import launch_readiness
        return {"answer": launch_readiness.launch_readiness_score(), "source": "launch_readiness.py::launch_readiness_score() (ADR-153)."}
    if domain == "affiliate_networks":
        import affiliate_commerce.click_tracking as click_tracking
        return {"answer": click_tracking.click_summary(), "source": "affiliate_commerce/click_tracking.py::click_summary() (ADR-149)."}
    if domain == "marketplaces":
        import global_opportunity_exchange as gox
        return {"answer": gox.marketplace_catalog(), "source": "global_opportunity_exchange.py::marketplace_catalog() (ADR-140)."}
    if domain == "customers":
        import customer_pipeline
        return {"answer": customer_pipeline.funnel_conversion_summary(), "source": "customer_pipeline.py::funnel_conversion_summary()."}
    if domain == "workflows":
        import gfos
        return {"answer": gfos.mission_lifecycle_summary(), "source": "gfos.py::mission_lifecycle_summary() (ADR-147) -- scheduler.py's real buckets + orchestrator.py's real stages."}
    if domain == "ai_agents":
        from ai_capability import registry as ai_registry
        return {"answer": ai_registry.list_providers(), "source": "ai_capability/registry.py -- the real Technology Investment Council."}
    if domain == "financial_flows":
        from channels import ledger
        return {"answer": ledger.revenue_trend(), "source": "channels/ledger.py::revenue_trend()."}
    if domain == "costs":
        import enterprise_executive_brain as eeb
        return {"answer": eeb._ai_cost_trailing_daily_avg(), "source": "enterprise_executive_brain.py::_ai_cost_trailing_daily_avg() (ADR-156), data/ai_cost_log.jsonl."}
    if domain == "expected_revenue":
        import capital_allocation_engine as cap
        return {"answer": cap.build_capital_allocation_dashboard()["expected_portfolio_return"], "source": "capital_allocation_engine.py::build_capital_allocation_dashboard()['expected_portfolio_return'] (ADR-139)."}
    if domain == "inventory":
        return {"answer": "not_applicable", "source": "This is a digital-products factory -- no physical inventory concept exists anywhere in this factory's real architecture (CLAUDE.md's own six-track vision). Not a gap to fill, a real structural fact."}
    if domain == "publishing_pipeline":
        from channels import publish_protection
        return {"answer": publish_protection.list_publish_protection_status(), "source": "channels/publish_protection.py::list_publish_protection_status() (ADR-134)."}
    if domain == "legal_compliance":
        import executive_quality_gate as eqg
        return {"answer": {"hard_reject_pipeline": eqg.REJECT_IF_FAIL}, "source": "executive_quality_gate.py::REJECT_IF_FAIL (ADR-160)."}
    if domain == "risks":
        import resilience_monitor
        return {"answer": resilience_monitor.assess_resilience(), "source": "resilience_monitor.py::assess_resilience() (ADR-136)."}
    if domain == "failures":
        import resilience_monitor
        return {"answer": resilience_monitor.list_incidents(), "source": "resilience_monitor.py::list_incidents() (ADR-136), data/incidents.jsonl."}
    if domain == "recovery":
        import factory_state
        state = factory_state.load_state()
        return {"answer": {"pending_retries": state.get("pending_retries"), "active_workflow": state.get("active_workflow")}, "source": "factory_state.py::load_state() (ADR-157's active_workflow bugfix)."}
    raise ValueError(f"unknown twin domain: {domain!r}")


# The 3 real, already-built overridable simulation functions this
# factory has -- the ONLY domains where digital_twin_state is genuinely
# a distinct, simulable model rather than a mirror of real_state.
_SIMULATION_CAPABLE_DOMAINS = {"company_state": "growth_stages", "workflows": "strategic_planning", "affiliate_networks": "affiliate_commerce"}


def twin_state_snapshot():
    """Objective 'everything must exist twice': real REAL STATE +
    DIGITAL TWIN per named domain. For the 3 domains with a real,
    already-built overridable simulation function, digital_twin_state is
    genuinely distinct (simulation_available: True). Every other domain
    honestly mirrors real_state with simulation_available: False and a
    canonical-vocabulary reason -- never a fabricated second model."""
    domains = {}
    for domain in TWIN_DOMAINS:
        real = _domain_real_state(domain)
        sim_module = _SIMULATION_CAPABLE_DOMAINS.get(domain)
        if sim_module:
            domains[domain] = {
                "real_state": real,
                "digital_twin_state": {
                    "simulation_available": True,
                    "source": f"{sim_module}.py's real simulate_*() function accepts hypothetical overrides -- see preview_action() below.",
                },
            }
        else:
            domains[domain] = {
                "real_state": real,
                "digital_twin_state": {
                    "simulation_available": False,
                    "value": NOT_IMPLEMENTED,
                    "reason": "No real, distinct simulable model exists for this domain -- the digital twin state mirrors real_state exactly until one is built.",
                    "mirrors_real_state": real["answer"],
                },
            }
    return {"domains": domains, "generated_at": _now_iso()}


# The 5 real, named production action types this factory actually has a
# preview/simulate/estimate/rollback story for -- never an invented
# action type with no real backing.
PREVIEW_ACTIONS = {
    "growth_stage_progression": {"preview": True, "simulate": True, "estimate_impact": True, "rollback_plan": False},
    "roadmap_execution": {"preview": True, "simulate": True, "estimate_impact": True, "rollback_plan": False},
    "affiliate_simulation_cycle": {"preview": True, "simulate": True, "estimate_impact": True, "rollback_plan": False},
    "publish": {"preview": True, "simulate": False, "estimate_impact": True, "rollback_plan": True},
    "capital_reallocation": {"preview": False, "simulate": False, "estimate_impact": True, "rollback_plan": False},
}

# autonomous_business_builder.py's own real, deterministic per-stage
# rollback_plan citations (ADR-141) -- reused verbatim, never re-derived.
# execution_phases() is company-wide (no niche param), 5 real stages
# matching orchestrator.types.EXECUTION_ORDER.
_ROLLBACK_STAGE_BY_ACTION = {"publish": "publishing"}


def preview_action(action_type, **params):
    """PREVIEW/SIMULATE/ESTIMATE IMPACT/ROLLBACK PLAN for one real,
    named production action type. Advisory only: never calls a real
    approve/reject/publish/reallocate function itself -- see this
    module's own top docstring for the founder-confirmed architecture.
    Every hypothetical field is tagged SIMULATION (ADR-160's canonical
    vocabulary); real citations are tagged with their own real source."""
    if action_type not in PREVIEW_ACTIONS:
        raise ValueError(f"unknown action_type: {action_type!r} -- expected one of {sorted(PREVIEW_ACTIONS)}")

    capabilities = PREVIEW_ACTIONS[action_type]
    result = {"action_type": action_type, "capabilities": capabilities}

    if action_type == "growth_stage_progression":
        import growth_stages
        result["preview"] = {"answer": growth_stages.current_growth_stage(), "source": "growth_stages.py::current_growth_stage() (ADR-158) -- real current state."}
        result["simulate"] = {SIMULATION: growth_stages.simulate_stage_progression(**params)}
        result["estimate_impact"] = {"answer": growth_stages.remaining_requirements_for_next_stage(), "source": "growth_stages.py::remaining_requirements_for_next_stage()."}
        result["rollback_plan"] = _gap(NOT_IMPLEMENTED, "current_growth_stage() is a stateless, non-cached classification (ADR-158) -- there is no real state change to roll back.")

    elif action_type == "roadmap_execution":
        import strategic_planning
        import growth_stages
        result["preview"] = {"answer": strategic_planning.rolling_roadmap(), "source": "strategic_planning.py::rolling_roadmap() (ADR-159) -- real current roadmap."}
        result["simulate"] = {SIMULATION: strategic_planning.simulate_roadmap_execution(**params)}
        result["estimate_impact"] = {"answer": growth_stages.highest_roi_action_to_advance(), "source": "growth_stages.py::highest_roi_action_to_advance() (ADR-158), reused directly by strategic_planning.py."}
        result["rollback_plan"] = _gap(NOT_IMPLEMENTED, "The roadmap is a read-only recomputation (ADR-159) -- there is no real state change to roll back.")

    elif action_type == "affiliate_simulation_cycle":
        from affiliate_commerce import simulation as affiliate_sim
        result["preview"] = {"answer": affiliate_sim.simulation_funnel_report(), "source": "affiliate_commerce/simulation.py::simulation_funnel_report() (ADR-153) -- real current simulated funnel."}
        result["simulate"] = {SIMULATION: affiliate_sim.run_simulation_cycle()}
        result["estimate_impact"] = {"answer": affiliate_sim.simulation_funnel_report(), "source": "Same real simulated funnel report -- ADR-153's own disclosed assumed conversion/commission rates."}
        result["rollback_plan"] = {"answer": "AFFILIATE_MODE back to 'simulation' is a pure config revert -- production code paths (networks.py/click_tracking.py/products.py) are never touched by simulation.", "source": "simulation_mode.py (ADR-153)."}

    elif action_type == "publish":
        from channels import publish_protection
        arm_name = params.get("arm_name")
        result["preview"] = (
            {"answer": publish_protection.check_publish_allowed(arm_name), "source": "channels/publish_protection.py::check_publish_allowed() (ADR-134) -- the real pre-publish gate, dry-run exempt."}
            if arm_name else _gap(UNKNOWN, "pass arm_name= to preview a specific real arm's publish_protection state.")
        )
        result["simulate"] = _gap(NOT_BUILT, "distributor.py's real dry_run=True default (never a distinct labeled SIMULATION output) is the closest real analog -- no separate publish simulator exists.")
        result["estimate_impact"] = _gap(WAITING_FOR_REAL_DATA, "No real closed-sale revenue exists yet for any niche to estimate a real publish impact from (config/reality.json).")
        import autonomous_business_builder as abb
        stage_name = _ROLLBACK_STAGE_BY_ACTION["publish"]
        phases = abb.execution_phases()["phases"]
        stage_entry = next((p for p in phases if p["phase"] == stage_name), None)
        result["rollback_plan"] = (
            {"answer": stage_entry["rollback_plan"], "source": "autonomous_business_builder.py::execution_phases() (ADR-141) -- real, deterministic, company-wide per-stage rollback citation (orchestrator.types.EXECUTION_ORDER's 'publishing' stage)."}
            if stage_entry else _gap(UNKNOWN, f"no {stage_name!r} stage found in execution_phases()'s real output.")
        )

    elif action_type == "capital_reallocation":
        result["preview"] = _gap(NOT_IMPLEMENTED, "capital_allocation_engine.py never automatically reallocates -- 'the engine recommends, the Founder decides' (ADR-139) -- no preview state exists because no automated action exists to preview.")
        result["simulate"] = _gap(NOT_BUILT, "No simulation exists for a decision this factory has never automated.")
        import capital_allocation_engine as cap
        result["estimate_impact"] = {"answer": cap.opportunity_cost(), "source": "capital_allocation_engine.py::opportunity_cost() (ADR-139) -- real, already-computed impact citation."}
        result["rollback_plan"] = _gap(NOT_IMPLEMENTED, "No real automated reallocation exists to roll back -- this is a human decision, not a code path.")

    result["generated_at"] = _now_iso()
    return result


def what_if_scenarios():
    """The 8 named 'what happens if...' questions. Reuses enterprise_
    executive_brain.py::executive_scenario_simulator()'s real 3
    HYPOTHETICAL projections + its own disclosed NOT_ARCHITECTED
    reasoning for overlapping sibling scenarios, plus global_
    opportunity_exchange.py::ai_provider_concentration() and gfos.py::
    department_registry() directly -- never a second, competing
    scenario engine."""
    import enterprise_executive_brain as eeb
    import global_opportunity_exchange as gox
    import gfos

    scenarios = eeb.executive_scenario_simulator()
    ai_concentration = gox.ai_provider_concentration()
    departments = gfos.department_registry()

    return {
        "amazon_changes_policy": _gap(NOT_CONNECTED, "KDP has zero live registered channel arm today (CLAUDE.md) -- no real Amazon policy dependency exists to model impact from yet. Amazon Associates (affiliate_commerce/) does have a real dependency: AMAZON_ASSOCIATE_TAG, currently unset (ADR-149)."),
        "affiliate_network_closes": {
            **_gap(WAITING_FOR_REAL_DATA, "Same real reasoning executive_scenario_simulator() already applies to affiliate_expansion: this would require projecting off already-SIMULATED affiliate data (ADR-153) -- two layers removed from real revenue, not honest to present as a scenario result."),
        },
        "costs_increase": {
            "answer": scenarios["ai_cost_increase"],
            "source": "enterprise_executive_brain.py::executive_scenario_simulator()['ai_cost_increase'] (ADR-156) -- real HYPOTHETICAL projection off data/ai_cost_log.jsonl's real trailing average.",
        },
        "ai_provider_fails": {
            "answer": ai_concentration,
            "source": "global_opportunity_exchange.py::ai_provider_concentration() (ADR-140) -- a real, disclosed single-point-of-failure finding (Groq is ~100% of real AI spend today), not a fabricated failure simulation.",
        },
        "product_launch_fails": _gap(REFERENCE_IMPLEMENTATION, "inspectors.py's Dual Inspection + QUARANTINE.md already record every real launch-blocking failure this factory has ever had -- a real, working example, but not wired into a forward-looking 'what if the next launch fails' projection."),
        "marketing_doubles": {
            **_gap(NOT_MEASURED, scenarios["traffic_spikes"]["reason"]),
        },
        "sales_drop": {
            "answer": scenarios["revenue_growth"],
            "source": "enterprise_executive_brain.py::executive_scenario_simulator()['revenue_growth'] (ADR-156) -- same real baseline/technique, a negative assumed_growth_pct answers this question's inverse framing.",
        },
        "new_department_appears": {
            "answer": departments,
            "source": "gfos.py::department_registry() (ADR-147) -- the real, static 12-department roster. Departments are code, not data-driven, so a dynamic 'what if a new one appears' has no real mechanism to simulate.",
            "gap": _gap(NOT_IMPLEMENTED, "No real mechanism exists to dynamically add a department -- this is an engineering task, not a simulable business event."),
        },
        "generated_at": _now_iso(),
    }


def build_digital_twin_dashboard():
    """The one real aggregator. ARCHITECTURAL FACT, not a policy note:
    this function is advisory/read-only. It never calls a real
    approve/reject/publish/reallocate function, and no other module in
    this factory is wired to require its output before executing. The
    4 founder-protected human-gates (evolution execute, capital
    reallocation, business retirement, new-channel/elevated-risk
    publishing) and every other approval point are completely
    untouched by this module."""
    return {
        "twin_state": twin_state_snapshot(),
        "what_if_scenarios": what_if_scenarios(),
        "preview_actions_available": PREVIEW_ACTIONS,
        "advisory_only": True,
        "note": "This dashboard never authorizes or blocks any real action -- it is a real, disclosed citation layer for a human to consult before they decide, exactly like every other simulation this factory has built.",
        "generated_at": _now_iso(),
    }
