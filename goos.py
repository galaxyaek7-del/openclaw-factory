#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Opportunity Operating System (GOOS) — ADR-171, 2026-08-05.

Founder directive: "the highest decision-making system inside Galaxy
Forge... no digital product may enter production until GOOS has
evaluated and approved it." Flagged via AskUserQuestion before any code
(2 real conflicts): GOOS's 20 named dimensions and 15-section report
map almost entirely onto real, already-built systems -- building a
second, independent evaluation engine would duplicate profit_oracle.py
(9 real hard gates + weighted score), executive_quality_gate.py (23
real checks), strategic_intelligence_core.py (11-dim score),
capital_allocation_engine.py (14/15-dim Investment Score), and
business_dossier.py/production_blueprint.py/autonomous_business_
builder.py (the real report sections) -- and the directive's own
85/100 minimum threshold is meaningfully stricter than the real,
currently-enforced 65/100 weighted floor (profit_oracle.MIN_
OPPORTUNITY_SCORE / tier weighting). **Founder's answers, both
recommended**: build GOOS as a consolidation/citation layer, never a
parallel engine; GOOS's own score is advisory only -- it does not
replace or tighten the real 65-floor gate that already governs
production, since doing so silently would be a real business-policy
change (fewer real ACCEPTED opportunities, working against the
"shortest path to revenue" priority set earlier this session) smuggled
in as an engineering side effect.

Real, disclosed limitation found during research, honored literally
per this factory's own Truth First Constitution (ADR-160): TAM/SAM/SOM
has zero real data source anywhere in this factory (profit_oracle.py's
own docstring: "No free real TAM (dollar market size) data source
exists... No guessed TAM.") -- reported as NOT_MEASURABLE for every
niche, never estimated.

"No product may enter production until GOOS approves" is honored as:
GOOS's own `approved` field is a real, computed citation of the exact
same real gate that already exists (decision_engine's ACCEPTED status)
-- GOOS does not gate anything itself, it reports on the gate that
already does, plus its own advisory 85-line for visibility. Building a
second, competing gate would be the real duplication this factory's
whole session has repeatedly declined.
"""

from datetime import datetime, timezone

REAL = "REAL"
NOT_MEASURABLE = "NOT_MEASURABLE"

GOOS_ADVISORY_THRESHOLD = 85

# The directive's 20 named dimensions, each mapped to its real source.
# TAM/SAM/SOM is the one genuine, permanent gap (no real data source
# anywhere in this factory) -- disclosed, never estimated.
DIMENSION_SOURCES = {
    "real_customer_pain": "executive_quality_gate.check_customer_pain_evidence() + evaluation_snapshot.scores.market_demand",
    "market_size_tam_sam_som": "NOT_MEASURABLE -- no free real market-sizing data source exists anywhere in this factory (profit_oracle.py's own disclosed limitation)",
    "willingness_to_pay": "executive_quality_gate.check_willingness_to_pay()",
    "competition_level": "evaluation_snapshot.scores.competition_favorability + executive_quality_gate.check_market_saturation()",
    "difficulty_of_copying": "evaluation_snapshot.defensibility",
    "scalability": "value_engine.compute_value_profile()'s scalability dimension (ACCEPTED opportunities only) / executive_quality_gate.check_scalability()",
    "recurring_revenue_potential": "capital_allocation_engine.investment_score()'s recurring_revenue_potential (ACCEPTED opportunities only)",
    "automation_potential": "evaluation_snapshot.scores.automation_potential",
    "global_demand": "value_engine.compute_value_profile()'s global_demand dimension (ACCEPTED opportunities only)",
    "ai_leverage": "profit_oracle._score_ai_leverage() (ladder_opportunity_score's own ai_leverage field)",
    "development_complexity": "strategic_intelligence_core.strategic_score()'s difficulty dimension (technical_complexity)",
    "time_to_mvp": "NOT_MEASURABLE -- no real historical per-niche build-duration signal exists anywhere in this factory (same disclosed gap class as execution_status.py's own 'estimated_completion: Unknown')",
    "strategic_fit": "evaluation_snapshot.scores.long_term_value + capital_allocation_engine.investment_score()'s strategic_importance",
    "brand_fit": "brand_dna.py::validate_customer_facing_text() applied to the real product concept text, when available",
    "long_term_asset_value": "value_engine.compute_value_profile()'s long_term_strategic_value dimension (ACCEPTED opportunities only)",
    "profitability": "profit_oracle.ladder_opportunity_score()'s profit_potential + butter_price()",
    "customer_lifetime_value": "executive_quality_gate.check_customer_retention_potential() -- a real proxy, not a real dollar CLV figure (confirmed: no real CLV computation exists anywhere in this factory)",
    "risk_level": "evaluation_snapshot.risk",
    "legal_risk": "executive_quality_gate.check_legal_compliance_risk()",
    "operational_complexity": "executive_quality_gate.check_infrastructure_readiness() + check_automation_readiness()",
}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _latest_snapshot(niche):
    """The real, pre-acceptance evaluation snapshot every evaluated
    niche has -- decision_engine.store's own record, never re-computed.
    None if this niche has never been evaluated at all."""
    from decision_engine import store
    records = store.find_decisions_by_niche(niche)
    if not records:
        return None
    return records[-1]


def evaluate_dimensions(niche, snapshot=None):
    """Real, per-niche citation over all 20 named dimensions. Every
    value traces to `snapshot` (decision_engine's own real evaluation
    record) or is honestly NOT_MEASURABLE. Never a second, competing
    evaluation of the niche."""
    snapshot = snapshot if snapshot is not None else _latest_snapshot(niche)
    if snapshot is None:
        return {"status": "NOT_YET_EVALUATED", "reason": f"لا سجل قرار حقيقي مسجَّل لهذا النيتش بعد — {niche!r} لم يُقيَّم قط عبر decision_engine"}

    snap = snapshot.get("evaluation_snapshot") or {}
    scores = snap.get("scores") or {}
    risk = snap.get("risk") or {}

    dims = {
        "real_customer_pain": {"value": scores.get("market_demand"), "source": DIMENSION_SOURCES["real_customer_pain"]},
        "market_size_tam_sam_som": {"value": NOT_MEASURABLE, "source": DIMENSION_SOURCES["market_size_tam_sam_som"]},
        "willingness_to_pay": {"value": "see executive_quality_gate.check_willingness_to_pay() -- real per-niche market evidence, not re-queried here", "source": DIMENSION_SOURCES["willingness_to_pay"]},
        "competition_level": {"value": scores.get("competition_favorability"), "source": DIMENSION_SOURCES["competition_level"]},
        "difficulty_of_copying": {"value": snap.get("defensibility"), "source": DIMENSION_SOURCES["difficulty_of_copying"]},
        "scalability": {"value": "NOT_MEASURABLE_PRE_ACCEPTANCE -- value_engine.compute_value_profile() only computes this for a real ACCEPTED decision", "source": DIMENSION_SOURCES["scalability"]},
        "recurring_revenue_potential": {"value": "NOT_MEASURABLE_PRE_ACCEPTANCE", "source": DIMENSION_SOURCES["recurring_revenue_potential"]},
        "automation_potential": {"value": scores.get("automation_potential"), "source": DIMENSION_SOURCES["automation_potential"]},
        "global_demand": {"value": "NOT_MEASURABLE_PRE_ACCEPTANCE", "source": DIMENSION_SOURCES["global_demand"]},
        "ai_leverage": {"value": snap.get("ai_leverage"), "source": DIMENSION_SOURCES["ai_leverage"]},
        "development_complexity": {"value": snap.get("technical_complexity"), "source": DIMENSION_SOURCES["development_complexity"]},
        "time_to_mvp": {"value": NOT_MEASURABLE, "source": DIMENSION_SOURCES["time_to_mvp"]},
        "strategic_fit": {"value": scores.get("long_term_value"), "source": DIMENSION_SOURCES["strategic_fit"]},
        "brand_fit": {"value": "NOT_EVALUATED -- no product concept text supplied to this call", "source": DIMENSION_SOURCES["brand_fit"]},
        "long_term_asset_value": {"value": "NOT_MEASURABLE_PRE_ACCEPTANCE", "source": DIMENSION_SOURCES["long_term_asset_value"]},
        "profitability": {"value": scores.get("profit_potential"), "source": DIMENSION_SOURCES["profitability"]},
        "customer_lifetime_value": {"value": "see executive_quality_gate.check_customer_retention_potential() -- a proxy, never a real dollar CLV figure", "source": DIMENSION_SOURCES["customer_lifetime_value"]},
        "risk_level": {"value": risk.get("level"), "source": DIMENSION_SOURCES["risk_level"]},
        "legal_risk": {"value": "see executive_quality_gate.check_legal_compliance_risk() -- real per-niche check, not re-queried here", "source": DIMENSION_SOURCES["legal_risk"]},
        "operational_complexity": {"value": "see executive_quality_gate.check_infrastructure_readiness()/check_automation_readiness()", "source": DIMENSION_SOURCES["operational_complexity"]},
    }
    return {"status": "EVALUATED", "dimensions": dims, "snapshot_decided_at": snapshot.get("decided_at")}


def goos_score(niche, snapshot=None):
    """The real, disclosed, additive advisory score (0-100). Never
    replaces or feeds back into profit_oracle.py's real acceptance
    floor (65/100 weighted, tier-adjusted) -- a separate, informational
    number, always reported alongside that real gate's own verdict,
    never instead of it."""
    result = evaluate_dimensions(niche, snapshot=snapshot)
    if result["status"] != "EVALUATED":
        return {"score": None, "status": result["status"], "reason": result.get("reason")}

    dims = result["dimensions"]
    numeric = {k: v["value"] for k, v in dims.items() if isinstance(v["value"], (int, float))}
    # Real, disclosed weighting: pain/competition/automation/profitability/
    # strategic_fit carry double weight -- the 5 dimensions this factory's
    # own real decision_engine floor already treats as load-bearing
    # (matches profit_oracle.py's own real hard-gate emphasis, never a
    # fabricated new priority order).
    DOUBLE_WEIGHT = {"real_customer_pain", "competition_level", "automation_potential", "profitability", "strategic_fit"}
    total_weight = 0
    weighted_sum = 0
    for name, value in numeric.items():
        w = 2 if name in DOUBLE_WEIGHT else 1
        weighted_sum += value * w
        total_weight += w
    score = round(weighted_sum / total_weight, 1) if total_weight else None
    return {
        "score": score,
        "status": "EVALUATED",
        "dimensions_scored": len(numeric),
        "dimensions_total": len(dims),
        "note": f"Advisory only -- {len(numeric)}/{len(dims)} dimensions had a real numeric value at evaluation time; the rest (market size, pre-acceptance scalability/revenue/global-demand/long-term-value, time-to-mvp, brand fit) are honestly NOT_MEASURABLE at this stage, not blended into the score with a guessed number.",
        "meets_advisory_85_threshold": (score is not None and score >= GOOS_ADVISORY_THRESHOLD),
        "real_production_gate": "unchanged -- decision_engine's own real ACCEPTED/REJECTED/DEFERRED status, profit_oracle.py's real 65/100 weighted floor. This score never gates anything.",
    }


def build_opportunity_intelligence_report(niche):
    """The one real aggregator -- computes the real snapshot exactly
    once and threads it through every one of the 15 named report
    sections. Post-acceptance sections (Business Model/Revenue
    Potential/Strategic Advantages/Estimated ROI/Recommended Pricing/
    Expansion Potential) are only populated for a real ACCEPTED
    opportunity -- honestly NOT_AVAILABLE otherwise, never guessed."""
    from decision_engine import store

    snapshot = _latest_snapshot(niche)
    if snapshot is None:
        return {
            "niche": niche,
            "status": "NOT_YET_EVALUATED",
            "reason": f"لا سجل قرار حقيقي مسجَّل لهذا النيتش بعد — {niche!r} لم يُقيَّم قط عبر decision_engine",
            "generated_at": _now_iso(),
        }

    is_accepted = snapshot.get("status") == "ACCEPTED"
    dims_result = evaluate_dimensions(niche, snapshot=snapshot)
    score_result = goos_score(niche, snapshot=snapshot)

    post_acceptance = None
    if is_accepted:
        import value_engine
        import capital_allocation_engine as cae
        import autonomous_business_builder as abb
        profile = value_engine.compute_value_profile(niche)
        investment = cae.investment_score(niche)
        post_acceptance = {
            "business_model_and_revenue_potential": {"value_profile": profile, "source": "value_engine.compute_value_profile()"},
            "estimated_roi": {"value": profile.get("board_summary", {}).get("expected_roi") if profile else None, "source": "value_engine.compute_value_profile()'s board_summary.expected_roi"},
            "recommended_pricing": {"value": "see profit_oracle.butter_price(niche) -- real per-niche pricing floor, not re-queried here", "source": "profit_oracle.butter_price()"},
            "competitor_analysis": abb.competitor_map(niche, profile=profile),
            "weaknesses": abb.risk_assessment(niche, profile=profile),
            "investment_score_14dim": investment,
        }

    return {
        "niche": niche,
        "status": snapshot.get("status"),
        "executive_summary": {
            "real_decision": snapshot.get("status"),
            "goos_advisory_score": score_result.get("score"),
            "meets_85_advisory_line": score_result.get("meets_advisory_85_threshold"),
            "real_reasoning": snapshot.get("reasoning"),
        },
        "problem_analysis": {"pain_level": (snapshot.get("evaluation_snapshot") or {}).get("scores", {}).get("market_demand"), "source": "evaluation_snapshot.scores.market_demand"},
        "customer_analysis": {"note": "see executive_quality_gate.check_willingness_to_pay()/check_customer_acquisition_difficulty()/check_customer_retention_potential() -- real per-niche checks, not re-queried here"},
        "competitor_analysis": (post_acceptance or {}).get("competitor_analysis", "NOT_AVAILABLE -- competitor_map() requires a real ACCEPTED decision (autonomous_business_builder.py's own scope)"),
        "market_analysis": {"tam_sam_som": NOT_MEASURABLE, "global_demand": (post_acceptance or {}).get("business_model_and_revenue_potential", "NOT_AVAILABLE pre-acceptance")},
        "business_model": (post_acceptance or {}).get("business_model_and_revenue_potential", "NOT_AVAILABLE -- requires a real ACCEPTED decision"),
        "revenue_potential": (post_acceptance or {}).get("business_model_and_revenue_potential", "NOT_AVAILABLE -- requires a real ACCEPTED decision"),
        "strategic_advantages": {"ai_leverage": (snapshot.get("evaluation_snapshot") or {}).get("ai_leverage"), "defensibility": (snapshot.get("evaluation_snapshot") or {}).get("defensibility")},
        "weaknesses": (post_acceptance or {}).get("weaknesses", "NOT_AVAILABLE -- risk_assessment() requires a real ACCEPTED decision"),
        "implementation_difficulty": dims_result.get("dimensions", {}).get("development_complexity"),
        "automation_possibilities": dims_result.get("dimensions", {}).get("automation_potential"),
        "estimated_roi": (post_acceptance or {}).get("estimated_roi", "NOT_AVAILABLE -- requires a real ACCEPTED decision"),
        "recommended_pricing": (post_acceptance or {}).get("recommended_pricing", "NOT_AVAILABLE -- requires a real ACCEPTED decision"),
        "expansion_potential": "see global_opportunity_exchange.py/growth_engine.py -- company-wide, not re-queried per-niche here",
        "overall_recommendation": {
            "real_verdict": snapshot.get("status"),
            "goos_advisory_score": score_result,
        },
        "dimensions": dims_result,
        "generated_at": _now_iso(),
    }


def self_improvement_sources():
    """Pure citation -- GOOS never builds a second learning loop.
    decision_engine/learning.py::recalibration_report() (deliberately
    never auto-applied) and evolution_queue.py's real outcome
    measurement already are this factory's real "learn from successful/
    failed launches" mechanisms."""
    return {
        "successful_and_failed_launches": "decision_engine/learning.py::recalibration_report() -- real per-dimension historical-evidence statistics, deliberately never auto-applied (needs a separate founder decision to apply).",
        "outcome_tracking": "evolution_queue.py's real measure_outcome() -- IMPROVED/DEGRADED/NO_CHANGE/NOT_ENOUGH_DATA, no sooner than 7 real elapsed days after implementation.",
        "customer_behaviour": "brand_dna.py::continuous_improvement_sources() -- honestly FUTURE_INSTRUMENTATION for real customer questions/complaints (zero real intake path exists yet).",
        "market_changes_and_competitor_movements": "competitor_discovery.py's real cached database + market_hunter.py's real live HN/GitHub ingestion.",
        "note": "GOOS does not add a 4th, competing learning loop -- it cites the 3 that already exist.",
    }


# -- Strategic Impact Score (Galaxy Forge Executive Constitution, ADR-177, 2026-08-06) --
# The Global Dominance Directive asked for every project to receive a
# "Strategic Impact Score." Real, disclosed composite of 2 already-real
# scores -- GOOS's own advisory score (this module) and the Capital
# Allocation Engine's Investment Score (enterprise_capital_allocation.py,
# ADR-165/176) -- never a 3rd, independent scoring computation.
def strategic_impact_score(niche):
    """Real composite: avg(GOOS advisory score, extended Investment
    Score's own real numeric dimensions) when both exist; honestly
    reports whichever real component is unavailable rather than
    silently defaulting to the other alone."""
    import enterprise_capital_allocation as eca

    goos_result = goos_score(niche)
    try:
        investment = eca.extended_investment_score(niche)
        numeric_investment = [v["value"] for v in investment.values() if isinstance(v, dict) and isinstance(v.get("value"), (int, float))]
        investment_avg = round(sum(numeric_investment) / len(numeric_investment), 1) if numeric_investment else None
    except Exception as e:
        investment_avg = None
        investment = {"error": str(e)}

    components = [v for v in (goos_result.get("score"), investment_avg) if v is not None]
    composite = round(sum(components) / len(components), 1) if components else None

    return {
        "strategic_impact_score": composite,
        "components": {
            "goos_advisory_score": goos_result.get("score"),
            "capital_allocation_investment_score_avg": investment_avg,
        },
        "note": "A disclosed avg of 2 already-real scores (GOOS's advisory score, ADR-171; Capital Allocation's extended Investment Score, ADR-165/176) -- never a 3rd independent computation. Honestly None if neither real component is available.",
        "generated_at": _now_iso(),
    }


# -- Strategic Intelligence Engine, Revenue Mode (ADR-178, 2026-08-06) --
#
# The founder's "STRATEGIC INTELLIGENCE LAYER -- REVENUE MODE" directive
# asks for a permanent engine that ranks opportunities GLOBALLY --
# what to build next, why it beats the alternatives, evidence,
# realistic revenue, difficulty, defensibility, copyability, customer
# pain, underserved market, what to ignore -- rejecting anything that
# duplicates existing capability or creates engineering work without
# revenue, integrated permanently into the Executive Brain, feeding the
# production pipeline.
#
# Research before writing code found every one of the 10 named
# questions and 8 named recommendation fields already has a real,
# citable answer scattered across this module's own evaluate_
# dimensions()/goos_score(), profit_oracle.py, and capital_allocation_
# engine.py. The one genuine, verified gap: nothing in this factory
# ranks candidate niches AGAINST EACH OTHER -- every existing ranker
# (scheduler.py, execution_status.py) only orders an already-ACCEPTED
# portfolio, which is currently EMPTY (0 real ACCEPTED opportunities,
# verified live via decision_engine.store as of 2026-08-06) -- and
# nothing rejects a candidate niche/product specifically for
# duplicating an existing product family or creating cost without
# revenue (the two existing mechanical duplicate-checks in this
# factory, evolution_queue.py's _duplicate_architecture_check() and
# enterprise_executive_brain.py's _detect_duplicated_work(), both
# operate on engineering proposals/department code overlap, never on
# candidate products).
#
# "must directly feed the production pipeline" repeats the exact
# tension this module's own docstring already resolved for GOOS itself
# (ADR-171, confirmed via a real AskUserQuestion): advisory citation
# into executive_brain.py's arbitration, never a second competing gate.
# Applied directly here without a fresh AskUserQuestion -- the
# identical question, for this identical module, has already been
# asked and answered once; re-asking it again would be redundant, not
# careful.
#
# Passive-only, same discipline as automation_opportunity_scanner.py's
# own docstring: ranking never triggers a new live evaluation.
# Candidate niches come from real decision_engine.store records (any
# status -- DEFERRED/REJECTED niches are real, searchable
# reconsideration candidates per store.find_decisions_by_niche()'s own
# contract) plus automation_opportunity_scanner.py's real static seed
# list (ladders=None, ADR-175) for niches never evaluated at all.

def _confidence_from_coverage(dimensions_scored, dimensions_total):
    """Disclosed heuristic label, same class as executive_brain.py's own
    _confidence_estimate() -- never a fabricated precision number."""
    if not dimensions_total:
        return "n/a"
    ratio = dimensions_scored / dimensions_total
    if ratio >= 0.6:
        return "high"
    if ratio >= 0.3:
        return "medium"
    return "low"


def _is_real_value(value):
    """A real, disclosed heuristic for 'this dimension actually has a
    citable real value' -- excludes Unknown/NOT_MEASURABLE and the
    pointer-only strings evaluate_dimensions() uses for checks that
    exist but weren't re-queried here."""
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        return value not in ("Unknown", NOT_MEASURABLE) and not value.startswith(("NOT_", "see "))
    return False


def _candidate_evidence_and_fields(niche, snapshot):
    """The directive's 8 required per-recommendation fields (confidence
    score, evidence sources, expected ROI, competition score,
    difficulty, time to first revenue, long-term recurring potential,
    strategic importance), bundled from this module's own real
    evaluate_dimensions()/goos_score() -- never a 9th, competing
    scoring computation."""
    dims_result = evaluate_dimensions(niche, snapshot=snapshot)
    score_result = goos_score(niche, snapshot=snapshot)
    dims = dims_result.get("dimensions", {})

    evidence_sources = sorted({
        d["source"] for d in dims.values() if _is_real_value(d.get("value"))
    })

    return {
        "confidence_score": _confidence_from_coverage(score_result.get("dimensions_scored"), score_result.get("dimensions_total")),
        "evidence_sources": evidence_sources,
        "expected_roi": dims.get("profitability", {"value": "Unknown"}),
        "competition_score": dims.get("competition_level", {"value": "Unknown"}),
        "difficulty": dims.get("development_complexity", {"value": "Unknown"}),
        "time_to_first_revenue": dims.get("time_to_mvp", {"value": "Unknown"}),
        "long_term_recurring_potential": dims.get("recurring_revenue_potential", {"value": "Unknown"}),
        "strategic_importance": dims.get("strategic_fit", {"value": "Unknown"}),
        "goos_advisory_score": score_result.get("score"),
        "score_status": score_result.get("status"),
    }


def _duplicates_existing_family(ladder, family_distribution):
    """Real, mechanical duplicate-capability check at the candidate-
    PRODUCT level -- genuinely new (the 2 existing duplicate-checks in
    this factory both operate on engineering proposals, never
    products). Cites global_opportunity_exchange.product_family_
    distribution()'s own real Counter over ACCEPTED decisions -- never
    a second concentration computation."""
    from product_families.mapping import resolve_product_family

    family = resolve_product_family(ladder)
    if not family:
        return {"duplicates_existing_family": False, "reason": f"لا عائلة منتج معروفة لـ ladder={ladder!r} -- لا فحص تكرار ممكن"}
    if family_distribution.get("answer") == "NOT ENOUGH EVIDENCE":
        return {"duplicates_existing_family": False, "family": family,
                "reason": "لا محفظة ACCEPTED حقيقية بعد للمقارنة -- لا تكرار قابل للاكتشاف اليوم"}
    distribution = family_distribution.get("distribution", {})
    if family in distribution:
        return {"duplicates_existing_family": True, "family": family,
                "reason": f"عائلة المنتج '{family}' موجودة فعلاً في {distribution[family]['count']} قرار ACCEPTED حقيقي ({distribution[family]['pct']}%)",
                "source": "global_opportunity_exchange.product_family_distribution()"}
    return {"duplicates_existing_family": False, "family": family,
            "reason": f"عائلة المنتج '{family}' غير ممثَّلة بعد في المحفظة الحقيقية ACCEPTED"}


def _engineering_without_revenue(niche, snapshot):
    """Only computable post-acceptance -- real engineering_cost/
    expected_revenue both need a real ACCEPTED decision's value_engine
    profile. Honestly Unknown pre-acceptance -- never a fabricated
    rejection off a guessed cost/revenue pair."""
    if snapshot.get("status") != "ACCEPTED":
        return {"engineering_without_revenue": "Unknown", "reason": "يتطلب فحصاً حقيقياً بعد قرار ACCEPTED فعلي -- لا يُخمَّن قبل ذلك"}
    import capital_allocation_engine as cae
    investment = cae.investment_score(niche)
    cost = investment.get("engineering_cost", {}).get("value")
    revenue = investment.get("expected_revenue", {}).get("value")
    if not isinstance(cost, (int, float)) or not isinstance(revenue, (int, float)):
        return {"engineering_without_revenue": "Unknown", "reason": "تكلفة الهندسة و/أو الإيراد المتوقع غير مسجَّلين بعد كرقمين حقيقيين"}
    flagged = cost > 0 and revenue <= 0
    return {"engineering_without_revenue": flagged, "engineering_cost": cost, "expected_revenue": revenue,
            "source": "capital_allocation_engine.investment_score()"}


def rank_build_candidates(decisions_path=None, top_n=10):
    """The one genuine gap: global ranking of candidate niches AGAINST
    EACH OTHER -- not just within an ACCEPTED portfolio (which
    scheduler.py/execution_status.py already rank, and which is
    currently empty). Real candidate sources only, both passive: every
    niche with a real decision_engine record (any status), plus
    automation_opportunity_scanner.py's real static seed list for
    niches never evaluated at all. Never triggers a new live
    evaluation -- reads only decision_engine.store and market_hunter.
    SEED_CATEGORIES, the same passive discipline automation_
    opportunity_scanner.py's own docstring establishes."""
    from decision_engine import store
    import automation_opportunity_scanner as scanner
    import global_opportunity_exchange as gox

    latest = store.latest_decision_per_niche(decisions_path)
    family_distribution = gox.product_family_distribution(decisions_path)

    scored, not_yet_scorable = [], []
    for decision in latest.values():
        niche = decision.get("niche")
        ladder = decision.get("ladder")
        fields = _candidate_evidence_and_fields(niche, decision)
        duplicate_check = _duplicates_existing_family(ladder, family_distribution)
        revenue_check = _engineering_without_revenue(niche, decision)
        prior_status = decision.get("status")
        entry = {
            "niche": niche, "ladder": ladder, "prior_status": prior_status,
            "decided_at": decision.get("decided_at"),
            **fields,
            "duplicate_check": duplicate_check,
            "engineering_without_revenue_check": revenue_check,
            "reject_recommended": (
                bool(duplicate_check.get("duplicates_existing_family"))
                or revenue_check.get("engineering_without_revenue") is True
                or prior_status == "REJECTED"
            ),
        }
        if isinstance(fields.get("goos_advisory_score"), (int, float)):
            scored.append(entry)
        else:
            entry["reason"] = fields.get("score_status")
            not_yet_scorable.append(entry)

    seen_niches = {store._normalize_key(d.get("niche")) for d in latest.values()}
    never_evaluated = [
        {
            "niche": seed["niche"], "ladder": seed["ladder"], "prior_status": "NEVER_EVALUATED",
            "source": seed["source"],
            "reason": "لم يُقيَّم عبر decision_engine قط -- يحتاج تقييماً حقيقياً قبل ترتيبه برقم حقيقي، لا تخمين",
        }
        for seed in scanner._seed_candidates(ladders=None)
        if store._normalize_key(seed["niche"]) not in seen_niches
    ]

    scored.sort(key=lambda e: e["goos_advisory_score"], reverse=True)

    return {
        "build_next": [e for e in scored if not e["reject_recommended"]][:top_n],
        "ignore": [e for e in scored if e["reject_recommended"]],
        "not_yet_scorable": not_yet_scorable,
        "never_evaluated": never_evaluated[:top_n],
        "total_real_candidates": len(latest) + len(never_evaluated),
        "real_accepted_portfolio_size": sum(1 for d in latest.values() if d.get("status") == "ACCEPTED"),
        "generated_at": _now_iso(),
    }


def strategic_intelligence_engine_report(decisions_path=None, top_n=10):
    """The one real aggregator the directive asked for -- 'what should
    be built next,' as a permanent, re-runnable report. Feeds
    executive_brain.py's arbitration as an advisory citation only; the
    real production gate is unchanged (see note below and this
    module's own header)."""
    ranking = rank_build_candidates(decisions_path=decisions_path, top_n=top_n)
    return {
        "ranking": ranking,
        "real_production_gate": "unchanged -- decision_engine's own real ACCEPTED/REJECTED/DEFERRED status, profit_oracle.py's real 65/100 weighted floor. This report never gates or triggers production itself.",
        "note": "Advisory-only global ranking layer -- same resolution as goos_score() (ADR-171, confirmed via AskUserQuestion) applied directly to this identical 'must feed the pipeline' tension without re-asking.",
        "generated_at": _now_iso(),
    }
