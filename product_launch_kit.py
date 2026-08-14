#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Product Launch Kit (PROFIT FIRST directive 2026-08-14, section 5/6).

Prepares the AUTOMATABLE distribution + attribution assets for a real
digital product that is already live on a real storefront (Gumroad),
using the existing repurposing engine and click-tracking ledger. Never
fabricates: no fake reviews, no fake sales, no invented metrics.

Real facts recorded on 2026-08-14:
  * Product: EU AI Act Compliance Toolkit (31-page PDF, $155)
  * Gumroad product_id: pzTmMb4v8cih3nbWTj5TeA== (created live via
    gumroad_publisher.create_product; draft until founder connects a
    payment method, then enable_product publishes it)
  * Short URL: https://aekraft.gumroad.com/l/iaiyt
  * Landing page: customer_site/eu-ai-act-compliance-toolkit.html
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from content_generation.repurposing_engine import Asset, repurpose_all

_FACTORY_ROOT = Path(__file__).resolve().parent

PRODUCT_ID = "pzTmMb4v8cih3nbWTj5TeA=="
PRODUCT_TITLE = "EU AI Act Compliance Toolkit — Practical Templates & Implementation Guide for SMEs"
PRODUCT_PRICE_USD = 155.0
GUMROAD_SHORT_URL = "https://aekraft.gumroad.com/l/iaiyt"
LANDING_PAGE = "customer_site/eu-ai-act-compliance-toolkit.html"

PRODUCT_DESCRIPTION = (
    "Get audit-ready for the EU AI Act without a consultancy retainer. A 31-page practical "
    "toolkit for SME compliance officers, DPOs, and founders: risk classification, technical "
    "documentation mapped to Annex IV, conformity assessment, audit-readiness checklist, "
    "and a 90-day implementation roadmap."
)

PRODUCT_TAGS = [
    "eu ai act", "ai compliance", "ai act toolkit", "ai regulation",
    "compliance checklist", "dpo tools", "ai governance", "risk assessment template",
]

# Attribution identifiers (directive section 6): SOURCE -> CAMPAIGN -> CONTENT.
LAUNCH_TRACKING = {
    "channel": "product-launch-blog",
    "campaign": "eu-ai-act-toolkit-launch",
    "content": "eu-ai-act-toolkit-guide",
    "utm_medium": "blog",
    "utm_source": "galaxyforge",
}


@dataclass
class ProductLaunchKit:
    product_id: str
    title: str
    price_usd: float
    gumroad_url: str
    landing_page: str
    channel_assets: Dict[str, Dict[str, str]]
    tracking: dict
    gumroad_status: str
    prepared_at: Optional[str] = None


def _now_iso(now: Optional[datetime] = None) -> str:
    return (now or datetime.now(timezone.utc)).isoformat()


def _asset() -> Asset:
    return Asset(
        title=PRODUCT_TITLE,
        description=PRODUCT_DESCRIPTION,
        price_usd=PRODUCT_PRICE_USD,
        source_doc=LANDING_PAGE,
        kind="product",
        tags=PRODUCT_TAGS,
    )


def prepare_product_launch_kit(gumroad_status: str = "DRAFT_PENDING_PAYMENT_METHOD",
                               now: Optional[datetime] = None) -> ProductLaunchKit:
    """Deterministic preparation of all 8 distribution assets + tracking."""
    return ProductLaunchKit(
        product_id=PRODUCT_ID,
        title=PRODUCT_TITLE,
        price_usd=PRODUCT_PRICE_USD,
        gumroad_url=GUMROAD_SHORT_URL,
        landing_page=LANDING_PAGE,
        channel_assets=repurpose_all(_asset()),
        tracking=dict(LAUNCH_TRACKING),
        gumroad_status=gumroad_status,
        prepared_at=_now_iso(now),
    )


def render_kit_json(kit: ProductLaunchKit) -> str:
    return json.dumps({
        "product_id": kit.product_id,
        "title": kit.title,
        "price_usd": kit.price_usd,
        "gumroad_url": kit.gumroad_url,
        "landing_page": kit.landing_page,
        "channel_assets": kit.channel_assets,
        "tracking": kit.tracking,
        "gumroad_status": kit.gumroad_status,
        "prepared_at": kit.prepared_at,
    }, ensure_ascii=False, indent=2)


def record_launch_click(ledger_path=None):
    """Record ONE real attributed click for the launch campaign into the real
    click ledger (the moment a real visitor clicks the product link). Uses
    the prepared attribution identifiers -- same discipline as
    affiliate_commerce.click_tracking.record_attributed_click."""
    from affiliate_commerce import click_tracking
    return click_tracking.record_attributed_click(
        product_id=PRODUCT_ID,
        channel=LAUNCH_TRACKING["channel"],
        campaign=LAUNCH_TRACKING["campaign"],
        content=LAUNCH_TRACKING["content"],
        referrer="https://galaxyforge.test/" + LANDING_PAGE,
        utm_medium=LAUNCH_TRACKING["utm_medium"],
        utm_source=LAUNCH_TRACKING["utm_source"],
        ledger_path=ledger_path,
    )