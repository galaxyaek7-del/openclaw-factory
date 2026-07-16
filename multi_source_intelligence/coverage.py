"""
Evidence Coverage Score (ADR-059) — requirement 6: which sources were
checked, which succeeded, which failed (raised an exception a connector
itself didn't catch), which remain honestly unknown/unavailable.

Every registered connector is called, in isolation (a try/except per
connector — one source's bug can never take down another, and never
breaks the factory, per requirement 4).
"""

from datetime import datetime, timezone

from multi_source_intelligence import connectors  # noqa: F401 — triggers auto-registration
from multi_source_intelligence.registry import get_connectors
from multi_source_intelligence.types import SOURCES, unavailable_result


def evidence_coverage_score(niche, max_results=10):
    checked, succeeded, failed, unknown = [], [], [], []
    results = {}
    connectors_map = get_connectors()

    for source in SOURCES:
        fn = connectors_map.get(source)
        checked.append(source)

        if fn is None:
            result = unavailable_result(source, "لا مُوصِّل مُسجَّل لهذا المصدر")
            results[source] = result
            unknown.append(source)
            continue

        try:
            result = fn(niche, max_results)
        except Exception as e:
            result = unavailable_result(source, f"المُوصِّل نفسه أطلق استثناءً غير مُمسوك: {e}")
            results[source] = result
            failed.append(source)
            continue

        results[source] = result
        if result.availability == "available" and result.verification_status == "VERIFIED":
            succeeded.append(source)
        else:
            unknown.append(source)

    return {
        "niche": niche,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checked": checked,
        "succeeded": succeeded,
        "failed": failed,
        "unknown": unknown,
        "coverage_pct": round(100 * len(succeeded) / len(SOURCES), 1),
        "results": {s: r.to_dict() for s, r in results.items()},
    }
