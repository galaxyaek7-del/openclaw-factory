"""
Google Trends connector (ADR-059) — honestly unavailable. Same real
reason already documented since this factory's earliest sessions
(FACTORY_STATUS.md, competitor_discovery.py's UNKNOWN_METRICS): the n8n
"Sensing Engine" workflow for Trends exists but is not activated — that
requires a manual n8n login step (BLOCKERS.md #1), not a code change.
"""

from multi_source_intelligence.registry import register_connector
from multi_source_intelligence.types import unavailable_result


@register_connector("google_trends")
def check(niche, max_results=10):
    return unavailable_result(
        "google_trends",
        "لا اتصال Trends حي — n8n Sensing Engine مبني لكن غير مُفعَّل (يحتاج تسجيل دخول يدوي، BLOCKERS.md #1)",
    )
