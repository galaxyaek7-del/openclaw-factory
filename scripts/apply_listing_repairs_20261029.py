#!/usr/bin/env python3
"""Listing repairs found on 2026-10-29 (risk R13, backlog B41/B42).

  vkqogv  Trademark DIY Filing Action Kit ($69): the listing promises a
          four-sheet XLSX tracker that was never attached, and the guide
          quoted two USPTO fees wrongly. Deliverable becomes a bundle of the
          guide v2 (original pages + a dated fee-correction page) and the
          repaired tracker (fee sheet rebuilt on the USPTO schedule).
  fetmu   GPSR EU Seller Action Kit ($79): the listing promises a cost
          planner that was never attached. Deliverable becomes a bundle of
          the guide and the repaired cost-planner workbook.
  ciowwm, hasjmp, dyjavs ($59, $39, $59): each guide refers to a tracker or
          workbook that exists locally but was never attached; bundled with
          the exact live PDF, descriptions say what the buyer now receives.
  27 listings (batches 14-16) say "... and this guide." on the listing page,
          where no guide is in view: "and a PDF guide." instead.

Default is a dry run: bundles are built and file-tested locally, live state
is read with GET only, and every planned change is printed. Nothing is
written to Gumroad.

    python scripts/apply_listing_repairs_20261029.py            # dry run
    python scripts/apply_listing_repairs_20261029.py --live     # apply

With --live each write gets its own single-use scope (channels/write_scope)
and is verified by re-read inside channels/gumroad_publisher; the central
write gate (FACTORY_LIVE_PUBLISH, fresh VERIFIED auth state) still applies,
and FACTORY_LIVE_PUBLISH is set back to false when the run ends.
Results: data/listing_repairs_20261029.json.
"""
import argparse
import hashlib
import json
import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT = ROOT / "books" / "repairs_20261029"
REPORT = ROOT / "data" / "listing_repairs_20261029.json"
OLD_PHRASE, NEW_PHRASE = " and this guide.", " and a PDF guide."
BUNDLES = {
    "vkqogv": ("trademark_diy_filing_kit_bundle.zip",
               ["books/trademark_diy_filing_kit_v2.pdf", "books/trademark_filing_tracker.xlsx"]),
    # The exact live PDF (18,208 B, matches the delivery audit); the 21 Sep
    # local build in books/ has the same text but different bytes.
    "fetmu": ("gpsr_eu_seller_action_kit_bundle.zip",
              ["backups/catalog_audit_2026-10-14/VPYaNkAdv7Yocko-lIJsZQ_0.pdf", "books/gpsr_eu_seller_cost_planner.xlsx"]),
    # Each guide below points at its workbook ("tracker", "workbook sheet 1") but
    # only the PDF was ever attached. The PDFs are the exact live files (byte
    # sizes match the delivery audit); the workbooks recalculate with 0 errors
    # (lib/xlsx_eval: 1,224 / 1,427 / 209+2 COUNTIFS formulas).
    "ciowwm": ("eu_late_payment_recovery_kit_bundle.zip",
               ["factory_workspace/sprint14/eu_late_payment_recovery_kit.pdf", "books/eu_late_payment_calculator.xlsx"]),
    "hasjmp": ("etsy_ads_roi_playbook_bundle.zip",
               ["factory_workspace/sprint14/etsy_ads_roi_playbook.pdf", "books/etsy_ads_roi_calculator.xlsx"]),
    "dyjavs": ("diminished_value_claim_kit_bundle.zip",
               ["backups/catalog_audit_2026-10-14/f542PZ92SUPOjV9F5GJh-Q_0.pdf", "books/diminished_value_claim_pack.xlsx"]),
}
ARCHIVE_NAMES = {  # backup copies carry a Gumroad product id as their name
    "backups/catalog_audit_2026-10-14/f542PZ92SUPOjV9F5GJh-Q_0.pdf": "diminished_value_claim_kit.pdf",
    "backups/catalog_audit_2026-10-14/VPYaNkAdv7Yocko-lIJsZQ_0.pdf": "gpsr_eu_seller_action_kit.pdf",
}
SINGLE_FILE = "A single, focused file you download and use immediately"
DESCRIPTION_EDITS = {
    # fetmu's listing calls the planner a PDF; it is a workbook.
    "fetmu": [("PDF cost planner", "XLSX cost planner workbook")],
    # The delivery line must name what the bundle now contains.
    "vkqogv": [("Instant digital download. PDF guide.",
                "Instant digital download: PDF guide (with a dated USPTO fee-correction page) and the four-sheet XLSX docket tracker.")],
    "ciowwm": [(SINGLE_FILE, "A short PDF guide plus a working XLSX calculator workbook (invoice tracker, notice ladder)")],
    "hasjmp": [(SINGLE_FILE, "A short PDF playbook plus the XLSX calculator workbook (per-listing tracker, readiness check)")],
    "dyjavs": [("3-page PDF guide covering", "3-page PDF guide plus a six-sheet XLSX claim workbook, covering")],
}


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def archive_name(member):
    return ARCHIVE_NAMES.get(member, Path(member).name.replace("_v2.pdf", ".pdf"))


def build_bundle(slug):
    import file_testing_engine as fte
    name, members = BUNDLES[slug]
    OUT.mkdir(parents=True, exist_ok=True)
    dst = OUT / name
    tmp = dst.with_suffix(".zip.tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for m in members:
            src = ROOT / m
            z.write(src, archive_name(m))
    os.replace(tmp, dst)
    results = {m: fte.test_file(ROOT / m).status for m in members}
    return {"path": str(dst.relative_to(ROOT)), "bytes": dst.stat().st_size, "sha256": sha256(dst),
            "members": [archive_name(m) for m in members], "member_file_tests": results,
            "ok": all(s == "PASS" for s in results.values())}


def plan(token, gp):
    products = gp.list_products(token)
    by_slug = {}
    for p in products:
        slug = (p.get("short_url") or "").rstrip("/").rsplit("/", 1)[-1]
        by_slug[slug] = p
    actions = []
    for slug in BUNDLES:
        p = by_slug.get(slug)
        if not p:
            actions.append({"slug": slug, "kind": "attach_bundle", "error": "listing not found"})
            continue
        b = build_bundle(slug)
        # Idempotent: a listing whose attachment already has exactly the
        # bundle's size is the repaired state; it is not uploaded again.
        live_sizes = [f.get("size") for f in (gp.get_product(token, p["id"]).get("files") or [])]
        actions.append({"slug": slug, "kind": "attach_bundle", "product_id": p["id"], "name": p.get("name"),
                        "bundle": b, "live_file_sizes": live_sizes,
                        "already_applied": b["bytes"] in live_sizes})
    for slug, p in sorted(by_slug.items()):
        desc = p.get("description") or ""
        new = desc.replace(OLD_PHRASE, NEW_PHRASE)
        for old, rep in DESCRIPTION_EDITS.get(slug, []):
            new = new.replace(old, rep)
        if new != desc:
            actions.append({"slug": slug, "kind": "update_description", "product_id": p["id"],
                            "name": p.get("name"), "published": bool(p.get("published")),
                            "old_sha256": hashlib.sha256(desc.encode()).hexdigest(),
                            "new_description": new,
                            "changes": [c for c in ([(OLD_PHRASE, NEW_PHRASE)] + DESCRIPTION_EDITS.get(slug, []))
                                        if c[0] in desc]})
    return actions


def apply(token, gp, ws, actions):
    done = []
    for a in actions:
        if a.get("error") or (a["kind"] == "attach_bundle" and not a["bundle"]["ok"]):
            done.append({**a, "result": "SKIPPED", "reason": a.get("error") or "bundle member failed its file test"})
            continue
        if a.get("already_applied"):
            done.append({**a, "result": "ALREADY_APPLIED"})
            continue
        try:
            if a["kind"] == "attach_bundle":
                path = str(ROOT / a["bundle"]["path"])
                scope = ws.issue_scope(product_id=a["product_id"], slug=a["slug"], payload={"file_path": path},
                                       operation="upload_file", note="2026-10-29 listing repair (founder authority)")
                gp.update_product_file(token, a["product_id"], path, upload_scope_id=scope.scope_id)
            else:
                scope = ws.issue_scope(product_id=a["product_id"], slug=a["slug"],
                                       payload={"description": a["new_description"]},
                                       operation="update_description", note="2026-10-29 listing repair")
                gp.update_product_description_scoped(token, a["product_id"], a["new_description"],
                                                     scope_id=scope.scope_id)
            done.append({**a, "result": "PASS"})
        except Exception as e:  # each action stands alone; one failure never hides the rest
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
        state = auth.poll()
        pa.assert_session_fresh(state, max_age_seconds=3600)
        os.environ["FACTORY_LIVE_PUBLISH"] = "true"
        try:
            report["actions"] = apply(token, gp, ws, actions)
        finally:
            os.environ["FACTORY_LIVE_PUBLISH"] = "false"
    else:
        report["actions"] = [{**a, "result": "ALREADY_APPLIED" if a.get("already_applied") else "PLANNED"}
                             for a in actions]
    tmp = REPORT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, REPORT)
    summary = {}
    for a in report["actions"]:
        summary.setdefault(f"{a['kind']}:{a['result']}", 0)
        summary[f"{a['kind']}:{a['result']}"] += 1
    print(json.dumps({"mode": report["mode"], "summary": summary, "report": str(REPORT.relative_to(ROOT))}))
    return 0 if all(a["result"] in ("PASS", "PLANNED", "ALREADY_APPLIED") for a in report["actions"]) else 1


if __name__ == "__main__":
    sys.exit(main())
