"""Pioneer (Strategic Phase, 2026-07-19) — real, novel-candidate
discovery, upstream of Golden Hunter's existing scoring.

Confirmed by reading every real source in this factory before writing
this: `market_hunter.py`'s SEED_CATEGORIES is a fixed, hand-written list
(its own comment: "لا يولِّد جديداً" — doesn't generate anything new,
ADR-028); `multi_source_intelligence`'s 9 connectors and
`competitor_discovery.py`'s HN/GitHub queries all require a niche as
input already (per-niche evidence enrichment, not raw discovery). Pioneer
is the missing piece: it finds real, CURRENT candidate topics with no
niche pre-specified, then hands them to Golden Hunter's existing,
unchanged scoring/accept-reject pipeline (`market_hunter.hunt_market()`).
Pioneer never scores, accepts, or records a decision itself — that stays
Golden Hunter's job, unduplicated.

v1 source: Hacker News's real, free, keyless Firebase API
(`/v0/topstories.json` + `/v0/item/{id}.json`) — a genuinely different
endpoint from `competitor_discovery.py`'s existing HN Algolia SEARCH API
(which needs a query already, confirmed by reading it directly). Reddit
is a real, honest gap for v1 — it needs registered app credentials not
present in `.env` today (same reason `multi_source_intelligence`'s own
Reddit connector is honestly `unavailable`, see BLOCKERS.md) — and
Product Hunt/Google Trends aren't wired to any discovery-mode endpoint
in this codebase yet either. Both are real, named next steps, not
silently skipped.
"""

from market_intelligence_core import http_client as MIC_HTTP_CLIENT

HN_TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"
_USER_AGENT = "Mozilla/5.0 (OpenClaw-Factory-Pioneer)"

# A real, honest keyword heuristic for "this looks like a real product/
# business opportunity" rather than plain news — same "keyword
# heuristic, disclosed as one" discipline profit_oracle.py's own
# SUBNICHE_QUALIFIERS already uses. A title matching none of these is
# still returned (never silently dropped), just ranked lower and
# labeled `signal_matched=False` — an honest ranking signal, not a hard
# filter, since the keyword list can't be exhaustive.
OPPORTUNITY_SIGNAL_KEYWORDS = (
    "show hn", "i built", "i made", "i launched", "launch hn",
    "saas", "startup", "side project", "open source",
)


def _fetch_top_story_ids(limit):
    """Real HN Firebase call. Returns [] on any network failure, never
    raises — a discovery run must survive this one source being down,
    same discipline competitor_discovery.py's own query functions use."""
    try:
        ids = MIC_HTTP_CLIENT.http_get_json(HN_TOP_STORIES_URL, timeout=10, user_agent=_USER_AGENT)
        return ids[:limit] if isinstance(ids, list) else []
    except Exception:
        return []


def _fetch_item(item_id):
    try:
        return MIC_HTTP_CLIENT.http_get_json(HN_ITEM_URL.format(item_id), timeout=10, user_agent=_USER_AGENT)
    except Exception:
        return None


def discover_candidates(limit=10, scan_pool=30):
    """Real discovery: fetches today's real HN top stories (no niche
    input — this is what makes Pioneer genuinely upstream of Golden
    Hunter, not a duplicate of competitor_discovery.py's per-niche
    search) and returns up to `limit` candidate dicts, opportunity-
    signal matches ranked first. Never scores or accepts anything —
    that stays market_hunter.hunt_market()'s unchanged job. A network
    failure returns an honestly empty list, never fabricated candidates.
    """
    candidates = []
    for story_id in _fetch_top_story_ids(scan_pool):
        item = _fetch_item(story_id)
        if not item or not item.get("title"):
            continue
        title = item["title"]
        matched = any(kw in title.lower() for kw in OPPORTUNITY_SIGNAL_KEYWORDS)
        candidates.append({
            "niche": title,
            "source": "hacker_news_top_stories",
            "source_url": item.get("url") or f"https://news.ycombinator.com/item?id={story_id}",
            "points": item.get("score", 0),
            "signal_matched": matched,
        })

    candidates.sort(key=lambda c: (not c["signal_matched"], -c["points"]))
    return candidates[:limit]
