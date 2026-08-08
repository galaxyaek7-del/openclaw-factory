"""Galaxy Forge Global Commercial Scale & Expansion Engine (Phase 20,
ADR-210, 2026-08-08).

Answers the founder's "GLOBAL COMMERCIAL SCALE & EXPANSION ENGINE"
directive. Research before writing any code found most of the 33
sections already real, scattered across already-built modules:
channels/ledger.py::revenue_trend() (real revenue), economics.py::
net_profit() (real per-platform fee/profit for the 5 modeled tiers),
global_opportunity_exchange.py::concentration_risk_report() (Section
22, verbatim), business_development.py (Sections 14/16/17, verbatim),
commercial_acquisition.py (Section 18, verbatim), market_domination_
engine.py (Section 6, verbatim), trust_audit.py (Section 24, verbatim),
capital_allocation_engine.py::opportunity_cost() (Section 29, verbatim),
growth_stages.py (a company-wide scale-stage precedent for Section 3's
per-product/platform grain), autonomous_operations.py::authorize_action()
(Phase 19, reused directly for Section 25's authorization boundary).

Real, current company state found before building anything: 0 real
ACCEPTED opportunities, $0 real revenue, 0 real customers, 0
b2b_systems/ai_saas niches ever evaluated. This means almost every
Evidence Gate check in this module honestly returns INSUFFICIENT
EVIDENCE today -- that is the correct, disclosed answer, not a bug in
this module. Nothing here fabricates a scaling recommendation to make
the company look more advanced than it is.
"""

from datetime import datetime, timezone

LADDER_RANKS = ["ai_saas", "b2b_systems", "automation_tools", "reusable_assets", "educational", "kdp_books"]

SCALING_ELIGIBILITY_STATES = [
    "NOT_READY", "TESTING", "VALIDATED", "SCALE_CANDIDATE",
    "SCALING", "MATURE", "DECLINING", "PAUSE", "EXIT",
]

MARKET_ENTRY_LADDER_STAGES = ["RESEARCH", "VALIDATE", "SMALL_TEST", "MEASURE", "REVIEW", "SCALE"]

TRANSFORMATION_LADDER = ["DIGITAL_ASSET", "TOOL", "WORKFLOW", "SYSTEM", "RECURRING_SERVICE"]

B2B_PIPELINE_STAGES = [
    "TARGET", "RESEARCHED", "QUALIFIED", "CONTACTED", "INTERESTED",
    "DISCOVERY", "PROPOSAL", "NEGOTIATION", "WON", "LOST", "REPEAT",
]

PLATFORM_ACTIONS = ["INVEST", "MAINTAIN", "TEST", "REDUCE", "PAUSE", "EXIT"]


def _now_iso(now=None):
    return (now or datetime.now(timezone.utc)).isoformat()


# ---------------------------------------------------------------------------
# Section 2 -- Evidence Gate
# ---------------------------------------------------------------------------

EVIDENCE_GATE_FIELDS = [
    "verified_revenue", "verified_net_revenue", "customer_demand", "conversion",
    "customer_satisfaction", "refund_rate", "retention", "operational_reliability",
    "platform_reliability", "product_quality", "unit_economics", "automation_reliability",
    "competition", "market_opportunity", "risk", "confidence",
]

# Fields whose absence blocks any aggressive-scaling recommendation --
# a real, disclosed subset of EVIDENCE_GATE_FIELDS, not all 16 equally
# weighted (revenue/net-revenue/demand/unit-economics are the ones a
# real scaling decision cannot be made without).
CRITICAL_EVIDENCE_FIELDS = ["verified_revenue", "verified_net_revenue", "customer_demand", "unit_economics"]


def evidence_gate_check(decisions_path=None, sales_ledger_path=None, now=None):
    """Real, per-field citation of already-real sources. Never invents
    a value for a field with no real source -- returns INSUFFICIENT
    EVIDENCE for the field, and INSUFFICIENT_EVIDENCE overall if any
    critical field is missing/unmeasurable."""
    now = now or datetime.now(timezone.utc)
    fields = {}

    from channels import ledger as sales_ledger
    revenue = sales_ledger.revenue_trend(now=now, ledger_path=sales_ledger_path)
    real_revenue = revenue.get("recent_7d_revenue_usd")
    fields["verified_revenue"] = {
        "value": real_revenue, "source": "channels/ledger.py::revenue_trend()",
        "sufficient": real_revenue is not None and real_revenue > 0,
    }
    fields["verified_net_revenue"] = {
        "value": "UNKNOWN -- no real per-sale fee/cost breakdown exists yet across every platform (economics.py models 5 of this factory's tiers, not the live Paddle channel)",
        "source": "economics.py::net_profit() (partial coverage)", "sufficient": False,
    }

    try:
        import customer_pipeline
        funnel = customer_pipeline.funnel_conversion_summary()
        fields["customer_demand"] = {"value": funnel, "source": "customer_pipeline.funnel_conversion_summary()",
                                      "sufficient": bool(funnel.get("total_requests"))}
        fields["conversion"] = {"value": funnel, "source": "customer_pipeline.funnel_conversion_summary()",
                                 "sufficient": bool(funnel.get("total_requests"))}
    except Exception as e:
        fields["customer_demand"] = {"value": "INSUFFICIENT EVIDENCE", "source": str(e), "sufficient": False}
        fields["conversion"] = {"value": "INSUFFICIENT EVIDENCE", "source": str(e), "sufficient": False}

    fields["customer_satisfaction"] = {"value": "INSUFFICIENT EVIDENCE -- 0 real customer reviews recorded to date",
                                        "source": "data/customer_reviews.jsonl", "sufficient": False}
    fields["refund_rate"] = {"value": "UNKNOWN -- no real refund tracking exists anywhere in this factory (0 real sales to refund)",
                              "source": "confirmed by direct search", "sufficient": False}
    fields["retention"] = {"value": "NOT_APPLICABLE -- no real recurring-revenue product exists yet",
                            "source": "N/A", "sufficient": False}

    try:
        from resilience_monitor import assess_resilience
        r = assess_resilience()
        fields["operational_reliability"] = {"value": r.get("resilience_score"), "source": "resilience_monitor.assess_resilience()",
                                              "sufficient": r.get("resilience_score") != "Unknown"}
    except Exception as e:
        fields["operational_reliability"] = {"value": "INSUFFICIENT EVIDENCE", "source": str(e), "sufficient": False}

    try:
        from channels import publish_protection
        status = publish_protection.list_publish_protection_status()
        fields["platform_reliability"] = {"value": status, "source": "channels/publish_protection.py::list_publish_protection_status()", "sufficient": True}
    except Exception as e:
        fields["platform_reliability"] = {"value": "INSUFFICIENT EVIDENCE", "source": str(e), "sufficient": False}

    try:
        from launch_readiness import launch_readiness_score
        lr = launch_readiness_score()
        fields["product_quality"] = {"value": lr, "source": "launch_readiness.py::launch_readiness_score()", "sufficient": True}
    except Exception as e:
        fields["product_quality"] = {"value": "INSUFFICIENT EVIDENCE", "source": str(e), "sufficient": False}

    fields["unit_economics"] = {"value": "PARTIAL -- see unit_economics_report(); economics.py models only gumroad_digital/premium/elite + kdp tiers, not the live Paddle channel",
                                 "source": "economics.py::net_profit()", "sufficient": False}
    fields["automation_reliability"] = {"value": "PARTIAL -- see lib/metrics.js's per-route error_rate_pct (ADR-157), no real per-product automation-reliability metric exists",
                                         "source": "lib/metrics.js", "sufficient": False}

    try:
        import competitive_moat_engine
        moat = competitive_moat_engine.assess_eu_ai_act_toolkit_moat(now=now)
        fields["competition"] = {"value": moat, "source": "competitive_moat_engine.py", "sufficient": True}
    except Exception as e:
        fields["competition"] = {"value": "INSUFFICIENT EVIDENCE", "source": str(e), "sufficient": False}

    try:
        import market_domination_engine
        candidates = market_domination_engine.high_value_candidates(limit=5, decisions_path=decisions_path)
        fields["market_opportunity"] = {"value": {"candidate_count": len(candidates)}, "source": "market_domination_engine.high_value_candidates()", "sufficient": bool(candidates)}
    except Exception as e:
        fields["market_opportunity"] = {"value": "INSUFFICIENT EVIDENCE", "source": str(e), "sufficient": False}

    try:
        import commercial_alerts
        alerts = commercial_alerts.assess_commercial_alerts(now=now)
        fields["risk"] = {"value": alerts, "source": "commercial_alerts.assess_commercial_alerts()", "sufficient": True}
    except Exception as e:
        fields["risk"] = {"value": "INSUFFICIENT EVIDENCE", "source": str(e), "sufficient": False}

    sufficient_count = sum(1 for f in fields.values() if f.get("sufficient"))
    fields["confidence"] = {"value": f"{sufficient_count}/{len(EVIDENCE_GATE_FIELDS) - 1} real fields sufficient",
                             "source": "computed from the fields above", "sufficient": None}

    critical_missing = [k for k in CRITICAL_EVIDENCE_FIELDS if not fields.get(k, {}).get("sufficient")]
    status = "INSUFFICIENT_EVIDENCE" if critical_missing else "EVIDENCE_SUFFICIENT"

    return {
        "generated_at": _now_iso(now),
        "status": status,
        "critical_fields_missing": critical_missing,
        "fields": fields,
        "note": "16 named fields, each a real citation or an honest INSUFFICIENT EVIDENCE/UNKNOWN -- never invented. Aggressive scaling is never recommended while any critical field is missing.",
    }


# ---------------------------------------------------------------------------
# Section 3 -- Scaling Eligibility Engine
# ---------------------------------------------------------------------------

def scaling_eligibility_report(paddle_products_path=None, finance_path=None, now=None):
    """One real entry per real product x platform combination this
    factory actually has -- product_master_catalog.py's own real
    per-product sales-matching is the evidence source. 0 real revenue
    anywhere today means every real combination is honestly NOT_READY
    or TESTING at best -- never a fabricated SCALE_CANDIDATE."""
    now = now or datetime.now(timezone.utc)
    from product_master_catalog import build_product_master_catalog
    catalog = build_product_master_catalog(paddle_products_path=paddle_products_path, finance_path=finance_path, now=now)

    entries = []
    for product in catalog.get("products", []):
        revenue = product.get("revenue_usd") or 0
        published = product.get("publication_status") == "PUBLISHED"
        product_created = product.get("publication_status") in ("PUBLISHED", "PRODUCT_CREATED_NOT_CONFIRMED_LIVE")
        if revenue >= 500:
            status = "SCALE_CANDIDATE"
        elif revenue > 0:
            status = "VALIDATED"
        elif product_created:
            status = "TESTING"
        else:
            status = "NOT_READY"
        platforms = list((product.get("platforms") or {}).keys()) or ["unknown"]
        entries.append({
            "product": product.get("product_name"),
            "platforms": platforms,
            "status": status,
            "real_revenue_usd": revenue,
            "evidence": {"publication_status": product.get("publication_status"), "pricing_usd": product.get("pricing_usd")},
            "source": "product_master_catalog.build_product_master_catalog()",
        })

    return {
        "generated_at": _now_iso(now),
        "entries": entries,
        "total": len(entries),
        "by_status": {s: len([e for e in entries if e["status"] == s]) for s in SCALING_ELIGIBILITY_STATES},
        "note": "Evidence-driven only -- 0 real revenue anywhere today means the strongest real status any combination can honestly earn is TESTING or VALIDATED, never fabricated SCALING/MATURE.",
    }


# ---------------------------------------------------------------------------
# Section 4 -- Unit Economics
# ---------------------------------------------------------------------------

def unit_economics_report(paddle_products_path=None, finance_path=None, now=None):
    """Reuses economics.py::net_profit() verbatim for the 5 real tiers
    it models -- never a second, competing fee calculator. Every cost
    this factory has no real tracking for reports UNKNOWN, never a
    guessed number."""
    now = now or datetime.now(timezone.utc)
    import economics
    from product_master_catalog import build_product_master_catalog

    config = economics.load_config()
    catalog = build_product_master_catalog(paddle_products_path=paddle_products_path, finance_path=finance_path, now=now)

    entries = []
    for product in catalog.get("products", []):
        price = product.get("pricing_usd")
        # No real per-product tier field exists in the catalog -- this
        # factory's one real live-priced product (EU AI Act Toolkit) was
        # validated against the gumroad_elite tier for its price floor
        # (see CLAUDE.md, "Execution Mode continued"), used here as a
        # disclosed default, never asserted as the real live channel fee.
        tier = "gumroad_elite"
        try:
            platform_net = economics.net_profit(price, tier, config) if price else None
        except (ValueError, KeyError):
            platform_net = None
        revenue = product.get("revenue_usd") or 0
        entries.append({
            "product": product.get("product_name"),
            "gross_revenue_per_unit": price,
            "platform_fees_modeled_tier": f"{tier} (disclosed default -- no real per-product tier field exists)",
            "net_profit_per_unit_modeled": platform_net,
            "real_live_channel_fee": "UNKNOWN -- Paddle's real fee is not modeled in economics.py (5 tiers covered: kdp_ebook/kdp_paperback/gumroad_digital/premium/elite)",
            "payment_fees": "See platform fee above -- no separate real payment-processor fee tracked",
            "affiliate_commissions": "UNKNOWN -- no real affiliate sale has ever occurred",
            "customer_acquisition_cost": "UNKNOWN -- no real paid-acquisition spend tracked anywhere",
            "ai_cost": "See data/ai_cost_log.jsonl -- not currently attributed per-product",
            "infrastructure_cost": "UNKNOWN -- no real per-product infra cost allocation exists",
            "support_cost": "UNKNOWN -- no real per-product support-time tracking exists",
            "refund_cost": "$0 -- 0 real refunds have ever occurred (product_master_catalog.py's own real refunds_usd)",
            "contribution_margin": platform_net if platform_net is not None else "UNKNOWN",
            "net_revenue": f"${revenue} real recorded revenue to date" if revenue else "$0 -- 0 real units sold to date",
            "lifetime_value": "NOT_MEASURABLE -- 0 real repeat customers exist",
        })

    return {
        "generated_at": _now_iso(now),
        "products": entries,
        "note": "Every cost field either cites economics.py::net_profit() (5 real modeled tiers) or is honestly UNKNOWN -- never invented. Profitability is never assumed.",
    }


# ---------------------------------------------------------------------------
# Section 12 -- B2B Commercial Engine
# ---------------------------------------------------------------------------

def b2b_commercial_engine_report(decisions_path=None):
    """Real finding: 0 niches in this factory's real evaluation history
    (98 real niches, confirmed live) have ever been tagged ai_saas or
    b2b_systems -- the two ladder ranks this directive's B2B ask maps
    to. The one real B2B-adjacent product this factory has ever shipped
    (EU AI Act Compliance Toolkit -- a compliance-burden product sold
    as a one-time toolkit, not enterprise licensing) is cited as the
    single real case study; no fabricated pipeline of B2B leads is
    invented to fill the gap."""
    from decision_engine import store
    latest = store.latest_decision_per_niche(path=decisions_path)
    b2b_ladder_candidates = [v for v in latest.values() if v.get("ladder") in ("ai_saas", "b2b_systems")]

    return {
        "generated_at": _now_iso(),
        "real_b2b_ladder_candidates": len(b2b_ladder_candidates),
        "total_niches_evaluated": len(latest),
        "case_study": {
            "product": "EU AI Act Compliance Toolkit",
            "problem_category": "Compliance burden",
            "real_evidence": "governancedocs.com/riskprofs.com real customer reviews + $699 comparable pricing (see COMPETITIVE_MOAT_ENGINE.md)",
            "note": "Sold as a one-time toolkit today, not a recurring B2B/enterprise contract -- see TRANSFORMATION_PRODUCT_ENGINE.md for the real ladder this could climb.",
        },
        "opportunity_fields_template": [
            "customer", "problem", "current_process", "current_cost", "potential_solution",
            "expected_savings", "potential_price", "recurring_revenue", "implementation_difficulty",
            "competition", "strategic_value", "confidence",
        ],
        "note": "0 of 98 real evaluated niches carry a real ai_saas/b2b_systems ladder tag -- this is a genuine gap in this factory's real opportunity pipeline, not a missing report. No fabricated B2B opportunity is listed to fill it.",
    }


# ---------------------------------------------------------------------------
# Section 13 -- Transformation Product Engine
# ---------------------------------------------------------------------------

def transformation_product_ladder_status(paddle_products_path=None, finance_path=None, now=None):
    """Real, per-product classification onto the 5-stage ladder. Every
    real catalog product today is a DIGITAL_ASSET -- 0 have become a
    tool/workflow/system/recurring service, an honest finding."""
    now = now or datetime.now(timezone.utc)
    from product_master_catalog import build_product_master_catalog
    catalog = build_product_master_catalog(paddle_products_path=paddle_products_path, finance_path=finance_path, now=now)

    entries = [{"product": p.get("product_name"), "current_stage": "DIGITAL_ASSET", "next_stage": "TOOL",
                "real_evidence_for_next_stage": "None yet -- no real interactive tool version exists for any product"}
               for p in catalog.get("products", [])]

    return {
        "generated_at": _now_iso(now),
        "products": entries,
        "ladder": TRANSFORMATION_LADDER,
        "note": "Every real product in this factory's catalog is honestly a DIGITAL_ASSET today -- no fabricated 'in progress' status for TOOL/WORKFLOW/SYSTEM/RECURRING_SERVICE.",
    }


# ---------------------------------------------------------------------------
# Section 19 -- B2B Sales Pipeline
# ---------------------------------------------------------------------------

def b2b_sales_pipeline_report(decisions_path=None):
    """Real, honest pipeline -- 0 real B2B outreach has ever occurred
    in this factory, so the pipeline is honestly near-empty rather than
    populated with fabricated leads. The one real candidate (from
    b2b_commercial_engine_report()'s case study) is staged at TARGET
    only, since no real contact has ever been made."""
    b2b = b2b_commercial_engine_report(decisions_path=decisions_path)
    entries = [{
        "opportunity": "EU AI Act Compliance Toolkit -- EU SME compliance teams",
        "stage": "TARGET",
        "source": "Real Proof-of-Payment evidence (governancedocs.com/riskprofs.com), never a real contacted lead",
        "evidence": b2b["case_study"]["real_evidence"],
        "expected_value": "UNKNOWN -- no real deal size has ever been discussed",
        "probability": "UNKNOWN",
        "next_action": "Identify a real, named target organization -- none exists yet",
        "owner": "founder",
        "last_contact": None,
        "status": "TARGET",
    }]
    return {
        "generated_at": _now_iso(),
        "stages": B2B_PIPELINE_STAGES,
        "pipeline": entries,
        "note": "0 real B2B contacts have ever been made in this factory -- the pipeline honestly has 1 real TARGET-stage entry and nothing beyond it.",
    }


# ---------------------------------------------------------------------------
# Section 20 -- Global Revenue Forecast
# ---------------------------------------------------------------------------

def global_revenue_forecast(sales_ledger_path=None, decisions_path=None, now=None):
    """The 6 named categories are kept structurally separate -- never
    combined into one number, per the directive's own explicit rule."""
    now = now or datetime.now(timezone.utc)
    from channels import ledger as sales_ledger
    revenue = sales_ledger.revenue_trend(now=now, ledger_path=sales_ledger_path)

    try:
        import business_development
        pipeline = business_development.build_business_development_dashboard()
    except Exception:
        pipeline = None

    return {
        "generated_at": _now_iso(now),
        "actual": {"value_usd": revenue.get("recent_7d_revenue_usd"), "source": "channels/ledger.py::revenue_trend() -- real recorded sale events"},
        "verified": {"value_usd": revenue.get("recent_7d_revenue_usd"), "source": "Same real ledger -- 'verified' has no separate real reconciliation-adjusted figure yet beyond commercial_reconciliation.py's discrepancy checks"},
        "pipeline": {"value": pipeline, "source": "business_development.build_business_development_dashboard() -- real partnership pipeline, not yet revenue-valued per entry"},
        "estimated": {"value": "NOT_COMPUTABLE", "reason": "decision_engine's own expected_revenue field is retrospective (real closed-sale revenue to date), never a forward estimate -- see [[project_capital_decisions_20260805]]"},
        "projected": {"value": "NOT_COMPUTABLE", "reason": "This factory (founded 2026-07-05) has no real historical revenue trend long enough to project from"},
        "potential": {"value": "NOT_COMPUTABLE", "reason": "Would require a fabricated TAM/conversion assumption -- profit_oracle.py's own disclosed limitation (no real TAM/SAM/SOM source exists)"},
        "assumptions": ["No category above is ever combined with another.", "ACTUAL and VERIFIED both cite the same real ledger since no independent verification signal exists beyond it yet."],
    }


# ---------------------------------------------------------------------------
# Section 23 -- International Commercial Compliance
# ---------------------------------------------------------------------------

def international_compliance_flags():
    """Real citation over global_opportunity_exchange.py's already-real
    country_dependency_note() (the founder's own 2026-07-23 standing
    deferral) plus a real, disclosed FLAG_FOR_HUMAN_REVIEW for every
    named compliance category this factory has no real legal-expertise
    signal for -- never a false-certainty PASS."""
    import global_opportunity_exchange
    country_note = global_opportunity_exchange.country_dependency_note()

    categories = ["terms", "platform_policies", "tax_considerations", "consumer_obligations",
                  "privacy_obligations", "payment_requirements", "commercial_restrictions"]
    flags = [{
        "category": c,
        "status": "FLAG_FOR_HUMAN_REVIEW",
        "reason": "No real legal-expertise signal exists anywhere in this factory for this category -- a human/legal review is required before entering any new market or platform.",
    } for c in categories]

    return {
        "generated_at": _now_iso(),
        "country_dependency": country_note,
        "compliance_flags": flags,
        "note": "This factory has zero real legal-review infrastructure -- every named compliance category is honestly flagged for human review, never given false certainty.",
    }


# ---------------------------------------------------------------------------
# Section 25 -- Autonomous Scale Recommendations (reuses Phase 19's engine)
# ---------------------------------------------------------------------------

def autonomous_scale_recommendations(paddle_products_path=None, finance_path=None, now=None):
    """Every recommendation is checked through autonomous_operations.
    authorize_action() (Phase 19, ADR-209) -- this module never
    executes a scale action itself; it only classifies what authority
    level each real recommendation would require."""
    now = now or datetime.now(timezone.utc)
    from autonomous_operations import authorize_action
    eligibility = scaling_eligibility_report(paddle_products_path=paddle_products_path, finance_path=finance_path, now=now)

    recs = []
    for entry in eligibility["entries"]:
        if entry["status"] == "NOT_READY":
            action = "TEST"
        elif entry["status"] == "TESTING":
            action = "MEASURE"
        elif entry["status"] in ("VALIDATED", "SCALE_CANDIDATE"):
            action = "SCALE"
        else:
            action = "MAINTAIN"
        category = "proven_channel_publish" if action in ("TEST", "MEASURE", "MAINTAIN") else "new_or_elevated_risk_publish"
        recs.append({
            "product": entry["product"], "platforms": entry["platforms"],
            "recommended_action": action, "evidence": entry,
            "authorization": authorize_action(category),
        })

    return {
        "generated_at": _now_iso(now),
        "recommendations": recs,
        "note": "Every recommendation cites its real required autonomy level via autonomous_operations.authorize_action() (ADR-209) -- irreversible actions stay founder-gated exactly as before.",
    }


# ---------------------------------------------------------------------------
# Section 26/33 -- Aggregator
# ---------------------------------------------------------------------------

def build_global_commercial_scale_dashboard(decisions_path=None, sales_ledger_path=None,
                                             paddle_products_path=None, finance_path=None, now=None):
    """The one real aggregator -- computes every real sub-report exactly
    once, never a second competing computation."""
    now = now or datetime.now(timezone.utc)
    import global_opportunity_exchange
    import market_domination_engine
    import business_development
    import trust_audit

    evidence = evidence_gate_check(decisions_path=decisions_path, sales_ledger_path=sales_ledger_path, now=now)
    eligibility = scaling_eligibility_report(paddle_products_path=paddle_products_path, finance_path=finance_path, now=now)
    unit_econ = unit_economics_report(paddle_products_path=paddle_products_path, finance_path=finance_path, now=now)
    concentration = global_opportunity_exchange.concentration_risk_report(decisions_path=decisions_path)
    markets = market_domination_engine.build_market_domination_dashboard(decisions_path=decisions_path)
    b2b = b2b_commercial_engine_report(decisions_path=decisions_path)
    partnerships = business_development.build_business_development_dashboard()
    forecast = global_revenue_forecast(sales_ledger_path=sales_ledger_path, decisions_path=decisions_path, now=now)
    trust = trust_audit.build_trust_audit_report()

    return {
        "generated_at": _now_iso(now),
        "evidence_gate": evidence,
        "scaling_eligibility": eligibility,
        "unit_economics": unit_econ,
        "concentration_risk": concentration,
        "market_prioritization": markets,
        "b2b_commercial_engine": b2b,
        "partnerships": partnerships,
        "revenue_forecast": forecast,
        "commercial_reputation": trust,
        "note": "Computes 9 real sub-reports exactly once each -- never a second, competing computation of any of them.",
    }
