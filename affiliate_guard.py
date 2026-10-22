# -*- coding: utf-8 -*-
"""Affiliate Runtime Guard (Galaxy Forge Phase 4, §11).

Minimal, FAIL-CLOSED validation for affiliate links. Default DENY.
No external calls. No real links are injected by this module.

Capabilities (per directive §11):
  * approved-domain allowlist
  * approved-link registry (via check_link)
  * placeholder detection
  * unauthorized-link rejection
  * affiliate disclosure enforcement
  * link integrity verification (scheme/host parse)
  * fail-closed behavior

NOTE: No real Fiverr links are permitted (directive forbids real Fiverr traffic
now). The Fiverr domain is explicitly blocked, not merely unapproved.
"""

from urllib.parse import urlparse

# Real, known affiliate/partner platforms. Expand ONLY with founder approval.
APPROVED_DOMAINS = {
    "amazon.com", "amazon.co.uk", "amazon.de", "amazon.fr", "amazon.ca", "amazon.es",
    "amazon.it", "amazon.co.jp",
    "gumroad.com", "paddle.com", "etsy.com", "envato.com", "creativemarket.com",
    "canva.com", "zapier.com", "n8n.io", "adobe.com", "google.com", "brevo.com",
    "aweber.com", "digitalocean.com", "siteground.com",
    "systeme.io",
}

# Explicitly forbidden as affiliate destinations right now.
BLOCKED_DOMAINS = {"fiverr.com"}

# A link whose text/URL matches any of these is treated as not-ready (placeholder).
# Deliberately narrow: real domains like example.com / random hex must NOT trip this.
PLACEHOLDER_PATTERNS = [
    r"YOUR_", r"PLACEHOLDER", r"TODO", r"FILLME", r"TBD",
    r"\{\{.*\}\}", r"<.*>",
]

REQUIRED_DISCLOSURE_TOKEN = "affiliate"


def _domain_of(url):
    try:
        netloc = urlparse(url).netloc.lower()
        return netloc[4:] if netloc.startswith("www.") else netloc
    except Exception:
        return ""


def is_placeholder(value):
    if value is None:
        return True
    text = str(value).strip()
    if text == "" or text.lower() in ("none", "null", "nan"):
        return True
    for pat in PLACEHOLDER_PATTERNS:
        import re
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False


def check_link(url, disclosure_text=None):
    """Validate a single affiliate link. FAIL-CLOSED: returns allowed=False
    on any uncertainty."""
    if is_placeholder(url):
        return {"allowed": False, "reason": "placeholder_or_empty_link",
                "domain": None, "placeholder": True, "disclosure_ok": False}

    try:
        parsed = urlparse(url)
        scheme = (parsed.scheme or "").lower()
    except Exception:
        return {"allowed": False, "reason": "unparseable_url",
                "domain": None, "placeholder": False, "disclosure_ok": False}

    # Link integrity: only http/https, never javascript:/data:/etc.
    if scheme not in ("http", "https"):
        return {"allowed": False, "reason": "unsafe_scheme",
                "domain": None, "placeholder": False, "disclosure_ok": False}

    domain = _domain_of(url)
    if not domain:
        return {"allowed": False, "reason": "no_domain",
                "domain": None, "placeholder": False, "disclosure_ok": False}

    if domain in BLOCKED_DOMAINS:
        return {"allowed": False, "reason": "blocked_domain",
                "domain": domain, "placeholder": False, "disclosure_ok": False}

    disclosure_ok = bool(disclosure_text) and (
        REQUIRED_DISCLOSURE_TOKEN in str(disclosure_text).lower()
    )

    if domain not in APPROVED_DOMAINS:
        return {"allowed": False, "reason": "domain_not_approved",
                "domain": domain, "placeholder": False, "disclosure_ok": disclosure_ok}

    if not disclosure_ok:
        return {"allowed": False, "reason": "disclosure_missing",
                "domain": domain, "placeholder": False, "disclosure_ok": False}

    return {"allowed": True, "reason": "ok",
            "domain": domain, "placeholder": False, "disclosure_ok": True}


def guard_affiliate_links(urls, disclosure_text=None):
    """Validate a batch. Returns {passed, rejected_count, rejected, results}."""
    results = [check_link(u, disclosure_text) for u in (urls or [])]
    rejected = [r for r in results if not r["allowed"]]
    return {
        "passed": len(rejected) == 0,
        "rejected_count": len(rejected),
        "rejected": rejected,
        "results": results,
    }
