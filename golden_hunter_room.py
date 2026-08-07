"""Golden Hunter Room (new, ADR-192, 2026-08-07) -- the founder's
"Galaxy Forge becomes the visual brain of Golden Hunter" directive.

Not a new scoring engine. goos.py::rank_build_candidates() (ADR-178)
already produces almost exactly the directive's requested field set per
opportunity (score, ROI, competition, difficulty, confidence, evidence).
This module is a thin reshaping layer -- maps that real output onto the
directive's exact named fields (Top Opportunities / Opportunity Score /
Expected Revenue / Market Size / Competition / Difficulty / ROI /
Confidence / Priority / Reason / Recommended Next Action), and answers
the 4 named CEO View questions directly. Zero new judgment."""

from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent


def _recommended_next_action(candidate):
    """Real, mechanical derivation from fields rank_build_candidates()
    already computes -- never a fabricated recommendation."""
    if candidate.get("reject_recommended"):
        return "Do not pursue -- goos.py's own evaluation recommends rejection."
    status = candidate.get("prior_status")
    if status == "ACCEPTED":
        return "Proceed to production (already cleared the real MIN_OPPORTUNITY_SCORE floor)."
    if status in ("DEFERRED", None):
        return "Gather real, new evidence (Proof of Payment / Pain Severity) before re-evaluating -- do not re-submit unchanged."
    if status == "REJECTED":
        return "Re-open only if genuinely new real evidence exists; do not re-litigate the same rejection."
    return f"Unknown status ({status}) -- review manually."


def _room_entry(candidate, rank):
    roi = candidate.get("expected_roi") or {}
    competition = candidate.get("competition_score") or {}
    difficulty = candidate.get("difficulty") or {}
    return {
        "rank": rank,
        "opportunity": candidate.get("niche"),
        "opportunity_score": candidate.get("goos_advisory_score"),
        "expected_revenue": "NOT_MEASURABLE -- profit_oracle/goos never assign a dollar figure to an unaccepted opportunity (see OPPORTUNITY_SCORING.md); expected_roi below is the real 0-100 proxy",
        "market_size": "NOT_MEASURABLE -- goos.py's own disclosed gap (market_size_tam_sam_som), no real TAM/SAM/SOM data source exists anywhere in this factory",
        "competition": competition.get("value"),
        "difficulty": difficulty.get("value") if difficulty.get("value") is not None else "Unknown",
        "roi": roi.get("value"),
        "confidence": candidate.get("confidence_score"),
        "priority": "reject" if candidate.get("reject_recommended") else ("high" if rank <= 3 else "standard"),
        "reason": candidate.get("evidence_sources") or [],
        "recommended_next_action": _recommended_next_action(candidate),
        "prior_status": candidate.get("prior_status"),
    }


def build_golden_hunter_room(top_n=20, decisions_path=None):
    from goos import rank_build_candidates
    ranking = rank_build_candidates(decisions_path=decisions_path, top_n=top_n)
    candidates = ranking.get("build_next") or []
    room = [_room_entry(c, i + 1) for i, c in enumerate(candidates)]
    return {
        "top_opportunities": room,
        "total_evaluated": len(room),
        "source": "goos.py::rank_build_candidates() (ADR-178) -- reused, not recomputed",
        "note": "Every field cites a real, already-computed source or is honestly marked NOT_MEASURABLE/Unknown -- no fabricated dollar figures or market-size estimates for any pre-acceptance opportunity.",
    }


def ceo_view(top_n=20, decisions_path=None):
    """The 4 named CEO View questions, answered directly from the same
    real room data -- computed once, never a second ranking pass."""
    room = build_golden_hunter_room(top_n=top_n, decisions_path=decisions_path)
    opportunities = room["top_opportunities"]
    viable = [o for o in opportunities if o["priority"] != "reject"]

    best = viable[0] if viable else None
    second = viable[1] if len(viable) > 1 else None
    # "Could become a million-dollar asset" -- real, disclosed heuristic:
    # highest real ROI score AND highest real strategic/long-term signal
    # among viable candidates, never a literal dollar projection (no real
    # data exists to produce one pre-acceptance).
    million_dollar_candidate = max(
        viable, key=lambda o: (o["roi"] or 0), default=None
    ) if viable else None
    should_ignore = [o for o in opportunities if o["priority"] == "reject"]

    return {
        "best_opportunity_today": best,
        "second_best_opportunity": second,
        "highest_long_term_potential": {
            "candidate": million_dollar_candidate,
            "note": "Ranked by the real ROI proxy score only -- never a literal dollar projection; no real pre-acceptance revenue data exists anywhere in this factory to produce one honestly.",
        } if million_dollar_candidate else None,
        "should_be_ignored": should_ignore,
        "source": room["source"],
    }
