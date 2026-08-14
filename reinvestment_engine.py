#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reinvestment Engine (directive 2026-08-14, section 10).

When affiliate revenue actually starts, profit is split per the founder's
capital policy, never spent randomly. The priority order below is the
directive's own (1. improve system, 2. expand income sources, 3. tools
with clear ROI, 4. build Galaxy Forge assets, 5. premium B2B products,
6. recurring revenue products).

Honesty contract: this module computes ALLOCATIONS only from REAL
realized revenue provided as input (or read from the real commission
ledger). It never invents a profit figure. With zero realized revenue it
returns an honest all-zero plan. It never spends anything itself -- it
only produces an allocation plan awaiting founder approval.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

# The directive's priority order for reinvestment (weights are documented
# defaults the founder may change; they only ever apply to real profit).
REINVESTMENT_PRIORITY = [
    ("system_improvement", "تحسين النظام"),
    ("expand_income_sources", "توسيع مصادر الدخل"),
    ("production_tools_clear_roi", "أدوات الإنتاج ذات العائد الواضح"),
    ("galaxy_forge_assets", "بناء الأصول الخاصة بـ Galaxy Forge"),
    ("premium_b2b_products", "Premium B2B products"),
    ("recurring_revenue_products", "Recurring revenue products"),
]

DEFAULT_POLICY = {
    "system_improvement": 0.30,
    "expand_income_sources": 0.25,
    "production_tools_clear_roi": 0.20,
    "galaxy_forge_assets": 0.15,
    "premium_b2b_products": 0.05,
    "recurring_revenue_products": 0.05,
}

FOUNDER_RESERVE_RATE = 0.20  # fixed reserve kept before any reinvestment split


@dataclass
class ReinvestmentPlan:
    realized_net_profit_usd: float
    founder_reserve_usd: float
    reinvestable_usd: float
    allocations: Dict[str, float]
    notes: List[str]
    generated_at: Optional[str] = None


def realized_affiliate_profit(commission_ledger_path=None) -> float:
    """Real realized profit from the REAL commission ledger (CONFIRMED/PAID,
    REAL environment only). With nothing real, returns 0.0 honestly."""
    try:
        import commission_ledger as cl
        ledger = cl.load_ledger(commission_ledger_path)
        return sum(
            float(r.get("gross_commission") or 0)
            for r in ledger
            if r.get("environment") == "REAL"
            and r.get("commission_status") in ("CONFIRMED", "PAID")
        )
    except Exception:
        return 0.0


def build_reinvestment_plan(net_profit: Optional[float] = None,
                            policy: Optional[Dict[str, float]] = None,
                            commission_ledger_path=None,
                            now: Optional[datetime] = None) -> ReinvestmentPlan:
    """Build the founder-approval reinvestment plan.

    net_profit: optional explicit real figure; if None it is read from the
    real commission ledger (0.0 if nothing real). `policy` weights default
    to the directive order. Any negative/invalid net profit is clamped to
    0.0 with an honest note (no fabricated loss allocations).
    """
    if net_profit is None:
        net_profit = realized_affiliate_profit(commission_ledger_path)
    if net_profit < 0:
        net_profit = 0.0
    policy = dict(DEFAULT_POLICY if policy is None else policy)

    reserve = round(net_profit * FOUNDER_RESERVE_RATE, 2)
    reinvestable = round(net_profit - reserve, 2)

    notes = []
    if net_profit <= 0:
        notes.append("صفر إيراد حقيقي محقق — الخطة كلها أصفار؛ لا يُختلق ربح.")
    if any(w < 0 for w in policy.values()):
        notes.append("تم تجاهل أي وزن سالب في السياسة (لا يوجد إنفاق سلبي).")

    allocations: Dict[str, float] = {}
    weight_sum = sum(max(w, 0) for w in policy.values())
    for key, _label in REINVESTMENT_PRIORITY:
        w = max(policy.get(key, 0.0), 0.0)
        allocations[key] = round(reinvestable * (w / weight_sum), 2) if weight_sum > 0 else 0.0

    # Fix rounding drift so allocations sum exactly to reinvestable.
    allocated = sum(allocations.values())
    if reinvestable > 0 and allocated != reinvestable:
        first_key = next(iter(allocations))
        allocations[first_key] = round(allocations[first_key] + (reinvestable - allocated), 2)

    return ReinvestmentPlan(
        realized_net_profit_usd=round(net_profit, 2),
        founder_reserve_usd=reserve,
        reinvestable_usd=reinvestable,
        allocations=allocations,
        notes=notes,
        generated_at=(now or datetime.now(timezone.utc)).isoformat(),
    )


def reinvestment_status(commission_ledger_path=None) -> Dict[str, object]:
    """Honest status for the dashboard: real realized profit + the plan.
    Never reports a profit that isn't real."""
    plan = build_reinvestment_plan(commission_ledger_path=commission_ledger_path)
    return {
        "realized_net_profit_usd": plan.realized_net_profit_usd,
        "founder_reserve_usd": plan.founder_reserve_usd,
        "reinvestable_usd": plan.reinvestable_usd,
        "allocations": plan.allocations,
        "policy": dict(DEFAULT_POLICY),
        "notes": plan.notes,
        "note": "القيم مبنية فقط على أرباح حقيقية محققة من ledger العمولة — لا تخمين.",
    }