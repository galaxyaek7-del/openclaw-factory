"""Galaxy Forge — COMMERCIAL GOVERNANCE.

Implements the founder's POST-FIRST-SALE GOVERNANCE & REPEATABILITY GATE.

Key principles:
  - REVENUE OVER ACTIVITY
  - EVIDENCE OVER ASSUMPTION
  - REPEATABILITY OVER ONE-OFF SUCCESS
  - ECONOMICS OVER VANITY METRICS
  - NO CLAIM WITHOUT EVIDENCE
  - NO MASS EXPANSION WITHOUT REPEATABILITY

This module adds:
  A) FINANCIAL TRUTH — verified accounting, never "100% profit"
  B) REPEATABILITY GATE — can the system generate another customer?
  C) GF-001 MONITORING — protect the working revenue loop
  D) SCALE LEVELS — enforce LEVEL 0-8 progression
  E) PORTFOLIO CONTROL — SCALE/TEST/IMPROVE/HOLD/KILL
  F) GOVERNANCE DASHBOARD — the commercial control center

Honesty contract: never fabricate revenue, conversion, or evidence.
Every metric must come from real observed data or be reported as UNKNOWN.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

_FACTORY_ROOT = Path(__file__).resolve().parent
GOVERNANCE_PATH = _FACTORY_ROOT / "data" / "commercial_governance.json"
FINANCE_PATH = _FACTORY_ROOT / "finance_data.json"
REALITY_PATH = _FACTORY_ROOT / "config" / "reality.json"
TRANSACTIONS_PATH = _FACTORY_ROOT / "data" / "verified_transactions.jsonl"
GF001_METRICS_PATH = _FACTORY_ROOT / "data" / "gf001_metrics.json"


class ScaleLevel(int, Enum):
    """The 9 scale levels from the directive."""
    NO_EVIDENCE = 0
    FIRST_TRANSACTION = 1
    MULTIPLE_TRANSACTIONS = 2
    REPEATABLE_ACQUISITION = 3
    POSITIVE_ECONOMICS = 4
    PRODUCT_FAMILY = 5
    PREDICTABLE_REVENUE = 6
    RECURRING_REVENUE = 7
    PORTFOLIO_SCALE = 8


class PortfolioState(str, Enum):
    """Asset portfolio states from the directive."""
    SCALE = "SCALE"
    TEST = "TEST"
    IMPROVE = "IMPROVE"
    HOLD = "HOLD"
    KILL = "KILL"


SCALE_LEVEL_DEFINITIONS = {
    0: "NO_EVIDENCE — No commercial evidence",
    1: "FIRST_TRANSACTION — First verified transaction",
    2: "MULTIPLE_TRANSACTIONS — Multiple verified transactions",
    3: "REPEATABLE_ACQUISITION — System can generate customers on demand",
    4: "POSITIVE_ECONOMICS — Contribution margin positive and verified",
    5: "PRODUCT_FAMILY — Validated bundle/complementary offers",
    6: "PREDICTABLE_REVENUE — Revenue is forecastable from evidence",
    7: "RECURRING_REVENUE — Validated subscription/membership model",
    8: "PORTFOLIO_SCALE — Multiple products, multiple channels, scaling",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> Any:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# A) FINANCIAL TRUTH — verified accounting
# ---------------------------------------------------------------------------

def record_transaction(transaction_id: str, product_id: str, gross_amount: float,
                       currency: str = "USD", payment_processor: str = "unknown",
                       payment_fees: float = 0.0, direct_costs: float = 0.0,
                       infrastructure_cost: float = 0.0, support_cost: float = 0.0,
                       acquisition_cost: float = 0.0, refund_status: str = "none",
                       delivery_status: str = "delivered",
                       customer_record: Optional[Dict] = None,
                       evidence_source: str = "unknown") -> Dict[str, Any]:
    """Record a verified transaction with full financial breakdown.

    This is the ONLY way to record revenue. Every field must come from
    real observed data, never estimated.
    """
    net_receipts = gross_amount - payment_fees
    contribution = net_receipts - direct_costs - infrastructure_cost - support_cost - acquisition_cost
    net_profit = contribution  # Same as contribution for digital products (no COGS)

    record = {
        "transaction_id": transaction_id,
        "product_id": product_id,
        "gross_revenue": gross_amount,
        "currency": currency,
        "payment_processor": payment_processor,
        "payment_fees": payment_fees,
        "net_receipts": net_receipts,
        "direct_costs": direct_costs,
        "infrastructure_cost": infrastructure_cost,
        "support_cost": support_cost,
        "acquisition_cost": acquisition_cost,
        "contribution": contribution,
        "net_profit": net_profit,
        "refund_status": refund_status,
        "delivery_status": delivery_status,
        "customer_record": customer_record or {},
        "evidence_source": evidence_source,
        "recorded_at": _now_iso(),
    }

    # Append to ledger
    TRANSACTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TRANSACTIONS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # Update finance_data.json
    _update_finance_data(record)

    # Update reality.json
    _update_reality_after_transaction(record)

    return record


def _update_finance_data(record: Dict) -> None:
    """Update finance_data.json with verified transaction."""
    finance = _load_json(FINANCE_PATH)
    if not finance:
        finance = {"sales": [], "totalKDP": 0, "totalEtsy": 0, "totalGumroad": 0, "totalPaddle": 0, "totalSales": 0}

    finance.setdefault("sales", []).append({
        "id": record["transaction_id"],
        "product": record["product_id"],
        "amount": record["gross_revenue"],
        "net": record["net_receipts"],
        "platform": record["payment_processor"],
        "timestamp": record["recorded_at"],
    })

    processor = record["payment_processor"].lower()
    if "paddle" in processor:
        finance["totalPaddle"] = finance.get("totalPaddle", 0) + record["gross_revenue"]
    elif "gumroad" in processor:
        finance["totalGumroad"] = finance.get("totalGumroad", 0) + record["gross_revenue"]
    elif "kdp" in processor:
        finance["totalKDP"] = finance.get("totalKDP", 0) + record["gross_revenue"]
    elif "etsy" in processor:
        finance["totalEtsy"] = finance.get("totalEtsy", 0) + record["gross_revenue"]

    finance["totalSales"] = finance.get("totalSales", 0) + record["gross_revenue"]
    finance["lastUpdated"] = _now_iso()

    _save_json(FINANCE_PATH, finance)


def _update_reality_after_transaction(record: Dict) -> None:
    """Update reality.json after verified transaction."""
    reality = _load_json(REALITY_PATH)
    reality["commercial_proof"] = "VERIFIED"
    reality["repeatability"] = "UNPROVEN"  # One transaction doesn't prove repeatability
    reality["scale_level"] = max(reality.get("scale_level", 0), 1)
    reality["last_updated"] = _now_iso()
    _save_json(REALITY_PATH, reality)


def get_financial_summary() -> Dict[str, Any]:
    """Get verified financial summary with full breakdown."""
    transactions = []
    if TRANSACTIONS_PATH.exists():
        with open(TRANSACTIONS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    transactions.append(json.loads(line))

    if not transactions:
        return {
            "gross_revenue": 0.0,
            "total_fees": 0.0,
            "total_direct_costs": 0.0,
            "total_infrastructure": 0.0,
            "total_support": 0.0,
            "total_acquisition": 0.0,
            "net_receipts": 0.0,
            "total_contribution": 0.0,
            "net_profit": 0.0,
            "transaction_count": 0,
            "status": "NO_TRANSACTIONS",
        }

    gross = sum(t["gross_revenue"] for t in transactions)
    fees = sum(t["payment_fees"] for t in transactions)
    direct = sum(t["direct_costs"] for t in transactions)
    infra = sum(t["infrastructure_cost"] for t in transactions)
    support = sum(t["support_cost"] for t in transactions)
    acq = sum(t["acquisition_cost"] for t in transactions)
    net = sum(t["net_receipts"] for t in transactions)
    contrib = sum(t["contribution"] for t in transactions)
    profit = sum(t["net_profit"] for t in transactions)

    return {
        "gross_revenue": gross,
        "total_fees": fees,
        "total_direct_costs": direct,
        "total_infrastructure": infra,
        "total_support": support,
        "total_acquisition": acq,
        "net_receipts": net,
        "total_contribution": contrib,
        "net_profit": profit,
        "transaction_count": len(transactions),
        "status": "VERIFIED",
    }


# ---------------------------------------------------------------------------
# B) REPEATABILITY GATE
# ---------------------------------------------------------------------------

def assess_repeatability() -> Dict[str, Any]:
    """Assess whether the first commercial signal can be repeated.

    Returns honest assessment based on real transaction data only.
    """
    transactions = []
    if TRANSACTIONS_PATH.exists():
        with open(TRANSACTIONS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    transactions.append(json.loads(line))

    unique_customers = len(set(
        t.get("customer_record", {}).get("email", t["transaction_id"])
        for t in transactions
    ))

    unique_products = len(set(t["product_id"] for t in transactions))

    # Time span
    if len(transactions) >= 2:
        timestamps = [t["recorded_at"] for t in transactions]
        first = min(timestamps)
        last = max(timestamps)
        try:
            first_dt = datetime.fromisoformat(first)
            last_dt = datetime.fromisoformat(last)
            if first_dt.tzinfo is None:
                first_dt = first_dt.replace(tzinfo=timezone.utc)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            days_between = (last_dt - first_dt).days
        except (ValueError, TypeError):
            days_between = "UNKNOWN"
    else:
        days_between = "INSUFFICIENT_DATA"

    # Assessment
    if len(transactions) == 0:
        verdict = "NO_TRANSACTIONS"
        confidence = "NONE"
    elif len(transactions) == 1:
        verdict = "SINGLE_TRANSACTION"
        confidence = "LOW"
    elif len(transactions) == 2:
        verdict = "TWO_TRANSACTIONS"
        confidence = "MEDIUM"
    elif len(transactions) >= 3 and unique_customers >= 2:
        verdict = "REPEATABLE_EVIDENCE_EMERGING"
        confidence = "MEDIUM"
    else:
        verdict = "MULTIPLE_TRANSACTIONS_SAME_CUSTOMER"
        confidence = "LOW"

    return {
        "assessed_at": _now_iso(),
        "total_transactions": len(transactions),
        "unique_customers": unique_customers,
        "unique_products": unique_products,
        "days_between_first_last": days_between,
        "verdict": verdict,
        "confidence": confidence,
        "honesty_note": "Repeatability requires multiple unique customers over time. One transaction proves nothing about the second.",
    }


# ---------------------------------------------------------------------------
# C) GF-001 MONITORING
# ---------------------------------------------------------------------------

def update_gf001_metrics(metric_type: str, value: Any, source: str = "unknown") -> None:
    """Update GF-001 performance metrics.

    metric_type: visitors, page_views, checkout_starts, purchases,
                 refunds, delivery_failures, support_requests, feedback
    """
    metrics = _load_json(GF001_METRICS_PATH)
    if not metrics:
        metrics = {
            "product_id": "GF-001",
            "product_name": "EU AI Act Compliance Toolkit",
            "visitors": 0,
            "page_views": 0,
            "checkout_starts": 0,
            "purchases": 0,
            "refunds": 0,
            "delivery_failures": 0,
            "support_requests": 0,
            "feedback_count": 0,
            "revenue": 0.0,
            "last_updated": None,
        }

    if metric_type in metrics:
        if isinstance(metrics[metric_type], (int, float)):
            metrics[metric_type] += value if isinstance(value, (int, float)) else 1
        else:
            metrics[metric_type] = value

    metrics["last_updated"] = _now_iso()
    _save_json(GF001_METRICS_PATH, metrics)


def get_gf001_funnel() -> Dict[str, Any]:
    """Get the GF-001 conversion funnel status."""
    metrics = _load_json(GF001_METRICS_PATH)
    if not metrics:
        return {
            "product_id": "GF-001",
            "status": "NO_DATA",
            "funnel": {
                "visitors": "UNKNOWN",
                "page_views": "UNKNOWN",
                "checkout_starts": "UNKNOWN",
                "purchases": 0,
                "revenue": 0.0,
            },
            "conversion_rate": "UNKNOWN",
            "note": "No funnel data exists. Add visitor tracking first.",
        }

    visitors = metrics.get("visitors", 0)
    purchases = metrics.get("purchases", 0)
    conversion = (purchases / visitors * 100) if visitors > 0 else "UNKNOWN"

    return {
        "product_id": "GF-001",
        "product_name": metrics.get("product_name", "EU AI Act Compliance Toolkit"),
        "status": "TRACKING" if visitors > 0 else "NO_DATA",
        "funnel": {
            "visitors": visitors,
            "page_views": metrics.get("page_views", 0),
            "checkout_starts": metrics.get("checkout_starts", 0),
            "purchases": purchases,
            "refunds": metrics.get("refunds", 0),
            "delivery_failures": metrics.get("delivery_failures", 0),
            "support_requests": metrics.get("support_requests", 0),
            "revenue": metrics.get("revenue", 0.0),
        },
        "conversion_rate": f"{conversion:.1f}%" if isinstance(conversion, float) else conversion,
        "last_updated": metrics.get("last_updated"),
    }


# ---------------------------------------------------------------------------
# D) SCALE LEVELS
# ---------------------------------------------------------------------------

def get_current_scale_level() -> Dict[str, Any]:
    """Determine the current scale level based on real evidence."""
    reality = _load_json(REALITY_PATH)
    finance = get_financial_summary()
    repeatability = assess_repeatability()

    # Determine actual level from evidence
    if finance["transaction_count"] == 0:
        level = 0
    elif finance["transaction_count"] == 1:
        level = 1
    elif finance["transaction_count"] >= 2 and repeatability["unique_customers"] >= 2:
        level = 2
    elif repeatability["verdict"] == "REPEATABLE_EVIDENCE_EMERGING":
        level = 3
    else:
        level = max(reality.get("scale_level", 0), 1)

    return {
        "current_level": level,
        "level_definition": SCALE_LEVEL_DEFINITIONS.get(level, "UNKNOWN"),
        "evidence": {
            "transactions": finance["transaction_count"],
            "unique_customers": repeatability["unique_customers"],
            "revenue": finance["gross_revenue"],
            "repeatability_verdict": repeatability["verdict"],
        },
        "authorized_next_level": min(level + 1, 8),
        "honesty_note": "Scale level is determined by evidence, not aspiration. The system must not skip levels.",
    }


def can_advance_scale_level() -> Dict[str, Any]:
    """Check if the factory has enough evidence to advance to the next scale level."""
    current = get_current_scale_level()
    level = current["current_level"]

    requirements = {
        0: {"next": 1, "required": "At least one verified transaction", "status": "MET" if level >= 1 else "NOT_MET"},
        1: {"next": 2, "required": "At least two transactions from different customers", "status": "MET" if level >= 2 else "NOT_MET"},
        2: {"next": 3, "required": "System can generate customers on demand (acquisition channel proven)", "status": "MET" if level >= 3 else "NOT_MET"},
        3: {"next": 4, "required": "Contribution margin positive and verified", "status": "MET" if level >= 4 else "NOT_MET"},
        4: {"next": 5, "required": "Validated bundle/complementary product family", "status": "MET" if level >= 5 else "NOT_MET"},
        5: {"next": 6, "required": "Revenue is forecastable from evidence (3+ months data)", "status": "MET" if level >= 6 else "NOT_MET"},
        6: {"next": 7, "required": "Validated subscription/membership with real recurring customers", "status": "MET" if level >= 7 else "NOT_MET"},
        7: {"next": 8, "required": "Multiple products, multiple channels, proven scaling", "status": "MET" if level >= 8 else "NOT_MET"},
    }

    req = requirements.get(level, {"next": level, "required": "UNKNOWN", "status": "UNKNOWN"})

    return {
        "current_level": level,
        "next_level": req["next"],
        "requirement": req["required"],
        "status": req["status"],
        "can_advance": req["status"] == "MET",
    }


# ---------------------------------------------------------------------------
# E) PORTFOLIO CONTROL
# ---------------------------------------------------------------------------

def classify_asset(asset_id: str, demand_score: int = 0, quality_score: int = 0,
                   economics_score: int = 0, conversion_score: int = 0,
                   customer_value_score: int = 0) -> Dict[str, Any]:
    """Classify an asset into SCALE/TEST/IMPROVE/HOLD/KILL based on evidence.

    All scores are 0-100. Classification follows the directive's rules.
    """
    # Composite score
    composite = (
        demand_score * 0.25 +
        quality_score * 0.20 +
        economics_score * 0.25 +
        conversion_score * 0.15 +
        customer_value_score * 0.15
    )

    # Classification rules
    if composite >= 70 and economics_score >= 60:
        state = PortfolioState.SCALE
        reason = "Strong demand, quality, economics, and conversion"
    elif composite >= 50 and conversion_score >= 30:
        state = PortfolioState.TEST
        reason = "Decent signals but needs validation"
    elif composite >= 40:
        state = PortfolioState.IMPROVE
        reason = "Has potential but needs optimization"
    elif composite >= 25:
        state = PortfolioState.HOLD
        reason = "Weak signals — monitor but don't invest"
    else:
        state = PortfolioState.KILL
        reason = "No evidence of commercial viability"

    return {
        "asset_id": asset_id,
        "state": state.value,
        "composite_score": composite,
        "scores": {
            "demand": demand_score,
            "quality": quality_score,
            "economics": economics_score,
            "conversion": conversion_score,
            "customer_value": customer_value_score,
        },
        "reason": reason,
        "honesty_note": "Classification is mechanical. Retest periodically with fresh data.",
    }


# ---------------------------------------------------------------------------
# F) GOVERNANCE DASHBOARD
# ---------------------------------------------------------------------------

def commercial_governance_dashboard() -> Dict[str, Any]:
    """The unified commercial governance dashboard.

    One view of the factory's commercial state, grounded in real evidence.
    """
    reality = _load_json(REALITY_PATH)
    financial = get_financial_summary()
    repeatability = assess_repeatability()
    scale = get_current_scale_level()
    gf001 = get_gf001_funnel()
    advancement = can_advance_scale_level()

    return {
        "generated_at": _now_iso(),
        "governance_state": reality.get("governance_state", "UNKNOWN"),
        "commercial_proof": reality.get("commercial_proof", "UNKNOWN"),
        "repeatability": reality.get("repeatability", "UNKNOWN"),
        "pmf": reality.get("pmf", "UNKNOWN"),
        "predictable_revenue": reality.get("predictable_revenue", "UNKNOWN"),
        "recurring_revenue": reality.get("recurring_revenue", "UNKNOWN"),
        "saas_validation": reality.get("saas_validation", "UNKNOWN"),
        "scale_authorization": reality.get("scale_authorization", "UNKNOWN"),
        "portfolio_expansion": reality.get("portfolio_expansion", "UNKNOWN"),
        "financial_summary": financial,
        "repeatability_assessment": repeatability,
        "scale_level": scale,
        "advancement_check": advancement,
        "gf001_funnel": gf001,
        "golden_law": "REVENUE OVER ACTIVITY. EVIDENCE OVER ASSUMPTION. NO CLAIM WITHOUT EVIDENCE.",
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    result = commercial_governance_dashboard()
    print(json.dumps(result, indent=2, ensure_ascii=False))
