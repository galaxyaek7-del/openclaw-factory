"""
Decision Engine — shared types (ADR-050).
"""

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

STATUSES = ("ACCEPTED", "REJECTED", "DEFERRED")


def make_decision_id(niche, tier, analyzed_at):
    """Deterministic — same (niche, tier, analyzed_at) always produces the
    same ID. Part of what makes a decision reproducible: its identity
    itself is derived from its own real inputs, not a random UUID."""
    raw = f"{niche}|{tier}|{analyzed_at}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


@dataclass
class Decision:
    decision_id: str
    niche: str
    tier: str
    decided_at: str
    status: str  # one of STATUSES
    ai_ceo_decision: str  # BUILD/IMPROVE/WAIT/REJECT/PIVOT (market_intelligence_core's own verdict, unchanged) — "N/A" for the fast ladder-gate path below, which runs no live AI-CEO evidence gathering
    opportunity_score: Optional[float]  # profit_oracle.opportunity_score()'s tier-aware composite (ADR-026), OR profit_oracle.ladder_opportunity_score()'s ladder_score (ADR-066) when decision_path=="ladder_fast_gate" — same field, same 0-100 scale, so ranking.py's sort stays meaningful across both; which one produced it is always in decision_path, never ambiguous
    opportunity_score_accepted: Optional[bool]
    reasoning: List[str]  # explicit, human-readable evidence — never a bare status with no citation
    evaluation_snapshot: Dict[str, Any]  # the FULL evaluate_opportunity() output — reproducibility
    external_signal: Optional[Dict[str, Any]] = None
    # ADR-076 (Decision Surface Reconciliation, 2026-07-18): both fields
    # additive with defaults that preserve every existing historical
    # record's real meaning unchanged — every decision recorded before
    # these fields existed came from the full AI-CEO evaluation path
    # against no particular ladder rank, which is exactly what these
    # defaults say.
    ladder: Optional[str] = None  # Strategic Production Priority Ladder rank (MASTER_CHARTER.md §2), when known
    decision_path: str = "ai_ceo_full_evaluation"  # "ai_ceo_full_evaluation" (engine.evaluate_and_decide(), live evidence gathering) or "ladder_fast_gate" (engine.record_ladder_decision(), no live evidence gathering — market_hunter.py's per-tick discovery path)
    # Packaging Architecture Plan §1 (Phase A, 2026-07-18): orthogonal to
    # `ladder` — `ladder` answers "how much should we prioritize/pay for
    # this," `product_family` answers "what kind of file do we build."
    # Additive, default None — every decision recorded before this field
    # existed keeps its real meaning (no family was ever decided for it).
    product_family: Optional[str] = None

    def to_dict(self):
        return {
            "decision_id": self.decision_id,
            "niche": self.niche,
            "tier": self.tier,
            "decided_at": self.decided_at,
            "status": self.status,
            "ai_ceo_decision": self.ai_ceo_decision,
            "opportunity_score": self.opportunity_score,
            "opportunity_score_accepted": self.opportunity_score_accepted,
            "reasoning": self.reasoning,
            "evaluation_snapshot": self.evaluation_snapshot,
            "external_signal": self.external_signal,
            "ladder": self.ladder,
            "decision_path": self.decision_path,
            "product_family": self.product_family,
        }


@dataclass
class Outcome:
    outcome_id: str
    decision_id: Optional[str]  # None when a real sale could not be confidently matched to any decision
    niche: Optional[str]
    recorded_at: str
    matched: bool
    match_method: str  # e.g. "niche_substring_in_product_text", "unmatched"
    raw_sale_event: Dict[str, Any]  # verbatim from data/sales_ledger.jsonl — never reshaped/guessed

    def to_dict(self):
        return {
            "outcome_id": self.outcome_id,
            "decision_id": self.decision_id,
            "niche": self.niche,
            "recorded_at": self.recorded_at,
            "matched": self.matched,
            "match_method": self.match_method,
            "raw_sale_event": self.raw_sale_event,
        }
