#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Secret-free outbound-link registry (local operational record).

Why this exists: click ledgers record WHAT was clicked; nothing records
WHICH content asset carries WHICH program link on WHICH channel under WHICH
campaign, nor when each link was last verified. This registry closes exactly
that gap — and stores merchant DOMAINS only, never tokenized URLs, IDs, or
credentials. A registry entry can never leak a secret because none is stored.

Writes only to data/affiliate_links.jsonl (operational registry — never
financial truth). All functions pure except register_link (append-only).
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY_PATH = _FACTORY_ROOT / "data" / "affiliate_links.jsonl"


def _now():
    return datetime.now(timezone.utc).isoformat()


def register_link(program, content_asset, channel, campaign, cta,
                  merchant_domain, registry_path=None) -> dict:
    """Append one link-usage record. `merchant_domain` must be a bare domain
    (e.g. "systeme.io") — any value containing query strings, tokens, or
    credential-like material is rejected outright."""
    if not all(isinstance(v, str) and v.strip()
               for v in (program, content_asset, channel, campaign, cta, merchant_domain)):
        return {"ok": False, "error": "all fields required as non-empty strings"}
    if any(tok in merchant_domain for tok in ("?", "&", "=", "sa_", "token", "key", "aff_id")):
        return {"ok": False, "error": "merchant_domain must be a bare domain, never a tokenized URL"}
    if len(merchant_domain) > 253 or " " in merchant_domain:
        return {"ok": False, "error": "invalid domain"}
    entry = {"program": program.strip(), "content_asset": content_asset.strip(),
             "channel": channel.strip(), "campaign": campaign.strip(),
             "cta": cta.strip(), "merchant_domain": merchant_domain.strip().lower(),
             "registered_at": _now(), "last_verified": None, "http_status": None}
    path = Path(registry_path) if registry_path else DEFAULT_REGISTRY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return {"ok": True, "entry": entry}


def list_links(registry_path=None) -> list:
    """Read-only: every registered link-usage record (skips corrupt lines)."""
    path = Path(registry_path) if registry_path else DEFAULT_REGISTRY_PATH
    out = []
    if not path.exists():
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def flag_link(campaign: str, reason: str, registry_path=None) -> dict:
    """Append a FLAG event row (link stays registered; distribution must
    treat flagged campaigns as ISOLATED until re-verified). Read-back
    helpers ignore FLAG rows for counts (they are events, not links)."""
    path = Path(registry_path) if registry_path else DEFAULT_REGISTRY_PATH
    row = {"event": "FLAG", "campaign": campaign, "reason": reason,
           "flagged_at": _now()}
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"ok": True, "campaign": campaign}


def flagged_campaigns(registry_path=None) -> list:
    return [r.get("campaign") for r in list_links(registry_path)
            if r.get("event") == "FLAG"]


def active_links(registry_path=None) -> list:
    """Link-usage records minus FLAG event rows (counts stay honest)."""
    flagged = set(flagged_campaigns(registry_path))
    return [r for r in list_links(registry_path)
            if not r.get("event") and r.get("campaign") not in flagged]


def check_link_status(url, timeout=15) -> dict:
    """Best-effort HTTP reachability of a destination URL. Explicitly opt-in
    per call (never crawled automatically): some merchants rate-limit
    probing. Returns status only — never stores credentials, never follows
    login walls (non-2xx/3xx reported honestly)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GalaxyForge-linkcheck/1.0"},
                                     method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return {"url_domain": urllib.parse.urlsplit(url).netloc,
                    "http_status": r.status, "checked_at": _now()}
    except Exception as e:
        return {"url_domain": "", "http_status": None,
                "error": "%s" % type(e).__name__, "checked_at": _now()}
