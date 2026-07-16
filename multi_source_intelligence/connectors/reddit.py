"""
Reddit connector (ADR-059) — honestly unavailable. Same real reason
already documented since ADR-042/043 (competitor_discovery.py's
UNKNOWN_METRICS, market_intelligence_engine.py's unknown_sources):
Reddit's API requires registered app credentials this factory does not
have in .env (confirmed: only GROQ_KEY present).
"""

from multi_source_intelligence.registry import register_connector
from multi_source_intelligence.types import unavailable_result


@register_connector("reddit")
def check(niche, max_results=10):
    return unavailable_result("reddit", "لا بيانات اعتماد Reddit API متوفرة (BLOCKERS.md) — لا وصول اليوم")
