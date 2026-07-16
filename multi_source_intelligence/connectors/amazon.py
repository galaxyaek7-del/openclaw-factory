"""
Amazon connector (ADR-059) — reuses real_market_evidence.evidence_collector
(ADR-058) directly, the one real Amazon evidence mechanism this factory
has: niche_validator_v2.py's deliberately offline, manual saved-report
lookup. No live Amazon scraping is performed or added here — that would
violate Amazon's Terms of Service, a real boundary already documented in
ADR-058, not crossed here either.
"""

from datetime import datetime, timezone

from multi_source_intelligence.registry import register_connector
from multi_source_intelligence.types import CONFIDENCE_SCALE, ConnectorResult, unavailable_result
from real_market_evidence import evidence_collector


@register_connector("amazon")
def check(niche, max_results=10):
    evidence = evidence_collector.collect_evidence(niche)
    real_metrics = {m: e.to_dict() for m, e in evidence.items() if e.confidence > 0}

    if not real_metrics:
        return unavailable_result(
            "amazon",
            "لا تقرير Amazon محفوظ يدوياً لهذا النيتش (niche_validator_v2.py) — لا استخراج آلي حي من Amazon يُبنى هنا (يخالف شروط الاستخدام)",
        )

    return ConnectorResult(
        source="amazon", timestamp=datetime.now(timezone.utc).isoformat(), availability="available",
        raw_data={m: e.raw_value for m, e in evidence.items() if e.confidence > 0},
        parsed_data=real_metrics, confidence=CONFIDENCE_SCALE["high"],
        evidence_quality="verified", verification_status="VERIFIED", reason=None,
    )
