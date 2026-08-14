"""Affiliate Launch Batch — one verified offer -> publish-ready multi-channel
assets, each carrying its own UTM/tracking fingerprint.

Deterministic, zero-cost, no fabricated facts: every asset is derived from the
real, verified portfolio offer; the affiliate destination is never guessed
(NOT_CONFIGURED until the network issues the real tracking link).

Channels generated are the ones the repurposing engine can genuinely build for
this offer type: short video (TikTok/Reel/Short), X, Facebook, Pinterest,
LinkedIn, email, and SEO/landing. Nothing is auto-published here — platform
rules are respected and publishing happens only via the founder's authorized
accounts.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from affiliate_launch_prep import LAUNCH_TRACKING, LAUNCH_LINK_STATUS
from affiliate_content_factory import from_portfolio_opportunity
from commission_engine import load_opportunity_portfolio
from content_generation.repurposing_engine import Asset, repurpose

_FACTORY_ROOT = Path(__file__).resolve().parent
_DEFAULT_OUTPUT_DIR = _FACTORY_ROOT / "launch_batches"

# Channels this offer's audience genuinely lives on, matched to real builders.
LAUNCH_CHANNELS = (
    "short_video_script",   # TikTok / Reels / YouTube Shorts
    "x_post",
    "facebook_post",
    "pinterest_asset",
    "linkedin_post",
    "email_newsletter",
    "seo_content",
)

UTM_SOURCE_BY_CHANNEL = {
    "short_video_script": "tiktok",
    "x_post": "x",
    "facebook_post": "facebook",
    "pinterest_asset": "pinterest",
    "linkedin_post": "linkedin",
    "email_newsletter": "email",
    "seo_content": "seo",
}


@dataclass
class BatchAsset:
    channel: str
    utm_source: str
    content: dict
    destination_status: str
    destination_url: Optional[str] = None
    attribution: dict = field(default_factory=dict)


@dataclass
class LaunchBatch:
    opportunity_id: str
    program_name: str
    campaign: dict
    assets: List[BatchAsset]
    disclosure: str
    link_status: str
    generated_at: Optional[str] = None


def _now_iso(now: Optional[datetime] = None) -> str:
    return (now or datetime.now(timezone.utc)).isoformat()


def _utm_for(channel: str, content_key: str) -> dict:
    utm_source = UTM_SOURCE_BY_CHANNEL.get(channel, "galaxyforge")
    return {
        "utm_source": utm_source,
        "utm_medium": LAUNCH_TRACKING.get("utm_medium", "blog"),
        "utm_campaign": LAUNCH_TRACKING.get("campaign", "first-revenue"),
        "utm_content": content_key,
    }


def build_launch_batch(opportunity_id: Optional[str] = None,
                       portfolio: Optional[List[dict]] = None,
                       channels: Optional[tuple] = None,
                       now: Optional[datetime] = None) -> LaunchBatch:
    """Build the full multi-channel launch batch for the selected verified
    opportunity. Real fields only; destination stays honest NOT_CONFIGURED."""
    portfolio = portfolio if portfolio is not None else load_opportunity_portfolio()
    opp_id = opportunity_id or "CO-digitalocean-affiliate"
    offer = next((o for o in portfolio if o.get("opportunity_id") == opp_id), None)
    if offer is None:
        raise ValueError(f"opportunity {opp_id} not in real portfolio")

    name = offer.get("program_name") or offer.get("partner_name") or opp_id
    product = offer.get("product_or_service") or offer.get("program_name") or "cloud infrastructure"
    problem = offer.get("customer_problem") or "cheap, predictable cloud infrastructure"
    audience = offer.get("target_customer") or "developers and startups"
    commission = offer.get("commission_value") or ""

    # One real source asset -> every channel (deterministic, no fabrication).
    asset = Asset(
        title=f"Deploy on cloud in minutes: {product}",
        description=(
            f"Plain-language guide to solving: {problem} for {audience}. "
            f"Official program terms: {commission}. "
            "No overpromises — see the official site before committing."
        ),
        price_usd=None,
        kind="service",
        tags=["cloud", "devops", "developers", "startups"],
    )

    sel_channels = list(channels or LAUNCH_CHANNELS)
    generated = repurpose(asset, channels=sel_channels)

    disclosure = (
        f"Affiliate disclosure: this post contains affiliate links for {name}. "
        f"We may earn a commission if you purchase via our links, at no extra cost to you. "
        f"Official commission terms: {commission}."
    )

    # The 5 content pieces (educational/comparison/usecase/tutorial/recommendation)
    # are the SEO/landing backbone; the repurposed channel assets above are the
    # social/short-form layer. Attribution is wired per channel.
    pieces = from_portfolio_opportunity(offer, verified_usage=False, now=now)

    assets: List[BatchAsset] = []
    for ch in sel_channels:
        content = generated.get(ch)
        if content is None:
            continue
        content_key = f"{opp_id}-{ch}"
        utm = _utm_for(ch, content_key)
        assets.append(BatchAsset(
            channel=ch,
            utm_source=utm["utm_source"],
            content=content,
            destination_status=LAUNCH_LINK_STATUS,
            destination_url=None,
            attribution={
                "source": utm["utm_source"],
                "campaign": LAUNCH_TRACKING.get("campaign", "first-revenue"),
                "content": content_key,
                "opportunity_id": opp_id,
            },
        ))

    return LaunchBatch(
        opportunity_id=opp_id,
        program_name=name,
        campaign=dict(LAUNCH_TRACKING),
        assets=assets,
        disclosure=disclosure,
        link_status=LAUNCH_LINK_STATUS,
        generated_at=_now_iso(now),
    )


def render_batch_json(batch: LaunchBatch) -> str:
    """Deterministic JSON rendering — the full publish-ready batch, honest."""
    return json.dumps({
        "opportunity_id": batch.opportunity_id,
        "program_name": batch.program_name,
        "campaign": batch.campaign,
        "link_status": batch.link_status,
        "disclosure": batch.disclosure,
        "assets": [
            {
                "channel": a.channel,
                "utm_source": a.utm_source,
                "attribution": a.attribution,
                "destination_status": a.destination_status,
                "destination_url": a.destination_url,
                "content": a.content,
            }
            for a in batch.assets
        ],
        "generated_at": batch.generated_at,
    }, ensure_ascii=False, indent=2)


def write_batch_file(batch: LaunchBatch,
                     output_dir: Optional[Path] = None) -> Path:
    """Persist the batch as a JSON file under launch_batches/ (git-friendly)."""
    out_dir = Path(output_dir) if output_dir else _DEFAULT_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = batch.generated_at or _now_iso()
    safe = stamp.replace(":", "-").split("+")[0]
    path = out_dir / f"launch_batch_{batch.opportunity_id}_{safe}.json"
    path.write_text(render_batch_json(batch), encoding="utf-8")
    return path