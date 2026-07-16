"""
Product Hunt connector (ADR-059) — honestly unavailable. Same real
reason already documented in this factory since ADR-042/043
(competitor_discovery.py's UNKNOWN_METRICS, market_intelligence_engine.py's
unknown_sources): Product Hunt requires official prior contact before
commercial API use (GOLDEN_HUNTER_V2_STRATEGY.md §2) — not a free/keyless
API like HN/GitHub/Stack Exchange.
"""

from multi_source_intelligence.registry import register_connector
from multi_source_intelligence.types import unavailable_result


@register_connector("product_hunt")
def check(niche, max_results=10):
    return unavailable_result(
        "product_hunt",
        "يحتاج تواصلاً رسمياً مسبقاً مع Product Hunt قبل استخدام تجاري (GOLDEN_HUNTER_V2_STRATEGY.md §2) — لا وصول اليوم",
    )
