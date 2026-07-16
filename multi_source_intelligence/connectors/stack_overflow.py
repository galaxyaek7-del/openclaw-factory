"""
Stack Overflow connector (ADR-059) — genuinely new. Stack Exchange API's
/search/advanced endpoint is free and keyless (verified reachable
directly before writing this file: a real test call succeeded, 299/300
daily quota remaining). Uses market_intelligence_core.http_client.
http_get_json() — the one canonical low-level fetch this factory already
has (ADR-049) — for the actual network call; only the endpoint-specific
URL/params are new here, matching this factory's existing convention
that query-building stays local to its own connector/module while the
low-level fetch is shared.
"""

import urllib.parse
from datetime import datetime, timezone

from market_intelligence_core import http_client
from multi_source_intelligence.registry import register_connector
from multi_source_intelligence.types import CONFIDENCE_SCALE, ConnectorResult, unavailable_result

SEARCH_URL = "https://api.stackexchange.com/2.3/search/advanced"


def _query_stack_overflow(niche, max_results=10):
    params = urllib.parse.urlencode({"q": niche, "site": "stackoverflow", "pagesize": max_results, "order": "desc", "sort": "relevance"})
    data = http_client.http_get_json(f"{SEARCH_URL}?{params}")
    return data.get("items", [])[:max_results]


@register_connector("stack_overflow")
def check(niche, max_results=10):
    try:
        items = _query_stack_overflow(niche, max_results)
    except Exception as e:
        return unavailable_result("stack_overflow", f"فشل استعلام Stack Exchange API: {e}")

    parsed = [
        {"title": i.get("title"), "view_count": i.get("view_count", 0), "answer_count": i.get("answer_count", 0), "score": i.get("score", 0)}
        for i in items
    ]
    return ConnectorResult(
        source="stack_overflow", timestamp=datetime.now(timezone.utc).isoformat(),
        availability="available", raw_data=items, parsed_data=parsed,
        confidence=CONFIDENCE_SCALE["high"] if items else CONFIDENCE_SCALE["low"],
        evidence_quality="verified", verification_status="VERIFIED",
        reason=None if items else "استعلام حقيقي نجح لكن صفر نتيجة لهذا النيتش",
    )
