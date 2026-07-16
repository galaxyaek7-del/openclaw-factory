"""
Public search engines connector (ADR-059) — honestly unavailable. Real
general-purpose search (Google Custom Search API, Bing Search API) both
require a paid, registered API key; none exists in .env (confirmed: only
GROQ_KEY present). A free alternative was considered (DuckDuckGo's
Instant Answer API) and deliberately not used: it returns infobox/
definition-style data, not search-result counts or listings — using it
here would produce technically-real-but-practically-meaningless output
dressed up as market evidence, which is its own kind of fabrication.
Honest "unavailable" is the correct answer until a real, fit-for-purpose
search API is actually provisioned.
"""

from multi_source_intelligence.registry import register_connector
from multi_source_intelligence.types import unavailable_result


@register_connector("public_search")
def check(niche, max_results=10):
    return unavailable_result(
        "public_search",
        "لا مفتاح API بحث ويب حقيقي (Google Custom Search/Bing) في .env — البدائل المجانية (DuckDuckGo Instant Answer) لا تُنتج بيانات سوق ذات معنى",
    )
