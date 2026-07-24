#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Galaxy Forge — Real Competitor Discovery Engine (ADR-042)

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
import argparse
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone

from market_intelligence_core import http_client as MIC_HTTP_CLIENT

for _stream in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8')
    except Exception:
        pass

FACTORY_DIR = os.path.dirname(os.path.abspath(__file__))
COMPETITOR_DB_FILE = os.path.join(FACTORY_DIR, 'data', 'competitor_database.json')
# Live Competitive Intelligence Layer (2026-07-23, founder directive):
# real historical tracking. Before this, save_database() overwrote each
# niche's ONE cached snapshot on every refresh -- no prior state ever
# survived to diff against, which is exactly the gap
# enterprise_readiness.py's own run_risk_intelligence_scan() already
# disclosed ("pricing_changes... needs repeated real runs to compare").
# Append-only, same convention as every other *.jsonl ledger in this
# factory -- never overwritten, so a real trend can be computed later
# from more than the current + immediately-prior snapshot if needed.
COMPETITOR_HISTORY_FILE = os.path.join(FACTORY_DIR, 'data', 'competitor_history.jsonl')
MAX_AGE_DAYS_DEFAULT = 7  # "don't redo the full search unless needed" — a real, tunable freshness window

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"
GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"

CATEGORIES = ["Direct Competitor", "Indirect Competitor", "Alternative Solution", "Enterprise Leader", "Emerging Startup", "Unclassified"]


# ── NETWORK I/O (thin, real, no fabrication — separated from logic below so
#    the logic can be unit-tested with fixture data, no live calls needed) ──

def _http_get_json(url, timeout=10):
    """ADR-049: delegates to market_intelligence_core.http_client — the
    urllib logic itself now lives in exactly one place (it was
    byte-for-byte duplicated with market_intelligence_engine.py's own
    copy before this). Kept as a real local function (not a bare
    re-export) so `@patch("competitor_discovery._http_get_json")` in
    tests/test_competitor_discovery.py keeps intercepting every caller
    below unchanged."""
    return MIC_HTTP_CLIENT.http_get_json(
        url, timeout=timeout, user_agent='Mozilla/5.0 (Galaxy-Forge-CompetitorDiscovery)'
    )


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


# Live Competitive Intelligence Layer (2026-07-23): a real comparison
# between two real, previously-computed snapshots for the same niche --
# never fabricates a trend from a single data point. Matched by
# competitor name (the same real identity field discover_competitors()
# already uses) -- pure, no I/O, independently unit-testable with
# fixture data.
def diff_competitor_snapshots(old_snapshot, new_snapshot):
    if not old_snapshot:
        return {
            "has_history": False,
            "new_competitors": [],
            "disappeared_competitors": [],
            "growth_signals": [],
            "note": "لا لقطة سابقة لهذا النيتش — هذا أول رصد حقيقي، لا مقارنة ممكنة بعد",
        }

    old_by_name = {c["name"]: c for c in (old_snapshot.get("competitors") or [])}
    new_by_name = {c["name"]: c for c in (new_snapshot.get("competitors") or [])}

    new_names = set(new_by_name) - set(old_by_name)
    gone_names = set(old_by_name) - set(new_by_name)
    shared_names = set(new_by_name) & set(old_by_name)

    growth_signals = []
    for name in shared_names:
        old_metrics = old_by_name[name].get("metrics") or {}
        new_metrics = new_by_name[name].get("metrics") or {}
        for metric_key in ("github_stars", "hacker_news_points"):
            old_value, new_value = old_metrics.get(metric_key), new_metrics.get(metric_key)
            if isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)) and new_value > old_value:
                growth_signals.append({
                    "name": name, "metric": metric_key, "from": old_value, "to": new_value,
                    "note": f"نمو حقيقي في {metric_key}: {old_value} → {new_value}",
                })

    return {
        "has_history": True,
        "compared_at": new_snapshot.get("discovered_at"),
        "previous_discovered_at": old_snapshot.get("discovered_at"),
        "new_competitors": [new_by_name[n] for n in sorted(new_names)],
        "disappeared_competitors": [old_by_name[n] for n in sorted(gone_names)],
        "growth_signals": growth_signals,
    }


def _append_history(snapshot, history_file=None):
    """Best-effort, append-only — a failed history write must never block
    the real refresh it's recording, same discipline as every other
    non-critical ledger write in this factory."""
    history_file = history_file or COMPETITOR_HISTORY_FILE
    try:
        os.makedirs(os.path.dirname(history_file), exist_ok=True)
        with open(history_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(snapshot, ensure_ascii=False) + '\n')
    except OSError as e:
        print(f"[competitor_discovery] history write failed: {e}")


# Threat Engine (Live Competitive Intelligence Layer, 2026-07-23): 8
# dimensions were requested; a real search for a data source behind each
# found only 3 this factory can honestly derive today from HN/GitHub
# data already gathered above. The other 5 have no real, accessible
# source anywhere in this factory (no Crunchbase/PitchBook/LinkedIn/CVE/
# regulatory-filing connector exists) -- reported as explicit Unknown
# with the exact reason, never guessed or defaulted to a neutral number.
THREAT_DIMENSIONS_WITHOUT_REAL_DATA = {
    "funding_pressure": "لا مصدر بيانات تمويل حقيقي متصل (Crunchbase/PitchBook يحتاجان اشتراكاً مدفوعاً)",
    "pricing_pressure": "لا بيانات تسعير منافسين حقيقية مرصودة — لا مصدر مجاني يكشف أسعار المنافسين الفعلية",
    "technology_disruption": "لا مصدر حقيقي لرصد نقلات تقنية جوهرية لدى المنافسين (براءات اختراع/تقارير تقنية) متاح اليوم",
    "regulatory_threat": "لا اتصال حقيقي بمصدر تنظيمي/قانوني — لا قاعدة بيانات لوائح متصلة",
    "talent_competition": "لا مصدر حقيقي لبيانات التوظيف لدى المنافسين (LinkedIn/Indeed API تحتاج اعتماداً غير متوفر)",
}


def _score_competitor_saturation(snapshot):
    """Real, derived directly from the real competitor count
    discover_competitors() already found — no new measurement, no
    fabricated market-size denominator."""
    total = snapshot.get("total_found", 0)
    if total == 0:
        level, score = "لا تشبع ملحوظ", 0
    elif total <= 2:
        level, score = "منخفض", 25
    elif total <= 5:
        level, score = "متوسط", 50
    elif total <= 9:
        level, score = "مرتفع", 75
    else:
        level, score = "مرتفع جداً", 100
    return {"level": level, "score": score, "basis": f"{total} منافس حقيقي مكتشف (HN+GitHub)"}


def _score_market_concentration(snapshot):
    """A real Herfindahl-Hirschman Index computed over each competitor's
    real popularity metric (GitHub stars or HN points — whichever that
    competitor actually has). Honest Unknown when no competitor carries
    either real metric, rather than treating an empty/zero weight as
    'perfectly competitive'."""
    weights = []
    for c in snapshot.get("competitors") or []:
        metrics = c.get("metrics") or {}
        w = metrics.get("github_stars") or metrics.get("hacker_news_points") or 0
        if isinstance(w, (int, float)) and w > 0:
            weights.append(w)

    total_weight = sum(weights)
    if total_weight <= 0:
        return {
            "level": "Unknown", "score": None,
            "basis": "لا مقياس شعبية حقيقي (نجوم GitHub/نقاط HN) لأي منافس مكتشف — لا يمكن حساب التركّز",
        }

    hhi = sum((w / total_weight) ** 2 for w in weights) * 10000
    if hhi < 1500:
        level = "غير مركّز — منافسة موزّعة بين لاعبين متعددين"
    elif hhi < 2500:
        level = "تركّز معتدل"
    else:
        level = "تركّز عالٍ — سوق يهيمن عليه عدد قليل من اللاعبين"
    return {
        "level": level, "score": round(hhi / 100, 1),
        "basis": f"مؤشر HHI محسوب من {len(weights)} قيمة شعبية حقيقية (نجوم/نقاط)، إجمالي الوزن={total_weight}",
    }


def _score_new_entrant_trajectory(snapshot):
    """Reuses diff_competitor_snapshots()'s real 'changes' key — never a
    trend from a single data point. Honest Unknown until a real second
    refresh exists for this niche."""
    changes = snapshot.get("changes")
    if not changes or not changes.get("has_history"):
        return {
            "level": "Unknown", "score": None,
            "basis": "لا سجل تاريخي كافٍ بعد لهذا النيتش — يحتاج تشغيلات حقيقية متكررة للمقارنة",
        }

    new_count = len(changes.get("new_competitors") or [])
    gone_count = len(changes.get("disappeared_competitors") or [])
    growth_count = len(changes.get("growth_signals") or [])
    net = new_count - gone_count
    if net > 0:
        level = "تصاعدي — داخلون جدد حقيقيون يفوقون عدد من اختفى"
    elif net < 0:
        level = "تراجعي — عدد من اختفى أكبر من الداخلين الجدد"
    else:
        level = "مستقر"
    return {
        "level": level, "score": net,
        "basis": (
            f"{new_count} داخل جديد حقيقي، {gone_count} اختفى، {growth_count} إشارة نمو حقيقية "
            f"منذ اللقطة السابقة ({changes.get('previous_discovered_at')})"
        ),
    }


def compute_threat_assessment(snapshot):
    """Threat Engine: pure function over an already-computed real
    snapshot (the same shape discover_competitors()/
    get_or_refresh_competitors() produce) — no I/O, no new network call,
    fully unit-testable with fixture data. Returns all 8 requested
    dimensions; 5 are explicit, reasoned Unknown rather than a fabricated
    number."""
    return {
        "competitor_saturation": _score_competitor_saturation(snapshot),
        "market_concentration": _score_market_concentration(snapshot),
        "new_entrant_trajectory": _score_new_entrant_trajectory(snapshot),
        **{
            dim: {"level": "Unknown", "score": None, "basis": reason}
            for dim, reason in THREAT_DIMENSIONS_WITHOUT_REAL_DATA.items()
        },
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


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
            # Live Competitive Intelligence Layer (2026-07-23): real,
            # 100%-verifiable fact straight from which API the hit came
            # from -- not a heuristic. Closes "identify open-source
            # substitutes" from the real Competitor Discovery request.
            # "Bundled platform alternative" (the 6th requested type) is
            # deliberately NOT tagged here -- no real signal in either
            # API's response distinguishes "this is a feature of a
            # larger platform" from a standalone product, and guessing
            # would be exactly the fabricated classification this
            # module's own docstring already refuses to do.
            "is_open_source": source == "github",
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


def get_or_refresh_competitors(niche, max_age_days=MAX_AGE_DAYS_DEFAULT, force=False, db_file=None, max_results=10, history_file=None):
    """The actual caching decision: real, stored data is reused until it's
    genuinely stale, instead of re-querying live APIs on every call.

    Live Competitive Intelligence Layer (2026-07-23): every real refresh
    (never a cache hit) now also computes a real diff against whatever
    snapshot it's about to replace, and preserves that outgoing snapshot
    in COMPETITOR_HISTORY_FILE first — closing the exact gap
    enterprise_readiness.py's own risk-intelligence scan already
    disclosed ("needs repeated real runs to compare"). history_file
    mirrors db_file's own test-isolation convention (omitting it uses
    the real default; tests always override it) — the same real bug
    class this factory already found once this session in
    market_hunter.py's decisions_path, applied here from the start
    rather than discovered later."""
    db = load_database(db_file)
    key = _normalize_key(niche)
    existing = db.get(key)

    if existing and not force:
        age_days = _days_since(existing.get('discovered_at'))
        if age_days is not None and age_days <= max_age_days:
            existing['_cache'] = {"hit": True, "age_days": age_days}
            # Threat Engine (2026-07-23): cheap, pure, re-derived from
            # already-cached real fields on every call — never a stale
            # cached score, and never a new network call.
            existing['threat_assessment'] = compute_threat_assessment(existing)
            return existing

    result = discover_competitors(niche, max_results=max_results)
    result['_cache'] = {"hit": False, "age_days": 0}
    result['changes'] = diff_competitor_snapshots(existing, result)
    result['threat_assessment'] = compute_threat_assessment(result)
    if existing:
        _append_history(existing, history_file)
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
