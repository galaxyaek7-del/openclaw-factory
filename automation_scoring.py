#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI Automation Revenue Engine — Scoring (ADR-164, 2026-07-31).

Calls profit_oracle.py::ladder_opportunity_score() verbatim -- never a
second scoring algorithm -- and relabels its already-real output into
the directive's named Quality Gate fields. Every field either cites a
real sub-value from that call, or is honestly "UNKNOWN" per the
directive's own explicit instruction ("If evidence is missing, say
UNKNOWN instead of hallucinating") -- never a fabricated number.
"""

from datetime import datetime, timezone

import automation_intelligence

UNKNOWN = "UNKNOWN"


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def score_opportunity(niche, ladder, evidence_path=None, db_file=None):
    """The one real per-candidate scorer. Never re-implements profit_
    oracle's real scoring/gates -- relabels its real output only."""
    import profit_oracle

    result = profit_oracle.ladder_opportunity_score(niche, ladder=ladder, evidence_path=evidence_path, db_file=db_file)
    components = result["components"]

    is_b2b, b2b_reason = automation_intelligence.is_b2b(niche, ladder=ladder)
    saturation = automation_intelligence.reject_saturated(niche)

    # Estimated Build Time: this factory tracks real per-call AI COST
    # (revenue_pipeline.plan.estimate_production_cost()), never real
    # per-product build DURATION -- a different unit. Conflating the two
    # would be exactly the kind of "optimistic description unsupported
    # by code" this directive forbids. Honestly UNKNOWN.
    estimated_build_time = {
        "value": UNKNOWN,
        "reason": "No real per-product build-DURATION tracking exists anywhere in this factory (distinct from real AI-call cost tracking, which does exist -- see known_risks/cost_context below).",
    }

    # Potential Monthly Revenue Range: recurring_revenue_potential is a
    # real, ladder-grounded 0-100 POTENTIAL score, not a probability or
    # a customer-volume forecast -- this factory has zero real recurring
    # customer/subscription data to multiply into an actual dollar
    # range. Presenting one would be a fabricated number, explicitly
    # forbidden by this directive. Cites the real score, honestly
    # declines to convert it into an invented dollar range.
    potential_monthly_revenue_range = {
        "value": UNKNOWN,
        "real_recurring_revenue_potential_score": components.get("recurring_revenue_potential"),
        "reason": "recurring_revenue_potential is a real, ladder-grounded 0-100 potential score, not a customer-volume forecast -- no real recurring-customer data exists in this factory to compute an actual dollar range. A fabricated multiplication is explicitly forbidden.",
    }

    known_risks = [result.get("risk"), saturation["detail"]]
    if not result["accepted"]:
        known_risks.append({"hard_gate_failure": result["reason"]})

    return {
        "niche": niche,
        "ladder": ladder,
        "accepted": result["accepted"],
        "evidence_source": {
            "answer": result["payment_evidence"] or [],
            "source": "profit_oracle.py::ladder_opportunity_score()['payment_evidence'] -- real, cited proof-of-payment records (empty list, never fabricated, when none recorded).",
        },
        "confidence_score": {
            "answer": result.get("confidence"),
            "source": "profit_oracle.py::score_opportunity()['confidence'] (via ladder_opportunity_score()).",
        },
        "known_risks": known_risks,
        "estimated_build_time": estimated_build_time,
        "estimated_selling_price": {
            "answer": result.get("price"),
            "source": "profit_oracle.py::butter_price() (via ladder_opportunity_score()) -- real, niche-specific, never a flat number.",
        },
        "potential_monthly_revenue_range": potential_monthly_revenue_range,
        "reason_for_recommendation": result.get("reason"),
        "is_b2b": {"answer": is_b2b, "reason": b2b_reason},
        "automation_percentage": automation_intelligence.automation_percentage(ladder),
        "market_saturation_check": saturation,
        "ladder_score": result.get("ladder_score"),
        "generated_at": _now_iso(),
    }
