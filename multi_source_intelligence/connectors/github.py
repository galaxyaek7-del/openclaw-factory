"""
GitHub connector (ADR-059) — real, since ADR-042. Reuses
competitor_discovery._query_github() directly (GitHub repository search,
free/keyless up to standard rate limits) rather than a second
implementation of the same query.

Real Evidence Provider abstraction (ADR-179, 2026-08-06): unlike
stack_overflow.py/arxiv.py, this connector cannot distinguish a real
HTTP 403/429 block from any other failure — competitor_discovery.
_query_github()'s own "never raises" contract (real, tested, relied on
by its other callers, e.g. the real Competitor Discovery report)
deliberately swallows every exception, including a real block, before
it would ever reach here. Disclosed honestly rather than silently
touching that shared, load-bearing function's contract for every other
caller just to gain blocked-detection on this one path.
"""

from datetime import datetime, timezone

import competitor_discovery
from multi_source_intelligence.registry import register_connector
from multi_source_intelligence.types import CONFIDENCE_SCALE, ConnectorResult, unavailable_result


@register_connector("github")
def check(niche, max_results=10):
    try:
        hits = competitor_discovery._query_github(niche, max_results)
    except Exception as e:
        return unavailable_result("github", f"فشل استعلام GitHub Search: {e}")

    parsed = [{"full_name": h.get("full_name"), "stars": h.get("stargazers_count", 0), "created_at": h.get("created_at")} for h in hits]
    return ConnectorResult(
        source="github", timestamp=datetime.now(timezone.utc).isoformat(),
        availability="available", raw_data=hits, parsed_data=parsed,
        confidence=CONFIDENCE_SCALE["high"] if hits else CONFIDENCE_SCALE["low"],
        evidence_quality="verified", verification_status="VERIFIED",
        reason=None if hits else "استعلام حقيقي نجح لكن صفر نتيجة لهذا النيتش",
    )
