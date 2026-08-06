"""
Public reports connector (Real Evidence Provider abstraction, ADR-179,
2026-08-06) — honestly not architected. "Public reports" (industry
research, government/trade-body statistics, market-sizing PDFs) has no
real connector anywhere in this factory — confirmed by direct search.
Registered here so the founder's own named priority-3 evidence source
is complete and real in this registry, not just documented in prose.
Same disclosed-gap discipline as rss_feeds.py.
"""

from multi_source_intelligence.registry import register_connector
from multi_source_intelligence.types import not_architected_result


@register_connector("public_reports")
def check(niche, max_results=10):
    return not_architected_result(
        "public_reports",
        "لا مُوصِّل تقارير عامة/صناعية حقيقي مبني في هذا المصنع بعد — لا مصدر تقارير سوق مسجَّل",
    )
