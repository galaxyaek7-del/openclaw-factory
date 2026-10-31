"""Customer-problem signals for the trend candidates from Stack Exchange (backlog B32, 2026-10-29).

Reads questions people actually asked, through the documented public Stack Exchange
API (api.stackexchange.com/2.3, no key, no account; quota 300 requests/day per IP).
Each query is recorded as a source (access PUBLIC_API_KEYLESS, type ANECDOTAL:
a question is one person's stated problem), and each topic gets one aggregated
CUSTOMER_PROBLEM signal (label DERIVED) with the question count, views and a sample
of links. Question text stays on Stack Exchange (CC BY-SA): titles are cited as
evidence, never reused in a product.

Rate limits: at most len(QUERIES) calls per run, a pause between calls, stops at the
first `backoff` or when quota_remaining < QUOTA_FLOOR. `--if-due` runs only when the
last run is >= DUE_DAYS old (scripts/registry_daily.py calls it that way).

A topic with no matching question gets no signal; the run log says so. After the
signals are recorded, opportunities on those topics are re-scored (append-only).
"""
import html
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from trend_to_product import records, scoring  # noqa: E402

API = "https://api.stackexchange.com/2.3/search/advanced"
RUN_STATE = os.path.join(ROOT, "data", "trend_to_product", "problem_signals_run.json")
WINDOW_YEARS = 5
DUE_DAYS = 7
RETRY_AFTER_SECONDS = 3600  # after a run in which every call failed
QUOTA_FLOOR = 50
PAUSE_S = 0.5

# topic -> [(site, query, groups)]. A question counts only if its title matches at
# least one whole word/phrase from EVERY group. The first live run (2026-10-29) used
# one loose substring list and counted "Do they sell artist gloves" as a pricing
# problem and a Bronte question ("keeps its mystery") as a reading-tracker problem;
# requiring a topic anchor AND a problem term removes those.
QUERIES = {
    "crochet_patterns": [("crafts", "crochet pattern", (
        ("pattern", "patterns", "chart", "instructions"),
        ("crochet", "crocheted", "crocheting", "stitch", "stitches", "yarn", "row", "rows", "round",
         "mean", "read", "follow", "understand", "gauge")))],
    "craft_planners": [("crafts", "yarn", (
        ("how much yarn", "how many skeins", "yardage", "how much wool", "keep track", "track",
         "row counter", "count rows", "estimate", "calculate", "plan", "planning"),
        ("yarn", "skein", "skeins", "crochet", "knitting", "project", "projects", "rows")))],
    "maker_pricing": [
        ("crafts", "price", (
            ("price", "prices", "pricing", "charge", "profit", "worth"),
            ("sell", "selling", "handmade", "my work", "commission", "customer", "customers", "etsy",
             "market"))),
        ("money", "etsy", (
            ("price", "prices", "pricing", "fee", "fees", "profit", "charge"),
            ("etsy", "handmade", "crafts", "craft"))),
        ("freelancing", "handmade", (
            ("price", "prices", "pricing", "charge", "profit"),
            ("handmade", "craft", "crafts", "etsy")))],
    "printable_miniatures": [("crafts", "miniature paper", (
        ("miniature", "miniatures", "dollhouse", "doll house", "1:12", "1/12"),
        ("paper", "printable", "print", "printed", "printing", "cardstock", "card")))],
    "reading_journals": [
        ("literature", "reading log", (
            ("reading log", "reading journal", "reading list", "books i have read", "track my reading",
             "tracking books", "book tracker"),)),
        ("ebooks", "reading progress", (
            ("reading log", "reading journal", "track my reading", "reading history", "books i have read",
             "book tracker", "reading statistics"),))],
    "content_planning": [
        ("webmasters", "content calendar", (
            ("content calendar", "editorial calendar", "content plan", "content planning",
             "posting schedule", "schedule posts", "publishing schedule"),)),
        ("freelancing", "content calendar", (
            ("content calendar", "editorial calendar", "content plan", "posting schedule",
             "schedule posts"),))],
}


def _get(url, fetch=None):
    if fetch:
        return fetch(url)
    req = Request(url, headers={"User-Agent": "GalaxyForge-trend-research/1.0 (read-only)",
                                "Accept-Encoding": "gzip"})
    with urlopen(req, timeout=20) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            import gzip
            raw = gzip.decompress(raw)
    return json.loads(raw.decode("utf-8"))


def _has(title, term):
    return re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", title) is not None


def _matches(title, groups):
    t = title.lower()
    return all(any(_has(t, w) for w in g) for g in groups)


def collect(now=None, fetch=None, sleep=time.sleep, base_dir=None):
    now = now or datetime.now(timezone.utc)
    day = now.date().isoformat()
    since = int((now - timedelta(days=365 * WINDOW_YEARS)).timestamp())
    log = {"day": day, "calls": 0, "stopped": None, "topics": {}}
    for topic, queries in QUERIES.items():
        questions, src_ids = {}, []
        for site, q, groups in queries:
            if log["stopped"]:
                break
            params = {"site": site, "q": q, "fromdate": since, "pagesize": 100,
                      "order": "desc", "sort": "relevance"}
            url = f"{API}?{urlencode(params)}"
            try:
                d = _get(url, fetch)
            except Exception as e:  # recorded, never raised: one failed site must not stop the rest
                log["topics"].setdefault(topic, {}).setdefault("errors", []).append(f"{site}/{q}: {type(e).__name__}")
                continue
            finally:
                log["calls"] += 1
            if d.get("error_message"):
                log["topics"].setdefault(topic, {}).setdefault("errors", []).append(d["error_message"])
                continue
            kept = [i for i in d.get("items", []) if _matches(html.unescape(i.get("title", "")), groups)]
            src = records.record_source(url, day, q, topic, "ANECDOTAL", "PUBLIC_API_KEYLESS", "SIGNAL_ONLY",
                                        title=f"Stack Exchange {site}: questions matching '{q}'",
                                        notes=f"{len(d.get('items', []))} returned, {len(kept)} match topic words; "
                                              "question text CC BY-SA, cited not reused",
                                        rate_limit_note=f"quota_remaining={d.get('quota_remaining')}",
                                        base_dir=base_dir)
            src_ids.append(src["source_id"])
            for i in kept:
                questions[f"{site}:{i['question_id']}"] = {
                    "site": site, "title": html.unescape(i["title"]), "link": i.get("link"),
                    "views": i.get("view_count", 0), "answers": i.get("answer_count", 0),
                    "created": datetime.fromtimestamp(i["creation_date"], timezone.utc).date().isoformat()}
            if d.get("backoff"):
                log["stopped"] = f"backoff {d['backoff']}s requested by API"
            elif d.get("quota_remaining") is not None and d["quota_remaining"] < QUOTA_FLOOR:
                log["stopped"] = f"quota_remaining {d['quota_remaining']} < {QUOTA_FLOOR}"
            sleep(PAUSE_S)
        entry = log["topics"].setdefault(topic, {})
        entry["questions"] = len(questions)
        entry["complete"] = len(src_ids) == len(queries)
        if not questions:
            entry["signal"] = None
            continue
        qs = sorted(questions.values(), key=lambda x: -x["views"])
        value = {"question_count": len(qs), "views_total": sum(x["views"] for x in qs),
                 "answered_share": round(sum(1 for x in qs if x["answers"]) / len(qs), 2),
                 "window_years": WINDOW_YEARS, "sites": sorted({x["site"] for x in qs}),
                 "sample": qs[:10]}
        sig = records.record_signal(
            "CUSTOMER_PROBLEM", topic,
            f"{len(qs)} Stack Exchange question(s) in the last {WINDOW_YEARS} years state a {topic} problem "
            f"({value['views_total']:,} views in total; sites: {', '.join(value['sites'])}). "
            "Questions show a problem exists; they are not purchase intent.",
            src_ids, day, value=value, label="DERIVED", base_dir=base_dir)
        entry["signal"] = sig["signal_id"]
    return log


def rescore_topics(log, base_dir=None):
    """Make each topic's problem evidence match this run (new record, history kept).

    When every query for a topic answered, its earlier CUSTOMER_PROBLEM signals are
    replaced by this run's signal, or by none when no question matched. A topic with
    a failed or skipped query keeps its previous signals.
    """
    out = []
    for o in scoring.latest_opportunities(base_dir):
        entry = log["topics"].get(o["topic"]) or {}
        if not entry.get("complete"):
            continue
        sid = entry.get("signal")
        old = {s["signal_id"] for s in records.signals_for(topic=o["topic"], base_dir=base_dir)
               if s["signal_type"] == "CUSTOMER_PROBLEM"}
        sigs = [s for s in o["signal_ids"] if s not in old] + ([sid] if sid else [])
        if sorted(sigs) == sorted(o["signal_ids"]):
            continue
        r = scoring.record_opportunity(o["name"], o["topic"], o["format"], sigs,
                                       assessments=o.get("assessments"),
                                       idea_text=f"{o['name']}: an original product built by the factory",
                                       base_dir=base_dir)
        out.append((o["name"], o["band"], r["band"], r["composite"]))
    return out


def run(if_due=False, now=None, fetch=None, sleep=time.sleep, base_dir=None, state_path=None,
        write_state=True):
    now = now or datetime.now(timezone.utc)
    state_path = state_path or (os.path.join(base_dir, "problem_signals_run.json") if base_dir else RUN_STATE)
    try:
        with open(state_path, encoding="utf-8") as f:
            prev = json.load(f)
    except (OSError, ValueError):
        prev = {}
    last = prev.get("day")
    if if_due and last and (now.date() - datetime.strptime(last, "%Y-%m-%d").date()).days < DUE_DAYS:
        return {"action": "none", "detail": f"last run {last}; due every {DUE_DAYS} days"}
    failed_at = prev.get("last_failed_at")
    if if_due and failed_at and (now - datetime.fromisoformat(failed_at)).total_seconds() < RETRY_AFTER_SECONDS:
        return {"action": "none", "detail": f"every call failed at {failed_at}; retrying after an hour"}
    log = collect(now, fetch, sleep, base_dir)
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    tmp = state_path + ".tmp"
    errors = sum(len(t.get("errors") or []) for t in log["topics"].values())
    if log["calls"] and errors >= log["calls"]:
        # Every call failed (network outage, API down): this is not a run. The
        # previous run's state is kept, so the weekly gate stays open and the
        # step retries at most hourly instead of waiting seven days.
        prev.update({"last_failed_at": now.isoformat(timespec="seconds"), "last_failed_calls": log["calls"],
                     "last_failed_errors": [e for t in log["topics"].values() for e in t.get("errors") or []][:5]})
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(prev, f, ensure_ascii=False, indent=1)
        os.replace(tmp, state_path)
        return {"action": "unreachable", "calls": log["calls"], "detail": "every call failed; retrying after an hour"}
    log["rescored"] = rescore_topics(log, base_dir)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=1)
    os.replace(tmp, state_path)
    if write_state and base_dir is None:  # the dashboard state reflects live ledgers only
        from trend_to_product import linkage
        linkage.write_state()
    return {"action": "ran", "calls": log["calls"], "stopped": log["stopped"],
            "topics": {k: v.get("questions") for k, v in log["topics"].items()}, "rescored": log["rescored"]}


if __name__ == "__main__":
    sys.stdout.write(json.dumps(run(if_due="--if-due" in sys.argv), ensure_ascii=False, indent=1) + "\n")
