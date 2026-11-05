#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Add the "What you actually receive" line to the ten batch-18 listings (2026-11-05).

The line already exists on the thin listings (apply_thin_listing_disclosures_20261031.py). Batch 18's run
script promised it and the first publish did not carry it, so a buyer saw file names but not how much
there is. The facts are MEASURED from the bundle each listing delivers (the local bundle, whose size and hash
the publisher already matched to the upload): sheet count and names, guide pages and words. Nothing is typed in.

Nothing else on a listing changes: no price, title, file or tag. Idempotent (a listing that already has the line
is skipped). Dry run by default; --live needs a fresh Gumroad session and goes through the write gate and one
write scope per listing, like the 2026-10-31 script.

    python scripts/apply_batch18_listing_facts.py            # dry run, writes data/batch18_listing_facts.json
    python scripts/apply_batch18_listing_facts.py --live
"""
import argparse
import hashlib
import io
import json
import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
REPORT = ROOT / "data" / "batch18_listing_facts.json"
MARK = "What you actually receive:"


def measure_bundle(path):
    """Sheets of the workbook and pages/words of the guide, read from the bundle bytes."""
    from openpyxl import load_workbook
    from pypdf import PdfReader
    z = zipfile.ZipFile(path)
    sheets, pages, words = None, None, None
    for n in z.namelist():
        if n.lower().endswith(".xlsx"):
            sheets = load_workbook(io.BytesIO(z.read(n))).sheetnames
        elif n.lower().endswith(".pdf"):
            r = PdfReader(io.BytesIO(z.read(n)))
            pages = len(r.pages)
            words = sum(len((p.extract_text() or "").split()) for p in r.pages)
    if sheets is None or pages is None:
        raise ValueError(f"{path}: bundle lacks a workbook or a guide")
    return {"sheets": sheets, "pages": pages, "words": words}


def line_html(m):
    names = ", ".join(m["sheets"])
    return (f"<p><strong>{MARK}</strong> a ZIP containing a {len(m['sheets'])}-sheet Excel workbook ({names}) and a "
            f"{m['pages']}-page PDF guide ({m['words']:,} words). No sales or reviews yet; the example figures inside "
            f"the workbook are illustrative.</p>")


def plan(token, gp):
    by_slug = {(p.get("short_url") or "").rstrip("/").rsplit("/", 1)[-1]: p for p in gp.list_products(token)}
    results = json.loads((ROOT / "data" / "batch18_publish_results.json").read_text(encoding="utf-8"))
    urls = {}
    for run in results:
        for r in run.get("results", []):
            if r.get("url") and r.get("steps", {}).get("published"):
                urls[r["id"]] = r["url"].rstrip("/").rsplit("/", 1)[-1]
    actions = []
    for pid in sorted(urls):
        slug = urls[pid]
        man = json.loads((ROOT / "books" / "batch18" / pid / "manifest.json").read_text(encoding="utf-8"))
        p = by_slug.get(slug)
        if not p:
            actions.append({"id": pid, "slug": slug, "error": "listing not found"})
            continue
        full = gp.get_product(token, p["id"])
        desc = full.get("description") or ""
        base = {"id": pid, "slug": slug, "product_id": p["id"], "name": full.get("name"), "price_cents": full.get("price"),
                "published": bool(full.get("published"))}
        if MARK in desc:
            actions.append({**base, "already_applied": True})
            continue
        m = measure_bundle(ROOT / man["files"]["bundle"]["path"])
        add = line_html(m)
        actions.append({**base, "measured": m, "added": add, "old_sha256": hashlib.sha256(desc.encode()).hexdigest(),
                        "new_description": desc.rstrip() + add})
    return actions


def apply(token, gp, ws, actions):
    done = []
    for a in actions:
        if a.get("error") or a.get("already_applied"):
            done.append({**a, "result": "SKIPPED" if a.get("error") else "ALREADY_APPLIED"})
            continue
        try:
            scope = ws.issue_scope(product_id=a["product_id"], slug=a["slug"], payload={"description": a["new_description"]},
                                   operation="update_description", note="2026-11-05 batch 18 listing facts")
            gp.update_product_description_scoped(token, a["product_id"], a["new_description"], scope_id=scope.scope_id)
            done.append({**a, "result": "PASS"})
        except Exception as e:  # each listing stands alone
            done.append({**a, "result": "FAILED", "reason": f"{type(e).__name__}: {str(e)[:300]}"})
    return done


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args(argv)
    from channels import gumroad_publisher as gp
    token = gp.load_token()
    actions = plan(token, gp)
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "mode": "LIVE" if args.live else "DRY_RUN"}
    if args.live:
        import gumroad_auth_watch as auth
        from channels import publication_authorization as pa
        from channels import write_scope as ws
        pa.assert_session_fresh(auth.poll(), max_age_seconds=3600)
        os.environ["FACTORY_LIVE_PUBLISH"] = "true"
        try:
            report["actions"] = apply(token, gp, ws, actions)
        finally:
            os.environ["FACTORY_LIVE_PUBLISH"] = "false"
    else:
        report["actions"] = [{**a, "result": "SKIPPED" if a.get("error") else
                              ("ALREADY_APPLIED" if a.get("already_applied") else "PLANNED")} for a in actions]
    REPORT.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    summary = {}
    for a in report["actions"]:
        summary[a["result"]] = summary.get(a["result"], 0) + 1
    print(json.dumps({"mode": report["mode"], "summary": summary, "report": str(REPORT.relative_to(ROOT))}))
    return 0 if all(a["result"] in ("PASS", "PLANNED", "ALREADY_APPLIED") for a in report["actions"]) else 1


if __name__ == "__main__":
    sys.exit(main())
