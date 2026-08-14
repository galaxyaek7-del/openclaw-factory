"""Galaxy Forge — Content Repurposing Engine (ONE ASSET → MANY CHANNELS).

Directive (2026-08-14): "أي أصل قوي يتم إنتاجه يجب أن يستطيع النظام تحويله
تلقائيًا إلى Product page / short video / TikTok-Reel-Short / LinkedIn post /
X post / Facebook post / Pinterest asset / email-newsletter asset / SEO
content." — NOT manual per-platform content.

This module is deterministic and zero-cost by design: it repurposes the
facts of a single real asset (title, description, price, source doc) into
ready-to-use text blocks for every distribution channel. It NEVER calls an
LLM, never invents facts, and never fabricates demand — every string is
derived from the asset's own real fields plus honest, static framing.

Everything here is DISCOVERY-side material: an output is a draft that a
human (or a later, founder-approved automation) decides to publish. Nothing
in this module posts externally.

Output is deterministic given the same asset dict, so it is fully unit-
testable and safe to run in CI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Asset contract
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = ("title", "description")


class RepurposingError(ValueError):
    """A missing/invalid asset field — never a fabricated value."""


@dataclass
class Asset:
    """The single real source asset the engine repurposes. Fields mirror
    what schemas/product.py and the validation concept docs already carry.

    `kind` drives channel framing (product vs service vs asset) so the
    repurposed copy stays honest about what the thing actually is."""

    title: str
    description: str
    price_usd: Optional[float] = None
    source_doc: Optional[str] = None
    kind: str = "product"  # "product" | "service" | "asset" | "book"
    tags: List[str] = field(default_factory=list)

    def validate(self) -> None:
        for f in REQUIRED_FIELDS:
            value = getattr(self, f)
            if not value or not str(value).strip():
                raise RepurposingError(f"asset missing required field: {f}")

    @classmethod
    def from_product(cls, product) -> "Asset":
        """Adapt a schemas.product.Product (distributor.py's input) into a
        repurposable Asset without coupling this module to that schema."""
        return cls(
            title=getattr(product, "title", "") or "",
            description=getattr(product, "description", "") or "",
            price_usd=getattr(product, "price_usd", None),
            source_doc=getattr(product, "file_path", None),
            kind="book" if getattr(product, "product_type", "book") == "book" else "product",
            tags=list(getattr(product, "tags", None) or []),
        )


# ---------------------------------------------------------------------------
# Channel generators — each returns a dict with one or more text fields.
# All deterministic; no randomness, no network, no external calls.
# ---------------------------------------------------------------------------

def _price_line(asset: Asset) -> str:
    if asset.price_usd is None:
        return "Pricing: see product page."
    if asset.price_usd == int(asset.price_usd):
        return f"${int(asset.price_usd)}"
    return f"${asset.price_usd:,.2f}"


def product_page(asset: Asset) -> Dict[str, str]:
    asset.validate()
    price = _price_line(asset)
    return {
        "title": asset.title,
        "description": asset.description,
        "price": price,
        "call_to_action": f"Get {asset.title} — {price}",
    }


def short_video_script(asset: Asset) -> Dict[str, str]:
    """A 20-30s short-video script (TikTok/Reel/Short). Hooks with the pain
    the asset's own description claims to solve; ends with a CTA. No facts
    beyond what the description already states."""
    asset.validate()
    first_sentence = asset.description.strip().split(".")[0].strip() or asset.title
    pain = _pain_from_description(asset)
    price = _price_line(asset)
    if _has_pain_marker(asset):
        hook = f"Stop {pain} — there's a better way."
    else:
        hook = f"Need {pain}?"
    return {
        "hook": hook,
        "body": first_sentence,
        "cta": f"Grab the {asset.kind} — {price}. Link in bio.",
        "hashtags": " ".join(f"#{t.replace(' ', '')}" for t in asset.tags[:5]) or "#productivity",
        "duration_seconds": 25,
    }


def linkedin_post(asset: Asset) -> Dict[str, str]:
    asset.validate()
    price = _price_line(asset)
    body = (
        f"{asset.description}\n\n"
        f"{price} — one-time, no subscription, no seat minimum.\n"
        f"This is a {asset.kind} (validation concept — not a launched product)."
    )
    return {
        "headline": asset.title,
        "body": body,
        "cta": "Comments and DMs welcome.",
        "post_length_chars": len(body),
    }


def x_post(asset: Asset) -> Dict[str, str]:
    asset.validate()
    price = _price_line(asset)
    return {
        "text": f"{asset.title}: {_truncate(asset.description, 200)} {price} #galaxyforge",
        "max_chars": 280,
    }


def facebook_post(asset: Asset) -> Dict[str, str]:
    asset.validate()
    price = _price_line(asset)
    return {
        "text": f"{asset.title}\n\n{asset.description}\n\n{price}",
        "cta": "Learn more.",
    }


def pinterest_asset(asset: Asset) -> Dict[str, str]:
    asset.validate()
    return {
        "pin_title": asset.title,
        "pin_description": _truncate(asset.description, 200),
        "image_alt_text": f"{asset.title} — {asset.kind}",
    }


def email_newsletter(asset: Asset) -> Dict[str, str]:
    asset.validate()
    price = _price_line(asset)
    return {
        "subject": f"{asset.title}",
        "preview_text": _truncate(asset.description, 90),
        "body": (
            f"Hi,\n\n{asset.description}\n\n"
            f"{price}. No subscription. Instant delivery.\n\n"
            f"— Galaxy Forge"
        ),
    }


def seo_content(asset: Asset) -> Dict[str, str]:
    asset.validate()
    keywords = [t.replace("-", " ").strip() for t in asset.tags[:5] if t.strip()]
    return {
        "meta_title": asset.title,
        "meta_description": _truncate(asset.description, 155),
        "keywords": ", ".join(keywords) if keywords else asset.title.lower(),
        "h1": asset.title,
        "body_preview": _truncate(asset.description, 300),
    }


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

# Registry of channel builders. Adding a channel = adding one function here
# and one name in this dict — the engine and its tests stay unchanged.
CHANNEL_BUILDERS = {
    "product_page": product_page,
    "short_video_script": short_video_script,
    "linkedin_post": linkedin_post,
    "x_post": x_post,
    "facebook_post": facebook_post,
    "pinterest_asset": pinterest_asset,
    "email_newsletter": email_newsletter,
    "seo_content": seo_content,
}


def repurpose(asset: Asset, channels: Optional[List[str]] = None) -> Dict[str, Dict[str, str]]:
    """Repurpose ONE asset into every requested channel (all by default).

    Deterministic: same asset -> same output. Never raises for a missing
    channel name; unknown channels are skipped (honest: we don't fabricate
    a variant we can't produce)."""
    asset.validate()
    names = [c for c in channels or CHANNEL_BUILDERS.keys()]
    out = {}
    for name in names:
        builder = CHANNEL_BUILDERS.get(name)
        if builder is None:
            continue
        out[name] = builder(asset)
    return out


def repurpose_all(asset: Asset) -> Dict[str, Dict[str, str]]:
    return repurpose(asset)


# ---------------------------------------------------------------------------
# Helpers (pure text; no external state)
# ---------------------------------------------------------------------------

def _truncate(text: str, max_chars: int) -> str:
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def _pain_from_description(asset: Asset) -> str:
    """Extract a short pain phrase from the description's first clause.
    Falls back to the title when the description is empty. Pure text
    manipulation — never invents a pain the asset doesn't claim."""
    desc = (asset.description or "").strip()
    lower = desc.lower()
    for marker in ("without ", "while ", "instead of "):
        idx = lower.find(marker)
        if idx != -1:
            candidate = desc[idx + len(marker):].split(".")[0].strip()
            if candidate:
                return candidate
    if desc:
        # No pain marker: use the short first subject phrase so the hook
        # stays grammatical ("Need <subject>?").
        first_clause = desc.split(".")[0].strip()
        words = first_clause.split()
        if len(words) > 8:
            return " ".join(words[:8]).rstrip(",;") + "…"
        return first_clause
    return asset.title


def _has_pain_marker(asset: Asset) -> bool:
    """True when the description names a pain explicitly via one of the
    recognized markers, so the hook can use the "Stop <pain>" framing
    without inventing anything."""
    desc = (asset.description or "").lower()
    return any(marker in desc for marker in ("without ", "while ", "instead of "))
