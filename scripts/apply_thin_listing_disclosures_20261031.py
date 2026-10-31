#!/usr/bin/env python3
"""Thin-listing disclosures found on 2026-10-31 (repair plan: docs/factory/THIN_LISTINGS_REPAIR_PLAN_2026-10-31.md).

Eleven paid listings deliver a 1-3 page file while their page either lists many
components or speaks in general terms. Five sister listings already carry an
honest line, "What you actually receive: a N-page PDF (W words)...". This adds
the same line to the eleven, with the page and word counts MEASURED from the
file each listing delivers right now (downloaded read-only), never typed in.

Nothing else on the listing changes: no price, file, title or wording. Prices
and content expansions are separate founder decisions (see the plan).

Default is a dry run: files are measured, every planned description is
printed to the report, nothing is written to Gumroad. --live needs a fresh
Gumroad session and goes through the write gate and a write scope per listing.

    python scripts/apply_thin_listing_disclosures_20261031.py            # dry run
    python scripts/apply_thin_listing_disclosures_20261031.py --live     # founder decision
"""
import argparse
import io
import json
import os
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
REPORT = ROOT / "data" / "thin_listing_disclosures_20261031.json"
MARK = "**What you actually receive:**"
TARGETS = ["fwrjot", "palmdr", "fccqk", "engiwk", "edgiq", "bfdgx", "roxdbe", "ldrdm", "yhnyn", "zjwpx", "eiebdt"]


def _pdf_stats(data):
    from pypdf import PdfReader
    r = PdfReader(io.BytesIO(data))
    words = sum(len((p.extract_text() or "").split()) for p in r.pages)
    return len(r.pages), words


def measure(data):
    """What a buyer receives, from the file bytes: ('pdf', pages, words) or a ZIP's members."""
    if data[:4] != b"PK\x03\x04":
        pages, words = _pdf_stats(data)
        return {"kind": "pdf", "pages": pages, "words": words}
    z = zipfile.ZipFile(io.BytesIO(data))
    names = z.namelist()
    if "[Content_Types].xml" in names:  # the file itself is a workbook
        return {"kind": "xlsx"}
    members = []
    for n in names:
        if n.lower().endswith(".pdf"):
            p, w = _pdf_stats(z.read(n))
            members.append({"name": os.path.basename(n), "kind": "pdf", "pages": p, "words": w})
        elif n.lower().endswith(".xlsx"):
            from openpyxl import load_workbook
            wb = load_workbook(io.BytesIO(z.read(n)))
            members.append({"name": os.path.basename(n), "kind": "xlsx", "sheets": len(wb.sheetnames)})
    return {"kind": "zip", "members": members}


def disclosure(m):
    def pdf(x):
        return f"a {x['pages']}-page PDF ({x['words']:,} words)"
    if m["kind"] == "pdf":
        what = pdf(m)
    elif m["kind"] == "zip" and m["members"]:
        parts = [pdf(x) if x["kind"] == "pdf" else f"a {x['sheets']}-sheet starter workbook" for x in m["members"]]
        what = "a ZIP with " + " and ".join(parts)
    else:
        return None
    return (f"\n\n{MARK} {what}. It is a condensed operating reference, not an expanded toolkit. "
            "0 sales recorded for this item to date; no reviews.")


def plan(token, gp, fetch=None):
    fetch = fetch or (lambda u: urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}),
                                                       timeout=60).read())
    by_slug = {(p.get("short_url") or "").rstrip("/").rsplit("/", 1)[-1]: p for p in gp.list_products(token)}
    actions = []
    for slug in TARGETS:
        p = by_slug.get(slug)
        if not p:
            actions.append({"slug": slug, "error": "listing not found"})
            continue
        full = gp.get_product(token, p["id"])
        desc = full.get("description") or ""
        base = {"slug": slug, "product_id": p["id"], "name": full.get("name"), "published": bool(full.get("published"))}
        if MARK in desc:
            actions.append({**base, "already_applied": True})
            continue
        files = full.get("files") or []
        if len(files) != 1:
            actions.append({**base, "error": f"expected one attached file, found {len(files)}"})
            continue
        m = measure(fetch(files[0]["url"]))
        line = disclosure(m)
        if not line:
            actions.append({**base, "error": f"nothing to disclose for a {m['kind']} deliverable", "measured": m})
            continue
        actions.append({**base, "measured": m, "added": line.strip(), "old_sha256": __import__("hashlib").sha256(desc.encode()).hexdigest(),
                        "new_description": desc.rstrip() + line})
    return actions


def apply(token, gp, ws, actions):
    done = []
    for a in actions:
        if a.get("error") or a.get("already_applied"):
            done.append({**a, "result": "SKIPPED" if a.get("error") else "ALREADY_APPLIED"})
            continue
        try:
            scope = ws.issue_scope(product_id=a["product_id"], slug=a["slug"], payload={"description": a["new_description"]},
                                   operation="update_description", note="2026-10-31 thin-listing disclosure")
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
