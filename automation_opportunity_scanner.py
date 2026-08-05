#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI Automation Revenue Engine — Opportunity Scanner (ADR-164,
2026-07-31).

Real candidate sources, both PASSIVE (never triggers a new live
evaluation cycle):

1. market_hunter.py::SEED_CATEGORIES -- a real, static, deterministic
   candidate list (that module's own docstring: "not a live market
   scan"). Filtered to the automation_catalog.py's real ladder tags.
2. Real, ALREADY-RECORDED decisions from data/decisions.jsonl (via
   decision_engine.ranking.rank_all(), a pure read), filtered the same
   way -- real historical evaluations, never re-evaluated here.

Deliberately does NOT call golden_hunter.hunt.run_hunt() from this
scanner: direct inspection (ADR-164 research) found run_hunt() calls
orchestrator.run_cycle(execute_production=False, ...) -- the
execute_production=False flag only gates real PRODUCTION/PUBLISH, not
real DECISION RECORDING; run_hunt() genuinely evaluates real signals
and appends real new decisions every time it's called. A passive
dashboard scanner must never trigger that as a side effect of being
refreshed -- the exact class of bug ADR-162's own addendum discloses
and fixed in reality_audit.py's safety gate, applied here proactively
instead of discovered the hard way a second time.
"""

from datetime import datetime, timezone

from automation_catalog import AUTOMATION_CATEGORIES

NO_VERIFIED_OPPORTUNITY = "NO VERIFIED OPPORTUNITY FOUND"

_AUTOMATION_LADDERS = set(AUTOMATION_CATEGORIES.values())


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _seed_candidates(ladders=None):
    """`ladders=None` (Market Domination Engine, ADR-175, 2026-08-05)
    means no filter -- every real SEED_CATEGORIES entry, any ladder.
    Default unchanged (_AUTOMATION_LADDERS) so every existing real
    caller of this module keeps its exact original behavior."""
    import market_hunter
    return [
        {"niche": c["niche"], "ladder": c["ladder"], "source": "market_hunter.py::SEED_CATEGORIES (real, static, deterministic candidate list)"}
        for c in market_hunter.SEED_CATEGORIES
        if ladders is None or c["ladder"] in ladders
    ]


def _historical_candidates(decisions_path=None, ladders=None):
    """Same `ladders=None` = no filter convention as _seed_candidates()."""
    import decision_engine.ranking as ranking
    seen = set()
    out = []
    for d in ranking.rank_all(path=decisions_path):
        ladder = d.get("ladder")
        niche = d.get("niche")
        if (ladders is None or ladder in ladders) and niche and niche not in seen:
            seen.add(niche)
            out.append({
                "niche": niche, "ladder": ladder,
                "source": f"data/decisions.jsonl (decision_engine, real prior evaluation, status={d.get('status')})",
                "prior_status": d.get("status"),
            })
    return out


def scan_candidates(limit=20, decisions_path=None):
    """Real, passive candidate scan -- never triggers a new live
    evaluation cycle. Deduplicates by niche, seed candidates first."""
    seen_niches = set()
    candidates = []
    for c in _seed_candidates(ladders=_AUTOMATION_LADDERS) + _historical_candidates(decisions_path=decisions_path, ladders=_AUTOMATION_LADDERS):
        if c["niche"] in seen_niches:
            continue
        seen_niches.add(c["niche"])
        candidates.append(c)
        if len(candidates) >= limit:
            break

    if not candidates:
        return {
            "answer": NO_VERIFIED_OPPORTUNITY,
            "reason": "No real candidate niche (market_hunter.py::SEED_CATEGORIES or data/decisions.jsonl) matches any of the 15 named automation categories' real ladders.",
            "generated_at": _now_iso(),
        }
    return {"candidates": candidates, "count": len(candidates), "generated_at": _now_iso()}
