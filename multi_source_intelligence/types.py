"""
Multi-Source Market Intelligence — shared types (ADR-059).
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from market_intelligence_core.types import CONFIDENCE_SCALE  # reused, not a second scale

SOURCES = (
    "amazon", "etsy", "gumroad", "product_hunt", "reddit",
    "google_trends", "hacker_news", "github", "stack_overflow", "public_search",
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
    verification_status: str  # "VERIFIED" | "UNKNOWN"
    reason: Optional[str] = None  # populated whenever availability/verification is not fully positive

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
