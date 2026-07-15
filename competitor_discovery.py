#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw Factory — Real Competitor Discovery Engine (ADR-042)

Honesty note (same discipline as market_hunter.py/profit_oracle.py): this
queries two real, free, keyless APIs — Hacker News Algolia
(hn.algolia.com/api/v1) and GitHub Search (api.github.com/search) — for
real competitors matching a niche. Every metric reported is either a real
field from one of these two APIs, or a value explicitly derived from real
fields with the derivation shown. Anything requested that has no free,
keyless real source today (website visits, SEO rank, Reddit mentions,
Google Trends, Product Hunt, company size, pricing model) is reported as
"Unknown" with the exact reason, never guessed. Classification into the
5 requested buckets is an explainable heuristic over real fields (repo
owner type, star count, account age) — when the signal is too weak to
classify with any real confidence, the bucket is "Unclassified" rather
than a forced guess.

Standalone tool, like market_hunter.py — run deliberately (manually or by
a future scheduled batch), never invoked inside profit_oracle.py's
synchronous scoring path. That keeps live network calls out of the fast,
already-tested production-gating code path; discovery results feed
scoring later via profit_oracle.opportunity_score()'s existing
external_signal mechanism (ADR-038/041), same pattern tier1_intake/'s
manual research already used.

Usage:
    python competitor_discovery.py --discover "AI agent compliance automation"
    python competitor_discovery.py --show "AI agent compliance automation"
"""

import os
import re
import sys
import json
import math
import argparse
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone

for _stream in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8')
    except Exception:
        pass

FACTORY_DIR = os.path.dirname(os.path.abspath(__file__))
COMPETITOR_DB_FILE = os.path.join(FACTORY_DIR, 'data', 'competitor_database.json')
MAX_AGE_DAYS_DEFAULT = 7  # "don't redo the full search unless needed" — a real, tunable freshness window

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"
GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"

CATEGORIES = ["Direct Competitor", "Indirect Competitor", "Alternative Solution", "Enterprise Leader", "Emerging Startup", "Unclassified"]


# ── NETWORK I/O (thin, real, no fabrication — separated from logic below so
#    the logic can be unit-tested with fixture data, no live calls needed) ──

def _http_get_json(url, timeout=10):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (OpenClaw-Factory-CompetitorDiscovery)',
        'Accept': 'application/json',
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def _query_hn(query, limit=10):
    """Real Hacker News Algolia search — Show HN posts, most relevant to a
    real product/competitor existing publicly. Returns [] on any network
    failure, never raises (a discovery run must survive one source being
    down)."""
    try:
        url = f"{HN_SEARCH_URL}?tags=show_hn&query={urllib.parse.quote(query)}"
        data = _http_get_json(url)
        return data.get('hits', [])[:limit]
    except Exception:
        return []


def _query_github(query, limit=10):
    """Real GitHub repository search — a live, open-source competitor or
    tool. Returns [] on any network failure, never raises."""
    try:
        url = f"{GITHUB_SEARCH_URL}?q={urllib.parse.quote(query)}&sort=stars&order=desc&per_page={limit}"
        data = _http_get_json(url)
        return data.get('items', [])[:limit]
    except Exception:
        return []


# ── PURE LOGIC (no network — fully unit-testable with fixture data) ──

def _days_since(iso_str, now=None):
    if not iso_str:
        return None
    try:
        now = now or datetime.now(timezone.utc)
        dt = datetime.fromisoformat(str(iso_str).replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (now - dt).days
    except Exception:
        return None


def classify_competitor(hit, source):
    """Explainable heuristic over REAL fields only — never a guess dressed
    as a category. Returns (category, reason). 'Unclassified' when the
    real signal is genuinely too weak to place it in one of the 4
    meaningful buckets — per the explicit instruction: no data, no forced
    answer.
    """
    if source == 'github':
        owner = hit.get('owner') or {}
        owner_type = owner.get('type')  # real GitHub field: 'Organization' or 'User'
        stars = hit.get('stargazers_count', 0)
        age_days = _days_since(hit.get('created_at'))

        if owner_type == 'Organization' and stars >= 2000:
            return "Enterprise Leader", f"مستودع تحت منظمة GitHub حقيقية، {stars} نجمة (حقيقي) — إشارة نضج/موارد فريق"
        if age_days is not None and age_days <= 180 and 0 < stars < 2000:
            return "Emerging Startup", f"مستودع عمره {age_days} يوماً فقط (حقيقي)، {stars} نجمة — إشارة مشروع جديد"
        if stars >= 500:
            return "Direct Competitor", f"{stars} نجمة حقيقية — اعتماد حقيقي كافٍ ليُعامَل كمنافس مباشر محتمل"
        return "Unclassified", f"إشارة ضعيفة جداً ({stars} نجمة، owner_type={owner_type}) — لا ثقة كافية للتصنيف"

    if source == 'hacker_news':
        points = hit.get('points', 0)
        num_comments = hit.get('num_comments', 0)
        if points >= 100:
            return "Direct Competitor", f"{points} نقطة HN حقيقية — اهتمام سوق حقيقي كافٍ لمنافس محتمل جدّي"
        if points >= 20:
            return "Alternative Solution", f"{points} نقطة HN حقيقية — اهتمام حقيقي معتدل، بديل محتمل لا منافس مباشر مؤكَّد"
        return "Unclassified", f"إشارة ضعيفة جداً ({points} نقطة، {num_comments} تعليق) — لا ثقة كافية للتصنيف"

    return "Unclassified", f"مصدر غير معروف ({source})"


UNKNOWN_METRICS = {
    "website_visits": "لا أداة قياس زيارات مجانية متصلة (SimilarWeb/Ahrefs تحتاج اشتراكاً مدفوعاً)",
    "seo_rank": "لا أداة SEO مجانية متصلة",
    "reddit_mentions": "Reddit API يحتاج بيانات اعتماد غير متوفرة في هذه الجلسة",
    "google_trends": "لا اتصال Trends حي (n8n Sensing Engine مبني، غير مُفعَّل — راجع BLOCKERS.md)",
    "product_hunt": "يحتاج تواصلاً رسمياً مسبقاً مع Product Hunt قبل استخدام تجاري (GOLDEN_HUNTER_V2_STRATEGY.md §2)",
    "company_size": "لا مصدر مجاني حقيقي لحجم الشركة",
    "pricing_model": "غير قابل للاستنتاج بثقة من بيانات HN/GitHub وحدها",
}


def gather_real_metrics(hit, source):
    """Every field either a real value from the API response, or an
    explicit Unknown + reason — never a placeholder number."""
    metrics = dict(UNKNOWN_METRICS)  # start as all-Unknown, fill in what's real below

    if source == 'github':
        metrics['github_stars'] = hit.get('stargazers_count', 0)
        metrics['github_forks'] = hit.get('forks_count', 0)
        metrics['open_issues'] = hit.get('open_issues_count', 0)
        metrics['last_updated'] = hit.get('updated_at') or hit.get('pushed_at')
        age_days = _days_since(hit.get('created_at'))
        pushed_days_ago = _days_since(hit.get('pushed_at'))
        if age_days is not None and pushed_days_ago is not None:
            metrics['development_velocity'] = (
                "نشط مؤخراً" if pushed_days_ago <= 30 else
                "نشط جزئياً" if pushed_days_ago <= 180 else
                "راكد على الأرجح"
            ) + f" (آخر push منذ {pushed_days_ago} يوماً، حقيقي)"
        del metrics['reddit_mentions']  # not applicable to a GitHub-sourced hit, not "unknown for it"
        del metrics['google_trends']
        del metrics['product_hunt']
    elif source == 'hacker_news':
        metrics['hacker_news_points'] = hit.get('points', 0)
        metrics['hacker_news_comments'] = hit.get('num_comments', 0)
        metrics['first_seen'] = hit.get('created_at')

    return metrics


def compute_opportunity_gap(demand_score, competition_score):
    """Honest derivation from two already-real/estimated components
    (profit_oracle.py's demand/competition, ADR-038/041) — not a new
    independent measurement. High demand + low competition = high gap."""
    return round(max(0, min(100, 0.6 * demand_score + 0.4 * (100 - competition_score))))


def discover_competitors(niche, max_results=10):
    """The real, automated discovery — queries both sources live, never
    guesses a competitor that wasn't actually found."""
    hn_hits = [(h, 'hacker_news') for h in _query_hn(niche, max_results)]
    gh_hits = [(h, 'github') for h in _query_github(niche, max_results)]

    competitors = []
    for hit, source in hn_hits + gh_hits:
        category, reason = classify_competitor(hit, source)
        competitors.append({
            "name": hit.get('title') or hit.get('full_name') or hit.get('name') or 'unknown',
            "url": hit.get('url') or hit.get('html_url'),
            "source": source,
            "category": category,
            "category_reason": reason,
            "metrics": gather_real_metrics(hit, source),
        })

    by_category = {}
    for c in competitors:
        by_category.setdefault(c["category"], []).append(c["name"])

    return {
        "niche": niche,
        "discovered_at": datetime.now(timezone.utc).isoformat(),
        "total_found": len(competitors),
        "by_category": by_category,
        "competitors": competitors,
        "market_saturation": "Unknown — يحتاج بيانات حجم سوق حقيقي (TAM)، لا عدد نتائج بحث فقط (ADR-040)",
        "barrier_to_entry": "Unknown — لا مؤشر تقني/رأسمالي حقيقي متاح من HN/GitHub وحدهما",
        "pricing_power": "Unknown — يحتاج بيانات مبيعات حقيقية، صفر مبيعات اليوم",
    }


# ── PERSISTENT DATABASE ("don't redo the full search unless needed") ──

def load_database(db_file=None):
    db_file = db_file or COMPETITOR_DB_FILE
    if not os.path.exists(db_file):
        return {}
    try:
        with open(db_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_database(db, db_file=None):
    db_file = db_file or COMPETITOR_DB_FILE
    os.makedirs(os.path.dirname(db_file), exist_ok=True)
    with open(db_file, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def _normalize_key(niche):
    return re.sub(r'\s+', ' ', niche.strip().lower())


def get_or_refresh_competitors(niche, max_age_days=MAX_AGE_DAYS_DEFAULT, force=False, db_file=None, max_results=10):
    """The actual caching decision: real, stored data is reused until it's
    genuinely stale, instead of re-querying live APIs on every call."""
    db = load_database(db_file)
    key = _normalize_key(niche)
    existing = db.get(key)

    if existing and not force:
        age_days = _days_since(existing.get('discovered_at'))
        if age_days is not None and age_days <= max_age_days:
            existing['_cache'] = {"hit": True, "age_days": age_days}
            return existing

    result = discover_competitors(niche, max_results=max_results)
    result['_cache'] = {"hit": False, "age_days": 0}
    db[key] = result
    save_database(db, db_file)
    return result


def main():
    parser = argparse.ArgumentParser(description="Real Competitor Discovery Engine (ADR-042)")
    parser.add_argument('--discover', metavar='NICHE', help="Discover (or refresh if stale) real competitors for a niche")
    parser.add_argument('--show', metavar='NICHE', help="Show cached competitors for a niche, never re-searches")
    parser.add_argument('--force', action='store_true', help="Force a fresh search even if cached data is not stale")
    parser.add_argument('--max-age-days', type=int, default=MAX_AGE_DAYS_DEFAULT)
    args = parser.parse_args()

    if args.discover:
        result = get_or_refresh_competitors(args.discover, max_age_days=args.max_age_days, force=args.force)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if args.show:
        db = load_database()
        result = db.get(_normalize_key(args.show))
        print(json.dumps(result or {"error": "not found — run --discover first"}, indent=2, ensure_ascii=False))
        return

    parser.print_help()


if __name__ == '__main__':
    main()
