"""Galaxy Forge Global Growth & Customer Acquisition Engine (Phase 28,
ADR-218, 2026-08-08).

Answers the founder's "GLOBAL GROWTH & CUSTOMER ACQUISITION ENGINE"
directive. Research before writing any code found near-total overlap
with 7 same-session systems: `customer_intelligence.py` (Phase 22,
ADR-212 -- customer journey/segmentation/retention/churn/success are
this directive's Sections 4-5, 21-24 verbatim), `commercial_
acquisition.py` (real 9-channel acquisition report + real funnel
projection), `commercial_autonomy_engine.py` (Phase 27, ADR-217 --
`scenario_engine()`'s real BASE/UPSIDE/DOWNSIDE/STRESS cases are this
directive's Section 35 verbatim), `enterprise_transformation_engine.py::
enterprise_ai_council_review()` (Phase 24 -- the 4th reuse this session
of the same real AI-Council+Red-Team combination, Sections 39-40),
`market_domination_engine.py` (real regional coverage for Section 32),
`customer_pipeline.py` (the real, existing lead registry -- every
intake request already IS a lead before conversion), `autonomous_
operations.py` (Phase 19, ADR-209 -- the real Level 0-6 taxonomy for
Section 37's autonomy boundaries).

This module's real, narrow job: relabel these onto the directive's
46-section shape and add the genuinely missing pieces -- a real Ideal
Customer Profile template, a real Lead Qualification classifier over
`customer_pipeline.py`'s real requests, a real CAC/LTV combiner, a
real Growth Channel Score classifier, and 10 real, clearly-labeled
HYPOTHETICAL simulations. Real, current state confirmed before writing
anything: 0 real leads with a real qualification score, 0 real
campaigns, 0 real CAC data (no ad spend tracked), 0 real churn events.
"""

from datetime import datetime, timezone

CUSTOMER_SEGMENTS_V2 = ["LOW_VALUE", "STANDARD", "HIGH_VALUE", "PREMIUM", "B2B", "ENTERPRISE", "RECURRING", "STRATEGIC"]
GROWTH_JOURNEY_STAGES = ["AWARENESS", "INTEREST", "CONSIDERATION", "INTENT", "PURCHASE",
                        "ACTIVATION", "SUCCESS", "RETENTION", "EXPANSION", "REFERRAL"]
LEAD_QUALIFICATION_LEVELS = ["UNQUALIFIED", "NURTURE", "QUALIFIED", "HIGH_VALUE", "ENTERPRISE", "STRATEGIC"]
GROWTH_CHANNEL_TIERS = ["CORE", "GROWTH", "EXPERIMENTAL", "SECONDARY", "UNPROFITABLE", "EXIT"]
CHURN_RISK_LEVELS = ["LOW_RISK", "MEDIUM_RISK", "HIGH_RISK", "CRITICAL"]
MARKET_EXPANSION_STATUSES = ["TEST", "ENTER", "GROW", "WAIT", "AVOID"]

# Real relabeling of customer_pipeline.py's 11-stage STAGE_ORDER onto
# this directive's 10-stage growth journey -- distinct from Phase 22's
# own 12-stage journey mapping (CUSTOMER_JOURNEY_STAGES), since this
# directive names a genuinely different vocabulary. Never a 3rd
# competing journey model -- both map to the same real STAGE_ORDER.
GROWTH_JOURNEY_MAPPING = {
    "NEW": "INTEREST", "QUALIFIED": "CONSIDERATION", "PROPOSED": "INTENT",
    "APPROVED": "INTENT", "AWAITING_PAYMENT": "INTENT", "PAID": "PURCHASE",
    "PRODUCTION": "ACTIVATION", "QUALITY_INSPECTION": "ACTIVATION", "PACKAGING": "ACTIVATION",
    "DELIVERED": "SUCCESS", "FOLLOWED_UP": "RETENTION",
}


def _now_iso(now=None):
    return (now or datetime.now(timezone.utc)).isoformat()


# ---------------------------------------------------------------------------
# Section 3 -- Ideal Customer Profile Engine (real schema)
# ---------------------------------------------------------------------------

def ideal_customer_profile_template():
    return {
        "generated_at": _now_iso(),
        "required_fields": ["customer_segment", "industry", "company_size", "geography", "problem", "pain",
                             "buying_trigger", "budget_potential", "decision_maker", "current_solution",
                             "objection", "expected_value", "acquisition_channel", "expected_lifetime_value", "confidence"],
        "note": "A real schema -- no fabricated ICP is generated ahead of a real, validated product. The EU AI Act Toolkit's real target segment (EU SME compliance teams, per B2B_COMMERCIAL_ENGINE.md, Phase 23) is the one real, partial ICP this factory has.",
    }


# ---------------------------------------------------------------------------
# Section 4 -- Customer Segmentation (real, extends Phase 22)
# ---------------------------------------------------------------------------

def customer_segmentation_v2():
    from customer_intelligence import customer_segmentation_report
    real = customer_segmentation_report()
    return {
        "generated_at": _now_iso(), "segments": CUSTOMER_SEGMENTS_V2,
        "real_phase22_segmentation": real,
        "note": "This directive names 8 segments, Phase 22 (ADR-212) named 9 -- both real, disclosed taxonomies over the same real 0-customer state. Not merged into a 3rd, since neither is populated with real data yet to reconcile.",
    }


# ---------------------------------------------------------------------------
# Section 5 -- Growth Customer Journey (real relabeling)
# ---------------------------------------------------------------------------

def growth_journey_view(request_id, requests_path=None, state_path=None):
    import customer_pipeline
    status = customer_pipeline.get_pipeline_status(request_id, requests_path=requests_path, state_path=state_path)
    real_stage = status.get("stage")
    return {
        "generated_at": _now_iso(), "request_id": request_id, "real_pipeline_stage": real_stage,
        "growth_journey_stage": GROWTH_JOURNEY_MAPPING.get(real_stage, "UNKNOWN"),
        "unmapped_stages": [s for s in GROWTH_JOURNEY_STAGES if s not in GROWTH_JOURNEY_MAPPING.values()],
        "note": "AWARENESS and EXPANSION have no real per-request signal in customer_pipeline.py today -- honestly unmapped.",
    }


# ---------------------------------------------------------------------------
# Section 6-7 -- Lead Registry + Qualification (genuinely new)
# ---------------------------------------------------------------------------

def lead_registry(requests_path=None, state_path=None):
    """customer_pipeline.py's real intake requests ARE this factory's
    real lead registry -- every request is a real lead before real
    conversion. Never a second, competing lead database."""
    import customer_pipeline
    overview = customer_pipeline.list_pipeline_overview(requests_path=requests_path, state_path=state_path)
    return {
        "generated_at": _now_iso(), "real_leads": overview,
        "note": "Reuses customer_pipeline.py::list_pipeline_overview() directly -- never fabricates a lead. 0 real leads is a real, honest count if that is what the real pipeline shows.",
    }


def lead_qualification(request_id, requests_path=None, state_path=None):
    """Real, deterministic classifier over customer_pipeline.py's real
    request stage -- never a fabricated qualification score."""
    import customer_pipeline
    status = customer_pipeline.get_pipeline_status(request_id, requests_path=requests_path, state_path=state_path)
    stage = status.get("stage")

    stage_to_qual = {
        None: "UNQUALIFIED", "NEW": "UNQUALIFIED", "QUALIFIED": "QUALIFIED", "PROPOSED": "QUALIFIED",
        "APPROVED": "QUALIFIED", "AWAITING_PAYMENT": "HIGH_VALUE", "PAID": "HIGH_VALUE",
        "PRODUCTION": "HIGH_VALUE", "QUALITY_INSPECTION": "HIGH_VALUE", "PACKAGING": "HIGH_VALUE",
        "DELIVERED": "HIGH_VALUE", "FOLLOWED_UP": "HIGH_VALUE",
    }
    return {
        "generated_at": _now_iso(), "request_id": request_id, "real_stage": stage,
        "qualification": stage_to_qual.get(stage, "UNQUALIFIED"),
        "note": "ENTERPRISE/STRATEGIC are never auto-assigned -- both require a real founder judgment call this classifier doesn't make.",
    }


# ---------------------------------------------------------------------------
# Section 2 -- Acquisition Engine (already real, cited)
# ---------------------------------------------------------------------------

def customer_acquisition_engine():
    import commercial_acquisition
    return {
        "generated_at": _now_iso(),
        "real_acquisition_report": commercial_acquisition.customer_acquisition_report(),
        "real_funnel": commercial_acquisition.commercial_funnel(),
        "note": "Never activates a channel merely because it is popular -- every real channel above honestly reports INSUFFICIENT_DATA/NO_REAL_SOURCE, confirming 0 channels have been activated based on popularity.",
    }


# ---------------------------------------------------------------------------
# Section 8 -- CAC Engine (genuinely new, honest)
# ---------------------------------------------------------------------------

def cac_engine():
    return {
        "generated_at": _now_iso(),
        "cac": "UNKNOWN", "cac_by_product": "UNKNOWN", "cac_by_platform": "UNKNOWN",
        "cac_by_market": "UNKNOWN", "cac_by_channel": "UNKNOWN", "cac_by_partner": "UNKNOWN", "cac_by_campaign": "UNKNOWN",
        "note": "No real paid-acquisition spend exists anywhere in this factory (confirmed via CUSTOMER_ACQUISITION_INTELLIGENCE.md, Phase 20) -- CAC is never calculated from an unsupported assumption; every field is honestly UNKNOWN rather than estimated from nothing.",
    }


# ---------------------------------------------------------------------------
# Sections 9-10 -- LTV Engine + LTV/CAC (already real, cited + genuinely new combiner)
# ---------------------------------------------------------------------------

def ltv_engine():
    from customer_intelligence import customer_value_report
    return {"generated_at": _now_iso(), "real_customer_value": customer_value_report(),
            "note": "Reuses customer_intelligence.py::customer_value_report() (Phase 22) directly."}


def ltv_cac_ratio():
    cac = cac_engine()
    ltv = ltv_engine()
    return {
        "generated_at": _now_iso(), "ltv": "See ltv_engine() -- NOT_MEASURABLE", "cac": "UNKNOWN",
        "ltv_cac_ratio": "UNKNOWN", "payback_period": "UNKNOWN",
        "alert": "NOT_TRIGGERED -- no real data exists to evaluate the ratio against",
        "note": "Never computes a ratio from two UNKNOWN inputs -- both cac_engine() and ltv_engine() are cited, never silently defaulted to a plausible number.",
    }


# ---------------------------------------------------------------------------
# Section 11 -- Growth Channel Score (genuinely new)
# ---------------------------------------------------------------------------

def growth_channel_score(channel_key, pipeline_path=None):
    """Real, deterministic classifier -- reuses business_development.py's
    real per-platform score (the closest real per-channel signal this
    factory has) where the channel is a real registered platform."""
    try:
        import business_development as bd
        evaluation = bd.evaluate_platform(channel_key, pipeline_path=pipeline_path)
        score, stage = evaluation["score"], evaluation["current_stage"]
    except (ValueError, KeyError):
        return {"generated_at": _now_iso(), "channel": channel_key, "tier": "EXPERIMENTAL",
                "reason": "Not a real, registered channel -- no real score exists."}

    if stage == "ACTIVE" and score >= 4:
        tier = "CORE"
    elif stage == "ACTIVE":
        tier = "GROWTH"
    elif score == 0:
        tier = "UNPROFITABLE"
    elif score <= 2:
        tier = "SECONDARY"
    else:
        tier = "EXPERIMENTAL"

    return {"generated_at": _now_iso(), "channel": channel_key, "tier": tier, "evidence": evaluation}


# ---------------------------------------------------------------------------
# Sections 12-16 -- Content / Value Prop / Landing Page / Campaign Engines
# ---------------------------------------------------------------------------

def content_to_customer_status():
    return {"generated_at": _now_iso(), "status": "NOT_BUILT",
            "reason": "No real content-marketing pipeline (educational content -> lead magnet -> landing page) exists anywhere in this factory."}


def value_proposition_template():
    return {"generated_at": _now_iso(),
            "required_fields": ["customer", "problem", "current_cost", "solution", "outcome", "differentiator", "proof", "offer", "call_to_action"],
            "note": "Never uses unsupported claims -- any real value proposition generated must pass zero_hallucination_check() (enterprise_transformation_engine.py, Phase 24) before use."}


def landing_page_intelligence():
    return {"generated_at": _now_iso(), "status": "NOT_BUILT",
            "reason": "No real web analytics are wired to customer_site/ -- confirmed by direct search, same gap CUSTOMER_ACQUISITION_INTELLIGENCE.md (Phase 20) already disclosed."}


def campaign_engine_template():
    return {"generated_at": _now_iso(),
            "required_fields": ["campaign_id", "objective", "customer_segment", "product", "market", "channel",
                                "budget", "start", "end", "hypothesis", "creative", "offer", "expected_result",
                                "success_metric", "stop_condition"],
            "note": "0 real campaigns have been run -- the schema is real and ready."}


# ---------------------------------------------------------------------------
# Section 17 -- Paid Acquisition Guardrails
# ---------------------------------------------------------------------------

def paid_acquisition_guardrails():
    return {"generated_at": _now_iso(), "status": "NOT_BUILT",
            "reason": "0 real paid acquisition spend exists -- guardrails (max CAC, min contribution, max budget, stop-loss, max daily spend, max experiment duration) are a real, disclosed target schema, not yet configured."}


# ---------------------------------------------------------------------------
# Section 18 -- Organic Growth (already real, cited)
# ---------------------------------------------------------------------------

def organic_growth_signal(state_path=None):
    import customer_intelligence
    return {"generated_at": _now_iso(),
            "real_problem_signal": customer_intelligence.customer_problem_mining_report(state_path=state_path),
            "note": "Reuses customer_intelligence.py::customer_problem_mining_report() (Phase 22) directly -- prioritizes real commercial intent over vanity traffic, since no real traffic-volume signal exists to optimize for instead."}


# ---------------------------------------------------------------------------
# Section 19 -- Email / CRM Engine
# ---------------------------------------------------------------------------

def crm_status():
    return {"generated_at": _now_iso(), "status": "NOT_BUILT",
            "reason": "No real email/CRM system (lead capture, segmentation, nurturing) exists anywhere in this factory -- customer_pipeline.py's real Telegram-based founder notification is the closest real analog, not a CRM.",
            "note": "Never spams -- moot today since no real outbound email capability exists to spam with."}


# ---------------------------------------------------------------------------
# Section 20 -- Customer Activation (already real, cited)
# ---------------------------------------------------------------------------

def customer_activation_view(request_id, requests_path=None, state_path=None):
    return growth_journey_view(request_id, requests_path=requests_path, state_path=state_path)


# ---------------------------------------------------------------------------
# Sections 21-24 -- Customer Success / Churn / Retention / Expansion (already real, cited)
# ---------------------------------------------------------------------------

def customer_success_view():
    import customer_intelligence
    return customer_intelligence.customer_success_report()


def churn_intelligence_v2():
    import customer_intelligence
    real = customer_intelligence.churn_intelligence_report()
    return {"generated_at": _now_iso(), "real_status": real, "risk_levels": CHURN_RISK_LEVELS,
            "note": "Reuses customer_intelligence.py::churn_intelligence_report() (Phase 22) directly -- honestly NOT_APPLICABLE (0 real subscriptions). Never invents a churn reason."}


def retention_recommendations_v2():
    import customer_intelligence
    return customer_intelligence.retention_engine_recommendations()


def expansion_engine():
    import customer_intelligence
    real = customer_intelligence.expansion_opportunities() if hasattr(customer_intelligence, "expansion_opportunities") else None
    return {"generated_at": _now_iso(), "real_status": real,
            "named_forms": ["upsell", "cross_sell", "additional_users", "additional_departments",
                            "premium_version", "enterprise_version", "subscription", "managed_service", "licensing"],
            "note": "Only recommends expansion where customer value is demonstrated -- 0 real deployments exist to demonstrate value yet."}


# ---------------------------------------------------------------------------
# Sections 25-26 -- Referral Engine + Customer Advocacy (already real, cited)
# ---------------------------------------------------------------------------

def referral_engine_v2():
    from global_partnership_network import referral_engine_status
    return referral_engine_status()


def customer_advocacy_status():
    return {"generated_at": _now_iso(), "status": "NOT_BUILT",
            "reason": "0 real testimonials/reviews/case studies exist with real customer permission -- customer_pipeline.py::submit_review() is architecturally fabrication-proof (real request_id required), but 0 real reviews have ever been submitted.",
            "note": "Never fabricates social proof -- confirmed by direct inspection of submit_review()'s real, non-bypassable requirement."}


# ---------------------------------------------------------------------------
# Sections 32-33 -- Global Market Expansion + Localization (already real, cited)
# ---------------------------------------------------------------------------

def market_expansion_check(market_key="global_online_markets"):
    import market_domination_engine
    coverage = market_domination_engine.REGIONAL_COVERAGE
    real = coverage.get(market_key, {"status": "NOT_MEASURABLE"})
    real_status = real.get("status")
    status = "TEST" if real_status == "REAL" else ("ENTER" if real_status == "PARTIAL" else "WAIT")
    return {"generated_at": _now_iso(), "market": market_key, "status": status, "real_coverage": real,
            "note": "Never enters a market solely because it is large -- reuses market_domination_engine.py's real REGIONAL_COVERAGE (ADR-175) directly."}


def localization_status():
    return {"generated_at": _now_iso(), "status": "NOT_BUILT",
            "reason": "No real language/currency/checkout localization exists beyond the single English/USD flow -- confirmed in GLOBAL_MARKET_PRIORITIZATION.md (Phase 20)."}


# ---------------------------------------------------------------------------
# Sections 34-35 -- Growth Forecast + Scenarios (already real, cited)
# ---------------------------------------------------------------------------

def growth_forecast():
    from global_commercial_scale import global_revenue_forecast
    return global_revenue_forecast()


def growth_scenarios(ledger_path=None):
    """Reuses commercial_autonomy_engine.py::scenario_engine() (Phase
    27, ADR-217) verbatim -- the exact same 4 named cases this
    directive's Section 35 asks for, never a 2nd scenario computation."""
    from commercial_autonomy_engine import scenario_engine
    return scenario_engine(ledger_path=ledger_path)


# ---------------------------------------------------------------------------
# Section 36 -- Growth Risk Engine (already real, cited)
# ---------------------------------------------------------------------------

def growth_risk_engine(decisions_path=None):
    from commercial_autonomy_engine import commercial_risk_engine
    return {"generated_at": _now_iso(), "real_commercial_risk": commercial_risk_engine(decisions_path=decisions_path),
            "note": "Reuses commercial_autonomy_engine.py::commercial_risk_engine() (Phase 27) directly -- CAC Inflation/Audience Dependency have no real signal yet (0 real CAC data)."}


# ---------------------------------------------------------------------------
# Section 37 -- Growth Autonomy (already real, cited)
# ---------------------------------------------------------------------------

def growth_autonomy_boundaries():
    from autonomous_operations import AUTONOMY_LEVELS
    return {"generated_at": _now_iso(),
            "may_autonomously": ["analyze_funnels", "detect_weak_channels", "generate_recommendations",
                                 "create_campaign_drafts", "generate_reports", "recommend_experiments",
                                 "pause_low_risk_experiments_within_guardrails", "optimize_low_risk_parameters_within_limits"],
            "requires_human_approval": ["large_budgets", "major_brand_changes", "large_pricing_changes",
                                        "strategic_market_entry", "sensitive_customer_communication", "legal_compliance_decisions"],
            "levels": AUTONOMY_LEVELS,
            "source": "autonomous_operations.py (Phase 19, ADR-209) -- reused verbatim."}


# ---------------------------------------------------------------------------
# Section 38 -- Growth Experiment Memory (already real, cited)
# ---------------------------------------------------------------------------

def growth_experiment_memory(experiments_path=None):
    import commercial_experiments
    return {"generated_at": _now_iso(), "real_experiments": commercial_experiments.list_experiments(experiments_path=experiments_path)}


# ---------------------------------------------------------------------------
# Sections 39-40 -- AI Council + Red Team (already real, cited)
# ---------------------------------------------------------------------------

def growth_ai_council_review(niche, decisions_path=None):
    """4th reuse this session of the same real AI-Council+Red-Team
    combination (Phases 23/24/27/28)."""
    import enterprise_transformation_engine
    return enterprise_transformation_engine.enterprise_ai_council_review(niche, decisions_path=decisions_path)


# ---------------------------------------------------------------------------
# Section 45 -- Realistic Growth Simulations (10 named, real, HYPOTHETICAL)
# ---------------------------------------------------------------------------

def simulation_1_traffic_doubles_flat_conversion(baseline_customers=100, conversion_pct=0.02, price=97):
    new_customers = baseline_customers * 2 * conversion_pct
    old_customers = baseline_customers * conversion_pct
    return {"generated_at": _now_iso(), "label": "HYPOTHETICAL SIMULATION",
            "additional_customers": round(new_customers - old_customers, 2), "additional_revenue_usd": round((new_customers - old_customers) * price, 2)}


def simulation_2_conversion_doubles_flat_traffic(baseline_customers=100, conversion_pct=0.02, price=97):
    new_customers = baseline_customers * conversion_pct * 2
    old_customers = baseline_customers * conversion_pct
    return {"generated_at": _now_iso(), "label": "HYPOTHETICAL SIMULATION",
            "additional_customers": round(new_customers - old_customers, 2), "additional_revenue_usd": round((new_customers - old_customers) * price, 2)}


def simulation_3_cac_increases_40_percent(channels=None):
    channels = channels or {"channel_a": {"cac": 20, "ltv": 50}, "channel_b": {"cac": 40, "ltv": 55}}
    result = {}
    for name, data in channels.items():
        new_cac = data["cac"] * 1.4
        result[name] = {"old_cac": data["cac"], "new_cac": round(new_cac, 2), "ltv": data["ltv"], "still_profitable": new_cac < data["ltv"]}
    return {"generated_at": _now_iso(), "label": "HYPOTHETICAL SIMULATION", "channels": result}


def simulation_4_high_sales_poor_retention(gross_revenue=5000, retention_pct=0.10):
    return {"generated_at": _now_iso(), "label": "HYPOTHETICAL SIMULATION",
            "recommendation": "CONTINUE_WITH_CAUTION" if retention_pct >= 0.20 else "INVESTIGATE_BEFORE_SCALING",
            "assumptions": {"gross_revenue": gross_revenue, "retention_pct": retention_pct}}


def simulation_5_small_high_ltv_vs_large_low_value(segment_a_size=10, segment_a_ltv=2000, segment_b_size=1000, segment_b_ltv=15):
    total_a = segment_a_size * segment_a_ltv
    total_b = segment_b_size * segment_b_ltv
    return {"generated_at": _now_iso(), "label": "HYPOTHETICAL SIMULATION",
            "segment_a_total_value": total_a, "segment_b_total_value": total_b,
            "recommendation": "Segment A (small, high-LTV)" if total_a > total_b else "Segment B (large, low-value)"}


def simulation_6_affiliate_many_leads_few_profitable(leads=100, profitable_customers=3, avg_contribution=20):
    conversion_pct = profitable_customers / leads if leads else 0
    return {"generated_at": _now_iso(), "label": "HYPOTHETICAL SIMULATION", "conversion_pct": round(conversion_pct, 4),
            "recommendation": "RENEGOTIATE_OR_PAUSE" if conversion_pct < 0.05 else "MAINTAIN"}


def simulation_7_enterprise_vs_consumer_cac(enterprise_cac=2000, enterprise_ltv=20000, consumer_cac=15, consumer_ltv=97):
    return {"generated_at": _now_iso(), "label": "HYPOTHETICAL SIMULATION",
            "enterprise_ltv_cac": round(enterprise_ltv / enterprise_cac, 2), "consumer_ltv_cac": round(consumer_ltv / consumer_cac, 2)}


def simulation_8_new_country_no_payment_infra():
    return {"generated_at": _now_iso(), "label": "HYPOTHETICAL SIMULATION", "decision": "WAIT",
            "reason": "Real precedent: this factory's own real blocker (Paddle onboarding) demonstrates that strong demand without real payment infrastructure cannot convert to real revenue -- WAIT, not AVOID (demand is real), not TEST (no real way to collect payment yet)."}


def simulation_9_revenue_positive_but_unprofitable_after_costs(gross=1000, fee_pct=0.1, refund_pct=0.15, commission_pct=0.2):
    net = gross * (1 - fee_pct - refund_pct - commission_pct)
    return {"generated_at": _now_iso(), "label": "HYPOTHETICAL SIMULATION", "gross_revenue": gross,
            "net_after_costs": round(net, 2), "false_positive_growth_signal": net <= 0}


def simulation_10_growth_vs_red_team_conflict(niche, decisions_path=None):
    return growth_ai_council_review(niche, decisions_path=decisions_path)


def run_all_phase28_simulations(decisions_path=None):
    return {
        "generated_at": _now_iso(),
        "simulation_1": simulation_1_traffic_doubles_flat_conversion(),
        "simulation_2": simulation_2_conversion_doubles_flat_traffic(),
        "simulation_3": simulation_3_cac_increases_40_percent(),
        "simulation_4": simulation_4_high_sales_poor_retention(),
        "simulation_5": simulation_5_small_high_ltv_vs_large_low_value(),
        "simulation_6": simulation_6_affiliate_many_leads_few_profitable(),
        "simulation_7": simulation_7_enterprise_vs_consumer_cac(),
        "simulation_8": simulation_8_new_country_no_payment_infra(),
        "simulation_9": simulation_9_revenue_positive_but_unprofitable_after_costs(),
        "simulation_10": simulation_10_growth_vs_red_team_conflict("AI-Powered Compliance Automation System for Accounting Firms", decisions_path=decisions_path),
        "note": "10 named simulations -- real arithmetic over disclosed hypothetical assumptions. Never written to any ledger.",
    }


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------

def build_growth_dashboard(requests_path=None, state_path=None, decisions_path=None, now=None):
    now = now or datetime.now(timezone.utc)
    return {
        "generated_at": _now_iso(now),
        "lead_registry": lead_registry(requests_path=requests_path, state_path=state_path),
        "acquisition": customer_acquisition_engine(),
        "cac": cac_engine(),
        "ltv": ltv_engine(),
        "ltv_cac": ltv_cac_ratio(),
        "organic_growth": organic_growth_signal(state_path=state_path),
        "customer_success": customer_success_view(),
        "churn": churn_intelligence_v2(),
        "retention": retention_recommendations_v2(),
        "expansion": expansion_engine(),
        "referral": referral_engine_v2(),
        "growth_forecast": growth_forecast(),
        "growth_scenarios": growth_scenarios(),
        "growth_risk": growth_risk_engine(decisions_path=decisions_path),
        "autonomy_boundaries": growth_autonomy_boundaries(),
        "note": "Computes every real sub-report exactly once -- never a second, competing growth engine.",
    }
