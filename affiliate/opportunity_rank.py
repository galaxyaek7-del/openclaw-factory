#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — First-commission opportunity ranking.

Transparent ranking for "which program should carry the first verified
commission attempt". It reuses priority.score_program() for the economics
and terms axes, then applies feasibility from eligibility_matrix:

  final = economics_score x eligibility_factor x payout_factor + account_bonus

Unknowns are penalised, never treated as positive. A high commission with
unknown Algeria eligibility ranks below a modest one with evidence. Every
component is returned so the order can be explained. Not a revenue forecast.
"""
from . import eligibility_matrix, priority, registry

ELIGIBILITY_FACTOR = {
    "APPROVED": 1.0, "ELIGIBLE_EVIDENCE_FOUND": 1.0, "PENDING_APPROVAL": 0.8,
    "APPLICATION_SUBMITTED": 0.8, "APPLICATION_PREPARED": 0.6, "ELIGIBILITY_UNKNOWN": 0.4,
    "DISCOVERED": 0.4, "INELIGIBLE": 0.0, "REJECTED": 0.0, "SUSPENDED": 0.0, "CLOSED": 0.0,
}
PAYOUT_FACTOR = {
    "PAYOUT_VERIFIED": 1.0, "PAYOUT_ROUTE_CONDITIONAL": 0.7,
    "PAYOUT_UNVERIFIED": 0.4, "PAYOUT_ROUTE_BLOCKED": 0.1,
}
# An affiliate account that already exists removes the signup/approval step.
ACCOUNT_BONUS = 10


def rank(opportunities=None, evidence=None):
    opps = opportunities if opportunities is not None else registry.load_opportunities()
    m = {r["opportunity_id"]: r for r in eligibility_matrix.matrix(opps, evidence)}
    out = []
    for opp in opps:
        oid = opp.get("opportunity_id", "UNKNOWN")
        econ = priority.score_program(registry.program_record(opp, [], []))
        row = m[oid]
        ef = ELIGIBILITY_FACTOR.get(row["eligibility_state"], 0.4)
        pf = PAYOUT_FACTOR.get(row["payout_state"], 0.4)
        bonus = ACCOUNT_BONUS if row.get("account_observed") else 0
        final = round(econ["score"] * ef * pf + bonus, 1)
        out.append({
            "opportunity_id": oid, "program_name": row["program_name"],
            "final_score": final,
            "components": {"economics_score": econ["score"], "economics_axes": econ["components"],
                           "eligibility_state": row["eligibility_state"], "eligibility_factor": ef,
                           "payout_state": row["payout_state"], "payout_factor": pf,
                           "account_bonus": bonus},
            "rankable": ef > 0 and not econ["warnings"],
            "next_action": row["next_action"],
            "not_a_revenue_forecast": True,
        })
    out.sort(key=lambda r: (r["rankable"], r["final_score"]), reverse=True)
    return out
