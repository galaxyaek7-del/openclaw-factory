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
import urllib.request

DEFAULT_USER_AGENT = "Mozilla/5.0 (OpenClaw-Factory-MarketIntelligence)"


def http_get_json(url, timeout=10, user_agent=DEFAULT_USER_AGENT):
    req = urllib.request.Request(url, headers={
        'User-Agent': user_agent,
        'Accept': 'application/json',
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


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
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8')
