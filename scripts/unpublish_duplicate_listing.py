#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unpublish ONE live listing that duplicates another live listing (2026-11-06).

Found by the registry drift report (duplicate_live_titles): two published listings "The 5-Minute Context Reset
Playbook", both $15, both zero sales. Two copies split the page's search weight and confuse a buyer.

Safety: the listing to unpublish and the listing to keep are named explicitly; both must be published, carry the same
title (case-insensitive) and the one to unpublish must have ZERO sales and the kept one must stay published after the
run; the sanctioned write gate and a fresh Gumroad auth apply; after the call the listing is read back and must say
published=false; nothing is deleted and `enable_product` reverses it; no price, file, title or description is sent.

    python scripts/unpublish_duplicate_listing.py --slug vhofn --keep akxaae            # dry run
    python scripts/unpublish_duplicate_listing.py --slug vhofn --keep akxaae --live
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
REPORT = ROOT / "data" / "unpublish_duplicate_listing.json"


def slug_of(p):
    return (p.get("short_url") or "").rstrip("/").rsplit("/", 1)[-1]


def plan(token, gp, slug, keep):
    by = {slug_of(p): p for p in gp.list_products(token)}
    if slug == keep:
        return {"result": "REFUSED", "reason": "the listing to unpublish and the one to keep are the same"}
    if slug not in by or keep not in by:
        return {"result": "REFUSED", "reason": "a named listing was not found"}
    a, b = gp.get_product(token, by[slug]["id"]), gp.get_product(token, by[keep]["id"])
    base = {"slug": slug, "product_id": by[slug]["id"], "keep": keep, "name": a.get("name")}
    if not a.get("published"):
        return {**base, "result": "ALREADY_UNPUBLISHED"}
    if not b.get("published"):
        return {**base, "result": "REFUSED", "reason": "the listing to keep is not published: nothing would remain"}
    if (a.get("name") or "").strip().lower() != (b.get("name") or "").strip().lower():
        return {**base, "result": "REFUSED", "reason": "titles differ: not a duplicate"}
    if int(a.get("sales_count") or 0) > 0:
        return {**base, "result": "REFUSED", "reason": "it has sales: never hidden by this tool"}
    return {**base, "result": "PLANNED", "keep_id": by[keep]["id"]}


def apply(token, gp, a):
    gp.disable_product(token, a["product_id"])
    after = gp.get_product(token, a["product_id"])
    kept = gp.get_product(token, a["keep_id"])
    ok = after.get("published") is False and kept.get("published") is True
    return {**a, "result": "PASS" if ok else "FAILED", "published_after": after.get("published"), "keep_published": kept.get("published")}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--keep", required=True)
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args(argv)
    from channels import gumroad_publisher as gp
    token = gp.load_token()
    a = plan(token, gp, args.slug, args.keep)
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "mode": "LIVE" if args.live else "DRY_RUN"}
    if args.live and a["result"] == "PLANNED":
        import gumroad_auth_watch as auth
        from channels import publication_authorization as pa
        pa.assert_session_fresh(auth.poll(), max_age_seconds=3600)
        os.environ["FACTORY_LIVE_PUBLISH"] = "true"
        try:
            a = apply(token, gp, a)
        finally:
            os.environ["FACTORY_LIVE_PUBLISH"] = "false"
    report["action"] = a
    REPORT.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"mode": report["mode"], "result": a["result"], "reason": a.get("reason")}))
    return 0 if a["result"] in ("PASS", "PLANNED", "ALREADY_UNPUBLISHED") else 1


if __name__ == "__main__":
    sys.exit(main())
