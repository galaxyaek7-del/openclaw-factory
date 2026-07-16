"""
Market Intelligence Core — shared types (ADR-049).

Score is the one contract every scoring module returns (requirement:
"Every score must expose raw_data, normalized_score, confidence,
explanation"), so the pipeline and every caller can treat all scoring
dimensions uniformly regardless of which real data source backs them.

CONFIDENCE_SCALE is the single numeric anchor for confidence used
factory-wide (high=80, medium=55, low=30) — this generalizes the fix
from the 2026-07-15 self-audit (market_intelligence_engine.
ai_ceo_decision's PAIN_CONFIDENCE_SCALE bug, where "medium" was
wrongly mapped to 100) into one canonical place instead of letting each
module invent its own scale.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

CONFIDENCE_SCALE = {"high": 80, "medium": 55, "low": 30}


@dataclass
class Score:
    dimension: str
    raw_data: Dict[str, Any]
    # 0-100, or None when genuinely not computable (DISCOVERY) — never a guessed number standing in for real evidence.
    normalized_score: Optional[float]
    confidence: int  # 0-100, see CONFIDENCE_SCALE
    explanation: str

    def to_dict(self):
        return {
            "dimension": self.dimension,
            "raw_data": self.raw_data,
            "normalized_score": self.normalized_score,
            "confidence": self.confidence,
            "explanation": self.explanation,
        }


@dataclass
class EvaluationContext:
    """Everything a scorer might need. Every scorer takes exactly one of
    these and returns exactly one Score — no scorer reaches into another
    scorer's internals, so a new scoring dimension can be added without
    touching any of the existing ones (see scoring/__init__.py's
    auto-discovery and registry.py's plugin registration).

    `analysis`: the already-computed market_intelligence_engine.
    analyze_opportunity() result, when core.evaluate_opportunity() has
    already run it (it always has, by the time the pipeline runs) — real
    network-fetched data (competitors, customer pain, demand pattern)
    lives here so scorers reuse it instead of re-fetching."""
    niche: str
    tier: str = "tier4"
    external_signal: Optional[Dict[str, Any]] = None
    max_results: int = 10
    now: Any = None
    analysis: Optional[Dict[str, Any]] = None
