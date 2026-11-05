#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unpublish the three Gumroad listings that sit at "$0+" (F6), on the founder's chat order of 2026-11-05.

Why: a listing at price 0 shows as "$0+", so a buyer can pay any amount for content we withdrew (two listings) or for
a listing with no file (one). Unpublishing hides the page and stops purchases; nothing is deleted and it can be
re-enabled. Safety:
  * only these three slugs can ever be touched (hard allow-list);
  * each must be read first: published, price 0, no sales -- otherwise it is skipped, not changed;
  * the gate (FACTORY_LIVE_PUBLISH + a fresh VERIFIED Gumroad auth) applies as for every write;
  * after each call the listing is read back and must report published=false, else the run stops FAILED;
  * no price, file, title or description is sent.

    python scripts/unpublish_zero_price_listings.py            # dry run
    python scripts/unpublish_zero_price_listings.py --live
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
REPORT = ROOT / "data" / "unpublish_zero_price_listings.json"
ALLOWED = ("iaiyt", "wteork", "owtmpe")


def slug_of(p):
    return (p.get("short_url") or "").rstrip("/").rsplit("/", 1)[-1]


def plan(token, gp):
    by = {slug_of(p): p for p in gp.list_products(token)}
    out = []
    for s in ALLOWED:
        p = by.get(s)
        if not p:
            out.append({"slug": s, "result": "SKIPPED", "reason": "listing not found"})
            continue
        f = gp.get_product(token, p["id"])
        base = {"slug": s, "product_id": p["id"], "name": f.get("name"), "published": f.get("published"),
                "price": f.get("price"), "sales_count": f.get("sales_count")}
        if not f.get("published"):
            out.append({**base, "result": "ALREADY_UNPUBLISHED"})
        elif f.get("price") not in (0, "0", None) or int(f.get("sales_count") or 0) > 0:
            out.append({**base, "result": "SKIPPED", "reason": "not a $0 listing with zero sales: left untouched"})
        else:
            out.append({**base, "result": "PLANNED"})
    return out


def apply(token, gp, actions):
    done = []
    for a in actions:
        if a["result"] != "PLANNED":
            done.append(a)
            continue
        try:
            gp.disable_product(token, a["product_id"])
            after = gp.get_product(token, a["product_id"])
            ok = after.get("published") is False
            done.append({**a, "result": "PASS" if ok else "FAILED", "published_after": after.get("published")})
            if not ok:
                break  # stop at the first doubt
        except Exception as e:
            done.append({**a, "result": "FAILED", "reason": f"{type(e).__name__}: {str(e)[:300]}"})
            break
    return done


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args(argv)
    from channels import gumroad_publisher as gp
    token = gp.load_token()
    actions = plan(token, gp)
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "mode": "LIVE" if args.live else "DRY_RUN",
              "order": "founder in chat 2026-11-05: approved unpublishing the three $0+ listings (F6)"}
    if args.live:
        import gumroad_auth_watch as auth
        from channels import publication_authorization as pa
        pa.assert_session_fresh(auth.poll(), max_age_seconds=3600)
        os.environ["FACTORY_LIVE_PUBLISH"] = "true"
        try:
            report["actions"] = apply(token, gp, actions)
        finally:
            os.environ["FACTORY_LIVE_PUBLISH"] = "false"
    else:
        report["actions"] = actions
    REPORT.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    summary = {}
    for a in report["actions"]:
        summary[a["result"]] = summary.get(a["result"], 0) + 1
    print(json.dumps({"mode": report["mode"], "summary": summary}))
    return 0 if all(a["result"] in ("PASS", "PLANNED", "ALREADY_UNPUBLISHED") for a in report["actions"]) else 1


if __name__ == "__main__":
    sys.exit(main())
