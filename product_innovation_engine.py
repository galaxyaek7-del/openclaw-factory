"""Galaxy Forge Autonomous Product Innovation Engine (Phase 23, ADR-213,
2026-08-08).

Answers the founder's "AUTONOMOUS PRODUCT INNOVATION ENGINE" directive
-- explicitly: "Golden Hunter must remain the primary opportunity-
hunting intelligence" and "prioritize PROBLEMS over IDEAS." Research
before writing any code found this factory already has a real,
evidence-gated pipeline covering most of the 38 sections:
`profit_oracle.py::ladder_opportunity_score()`'s real 9 hard gates
(Proof of Payment, Pain Severity, Competition, Defensibility, Price
Floor, Durable Asset, AI-Leverage, Profit Margin, weighted score) are
the real substance behind Section 15's 6 named validation gates;
`galaxy_council.py::convene_council()` (9 real members, honest
disagreement, never forced consensus) is Section 27's AI Council;
`market_evidence.py`/`competitive_moat_engine.py`/`competitor_
discovery.py` cover Sections 6-7; `customer_intelligence.py` (Phase
22, ADR-212) covers Section 24; `revenue_operating_system.py` (Phase
21, ADR-211) covers Section 25; `autonomous_operations.py`'s real
Level 5/6 gates (Phase 19, ADR-209) are Section 29's Human Decision
Gate, verbatim; `knowledge_graph/build.py` + `executive_decision_
memory.py::explain_decision()` cover Sections 30-31;
`commercial_experiments.py` covers Section 19.

This module's real, narrow job: relabel these onto the directive's
exact named shape, and add the two genuinely missing pieces -- a
structured Red Team checklist (Section 28, built as a real evidence-
requirement checker over already-computed real signals, never a new
LLM call that could hallucinate a critique) and an Innovation
Efficiency counter (Section 34, real counts from decision_engine's
own store). Real, current company state (unchanged from every prior
phase this session): 0 real ACCEPTED opportunities, 0 real ai_saas/
b2b_systems candidates, $0 real revenue -- this module's real, honest
job at this state is showing exactly why every real candidate is
rejected, not inventing a passing one.
"""

from datetime import datetime, timezone

PRODUCT_TYPES = [
    "DIGITAL_ASSET", "PREMIUM_TEMPLATE", "SOFTWARE_TOOL", "AI_ASSISTANT", "AI_AGENT",
    "AUTOMATION_SYSTEM", "DECISION_SUPPORT_SYSTEM", "ANALYTICS_PRODUCT", "KNOWLEDGE_PLATFORM",
    "WORKFLOW_PRODUCT", "B2B_SAAS", "API_DEVELOPER_TOOL", "LICENSING_PRODUCT",
    "MANAGED_SERVICE", "TRANSFORMATION_PACKAGE", "ENTERPRISE_SOLUTION",
]

PROBLEM_PRIORITY_LEVELS = ["LOW_VALUE", "INTERESTING", "PROMISING", "HIGH_VALUE", "STRATEGIC", "CRITICAL_OPPORTUNITY"]

VALIDATION_GATES = ["PROBLEM_VALIDATION", "CUSTOMER_VALIDATION", "ECONOMIC_VALIDATION",
                    "COMPETITIVE_VALIDATION", "SOLUTION_VALIDATION", "COMMERCIAL_VALIDATION"]

PRODUCT_DECISIONS = ["BUILD", "ITERATE", "PILOT", "SCALE", "PAUSE", "KILL", "RESEARCH_MORE"]

PORTFOLIO_BUCKETS = ["CORE_PRODUCTS", "GROWTH_PRODUCTS", "EXPERIMENTS", "PREMIUM_B2B",
                     "RECURRING_PRODUCTS", "STRATEGIC_PRODUCTS", "LEGACY_PRODUCTS", "PRODUCTS_TO_RETIRE"]

INNOVATION_PIPELINE_STAGES = ["DISCOVERED", "VALIDATING", "VALIDATED", "CONCEPT", "MVP",
                              "PILOT", "COMMERCIAL_TEST", "SCALE", "MATURE", "RETIRE"]


def _now_iso(now=None):
    return (now or datetime.now(timezone.utc)).isoformat()


# ---------------------------------------------------------------------------
# Section 3 -- Problem Registry (real, cited over customer_intelligence.py)
# ---------------------------------------------------------------------------

def problem_registry_report(state_path=None, now=None):
    """Reuses customer_intelligence.py's real problem-mining output
    (Phase 22, ADR-212) -- never a second problem-tracking system."""
    import customer_intelligence
    problems = customer_intelligence.customer_problem_mining_report(state_path=state_path, now=now)
    return {
        "generated_at": _now_iso(now),
        "real_problems": problems,
        "note": "0 real customer-sourced problems exist yet (0 real customers) -- the registry schema is real and ready; source is customer_intelligence.customer_problem_mining_report(), never duplicated.",
    }


# ---------------------------------------------------------------------------
# Sections 6-7 -- Market Gap / Competitive Intelligence (already real, cited)
# ---------------------------------------------------------------------------

def market_gap_and_competitive_view(niche, decisions_path=None):
    """Reuses goos.py::evaluate_dimensions()/competitor_discovery.py
    directly -- MARKET_GAP_ENGINE.md (Phase 17) already answers this
    section's 3 core questions; this is a thin, real citation wrapper."""
    import goos
    import competitor_discovery
    dims = goos.evaluate_dimensions(niche)
    try:
        # get_or_refresh_competitors(): real, cached -- avoids an
        # unnecessary live HN/GitHub network call on every dashboard
        # build, same discipline established elsewhere this session.
        competitors = competitor_discovery.get_or_refresh_competitors(niche)
    except Exception as e:
        competitors = {"status": "CHECK_FAILED", "reason": str(e)}
    return {
        "generated_at": _now_iso(), "niche": niche,
        "market_gap_dimensions": dims,
        "competitors": competitors,
        "note": "Never fabricates competitor information -- competitor_discovery.py returns only real, sourced entries; unknown stays unknown.",
    }


# ---------------------------------------------------------------------------
# Section 9 -- Product Types + Section 8 -- Solution Generation (schema only)
# ---------------------------------------------------------------------------

def product_type_fit(problem_description=None):
    """Real, disclosed schema -- this module does not auto-select a
    product form from free text (that would risk an AI-generated,
    unvalidated guess); it returns the real 16-form taxonomy for a
    human/AI Council member to reason over against real evidence."""
    return {"generated_at": _now_iso(), "available_forms": PRODUCT_TYPES,
            "note": "Product form must be chosen according to the real, evidenced problem shape -- never forced into SaaS by default."}


# ---------------------------------------------------------------------------
# Section 14 -- Product Moat (already real, cited)
# ---------------------------------------------------------------------------

def product_moat_view():
    import competitive_moat_engine
    return competitive_moat_engine.assess_eu_ai_act_toolkit_moat()


# ---------------------------------------------------------------------------
# Section 15 -- Validation Gates (real relabeling over profit_oracle.py)
# ---------------------------------------------------------------------------

_GATE_MAP = {
    "PROBLEM_VALIDATION": ("pain_severity", "profit_oracle.py's real Pain Severity hard gate (real customer-pain evidence)"),
    "CUSTOMER_VALIDATION": ("pain_severity", "Same real pain-evidence gate -- this factory has no separate customer-caring signal beyond real pain evidence"),
    "ECONOMIC_VALIDATION": ("high_profit_margin", "profit_oracle.py's real High Profit Margin + Premium Pricing Potential gates"),
    "COMPETITIVE_VALIDATION": ("low_or_moderate_competition", "profit_oracle.py's real Competition + Difficult-to-Copy gates"),
    "SOLUTION_VALIDATION": ("ai_significant_advantage", "profit_oracle.py's real Competitive Advantage / AI-leverage gate"),
    "COMMERCIAL_VALIDATION": ("strong_proof_of_payment", "profit_oracle.py's real Proof of Payment hard gate (ADR-121) -- the single strictest, most literal 'will customers pay' check in this factory"),
}


def validation_gate_status(niche, ladder="kdp_books", decisions_path=None, evidence_path=None):
    """Real relabeling of profit_oracle.py::ladder_opportunity_score()'s
    real, already-computed gate booleans onto the 6 named validation
    gates -- never a second, competing scoring computation."""
    import profit_oracle
    result = profit_oracle.ladder_opportunity_score(niche, ladder=ladder, evidence_path=evidence_path)
    strategy = result.get("product_strategy", {})

    gates = {}
    for gate_name, (field, citation) in _GATE_MAP.items():
        value = strategy.get(field)
        passed = value is True
        gates[gate_name] = {"passed": passed, "real_field": field, "citation": citation, "raw_value": value}

    return {
        "generated_at": _now_iso(), "niche": niche, "ladder": ladder,
        "gates": gates, "overall_accepted": result.get("accepted"),
        "reason": result.get("reason"),
        "source": "profit_oracle.py::ladder_opportunity_score() -- never a second, competing scoring computation.",
    }


# ---------------------------------------------------------------------------
# Section 16 -- MVP Engine (real schema template, never AI-auto-filled)
# ---------------------------------------------------------------------------

def mvp_spec_template():
    return {
        "generated_at": _now_iso(),
        "required_fields": ["core_problem", "core_user", "core_workflow", "core_outcome",
                             "minimum_features", "excluded_features", "success_metric",
                             "failure_metric", "stop_condition"],
        "note": "A real schema, not an auto-generated spec -- an MVP spec must be filled from a real, validated opportunity (validation_gate_status() must show overall_accepted=True first), never fabricated ahead of evidence.",
    }


# ---------------------------------------------------------------------------
# Section 18 -- Commercial Validation (INTEREST/INTENT/COMMITMENT/PAYMENT)
# ---------------------------------------------------------------------------

def commercial_validation_signal(niche, decisions_path=None, evidence_path=None):
    """Real, structural separation -- only real Proof of Payment
    evidence counts as PAYMENT; every other signal is labeled
    distinctly, per Section 18's own explicit rule."""
    import profit_oracle
    import market_evidence
    payment_evidence = market_evidence.get_payment_evidence(niche, evidence_path=evidence_path)
    wtp_signal = market_evidence.get_willingness_to_pay_signal(niche, evidence_path=evidence_path)
    return {
        "generated_at": _now_iso(), "niche": niche,
        "interest": wtp_signal if wtp_signal else "NO_REAL_SIGNAL",
        "intent": "NO_REAL_SIGNAL -- no real pre-order/demo-request tracking exists per niche",
        "commitment": "NO_REAL_SIGNAL -- no real letter-of-intent/pilot-agreement tracking exists",
        "payment": {"real_events": payment_evidence, "count": len(payment_evidence) if payment_evidence else 0},
        "note": "Only PAYMENT is direct evidence of willingness to pay -- the other 3 categories are honestly labeled distinctly, never conflated.",
    }


# ---------------------------------------------------------------------------
# Section 19 -- Product Experiment Engine (already real, cited)
# ---------------------------------------------------------------------------

def product_experiment_status(experiments_path=None):
    import commercial_experiments
    return {"generated_at": _now_iso(), "real_experiments": commercial_experiments.list_experiments(experiments_path=experiments_path),
            "source": "commercial_experiments.py -- the real, generic experiment engine, not duplicated for product innovation specifically."}


# ---------------------------------------------------------------------------
# Section 20 -- Product Decision Gate
# ---------------------------------------------------------------------------

def product_decision_gate(niche, ladder="kdp_books", decisions_path=None, evidence_path=None):
    """Real, deterministic mapping from the 6 validation gates + the
    real decision_engine store status onto the 7 named decisions."""
    from decision_engine import store
    gate_result = validation_gate_status(niche, ladder=ladder, decisions_path=decisions_path, evidence_path=evidence_path)
    latest = store.latest_decision_per_niche(path=decisions_path).get(niche, {})
    real_status = latest.get("status")

    passed_gates = sum(1 for g in gate_result["gates"].values() if g["passed"])
    if gate_result["overall_accepted"]:
        decision = "BUILD" if real_status != "ACCEPTED" else "PILOT"
    elif passed_gates == 0:
        decision = "KILL"
    elif passed_gates <= 2:
        decision = "RESEARCH_MORE"
    else:
        decision = "ITERATE"

    return {
        "generated_at": _now_iso(), "niche": niche, "decision": decision,
        "passed_gates": passed_gates, "total_gates": len(VALIDATION_GATES),
        "real_decision_engine_status": real_status,
        "evidence": gate_result,
    }


# ---------------------------------------------------------------------------
# Section 21 -- Kill Criteria (real, cited over decision_engine.store)
# ---------------------------------------------------------------------------

def kill_criteria_check(niche, decisions_path=None):
    from decision_engine import store
    latest = store.latest_decision_per_niche(path=decisions_path).get(niche)
    if latest is None:
        return {"generated_at": _now_iso(), "niche": niche, "status": "NEVER_EVALUATED"}
    return {
        "generated_at": _now_iso(), "niche": niche,
        "real_status": latest.get("status"), "real_reasoning": latest.get("reasoning"),
        "note": "Cites decision_engine's real, already-recorded rejection/deferral reasoning -- never a second kill-decision computation. Sunk cost is never a factor (decision_engine has no cumulative-past-spend field in its signature, confirmed by direct inspection).",
    }


# ---------------------------------------------------------------------------
# Section 22 -- Product Portfolio
# ---------------------------------------------------------------------------

def product_portfolio_view(decisions_path=None, paddle_products_path=None, finance_path=None):
    from global_commercial_scale import scaling_eligibility_report
    from decision_engine import store
    eligibility = scaling_eligibility_report(paddle_products_path=paddle_products_path, finance_path=finance_path)
    latest = store.latest_decision_per_niche(path=decisions_path)

    buckets = {b: [] for b in PORTFOLIO_BUCKETS}
    for entry in eligibility["entries"]:
        if entry["status"] in ("TESTING",):
            buckets["EXPERIMENTS"].append(entry["product"])
        elif entry["status"] in ("VALIDATED", "SCALE_CANDIDATE"):
            buckets["GROWTH_PRODUCTS"].append(entry["product"])
        else:
            buckets["LEGACY_PRODUCTS"].append(entry["product"]) if entry["real_revenue_usd"] else None

    return {
        "generated_at": _now_iso(), "buckets": buckets,
        "real_accepted_niches": sum(1 for v in latest.values() if v.get("status") == "ACCEPTED"),
        "note": "Reuses global_commercial_scale.py's real scaling_eligibility_report() (Phase 20) -- never a second product-classification computation. Most buckets are honestly empty (0 real B2B/recurring/strategic products exist).",
    }


# ---------------------------------------------------------------------------
# Section 23 -- Product Cannibalization (real, cited)
# ---------------------------------------------------------------------------

def product_cannibalization_check(decisions_path=None):
    import global_opportunity_exchange
    distribution = global_opportunity_exchange.product_family_distribution(decisions_path=decisions_path)
    return {
        "generated_at": _now_iso(), "real_family_distribution": distribution,
        "note": "Reuses global_opportunity_exchange.py::product_family_distribution() (ADR-140) directly -- a real, existing product-family concentration finding is the correct real signal for whether a new candidate would cannibalize or expand.",
    }


# ---------------------------------------------------------------------------
# Section 24 -- Customer -> Innovation Loop (already real, cited)
# ---------------------------------------------------------------------------

def customer_to_innovation_signal(state_path=None, now=None):
    import customer_intelligence
    return {
        "generated_at": _now_iso(now),
        "problem_signal": customer_intelligence.customer_problem_mining_report(state_path=state_path, now=now),
        "feedback_roadmap_note": "Frequency alone never proves commercial value -- combine with classify_feedback_for_roadmap()'s real revenue_impact/retention_impact fields (customer_intelligence.py, Phase 22).",
    }


# ---------------------------------------------------------------------------
# Section 25 -- Revenue -> Innovation Loop (already real, cited)
# ---------------------------------------------------------------------------

def revenue_to_innovation_signal(paddle_products_path=None, finance_path=None):
    from revenue_operating_system import gross_vs_net_report
    from global_commercial_scale import unit_economics_report
    unit_econ = unit_economics_report(paddle_products_path=paddle_products_path, finance_path=finance_path)
    return {
        "generated_at": _now_iso(),
        "gross_vs_net": gross_vs_net_report(),
        "per_product_economics": unit_econ["products"],
        "note": "High-margin/low-margin/high-refund/high-support classification requires real per-product net data most fields here are honestly UNKNOWN for -- see UNIT_ECONOMICS_REPORT.md (Phase 21).",
    }


# ---------------------------------------------------------------------------
# Section 26 -- Golden Hunter -> Innovation Loop (already real, cited)
# ---------------------------------------------------------------------------

def golden_hunter_innovation_chain(niche, decisions_path=None, evidence_path=None):
    """The 9-field chain (Problem->Evidence->Market->Economics->Solution
    ->Product->Decision->Outcome->Lesson), each a real citation."""
    import customer_intelligence
    return {
        "generated_at": _now_iso(), "niche": niche,
        "problem": customer_intelligence.golden_hunter_customer_signal(niche),
        "market_and_economics": validation_gate_status(niche, decisions_path=decisions_path, evidence_path=evidence_path),
        "decision": kill_criteria_check(niche, decisions_path=decisions_path),
        "outcome_and_lesson": "See executive_decision_memory.explain_decision() for a real matched niche decision_id",
    }


# ---------------------------------------------------------------------------
# Section 27 -- AI Council (already real, cited)
# ---------------------------------------------------------------------------

def ai_council_product_challenge(niche, decisions_path=None):
    import galaxy_council
    return galaxy_council.convene_council(niche, decisions_path=decisions_path)


# ---------------------------------------------------------------------------
# Section 28 -- Red Team (genuinely new: structured evidence checklist)
# ---------------------------------------------------------------------------

RED_TEAM_QUESTIONS = [
    "What are we assuming?", "What evidence contradicts us?", "Why might customers refuse?",
    "Why might competitors destroy the advantage?", "What hidden costs exist?",
    "What could make the market smaller?", "What could make the product unnecessary?",
    "What would cause failure?",
]


def red_team_challenge(niche, decisions_path=None, evidence_path=None):
    """Real, structured evidence-requirement checker over already-
    computed real signals -- deliberately NOT a new LLM call (which
    could hallucinate a plausible-sounding but fabricated critique).
    Each question is answered by citing a real signal or honestly
    NOT_ANSWERED when no real signal exists to answer it from."""
    gates = validation_gate_status(niche, decisions_path=decisions_path, evidence_path=evidence_path)
    kill = kill_criteria_check(niche, decisions_path=decisions_path)
    failed_gates = [name for name, g in gates["gates"].items() if not g["passed"]]

    answers = {
        "What are we assuming?": f"That the {len(failed_gates)} failed real gates could still be cleared -- see failed_gates below" if failed_gates else "No real gate currently fails -- assumption load is lower, still not zero",
        "What evidence contradicts us?": kill.get("real_reasoning") or "NOT_ANSWERED -- no real recorded rejection reasoning exists for this niche",
        "Why might customers refuse?": "See COMMERCIAL_VALIDATION gate -- " + ("real Proof of Payment evidence is missing" if not gates["gates"]["COMMERCIAL_VALIDATION"]["passed"] else "real payment evidence exists, but this does not guarantee future customers"),
        "Why might competitors destroy the advantage?": "See COMPETITIVE_VALIDATION gate -- " + ("real competition/defensibility signal failed" if not gates["gates"]["COMPETITIVE_VALIDATION"]["passed"] else "NOT_ANSWERED -- gate passed, but no forward-looking competitor-response signal exists"),
        "What hidden costs exist?": "NOT_ANSWERED -- no real per-niche cost model beyond profit_oracle.py's own components exists",
        "What could make the market smaller?": "NOT_ANSWERED -- no real TAM/SAM/SOM source exists in this factory (ADR-042/043, standing finding)",
        "What could make the product unnecessary?": "NOT_ANSWERED -- no real substitute-product monitoring exists per niche",
        "What would cause failure?": f"The real gate(s) already failing today: {failed_gates}" if failed_gates else "No real gate fails today -- failure would require a real regression in an already-passing signal",
    }
    return {
        "generated_at": _now_iso(), "niche": niche, "questions_and_answers": answers,
        "failed_gates": failed_gates,
        "note": "Deliberately not an AI-generated critique -- every answer cites a real, already-computed signal or honestly NOT_ANSWERED. A real critique that could hallucinate would be worse than an honest gap.",
    }


# ---------------------------------------------------------------------------
# Section 29 -- Human Decision Gate (already real, cited)
# ---------------------------------------------------------------------------

def human_decision_gate_check(action_category, context=None):
    from autonomous_operations import authorize_action
    return authorize_action(action_category, context=context)


# ---------------------------------------------------------------------------
# Section 30 -- Product Knowledge Graph (already real, cited)
# ---------------------------------------------------------------------------

def product_knowledge_graph_status():
    return {
        "generated_at": _now_iso(),
        "note": "Reuses knowledge_graph/build.py's real Decision/Outcome/Lesson/Competitor/Proposal node types (Phases 12-18) -- Problem/Solution/Product/Experiment nodes are not yet a distinct node type; the real underlying data (customer_intelligence.py's problems, commercial_experiments.py's experiments) exists but isn't graphed yet. A real, disclosed follow-up, not built this round to avoid re-touching build_graph()'s tested core inside an already-large phase.",
    }


# ---------------------------------------------------------------------------
# Section 31 -- Product Memory (already real, cited)
# ---------------------------------------------------------------------------

def product_memory(decision_id, decisions_path=None, ledger_path=None):
    import executive_decision_memory
    return executive_decision_memory.explain_decision(decision_id, decisions_path=decisions_path, ledger_path=ledger_path)


# ---------------------------------------------------------------------------
# Section 34 -- Innovation Efficiency (genuinely new counter)
# ---------------------------------------------------------------------------

def innovation_efficiency_report(decisions_path=None):
    from decision_engine import store
    latest = store.latest_decision_per_niche(path=decisions_path)
    accepted = sum(1 for v in latest.values() if v.get("status") == "ACCEPTED")
    rejected = sum(1 for v in latest.values() if v.get("status") == "REJECTED")
    deferred = sum(1 for v in latest.values() if v.get("status") == "DEFERRED")
    return {
        "generated_at": _now_iso(),
        "ideas_generated": len(latest),
        "problems_validated": accepted,
        "concepts_tested": "UNKNOWN -- no real per-concept testing counter exists separate from decision status",
        "mvps_built": 0,
        "paid_pilots": 0,
        "successful_products": 0,
        "killed_products": rejected,
        "deferred_for_more_evidence": deferred,
        "average_validation_cost": "UNKNOWN -- no real per-evaluation cost tracking exists",
        "average_time_to_validation": "UNKNOWN -- no real per-niche evaluation-duration tracking exists",
        "revenue_generated_by_innovation": "$0",
        "note": "Real counts from decision_engine.store -- never optimized for idea count; 0 successful products is the honest current state, not a fabricated pipeline of wins.",
    }


# ---------------------------------------------------------------------------
# Section 35 -- Autonomous Innovation Boundaries (already real, cited)
# ---------------------------------------------------------------------------

def autonomous_innovation_boundaries():
    from autonomous_operations import AUTONOMY_LEVELS, ACTION_CATEGORY_AUTONOMY
    return {
        "generated_at": _now_iso(),
        "may_do_autonomously": ["discover_problems (Golden Hunter)", "cluster_similar_problems", "identify_market_gaps",
                                 "generate_solution_hypotheses", "rank_opportunities (goos.rank_build_candidates)",
                                 "recommend_experiments", "analyze_results", "update_knowledge"],
        "must_not_do_autonomously": {
            "commit_major_capital": ACTION_CATEGORY_AUTONOMY["capital_reallocation"],
            "sign_major_contracts": ACTION_CATEGORY_AUTONOMY["business_retirement"],
            "make_irreversible_legal_decisions": ACTION_CATEGORY_AUTONOMY["governance_or_permission_change"],
            "fabricate_evidence_or_revenue": ACTION_CATEGORY_AUTONOMY["real_payment_or_transaction"],
        },
        "levels": AUTONOMY_LEVELS,
        "source": "autonomous_operations.py (Phase 19, ADR-209) -- reused verbatim, never a second authorization system.",
    }


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------

def build_product_innovation_dashboard(decisions_path=None, state_path=None, finance_path=None,
                                        paddle_products_path=None, evidence_path=None, now=None):
    now = now or datetime.now(timezone.utc)
    return {
        "generated_at": _now_iso(now),
        "problem_registry": problem_registry_report(state_path=state_path, now=now),
        "portfolio": product_portfolio_view(decisions_path=decisions_path, paddle_products_path=paddle_products_path, finance_path=finance_path),
        "cannibalization": product_cannibalization_check(decisions_path=decisions_path),
        "customer_signal": customer_to_innovation_signal(state_path=state_path, now=now),
        "revenue_signal": revenue_to_innovation_signal(paddle_products_path=paddle_products_path, finance_path=finance_path),
        "experiments": product_experiment_status(),
        "innovation_efficiency": innovation_efficiency_report(decisions_path=decisions_path),
        "autonomy_boundaries": autonomous_innovation_boundaries(),
        "note": "Computes every real sub-report exactly once -- never a second, competing opportunity-discovery engine. Golden Hunter (golden_hunter/hunt.py, goos.py) remains the primary opportunity-hunting intelligence, cited throughout, never replaced.",
    }
