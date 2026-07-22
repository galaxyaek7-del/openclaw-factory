"""
arXiv connector (Strategic Phase 3, Round 1, 2026-07-22) — genuinely new.
arXiv's official API (export.arxiv.org/api/query) is free and keyless,
and its terms of use explicitly permit this kind of automated querying
(https://arxiv.org/help/api/tou) — unlike Reddit/Product Hunt, no business
contact or paid tier is required. It returns Atom XML, not JSON, so this
uses market_intelligence_core.http_client.http_get_text() (the raw-fetch
primitive) plus stdlib xml.etree.ElementTree for parsing — no new
dependency. Closes Strategic Phase 3's named "research papers" source.
"""

import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from market_intelligence_core import http_client
from multi_source_intelligence.registry import register_connector
from multi_source_intelligence.types import CONFIDENCE_SCALE, ConnectorResult, unavailable_result

SEARCH_URL = "http://export.arxiv.org/api/query"
ATOM_NS = "{http://www.w3.org/2005/Atom}"


def _query_arxiv(niche, max_results=10):
    params = urllib.parse.urlencode({
        "search_query": f"all:{niche}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    })
    xml_text = http_client.http_get_text(f"{SEARCH_URL}?{params}")
    root = ET.fromstring(xml_text)

    entries = []
    for entry in root.findall(f"{ATOM_NS}entry"):
        title_el = entry.find(f"{ATOM_NS}title")
        summary_el = entry.find(f"{ATOM_NS}summary")
        published_el = entry.find(f"{ATOM_NS}published")
        id_el = entry.find(f"{ATOM_NS}id")
        entries.append({
            "title": title_el.text.strip() if title_el is not None and title_el.text else None,
            "summary": summary_el.text.strip() if summary_el is not None and summary_el.text else None,
            "published": published_el.text if published_el is not None else None,
            "url": id_el.text if id_el is not None else None,
        })
    return entries


@register_connector("arxiv")
def check(niche, max_results=10):
    try:
        entries = _query_arxiv(niche, max_results)
    except Exception as e:
        return unavailable_result("arxiv", f"فشل استعلام arXiv API: {e}")

    return ConnectorResult(
        source="arxiv", timestamp=datetime.now(timezone.utc).isoformat(),
        availability="available", raw_data=entries, parsed_data=entries,
        confidence=CONFIDENCE_SCALE["high"] if entries else CONFIDENCE_SCALE["low"],
        evidence_quality="verified", verification_status="VERIFIED",
        reason=None if entries else "استعلام حقيقي نجح لكن صفر نتيجة لهذا النيتش",
    )
