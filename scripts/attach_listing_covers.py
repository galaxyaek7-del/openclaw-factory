"""Attach the generated covers to live Gumroad products that still have none.

    python scripts/attach_listing_covers.py            # dry run: what would be attached
    python scripts/attach_listing_covers.py --live [--limit N]

Authorization: the founder's standing order of 2026-10-24 to build, fix and
publish on every arm without waiting for each instruction (recorded in each
result). The write still passes the factory's gate: the Gumroad auth state must
be VERIFIED, and FACTORY_LIVE_PUBLISH is set for this process only and reset in
`finally`, exactly as scripts/publish_batch14.py does.

For each product, immediately before writing: a fresh GET must show it published
with zero covers, and the cover's public URL must answer 200 with an image type.
gumroad_publisher.add_product_cover() sends only the cover (never price, files,
name or publication state) and proves the attach by re-reading the product.
The run stops at the first failure. Results: data/gumroad_cover_results.json.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "channels"))
COVERS = ROOT / "data" / "gumroad_covers.json"
RESULTS = ROOT / "data" / "gumroad_cover_results.json"
AUTHORIZATION = ("founder standing order, 2026-10-24: fix, build, produce and publish on all arms automatically; "
                 "covers only, no price/file/name/publication change")


def image_ok(url, opener=urllib.request.urlopen):
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
        with opener(req, timeout=30) as r:
            return r.status == 200 and r.headers.get("Content-Type", "").startswith("image/")
    except Exception:  # noqa: BLE001
        return False


def plan(covers: dict, live: dict) -> list:
    out = []
    for gid, c in covers.items():
        p = live.get(gid)
        if p is None:
            out.append({"id": gid, "name": c["name"], "action": "SKIP", "why": "not in the live catalog"})
        elif not p.get("published"):
            out.append({"id": gid, "name": c["name"], "action": "SKIP", "why": "not published"})
        elif p.get("covers"):
            out.append({"id": gid, "name": c["name"], "action": "SKIP", "why": "already has a cover"})
        else:
            out.append({"id": gid, "name": c["name"], "action": "ATTACH", "cover": c["public_url"]})
    return out


AUDIT = ROOT / "reports" / "covers" / "cover_audit.json"
PAGES_ROOT = "https://galaxyaek7-del.github.io/openclaw-factory/"


def ours_attached(results_path=RESULTS) -> set:
    try:
        runs = json.loads(Path(results_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    return {r["id"] for run in runs for r in run.get("results", []) if r.get("result") == "ATTACHED"}


def plan_second(audit: dict, live: dict, ours: set) -> list:
    """The 2026-10-17 designs that show a product's real book cover, added as a
    SECOND image only where the product has exactly one cover and it is the one
    attached by this script (so no image placed by anyone else is ever involved)."""
    out = []
    for i in audit.get("items", []):
        if not i.get("matched_book_cover"):
            continue
        pid, p = i["product_id"], live.get(i["product_id"])
        t = {"id": pid, "name": i["title"], "cover": PAGES_ROOT + i["cover_file"], "expected": 1}
        if p is None or not p.get("published"):
            out.append(dict(t, action="SKIP", why="not live"))
        elif pid not in ours:
            out.append(dict(t, action="SKIP", why="its cover was not attached by this script"))
        elif len(p.get("covers") or []) != 1:
            out.append(dict(t, action="SKIP", why=f"has {len(p.get('covers') or [])} covers, expected exactly 1"))
        else:
            out.append(dict(t, action="ATTACH"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--second-book-cover", action="store_true",
                    help="add the 2026-10-17 real-book-cover design as a second image")
    a = ap.parse_args()
    import gumroad_publisher as gp
    token = gp.load_token()
    live = {p["id"]: p for p in gp.list_products(token)}  # read-only GET
    if a.second_book_cover:
        todo = plan_second(json.loads(AUDIT.read_text(encoding="utf-8")), live, ours_attached())
    else:
        todo = plan(json.loads(COVERS.read_text(encoding="utf-8"))["covers"], live)
    attach = [t for t in todo if t["action"] == "ATTACH"]
    if a.limit:
        attach = attach[: a.limit]
    print(json.dumps({"attach": len(attach), "skip": sum(1 for t in todo if t["action"] == "SKIP")}, indent=1))
    if not a.live:
        print("dry run only")
        return 0
    import gumroad_auth_watch as auth
    state = auth.poll()
    if state.get("status") != "VERIFIED":
        print(json.dumps({"error": f"Gumroad auth state is {state.get('status')}, not VERIFIED"}))
        return 1
    results = []
    os.environ["FACTORY_LIVE_PUBLISH"] = "true"  # this process only
    try:
        for t in attach:
            rec = {"id": t["id"], "name": t["name"], "cover": t["cover"]}
            try:
                expected = t.get("expected", 0)
                fresh = gp.get_product(token, t["id"])
                if not fresh.get("published") or len(fresh.get("covers") or []) != expected:
                    rec["result"] = f"SKIPPED: changed since planning (unpublished or not exactly {expected} covers)"
                elif not image_ok(t["cover"]):
                    rec["result"] = "FAILED: cover URL not reachable as an image"
                else:
                    got = gp.add_product_cover(token, t["id"], t["cover"], expected_cover_count=expected)
                    rec["result"] = ("ATTACHED_SECOND" if expected else "ATTACHED") if len(got.get("covers") or []) > expected \
                        else "FAILED: re-read shows no new cover"
            except Exception as e:  # noqa: BLE001 -- recorded and the run stops
                rec["result"] = f"FAILED: {type(e).__name__}: {str(e)[:200]}"
            results.append(rec)
            print(json.dumps(rec, ensure_ascii=False))
            if rec["result"].startswith("FAILED"):
                break
            time.sleep(1.5)
    finally:
        os.environ["FACTORY_LIVE_PUBLISH"] = "false"
        prev = json.loads(RESULTS.read_text(encoding="utf-8")) if RESULTS.exists() else []
        RESULTS.write_text(json.dumps(prev + [{"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                               "authorization": AUTHORIZATION, "results": results}], indent=1,
                                      ensure_ascii=False) + "\n", encoding="utf-8")
    return 0 if results and all(r["result"] in ("ATTACHED", "ATTACHED_SECOND") or r["result"].startswith("SKIPPED")
                                for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
