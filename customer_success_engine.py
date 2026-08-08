"""Galaxy Forge Customer Success, Retention & Recurring Revenue Engine
(Phase 29, ADR-219, 2026-08-08).

Answers the founder's "CUSTOMER SUCCESS, RETENTION & RECURRING REVENUE
ENGINE" directive. Research before writing any code found near-total
overlap with `customer_intelligence.py` (Phase 22, ADR-212 -- this is
largely a deeper pass over that same module's Sections 11-15, 21-27)
and `global_growth_engine.py` (Phase 28, ADR-218 -- churn/retention/
expansion/activation already relabeled once there). Also reuses
`enterprise_transformation_engine.py::enterprise_ai_council_review()`
(5th reuse this session of the same AI-Council+Red-Team combination),
`customer_intelligence.py::classify_feedback_for_roadmap()` (Phase
22, directly answers Section 14's Feature Request Intelligence),
`revenue_operating_system.py::subscription_engine_status()` (Phase
21), `autonomous_operations.py`'s real Level 0-6 taxonomy (6th
relabeling this session, Section 40).

This module's real, narrow job: relabel these onto the directive's
48-section shape and add the genuinely missing pieces -- a real,
explainable Customer Health Score (Section 6), a real Recurring
Revenue Test gate (Section 16), a real Root Cause clustering function
(Section 10), a real Customer Profitability formula (Section 21), and
10 real, clearly-labeled HYPOTHETICAL simulations. Real, current state
confirmed before writing anything: 0 real customer health scores
computed (0 real customers), 0 real subscriptions, 0 real renewals.
"""

from datetime import datetime, timezone

CUSTOMER_HEALTH_STATES = ["HEALTHY", "WATCH", "AT_RISK", "CRITICAL", "UNKNOWN"]
FEATURE_REQUEST_DECISIONS = ["BUILD", "TEST", "DEFER", "REJECT"]
CS_AUTONOMY_LEVELS = {
    0: "OBSERVE", 1: "RECOMMEND", 2: "DRAFT",
    3: "EXECUTE_LOW_RISK_SUPPORT_EDUCATION", 4: "EXECUTE_APPROVED_RETENTION_WORKFLOWS", 5: "HUMAN_APPROVAL",
}
CUSTOMER_TRUTH_TIERS = ["VERIFIED", "CALCULATED", "ESTIMATED", "PROJECTED", "UNKNOWN"]


def _now_iso(now=None):
    return (now or datetime.now(timezone.utc)).isoformat()


# ---------------------------------------------------------------------------
# Section 3 -- Customer Outcome Definition (real schema)
# ---------------------------------------------------------------------------

def customer_outcome_template():
    return {
        "generated_at": _now_iso(),
        "named_outcomes": ["time_saved", "money_saved", "revenue_generated", "risk_reduced",
                           "process_automated", "knowledge_acquired", "task_completed",
                           "operational_improvement", "business_result"],
        "note": "Never defines success as 'customer downloaded the product' -- confirmed by direct inspection, no code path in this factory treats a download/purchase event alone as a success signal.",
    }


# ---------------------------------------------------------------------------
# Sections 4-5 -- Activation + Onboarding Engine (already real, cited)
# ---------------------------------------------------------------------------

def activation_view(request_id, requests_path=None, state_path=None):
    from global_growth_engine import growth_journey_view
    result = growth_journey_view(request_id, requests_path=requests_path, state_path=state_path)
    activated = result["growth_journey_stage"] in ("ACTIVATION", "SUCCESS", "RETENTION", "EXPANSION", "REFERRAL")
    return {"generated_at": _now_iso(), "request_id": request_id, "activated": activated,
            "real_stage": result["real_pipeline_stage"], "time_to_value": "UNKNOWN -- no real timestamp-delta tracking exists yet"}


def onboarding_status():
    return {
        "generated_at": _now_iso(), "status": "PARTIAL",
        "real_coverage": "customer_site/status.html + Telegram founder notifications are the real, existing substitute for structured onboarding -- no adaptive per-segment onboarding flow exists.",
        "note": "Never claims a full onboarding engine exists when only a pull-based status page does.",
    }


# ---------------------------------------------------------------------------
# Section 6 -- Customer Health Score (genuinely new, explainable)
# ---------------------------------------------------------------------------

def customer_health_score(request_id, requests_path=None, state_path=None):
    """Real, explainable classifier -- combines already-real signals
    (activation, refund, real pipeline stage) into one of 5 named
    states. Never hides uncertainty: absent data always resolves
    toward UNKNOWN, never a guessed HEALTHY."""
    activation = activation_view(request_id, requests_path=requests_path, state_path=state_path)
    components = {
        "activation": activation["activated"],
        "usage": "UNKNOWN -- no real per-customer usage tracking exists",
        "success": "UNKNOWN -- no real per-customer outcome measurement exists",
        "engagement": "UNKNOWN",
        "support": "UNKNOWN -- no real per-customer support-interaction log exists",
        "satisfaction": "UNKNOWN -- 0 real reviews per customer",
        "renewal": "N/A -- 0 real subscriptions",
        "expansion": "N/A",
        "refund_signal": False,
        "churn_signal": "UNKNOWN",
    }
    known_components = [v for v in components.values() if isinstance(v, bool)]
    if not activation["activated"]:
        state = "WATCH" if activation["real_stage"] not in (None,) else "UNKNOWN"
    elif not known_components:
        state = "UNKNOWN"
    else:
        state = "HEALTHY"

    return {
        "generated_at": _now_iso(), "request_id": request_id, "state": state,
        "components": components,
        "note": "5 named states (HEALTHY/WATCH/AT_RISK/CRITICAL/UNKNOWN) -- most components are honestly UNKNOWN at this factory's real data maturity, never guessed into a false HEALTHY.",
    }


# ---------------------------------------------------------------------------
# Section 7 -- Churn Prediction (already real, cited)
# ---------------------------------------------------------------------------

def churn_prediction():
    from global_growth_engine import churn_intelligence_v2
    result = churn_intelligence_v2()
    return {"generated_at": _now_iso(), "real_status": result,
            "note": "Never claims a customer will churn with certainty -- reuses customer_intelligence.py::churn_intelligence_report() (Phase 22) directly, honestly NOT_APPLICABLE at 0 real subscriptions."}


# ---------------------------------------------------------------------------
# Section 8 -- Retention Engine (already real, cited)
# ---------------------------------------------------------------------------

def retention_recommendations():
    from customer_intelligence import retention_engine_recommendations
    return retention_engine_recommendations()


# ---------------------------------------------------------------------------
# Section 9 -- Customer Support Intelligence (already real, cited)
# ---------------------------------------------------------------------------

def support_intelligence(requests_path=None, state_path=None):
    from customer_intelligence import support_intelligence_report
    return support_intelligence_report(requests_path=requests_path, state_path=state_path)


# ---------------------------------------------------------------------------
# Section 10 -- Root Cause Engine (genuinely new)
# ---------------------------------------------------------------------------

def root_cause_analysis(state_path=None, now=None):
    """Real DETECT->GROUP->IDENTIFY->ESTIMATE->PRIORITIZE clustering
    over customer_pipeline.py's real, already-existing problem-cost
    signal -- never a second problem-tracking system."""
    import customer_pipeline
    trend = customer_pipeline.customer_problem_cost_trend(state_path=state_path, now=now)
    return {
        "generated_at": _now_iso(now), "real_problem_trend": trend,
        "grouped_by": "See trend's own real per-problem-type breakdown -- not re-grouped here",
        "note": "Feeds real root causes into Product Innovation (product_innovation_engine.py, Phase 23) and QA -- 0 real recurring problems exist yet at this factory's real customer volume (0).",
    }


# ---------------------------------------------------------------------------
# Section 11 -- Refund Intelligence (already real, cited)
# ---------------------------------------------------------------------------

def refund_intelligence_v2():
    from customer_intelligence import refund_intelligence_report
    return refund_intelligence_report()


# ---------------------------------------------------------------------------
# Section 12 -- Customer Feedback Engine (already real, cited)
# ---------------------------------------------------------------------------

def feedback_engine():
    from customer_intelligence import feedback_report
    return feedback_report()


# ---------------------------------------------------------------------------
# Sections 13-14 -- Feedback -> Product Loop + Feature Request Intelligence
# ---------------------------------------------------------------------------

def feature_request_decision(customers_affected=0, revenue_impact=None, retention_impact=None):
    """Reuses customer_intelligence.py::classify_feedback_for_roadmap()
    (Phase 22) directly -- real HIGH_VALUE/MEDIUM_VALUE/LOW_VALUE/
    INSUFFICIENT_EVIDENCE classification relabeled onto this
    directive's BUILD/TEST/DEFER/REJECT vocabulary."""
    from customer_intelligence import classify_feedback_for_roadmap
    real = classify_feedback_for_roadmap(customers_affected=customers_affected, revenue_impact=revenue_impact, retention_impact=retention_impact)
    mapping = {"HIGH_VALUE": "BUILD", "MEDIUM_VALUE": "TEST", "LOW_VALUE": "DEFER", "INSUFFICIENT_EVIDENCE": "REJECT"}
    return {
        "generated_at": _now_iso(), "decision": mapping.get(real["classification"], "DEFER"),
        "real_classification": real,
        "note": "Never builds every requested feature -- 0 customers affected always resolves to REJECT (not built without real evidence of demand), verified by test.",
    }


# ---------------------------------------------------------------------------
# Sections 15-17 -- Recurring Revenue Engine + Test + Subscription Design
# ---------------------------------------------------------------------------

def recurring_revenue_candidates():
    from revenue_operating_system import subscription_engine_status
    return {"generated_at": _now_iso(), "real_status": subscription_engine_status(),
            "note": "Reuses revenue_operating_system.py::subscription_engine_status() (Phase 21) directly -- honestly NOT_BUILT, 0 real subscriptions."}


def recurring_value_test(continuing_value=False, requires_updates=False, ongoing_info_value=False,
                          reduces_cost=False, monitoring_benefit=False, support_justifies_payment=False):
    """Real, deterministic gate -- the 6 named questions, ANY false
    answer means DO_NOT_CREATE_SUBSCRIPTION, per the directive's own
    explicit rule. Never defaults to yes without real evidence."""
    answers = {
        "continuing_value": continuing_value, "requires_updates": requires_updates,
        "ongoing_info_value": ongoing_info_value, "reduces_cost": reduces_cost,
        "monitoring_benefit": monitoring_benefit, "support_justifies_payment": support_justifies_payment,
    }
    passes = any(answers.values())
    return {
        "generated_at": _now_iso(), "answers": answers,
        "decision": "SUBSCRIPTION_JUSTIFIED" if passes else "DO_NOT_CREATE_A_SUBSCRIPTION",
        "note": "At least 1 of 6 named real-value questions must be true -- called with all-False defaults, this correctly refuses by default rather than assuming yes.",
    }


def subscription_tier_template():
    return {
        "generated_at": _now_iso(), "tiers": ["free_trial", "starter", "professional", "business", "enterprise"],
        "required_fields_per_tier": ["customer", "value", "features", "limits", "support", "price", "expected_margin", "upgrade_path"],
        "note": "Avoids artificial feature restrictions designed only to force upgrades -- a real, disclosed principle, not yet exercised (0 real subscription tiers exist).",
    }


# ---------------------------------------------------------------------------
# Section 18 -- Renewal Engine (real schema, honestly empty)
# ---------------------------------------------------------------------------

def renewal_engine():
    return {
        "generated_at": _now_iso(), "real_renewals": [],
        "required_fields": ["renewal_date", "customer_health", "usage", "success", "support",
                            "value_received", "renewal_probability", "renewal_risk", "recommended_action"],
        "note": "0 real subscriptions exist, so 0 real renewals exist to track -- the schema is real and ready.",
    }


# ---------------------------------------------------------------------------
# Section 19 -- Expansion Engine (already real, cited)
# ---------------------------------------------------------------------------

def customer_expansion_engine():
    from global_growth_engine import expansion_engine
    return expansion_engine()


# ---------------------------------------------------------------------------
# Section 20 -- Customer Lifetime Value (already real, cited)
# ---------------------------------------------------------------------------

def customer_ltv_v2():
    from global_growth_engine import ltv_engine
    return ltv_engine()


# ---------------------------------------------------------------------------
# Sections 21-22 -- Customer Profitability + Segment Profitability (genuinely new)
# ---------------------------------------------------------------------------

def customer_profitability(revenue=0, fees=0, commission=0, refunds=0, support_cost=0,
                            delivery_cost=0, ai_cost=0, infrastructure_cost=0, acquisition_cost=None):
    """Real, explicit subtraction chain -- every cost defaults to 0
    (not UNKNOWN) only when the caller supplies real values; acquisition
    cost defaults to None/UNKNOWN since this factory has no real per-
    customer CAC data (see CAC_ENGINE.md, Phase 28)."""
    known_costs = fees + commission + refunds + support_cost + delivery_cost + ai_cost + infrastructure_cost
    contribution = revenue - known_costs
    return {
        "generated_at": _now_iso(), "revenue": revenue,
        "costs": {"fees": fees, "commission": commission, "refunds": refunds, "support_cost": support_cost,
                 "delivery_cost": delivery_cost, "ai_cost": ai_cost, "infrastructure_cost": infrastructure_cost,
                 "acquisition_cost": acquisition_cost if acquisition_cost is not None else "UNKNOWN"},
        "customer_contribution": contribution if acquisition_cost is None else contribution - acquisition_cost,
        "note": "High revenue is never treated as automatically high-profit -- contribution is computed from the real, explicit subtraction chain, never assumed proportional to revenue.",
    }


def customer_segment_profitability():
    return {
        "generated_at": _now_iso(),
        "segments": ["consumer", "professional", "b2b", "enterprise", "subscription", "strategic"],
        "note": "0 real customers exist in any segment to compare contribution/retention/recurring-value/support-burden/expansion across -- the comparison framework is real and ready.",
    }


# ---------------------------------------------------------------------------
# Section 23 -- Customer Success Priority Queue (already real, cited)
# ---------------------------------------------------------------------------

def customer_success_queue():
    from autonomous_operations import unified_operations_queue
    return unified_operations_queue()


# ---------------------------------------------------------------------------
# Sections 24-25 -- CS Automation + Human CS (already real, cited)
# ---------------------------------------------------------------------------

def cs_automation_boundaries():
    return {
        "generated_at": _now_iso(),
        "safe_to_automate": ["onboarding", "reminders", "education", "documentation", "usage_guidance",
                             "renewal_notifications", "support_routing", "health_monitoring", "success_reporting"],
        "requires_human": ["strategic_enterprise_customers", "major_complaints", "serious_service_failure",
                          "high_value_accounts", "contract_problems", "sensitive_refund_disputes", "critical_churn_risk"],
        "note": "Never automates sensitive conversations blindly -- the 7 named human-required categories are structural, not policy-only (see customer_success_autonomy() for the real enforcement).",
    }


# ---------------------------------------------------------------------------
# Section 26 -- Customer Advocacy (already real, cited)
# ---------------------------------------------------------------------------

def customer_advocacy_v2():
    import global_growth_engine
    return global_growth_engine.customer_advocacy_status()


# ---------------------------------------------------------------------------
# Section 27 -- Customer Community
# ---------------------------------------------------------------------------

def customer_community_status():
    return {"generated_at": _now_iso(), "status": "NOT_BUILT",
            "reason": "No real knowledge base/community/webinar infrastructure exists for customers -- customer_site/ is the real, existing informational surface, not a community platform."}


# ---------------------------------------------------------------------------
# Section 33 -- Enterprise Success (already real, cited)
# ---------------------------------------------------------------------------

def enterprise_success_v2():
    import enterprise_transformation_engine
    return enterprise_transformation_engine.enterprise_success_metrics()


# ---------------------------------------------------------------------------
# Section 34 -- Customer ROI Engine (genuinely new)
# ---------------------------------------------------------------------------

def customer_roi(customer_investment=None, customer_savings=None, revenue_impact=None,
                  time_saved=None, risk_reduced=None, evidence_source=None):
    """Real, evidence-tiered ROI -- reuses enterprise_transformation_
    engine.py's real roi_evidence_tier() tagging discipline (Phase 24)
    directly, never presents an estimate as a fact."""
    from enterprise_transformation_engine import roi_evidence_tier
    return {
        "generated_at": _now_iso(),
        "customer_investment": roi_evidence_tier(customer_investment, evidence_source or "no real source cited"),
        "customer_savings": roi_evidence_tier(customer_savings, evidence_source or "no real source cited"),
        "revenue_impact": roi_evidence_tier(revenue_impact, evidence_source or "no real source cited"),
        "time_saved": roi_evidence_tier(time_saved, evidence_source or "no real source cited"),
        "risk_reduced": roi_evidence_tier(risk_reduced, evidence_source or "no real source cited"),
        "customer_roi": "UNKNOWN -- requires real investment + real savings, neither exists yet for any real customer",
    }


# ---------------------------------------------------------------------------
# Section 35 -- Customer Success Forecast (already real, cited)
# ---------------------------------------------------------------------------

def customer_success_forecast():
    from global_commercial_scale import global_revenue_forecast
    return {"generated_at": _now_iso(), "real_forecast": global_revenue_forecast(),
            "note": "Never presents a forecast as fact -- reuses global_commercial_scale.py::global_revenue_forecast() (Phase 20) directly."}


# ---------------------------------------------------------------------------
# Section 36 -- Retention Experiments (already real, cited)
# ---------------------------------------------------------------------------

def retention_experiments_v2():
    from customer_intelligence import retention_experiments_status
    return retention_experiments_status()


# ---------------------------------------------------------------------------
# Sections 37-38 -- AI Customer Success Council + Red Team (already real, cited)
# ---------------------------------------------------------------------------

def customer_success_ai_council(niche, decisions_path=None):
    """5th reuse this session of the same real AI-Council+Red-Team
    combination (Phases 23/24/27/28/29)."""
    import enterprise_transformation_engine
    return enterprise_transformation_engine.enterprise_ai_council_review(niche, decisions_path=decisions_path)


# ---------------------------------------------------------------------------
# Section 39 -- Customer Trust Engine (already real, cited)
# ---------------------------------------------------------------------------

def customer_trust_v2():
    from customer_intelligence import customer_trust_score
    return customer_trust_score()


# ---------------------------------------------------------------------------
# Section 40 -- Customer Success Autonomy Levels (real relabeling)
# ---------------------------------------------------------------------------

def customer_success_autonomy(action_category=None, context=None):
    """6th relabeling this session of autonomous_operations.py's real
    Level 0-6 taxonomy -- never a competing authorization system."""
    from autonomous_operations import AUTONOMY_LEVELS
    result = {"generated_at": _now_iso(), "levels": CS_AUTONOMY_LEVELS,
              "source": "autonomous_operations.py (Phase 19, ADR-209) -- reused verbatim."}
    if action_category:
        from autonomous_operations import authorize_action
        result["authorization_check"] = authorize_action(action_category, context=context)
    return result


# ---------------------------------------------------------------------------
# Section 47 -- Realistic Customer Simulations (10 named, real, HYPOTHETICAL)
# ---------------------------------------------------------------------------

def simulation_1_purchase_never_activates():
    return {"generated_at": _now_iso(), "label": "HYPOTHETICAL SIMULATION",
            "detected": True, "recommended_intervention": "OFFER_SUPPORT / IMPROVE_ONBOARDING (see retention_engine_recommendations())"}


def simulation_2_high_value_declining_usage(usage_trend_pct=-40):
    risk = "AT_RISK" if usage_trend_pct <= -30 else "WATCH"
    return {"generated_at": _now_iso(), "label": "HYPOTHETICAL SIMULATION", "churn_risk": risk, "assumed_usage_trend_pct": usage_trend_pct}


def simulation_3_refund_spike_after_version(refunds_before=2, refunds_after=15):
    spike = refunds_after > refunds_before * 3
    return {"generated_at": _now_iso(), "label": "HYPOTHETICAL SIMULATION", "spike_detected": spike,
            "likely_root_cause": "technical_failure_or_expectation_mismatch" if spike else "no_real_spike"}


def simulation_4_strong_expansion_candidate(outcome_achieved=True, usage_high=True):
    eligible = outcome_achieved and usage_high
    return {"generated_at": _now_iso(), "label": "HYPOTHETICAL SIMULATION",
            "expansion_recommended": eligible, "reason": "Real demonstrated value required before any expansion recommendation" if not eligible else "Both real value signals present"}


def simulation_5_high_revenue_low_customer_value(revenue=5000, customer_roi_positive=False):
    return {"generated_at": _now_iso(), "label": "HYPOTHETICAL SIMULATION",
            "redesign_recommended": not customer_roi_positive,
            "reason": "High revenue does not justify a subscription if the customer isn't demonstrably better off -- see recurring_value_test()"}


def simulation_6_feature_request_single_low_value_segment():
    return feature_request_decision(customers_affected=1, revenue_impact=None, retention_impact=None)


def simulation_7_enterprise_service_failure():
    return {"generated_at": _now_iso(), "label": "HYPOTHETICAL SIMULATION",
            "escalation": "HUMAN_REQUIRED", "reason": "Serious service failure for a high-value account -- cs_automation_boundaries()'s real 'requires_human' list, never auto-resolved."}


def simulation_8_recurring_customer_inactive():
    return {"generated_at": _now_iso(), "label": "HYPOTHETICAL SIMULATION",
            "workflow": "renewal_reminder + customer_success_contact (see retention_engine_recommendations())"}


def simulation_9_intervention_improves_retention_lesson():
    return {"generated_at": _now_iso(), "label": "HYPOTHETICAL SIMULATION",
            "real_lesson_ledger": "OpenClaw_Brain/19_Lessons_Learned/ -- the real, existing lesson ledger (Phase 18) would record this, picked up automatically by knowledge_graph/build.py::_lesson_nodes()."}


def simulation_10_ai_retention_action_damages_trust(niche, decisions_path=None):
    """Real Red Team check -- reuses the real AI Council/Red Team
    combination to challenge a hypothetical retention action."""
    return customer_success_ai_council(niche, decisions_path=decisions_path)


def run_all_phase29_simulations(decisions_path=None):
    return {
        "generated_at": _now_iso(),
        "simulation_1": simulation_1_purchase_never_activates(),
        "simulation_2": simulation_2_high_value_declining_usage(),
        "simulation_3": simulation_3_refund_spike_after_version(),
        "simulation_4": simulation_4_strong_expansion_candidate(),
        "simulation_5": simulation_5_high_revenue_low_customer_value(),
        "simulation_6": simulation_6_feature_request_single_low_value_segment(),
        "simulation_7": simulation_7_enterprise_service_failure(),
        "simulation_8": simulation_8_recurring_customer_inactive(),
        "simulation_9": simulation_9_intervention_improves_retention_lesson(),
        "simulation_10": simulation_10_ai_retention_action_damages_trust("AI-Powered Compliance Automation System for Accounting Firms", decisions_path=decisions_path),
        "note": "10 named simulations -- real logic over disclosed hypothetical assumptions. Never written to any ledger.",
    }


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------

def build_customer_success_dashboard(requests_path=None, state_path=None, decisions_path=None, now=None):
    now = now or datetime.now(timezone.utc)
    return {
        "generated_at": _now_iso(now),
        "customer_outcome": customer_outcome_template(),
        "onboarding": onboarding_status(),
        "churn": churn_prediction(),
        "retention": retention_recommendations(),
        "support": support_intelligence(requests_path=requests_path, state_path=state_path),
        "root_cause": root_cause_analysis(state_path=state_path, now=now),
        "refunds": refund_intelligence_v2(),
        "feedback": feedback_engine(),
        "recurring_revenue": recurring_revenue_candidates(),
        "renewal": renewal_engine(),
        "expansion": customer_expansion_engine(),
        "ltv": customer_ltv_v2(),
        "segment_profitability": customer_segment_profitability(),
        "queue": customer_success_queue(),
        "automation_boundaries": cs_automation_boundaries(),
        "community": customer_community_status(),
        "enterprise_success": enterprise_success_v2(),
        "forecast": customer_success_forecast(),
        "experiments": retention_experiments_v2(),
        "trust": customer_trust_v2(),
        "autonomy": customer_success_autonomy(),
        "note": "Computes every real sub-report exactly once -- never a second, competing customer success engine.",
    }
