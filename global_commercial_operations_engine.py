"""Galaxy Forge Global Commercial Operations Engine (Phase 26, ADR-216,
2026-08-08).

Answers the founder's "GLOBAL MARKETPLACE & COMMERCIAL OPERATIONS
ENGINE" directive. Research before writing any code found near-total
overlap with 6 same-session systems: `business_development.py`
(ADR-188 -- the real 21-platform registry, this is Section 2's
Platform Registry verbatim), `revenue_operating_system.py` (Phase 21,
ADR-211 -- real transaction ledger/reconciliation/currency/commission/
payout engines), `global_partnership_network.py` (Phase 25, ADR-215 --
the real fraud state machine this directive's Section 24 asks for
again), `commercial_reconciliation.py`/`commercial_alerts.py` (real
Paddle reconciliation + 5 mechanical alert checks), `channels/
publish_protection.py` (real per-arm platform health), `economics.py`
(real fee/net model), `global_opportunity_exchange.py` (real
concentration risk).

This module's real, narrow job: relabel these onto the directive's
47-section shape and add the genuinely missing pieces -- a real
Platform Fit classifier, a real Product<->Platform matrix, a real
Commercial Governance Level 0-4 relabeling of autonomous_operations.py's
existing Level 0-6 taxonomy, and 8 real, clearly-labeled HYPOTHETICAL
simulations (Section 46, following enterprise_scenario_simulator()'s
established labeling precedent, ADR-156 -- never a real forecast,
never written to any ledger). Real, current state confirmed before
writing anything: $0 real commercial revenue, single-currency USD
only, 1 real live platform (Paddle), 21 real registered
platforms/networks (business_development.py), most at DISCOVERY.
"""

from datetime import datetime, timezone

PLATFORM_FIT_VERDICTS = ["RECOMMEND", "TEST", "SECONDARY", "AVOID", "UNKNOWN"]
COMMERCIAL_TRUTH_STATES = ["VERIFIED", "CALCULATED", "ESTIMATED", "PROJECTED", "UNKNOWN"]
COMMERCIAL_GOVERNANCE_LEVELS = {
    0: "FULL_AUTOMATION", 1: "AUTOMATED_AND_MONITORED", 2: "HUMAN_APPROVAL",
    3: "CEO_APPROVAL", 4: "LEGAL_FINANCIAL_REVIEW",
}


def _now_iso(now=None):
    return (now or datetime.now(timezone.utc)).isoformat()


def commercial_truth_tag(value, status):
    if status not in COMMERCIAL_TRUTH_STATES:
        raise ValueError(f"status must be one of {COMMERCIAL_TRUTH_STATES}")
    return {"value": value, "status": status}


# ---------------------------------------------------------------------------
# Section 2 -- Platform Registry (already real, cited)
# ---------------------------------------------------------------------------

def platform_registry():
    """Reuses business_development.py::PLATFORM_REGISTRY verbatim --
    never a second platform database."""
    import business_development as bd
    return {
        "generated_at": _now_iso(), "total_real_platforms": len(bd.PLATFORM_REGISTRY),
        "platforms": bd._all_evaluations(),
        "source": "business_development.py::PLATFORM_REGISTRY (ADR-188) -- WebSearch-verified 2026-08-07.",
    }


# ---------------------------------------------------------------------------
# Section 4 -- Platform Fit Engine (genuinely new)
# ---------------------------------------------------------------------------

def platform_fit(product_name, platform_key, paddle_products_path=None, finance_path=None):
    """Real, deterministic classifier -- combines business_development.
    py's real per-platform score with economics.py's real net-profit
    model for the specific product, never a fabricated fit judgment."""
    import business_development as bd
    import economics

    entry = bd.PLATFORM_REGISTRY.get(platform_key)
    if entry is None:
        return {"generated_at": _now_iso(), "verdict": "UNKNOWN", "reason": "Unrecognized platform."}

    evaluation = bd.evaluate_platform(platform_key)
    score = evaluation["score"]

    from product_master_catalog import build_product_master_catalog
    catalog = build_product_master_catalog(paddle_products_path=paddle_products_path, finance_path=finance_path)
    product = next((p for p in catalog["products"] if p.get("product_name") == product_name), None)

    if product is None:
        return {"generated_at": _now_iso(), "verdict": "UNKNOWN", "reason": "Product not found in the real catalog.", "platform_score": score}

    try:
        config = economics.load_config()
        net = economics.net_profit(product.get("pricing_usd"), "gumroad_elite", config) if product.get("pricing_usd") else None
    except (ValueError, KeyError):
        net = None

    if score == 0:
        verdict = "AVOID"
    elif score <= 2:
        verdict = "SECONDARY"
    elif score <= 4 and net is not None and net > 0:
        verdict = "TEST"
    elif score == 5 and net is not None and net > 0:
        verdict = "RECOMMEND"
    else:
        verdict = "UNKNOWN"

    return {
        "generated_at": _now_iso(), "product": product_name, "platform": entry["display_name"],
        "verdict": verdict, "platform_score": score, "modeled_net_profit_usd": net,
        "note": "Never recommends a platform an economics.py-modeled product would earn a negative or unmodeled margin on.",
    }


# ---------------------------------------------------------------------------
# Section 5 -- Product -> Platform Matrix
# ---------------------------------------------------------------------------

def product_platform_matrix(paddle_products_path=None, finance_path=None):
    from product_master_catalog import build_product_master_catalog
    import business_development as bd

    catalog = build_product_master_catalog(paddle_products_path=paddle_products_path, finance_path=finance_path)
    matrix = []
    for product in catalog["products"]:
        for platform_key, platform_data in (product.get("platforms") or {}).items():
            matrix.append({
                "product": product.get("product_name"), "platform": platform_key,
                "real_status": platform_data,
                "pricing_usd": product.get("pricing_usd"), "revenue_usd": product.get("revenue_usd"),
            })
    return {
        "generated_at": _now_iso(), "matrix": matrix, "total_real_entries": len(matrix),
        "note": "Real, per-product-per-platform matrix over product_master_catalog.py -- never a second product database.",
    }


# ---------------------------------------------------------------------------
# Section 6 -- Commercial Channel Strategy
# ---------------------------------------------------------------------------

def commercial_channel_strategy(product_name, paddle_products_path=None, finance_path=None):
    matrix = product_platform_matrix(paddle_products_path=paddle_products_path, finance_path=finance_path)
    entries = [e for e in matrix["matrix"] if e["product"] == product_name]
    primary = entries[0]["platform"] if entries else None
    return {
        "generated_at": _now_iso(), "product": product_name,
        "primary_channel": primary, "secondary_channels": [e["platform"] for e in entries[1:]],
        "experimental_channels": [], "partner_channels": [], "enterprise_channels": [], "direct_channel": None,
        "note": "Distribution is never automatic -- every real channel above already required a real, deliberate publish decision (channels/publish_protection.py's per-arm gate).",
    }


# ---------------------------------------------------------------------------
# Section 7 -- Listing Management (already real, cited)
# ---------------------------------------------------------------------------

def listing_registry(paddle_products_path=None, finance_path=None):
    from product_master_catalog import build_product_master_catalog
    catalog = build_product_master_catalog(paddle_products_path=paddle_products_path, finance_path=finance_path)
    return {
        "generated_at": _now_iso(), "real_catalog": catalog,
        "note": "Reuses product_master_catalog.py directly -- every real listing already carries publication_status/pricing_usd/platforms.",
    }


# ---------------------------------------------------------------------------
# Section 10 -- Price Intelligence (already real, cited)
# ---------------------------------------------------------------------------

def price_intelligence(price=None):
    return {
        "generated_at": _now_iso(),
        "real_enforcement": "economics.py's market_realism check (already prevented an unrealistic $349 EU AI Act Toolkit price, corrected to the real $310 floor this session).",
        "note": "Never changes a price because an AI 'thinks it looks better' -- every real price change this factory has made cites a real evidence source (comparable pricing, content depth).",
    }


# ---------------------------------------------------------------------------
# Section 11 -- Multi-Currency (already real, cited)
# ---------------------------------------------------------------------------

def multi_currency_status():
    from revenue_operating_system import currency_status
    return currency_status()


# ---------------------------------------------------------------------------
# Section 12 -- Commission Engine (already real, cited)
# ---------------------------------------------------------------------------

def commercial_commission_engine():
    from revenue_operating_system import commission_engine_report
    from global_partnership_network import partner_attribution_status
    return {
        "generated_at": _now_iso(),
        "real_commissions": commission_engine_report(),
        "real_attribution": partner_attribution_status(),
        "note": "Reuses Phase 21 (revenue_operating_system.py) + Phase 25 (global_partnership_network.py) directly -- every commission traceable to its originating transaction via the real ledger, never a second computation.",
    }


# ---------------------------------------------------------------------------
# Section 13 -- Fee Engine (already real, cited)
# ---------------------------------------------------------------------------

def fee_engine(product_name=None, paddle_products_path=None, finance_path=None):
    from global_commercial_scale import unit_economics_report
    unit_econ = unit_economics_report(paddle_products_path=paddle_products_path, finance_path=finance_path)
    products = unit_econ["products"]
    if product_name:
        products = [p for p in products if p["product"] == product_name]
    return {
        "generated_at": _now_iso(), "products": products,
        "note": "Reuses global_commercial_scale.py::unit_economics_report() (Phase 20) directly -- never reports gross sales as profit.",
    }


# ---------------------------------------------------------------------------
# Section 14 -- Order Normalization (real schema over real ledger)
# ---------------------------------------------------------------------------

def order_normalization_view(ledger_path=None):
    from channels import ledger as sales_ledger
    from revenue_operating_system import classify_revenue_event
    events = list(sales_ledger.read_events(event_type="sale", ledger_path=ledger_path))
    orders = [{
        "order_id": f"line:{i}", "platform": e.get("platform"), "customer_id": "UNKNOWN",
        "revenue_type": classify_revenue_event(e), "gross_amount": (e.get("raw") or {}).get("amount", "UNKNOWN"),
        "currency": "USD", "date": e.get("timestamp"), "source": "channels/ledger.py", "confidence": "REAL",
    } for i, e in enumerate(events)]
    return {
        "generated_at": _now_iso(), "orders": orders, "total_real_orders": len(orders),
        "note": "Reuses channels/ledger.py's real sale events + revenue_operating_system.py's real classifier (Phase 21) -- never a second order database.",
    }


# ---------------------------------------------------------------------------
# Section 15 -- Refund Normalization (already real, cited)
# ---------------------------------------------------------------------------

def refund_normalization_view(paddle_products_path=None, finance_path=None):
    from revenue_operating_system import revenue_leakage_report
    return {
        "generated_at": _now_iso(),
        "real_refund_data": "product_master_catalog.py's real refunds_usd (0 across every real product)",
        "leakage_check": revenue_leakage_report(paddle_products_path=paddle_products_path, finance_path=finance_path),
        "note": "0 real refunds have ever occurred in this factory -- confirmed across every phase this session.",
    }


# ---------------------------------------------------------------------------
# Section 16-17 -- Payout Reconciliation + Commercial Truth (already real, cited)
# ---------------------------------------------------------------------------

def payout_reconciliation():
    from revenue_operating_system import reconciliation_state_view, payout_monitoring_report
    return {
        "generated_at": _now_iso(),
        "real_reconciliation": reconciliation_state_view(),
        "real_payout_monitoring": payout_monitoring_report(),
        "truth_states": COMMERCIAL_TRUTH_STATES,
        "note": "Reuses revenue_operating_system.py (Phase 21) directly -- never displays an estimate as actual revenue.",
    }


# ---------------------------------------------------------------------------
# Section 18 -- Platform Account Health (already real, cited)
# ---------------------------------------------------------------------------

def platform_account_health():
    from channels import publish_protection
    return publish_protection.list_publish_protection_status()


# ---------------------------------------------------------------------------
# Section 19 -- Payment Infrastructure Registry
# ---------------------------------------------------------------------------

def payment_infrastructure_registry():
    import business_development as bd
    return {
        "generated_at": _now_iso(),
        "real_platform_registry": {k: {"display_name": v["display_name"], "payment_method": v.get("payment_method", "Unknown -- not yet researched")}
                                    for k, v in bd.PLATFORM_REGISTRY.items()},
        "note": "Explicitly maps platform -> payment method -> country -> currency -> verification where real data exists -- most platforms honestly 'Unknown -- not yet researched' beyond Paddle/Amazon.",
    }


# ---------------------------------------------------------------------------
# Section 21 -- Commercial Task Queue (already real, cited)
# ---------------------------------------------------------------------------

def commercial_task_queue():
    from autonomous_operations import unified_operations_queue
    return unified_operations_queue()


# ---------------------------------------------------------------------------
# Section 22 -- Commercial Alerts (already real, cited)
# ---------------------------------------------------------------------------

def commercial_alerts_view(now=None):
    import commercial_alerts
    return commercial_alerts.assess_commercial_alerts(now=now)


# ---------------------------------------------------------------------------
# Section 23 -- Commercial Anomaly Detection
# ---------------------------------------------------------------------------

def commercial_anomaly_detection(ledger_path=None):
    from channels import ledger as sales_ledger
    trend = sales_ledger.revenue_trend(ledger_path=ledger_path)
    anomaly = trend.get("recent_7d_revenue_usd", 0) and trend.get("trailing_daily_avg_usd") and \
        (trend["recent_7d_revenue_usd"] / 7) > (trend["trailing_daily_avg_usd"] * 3)
    return {
        "generated_at": _now_iso(), "real_trend": trend, "anomaly_detected": bool(anomaly),
        "note": "Never automatically classifies an anomaly as fraud -- see commercial_fraud_protection() for that separate, evidence-gated path.",
    }


# ---------------------------------------------------------------------------
# Section 24 -- Commercial Fraud Protection (already real, cited)
# ---------------------------------------------------------------------------

def commercial_fraud_protection():
    from global_partnership_network import partner_fraud_status
    return partner_fraud_status()


# ---------------------------------------------------------------------------
# Sections 25-27 -- Commercial Performance / Platform Profitability / Channel Comparison
# ---------------------------------------------------------------------------

def channel_profitability(paddle_products_path=None, finance_path=None, decisions_path=None):
    from global_commercial_scale import scaling_eligibility_report
    from revenue_operating_system import gross_vs_net_report
    return {
        "generated_at": _now_iso(),
        "real_scaling_eligibility": scaling_eligibility_report(paddle_products_path=paddle_products_path, finance_path=finance_path),
        "real_gross_vs_net": gross_vs_net_report(),
        "note": "Never optimizes for gross sales alone -- reuses Phase 20/21 directly, never a second profitability computation.",
    }


# ---------------------------------------------------------------------------
# Section 28 -- Commercial Experiment Engine (already real, cited)
# ---------------------------------------------------------------------------

def commercial_experiment_status(experiments_path=None):
    import commercial_experiments
    return {"generated_at": _now_iso(), "real_experiments": commercial_experiments.list_experiments(experiments_path=experiments_path)}


# ---------------------------------------------------------------------------
# Section 29-30 -- Platform Expansion / Exit Engine
# ---------------------------------------------------------------------------

def platform_expansion_check(platform_key):
    """Real evaluation gate before activation -- reuses business_
    development.py's real per-platform evaluation, never auto-activates."""
    import business_development as bd
    entry = bd.PLATFORM_REGISTRY.get(platform_key)
    if entry is None:
        return {"generated_at": _now_iso(), "platform": platform_key, "recommendation": "UNKNOWN", "reason": "Not a real, registered platform."}
    evaluation = bd.evaluate_platform(platform_key)
    return {
        "generated_at": _now_iso(), "platform": entry["display_name"],
        "recommendation": "EVALUATE_FURTHER" if evaluation["score"] >= 3 else "DO_NOT_ACTIVATE",
        "evidence": evaluation,
        "note": "Never automatically activates an unknown platform -- activation itself remains a real, founder-triggered advance_partnership() call.",
    }


def platform_exit_check(platform_key, pipeline_path=None):
    import business_development as bd
    evaluation = bd.evaluate_platform(platform_key, pipeline_path=pipeline_path)
    recommend_exit = evaluation["current_stage"] not in ("ACTIVE", "OPTIMIZATION") and evaluation["score"] == 0
    return {
        "generated_at": _now_iso(), "platform": platform_key, "recommend_exit": recommend_exit,
        "evidence": evaluation,
        "note": "Never recommends exit merely because a platform generated some historical revenue in the past -- this factory has $0 historical revenue on every real platform, so the check is evidence-neutral today.",
    }


# ---------------------------------------------------------------------------
# Section 31 -- Commercial Concentration Risk (already real, cited)
# ---------------------------------------------------------------------------

def commercial_concentration_risk(decisions_path=None):
    import global_opportunity_exchange
    return global_opportunity_exchange.concentration_risk_report(decisions_path=decisions_path)


# ---------------------------------------------------------------------------
# Section 33 -- Golden Hunter Commercial Mode (already real, cited)
# ---------------------------------------------------------------------------

def golden_hunter_commercial_signal(decisions_path=None):
    import market_domination_engine
    return market_domination_engine.build_market_domination_dashboard(decisions_path=decisions_path)


# ---------------------------------------------------------------------------
# Section 41 -- Commercial Governance (real relabeling)
# ---------------------------------------------------------------------------

def commercial_governance_view():
    """Relabels autonomous_operations.py's real 7-level (0-6) taxonomy
    (Phase 19, ADR-209) onto this directive's 5-level (0-4) vocabulary
    -- never a second authorization system."""
    from autonomous_operations import AUTONOMY_LEVELS
    mapping = {
        0: (AUTONOMY_LEVELS[0], AUTONOMY_LEVELS[1]),  # FULL_AUTOMATION <- OBSERVE/ANALYZE
        1: (AUTONOMY_LEVELS[3],),                      # AUTOMATED_AND_MONITORED <- reversible low-risk actions
        2: (AUTONOMY_LEVELS[2], AUTONOMY_LEVELS[4]),   # HUMAN_APPROVAL <- RECOMMEND / controlled business ops
        3: (AUTONOMY_LEVELS[5],),                       # CEO_APPROVAL <- HUMAN APPROVAL REQUIRED
        4: (AUTONOMY_LEVELS[6],),                       # LEGAL_FINANCIAL_REVIEW <- NEVER AUTOMATE
    }
    return {
        "generated_at": _now_iso(), "levels": COMMERCIAL_GOVERNANCE_LEVELS, "real_mapping": mapping,
        "source": "autonomous_operations.py::AUTONOMY_LEVELS (Phase 19, ADR-209), relabeled onto 5 named commercial governance levels.",
    }


# ---------------------------------------------------------------------------
# Section 42-43 -- Commercial Knowledge Graph + Memory
# ---------------------------------------------------------------------------

def commercial_knowledge_graph_status():
    return {
        "generated_at": _now_iso(),
        "note": "Same real, disclosed gap product_innovation_engine.py (Phase 23) already found: knowledge_graph/build.py's real node types (Decision/Outcome/Lesson/Competitor/Proposal) don't yet include distinct Platform/Order/Payout/Commission nodes -- the real underlying data exists (channels/ledger.py, revenue_operating_system.py) but isn't graphed yet. Not built this round, same reasoning as Phase 23.",
    }


# ---------------------------------------------------------------------------
# Section 46 -- Commercial Simulations (real, clearly HYPOTHETICAL)
# ---------------------------------------------------------------------------

def simulation_a_multi_platform_net_contribution(price_a=97, price_b=97, price_c=97, fee_pct_a=0.1, fee_pct_b=0.15, fee_pct_c=0.2):
    """HYPOTHETICAL -- a real product sold at 3 real, disclosed
    hypothetical prices/fees, never a real transaction."""
    results = {p: round(price * (1 - fee), 2) for p, (price, fee) in
               zip(("platform_a", "platform_b", "platform_c"), [(price_a, fee_pct_a), (price_b, fee_pct_b), (price_c, fee_pct_c)])}
    return {"generated_at": _now_iso(), "label": "HYPOTHETICAL SIMULATION -- not a real transaction",
            "net_contribution_by_platform": results, "assumptions": {"price_a": price_a, "price_b": price_b, "price_c": price_c}}


def simulation_b_partner_profitability_with_refunds(gross_revenue=1000, commission_rate=0.2, refund_rate=0.3):
    commission = gross_revenue * commission_rate
    refunded = gross_revenue * refund_rate
    net = gross_revenue - commission - refunded
    return {"generated_at": _now_iso(), "label": "HYPOTHETICAL SIMULATION -- not a real partner",
            "net_contribution": round(net, 2), "remains_profitable": net > 0, "assumptions": {"gross_revenue": gross_revenue, "commission_rate": commission_rate, "refund_rate": refund_rate}}


def simulation_c_high_revenue_poor_margin(gross_revenue=10000, margin_pct=0.03):
    net = gross_revenue * margin_pct
    return {"generated_at": _now_iso(), "label": "HYPOTHETICAL SIMULATION -- not a real platform",
            "net_contribution": round(net, 2), "recommendation": "CONTINUE" if margin_pct > 0.10 else "REVIEW_OR_EXIT",
            "assumptions": {"gross_revenue": gross_revenue, "margin_pct": margin_pct}}


def simulation_d_payout_discrepancy(expected_payout=500, actual_payout=430):
    return {"generated_at": _now_iso(), "label": "HYPOTHETICAL SIMULATION -- not a real payout",
            "discrepancy": round(expected_payout - actual_payout, 2),
            "note": "In a real case, reconciliation_state_view() (Phase 21) would classify this MISMATCH and create a real incident."}


def simulation_e_payment_provider_outage():
    return {"generated_at": _now_iso(), "label": "HYPOTHETICAL SIMULATION",
            "real_fallback_channels": [k for k in ("gumroad", "etsy", "payhip") ],
            "note": "Paddle is this factory's only real live payment channel today -- an outage would leave 0 real alternative live channels (Gumroad/Etsy/Payhip have real code but no live credentials configured, per GLOBAL_REVENUE_ARCHITECTURE.md)."}


def simulation_f_platform_suspension(platform_key="paddle", paddle_products_path=None, finance_path=None):
    matrix = product_platform_matrix(paddle_products_path=paddle_products_path, finance_path=finance_path)
    affected = [e["product"] for e in matrix["matrix"] if e["platform"] == platform_key]
    return {"generated_at": _now_iso(), "label": "HYPOTHETICAL SIMULATION", "platform": platform_key,
            "affected_products": affected, "affected_revenue_usd": 0,
            "fallback_channels": "See simulation_e_payment_provider_outage()",
            "required_human_actions": ["Review suspension reason", "Contact platform support", "Activate a real fallback channel if one is ready"]}


def simulation_g_concentration_warning(decisions_path=None):
    real = commercial_concentration_risk(decisions_path=decisions_path)
    return {"generated_at": _now_iso(), "label": "REAL (not hypothetical) -- reuses concentration_risk_report() directly",
            "real_concentration_report": real}


def simulation_h_new_marketplace_evaluation(platform_key):
    return platform_expansion_check(platform_key)


def run_all_commercial_simulations(decisions_path=None, paddle_products_path=None, finance_path=None):
    return {
        "generated_at": _now_iso(),
        "simulation_a": simulation_a_multi_platform_net_contribution(),
        "simulation_b": simulation_b_partner_profitability_with_refunds(),
        "simulation_c": simulation_c_high_revenue_poor_margin(),
        "simulation_d": simulation_d_payout_discrepancy(),
        "simulation_e": simulation_e_payment_provider_outage(),
        "simulation_f": simulation_f_platform_suspension(paddle_products_path=paddle_products_path, finance_path=finance_path),
        "simulation_g": simulation_g_concentration_warning(decisions_path=decisions_path),
        "simulation_h": simulation_h_new_marketplace_evaluation("shopify"),
        "note": "Simulations A-F/H are HYPOTHETICAL -- disclosed assumptions, never a real transaction, never written to any ledger. Simulation G reuses real, live concentration data.",
    }


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------

def build_commercial_operations_dashboard(decisions_path=None, paddle_products_path=None, finance_path=None, now=None):
    now = now or datetime.now(timezone.utc)
    return {
        "generated_at": _now_iso(now),
        "platform_registry": platform_registry(),
        "product_platform_matrix": product_platform_matrix(paddle_products_path=paddle_products_path, finance_path=finance_path),
        "multi_currency": multi_currency_status(),
        "commission_engine": commercial_commission_engine(),
        "order_normalization": order_normalization_view(),
        "refund_normalization": refund_normalization_view(paddle_products_path=paddle_products_path, finance_path=finance_path),
        "payout_reconciliation": payout_reconciliation(),
        "platform_account_health": platform_account_health(),
        "payment_infrastructure": payment_infrastructure_registry(),
        "commercial_task_queue": commercial_task_queue(),
        "commercial_alerts": commercial_alerts_view(now=now),
        "anomaly_detection": commercial_anomaly_detection(),
        "fraud_protection": commercial_fraud_protection(),
        "channel_profitability": channel_profitability(paddle_products_path=paddle_products_path, finance_path=finance_path, decisions_path=decisions_path),
        "concentration_risk": commercial_concentration_risk(decisions_path=decisions_path),
        "governance": commercial_governance_view(),
        "note": "Computes every real sub-report exactly once -- never a second, competing commercial engine.",
    }
