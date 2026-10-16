"""Galaxy Forge — Unit Economics Engine (P0) - Upgraded (ADR-UE-ENGINE-V2)
Provides advisory, read-only unit economic analysis for opportunities.
Enforces REAL/TEST/MOCK/UNKNOWN classification discipline.
Strictly read-only: never modifies financial ledgers.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import uuid
import math

# Canonical classification
REAL = "REAL"
TEST = "TEST"
MOCK = "MOCK"
UNKNOWN = "UNKNOWN"

VERDICT_PROCEED = "PROCEED"
VERDICT_HOLD = "HOLD"
VERDICT_KILL = "KILL"
VERDICT_UNKNOWN = "UNKNOWN"

CONFIDENCE_HIGH = "HIGH"
CONFIDENCE_MEDIUM = "MEDIUM"
CONFIDENCE_LOW = "LOW"
CONFIDENCE_UNKNOWN = "UNKNOWN"

class UnitEconomicsEngine:
    def __init__(self):
        pass

    def _safe_div(self, n, d):
        return n / d if d != 0 else None

    def evaluate(self, opportunity_id: str, price: float, costs: Dict[str, float], 
                 evidence_sources: List[Dict[str, Any]], units: int = 1) -> Dict[str, Any]:
        """
        Evaluates economics for an opportunity with full audit trail.
        evidence_sources: [{'source': str, 'reality_state': str, 'confidence': str}]
        """
        revenue = price * units
        variable_cost = sum(costs.values())
        profit = revenue - variable_cost
        margin = self._safe_div(profit, revenue) if revenue != 0 else None
        
        # Aggregate confidence
        confidence = self._get_economic_confidence([e['confidence'] for e in evidence_sources])
        
        # Assess verdict
        verdict = self.assess_verdict(margin, confidence, [])
        
        return {
            "opportunity_id": opportunity_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "inputs": {
                "price": price,
                "costs": costs,
                "units": units
            },
            "analysis": {
                "revenue": revenue,
                "variable_costs": variable_cost,
                "contribution_profit": profit,
                "contribution_margin": margin,
            },
            "evidence": evidence_sources,
            "confidence": confidence,
            "verdict": verdict
        }

    def assess_verdict(self, margin: Optional[float], confidence: str, risks: List[str]) -> str:
        if margin is None or confidence == CONFIDENCE_UNKNOWN:
            return VERDICT_UNKNOWN
        if margin < 0.2 and confidence == CONFIDENCE_HIGH:
            return VERDICT_KILL
        if margin > 0.4:
            return VERDICT_PROCEED
        return VERDICT_HOLD

    def _get_economic_confidence(self, confidences: List[str]) -> str:
        if CONFIDENCE_HIGH in confidences: return CONFIDENCE_HIGH
        if CONFIDENCE_MEDIUM in confidences: return CONFIDENCE_MEDIUM
        return CONFIDENCE_UNKNOWN

# Singleton
unit_economics = UnitEconomicsEngine()

# Backwards compatibility wrappers
def calculate_economics(price: float, costs: Dict[str, float], units: int = 1, reality_state: str = UNKNOWN) -> Dict[str, Any]:
    return {"contribution_margin": unit_economics._safe_div(price * units - sum(costs.values()), price * units), "reality_state": reality_state}

def assess_verdict(margin: Optional[float], confidence: str, risks: List[str]) -> str:
    return unit_economics.assess_verdict(margin, confidence, risks)

def get_economic_confidence(data_sources: List[str]) -> str:
    # Map sources to confidence levels
    confidences = []
    for source in data_sources:
        if source == 'REAL': confidences.append(CONFIDENCE_HIGH)
        elif source == 'ESTIMATE': confidences.append(CONFIDENCE_MEDIUM)
        else: confidences.append(CONFIDENCE_UNKNOWN)
    return unit_economics._get_economic_confidence(confidences)


# --- Future-ready measures (ADR-UE-GAP-CLOSURE) ---------------------------------
# Each returns UNKNOWN when a required REAL input is missing. Estimated/partial
# inputs are NEVER silently promoted to an actual value.

def cac(total_acquisition_cost, customers_acquired):
    """Customer Acquisition Cost. UNKNOWN if inputs missing or no customers."""
    if total_acquisition_cost is None or customers_acquired is None or customers_acquired == 0:
        return UNKNOWN
    return total_acquisition_cost / customers_acquired


def payback_period(cac_value, gross_margin_per_period):
    """Periods to recover CAC. UNKNOWN if inputs missing or margin is zero/unknown."""
    if cac_value in (None, UNKNOWN) or gross_margin_per_period in (None, UNKNOWN):
        return UNKNOWN
    if gross_margin_per_period == 0:
        return UNKNOWN
    return cac_value / gross_margin_per_period


def recurring_potential_score(is_recurring):
    """REAL classification only. UNKNOWN if not yet known."""
    if is_recurring is None:
        return UNKNOWN
    return "RECURRING" if is_recurring else "ONE_TIME"


def price_sensitivity_band(price_low, price_high, demand_low, demand_high):
    """Direction-only elasticity signal. UNKNOWN if any input missing (no fabricated magnitude)."""
    if None in (price_low, price_high, demand_low, demand_high):
        return UNKNOWN
    if price_high > price_low and demand_low > demand_high:
        return "NEGATIVE_ELASTIC"
    if price_high > price_low and demand_high >= demand_low:
        return "INELASTIC_OR_UNPROVEN"
    return UNKNOWN
