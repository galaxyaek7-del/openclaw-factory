#!/usr/bin/env python3
"""Daily IndexNow notification for published customer_site pages (2026-10-23).

Founder authorization (2026-10-23): notify search engines automatically.
The only external call is a POST to api.indexnow.org telling search engines
that public URLs exist or changed; nothing is created on any platform. It is
gated by channels/write_gate.py with search_ping=True, which
GF_ALLOW_SEARCH_PING=true (or FACTORY_LIVE_PUBLISH) allows.

Which URLs: customer_site/*.html and sitemap.xml as they are on origin/main
(what GitHub Pages actually serves), whose blob changed since the last
submission recorded in data/indexnow_auto.json. Pages carrying a robots
noindex meta are skipped. Each URL must answer 200 live before it is sent.

Earlier manual submissions omitted keyLocation. The key file is served under
/openclaw-factory/, not at the host root (which answers 404), so IndexNow
could not verify ownership; this script always sends keyLocation.

  python scripts/indexnow_auto.py --once        # run (once per UTC day)
  python scripts/indexnow_auto.py --dry-run     # list what would be sent
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

HOST = "galaxyaek7-del.github.io"
BASE = f"https://{HOST}/openclaw-factory/"
KEY = "c8742f1da91ebe577587681839ae0004"
KEY_LOCATION = f"{BASE}{KEY}.txt"
ENDPOINT = "https://api.indexnow.org/indexnow"
STATE = ROOT / "data" / "indexnow_auto.json"
LEDGER = ROOT / "data" / "indexnow_submissions.jsonl"
MAX_URLS = 500
NOINDEX = re.compile(rb'<meta[^>]+name=["\']robots["\'][^>]+noindex', re.I)


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True).stdout


def published_pages(ref="origin/main"):
    """{path: blob_sha} for indexable pages in the published tree."""
    out = {}
    for line in git("ls-tree", "-r", ref, "--", "customer_site", "sitemap.xml").decode().splitlines():
        meta, path = line.split("\t", 1)
        blob = meta.split()[2]
        if not (path.endswith(".html") or path.endswith("sitemap.xml")):
            continue
        if path.endswith(".html") and NOINDEX.search(git("cat-file", "-p", blob)[:20000]):
            continue
        out[path] = blob
    return out


def read_state(p=STATE):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"submitted": {}, "last_day": None}


def write_state(state, p=STATE):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1), encoding="utf-8")
    os.replace(tmp, p)


def changed(pages, state):
    return sorted(path for path, blob in pages.items() if state.get("submitted", {}).get(path) != blob)


def is_live(url, timeout=15):
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "GalaxyForge-indexnow/1.0"})
        return urllib.request.urlopen(req, timeout=timeout).status == 200
    except Exception:
        return False


def submit(urls, timeout=30):
    from channels.write_gate import require_platform_write
    require_platform_write("indexnow", "submit_urls", search_ping=True)
    payload = json.dumps({"host": HOST, "key": KEY, "keyLocation": KEY_LOCATION, "urlList": urls}).encode()
    req = urllib.request.Request(ENDPOINT, data=payload, headers={"Content-Type": "application/json; charset=utf-8",
                                                                  "User-Agent": "GalaxyForge-indexnow/1.0"})
    try:
        return urllib.request.urlopen(req, timeout=timeout).status
    except urllib.error.HTTPError as e:
        return e.code


def run(*, dry_run=False, today=None, state_path=STATE, ledger_path=LEDGER, pages=None, live=is_live, post=submit):
    today = today or dt.datetime.now(dt.timezone.utc).date().isoformat()
    state = read_state(state_path)
    if not dry_run and state.get("last_day") == today:
        return {"action": "none", "detail": f"IndexNow already ran for {today}"}
    pages = pages if pages is not None else published_pages()
    todo = changed(pages, state)[:MAX_URLS]
    if not todo:
        if not dry_run:
            state["last_day"] = today
            write_state(state, state_path)
        return {"action": "none", "detail": f"no published page changed since the last submission ({len(pages)} indexable)"}
    urls = {path: BASE + path for path in todo}
    # Parallel: on this host a single HEAD sometimes takes 15-30 s before it
    # answers (measured 2026-10-23), so a serial pass over ~90 pages could
    # take many minutes.
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=16) as pool:
        flags = list(pool.map(lambda p: live(urls[p]), todo))
    live_paths = [p for p, ok in zip(todo, flags) if ok]
    if dry_run:
        return {"action": "dry_run", "detail": f"{len(live_paths)} of {len(todo)} changed pages live", "urls": [urls[p] for p in live_paths]}
    if not live_paths:
        return {"action": "none", "detail": f"{len(todo)} changed pages not live yet (Pages deploy pending); retry next tick"}
    status = post([urls[p] for p in live_paths])
    ok = status in (200, 202)
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"submission_id": f"IDX-AUTO-{now[:19]}", "submitted_at": now, "endpoint": ENDPOINT,
                            "http_status": status, "urls": [p.replace("customer_site/", "") for p in live_paths],
                            "key_location": KEY_LOCATION,
                            "evidence": f"HTTP {status} observed", "note": "automatic daily run (scripts/indexnow_auto.py)"}) + "\n")
    if not ok:
        return {"action": "failed", "detail": f"IndexNow answered HTTP {status} for {len(live_paths)} URLs"}
    for p in live_paths:
        state.setdefault("submitted", {})[p] = pages[p]
    if len(live_paths) == len(todo):
        state["last_day"] = today
    write_state(state, state_path)
    return {"action": "submitted", "detail": f"HTTP {status}: {len(live_paths)} URLs submitted"
            + (f"; {len(todo) - len(live_paths)} not live yet" if len(live_paths) < len(todo) else "")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    try:
        r = run(dry_run=a.dry_run)
    except Exception as e:  # reported to factory_loop as a failed step, never a crash
        r = {"action": "failed", "detail": f"{type(e).__name__}: {str(e)[:200]}"}
    sys.stdout.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
