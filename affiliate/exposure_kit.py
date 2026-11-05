#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exposure readiness layer: URL instrumentation + landing/checkout health.
Instrumentation only — a generated URL is NEVER traffic. Health checks are
read-only GETs. No publishing, no spend, no account actions."""

from __future__ import annotations

import urllib.parse
import urllib.request


def campaign_url(base: str, source: str, medium: str, campaign: str) -> dict:
    """Build a UTM-tagged URL deterministically (same inputs -> same URL)."""
    parts = urllib.parse.urlparse(base)
    q = dict(urllib.parse.parse_qsl(parts.query))
    q.update({"utm_source": source, "utm_medium": medium, "utm_campaign": campaign})
    url = urllib.parse.urlunparse((parts.scheme, parts.netloc, parts.path,
                                   "", urllib.parse.urlencode(q), ""))
    return {"url": url, "deterministic": True,
            "note": "instrumentation, not traffic"}


def landing_health(url: str, timeout: int = 30) -> dict:
    """Fetch page; check reachability + buy affordance + price presence."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GalaxyForge-health/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            html = r.read().decode("utf-8", "replace")
            final = r.geturl()
    except Exception as e:
        return {"reachable": False, "error": "%s" % type(e).__name__}
    low = html.lower()
    links = sorted(set(urllib.parse.urljoin(final, h) for h in
                       __import__("re").findall(r'href="([^"]+)"', html)
                       if h.startswith("http") or h.startswith("/")))

    def head(u):
        try:
            rq = urllib.request.Request(u, method="HEAD",
                                        headers={"User-Agent": "GalaxyForge-health/1.0"})
            with urllib.request.urlopen(rq, timeout=12) as rr:
                return rr.status
        except Exception as e:
            return type(e).__name__

    broken = [(u, head(u)) for u in links[:15]
              if not isinstance(head(u), int) or head(u) >= 400]
    return {"reachable": True, "final_url": final,
            "buy_affordance": any(k in low for k in ("buy", "purchase", "checkout", "add to cart")),
            "price_visible": "$79" in html or ">79<" in html,
            "outbound_links_checked": min(len(links), 15),
            "broken_links": broken,
            "checked": "read-only GET + bounded HEADs"}
