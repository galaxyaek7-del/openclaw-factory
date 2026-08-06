"""
Hacker News connector (ADR-059) — real, since ADR-042. Reuses
competitor_discovery._query_hn() directly (Show HN search via HN
Algolia, free/keyless) rather than a second implementation of the same
query.

Real Evidence Provider abstraction (ADR-179, 2026-08-06): same
disclosed limitation as github.py — competitor_discovery._query_hn()'s
own "never raises" contract swallows a real block before it reaches
here. Not retrofitted for the same reason (shared, load-bearing
function, other real callers depend on it never raising).
"""

from datetime import datetime, timezone

import competitor_discovery
from multi_source_intelligence.registry import register_connector
from multi_source_intelligence.types import CONFIDENCE_SCALE, ConnectorResult, unavailable_result


@register_connector("hacker_news")
def check(niche, max_results=10):
    try:
        hits = competitor_discovery._query_hn(niche, max_results)
    except Exception as e:
        return unavailable_result("hacker_news", f"فشل استعلام HN Algolia: {e}")

    parsed = [{"title": h.get("title"), "points": h.get("points", 0), "num_comments": h.get("num_comments", 0)} for h in hits]
    return ConnectorResult(
        source="hacker_news", timestamp=datetime.now(timezone.utc).isoformat(),
        availability="available", raw_data=hits, parsed_data=parsed,
        confidence=CONFIDENCE_SCALE["high"] if hits else CONFIDENCE_SCALE["low"],
        evidence_quality="verified", verification_status="VERIFIED",
        reason=None if hits else "استعلام حقيقي نجح لكن صفر نتيجة لهذا النيتش",
    )
