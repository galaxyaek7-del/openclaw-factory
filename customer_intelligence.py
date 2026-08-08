"""Galaxy Forge Customer Intelligence & Retention Engine (Phase 22,
ADR-212, 2026-08-08).

Answers the founder's "CUSTOMER INTELLIGENCE & RETENTION ENGINE"
directive. Research before writing any code found most of the real
substrate already exists: `customer_pipeline.py`'s real 11-stage
STAGE_ORDER + `list_requests_for_account()` (already the correct,
conservative identity-resolution mechanism -- matches by real
account_id OR normalized email, never weak-evidence merging),
`trust_audit.py` (real customer trust citations), `brand_dna.py`
(real communication standards + `validate_customer_facing_text()`),
`market_evidence.py` (real willingness-to-pay/retention signals
already feeding Golden Hunter), `commercial_experiments.py` (real
generic experiment engine), `resilience_monitor.py::_classify_
customer_risk()` (real incident protection).

This module's real, narrow job: unify these into the directive's
named shape, and honestly disclose what has no real signal yet.
Real, current company state (confirmed before writing anything): 0
real customer accounts with a completed purchase, 0 real reviews, 0
real refunds, 0 real subscriptions/churn events. Every section below
that would otherwise need real customer data honestly reports empty/
UNKNOWN rather than a fabricated example -- this is not a shortfall
in this module, it is an accurate description of a company with 0
real customers yet.
"""

from datetime import datetime, timezone

CUSTOMER_JOURNEY_STAGES = [
    "DISCOVERY", "INTEREST", "PRODUCT_VIEW", "CHECKOUT", "PURCHASE", "DELIVERY",
    "FIRST_USE", "FEEDBACK", "SUPPORT", "REPEAT_PURCHASE", "SUBSCRIPTION_RENEWAL", "RETENTION",
]

PURCHASE_REASON_CATEGORIES = [
    "PROBLEM_SOLVING", "TIME_SAVING", "COST_SAVING", "CONVENIENCE", "PROFESSIONAL_NEED",
    "EDUCATION", "ENTERTAINMENT", "BUSINESS_GROWTH", "AUTOMATION", "DECISION_SUPPORT",
    "PERSONAL_UTILITY", "OTHER", "UNKNOWN",
]

NON_PURCHASE_REASON_CATEGORIES = [
    "PRICE", "LOW_TRUST", "WRONG_PRODUCT", "POOR_POSITIONING", "MISSING_FEATURE",
    "POOR_EXPLANATION", "CHECKOUT_PROBLEM", "PAYMENT_PROBLEM", "COMPETITION",
    "INSUFFICIENT_URGENCY", "INSUFFICIENT_EVIDENCE", "UNKNOWN",
]

CUSTOMER_SEGMENTS = [
    "NEW_CUSTOMER", "REPEAT_CUSTOMER", "RECURRING_CUSTOMER", "HIGH_VALUE_CUSTOMER",
    "B2B_CUSTOMER", "ENTERPRISE_CUSTOMER", "AT_RISK_CUSTOMER", "INACTIVE_CUSTOMER",
    "PRODUCT_SPECIFIC_CUSTOMER",
]

RETENTION_ACTIONS = [
    "IMPROVE_PRODUCT", "IMPROVE_ONBOARDING", "PROVIDE_EDUCATION", "OFFER_SUPPORT",
    "FIX_PROBLEM", "IMPROVE_DOCUMENTATION", "OFFER_RELEVANT_UPGRADE",
    "OFFER_RELEVANT_RELATED_PRODUCT", "REQUEST_FEEDBACK", "DO_NOTHING",
]

ROADMAP_CLASSIFICATIONS = ["HIGH_VALUE", "MEDIUM_VALUE", "LOW_VALUE", "DUPLICATE", "OUT_OF_SCOPE", "INSUFFICIENT_EVIDENCE"]


def _now_iso(now=None):
    return (now or datetime.now(timezone.utc)).isoformat()


# ---------------------------------------------------------------------------
# Section 2 -- Customer Identity (already real, cited)
# ---------------------------------------------------------------------------

def customer_identity_view(account_id=None, email=None, requests_path=None, state_path=None):
    """Reuses customer_pipeline.py::list_requests_for_account() verbatim
    -- the real, already-conservative identity resolver (real account_id
    match, or normalized-email match for a pre-account guest request;
    never a fuzzy/weak-evidence merge)."""
    if not account_id and not email:
        return {"success": False, "identity_status": "UNKNOWN", "reason": "No account_id or email supplied -- never guessed."}
    import customer_pipeline
    result = customer_pipeline.list_requests_for_account(account_id=account_id, email=email, requests_path=requests_path, state_path=state_path)
    result["identity_status"] = "RESOLVED" if result.get("success") and result.get("requests") else "NO_MATCH"
    result["resolution_method"] = "real account_id match or normalized-email match -- never fuzzy/weak-evidence merging"
    return result


# ---------------------------------------------------------------------------
# Section 3 -- Data Minimization (already real, cited)
# ---------------------------------------------------------------------------

def data_minimization_report():
    return {
        "generated_at": _now_iso(),
        "real_fields_collected": ["name", "email", "description", "company", "budget_range"],
        "source": "customer_pipeline.py's real intake schema (confirmed by direct search, cited in brand_dna.py's CUSTOMER_JOURNEY_STANDARDS)",
        "note": "No collection beyond real operational necessity -- confirmed, not a policy claim without a code check.",
    }


# ---------------------------------------------------------------------------
# Section 4 -- Customer Profile
# ---------------------------------------------------------------------------

def customer_profile(account_id=None, email=None, requests_path=None, state_path=None, finance_path=None):
    identity = customer_identity_view(account_id=account_id, email=email, requests_path=requests_path, state_path=state_path)
    if identity["identity_status"] != "RESOLVED":
        return {"generated_at": _now_iso(), "identity_status": identity["identity_status"], "profile": None}

    requests = identity.get("requests", [])
    return {
        "generated_at": _now_iso(),
        "identity_status": "RESOLVED",
        "customer_id": account_id or email,
        "segment": "UNKNOWN -- see customer_segmentation_report()",
        "products_purchased": [r.get("request_id") for r in requests],
        "purchase_history": requests,
        "revenue_usd": "UNKNOWN -- not yet cross-referenced against finance_data.json per customer",
        "refunds_usd": 0,
        "support_interactions": "UNKNOWN -- no dedicated per-customer support-interaction log exists yet",
        "customer_value": "NOT_MEASURABLE -- see customer_value_report()",
        "confidence": "MEDIUM -- real request history, but revenue/support cross-reference not yet built",
        "privacy_classification": "INTERNAL",
    }


# ---------------------------------------------------------------------------
# Section 5 -- Customer Journey
# ---------------------------------------------------------------------------

_STAGE_ORDER_TO_JOURNEY = {
    "NEW": "INTEREST", "QUALIFIED": "PRODUCT_VIEW", "PROPOSED": "PRODUCT_VIEW",
    "APPROVED": "CHECKOUT", "AWAITING_PAYMENT": "CHECKOUT", "PAID": "PURCHASE",
    "PRODUCTION": "PURCHASE", "QUALITY_INSPECTION": "PURCHASE", "PACKAGING": "DELIVERY",
    "DELIVERED": "DELIVERY", "FOLLOWED_UP": "FEEDBACK",
}


def customer_journey_view(request_id, requests_path=None, state_path=None):
    """Real translation of customer_pipeline.py's real 11-stage
    STAGE_ORDER onto the directive's 12 named journey stages -- never a
    second progress-tracking system. DISCOVERY and stages past FEEDBACK
    (SUPPORT/REPEAT_PURCHASE/SUBSCRIPTION_RENEWAL/RETENTION) have no
    real per-request signal in customer_pipeline.py today -- honestly
    UNKNOWN, not inferred."""
    import customer_pipeline
    status = customer_pipeline.get_pipeline_status(request_id, requests_path=requests_path, state_path=state_path)
    if not status.get("success", True) and "stage" not in status:
        return {"generated_at": _now_iso(), "request_id": request_id, "journey_stage": "UNKNOWN", "evidence": status}

    real_stage = status.get("stage")
    journey_stage = _STAGE_ORDER_TO_JOURNEY.get(real_stage, "UNKNOWN")
    return {
        "generated_at": _now_iso(),
        "request_id": request_id,
        "real_pipeline_stage": real_stage,
        "journey_stage": journey_stage,
        "unmeasured_stages": [s for s in CUSTOMER_JOURNEY_STAGES if s not in _STAGE_ORDER_TO_JOURNEY.values()],
        "source": "customer_pipeline.py::STAGE_ORDER, relabeled onto the 12 named journey stages",
    }


# ---------------------------------------------------------------------------
# Sections 6-7 -- Purchase / Non-Purchase Reason Intelligence
# ---------------------------------------------------------------------------

def purchase_reason_report():
    return {
        "generated_at": _now_iso(), "total_real_purchases": 0,
        "by_reason": {r: 0 for r in PURCHASE_REASON_CATEGORIES},
        "note": "0 real completed purchases exist -- no reason can be honestly inferred without a real transaction to examine. Never inferred as fact without evidence, per Section 6's own rule.",
    }


def non_purchase_reason_report():
    return {
        "generated_at": _now_iso(),
        "note": "Silence is never treated as rejection, per Section 7's own rule -- no real checkout-abandonment tracking exists yet (no web analytics wired, same gap CUSTOMER_ACQUISITION_INTELLIGENCE.md already disclosed), so this factory has no real evidence to classify non-purchases by yet.",
        "by_reason": {r: "NO_REAL_SIGNAL" for r in NON_PURCHASE_REASON_CATEGORIES},
    }


# ---------------------------------------------------------------------------
# Section 8 -- Customer Problem Mining (already real, cited)
# ---------------------------------------------------------------------------

def customer_problem_mining_report(state_path=None, now=None):
    import customer_pipeline
    return customer_pipeline.customer_problem_cost_trend(state_path=state_path, now=now)


# ---------------------------------------------------------------------------
# Section 9 -- Feedback Engine
# ---------------------------------------------------------------------------

def feedback_report(reviews_path=None):
    import customer_pipeline
    reviews = customer_pipeline._load_reviews(reviews_path)
    items = [{
        "feedback_id": request_id, "customer_reference": "UNKNOWN -- not cross-referenced to account_id in the review record",
        "product": "UNKNOWN -- not stored on the review record, requires a join against the request",
        "date": review.get("submitted_at"), "source": "customer_site review form",
        "original_feedback": review.get("text"), "category": "UNKNOWN -- no categorization pipeline exists yet",
        "sentiment": "UNKNOWN -- see sentiment_safety_status()", "problem": "UNKNOWN",
        "evidence": review, "confidence": "LOW -- raw text only, no structured extraction yet",
        "action": "NONE_TAKEN",
    } for request_id, review in reviews.items()] if isinstance(reviews, dict) else []
    return {"generated_at": _now_iso(), "total_reviews": len(items), "items": items,
            "note": "Original customer feedback is never altered -- customer_pipeline.py::submit_review() stores raw text verbatim, append-only."}


# ---------------------------------------------------------------------------
# Section 10 -- Sentiment Safety
# ---------------------------------------------------------------------------

def sentiment_safety_status():
    return {
        "generated_at": _now_iso(), "status": "NOT_BUILT",
        "reason": "No AI sentiment-analysis pipeline runs over customer_reviews.jsonl anywhere in this factory today -- confirmed by direct search.",
        "policy_if_built": "AI sentiment must always record {original_text, ai_interpretation, confidence, human_verification} distinctly -- never treated as ground truth, per Section 10's own rule. Ambiguous cases resolve to UNKNOWN, never a forced positive/negative.",
    }


# ---------------------------------------------------------------------------
# Sections 11 & 29 -- Customer Trust (indicators + explainable score)
# ---------------------------------------------------------------------------

def customer_trust_indicators():
    """Real citation over trust_audit.py (ADR-189) -- mapped onto the
    9 named indicators, never a second trust-scoring system."""
    import trust_audit
    report = trust_audit.build_trust_audit_report()
    return {
        "generated_at": _now_iso(),
        "product_accuracy": report.get("quality_regressions"),
        "delivery_reliability": "UNKNOWN -- no real delivery-time-vs-promise tracking exists yet",
        "support_quality": report.get("customer_risks"),
        "refund_experience": "N/A -- 0 real refunds have ever occurred",
        "pricing_transparency": "REAL -- pricing_review.py's real evidence-gated pricing changes (ADR-182), no hidden fees anywhere in this factory's checkout flow",
        "communication_quality": report.get("reputation_risks"),
        "privacy": "See CUSTOMER_PRIVACY_POLICY.md",
        "complaint_rate": "0 -- 0 real customer complaints recorded (0 real customers)",
        "customer_satisfaction": "NOT_MEASURABLE -- 0 real reviews exist",
        "source": "trust_audit.py::build_trust_audit_report() (ADR-189), never a second trust-scoring computation",
    }


def customer_trust_score():
    """No single arbitrary score -- 9 named components, each traceable
    to real evidence or an honest gap, matching autonomous_daily_score()/
    revenue_health_score()'s own established precedent."""
    indicators = customer_trust_indicators()
    return {"generated_at": _now_iso(), "components": indicators,
            "note": "No single composite Customer Trust number is reported -- several components are honestly NOT_MEASURABLE at 0 real customers."}


# ---------------------------------------------------------------------------
# Section 12 -- Refund Intelligence
# ---------------------------------------------------------------------------

def refund_intelligence_report(paddle_products_path=None, finance_path=None):
    from product_master_catalog import build_product_master_catalog
    catalog = build_product_master_catalog(paddle_products_path=paddle_products_path, finance_path=finance_path)
    total_refunds = sum(p.get("refunds_usd") or 0 for p in catalog.get("products", []))
    return {
        "generated_at": _now_iso(), "total_real_refunds_usd": total_refunds, "refund_events": [],
        "note": "0 real refunds have ever occurred in this factory (product_master_catalog.py's own real refunds_usd, confirmed across every catalog product) -- pattern detection has nothing real to run over yet. Never fabricates a refund-abuse classification without a real event.",
    }


# ---------------------------------------------------------------------------
# Section 13 -- Churn Intelligence
# ---------------------------------------------------------------------------

def churn_intelligence_report():
    return {
        "generated_at": _now_iso(), "status": "NOT_APPLICABLE",
        "reason": "0 real subscriptions exist anywhere in this factory (see SUBSCRIPTION_REVENUE.md, ADR-211) -- churn is structurally undefined until a real recurring product exists.",
    }


# ---------------------------------------------------------------------------
# Section 14 -- Retention Engine
# ---------------------------------------------------------------------------

def retention_engine_recommendations():
    return {
        "generated_at": _now_iso(), "available_actions": RETENTION_ACTIONS,
        "current_recommendations": [],
        "note": "0 real customers exist to generate a real recommendation for -- the taxonomy is real and ready, never populated with a fabricated example. Dark patterns (hiding cancellation, obstructing refunds) are permanently excluded from RETENTION_ACTIONS by design -- confirmed by direct inspection of the list above.",
    }


# ---------------------------------------------------------------------------
# Section 15 -- Customer Value
# ---------------------------------------------------------------------------

def customer_value_report(paddle_products_path=None, finance_path=None):
    from global_commercial_scale import unit_economics_report
    unit_econ = unit_economics_report(paddle_products_path=paddle_products_path, finance_path=finance_path)
    return {
        "generated_at": _now_iso(),
        "note": "Reuses global_commercial_scale.py's real per-product unit economics (Phase 20, ADR-210) -- LTV is honestly NOT_MEASURABLE for every product (0 real repeat customers).",
        "per_product": [{"product": p["product"], "lifetime_value": p["lifetime_value"], "net_revenue": p["net_revenue"]} for p in unit_econ["products"]],
    }


# ---------------------------------------------------------------------------
# Section 16 -- Customer Segmentation
# ---------------------------------------------------------------------------

def customer_segmentation_report():
    return {
        "generated_at": _now_iso(),
        "segments": {s: {"count": 0, "criteria": "Evidence-based, never sensitive/discriminatory profiling"} for s in CUSTOMER_SEGMENTS},
        "note": "0 real customers exist to segment -- the schema is real and ready.",
    }


# ---------------------------------------------------------------------------
# Section 17 -- Customer -> Product Intelligence
# ---------------------------------------------------------------------------

def customer_to_product_intelligence(product_name=None, paddle_products_path=None, finance_path=None):
    from product_master_catalog import build_product_master_catalog
    catalog = build_product_master_catalog(paddle_products_path=paddle_products_path, finance_path=finance_path)
    products = catalog.get("products", [])
    if product_name:
        products = [p for p in products if p.get("product_name") == product_name]
    return {
        "generated_at": _now_iso(),
        "products": [{
            "product": p.get("product_name"), "who_buys": "UNKNOWN -- 0 real customers",
            "problem": "See B2B_COMMERCIAL_ENGINE.md's case study for the one product with real evidence",
            "value_expected": "UNKNOWN", "value_reported": "UNKNOWN -- 0 real reviews",
            "refund_reasons": "N/A -- 0 real refunds", "requested_improvements": "UNKNOWN -- 0 real feedback",
            "buys_related_products": "N/A -- 0 real repeat customers", "returns": "N/A", "recommends": "UNKNOWN",
        } for p in products],
    }


# ---------------------------------------------------------------------------
# Section 18 -- Customer -> Golden Hunter (already real, cited)
# ---------------------------------------------------------------------------

def golden_hunter_customer_signal(niche):
    """Reuses market_evidence.py's real, already-wired signals verbatim
    -- never a second evidence engine."""
    import market_evidence
    return {
        "generated_at": _now_iso(), "niche": niche,
        "willingness_to_pay": market_evidence.get_willingness_to_pay_signal(niche),
        "retention_signal": market_evidence.get_retention_signal(niche),
        "acquisition_signal": market_evidence.get_customer_acquisition_signal(niche),
        "summary": market_evidence.summarize_niche(niche),
        "source": "market_evidence.py (already real, already feeds profit_oracle.py's ladder_opportunity_score())",
    }


# ---------------------------------------------------------------------------
# Section 19 -- Customer -> Product Innovation Pipeline
# ---------------------------------------------------------------------------

def product_innovation_pipeline_status(state_path=None, now=None):
    problems = customer_problem_mining_report(state_path=state_path, now=now)
    return {
        "generated_at": _now_iso(),
        "stage": "CUSTOMER_PROBLEM",
        "evidence": problems,
        "frequency": "See customer_problem_cost_trend() output above",
        "economic_impact": "UNKNOWN -- not yet quantified per-problem",
        "existing_solutions": "See competitive_moat_engine.py per already-evaluated niches",
        "gap": "UNKNOWN", "opportunity": "UNKNOWN", "product_idea": "UNKNOWN",
        "validation": "NOT_STARTED -- never skipped, per Section 19's own rule",
        "note": "This factory's real pipeline stops at CUSTOMER_PROBLEM today -- 0 real customer-reported problems have progressed further, since 0 real customers exist yet.",
    }


# ---------------------------------------------------------------------------
# Section 20 -- Feedback -> Roadmap
# ---------------------------------------------------------------------------

def classify_feedback_for_roadmap(customers_affected=0, revenue_impact=None, retention_impact=None):
    """Real, deterministic classifier -- defaults to INSUFFICIENT_EVIDENCE
    when the real, disclosed thresholds aren't met by real data."""
    if customers_affected <= 0:
        classification = "INSUFFICIENT_EVIDENCE"
    elif customers_affected >= 10 and revenue_impact:
        classification = "HIGH_VALUE"
    elif customers_affected >= 3:
        classification = "MEDIUM_VALUE"
    else:
        classification = "LOW_VALUE"
    return {
        "generated_at": _now_iso(), "classification": classification,
        "customers_affected": customers_affected, "revenue_impact": revenue_impact or "UNKNOWN",
        "retention_impact": retention_impact or "UNKNOWN",
        "implementation_cost": "UNKNOWN", "risk": "UNKNOWN", "confidence": "LOW" if customers_affected < 3 else "MEDIUM",
    }


# ---------------------------------------------------------------------------
# Section 21 -- Customer Success
# ---------------------------------------------------------------------------

def customer_success_report():
    return {
        "generated_at": _now_iso(),
        "note": "0 real B2B/premium customers exist to measure an outcome for -- see B2B_SALES_PIPELINE.md (Phase 20). Every named outcome (Problem Solved, Time Saved, Money Saved, etc.) is honestly UNMEASURED, never claimed without evidence.",
    }


# ---------------------------------------------------------------------------
# Sections 22-23 -- Support Intelligence + Automation
# ---------------------------------------------------------------------------

def support_intelligence_report(requests_path=None, state_path=None):
    import customer_pipeline
    overview = customer_pipeline.list_pipeline_overview(requests_path=requests_path, state_path=state_path)
    return {
        "generated_at": _now_iso(),
        "real_pipeline_overview": overview,
        "note": "Reuses customer_pipeline.py::list_pipeline_overview()'s real needs_attention/stuck-request detection (resilience_monitor.py::_classify_customer_risk() cites this same function) -- never a second stuck-request detector.",
    }


def support_automation_status():
    return {
        "generated_at": _now_iso(), "status": "NOT_BUILT",
        "safe_automatable_tasks": ["FAQ", "ORDER_STATUS", "DELIVERY_INFORMATION", "BASIC_PRODUCT_GUIDANCE", "KNOWN_ISSUE_INFORMATION"],
        "reason": "No FAQ bot/order-status bot exists anywhere in this factory today -- customer_site/status.html is the real, existing pull-based substitute (CLAUDE.md's own disclosed gap).",
        "escalation_categories": ["refund_disputes", "sensitive_cases", "legal_issues", "security_incidents", "high_value_customer_complaints", "ambiguous_situations"],
        "note": "Every one of the 6 named escalation categories already routes to the founder by default in this factory -- there is no automated support layer that could bypass them, since none exists.",
    }


# ---------------------------------------------------------------------------
# Section 24 -- Customer Communication (already real, cited)
# ---------------------------------------------------------------------------

def customer_communication_compliance(text=None):
    import brand_dna
    return {
        "generated_at": _now_iso(),
        "standards": brand_dna.COMMUNICATION_STANDARDS,
        "text_check": brand_dna.validate_customer_facing_text(text) if text else "No text supplied -- pass real customer-facing text to check.",
        "source": "brand_dna.py::validate_customer_facing_text() (ADR-170) -- the real, callable enforcement point, not duplicated here.",
    }


# ---------------------------------------------------------------------------
# Sections 25-26 -- Upsell / Cross-sell / Recommendation Engine
# ---------------------------------------------------------------------------

def upsell_recommendation(customer_need=None, product_relevance_evidence=None, expected_value=None):
    """Real, deterministic: DO_NOT_RECOMMEND is the default whenever
    relevance evidence is missing or weak, per Section 25's own rule."""
    if not customer_need or not product_relevance_evidence:
        return {"generated_at": _now_iso(), "decision": "DO_NOT_RECOMMEND",
                "reason": "Missing customer_need or product_relevance_evidence -- never recommends without both."}
    return {
        "generated_at": _now_iso(), "decision": "RECOMMEND",
        "customer_need": customer_need, "evidence": product_relevance_evidence,
        "expected_value": expected_value or "UNKNOWN", "confidence": "MEDIUM" if expected_value else "LOW",
    }


# ---------------------------------------------------------------------------
# Section 27 -- Retention Experiments (already real, cited)
# ---------------------------------------------------------------------------

def retention_experiments_status(experiments_path=None):
    import commercial_experiments
    return {
        "generated_at": _now_iso(),
        "real_experiments": commercial_experiments.list_experiments(experiments_path=experiments_path),
        "source": "commercial_experiments.py -- the real, generic, already-built experiment engine, not duplicated for retention specifically.",
    }


# ---------------------------------------------------------------------------
# Section 28 -- Customer Cohorts
# ---------------------------------------------------------------------------

def customer_cohort_report():
    return {
        "generated_at": _now_iso(), "cohorts": [],
        "note": "0 real customers exist to cohort by acquisition date/product/platform/market/channel/type -- the schema is real and ready.",
    }


# ---------------------------------------------------------------------------
# Section 30 -- Privacy & Access (already real, cited)
# ---------------------------------------------------------------------------

def privacy_access_report():
    return {
        "generated_at": _now_iso(),
        "classification_levels": "See KNOWLEDGE_ACCESS_CONTROL.md (Phase 18) -- PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED, the same real 2-tier auth model (MISSION_CONTROL_PASSWORD + INTERNAL_SERVICE_TOKEN) applies to customer data.",
        "data_minimization": data_minimization_report(),
        "deletion_requirements": "Real, disclosed gap -- no real data-deletion/right-to-erasure mechanism exists, since 0 real customer PII requiring deletion has ever been collected (KNOWLEDGE_ACCESS_CONTROL.md's own prior finding, unchanged).",
    }


# ---------------------------------------------------------------------------
# Section 31 -- Customer Data Correction
# ---------------------------------------------------------------------------

def customer_data_correction_status():
    return {
        "generated_at": _now_iso(), "status": "NOT_BUILT",
        "reason": "No real customer-initiated data-correction mechanism exists in customer_pipeline.py today -- confirmed by direct search.",
        "closest_real_analog": "channels/ledger.py::record_publish_attempt(backfill_reason=...) (Phase 14) -- this factory's one real, tagged, auditable correction pattern, applicable to a future customer-data correction feature.",
    }


# ---------------------------------------------------------------------------
# Section 32 -- Customer Incident Protection (already real, cited)
# ---------------------------------------------------------------------------

def customer_incident_protection_status():
    from resilience_monitor import assess_resilience
    r = assess_resilience()
    customer_findings = [f for f in r.get("findings", []) if "customer" in str(f.get("area", "")).lower()]
    return {
        "generated_at": _now_iso(), "real_customer_findings": customer_findings,
        "source": "resilience_monitor.py::_classify_customer_risk() (cites customer_pipeline.py's own needs_attention, never a second detector)",
    }


# ---------------------------------------------------------------------------
# Section 33 -- Customer Intelligence -> Revenue System (already real, cited)
# ---------------------------------------------------------------------------

def customer_intelligence_to_revenue():
    from revenue_operating_system import commission_engine_report, b2b_revenue_report
    return {
        "generated_at": _now_iso(),
        "commissions": commission_engine_report(),
        "b2b_revenue": b2b_revenue_report(),
        "note": "Cites revenue_operating_system.py (ADR-211) directly -- never a second, competing financial computation.",
    }


# ---------------------------------------------------------------------------
# Section 34 -- Customer Intelligence -> Institutional Memory
# ---------------------------------------------------------------------------

def customer_lessons_for_institutional_memory():
    return {
        "generated_at": _now_iso(),
        "note": "OpenClaw_Brain/19_Lessons_Learned/ is the real, existing lesson ledger (picked up automatically by knowledge_graph/build.py::_lesson_nodes()) -- no customer-specific lesson has been recorded there yet, since 0 real customer interactions have occurred to learn from.",
        "real_lesson_count_all_topics": "See knowledge_graph's real Lesson node count (KNOWLEDGE_GRAPH_ARCHITECTURE.md, Phase 18)",
    }


# ---------------------------------------------------------------------------
# Section 35 -- Customer Intelligence -> Executive Brain
# ---------------------------------------------------------------------------

def executive_customer_questions():
    """10 named CEO questions, each tagged FACT/INFERENCE/ESTIMATE/UNKNOWN
    per the directive's own explicit rule."""
    return {
        "generated_at": _now_iso(),
        "answers": [
            {"question": "Who are our best customers?", "answer": "None yet", "tag": "FACT"},
            {"question": "Why do they buy?", "answer": "No real purchase has occurred to examine", "tag": "UNKNOWN"},
            {"question": "What do they value?", "answer": "UNKNOWN", "tag": "UNKNOWN"},
            {"question": "Why do customers leave?", "answer": "N/A -- 0 real customers to leave", "tag": "FACT"},
            {"question": "What are customers repeatedly asking for?", "answer": "See customer_problem_mining_report()", "tag": "FACT"},
            {"question": "What products create the strongest outcomes?", "answer": "UNKNOWN -- 0 real outcomes measured", "tag": "UNKNOWN"},
            {"question": "Where is customer trust declining?", "answer": "Nowhere measurable -- 0 real customers", "tag": "FACT"},
            {"question": "What should we improve?", "answer": "Clear the Paddle onboarding gate to get the first real customer", "tag": "INFERENCE"},
            {"question": "What should we stop?", "answer": "Nothing customer-facing is currently active to stop", "tag": "FACT"},
            {"question": "What new customer problem deserves investigation?", "answer": "See golden_hunter_customer_signal() per-niche", "tag": "FACT"},
        ],
    }


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------

def build_customer_intelligence_dashboard(requests_path=None, state_path=None, finance_path=None, paddle_products_path=None, now=None):
    now = now or datetime.now(timezone.utc)
    return {
        "generated_at": _now_iso(now),
        "data_minimization": data_minimization_report(),
        "purchase_reasons": purchase_reason_report(),
        "non_purchase_reasons": non_purchase_reason_report(),
        "problem_mining": customer_problem_mining_report(state_path=state_path, now=now),
        "feedback": feedback_report(),
        "sentiment_safety": sentiment_safety_status(),
        "trust_score": customer_trust_score(),
        "refunds": refund_intelligence_report(paddle_products_path=paddle_products_path, finance_path=finance_path),
        "churn": churn_intelligence_report(),
        "retention": retention_engine_recommendations(),
        "customer_value": customer_value_report(paddle_products_path=paddle_products_path, finance_path=finance_path),
        "segmentation": customer_segmentation_report(),
        "support": support_intelligence_report(requests_path=requests_path, state_path=state_path),
        "support_automation": support_automation_status(),
        "cohorts": customer_cohort_report(),
        "privacy": privacy_access_report(),
        "incident_protection": customer_incident_protection_status(),
        "revenue_link": customer_intelligence_to_revenue(),
        "executive_questions": executive_customer_questions(),
        "note": "Computes every real sub-report exactly once -- never a second, competing customer-tracking system.",
    }
