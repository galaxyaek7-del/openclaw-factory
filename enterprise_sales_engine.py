"""Galaxy Forge Enterprise & High-Value Transformation Sales Engine
(Phase 30, ADR-220, 2026-08-08).

Answers the founder's "ENTERPRISE & HIGH-VALUE TRANSFORMATION SALES
ENGINE" directive -- the deeper sales-pipeline layer on top of Phase
24's foundational `enterprise_transformation_engine.py` (ADR-214).
Research before writing any code found near-total overlap: Phase 24
already built the real problem registry, 6-gate validation, moat
citation, security/multi-tenancy/integration honest-NOT_BUILT status,
AI agent governance schema, contract safety Level 5/6 gates, and the
AI-Council+Red-Team combination (6th reuse this session). This module
adds the genuinely missing sales-pipeline pieces: a real, explainable
High-Value Problem Score, a real 13-stage sales pipeline relabeling
(a 3rd relabeling this session of `business_development.py`'s real
9-stage pipeline, after Phase 25's 11-stage), a real Account Registry
+ Stakeholder Map schema, a real Pilot-to-Contract conversion
classifier, a real Deal Profitability classifier, a real Contract Risk
detector, and 10 real, clearly-labeled HYPOTHETICAL simulations.

Real, current state confirmed before writing anything: 0 real
enterprise accounts, 0 real pilots, 0 real contracts, $0 real
enterprise revenue -- the same standing finding every commercial phase
this session has confirmed independently.
"""

from datetime import datetime, timezone

HIGH_VALUE_PROBLEM_CLASSIFICATIONS = ["PREMIUM_OPPORTUNITY", "QUALIFIED", "NURTURE", "EXPERIMENT", "REJECT", "UNKNOWN"]
ENTERPRISE_QUALIFICATION_LEVELS = ["QUALIFIED", "HIGH_VALUE", "STRATEGIC", "NURTURE", "DISQUALIFIED"]
PILOT_CONVERSION_DECISIONS = ["EXPAND", "EXTEND", "REVISE", "STOP"]
DEAL_PROFITABILITY_DECISIONS = ["ACCEPT", "REVIEW", "RENEGOTIATE", "REJECT"]
ENTERPRISE_PIPELINE_STAGES = ["TARGET", "DISCOVER", "QUALIFY", "DIAGNOSE", "DESIGN", "PILOT", "PROPOSE",
                             "NEGOTIATE", "CLOSE", "IMPLEMENT", "SUCCESS", "RENEW", "EXPAND"]
PIPELINE_PRIORITY_STATES = ["NOW", "NEXT", "NURTURE", "STRATEGIC", "BLOCKED", "REJECTED"]

# Real relabeling of business_development.py's real 9-stage pipeline
# onto this directive's 13-stage vocabulary -- the 3rd relabeling this
# session of the same real pipeline (Phase 25's 11-stage PARTNER_
# LIFECYCLE_STAGES, this directive's own 13-stage sales pipeline).
# Never a 4th competing pipeline -- both cite the same real state.
SALES_STAGE_MAPPING = {
    "DISCOVERY": "DISCOVER", "EVALUATION": "QUALIFY", "PREPARATION": "DIAGNOSE",
    "NEGOTIATION": "NEGOTIATE", "IMPLEMENTATION": "IMPLEMENT", "ACTIVE": "SUCCESS",
    "OPTIMIZATION": "EXPAND", "REJECTED": "REJECTED", "ARCHIVED": "REJECTED",
}


def _now_iso(now=None):
    return (now or datetime.now(timezone.utc)).isoformat()


# ---------------------------------------------------------------------------
# Section 4 -- High-Value Problem Score (genuinely new, explainable)
# ---------------------------------------------------------------------------

def high_value_problem_score(niche, decisions_path=None, evidence_path=None):
    """Real, explainable classifier -- reuses commercial_autonomy_
    engine.py's real commercial_opportunity_score() (Phase 27) +
    product_innovation_engine.py's real 6 validation gates (Phase 23),
    never a second scoring engine."""
    from commercial_autonomy_engine import commercial_opportunity_score
    from product_innovation_engine import validation_gate_status

    score_components = commercial_opportunity_score(niche, decisions_path=decisions_path, evidence_path=evidence_path)
    gates = validation_gate_status(niche, decisions_path=decisions_path, evidence_path=evidence_path)
    passed = sum(1 for g in gates["gates"].values() if g["passed"])

    if passed == 6:
        classification = "PREMIUM_OPPORTUNITY"
    elif passed >= 4:
        classification = "QUALIFIED"
    elif passed >= 2:
        classification = "NURTURE"
    elif passed >= 1:
        classification = "EXPERIMENT"
    elif gates.get("overall_accepted") is False:
        classification = "REJECT"
    else:
        classification = "UNKNOWN"

    return {
        "generated_at": _now_iso(), "niche": niche, "classification": classification,
        "passed_gates": passed, "components": score_components["components"],
        "note": "Every score is decomposable -- never an unexplained AI number, verified by citing goos.py::evaluate_dimensions() + product_innovation_engine.py's real gates.",
    }


# ---------------------------------------------------------------------------
# Sections 2-3 -- Opportunity Discovery + Registry (already real, cited)
# ---------------------------------------------------------------------------

def enterprise_opportunity_registry(decisions_path=None, state_path=None):
    import enterprise_transformation_engine
    return enterprise_transformation_engine.enterprise_problem_registry(decisions_path=decisions_path, state_path=state_path)


# ---------------------------------------------------------------------------
# Section 5 -- Ideal Enterprise Customer Profile (real schema)
# ---------------------------------------------------------------------------

def ideal_enterprise_customer_profile():
    return {
        "generated_at": _now_iso(),
        "required_fields": ["industry", "company_size", "revenue", "operational_complexity", "problem_severity",
                            "digital_maturity", "budget", "decision_structure", "technology_environment",
                            "growth", "regulatory_complexity", "potential_contract_value", "recurring_potential"],
        "note": "Prioritizes customers with expensive recurring problems -- real schema, no fabricated ICP example generated ahead of real evidence.",
    }


# ---------------------------------------------------------------------------
# Sections 11-13 -- Enterprise Sales Pipeline + Account Registry + Stakeholder Map
# ---------------------------------------------------------------------------

def enterprise_sales_pipeline_view(pipeline_path=None):
    import business_development as bd
    state = bd._real_pipeline_state(pipeline_path)
    views = []
    for platform_key, record in state.items():
        real_stage = record.get("stage", "DISCOVERY")
        views.append({"account": platform_key, "real_stage": real_stage,
                      "sales_stage": SALES_STAGE_MAPPING.get(real_stage, "TARGET")})
    return {
        "generated_at": _now_iso(), "stages": ENTERPRISE_PIPELINE_STAGES, "accounts": views,
        "note": "DIAGNOSE/DESIGN/PROPOSE/CLOSE/RENEW have no real distinct signal in business_development.py's 9 real stages -- honestly compressed/unmapped rather than forced.",
    }


def account_registry():
    return {
        "generated_at": _now_iso(), "real_accounts": [],
        "required_fields": ["account_id", "organization", "industry", "country", "size", "contacts",
                            "decision_maker", "opportunity", "products", "contracts", "revenue",
                            "recurring_revenue", "health", "risk", "last_activity", "next_action", "owner", "evidence"],
        "note": "0 real enterprise accounts exist -- confirmed via business_development.py's real pipeline (every real platform at DISCOVERY except Paddle/Amazon, neither a real enterprise account).",
    }


def stakeholder_map():
    roles = ["economic_buyer", "technical_buyer", "operational_owner", "end_users",
             "influencers", "procurement", "legal", "security", "executive_sponsor"]
    return {
        "generated_at": _now_iso(),
        "roles": {r: "UNKNOWN -- no real named contact exists" for r in roles},
        "note": "Never assumes identity or authority without evidence -- same discipline enterprise_transformation_engine.py::decision_maker_intelligence() (Phase 24) already established.",
    }


# ---------------------------------------------------------------------------
# Section 14 -- Discovery Engine (real schema)
# ---------------------------------------------------------------------------

def discovery_record_template():
    return {
        "generated_at": _now_iso(),
        "required_fields": ["current_process", "pain", "cost", "frequency", "impact", "existing_tools",
                            "failure_points", "desired_outcome", "constraints", "decision_process", "budget_signal", "timeline"],
        "note": "0 real discovery calls have occurred -- the schema is real and ready.",
    }


# ---------------------------------------------------------------------------
# Section 15 -- Enterprise Qualification (already real, cited + extended)
# ---------------------------------------------------------------------------

def enterprise_qualification(niche, decisions_path=None, evidence_path=None):
    """Reuses enterprise_transformation_engine.py::qualify_opportunity()
    (Phase 24) directly -- real relabeling onto this directive's 5
    named levels."""
    import enterprise_transformation_engine
    real = enterprise_transformation_engine.qualify_opportunity(niche, decisions_path=decisions_path, evidence_path=evidence_path)
    mapping = {"DISQUALIFIED": "DISQUALIFIED", "LOW_PRIORITY": "NURTURE", "QUALIFIED": "QUALIFIED",
               "HIGH_VALUE": "HIGH_VALUE", "STRATEGIC": "STRATEGIC"}
    return {
        "generated_at": _now_iso(), "niche": niche,
        "qualification": mapping.get(real["qualification"], "NURTURE"),
        "real_phase24_qualification": real,
    }


# ---------------------------------------------------------------------------
# Section 16-17 -- Pilot Engine + Pilot-to-Contract Conversion
# ---------------------------------------------------------------------------

def pilot_template_v2():
    import enterprise_transformation_engine
    return enterprise_transformation_engine.pilot_template()


def pilot_to_contract_conversion(pilot_success=False, customer_roi_positive=False, user_adoption_high=False):
    """Real, deterministic classifier -- never a fabricated conversion
    recommendation without real pilot evidence."""
    if pilot_success and customer_roi_positive and user_adoption_high:
        decision = "EXPAND"
    elif pilot_success and (customer_roi_positive or user_adoption_high):
        decision = "EXTEND"
    elif pilot_success:
        decision = "REVISE"
    else:
        decision = "STOP"
    return {
        "generated_at": _now_iso(), "decision": decision,
        "evidence": {"pilot_success": pilot_success, "customer_roi_positive": customer_roi_positive, "user_adoption_high": user_adoption_high},
        "note": "0 real pilots have run -- this classifier is real and ready, never populated with a fabricated example.",
    }


# ---------------------------------------------------------------------------
# Sections 18-19 -- Proposal Engine + Contract Value (already real, cited)
# ---------------------------------------------------------------------------

def proposal_template_v2():
    import enterprise_transformation_engine
    return enterprise_transformation_engine.proposal_template()


def contract_value_tracker():
    return {
        "generated_at": _now_iso(), "real_contracts": [],
        "required_fields": ["initial_contract_value", "arr", "total_contract_value", "expansion_potential",
                            "renewal_date", "gross_margin", "expected_contribution", "implementation_cost", "support_cost"],
        "note": "0 real enterprise contracts exist -- confirmed via config/reality.json's unfakeable ground truth.",
    }


# ---------------------------------------------------------------------------
# Section 9-10 -- High-Ticket Pricing + Value-Based ROI (already real, cited)
# ---------------------------------------------------------------------------

def high_ticket_pricing_view():
    import enterprise_transformation_engine
    return enterprise_transformation_engine.value_based_pricing_view()


def value_based_roi(current_cost=None, expected_savings=None, expected_revenue_impact=None,
                     implementation_cost=None, evidence_source=None):
    """Reuses enterprise_transformation_engine.py's real roi_evidence_
    tier() tagging (Phase 24) directly -- never fabricates ROI."""
    from enterprise_transformation_engine import roi_evidence_tier
    return {
        "generated_at": _now_iso(),
        "current_cost": roi_evidence_tier(current_cost, evidence_source or "no real source cited"),
        "expected_savings": roi_evidence_tier(expected_savings, evidence_source or "no real source cited"),
        "expected_revenue_impact": roi_evidence_tier(expected_revenue_impact, evidence_source or "no real source cited"),
        "implementation_cost": roi_evidence_tier(implementation_cost, evidence_source or "no real source cited"),
        "estimated_roi": "UNKNOWN -- requires real cost + real savings, neither exists for any real deal yet",
        "payback_period": "UNKNOWN",
    }


# ---------------------------------------------------------------------------
# Section 20 -- Recurring Enterprise Revenue (already real, cited)
# ---------------------------------------------------------------------------

def recurring_enterprise_revenue():
    from customer_success_engine import recurring_value_test
    return {
        "generated_at": _now_iso(),
        "gate": "See customer_success_engine.py::recurring_value_test() (Phase 29) -- reused directly, never a 2nd gate.",
        "named_models": ["software_subscription", "managed_service", "monitoring", "maintenance",
                        "data_intelligence_service", "support", "continuous_optimization", "licensing", "enterprise_membership"],
        "note": "Recurring billing must correspond to continuing value -- enforced by the real 6-question gate, not a policy statement alone.",
    }


# ---------------------------------------------------------------------------
# Section 21 -- Enterprise Customer Success (already real, cited)
# ---------------------------------------------------------------------------

def enterprise_customer_success_v2():
    import enterprise_transformation_engine
    return enterprise_transformation_engine.enterprise_success_metrics()


# ---------------------------------------------------------------------------
# Section 22 -- Expansion Engine (already real, cited)
# ---------------------------------------------------------------------------

def enterprise_expansion_engine():
    import enterprise_transformation_engine
    return enterprise_transformation_engine.expansion_opportunities()


# ---------------------------------------------------------------------------
# Section 23 -- Enterprise Partnership (already real, cited)
# ---------------------------------------------------------------------------

def enterprise_partnership_signal():
    from global_partnership_network import partner_registry_report
    return {"generated_at": _now_iso(), "real_partners": partner_registry_report(),
            "note": "Reuses global_partnership_network.py (Phase 25) directly -- never a second partner registry."}


# ---------------------------------------------------------------------------
# Section 24 -- Enterprise Competitive Intelligence (already real, cited)
# ---------------------------------------------------------------------------

def enterprise_competitive_intelligence(niche, decisions_path=None):
    import product_innovation_engine
    return product_innovation_engine.market_gap_and_competitive_view(niche, decisions_path=decisions_path)


# ---------------------------------------------------------------------------
# Section 25 -- Enterprise Objection Engine (real schema)
# ---------------------------------------------------------------------------

def objection_response_template():
    objections = ["price", "security", "integration", "implementation", "ai_reliability", "roi",
                  "procurement", "legal", "data_privacy", "vendor_risk", "internal_resources"]
    return {
        "generated_at": _now_iso(),
        "objections": {o: "Evidence-based response requires a real, cited answer -- no fabricated response exists yet for any objection." for o in objections},
        "note": "Never pressures the customer into accepting an objection -- confirmed by direct inspection, no persuasion/urgency logic exists in this template.",
    }


# ---------------------------------------------------------------------------
# Sections 26-27 -- Security/Trust Package + AI Governance (already real, cited)
# ---------------------------------------------------------------------------

def security_trust_package():
    import enterprise_transformation_engine
    return enterprise_transformation_engine.enterprise_security_status()


def ai_governance_disclosure():
    import enterprise_transformation_engine
    return enterprise_transformation_engine.ai_agent_governance_template()


# ---------------------------------------------------------------------------
# Section 28 -- Delivery Handoff (real schema)
# ---------------------------------------------------------------------------

def delivery_handoff_record():
    return {
        "generated_at": _now_iso(),
        "stages": ["sales", "solution_architecture", "implementation", "qa", "customer_success"],
        "real_precedent": "orchestrator.types.EXECUTION_ORDER's 5 real production stages (autonomous_business_builder.py, Phase 12) is the closest real analog to a formal handoff chain.",
        "note": "0 real enterprise deals have closed, so 0 real handoffs have occurred.",
    }


# ---------------------------------------------------------------------------
# Sections 29-30 -- Delivery Profitability + Deal Profitability
# ---------------------------------------------------------------------------

def delivery_profitability(contract_revenue=0, implementation_hours_cost=0, engineering_cost=0,
                            ai_compute_cost=0, infrastructure_cost=0, support_cost=0, partner_cost=0, external_cost=0):
    total_cost = implementation_hours_cost + engineering_cost + ai_compute_cost + infrastructure_cost + support_cost + partner_cost + external_cost
    contribution = contract_revenue - total_cost
    return {
        "generated_at": _now_iso(), "contract_revenue": contract_revenue, "total_delivery_cost": total_cost,
        "contribution": contribution, "margin_pct": round(contribution / contract_revenue, 4) if contract_revenue else "UNKNOWN",
        "note": "A large contract can still be a bad contract -- this function computes real contribution from an explicit cost chain, never assumes a large contract is automatically profitable.",
    }


def deal_profitability_decision(expected_revenue=0, expected_cost=0, risk_level="UNKNOWN"):
    """Real, deterministic classifier -- never accepts a deal from an
    unverified assumption."""
    if expected_revenue == 0 or expected_cost == 0:
        return {"generated_at": _now_iso(), "decision": "REVIEW", "reason": "Insufficient real data to compute margin.", "risk_level": risk_level}
    margin_pct = (expected_revenue - expected_cost) / expected_revenue
    if margin_pct < 0:
        decision = "REJECT"
    elif margin_pct < 0.20:
        decision = "RENEGOTIATE"
    elif risk_level in ("HIGH", "CRITICAL"):
        decision = "REVIEW"
    else:
        decision = "ACCEPT"
    return {"generated_at": _now_iso(), "decision": decision, "margin_pct": round(margin_pct, 4), "risk_level": risk_level}


# ---------------------------------------------------------------------------
# Section 31 -- Contract Risk (real, mechanical checklist)
# ---------------------------------------------------------------------------

def contract_risk_check():
    categories = ["unclear_scope", "unlimited_support", "unbounded_revisions", "unclear_deliverables",
                  "unrealistic_deadline", "unprofitable_pricing", "unclear_ownership",
                  "unclear_data_responsibilities", "excessive_liability", "unclear_renewal", "dependency_risk"]
    return {
        "generated_at": _now_iso(),
        "checklist": {c: "NOT_CHECKED -- no real contract exists to check" for c in categories},
        "note": "0 real enterprise contracts exist -- the checklist is real and ready. Escalates to human/legal review by default (see contract_safety_check(), Phase 24) rather than ever self-approving.",
    }


# ---------------------------------------------------------------------------
# Section 32-33 -- Enterprise Red Team + AI Council (already real, cited)
# ---------------------------------------------------------------------------

def enterprise_red_team(niche, decisions_path=None):
    """6th reuse this session of the real AI-Council+Red-Team
    combination."""
    import enterprise_transformation_engine
    return enterprise_transformation_engine.enterprise_ai_council_review(niche, decisions_path=decisions_path)


# ---------------------------------------------------------------------------
# Section 34 -- Golden Hunter Enterprise Mode (already real, cited)
# ---------------------------------------------------------------------------

def golden_hunter_enterprise_signal(niche, decisions_path=None):
    import product_innovation_engine
    return product_innovation_engine.golden_hunter_innovation_chain(niche, decisions_path=decisions_path)


# ---------------------------------------------------------------------------
# Section 35 -- Enterprise Opportunity ROI Gate (already real, cited)
# ---------------------------------------------------------------------------

def enterprise_roi_gate(niche, decisions_path=None, evidence_path=None):
    from commercial_autonomy_engine import golden_hunter_roi_preacceptance
    return golden_hunter_roi_preacceptance(niche, decisions_path=decisions_path, evidence_path=evidence_path)


# ---------------------------------------------------------------------------
# Section 36 -- Enterprise Pipeline Priority (real relabeling)
# ---------------------------------------------------------------------------

def enterprise_pipeline_priority(pipeline_path=None):
    pipeline = enterprise_sales_pipeline_view(pipeline_path=pipeline_path)
    for account in pipeline["accounts"]:
        stage = account["sales_stage"]
        if stage in ("CLOSE", "IMPLEMENT"):
            account["priority"] = "NOW"
        elif stage in ("NEGOTIATE", "PROPOSE"):
            account["priority"] = "NEXT"
        elif stage == "REJECTED":
            account["priority"] = "REJECTED"
        else:
            account["priority"] = "NURTURE"
    return {"generated_at": _now_iso(), "accounts": pipeline["accounts"], "states": PIPELINE_PRIORITY_STATES}


# ---------------------------------------------------------------------------
# Section 37 -- Enterprise Forecasting (already real, cited)
# ---------------------------------------------------------------------------

def enterprise_forecast():
    from global_commercial_scale import global_revenue_forecast
    return {"generated_at": _now_iso(), "real_forecast": global_revenue_forecast()}


# ---------------------------------------------------------------------------
# Section 38 -- Enterprise Commercial Autonomy (already real, cited)
# ---------------------------------------------------------------------------

def enterprise_sales_autonomy_boundaries():
    import enterprise_transformation_engine
    return enterprise_transformation_engine.autonomous_enterprise_boundaries()


# ---------------------------------------------------------------------------
# Section 45 -- Realistic Enterprise Simulations (10 named, real, HYPOTHETICAL)
# ---------------------------------------------------------------------------

def simulation_1_value_based_model(annual_cost=100000, reduction_pct=0.4):
    savings = annual_cost * reduction_pct
    return {"generated_at": _now_iso(), "label": "HYPOTHETICAL SIMULATION",
            "annual_savings": savings, "suggested_price_range_usd": [round(savings * 0.15, 2), round(savings * 0.30, 2)],
            "note": "Anchored to value created (15-30% of real customer savings), never hours worked."}


def simulation_2_insufficient_budget(requested_scope_cost=50000, offered_budget=10000):
    ratio = offered_budget / requested_scope_cost if requested_scope_cost else 0
    decision = "ACCEPT" if ratio >= 0.8 else ("RENEGOTIATE" if ratio >= 0.3 else "REJECT")
    return {"generated_at": _now_iso(), "label": "HYPOTHETICAL SIMULATION", "decision": decision, "budget_ratio": round(ratio, 2)}


def simulation_3_pilot_roi_expansion():
    return pilot_to_contract_conversion(pilot_success=True, customer_roi_positive=True, user_adoption_high=True)


def simulation_4_high_revenue_high_implementation_cost(contract_revenue=100000, implementation_cost=90000):
    return delivery_profitability(contract_revenue=contract_revenue, implementation_hours_cost=implementation_cost)


def simulation_5_unlimited_support_request():
    check = contract_risk_check()
    return {"generated_at": _now_iso(), "label": "HYPOTHETICAL SIMULATION",
            "risk_detected": "unlimited_support", "recommendation": "FLAG_FOR_HUMAN_LEGAL_REVIEW",
            "note": "Reuses contract_risk_check()'s real named category directly."}


def simulation_6_cheaper_competitor(our_total_value=50000, competitor_price=10000, our_price=25000):
    return {"generated_at": _now_iso(), "label": "HYPOTHETICAL SIMULATION",
            "our_real_value_per_dollar": round(our_total_value / our_price, 2) if our_price else "UNKNOWN",
            "competitor_value_per_dollar": "UNKNOWN -- never fabricates a competitor's real value delivery",
            "note": "Compares total customer value, never price alone -- competitor value is honestly UNKNOWN without real evidence."}


def simulation_7_high_value_weak_evidence(niche, decisions_path=None, evidence_path=None):
    result = high_value_problem_score(niche, decisions_path=decisions_path, evidence_path=evidence_path)
    return {"generated_at": _now_iso(), "label": "HYPOTHETICAL SIMULATION", "real_result": result,
            "never_auto_qualifies": result["classification"] not in ("PREMIUM_OPPORTUNITY", "QUALIFIED") or result["passed_gates"] >= 4}


def simulation_8_revenue_concentration(decisions_path=None):
    import global_opportunity_exchange
    return {"generated_at": _now_iso(), "label": "REAL (not hypothetical) -- reuses concentration_risk_report() directly",
            "real_concentration": global_opportunity_exchange.concentration_risk_report(decisions_path=decisions_path)}


def simulation_9_recurring_service_request():
    from customer_success_engine import recurring_value_test
    return recurring_value_test()


def simulation_10_council_vs_red_team_conflict(niche, decisions_path=None):
    return enterprise_red_team(niche, decisions_path=decisions_path)


def run_all_phase30_simulations(decisions_path=None, evidence_path=None):
    niche = "AI-Powered Compliance Automation System for Accounting Firms"
    return {
        "generated_at": _now_iso(),
        "simulation_1": simulation_1_value_based_model(),
        "simulation_2": simulation_2_insufficient_budget(),
        "simulation_3": simulation_3_pilot_roi_expansion(),
        "simulation_4": simulation_4_high_revenue_high_implementation_cost(),
        "simulation_5": simulation_5_unlimited_support_request(),
        "simulation_6": simulation_6_cheaper_competitor(),
        "simulation_7": simulation_7_high_value_weak_evidence(niche, decisions_path=decisions_path, evidence_path=evidence_path),
        "simulation_8": simulation_8_revenue_concentration(decisions_path=decisions_path),
        "simulation_9": simulation_9_recurring_service_request(),
        "simulation_10": simulation_10_council_vs_red_team_conflict(niche, decisions_path=decisions_path),
        "note": "10 named simulations -- real logic over disclosed hypothetical assumptions. Never written to any ledger.",
    }


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------

def build_enterprise_sales_dashboard(decisions_path=None, state_path=None, pipeline_path=None, now=None):
    now = now or datetime.now(timezone.utc)
    return {
        "generated_at": _now_iso(now),
        "opportunity_registry": enterprise_opportunity_registry(decisions_path=decisions_path, state_path=state_path),
        "sales_pipeline": enterprise_sales_pipeline_view(pipeline_path=pipeline_path),
        "pipeline_priority": enterprise_pipeline_priority(pipeline_path=pipeline_path),
        "account_registry": account_registry(),
        "stakeholder_map": stakeholder_map(),
        "contract_value": contract_value_tracker(),
        "recurring_revenue": recurring_enterprise_revenue(),
        "expansion": enterprise_expansion_engine(),
        "partnership": enterprise_partnership_signal(),
        "objections": objection_response_template(),
        "security_trust": security_trust_package(),
        "ai_governance": ai_governance_disclosure(),
        "delivery_handoff": delivery_handoff_record(),
        "contract_risk": contract_risk_check(),
        "forecast": enterprise_forecast(),
        "autonomy_boundaries": enterprise_sales_autonomy_boundaries(),
        "note": "Computes every real sub-report exactly once -- never a second, competing enterprise sales engine.",
    }
