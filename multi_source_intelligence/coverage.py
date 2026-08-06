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
from multi_source_intelligence.types import CONFIDENCE_SCALE, EVIDENCE_SOURCE_PRIORITY, SOURCES, unavailable_result


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


def _evidence_item_count(result):
    """Real, mechanical count of actual evidence items in a VERIFIED
    result's parsed_data — never a fabricated positive count for an
    empty/unavailable result."""
    if result.verification_status != "VERIFIED":
        return 0
    data = result.parsed_data
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        return len(data) if data else 0
    return 1 if data else 0


def prioritized_evidence_summary(niche, max_results=10):
    """Real Evidence Provider abstraction (ADR-179, 2026-08-06) — the
    founder's directive: query every real evidence source in the
    founder's own named priority order (EVIDENCE_SOURCE_PRIORITY), never
    stop on one source being blocked/unavailable, and report exactly 4
    fields per opportunity: confidence, evidence_count,
    verification_status, missing_evidence.

    Every connector call is wrapped in its own try/except (on top of
    each connector's own internal handling) — a genuinely unexpected
    exception from ANY source, including one this factory has not yet
    seen, still cannot halt evaluation of the remaining sources. This is
    the literal, tested guarantee behind "never terminate evaluation."

    `confidence` only ever rises when a source is actually VERIFIED with
    real data — a BLOCKED or NOT_ARCHITECTED source can only ever lower
    it (by simply not contributing), exactly matching "only reduce
    confidence" from the directive; nothing here ever raises confidence
    based on a source being merely attempted."""
    connectors_map = get_connectors()
    per_source = {}
    verified_sources, blocked_sources, missing_evidence = [], [], []
    total_evidence_count = 0
    confidence_values = []

    for source in EVIDENCE_SOURCE_PRIORITY:
        fn = connectors_map.get(source)
        if fn is None:
            result = unavailable_result(source, "لا مُوصِّل مُسجَّل لهذا المصدر")
        else:
            try:
                result = fn(niche, max_results)
            except Exception as e:
                # Real Evidence Provider guarantee: even a connector bug
                # this factory has never seen before is caught here and
                # never propagates -- evaluation of every remaining
                # source in the priority list still proceeds.
                result = unavailable_result(source, f"المُوصِّل نفسه أطلق استثناءً غير مُمسوك: {e}")

        per_source[source] = result.to_dict()

        if result.verification_status == "VERIFIED":
            verified_sources.append(source)
            total_evidence_count += _evidence_item_count(result)
            confidence_values.append(result.confidence)
        else:
            missing_evidence.append({
                "source": source, "verification_status": result.verification_status,
                "reason": result.reason,
            })
            if result.verification_status == "BLOCKED":
                blocked_sources.append(source)

    if verified_sources:
        overall_status = "VERIFIED"
        confidence = round(sum(confidence_values) / len(confidence_values), 1)
    elif blocked_sources:
        overall_status = "BLOCKED"
        confidence = 0
    else:
        overall_status = "UNVERIFIED"
        confidence = 0

    return {
        "niche": niche,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "confidence": confidence,
        "evidence_count": total_evidence_count,
        "verification_status": overall_status,
        "missing_evidence": missing_evidence,
        "verified_sources": verified_sources,
        "blocked_sources": blocked_sources,
        "priority_order_used": list(EVIDENCE_SOURCE_PRIORITY),
        "sources": per_source,
    }
