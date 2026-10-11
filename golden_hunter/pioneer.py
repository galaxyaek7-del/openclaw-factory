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

v2 source expansion (2026-08-14, founding directive: "free and real
evidence sources"): v1 was HN top stories only. v2 adds three more real,
free, KEYLESS sources with no API key in `.env` required, each genuinely
upstream of per-niche scoring and each a different KIND of real signal:

  HN top stories        — what's trending in the developer world right now
  HN Ask HN             — real questions/problems people are actively
                          describing (HN Firebase /v0/askstories.json)
  HN Show HN            — real things people have actually built
                          (/v0/showstories.json)
  GitHub recent repos   — real projects CREATED in the last 30 days,
                          sorted by stars (api.github.com search API,
                          keyless, ~10 req/min unauthenticated; returns
                          real data, empty on any failure)

Reddit remains an honest, documented gap (it needs registered app
credentials not present in `.env` — same reason
`multi_source_intelligence`'s own Reddit connector is honestly
`unavailable`). Product Hunt / Google Trends likewise have no keyless
discovery-mode endpoint in this codebase. Those stay named next steps,
not silently skipped.
"""

from datetime import datetime, timezone

from market_intelligence_core import http_client as MIC_HTTP_CLIENT


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


HN_TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ASK_STORIES_URL = "https://hacker-news.firebaseio.com/v0/askstories.json"
HN_SHOW_STORIES_URL = "https://hacker-news.firebaseio.com/v0/showstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"
GITHUB_SEARCH_URL = (
    "https://api.github.com/search/repositories"
    "?q=created:%3E{}&sort=stars&order=desc&per_page={}"
)
_USER_AGENT = "Mozilla/5.0 (Galaxy-Forge-Pioneer)"

# A real, honest keyword heuristic for "this looks like a real product/
# business opportunity" rather than plain news — same "keyword
# heuristic, disclosed as one" discipline profit_oracle.py's own
# SUBNICHE_QUALIFIERS already uses. A title matching none of these is
# still returned (never silently dropped), just ranked lower and
# labeled `signal_matched=False` — an honest ranking signal, not a hard
# filter, since the keyword list can't be exhaustive.
OPPORTUNITY_SIGNAL_KEYWORDS = (
    "show hn", "ask hn", "i built", "i made", "i launched", "launch hn",
    "saas", "startup", "side project", "open source",
)


def _fetch_story_ids_with_status(url, limit):
    """Real HN Firebase call for any of the story-id feeds (top/ask/show).
    Returns (ids, status) -- status is 'OK' on a real response (even a
    real empty list) or 'UNKNOWN: <reason>' on a genuine fetch failure,
    so a caller can tell 'this feed is really empty today' apart from
    'this feed could not be reached' (Cycle 76, directive section 1:
    'إن تعذّر الجلب فسجّل UNKNOWN ولا تملأ بقيم افتراضية'). Never raises --
    a discovery run must survive this one source being down, same
    discipline competitor_discovery.py's own query functions use."""
    try:
        ids = MIC_HTTP_CLIENT.http_get_json(url, timeout=10, user_agent=_USER_AGENT)
        if not isinstance(ids, list):
            return [], "UNKNOWN: non-list response shape"
        return ids[:limit], "OK"
    except Exception as e:
        return [], f"UNKNOWN: {e}"


def _fetch_story_ids(url, limit):
    """Backward-compatible wrapper -- real callers that only need the ids
    (not fetch status) keep working unchanged."""
    ids, _status = _fetch_story_ids_with_status(url, limit)
    return ids


def _fetch_top_story_ids(limit):
    return _fetch_story_ids(HN_TOP_STORIES_URL, limit)


def _fetch_item(item_id):
    try:
        return MIC_HTTP_CLIENT.http_get_json(HN_ITEM_URL.format(item_id), timeout=10, user_agent=_USER_AGENT)
    except Exception:
        return None


def _discover_hn_feed_with_status(feed_url, source_label, limit, scan_pool):
    """Real candidate builder for any HN story-id feed, plus real fetch
    status ('OK' or 'UNKNOWN: <reason>' -- never a guessed/default value
    on failure, Cycle 76 section 1). Every candidate carries fetched_at
    (real UTC timestamp of this call) and raw (the real HN item dict,
    unmodified) -- the directive's explicit per-candidate shape
    requirement."""
    candidates = []
    story_ids, status = _fetch_story_ids_with_status(feed_url, scan_pool)
    for story_id in story_ids:
        item = _fetch_item(story_id)
        if not item or not item.get("title"):
            continue
        title = item["title"]
        matched = any(kw in title.lower() for kw in OPPORTUNITY_SIGNAL_KEYWORDS)
        candidates.append({
            "niche": title,
            "source": source_label,
            "source_url": item.get("url") or f"https://news.ycombinator.com/item?id={story_id}",
            "points": item.get("score", 0),
            "signal_matched": matched,
            "fetched_at": _now_iso(),
            "raw": item,
        })
    candidates.sort(key=lambda c: (not c["signal_matched"], -c["points"]))
    return candidates[:limit], status


def _discover_hn_feed(feed_url, source_label, limit, scan_pool):
    """Backward-compatible wrapper -- real callers that only need the
    candidate list (not fetch status) keep working unchanged."""
    candidates, _status = _discover_hn_feed_with_status(feed_url, source_label, limit, scan_pool)
    return candidates


def _days_ago(days):
    from datetime import datetime, timezone, timedelta
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")


def discover_github_recent_repos_with_status(limit=10, days=30):
    """Real discovery + real fetch status, same 'OK'/'UNKNOWN: <reason>'
    discipline as _fetch_story_ids_with_status (Cycle 76 section 1) --
    GitHub's free, keyless search API for repositories CREATED in the
    last `days` days, sorted by stars. Any failure (rate limit, network)
    returns an honestly empty list tagged UNKNOWN, never fabricated
    repos and never a silently-guessed default. Each candidate carries
    fetched_at (real UTC call time) and raw (the real repo dict,
    unmodified)."""
    try:
        data = MIC_HTTP_CLIENT.http_get_json(
            GITHUB_SEARCH_URL.format(_days_ago(days), limit),
            timeout=15, user_agent=_USER_AGENT,
        )
    except Exception as e:
        return [], f"UNKNOWN: {e}"
    if not isinstance(data, dict):
        return [], "UNKNOWN: non-dict response shape"
    items = data.get("items", [])
    candidates = []
    fetched_at = _now_iso()
    for repo in items:
        name = repo.get("full_name") or repo.get("name")
        if not name:
            continue
        description = repo.get("description") or ""
        candidates.append({
            "niche": f"{name}: {description}".strip() if description else name,
            "source": "github_recent_repos",
            "source_url": repo.get("html_url") or f"https://github.com/{name}",
            "points": repo.get("stargazers_count", 0),
            "signal_matched": any(kw in name.lower() or kw in description.lower()
                                  for kw in OPPORTUNITY_SIGNAL_KEYWORDS),
            "stars": repo.get("stargazers_count", 0),
            "language": repo.get("language"),
            "created_at": repo.get("created_at"),
            "fetched_at": fetched_at,
            "raw": repo,
        })
    candidates.sort(key=lambda c: (not c["signal_matched"], -c["points"]))
    return candidates[:limit], "OK"


def discover_github_recent_repos(limit=10, days=30):
    """Backward-compatible wrapper -- real callers that only need the
    candidate list (not fetch status) keep working unchanged."""
    candidates, _status = discover_github_recent_repos_with_status(limit=limit, days=days)
    return candidates


def discover_candidates_with_status(limit=10, scan_pool=30):
    """Real discovery + real fetch status (see _fetch_story_ids_with_status).
    Fetches today's real HN top stories (no niche input — this is what
    makes Pioneer genuinely upstream of Golden Hunter, not a duplicate of
    competitor_discovery.py's per-niche search) and returns up to `limit`
    candidate dicts, opportunity-signal matches ranked first, each
    carrying fetched_at (real UTC call time) and raw (the real HN item,
    unmodified). Never scores or accepts anything — that stays
    market_hunter.hunt_market()'s unchanged job. A network failure
    returns an honestly empty list tagged UNKNOWN, never a fabricated or
    defaulted candidate."""
    candidates = []
    story_ids, status = _fetch_story_ids_with_status(HN_TOP_STORIES_URL, scan_pool)
    for story_id in story_ids:
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
            "fetched_at": _now_iso(),
            "raw": item,
        })

    candidates.sort(key=lambda c: (not c["signal_matched"], -c["points"]))
    return candidates[:limit], status


def discover_candidates(limit=10, scan_pool=30):
    """Backward-compatible wrapper -- real callers that only need the
    candidate list (not fetch status) keep working unchanged."""
    candidates, _status = discover_candidates_with_status(limit=limit, scan_pool=scan_pool)
    return candidates


def discover_all(limit_per_source=10, scan_pool=30, github_days=30):
    """Continuous global discovery across ALL wired free/keyless real
    sources: HN top + Ask HN + Show HN + GitHub recent repos. Each source
    is independent — one being down returns its own empty list and never
    blocks the others. Returns a merged list; the caller (market_hunter's
    unchanged hunt_market loop) still scores/accepts/rejects every
    candidate — Pioneer never decides."""
    merged = []
    merged += _discover_hn_feed(HN_ASK_STORIES_URL, "hacker_news_ask_hn", limit_per_source, scan_pool)
    merged += _discover_hn_feed(HN_SHOW_STORIES_URL, "hacker_news_show_hn", limit_per_source, scan_pool)
    merged += discover_github_recent_repos(limit=limit_per_source, days=github_days)
    merged += discover_candidates(limit=limit_per_source, scan_pool=scan_pool)

    # Dedupe by normalized niche text, keeping the highest-point occurrence.
    seen = {}
    for c in merged:
        key = (c.get("niche") or "").strip().lower()
        if not key:
            continue
        if key in seen and (seen[key].get("points") or 0) >= (c.get("points") or 0):
            continue
        seen[key] = c
    return list(seen.values())[:limit_per_source * 4]


def discover_all_with_status(limit_per_source=10, scan_pool=30, github_days=30):
    """Same merge as discover_all(), plus a real per-source fetch status
    map ('OK' or 'UNKNOWN: <reason>', never a guessed default -- Cycle 76
    section 1). A separate function, not a parameter on discover_all(),
    so every existing real caller of discover_all() (market_hunter.py's
    hunt_market()) is untouched byte-for-byte; this is the one new,
    additive entrypoint for callers that need source-level observability
    (e.g. a future NEEDS_ATTENTION-style honest stagnation check)."""
    merged = []
    status = {}
    hn_ask, status["hacker_news_ask_hn"] = _discover_hn_feed_with_status(
        HN_ASK_STORIES_URL, "hacker_news_ask_hn", limit_per_source, scan_pool)
    merged += hn_ask
    hn_show, status["hacker_news_show_hn"] = _discover_hn_feed_with_status(
        HN_SHOW_STORIES_URL, "hacker_news_show_hn", limit_per_source, scan_pool)
    merged += hn_show
    gh, status["github_recent_repos"] = discover_github_recent_repos_with_status(
        limit=limit_per_source, days=github_days)
    merged += gh
    hn_top, status["hacker_news_top_stories"] = discover_candidates_with_status(
        limit=limit_per_source, scan_pool=scan_pool)
    merged += hn_top

    seen = {}
    for c in merged:
        key = (c.get("niche") or "").strip().lower()
        if not key:
            continue
        if key in seen and (seen[key].get("points") or 0) >= (c.get("points") or 0):
            continue
        seen[key] = c
    return list(seen.values())[:limit_per_source * 4], status
