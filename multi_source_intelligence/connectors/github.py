"""
GitHub connector (ADR-059) — real, since ADR-042. Reuses
competitor_discovery._query_github() directly (GitHub repository search,
free/keyless up to standard rate limits) rather than a second
implementation of the same query.
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
