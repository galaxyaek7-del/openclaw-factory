"""Campaign links (UTM) and the measurement ledger.

Link convention, one per draft:
  utm_source   = platform (linkedin | tiktok | instagram | x)
  utm_medium   = social_organic
  utm_campaign = gf-<offer id, lower-case>-<YYYYMM>
  utm_content  = <draft id>

Metrics are recorded with their evidence class:
  OBSERVED  reported directly by an authoritative source (platform, Gumroad, network)
  DERIVED   calculated from recorded observations
  INFERRED  a plausible reading that is not proven
  UNKNOWN   not established
Environment is REAL or SIMULATION; the two never share a file, and a REAL
metric needs a source and evidence. Nothing is double-counted: a purchase is
attributed to at most one campaign, by its own recorded referrer/UTM.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parent.parent
REAL_LEDGER = ROOT / "data" / "social_distribution_metrics.jsonl"
SIM_LEDGER = ROOT / "data" / "social_distribution_metrics.simulation.jsonl"

PLATFORMS = ("linkedin", "tiktok", "instagram", "x", "pinterest")
MEDIUM = "social_organic"
EVIDENCE_CLASSES = ("OBSERVED", "DERIVED", "INFERRED", "UNKNOWN")
METRICS = ("content_created", "content_approved", "post_scheduled", "post_published", "publication_failed",
           "impressions", "reach", "video_views", "watch_time_s", "engagements", "outbound_clicks",
           "landing_sessions", "product_page_visits", "leads", "checkout_starts", "purchases",
           "affiliate_clicks", "commissions_confirmed", "refunds", "net_revenue_cents")
UTM_KEYS = ("utm_source", "utm_medium", "utm_campaign", "utm_content")


class TrackingError(ValueError):
    pass


def campaign_id(offer_id: str, when: datetime | None = None) -> str:
    when = when or datetime.now(timezone.utc)
    return f"gf-{re.sub(r'[^a-z0-9]+', '-', offer_id.lower()).strip('-')}-{when:%Y%m}"


def build_link(url: str, platform: str, campaign: str, content: str) -> str:
    if platform not in PLATFORMS:
        raise TrackingError(f"unknown platform {platform!r}")
    if not url or not url.startswith("https://"):
        raise TrackingError(f"destination must be an https URL, got {url!r}")
    parts = urlsplit(url)
    q = [(k, v) for k, v in parse_qsl(parts.query) if k not in UTM_KEYS]
    q += [("utm_source", platform), ("utm_medium", MEDIUM), ("utm_campaign", campaign), ("utm_content", content)]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), ""))


def parse_link(link: str) -> dict:
    parts = urlsplit(link)
    q = dict(parse_qsl(parts.query))
    return {"base": urlunsplit((parts.scheme, parts.netloc, parts.path, "", "")),
            **{k: q.get(k) for k in UTM_KEYS}}


def validate_link(link: str, *, platform: str, offer_url: str, offer_id: str) -> list:
    p = parse_link(link)
    problems = [f"missing {k}" for k in UTM_KEYS if not p[k]]
    if p["base"] != urlunsplit(urlsplit(offer_url)[:3] + ("", "")):
        problems.append(f"link points to {p['base']}, offer destination is {offer_url}")
    if p["utm_source"] and p["utm_source"] != platform:
        problems.append(f"utm_source {p['utm_source']} on a {platform} draft")
    if p["utm_medium"] and p["utm_medium"] != MEDIUM:
        problems.append(f"utm_medium {p['utm_medium']}")
    slug = re.sub(r"[^a-z0-9]+", "-", offer_id.lower()).strip("-")
    if p["utm_campaign"] and not p["utm_campaign"].startswith(f"gf-{slug}-"):
        problems.append(f"utm_campaign {p['utm_campaign']} does not belong to offer {offer_id}")
    return problems


def record_metric(*, environment: str, campaign: str, platform: str, metric: str, value, evidence_class: str,
                  source: str, evidence: str | None, method: str, limitations: str = "", ledger=None) -> dict:
    if environment not in ("REAL", "SIMULATION"):
        raise TrackingError("environment must be REAL or SIMULATION")
    if metric not in METRICS:
        raise TrackingError(f"unknown metric {metric!r}")
    if evidence_class not in EVIDENCE_CLASSES:
        raise TrackingError(f"evidence class must be one of {EVIDENCE_CLASSES}")
    if environment == "REAL" and evidence_class in ("OBSERVED", "DERIVED") and (not source or not evidence or len(evidence) < 10):
        raise TrackingError("a REAL observed/derived metric needs its source and evidence (10+ characters)")
    if evidence_class == "UNKNOWN" and value is not None:
        raise TrackingError("an UNKNOWN metric carries no value")
    default = REAL_LEDGER if environment == "REAL" else SIM_LEDGER
    path = Path(ledger or default)
    if environment == "REAL" and path.name.endswith(".simulation.jsonl"):
        raise TrackingError("refusing to write REAL metrics into a simulation ledger")
    if environment == "SIMULATION" and not path.name.endswith(".simulation.jsonl"):
        raise TrackingError("simulation metrics only go to a *.simulation.jsonl ledger")
    row = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "environment": environment,
           "campaign": campaign, "platform": platform, "metric": metric, "value": value,
           "evidence_class": evidence_class, "source": source, "evidence": evidence, "method": method,
           "limitations": limitations}
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def read_metrics(ledger=REAL_LEDGER) -> list:
    p = Path(ledger)
    if not p.exists():
        return []
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def attribute_purchases(purchases: list) -> dict:
    """Attribute each purchase to at most one campaign using ITS OWN recorded
    UTM/referrer; purchases without one stay unattributed (never guessed)."""
    by_campaign, unattributed, seen = {}, [], set()
    for p in purchases:
        pid = p.get("purchase_id")
        if not pid or pid in seen:
            continue  # duplicates are counted once
        seen.add(pid)
        camp = None
        for field in ("utm_campaign", "referrer"):
            v = p.get(field) or ""
            m = re.search(r"(?:utm_campaign=)?(gf-[a-z0-9-]+-\d{6})", v)
            if m:
                camp = m.group(1)
                break
        if camp:
            by_campaign.setdefault(camp, []).append(pid)
        else:
            unattributed.append(pid)
    return {"by_campaign": {k: len(v) for k, v in by_campaign.items()}, "unattributed": len(unattributed),
            "evidence_class": "DERIVED", "limitation": "click-to-purchase only where the purchase carries the campaign; "
                                                      "correlation with posting is not causation"}
