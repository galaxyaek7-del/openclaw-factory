"""Build and validate Metricool review-flow posts (Pinterest first), and keep a
local record of every submission attempt.

The Metricool connector is called by the agent (an MCP tool), not by this
module: nothing here makes a network call. This module decides whether a call
may be made and what exactly it sends.

Schema, as observed from the connector's own documentation and validation
errors (2026-10-24; no guesses beyond these):
  createScheduledPostForReview(blogId, date, info, reviewers, approvalSystem, notify)
    date            ISO 8601 with offset, must be in the future
    approvalSystem  "any" | "all" | "optional"  ("optional" auto-publishes unless rejected)
    info (JSON)     text, providers[{network}], media[url], autoPublish,
                    publicationDate {dateTime (local, no offset), timezone (IANA)}  <- required
                    pinterestData {boardId, pinTitle, pinLink}                     <- all required
The connector has no tool to list or create Pinterest boards, so a boardId can
only come from a recorded source (the board's own Pinterest data), never made up.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from social_distribution import tracking

ROOT = Path(__file__).resolve().parent.parent
BRAND_FILE = ROOT / "data" / "metricool_brand.json"
ATTEMPTS = ROOT / "data" / "metricool_submissions.jsonl"

APPROVAL_SYSTEMS = ("any", "all", "optional")
SAFE_APPROVAL = ("any", "all")       # publication needs a person's approval
PIN_TITLE_MAX, PIN_TEXT_MAX = 100, 500
BOARD_ID = re.compile(r"^\d{10,20}$")  # Pinterest board ids are long numeric strings


class PostRejected(ValueError):
    """The post must not be sent; the message says why."""


def brand(path=BRAND_FILE) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_pinterest_review_post(*, offer: dict, board_id: str, when_local: str, tz: str, reviewers: str,
                                approval_system: str = "any", brand_record: dict | None = None,
                                now: datetime | None = None, allow_auto_approval: bool = False,
                                expected_brand_id=None) -> dict:
    """The exact createScheduledPostForReview arguments, or PostRejected."""
    b = brand_record if brand_record is not None else brand()
    problems = []
    if not str(b.get("brand_id", "")).isdigit():
        problems.append("recorded Metricool brand id is missing or not numeric")
    elif expected_brand_id is not None and str(expected_brand_id) != str(b["brand_id"]):
        problems.append(f"brand id {expected_brand_id} does not match the connected brand {b['brand_id']}")
    if "pinterest" not in (b.get("connected_networks") or {}):
        problems.append("Pinterest is not connected to the recorded Metricool brand")
    if approval_system not in APPROVAL_SYSTEMS:
        problems.append(f"approvalSystem must be one of {APPROVAL_SYSTEMS}")
    elif approval_system not in SAFE_APPROVAL:
        # 'optional' publishes unless someone rejects it: that is publication, so it
        # needs both an explicit request and the factory's live-publish switch.
        from channels.write_gate import check_platform_write
        gate = check_platform_write("pinterest", "auto_approved_post")
        if not allow_auto_approval or not gate.allowed:
            problems.append("approvalSystem 'optional' auto-publishes; it needs allow_auto_approval and an open write gate "
                            f"({gate.reason})")
    if not board_id or not BOARD_ID.match(str(board_id)):
        problems.append("boardId missing or not a Pinterest board id (a long number from the board's own data)")
    if not reviewers or "@" not in reviewers:
        problems.append("at least one reviewer email is required")
    try:
        zone = ZoneInfo(tz)
        local = datetime.fromisoformat(when_local)
        if local.tzinfo is not None:
            raise ValueError("when_local must be a local time without an offset")
        aware = local.replace(tzinfo=zone)
        if aware <= (now or datetime.now(timezone.utc)):
            problems.append(f"the publication time {aware.isoformat()} is not in the future")
    except Exception as exc:  # noqa: BLE001 -- any bad date or zone is a refusal
        problems.append(f"invalid publication time or timezone: {exc}")
        aware = None
    if offer.get("eligibility", {}).get("status") != "ELIGIBLE":
        problems.append("offer is not eligible: " + "; ".join(offer.get("eligibility", {}).get("reasons", [])))
    if not offer.get("cover_url"):
        problems.append("offer has no public cover image")
    title = offer.get("title") or ""
    text = (offer.get("pin_text") or "").strip()
    if not title or len(title) > PIN_TITLE_MAX:
        problems.append(f"pin title must be 1-{PIN_TITLE_MAX} characters")
    if not text or len(text) > PIN_TEXT_MAX:
        problems.append(f"pin text must be 1-{PIN_TEXT_MAX} characters")
    price = offer.get("price_cents")
    for amount in re.findall(r"\$\s?(\d[\d,]*(?:\.\d{2})?)", text):
        if price is None or abs(float(amount.replace(",", "")) * 100 - price) > 0.5:
            problems.append(f"amount ${amount} in the text does not match the offer price")
    link = None
    if offer.get("url"):
        link = tracking.build_link(offer["url"], "pinterest", tracking.campaign_id(offer["offer_id"]),
                                   f"{offer['offer_id'].lower()}-pinterest-v1")
        problems += tracking.validate_link(link, platform="pinterest", offer_url=offer["url"], offer_id=offer["offer_id"])
    else:
        problems.append("offer has no destination URL")
    if problems:
        raise PostRejected("; ".join(problems))
    info = {"text": text, "providers": [{"network": "pinterest"}], "media": [offer["cover_url"]], "autoPublish": True,
            "publicationDate": {"dateTime": local.isoformat(timespec="seconds"), "timezone": tz},
            "pinterestData": {"boardId": str(board_id), "pinTitle": title, "pinLink": link}}
    return {"blogId": str(b["brand_id"]), "date": aware.isoformat(timespec="seconds"), "info": json.dumps(info, ensure_ascii=False),
            "reviewers": reviewers, "approvalSystem": approval_system, "notify": True}


def fingerprint(call: dict) -> str:
    info = json.loads(call["info"])
    key = (call["blogId"], info["pinterestData"]["pinLink"], info["publicationDate"]["dateTime"], info["pinterestData"]["boardId"])
    return hashlib.sha256(json.dumps(key).encode()).hexdigest()[:16]


def duplicate_of(call: dict, scheduled_posts: list, attempts_path=ATTEMPTS) -> str | None:
    """A reason this post would be a duplicate, from Metricool's own list and our record."""
    info = json.loads(call["info"])
    link = info["pinterestData"]["pinLink"].split("?")[0]
    for p in scheduled_posts or []:
        blob = json.dumps(p, ensure_ascii=False)
        if link in blob and "pinterest" in blob.lower():
            return f"Metricool already has a scheduled Pinterest post for {link}"
    fp = fingerprint(call)
    for a in read_attempts(attempts_path):
        if a.get("fingerprint") == fp and a.get("created") is True:
            return f"this exact post was already created (post id {a.get('post_id')})"
    return None


def record_attempt(call: dict, *, created: bool, response: str, post_id=None, verified_by: str, attempts_path=ATTEMPTS) -> dict:
    row = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "fingerprint": fingerprint(call),
           "blogId": call["blogId"], "date": call["date"], "approvalSystem": call["approvalSystem"],
           "created": created, "post_id": post_id, "response": response[:500], "verified_by": verified_by}
    Path(attempts_path).parent.mkdir(parents=True, exist_ok=True)
    with open(attempts_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def read_attempts(attempts_path=ATTEMPTS) -> list:
    p = Path(attempts_path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out
