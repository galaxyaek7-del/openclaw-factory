#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Affiliate Launch Prep (First Revenue directive 2026-08-14).

Picks the ONE launch opportunity internally (never asks the founder to
choose) and prepares every AUTOMATABLE launch asset for it using only the
existing, already-built affiliate modules:

  * offer    -- the real portfolio record (commission, terms, evidence)
  * content  -- the full educational chain from affiliate_content_factory
                (from_portfolio_opportunity, verified_usage=False -- we never
                claim hands-on experience we do not have)
  * tracking -- the real channel/campaign/content/UTM identifiers that will
                tag every real click via
                affiliate_commerce.click_tracking.record_attributed_click
  * link     -- honest affiliate_link_status. A CJ tracking link only exists
                after the founder completes the ONE founder action (apply via
                CJ + connect Payoneer) and the network issues a link -- until
                then it is NOT_CONFIGURED, never fabricated.
  * measure  -- revenue_intelligence_dashboard() read over the real ledgers
                (0 revenue today, honestly reported).

Deterministic and zero-cost: same inputs -> same output; no LLM, no
network call, no fake revenue, no fabricated link. Nothing here posts
externally -- it only prepares what the ONE founder action unlocks.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from commission_engine import load_opportunity_portfolio
from affiliate_content_factory import from_portfolio_opportunity

_FACTORY_ROOT = Path(__file__).resolve().parent

# The single, internally-decided launch opportunity. Chosen 2026-08-14 after
# official-source verification (see portfolio records): it is the only
# VERIFIED recurring program whose payout is receivable in Algeria
# (DigitalOcean pays via CJ -> Payoneer; Payoneer supports Algeria. AWeber/
# SiteGround pay via PayPal and Brevo via PartnerStack/Airwallex -- none of
# which support receiving payments in Algeria, verified from official docs).
LAUNCH_OPPORTUNITY_ID = "CO-digitalocean-affiliate"

# Real tracking identifiers prepared for the launch. These are STATIC and
# reviewed; a real click will be recorded with exactly these values.
LAUNCH_TRACKING = {
    "channel": "digitalocean-educational-blog",
    "campaign": "first-revenue-cloud-infra",
    "content": "digitalocean-cloud-infra-guide",
    "utm_medium": "blog",
    "utm_source": "galaxyforge",
}

# Official CJ link shape -- only filled once the founder's CJ application is
# approved and the network issues the real tracking link. Until then the
# placeholder is honest (NOT_CONFIGURED), never a guessed URL.
LAUNCH_LINK_STATUS = "NOT_CONFIGURED"
LAUNCH_LINK_OFFICIAL_PROGRAM_URL = "https://www.digitalocean.com/affiliates"


@dataclass
class LaunchPrep:
    opportunity_id: str
    program_name: str
    offer: dict
    content_pieces: List[dict]
    tracking: dict
    affiliate_link_status: str
    affiliate_link_url: Optional[str]
    measurement: dict
    founder_action: dict
    prepared_at: Optional[str] = None


def _now_iso(now: Optional[datetime] = None) -> str:
    return (now or datetime.now(timezone.utc)).isoformat()


def prepare_launch(opportunity_id: Optional[str] = None,
                   portfolio: Optional[List[dict]] = None,
                   now: Optional[datetime] = None) -> LaunchPrep:
    """Prepare the automatable launch assets for the single launch
    opportunity. Real data only; everything honest and deterministic."""
    portfolio = portfolio if portfolio is not None else load_opportunity_portfolio()
    opp_id = opportunity_id or LAUNCH_OPPORTUNITY_ID

    offer = next((o for o in portfolio if o.get("opportunity_id") == opp_id), None)
    if offer is None:
        raise ValueError(f"opportunity {opp_id} not in real portfolio")

    pieces = from_portfolio_opportunity(offer, verified_usage=False, now=now)
    content_pieces = [
        {"format": p.format, "title": p.title, "body": p.body, "cta": p.cta, "disclosure": p.disclosure}
        for p in pieces
    ]

    measurement = _measurement_now(now=now)
    founder_action = _founder_action(offer)

    return LaunchPrep(
        opportunity_id=offer["opportunity_id"],
        program_name=offer.get("program_name") or offer.get("partner_name", ""),
        offer=offer,
        content_pieces=content_pieces,
        tracking=dict(LAUNCH_TRACKING),
        affiliate_link_status=LAUNCH_LINK_STATUS,
        affiliate_link_url=None,
        measurement=measurement,
        founder_action=founder_action,
        prepared_at=_now_iso(now),
    )


def _measurement_now(now: Optional[datetime] = None) -> dict:
    """Real measurement read over the real ledgers (via revenue_
    intelligence_dashboard). Never fabricates revenue -- zeros are real
    zeros, missing denominators stay N/A."""
    from revenue_intelligence import revenue_intelligence_dashboard
    dash = revenue_intelligence_dashboard(now=now)
    return {
        "REVENUE_COMMISSION_USD": dash["REVENUE_COMMISSION_USD"],
        "CLICKS": dash["CLICKS"],
        "PAGE_VIEWS": dash["PAGE_VIEWS"],
        "CONVERSIONS": dash["CONVERSIONS"],
        "CONVERSION_RATE": dash["CONVERSION_RATE"],
        "EPC_USD": dash["EPC_USD"],
        "RECURRING_COMMISSION_USD": dash["RECURRING_COMMISSION_USD"],
    }


def _founder_action(offer: dict) -> dict:
    """Exactly ONE founder action -- everything else is automated. The CJ
    application + Payoneer connection is the single legal/identity act only
    the founder can complete; every other launch asset is already prepared."""
    return {
        "action": "APPLY_CJ_DIGITALOCEAN",
        "what": (
            f"سجّل كمعلن (Publisher) على CJ Affiliate، قدّم طلب انضمام لبرنامج "
            f"{offer.get('program_name', 'DigitalOcean Affiliate Program')}، "
            f"وأضف حساب Payoneer كطريقة دفع (متوافقة مع الجزائر)."
        ),
        "why": (
            "PayPal لا يدعم استلام المدفوعات في الجزائر (تحقق رسمي 2026-08-14)؛ "
            "CJ تدفع عالميًا عبر Payoneer (متاح في الجزائر) -- هذا هو الممر "
            "الوحيد الموثّق لاستلام أول عمولة فعلية."
        ),
        "unlocks": (
            "رابط CJ tracking الرسمي -> نشره عبر المحتوى المُعد + تسجيل النقرات "
            "بمعرّفات LAUNCH_TRACKING -> تتبعها في revenue_intelligence."
        ),
    }


def render_launch_prep_json(prep: LaunchPrep) -> str:
    """Deterministic JSON rendering of the launch prep (for the short report)."""
    return json.dumps({
        "opportunity_id": prep.opportunity_id,
        "program_name": prep.program_name,
        "offer_snapshot": {
            "commission_value": prep.offer.get("commission_value"),
            "commission_currency": prep.offer.get("commission_currency"),
            "recurring_commission": prep.offer.get("recurring_commission"),
            "payout_terms": prep.offer.get("payout_terms"),
            "payout_algeria_compatible": prep.offer.get("payout_algeria_compatible"),
            "evidence_url": prep.offer.get("evidence_url"),
        },
        "content_piece_formats": [p["format"] for p in prep.content_pieces],
        "tracking": prep.tracking,
        "affiliate_link_status": prep.affiliate_link_status,
        "measurement": prep.measurement,
        "founder_action": prep.founder_action,
        "prepared_at": prep.prepared_at,
    }, ensure_ascii=False, indent=2)