"""
Web pages connector (Real Evidence Provider abstraction, ADR-179,
2026-08-06) — priority tier 10, last resort. Cannot be an autonomous
Python connector: loading an arbitrary commercial web page live
requires a real browser/session (the exact "Claude Code checking a
real public page during a session" limit market_evidence.py's own
docstring already discloses), not a background HTTP call this factory
can run unattended. Never fabricated as a live scraper.

What IS real: this connector reads multi_source_intelligence.
manual_verification's real ledger of attempts a human or Claude Code
actually made during a session. A niche with no recorded attempt is
honestly NOT_ARCHITECTED (never tried); one with a recorded BLOCKED
attempt is honestly BLOCKED (tried, actively refused — HTTP 403/429);
one with a recorded VERIFIED attempt is honestly VERIFIED (a real,
quoted page was actually read).
"""

from multi_source_intelligence import manual_verification
from multi_source_intelligence.registry import register_connector
from multi_source_intelligence.types import CONFIDENCE_SCALE, ConnectorResult, blocked_result, not_architected_result


@register_connector("web_pages")
def check(niche, max_results=10):
    attempts = manual_verification.get_verification_attempts(niche)
    if not attempts:
        return not_architected_result(
            "web_pages",
            "لا محاولة تحقق يدوية حقيقية مسجَّلة لهذا النيتش بعد — هذا مصدر بشري/Claude فقط، لا استخراج آلي حي",
        )

    verified = [a for a in attempts if a["status"] == "VERIFIED"]
    if verified:
        return ConnectorResult(
            source="web_pages", timestamp=attempts[-1]["recorded_at"], availability="available",
            raw_data=attempts, parsed_data=verified,
            confidence=CONFIDENCE_SCALE["medium"],  # a single-page manual read, never treated as high as a real API
            evidence_quality="verified", verification_status="VERIFIED",
            reason=f"{len(verified)} صفحة حقيقية تم التحقق منها يدوياً خلال جلسة",
        )

    blocked = [a for a in attempts if a["status"] == "BLOCKED"]
    urls = ", ".join(a["source_url"] for a in blocked)
    return blocked_result(
        "web_pages",
        f"{len(blocked)} محاولة تحقق حقيقية حُظِرت ({urls}) — لا يُوقِف التقييم، يُخفِّض الثقة فقط",
        status_code=blocked[-1].get("status_code"),
    )
