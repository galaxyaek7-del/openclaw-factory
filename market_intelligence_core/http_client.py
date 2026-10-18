"""
Market Intelligence Core — canonical HTTP client (ADR-049).

The one thing genuinely duplicated (confirmed by the 2026-07-16
architecture review, byte-for-byte): market_intelligence_engine.py and
competitor_discovery.py each defined their own near-identical
_http_get_json() — same urllib.request pattern, differing only in the
User-Agent string. That single primitive is consolidated here.

Deliberately NOT consolidated here: each module's higher-level query
functions (_query_hn/_query_github in competitor_discovery.py;
_query_github_issues/_query_hn_discussions in
market_intelligence_engine.py) hit different endpoints for different
purposes (competitor discovery vs. customer-pain search) — they were
never actually duplicates of each other, so forcing them into one
generic "search" function here would be a false abstraction traded for
a smaller file count, which this factory does not do (CLAUDE.md: never
sacrifice correctness for fewer files). They keep their own url-building
and keep calling their own module's local _http_get_json name (now a
one-line delegation to this module), so every existing test that
patches `<module>._http_get_json` continues to intercept the real call
exactly as before — nothing about their test surface changes.
"""

import json
import os
import ssl
import urllib.error
import urllib.request

try:
    # certifi ships a current, portable CA bundle. Some endpoints (arXiv,
    # observed 2026-10-18) are not verifiable with this interpreter's own
    # default bundle, but are with certifi's. See get_ssl_context().
    import certifi as _certifi
except Exception:  # pragma: no cover - certifi is a normal dependency of `requests`
    _certifi = None

DEFAULT_USER_AGENT = "Mozilla/5.0 (Galaxy-Forge-MarketIntelligence)"

_SSL_CONTEXT = None


def get_ssl_context():
    """Return a certificate-verifying TLS context, preferring certifi's bundle.

    Root cause of the arXiv ``CERTIFICATE_VERIFY_FAILED: unable to get
    local issuer certificate`` failure: this Python build resolves its
    default CA bundle to ``C:\\Program Files\\Common Files\\SSL\\cert.pem``,
    which lacks the issuer arXiv's chain needs, while certifi's bundle
    verifies it (both observed 2026-10-18).

    Certificate verification is always enabled. When certifi is
    unavailable or its bundle is missing we fall back to the interpreter's
    own defaults (still verifying) — never to an unverified context — so a
    missing bundle degrades to a clear verification failure, not a silent
    security downgrade.
    """
    global _SSL_CONTEXT
    if _SSL_CONTEXT is None:
        cafile = None
        if _certifi is not None:
            candidate = _certifi.where()
            if candidate and os.path.exists(candidate):
                cafile = candidate
        _SSL_CONTEXT = ssl.create_default_context(cafile=cafile)
    return _SSL_CONTEXT

# Real Evidence Provider abstraction (ADR-179, 2026-08-06): the codes a
# real server uses to actively refuse a request (bot-protection,
# rate-limiting, missing auth) rather than simply not having the
# resource (404) or failing internally (5xx) -- a real, meaningful
# distinction the founder's directive asked to preserve ("record it as
# verification blocked"), not collapse into one generic failure.
BLOCKED_STATUS_CODES = (401, 403, 429)


class EvidenceSourceBlocked(Exception):
    """A subclass of Exception (not a new exception hierarchy) so every
    existing `except Exception` call site in this factory's connectors
    keeps catching it exactly as before -- zero behavior change for any
    pre-existing caller. New code that wants to distinguish "actively
    blocked" from "any other failure" can `isinstance()`-check for this
    specific type."""
    def __init__(self, status_code, url):
        self.status_code = status_code
        self.url = url
        super().__init__(f"HTTP {status_code} (verification blocked): {url}")


def http_get_json(url, timeout=10, user_agent=DEFAULT_USER_AGENT):
    req = urllib.request.Request(url, headers={
        'User-Agent': user_agent,
        'Accept': 'application/json',
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=get_ssl_context()) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        if e.code in BLOCKED_STATUS_CODES:
            raise EvidenceSourceBlocked(e.code, url) from e
        raise


# Strategic Phase 3, Round 1 (2026-07-22): a second canonical primitive for
# APIs that don't speak JSON -- arXiv's official API returns Atom XML, not
# JSON, so http_get_json() above can't be reused for it (parsing XML is
# each connector's own concern, per this module's own docstring -- only
# the raw fetch is shared).
def http_get_text(url, timeout=10, user_agent=DEFAULT_USER_AGENT):
    req = urllib.request.Request(url, headers={
        'User-Agent': user_agent,
        'Accept': 'application/atom+xml, text/xml, */*',
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=get_ssl_context()) as r:
            return r.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        if e.code in BLOCKED_STATUS_CODES:
            raise EvidenceSourceBlocked(e.code, url) from e
        raise
