#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI Automation Revenue Engine — shared intelligence helpers (ADR-164,
2026-07-31).

Real, disclosed, mechanical helpers shared by the scanner/scoring/
dashboard modules -- never a second scoring algorithm. Reuses
executive_quality_gate.py::check_market_saturation() and profit_
oracle.py's real per-ladder constants directly.
"""

from datetime import datetime, timezone

# Real, disclosed, non-exhaustive B2B signal -- either a real B2B-
# adjacent ladder tag, or a real B2B-phrase match in the niche's own
# text (mirrors the real phrasing already used by market_hunter.py's
# own SEED_CATEGORIES entries, e.g. "for accounting firms"). Never
# claims to be a complete B2B classifier.
_B2B_LADDERS = ("b2b_systems", "ai_saas")
_B2B_PHRASES = (
    "for accounting firms", "for logistics companies", "for wholesale distributors",
    "for small businesses", "for e-commerce businesses", "for marketing agencies",
    "for saas developers", "for b2b startups", "for financial advisors",
    "for enterprises", "for agencies", "for teams", "for companies",
)


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def is_b2b(niche_text, ladder=None):
    """Real, disclosed, non-exhaustive B2B detector -- a real ladder
    tag match or a real B2B-phrase match in the niche's own text.
    Honestly False (never a guessed True) when neither real signal
    is present."""
    if ladder in _B2B_LADDERS:
        return True, f"ladder {ladder!r} is a real B2B-adjacent ladder"
    lowered = (niche_text or "").lower()
    hits = [p for p in _B2B_PHRASES if p in lowered]
    if hits:
        return True, f"real B2B-phrase match in niche text: {hits[0]!r}"
    return False, "no real B2B ladder tag or phrase match found"


def reject_saturated(niche, competitor_db=None):
    """Pure citation of executive_quality_gate.py::check_market_
    saturation() (ADR-102/105/126) -- never a second saturation check."""
    import executive_quality_gate as eqg
    result = eqg.check_market_saturation(niche, competitor_db=competitor_db)
    return {"rejected": result.get("status") == "FAIL", "detail": result}


def automation_percentage(ladder):
    """Pure citation of profit_oracle.AUTOMATION_POTENTIAL_BY_LADDER --
    a real, disclosed, already-documented per-ladder constant (see
    that constant's own docstring for why ai_saas/b2b_systems score
    LOW: they need real hosting/billing/support infra this factory
    doesn't have yet, while automation_tools/kdp_books already run
    end-to-end on the real, existing pipeline)."""
    import profit_oracle
    value = profit_oracle.AUTOMATION_POTENTIAL_BY_LADDER.get(ladder)
    if value is None:
        return {"value": "UNKNOWN", "reason": f"{ladder!r} is not a real, recognized ladder"}
    return {"value": value, "source": "profit_oracle.py::AUTOMATION_POTENTIAL_BY_LADDER (ADR-065/122)"}
