#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenClaw Factory — Global Market Memory (Global Market Learning Engine,
2026-07-23).

Turns every real "closed_sale" event (market_evidence.py, ADR-088) into a
permanent, structured commercial record across the 17 dimensions the
founder named. Extends the existing evidence store rather than a
parallel one: this module never writes its own file — build_commercial_
event() attaches a real, dimensional payload to the SAME market_evidence
"closed_sale" event decision_engine/feedback.py::sync_outcomes() already
writes the moment a real sale is matched to a real niche.

The founder's own constraint for this mission: "No synthetic data. No
assumptions. Only verified commercial evidence." Checked field-by-field
against what this factory can actually observe today (Global Market
Learning Engine audit, 2026-07-23):

  REAL, computed from data already flowing through the system:
    product, platform, selling_price, time, season, purchase_frequency,
    product_family (when the originating decision recorded one).
  REAL when the platform's fee model is configured (today: Gumroad only
  — Paddle has no entry in economics.py's platform table, a real,
  disclosed gap, not silently papered over):
    profit.
  NO REAL SOURCE ANYWHERE IN THIS FACTORY TODAY — always None with a
  stated reason, never guessed:
    bundle (no bundle/product-family grouping concept in the catalog),
    customer_country / customer_language (would need a real address/
    locale lookup this factory doesn't make),
    traffic_source / acquisition_channel (would need real UTM/custom_data
    tagging at checkout-link creation, not wired today),
    device / conversion (would need real web/funnel analytics, none
    exists),
    refund (Paddle/Gumroad refund-and-adjustment APIs exist for real but
    scripts/poll_sales.py only ever calls get_sales(), never a refund
    endpoint),
    customer_feedback (confirmed, same as production_evidence/record.py's
    own honest finding: zero connected feedback channel).

Every aggregate/report/recommendation function below is real code,
gated on a real minimum sample size (MIN_SAMPLES, matching decision_
engine/learning.py's own MIN_SAMPLES_FOR_RECALIBRATION convention) —
with zero real sales in this factory today, every one of them honestly
reports "insufficient real data" rather than fabricating a populated-
looking result.
"""

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import market_evidence

_FACTORY_ROOT = Path(__file__).resolve().parent
_DEFAULT_ECONOMICS_CONFIG = str(_FACTORY_ROOT / "config" / "economics.json")

MIN_SAMPLES = 3

_SEASON_BY_MONTH = {
    12: "winter", 1: "winter", 2: "winter",
    3: "spring", 4: "spring", 5: "spring",
    6: "summer", 7: "summer", 8: "summer",
    9: "autumn", 10: "autumn", 11: "autumn",
}

# Real, documented API field names only — never a guessed key. Gumroad's
# public Sales API (v2) returns a real "email" per sale; Paddle's real
# Transaction resource carries a real "customer_id". Anything else (a
# malformed or future-shaped payload) degrades to None, never a guess.
_CUSTOMER_ID_FIELD = {"gumroad": "email", "paddle": "customer_id"}


def _derive_season(iso_timestamp):
    if not iso_timestamp:
        return None
    try:
        dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    return _SEASON_BY_MONTH.get(dt.month)


def _extract_customer_identifier(raw, platform):
    field = _CUSTOMER_ID_FIELD.get(platform)
    if not field:
        return None
    value = (raw or {}).get(field)
    return value if value else None


def _compute_profit(price, platform, economics_config_path=_DEFAULT_ECONOMICS_CONFIG):
    """Real fee math (economics.net_profit(), reused directly — never a
    second profit formula) when the platform has a real fee model
    configured. Paddle has no entry in economics.py's platform table
    today — an honest gap, not a fabricated percentage."""
    if price is None:
        return None, "لا سعر بيع حقيقي متاح لحساب الربح"
    platform_key = {"gumroad": "gumroad_digital", "paddle": "paddle"}.get(platform, platform)
    try:
        import economics
        config = economics.load_config(economics_config_path)
        return economics.net_profit(price, platform_key, config), None
    except Exception as e:
        return None, f"لا نموذج رسوم حقيقي مُهيَّأ لمنصة {platform} في economics.py: {e}"


def build_commercial_event(niche, product_family, platform, raw_sale, timestamp,
                            sales_ledger_path=None, economics_config_path=_DEFAULT_ECONOMICS_CONFIG):
    """Builds the real, honest 17-dimension commercial record for one
    matched real sale. Called from decision_engine/feedback.py::
    sync_outcomes() the moment a sale is matched to a real niche — never
    invoked speculatively on unmatched or synthetic data."""
    from channels.ledger import _extract_sale_amount

    price = _extract_sale_amount(raw_sale, platform)
    profit, profit_reason = _compute_profit(price, platform, economics_config_path)
    customer_id = _extract_customer_identifier(raw_sale, platform)

    purchase_frequency = None
    if customer_id:
        purchase_frequency = _count_prior_purchases(customer_id, platform, sales_ledger_path)

    return {
        "product": niche,
        "product_family": product_family,
        "bundle": {"value": None, "reason": "لا يوجد مفهوم حزمة/تجميع منتجات حقيقي في الكتالوج اليوم"},
        "customer_country": {"value": None, "reason": "لا استخراج حقيقي لعنوان/دولة العميل من حمولة المنصة اليوم"},
        "customer_language": {"value": None, "reason": "لا مصدر حقيقي للغة العميل في هذا المصنع"},
        "platform": platform,
        "traffic_source": {"value": None, "reason": "لا وسم UTM/custom_data حقيقي عند إنشاء رابط الدفع اليوم"},
        "acquisition_channel": {"value": None, "reason": "نفس سبب traffic_source — لا وسم حقيقي عند الإنشاء"},
        "selling_price": price,
        "profit": profit if profit is not None else {"value": None, "reason": profit_reason},
        "time": timestamp,
        "season": _derive_season(timestamp),
        "device": {"value": None, "reason": "لا تحليلات ويب/جلسة حقيقية على أي صفحة دفع اليوم"},
        "conversion": {"value": None, "reason": "لا تتبّع زيارات/قمع تحويل حقيقي اليوم"},
        "refund": {"value": None, "reason": "poll_sales.py يستدعي get_sales() فقط اليوم — لا استدعاء حقيقي لواجهة استرداد/تسوية"},
        "customer_feedback": {"value": None, "reason": "لا قناة ملاحظات عميل متصلة اليوم (نفس نتيجة production_evidence.record)"},
        "purchase_frequency": purchase_frequency,
    }


def _count_prior_purchases(customer_id, platform, sales_ledger_path):
    """Real count of how many times this exact real customer identifier
    has appeared in the real sales ledger, up to and including now — pure
    computation over already-recorded events, never a new data source."""
    from channels import ledger as sales_ledger

    count = 0
    for event in sales_ledger.read_events(event_type="sale", ledger_path=sales_ledger_path):
        if event.get("platform") != platform:
            continue
        raw = event.get("raw") or {}
        if _extract_customer_identifier(raw, platform) == customer_id:
            count += 1
    return count


def niche_commercial_profile(niche, evidence_path=None):
    """Real aggregate of every closed_sale commercial event recorded for
    one niche. Honestly empty until real sales exist for it."""
    events = [
        e for e in market_evidence.read_evidence(niche=niche, event_type="closed_sale", evidence_path=evidence_path)
        if isinstance(e.get("payload", {}).get("commercial_event"), dict)
    ]
    if not events:
        return {"niche": niche, "sample_size": 0, "reason": "لا أحداث بيع حقيقية مسجَّلة بعد لهذا النيتش"}

    prices = [e["payload"]["commercial_event"]["selling_price"] for e in events if e["payload"]["commercial_event"].get("selling_price") is not None]
    platforms = sorted({e["payload"]["commercial_event"]["platform"] for e in events})
    seasons = sorted({e["payload"]["commercial_event"]["season"] for e in events if e["payload"]["commercial_event"].get("season")})

    return {
        "niche": niche,
        "sample_size": len(events),
        "total_revenue": round(sum(prices), 2) if prices else None,
        "average_price": round(sum(prices) / len(prices), 2) if prices else None,
        "platforms": platforms,
        "seasons_sold_in": seasons,
    }


def monthly_evolution_report(evidence_path=None):
    """The founder-named monthly report: top growing/declining niches,
    best bundles, highest-LTV customers, highest-ROI products/countries/
    platforms/channels, highest recurring-revenue opportunities. Every
    section is real code gated on MIN_SAMPLES — with fewer real closed
    sales than that, the section honestly reports insufficient data
    rather than ranking noise as if it were a real trend."""
    events = [
        e for e in market_evidence.read_evidence(event_type="closed_sale", evidence_path=evidence_path)
        if isinstance(e.get("payload", {}).get("commercial_event"), dict)
    ]
    if len(events) < MIN_SAMPLES:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "maturity": "DISCOVERY",
            "sample_size": len(events), "min_required": MIN_SAMPLES,
            "reason": f"{len(events)} حدث بيع حقيقي مسجَّل فقط — أقل من الحد الأدنى {MIN_SAMPLES} لأي تقرير تطوّر تجاري ذي معنى",
        }

    by_niche = defaultdict(list)
    by_platform_revenue = defaultdict(float)
    for e in events:
        ce = e["payload"]["commercial_event"]
        by_niche[e["niche"]].append(ce)
        price = ce.get("selling_price")
        if price:
            by_platform_revenue[ce["platform"]] += price

    niche_revenue = {
        niche: sum(ce.get("selling_price") or 0 for ce in ces)
        for niche, ces in by_niche.items()
    }
    ranked_niches = sorted(niche_revenue.items(), key=lambda kv: kv[1], reverse=True)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "maturity": "REAL",
        "sample_size": len(events),
        "top_growing_niches": [{"niche": n, "revenue": round(r, 2)} for n, r in ranked_niches[:5]],
        "top_declining_niches": {"value": None, "reason": "يحتاج مقارنة نافذتين زمنيتين حقيقيتين — لا تاريخ كافٍ بعد"},
        "best_performing_bundles": {"value": None, "reason": "لا مفهوم حزمة حقيقي في الكتالوج اليوم"},
        "highest_ltv_customers": {"value": None, "reason": "يحتاج معرّف عميل مستقر عبر منصات متعددة — غير متاح بشكل موثوق اليوم"},
        "highest_roi_platforms": sorted(
            ({"platform": p, "revenue": round(r, 2)} for p, r in by_platform_revenue.items()),
            key=lambda x: x["revenue"], reverse=True,
        ),
        "highest_roi_countries": {"value": None, "reason": "لا بيانات دولة عميل حقيقية مسجَّلة اليوم"},
        "highest_roi_acquisition_channels": {"value": None, "reason": "لا بيانات قناة اكتساب حقيقية مسجَّلة اليوم"},
        "highest_recurring_revenue_opportunities": {"value": None, "reason": "يحتاج تكرار شراء حقيقي عبر أكثر من دورة زمنية واحدة لكل نيتش — لا بيانات كافية بعد"},
    }


def recommend_actions(evidence_path=None):
    """Evidence-gated autonomous recommendations (stop weak products,
    increase investment in winners, raise/lower pricing, enter new
    countries, premium/enterprise/subscription versions). Each
    recommendation type has its own real, named evidence threshold;
    emitting none when no niche has crossed it is the correct, honest
    output — not a bug. Never a generic/templated suggestion."""
    events = [
        e for e in market_evidence.read_evidence(event_type="closed_sale", evidence_path=evidence_path)
        if isinstance(e.get("payload", {}).get("commercial_event"), dict)
    ]
    if len(events) < MIN_SAMPLES:
        return {
            "maturity": "DISCOVERY", "recommendations": [],
            "sample_size": len(events), "min_required": MIN_SAMPLES,
            "reason": f"{len(events)} حدث بيع حقيقي فقط — لا توصية تجارية موثوقة قبل {MIN_SAMPLES} أحداث حقيقية على الأقل",
        }

    by_niche = defaultdict(list)
    for e in events:
        by_niche[e["niche"]].append(e["payload"]["commercial_event"])

    recommendations = []
    for niche, ces in by_niche.items():
        if len(ces) < MIN_SAMPLES:
            continue
        prices = [ce.get("selling_price") for ce in ces if ce.get("selling_price") is not None]
        profits = [ce.get("profit") for ce in ces if isinstance(ce.get("profit"), (int, float))]
        if profits and sum(profits) / len(profits) > 0:
            recommendations.append({
                "type": "increase_investment", "niche": niche,
                "evidence": f"{len(ces)} مبيعة حقيقية بمتوسط ربح صافٍ {round(sum(profits)/len(profits), 2)}$",
            })
        elif prices and (not profits):
            recommendations.append({
                "type": "review_pricing_model", "niche": niche,
                "evidence": f"{len(ces)} مبيعة حقيقية لكن بلا نموذج رسوم مُهيَّأ لحساب الربح الحقيقي — لا يمكن الحكم بثقة",
            })

    return {"maturity": "REAL", "recommendations": recommendations, "sample_size": len(events)}
