"""Platform-native drafts from an offer's own facts, plus content QA.

Copy comes from content_generation.repurposing_engine (deterministic, no LLM,
no invented facts); this module picks the right builder per platform, adds the
tracked link, frames free content honestly (no price line), and attaches the
visual a platform needs only when it really exists. Every draft carries a QA
result; a draft with any QA issue cannot be approved.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from content_generation import repurposing_engine as rep
from social_distribution import tracking

ROOT = Path(__file__).resolve().parent.parent
LIMITS = {"linkedin": 3000, "instagram": 2200, "tiktok": 2200, "x": 280}
FORMAT = {"linkedin": "text_with_link", "x": "text_post", "instagram": "carousel", "tiktok": "vertical_video"}
FORBIDDEN = ("5 star", "5-star", "customers love", "trusted by", "best-selling", "#1 ", "guaranteed",
             "testimonial", "limited time", "only today", "last chance", "act now")
PLACEHOLDER = re.compile(r"\[(?:TODO|TBD|INSERT|PLACEHOLDER)[^\]]*\]|\{\{[^}]+\}\}|lorem ipsum", re.I)
# data-gap markers that leaked into public copy (found on 13 live guide pages, 2026-10-23)
RESIDUE = re.compile(r"\bUNKNOWN\b|not captured at this granularity|requires a separate real customer-discovery pass")


def _price(o):
    return None if o.get("price_cents") is None else o["price_cents"] / 100


def _asset(o, link):
    return rep.Asset(title=o["title"], description=o.get("description") or o.get("problem") or o["title"],
                     price_usd=_price(o), kind="product" if o["type"] == "digital_product" else "asset",
                     tags=list(o.get("tags") or []), url=link, status="live")


def _sentences(text, n):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text or "") if len(s.strip()) > 20][:n]


def _fit_lines(text, max_chars):
    """Leading whole lines of text up to max_chars (a heading left dangling at
    the end, such as "What's included", is dropped with its missing list)."""
    out = []
    for ln in (text or "").splitlines():
        if len("\n".join(out + [ln])) > max_chars:
            break
        out.append(ln)
    while out and not out[-1].startswith("- ") and len(out[-1]) < 40 and not out[-1].endswith((".", "!", "?")):
        out.pop()
    return "\n".join(out) or rep._fit_sentences(text, max_chars)


def _video_for(offer, offers):
    """A rendered video that names this offer in its purpose, if one exists."""
    for v in offers or []:
        if v["type"] == "media_asset" and offer["offer_id"] in (v.get("description") or ""):
            return v
    return None


def draft(offer: dict, platform: str, *, campaign: str, offers=None) -> dict:
    content_id = f"{offer['offer_id']}-{platform}-v1".lower()
    link = tracking.build_link(offer["url"], platform, campaign, content_id) if offer.get("url") else None
    paid = offer.get("price_cents") is not None
    # only guides and blog posts are free to read; other pages get a neutral label
    free = offer.get("subtype") in ("guide", "blog")
    label = "Free to read" if free else "Details"
    a = _asset(offer, link)
    visual = None
    if platform == "linkedin":
        if paid:
            # whole lines of the listing only, never a word cut in half, title on top
            short = rep.Asset(**dict(a.__dict__, description=_fit_lines(a.description, 1300)))
            body = f"{offer['title']}\n\n" + rep.linkedin_post(short)["body"]
        else:
            facts = " ".join(_sentences(offer.get("description"), 3)) or offer.get("problem")
            body = f"{offer['title']}\n\n{facts}\n\n{label}: {link}"
        fields = {"text": body}
    elif platform == "x":
        if paid:
            text = rep.x_post(a)["text"]
        else:
            room = 280 - rep.x_weighted_length(f"{offer['title']}: \n{label}: {link}")
            text = f"{offer['title']}: {rep._truncate(offer.get('problem') or '', max(0, room))}\n{label}: {link}"
        fields = {"text": text}
    elif platform == "instagram":
        slides = [offer["title"]] + _sentences(offer.get("description"), 3) + \
                 ([f"{rep._price_line(a)}. Link in bio."] if paid else ["Free. Link in bio."])
        fields = {"text": rep.instagram_caption(a)["caption"], "carousel_slides": slides}
        visual = {"kind": "carousel_images", "status": "NOT_RENDERED",
                  "note": "slides are text plans; images must be rendered as JPEG and hosted publicly"}
    elif platform == "tiktok":
        s = rep.short_video_script(a)
        # The engine's "Need <first clause>?" hook breaks on imperative openings
        # ("Need See every week's...?"); the offer's own first sentence is the hook.
        hook = rep._fit_sentences(offer.get("problem") or offer["title"], 150)
        s = dict(s, hook=hook)
        fields = {"text": f"{offer['title']}. {rep._price_line(a) if paid else 'Free'}. Link in bio. {s['hashtags']}",
                  "script": s, "scenes": [hook] + _sentences(offer.get("description"), 3)[1:] + [s["cta"]]}
        v = _video_for(offer, offers)
        visual = ({"kind": "video", "status": "RENDERED", "path": v.get("media_path"), "rights": v["rights_status"],
                   "offer": v["offer_id"]} if v and v.get("media_path") else
                  {"kind": "video", "status": "NOT_RENDERED", "note": "no rendered video for this offer"})
    else:
        raise ValueError(f"unknown platform {platform}")
    d = {"draft_id": content_id, "offer_id": offer["offer_id"], "arm": offer["arm"], "platform": platform,
         "format": FORMAT[platform], "campaign": campaign, "link": link, "language": offer.get("language", "en"),
         "fields": fields, "visual": visual, "generated_by": "repurposing_engine templates (deterministic)",
         "synthetic_media": bool(visual and visual.get("kind") == "video"),
         "offer_snapshot": {"url": offer.get("url"), "price_cents": offer.get("price_cents"), "title": offer["title"]}}
    d["content_sha256"] = hashlib.sha256(json.dumps(d["fields"], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    d["qa"] = qa(d, offer)
    return d


def _generated_part(text: str, offer: dict) -> str:
    """The text minus anything copied verbatim from the listing itself. The
    listing's own sentences are approved facts (including honest disclaimers
    such as "No result is guaranteed" and worked-example amounts); the claim
    and amount checks apply to what this module added."""
    desc = offer.get("description") or ""
    for line in sorted(desc.splitlines(), key=len, reverse=True):
        for piece in [line] + _sentences(line, 99):
            if len(piece) > 15:
                text = text.replace(piece, " ")
    # a whole generated line found inside the listing (e.g. the engine's
    # "first sentence" without its full stop) is the listing's own text
    text = "\n".join("" if len(ln.strip()) > 15 and ln.strip() in desc else ln for ln in text.split("\n"))
    # listing text cut short with an ellipsis is still the listing's own text
    for m in re.finditer(r"([^\n]{16,}?)…", text):
        before = m.group(1)
        # the longest tail of the cut text that the listing really contains
        for i in range(len(before) - 16 + 1):
            if before[i:].strip() in desc:
                text = text.replace(before[i:] + "…", " ")
                break
    return text


def _strings(v):
    """Every string inside a field, flattened (str() of a dict would wrap the
    listing's text in quotes and braces and hide it from the verbatim check)."""
    if isinstance(v, dict):
        return [s for x in v.values() for s in _strings(x)]
    if isinstance(v, (list, tuple)):
        return [s for x in v for s in _strings(x)]
    return [str(v)]


def qa(d: dict, offer: dict) -> dict:
    issues, text = [], d["fields"].get("text", "")
    every = "\n".join(_strings(d["fields"]))
    generated = _generated_part(every, offer)
    if offer["eligibility"]["status"] != "ELIGIBLE":
        issues.append(f"offer not eligible: {'; '.join(offer['eligibility']['reasons'])}")
    if d["platform"] not in offer.get("platforms", []):
        issues.append(f"{d['platform']} is not a suitable platform for a {offer['type']}")
    length = rep.x_weighted_length(text) if d["platform"] == "x" else len(text)
    if length > LIMITS[d["platform"]]:
        issues.append(f"text is {length} characters, limit {LIMITS[d['platform']]}")
    if not d.get("link"):
        issues.append("no destination link")
    else:
        issues += tracking.validate_link(d["link"], platform=d["platform"], offer_url=offer["url"], offer_id=offer["offer_id"])
        if d["platform"] in ("linkedin", "x") and d["link"] not in text:
            issues.append("tracked link missing from the post text")
    price = offer.get("price_cents")
    for amount in re.findall(r"\$\s?(\d[\d,]*(?:\.\d{2})?)", generated):
        if price is None or abs(float(amount.replace(",", "")) * 100 - price) > 0.5:
            issues.append(f"amount ${amount} does not match the offer price")
    low = generated.lower()
    issues += [f"forbidden claim {f!r}" for f in FORBIDDEN if f in low]
    try:
        from affiliate.content_qa import _BANNED_PHRASES
        issues += [f"banned phrase {p!r}" for p in _BANNED_PHRASES if p in low]
    except ImportError:
        pass
    if PLACEHOLDER.search(every):
        issues.append("unfilled placeholder")
    if RESIDUE.search(every):
        issues.append(f"data-gap text in copy: {RESIDUE.search(every).group(0)!r}")
    if "validation concept" in low and offer.get("primary_state") == "PUBLIC_LISTING_VERIFIED":
        issues.append("calls a verified live listing a 'validation concept'")
    try:
        import brand_dna
        b = brand_dna.validate_customer_facing_text(every)
        issues += [f"brand check failed: {c}" for c in b.get("failed_checks", [])]
    except Exception as exc:  # noqa: BLE001 -- a broken checker must block, not pass
        issues.append(f"brand check unavailable: {type(exc).__name__}")
    v = d.get("visual")
    if d["platform"] == "tiktok" and (not v or v.get("status") != "RENDERED"):
        issues.append("TikTok needs a rendered video; none exists for this offer")
    elif d["platform"] == "tiktok" and v.get("rights") != "CLEARED":
        issues.append(f"video rights {v.get('rights')}")
    if d["platform"] == "instagram" and (not v or v.get("status") != "RENDERED"):
        issues.append("Instagram needs rendered JPEG images; only slide text exists")
    return {"passed": not issues, "issues": issues, "checked": ["eligibility", "platform fit", "length", "tracked link",
                                                                  "price consistency", "forbidden claims", "placeholders",
                                                                  "brand_dna", "visual asset and rights"]}
