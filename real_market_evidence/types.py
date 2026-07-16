"""
Real Market Evidence — shared types (ADR-058).
"""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class Evidence:
    metric: str
    source: str  # "niche_validator_v2 saved report" or "unavailable"
    timestamp: Optional[str]  # when the underlying saved report was generated, if real
    confidence: int  # 0 (Unknown) or CONFIDENCE_SCALE["high"] (80) — real data read from an actual saved report
    raw_value: Any
    normalized_value: Optional[float]
    explanation: str

    def to_dict(self):
        return {
            "metric": self.metric,
            "source": self.source,
            "timestamp": self.timestamp,
            "confidence": self.confidence,
            "raw_value": self.raw_value,
            "normalized_value": self.normalized_value,
            "explanation": self.explanation,
        }


METRICS = (
    "amazon_search_result_count",
    "best_seller_rank",
    "competing_listings_count",
    "pricing_distribution",
    "review_count_distribution",
    "category_saturation",
    "marketplace_age",
    "update_frequency",
    "seller_concentration",
    "revenue_indicators",
)
