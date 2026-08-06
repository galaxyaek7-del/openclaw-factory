"""
Multi-Source Market Intelligence — shared types (ADR-059).
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from market_intelligence_core.types import CONFIDENCE_SCALE  # reused, not a second scale

SOURCES = (
    "amazon", "etsy", "gumroad", "product_hunt", "reddit",
    "google_trends", "hacker_news", "github", "stack_overflow", "public_search",
    "arxiv",  # Strategic Phase 3, Round 1 (2026-07-22): 11th source, real
    # Real Evidence Provider abstraction (ADR-179, 2026-08-06): the
    # founder's own named priority list included 2 sources with zero
    # real connector anywhere in this factory (RSS feeds, Public
    # reports — confirmed by direct search) and one that cannot be an
    # autonomous Python connector at all (raw web pages -- fetching them
    # requires a live browser/session, same "Claude Code checking a
    # real page during a session" limit market_evidence.py's own
    # docstring already discloses for Proof of Payment evidence).
    # Registered honestly rather than silently omitted -- every named
    # source in the priority list now has a real entry in this
    # registry, even where that entry's only honest status is
    # NOT_ARCHITECTED or MANUAL_SESSION_ONLY.
    "rss_feeds", "public_reports", "web_pages",
)

# Real Evidence Provider priority order (ADR-179, 2026-08-06) -- the
# founder's own named 10 tiers, mapped 1:1 onto this factory's real
# connector names, in the founder's own given order, never reordered to
# flatter which connectors already work. "Official APIs" (tier 1) maps
# to arxiv (this factory's one connector to an official, ToS-permitted,
# keyless government/institutional API) plus amazon/etsy/gumroad/
# public_search -- this factory's other officially-sourced (manual
# report / real evidence collector) connectors not named individually
# in the founder's own list, kept rather than silently dropped.
EVIDENCE_SOURCE_PRIORITY = (
    "arxiv", "amazon", "etsy", "gumroad", "public_search",  # 1. Official APIs
    "rss_feeds",                                            # 2. RSS feeds (NOT_ARCHITECTED)
    "public_reports",                                       # 3. Public reports (NOT_ARCHITECTED)
    "google_trends",                                        # 4. Google Trends (built, not activated)
    "github",                                               # 5. GitHub activity (real, keyless)
    "product_hunt",                                         # 6. Product Hunt (needs official contact)
    "reddit",                                                # 7. Reddit (needs API credentials)
    "hacker_news",                                          # 8. Hacker News (real, keyless)
    "stack_overflow",                                       # 9. Stack Overflow (real, keyless)
    "web_pages",                                            # 10. Web pages (Claude-session-only, last resort)
)


@dataclass
class ConnectorResult:
    source: str
    timestamp: str
    availability: str  # "available" | "unavailable"
    raw_data: Any
    parsed_data: Any
    confidence: int  # 0 or CONFIDENCE_SCALE["high"/"medium"/"low"]
    evidence_quality: str  # "verified" | "unknown"
    verification_status: str  # "VERIFIED" | "UNKNOWN" | "BLOCKED" | "NOT_ARCHITECTED"
    reason: Optional[str] = None  # populated whenever availability/verification is not fully positive
    status_code: Optional[int] = None  # real HTTP status code, populated only for BLOCKED

    def to_dict(self):
        return {
            "source": self.source,
            "timestamp": self.timestamp,
            "availability": self.availability,
            "raw_data": self.raw_data,
            "parsed_data": self.parsed_data,
            "confidence": self.confidence,
            "evidence_quality": self.evidence_quality,
            "verification_status": self.verification_status,
            "reason": self.reason,
            "status_code": self.status_code,
        }


def unavailable_result(source, reason):
    """Shared constructor for the "honestly unavailable" shape every
    connector without a real, working data path returns — a construction
    convenience (like real_market_evidence's _unknown() helper), not
    shared business logic, so each connector remains independent."""
    from datetime import datetime, timezone
    return ConnectorResult(
        source=source, timestamp=datetime.now(timezone.utc).isoformat(), availability="unavailable",
        raw_data=None, parsed_data=None, confidence=0, evidence_quality="unknown",
        verification_status="UNKNOWN", reason=reason,
    )


def not_architected_result(source, reason):
    """Real Evidence Provider abstraction (ADR-179, 2026-08-06): a
    source this factory has never built ANY connector for (RSS feeds,
    Public reports) -- distinct from `unavailable_result()`, which means
    a real connector exists but has no credentials/data today. Never
    conflated: a founder reading `verification_status` should be able to
    tell "not built yet" from "built, currently blocked/empty" at a
    glance."""
    from datetime import datetime, timezone
    return ConnectorResult(
        source=source, timestamp=datetime.now(timezone.utc).isoformat(), availability="unavailable",
        raw_data=None, parsed_data=None, confidence=0, evidence_quality="unknown",
        verification_status="NOT_ARCHITECTED", reason=reason,
    )


def blocked_result(source, reason, status_code=None):
    """Real Evidence Provider abstraction (ADR-179, 2026-08-06): a
    source that exists and was actually reached, but actively refused
    the request (HTTP 401/403/429, or any other explicit block) --
    distinct from `unavailable_result()` (no credentials/connector) and
    from a real query that succeeded with zero results. Per the
    founder's directive: recorded honestly, never treated as a reason
    to stop evaluating -- every real caller of this factory's
    evaluation pipeline already treats a `blocked_result()` exactly
    like any other non-VERIFIED result (reduces confidence, never
    raises, never halts)."""
    from datetime import datetime, timezone
    return ConnectorResult(
        source=source, timestamp=datetime.now(timezone.utc).isoformat(), availability="unavailable",
        raw_data=None, parsed_data=None, confidence=0, evidence_quality="unknown",
        verification_status="BLOCKED", reason=reason, status_code=status_code,
    )
