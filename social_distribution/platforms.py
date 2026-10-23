"""Platform capability declarations and live readiness for the four platforms.

Declarations come from the platforms' documentation as checked on 2026-10-23
(sources listed per platform; third-party figures are marked as such).
Readiness is computed from what is actually present on this machine: credential
NAMES in the environment (values are never read into reports) and recorded
evidence. Nothing here makes a network call.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKED_ON = "2026-10-23"

# connection states, weakest first
NOT_CONNECTED = "NOT_CONNECTED"            # no app, no credentials
CREDENTIALS_PRESENT = "CREDENTIALS_PRESENT"  # keys exist; posting never proven
BLOCKED_SPEND = "BLOCKED_SPEND"            # posting is possible only by paying
PUBLISH_VERIFIED = "PUBLISH_VERIFIED"      # a real post confirmed by read-back (none yet)
CONNECTED_VIA_METRICOOL = "CONNECTED_VIA_METRICOOL"  # account linked in Metricool (read-only proof)

PLATFORMS = {
    "linkedin": {
        "name": "LinkedIn",
        "formats": ["text_post", "text_with_link", "image_post", "document_post"],
        "account": "LinkedIn member (personal profile); company pages need separate organization permissions",
        "permissions": ["w_member_social via the 'Share on LinkedIn' product on a LinkedIn developer app"],
        "operations": ["create post on the authenticated member's feed"],
        "prerequisites": ["LinkedIn developer app", "Share on LinkedIn product added", "OAuth 2.0 member token (about 60 days)"],
        "constraints": {"text_max_chars": 3000},
        "rate_limits": "per-app and per-member daily limits shown in the developer portal (not verified here)",
        "scheduling": "no native scheduling through this API; schedule on our side",
        "verification": "read the created post id back; public visibility needs a fetch of the post URL",
        "manual_steps": ["create the developer app", "authorize the member token", "store token names in .env"],
        "env_keys": ["LINKEDIN_ACCESS_TOKEN", "LINKEDIN_PERSON_URN"],
        "cost": "free API",
        "sources": ["https://developer.linkedin.com/documents/share-api",
                    "https://learn.microsoft.com/linkedin/consumer/integrations/self-serve/share-on-linkedin"],
    },
    "tiktok": {
        "name": "TikTok",
        "formats": ["vertical_video", "photo_post"],
        "account": "TikTok account authorizing a TikTok for Developers app",
        "permissions": ["video.publish (Content Posting API, Direct Post) or video.upload (draft to inbox)"],
        "operations": ["direct post video", "upload video to the creator's inbox as a draft"],
        "prerequisites": ["TikTok for Developers app", "Content Posting API product", "app audit for public posts"],
        "constraints": {"unaudited_client": "posts are forced to SELF_ONLY (private); public publish fails with unaudited_client_can_only_post_to_private_accounts",
                        "caption_max_chars": 2200},
        "rate_limits": "unaudited Direct Post: few users per 24 h (third-party report, unverified)",
        "scheduling": "none in API; schedule on our side",
        "verification": "publish status endpoint by publish_id",
        "manual_steps": ["create the developer app", "pass the audit for public posting", "or upload by hand in the TikTok app"],
        "env_keys": ["TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_ACCESS_TOKEN"],
        "cost": "free API; audit takes weeks (third-party estimate)",
        "sources": ["https://developers.tiktok.com/doc/content-posting-api-reference-direct-post",
                    "https://developers.tiktok.com/docs/en/content-posting-api-get-started"],
    },
    "instagram": {
        "name": "Instagram",
        "formats": ["image_post", "carousel", "reel"],
        "account": "Instagram professional account (Business or Creator)",
        "permissions": ["instagram content publish permission on a Meta app (Instagram Login or Facebook Login path)"],
        "operations": ["create media container", "publish container", "check content_publishing_limit"],
        "prerequisites": ["Meta developer app", "professional Instagram account", "media hosted at a public URL"],
        "constraints": {"image_format": "JPEG only", "media": "fetched by Meta from a public URL",
                        "posts_per_24h": "100 API-published posts (docs also show a stale 50)", "caption_max_chars": 2200,
                        "links_in_caption": "not clickable"},
        "rate_limits": "100 published posts per 24 h moving window",
        "scheduling": "none in API; schedule on our side",
        "verification": "read the media id back and its permalink",
        "manual_steps": ["convert to a professional account", "create the Meta app", "host images publicly"],
        "env_keys": ["INSTAGRAM_ACCESS_TOKEN", "INSTAGRAM_USER_ID"],
        "cost": "free API",
        "sources": ["https://developers.facebook.com/docs/instagram-platform/content-publishing"],
    },
    "pinterest": {
        "name": "Pinterest",
        "formats": ["image_pin"],
        "account": "Pinterest account galaxyaek7, connected to Metricool brand 6965613",
        "permissions": ["Metricool connector post creation (Claude Code permission rule required)"],
        "operations": ["schedule a pin through Metricool (review flow)"],
        "prerequisites": ["a public image (the product cover)", "a destination link"],
        "constraints": {"title_max_chars": 100, "description_max_chars": 500},
        "rate_limits": "Metricool plan limits (not verified)",
        "scheduling": "native in Metricool",
        "verification": "Metricool getScheduledPosts, then the public pin URL",
        "manual_steps": ["allow the Metricool post tool in Claude Code permissions"],
        "env_keys": [],
        "via": "metricool",
        "cost": "free on the current Metricool plan (review flow availability unverified)",
        "sources": ["data/metricool_brand.json"],
    },
    "x": {
        "name": "X",
        "formats": ["text_post", "thread", "image_post"],
        "account": "X account authorizing a developer app (@AekGrafat per data/channel_x_assessment.json)",
        "permissions": ["OAuth 1.0a user context with write access"],
        "operations": ["create post (POST /2/tweets)"],
        "prerequisites": ["developer app", "pay-per-use credits for writes"],
        "constraints": {"text_max_chars": 280, "url_weight": 23},
        "rate_limits": "per-endpoint limits plus credit balance",
        "scheduling": "none in API; schedule on our side",
        "verification": "GET the post id back",
        "manual_steps": ["buy credits (spend: not authorized)", "or post by hand in the X app"],
        "env_keys": ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"],
        "cost": "pay-per-use: about $0.015 per post, about $0.20 when it contains a link (third-party summaries of docs.x.com, 2026)",
        "evidence": ["data/x_post_queue.json: a post attempt returned HTTP 402 credits-depleted",
                     "data/channel_x_assessment.json: credentials READ-OK, posting untested"],
        "sources": ["https://postproxy.dev/blog/x-api-pricing-2026",
                    "https://www.medianama.com/2026/02/223-x-developer-api-pricing-pay-per-use-model/"],
    },
}


def _env_names(env_path=ROOT / ".env"):
    names = set(k for k, v in os.environ.items() if v)
    try:
        for line in Path(env_path).read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                if v.strip():
                    names.add(k.strip())
    except OSError:
        pass
    return names


def _x_spend_blocked(root=ROOT):
    try:
        q = json.loads((Path(root) / "data" / "x_post_queue.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return any("402" in str(i.get("block_reason", "")) for i in q)


def _metricool(root=ROOT):
    try:
        return json.loads((Path(root) / "data" / "metricool_brand.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def readiness(env_names=None, root=ROOT) -> dict:
    """Per platform: connection state, missing credential names, publish mode."""
    names = _env_names() if env_names is None else set(env_names)
    mc = _metricool(root)
    out = {}
    for key, p in PLATFORMS.items():
        missing = [k for k in p["env_keys"] if k not in names]
        if key in mc.get("connected_networks", {}):
            blocked = str(mc.get("post_creation", "")).startswith("BLOCKED")
            out[key] = {"name": p["name"], "state": CONNECTED_VIA_METRICOOL, "missing_credentials": [],
                        "account": mc["connected_networks"][key], "brand_id": mc.get("brand_id"),
                        "publish_mode": "MANUAL_HANDOFF" if blocked else "METRICOOL",
                        "why": ("connected through Metricool; post creation needs a Claude Code permission rule"
                                if blocked else "connected through Metricool")}
            continue
        if key == "x" and not missing and _x_spend_blocked(root):
            state = BLOCKED_SPEND
        elif not missing:
            state = CREDENTIALS_PRESENT
        else:
            state = NOT_CONNECTED
        out[key] = {"name": p["name"], "state": state, "missing_credentials": missing,
                    "publish_mode": "MANUAL_HANDOFF",  # no adapter has a real transport yet
                    "why": {NOT_CONNECTED: "no app or credentials on this machine",
                            CREDENTIALS_PRESENT: "credentials exist but no publish transport is built or proven",
                            BLOCKED_SPEND: "posting needs paid API credits; TOTAL_NEW_SPEND=$0"}[state]}
    return out
