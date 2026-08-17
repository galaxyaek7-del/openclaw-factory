#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Product Launch Kit (PROFIT FIRST directive 2026-08-14, section 5/6).

Prepares the AUTOMATABLE distribution + attribution assets for a real
digital product that is already live on a real storefront (Gumroad),
using the existing repurposing engine and click-tracking ledger. Never
fabricates: no fake reviews, no fake sales, no invented metrics.

Production OS (ADR-203, 2026-08-17): the kit is now keyed by
production_id instead of hardcoded to one product. The EU AI Act
toolkit remains the DEFAULT real profile (the only product with a real
Gumroad URL/landing page on record), and any other production_id
resolves its title/price honestly from the real generation log
(books/_generation_log.jsonl), never inventing a Gumroad URL or landing
page that doesn't exist.

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
_GENERATION_LOG_PATH = _FACTORY_ROOT / "books" / "_generation_log.jsonl"

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

# The default real profile (EU AI Act toolkit) -- the one product with a real
# Gumroad URL + landing page on record. Keyed by PRODUCT_ID (the Gumroad id).
DEFAULT_PRODUCT_PROFILE = {
    "product_id": PRODUCT_ID,
    "title": PRODUCT_TITLE,
    "price_usd": PRODUCT_PRICE_USD,
    "gumroad_url": GUMROAD_SHORT_URL,
    "landing_page": LANDING_PAGE,
    "description": PRODUCT_DESCRIPTION,
    "tags": list(PRODUCT_TAGS),
    "tracking": dict(LAUNCH_TRACKING),
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


def _read_generation_log_record(production_id, generation_log_path=None):
    """Read-only: the latest real books/_generation_log.jsonl record for a
    production_id, or None. Never triggers any production."""
    path = Path(generation_log_path) if generation_log_path else _GENERATION_LOG_PATH
    latest = None
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if r.get("production_id") == production_id:
                    latest = r
    except OSError:
        return None
    return latest


def resolve_product_profile(production_id=None, generation_log_path=None):
    """Real profile dict for a production_id.

    production_id None or PRODUCT_ID (the EU AI Act toolkit's Gumroad id) ->
    the default real profile above. Any other production_id -> a real,
    honest profile derived from the real generation log: title/description
    from the record's real topic, price from the record's real price.
    gumroad_url/landing_page are the default product's real values ONLY when
    the id actually is the default product; for any other product they are
    honestly None (no real storefront page exists on record for it). Returns
    None when no real generation-log record exists -- never a fabricated
    profile."""
    if production_id is None or production_id == PRODUCT_ID:
        return dict(DEFAULT_PRODUCT_PROFILE)
    record = _read_generation_log_record(production_id, generation_log_path=generation_log_path)
    if record is None:
        return None
    topic = record.get("topic") or record.get("title") or production_id
    return {
        "product_id": production_id,
        "title": topic,
        "price_usd": record.get("price"),
        "gumroad_url": None,
        "landing_page": None,
        "description": topic,
        "tags": [],
        "tracking": {
            "channel": "product-launch-blog",
            "campaign": f"launch-{production_id}",
            "content": f"{production_id}-guide",
            "utm_medium": "blog",
            "utm_source": "galaxyforge",
        },
    }


def _asset(profile=None) -> Asset:
    profile = profile or DEFAULT_PRODUCT_PROFILE
    return Asset(
        title=profile["title"],
        description=profile["description"],
        price_usd=profile.get("price_usd"),
        source_doc=profile.get("landing_page"),
        kind="product",
        tags=profile.get("tags") or [],
    )


def prepare_product_launch_kit(gumroad_status: str = "DRAFT_PENDING_PAYMENT_METHOD",
                               now: Optional[datetime] = None,
                               production_id: Optional[str] = None,
                               generation_log_path: Optional[str] = None) -> ProductLaunchKit:
    """Deterministic preparation of all 8 distribution assets + tracking for
    the given production_id (default: the EU AI Act toolkit). Raises
    ValueError for an unknown production_id with no real generation-log
    record -- never fabricates a kit for a product that doesn't exist."""
    profile = resolve_product_profile(production_id, generation_log_path=generation_log_path)
    if profile is None:
        raise ValueError(
            f"no real profile available for production_id={production_id!r}: "
            "no real books/_generation_log.jsonl record exists for it"
        )
    return ProductLaunchKit(
        product_id=profile["product_id"],
        title=profile["title"],
        price_usd=profile["price_usd"],
        gumroad_url=profile["gumroad_url"],
        landing_page=profile["landing_page"],
        channel_assets=repurpose_all(_asset(profile)),
        tracking=dict(profile["tracking"]),
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


def record_launch_click(ledger_path=None, production_id: Optional[str] = None,
                        generation_log_path: Optional[str] = None):
    """Record ONE real attributed click for the launch campaign into the real
    click ledger (the moment a real visitor clicks the product link). Uses
    the prepared attribution identifiers for the given production_id (default:
    the EU AI Act toolkit) -- same discipline as
    affiliate_commerce.click_tracking.record_attributed_click. Raises
    ValueError for an unknown production_id -- never records a click for a
    product with no real profile."""
    profile = resolve_product_profile(production_id, generation_log_path=generation_log_path)
    if profile is None:
        raise ValueError(
            f"no real profile available for production_id={production_id!r}: "
            "no real books/_generation_log.jsonl record exists for it"
        )
    tracking = profile["tracking"]
    from affiliate_commerce import click_tracking
    return click_tracking.record_attributed_click(
        product_id=profile["product_id"],
        channel=tracking["channel"],
        campaign=tracking["campaign"],
        content=tracking["content"],
        referrer=("https://galaxyforge.test/" + profile["landing_page"]) if profile.get("landing_page") else None,
        utm_medium=tracking["utm_medium"],
        utm_source=tracking["utm_source"],
        ledger_path=ledger_path,
    )