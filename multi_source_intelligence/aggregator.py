"""
Evidence accumulation (ADR-059) — requirement 5: accumulate evidence from
multiple independent sources for one opportunity. This is a standalone,
deliberately-called function — NOT wired into orchestrator.run_cycle()
or profit_oracle.py's scoring, per the explicit instruction "No
production logic may change. Only improve evidence quality." It is
available for a human or a future, separately-approved decision to
consume; it does not silently alter what the Decision Engine accepts or
rejects today.
"""

from multi_source_intelligence.coverage import evidence_coverage_score


def accumulate_evidence(niche, max_results=10):
    coverage = evidence_coverage_score(niche, max_results=max_results)
    return {
        "niche": niche,
        "generated_at": coverage["generated_at"],
        "coverage": {
            "checked": coverage["checked"], "succeeded": coverage["succeeded"],
            "failed": coverage["failed"], "unknown": coverage["unknown"],
            "coverage_pct": coverage["coverage_pct"],
        },
        "evidence_by_source": coverage["results"],
    }
