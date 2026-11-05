#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""X-experiment measurement (post-URL intake onward). States kept separate:
NO MEASURED EXPOSURE / MEASURED EXPOSURE / UNKNOWN EXPOSURE / NO PURCHASE /
VERIFIED PURCHASE. Missing traffic data is never zero. End classifier:
A (verified purchase) / B (measured exposure, no purchase) / C (exposure
unknown, no purchase) / D (technical failure). B needs a traffic metric
that does not currently exist — the machine says so instead of faking it."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
XEXP_PATH = _FACTORY_ROOT / "data" / "x_experiment.json"
OEMBED = "https://publish.twitter.com/oembed?url=%s"


def intake(url: str) -> dict:
    u = (url or "").strip()
    if not (u.startswith("https://") and ("x.com/" in u or "twitter.com/" in u)):
        return {"accepted": False, "STATUS": "NOT_VERIFIED",
                "reason": "not a well-formed x.com/twitter.com https URL"}
    rec = {"POST_URL": u, "received_at": datetime.now(timezone.utc).isoformat(),
           "status": "PENDING_VERIFICATION"}
    XEXP_PATH.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"accepted": True, "STATUS": "PENDING_VERIFICATION"}


def verify_post(url: str, timeout: int = 20) -> dict:
    """oEmbed read-only check: resolvable, author, text markers. No metrics
    available from oEmbed — exposure stays UNKNOWN by design."""
    try:
        req = urllib.request.Request(OEMBED % urllib.parse.quote(url, safe=""),
                                     headers={"User-Agent": "GalaxyForge-verify/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read().decode())
    except Exception as e:
        return {"STATUS": "NOT_VERIFIED",
                "reason": "%s: %s" % (type(e).__name__, str(e)[:120])}
    author = str(d.get("author_name", ""))
    html = str(d.get("html", ""))
    checks = {
        "resolvable": True,
        "author_match": author.lower() == "aekgrafat",
        "product_link": "fetmu" in html or "gumroad" in html.lower(),
    }
    if all(checks.values()):
        return {"STATUS": "VERIFIED", "checks": checks, "author": author,
                "exposure": "UNKNOWN (oEmbed carries no metrics)",
                "checked_at": datetime.now(timezone.utc).isoformat()}
    failed = [k for k, v in checks.items() if not v]
    return {"STATUS": "HOLD", "checks": checks, "failed": failed,
            "reason": "marker mismatch, no silent repair"}


def monitor(since_iso: str) -> dict:
    """Sales deltas since post time (no causality claims from timing)."""
    from channels import gumroad_publisher as gp
    from prospecting import market_test as mt
    token = gp.load_token()
    sales = gp.get_sales(token, mt.PRODUCT_ID)
    since = datetime.fromisoformat(since_iso)
    new = [s for s in sales if str(s.get("created_at", s.get("sale_timestamp", ""))) >= since_iso]
    return {"sales_total": len(sales), "sales_since_post": len(new),
            "exposure": "UNKNOWN", "purchase": "VERIFIED" if new else "NO_PURCHASE",
            "causality": "not inferred from timing",
            "checked_at": datetime.now(timezone.utc).isoformat()}


def classify_end(verified_purchase: bool, exposure_measured: bool,
                 exposure_present: bool, technical_ok: bool) -> dict:
    if not technical_ok:
        return {"class": "D_TECHNICAL_FAILURE"}
    if verified_purchase:
        return {"class": "A_VERIFIED_PURCHASE"}
    if exposure_measured and exposure_present:
        return {"class": "B_MEASURED_EXPOSURE_NO_PURCHASE"}
    if exposure_measured and not exposure_present:
        return {"class": "C_EXPOSURE_UNKNOWN_NO_PURCHASE",
                "note": "measured-absent exposure is evidence; unmeasured is not"}
    return {"class": "C_EXPOSURE_UNKNOWN_NO_PURCHASE",
            "note": "default: exposure unmeasured -> diagnose distribution/measurement gap, never product failure"}
