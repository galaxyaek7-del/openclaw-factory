#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — Commercial Intelligence Engine (Real World Commercial
Expansion, 2026-07-24).

The founder-named signals (demand, willingness to pay, competition, price
ranges, buying behavior, regional differences, product opportunities,
customer pain), assembled as one real report — pure aggregation over
already-real, already-built intelligence, never a new gathering pass:

  demand                <- opportunity_pipeline.annotate_decision()'s
                            real market_size (discussion-volume proxy,
                            never a fabricated dollar TAM)
  willingness_to_pay     <- market_evidence.get_willingness_to_pay_signal()
                            (real demo_request/trial_request/purchase_
                            attempt/closed_sale evidence)
  competition            <- annotate_decision()'s real competition field
                            (competitor_discovery.py's cached snapshot,
                            never a fresh live network call from a report)
  price_ranges           <- profit_oracle.py's real, documented ladder
                            price bands + this decision's own real
                            recommended price
  buying_behavior        <- market_memory.niche_commercial_profile()
                            (real purchase frequency/season/platform)
  product_opportunities  <- growth_engine.evaluate_product_multiplication()
  customer_pain          <- annotate_decision()'s real pain_level

  NO REAL SOURCE ANYWHERE IN THIS FACTORY TODAY:
  regional_differences   <- honestly {value: None, reason: ...} — zero
                            real country-level customer/market data
                            exists yet (confirmed repeatedly, including
                            for this factory's one real live payment
                            processor). Real World Commercial Expansion
                            Priority 1/2 (2026-07-24): explicitly
                            deprioritized in favor of this module and
                            growth_engine.py's premium catalog, since
                            building this field without real data would
                            be exactly the fabrication this mission's
                            own rules forbid.
"""

from datetime import datetime, timezone


def build_commercial_intelligence_report(niche, decisions_path=None, board_path=None, alerts_path=None,
                                          reopen_log_path=None, evidence_path=None, db_file=None):
    """Real commercial intelligence for one niche. Returns None (never
    fabricated) when this niche has no real decision on record at
    all — this report is meaningful even for a not-yet-accepted niche
    (unlike value_engine's ACCEPTED-only scope), since demand/
    competition/pain intelligence is gathered pre-decision."""
    import factory_orchestrator as fo
    import opportunity_pipeline as op
    import market_evidence
    import market_memory
    import growth_engine

    decision = fo.find_decision(niche, decisions_path=decisions_path)
    if decision is None:
        return None

    annotated = op.annotate_decision(
        decision, board_path=board_path, alerts_path=alerts_path, reopen_log_path=reopen_log_path,
    )

    willingness_to_pay = market_evidence.get_willingness_to_pay_signal(niche, evidence_path=evidence_path)
    buying_behavior = market_memory.niche_commercial_profile(niche, evidence_path=evidence_path)
    price_ranges = _real_price_range(decision.get("ladder"), annotated.get("estimated_selling_price"))
    product_opportunities = (
        growth_engine.evaluate_product_multiplication(
            niche, decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
            reopen_log_path=reopen_log_path, evidence_path=evidence_path,
        )
        if decision.get("status") == "ACCEPTED" else
        {"value": None, "reason": "يتطلب قراراً مقبولاً فعلاً (ACCEPTED) — هذا القرار حالياً: " + str(decision.get("status"))}
    )

    return {
        "niche": niche,
        "demand": annotated.get("market_size"),
        "willingness_to_pay": willingness_to_pay,
        "competition": annotated.get("competition"),
        "price_ranges": price_ranges,
        "buying_behavior": buying_behavior,
        "regional_differences": {
            "value": None,
            "reason": "لا بيانات دولة/سوق إقليمي حقيقية في هذا المصنع اليوم لأي قناة حقيقية — مؤجَّل بوعي (Real World Commercial Expansion، أولوية 1/2، 2026-07-24)",
        },
        "product_opportunities": product_opportunities,
        "customer_pain": annotated.get("pain_level"),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }


def _real_price_range(ladder, estimated_selling_price):
    """Real, documented ladder price bands (profit_oracle.py) — never a
    second pricing model. Honestly Unknown with no real ladder."""
    import profit_oracle

    if not ladder or ladder not in profit_oracle.LADDER_PRICE_BAND:
        return {"value": None, "reason": "لا ladder حقيقي مُسجَّل لهذا القرار لتحديد نطاق سعر حقيقي"}

    band = profit_oracle.LADDER_PRICE_BAND[ladder]
    bounds = {
        "book": (profit_oracle.MIN_BUTTER_PRICE, profit_oracle.MAX_BUTTER_PRICE),
        "premium": (profit_oracle.MIN_BUTTER_PRICE_PREMIUM, profit_oracle.MAX_BUTTER_PRICE_PREMIUM),
        "elite": (profit_oracle.MIN_BUTTER_PRICE_ELITE, profit_oracle.MAX_BUTTER_PRICE_ELITE),
    }.get(band)
    if bounds is None:
        return {"value": None, "reason": f"نطاق سعر غير معروف لـ price_band={band!r}"}

    return {
        "ladder": ladder, "price_band": band,
        "min_price": bounds[0], "max_price": bounds[1],
        "this_decision_price": estimated_selling_price if isinstance(estimated_selling_price, (int, float)) else None,
    }
