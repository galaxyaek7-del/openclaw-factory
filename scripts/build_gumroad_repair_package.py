#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge -- build the local Gumroad repair package (2026-10-22).

Reads the evidence already gathered (delivery audit, per-product release
packages, cycle88 reconciliation, launch kits) and writes
drafts/release_packages/REPAIR_MANIFEST.json: every proposed live change with
before/after, required files (bytes, sha256, file test), evidence, rollback
and risk. With --queue it also files each action, individually, in the
founder approval queue (gf_ops/founder_approval.py), skipping actions that
an existing PENDING item already covers.

Makes no network call and no Gumroad write. Nothing here is applied.
"""
import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import file_testing_engine as fte  # noqa: E402

PKG = ROOT / "drafts" / "release_packages"
AUDIT = ROOT / "reports" / "GUMROAD_DELIVERY_AUDIT_2026-10-22.json"
RECON = ROOT / "data" / "cycle88_catalog_reconciliation.json"


def file_entry(rel):
    p = ROOT / rel
    b = p.read_bytes()
    r = fte.test_file(p)
    e = {"path": rel, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest(), "file_test": r.status}
    if rel.endswith(".xlsx"):
        e.update(sheets=r.detail.get("sheet_count"), formulas=r.detail.get("formula_count"))
    else:
        e.update(pages=r.detail.get("pages"))
    return e


def action(slug, product, kind, rec, before, after, files, evidence, rollback, risk="LOW"):
    return {"slug": slug, "product": product, "action": kind, "recommendation": rec,
            "before": before, "after": after, "required_files": [file_entry(f) for f in files],
            "evidence": evidence, "rollback": rollback, "risk": risk,
            "founder_approval_required": True, "status": "PREPARED_NOT_APPLIED"}


def build_actions():
    pk = {d.name: json.loads((d / "release_package.json").read_text(encoding="utf-8"))
          for d in PKG.iterdir() if (d / "release_package.json").exists()}
    gate = "release gate with the workbook: {} ({})"
    A = [
        action("fetmu", "GPSR EU Seller Action Kit", "attach_file+reword", "REPAIR",
               "Live: 1 PDF (18,208 B). Listing: 'YOU RECEIVE: PDF guide + PDF cost planner (...)'. "
               "Guide chapter 7 points to a companion .xlsx the buyer never receives.",
               "Attach the cost planner workbook; listing: 'PDF guide + XLSX cost planner workbook (4 sheets: ...)'.",
               ["books/gpsr_eu_seller_cost_planner.xlsx"],
               ["named in books/gpsr_eu_seller_action_kit_launch_kit.md",
                "sha256 equals data/cycle88_artifact_checksums.json",
                "already requested by founder_approvals.jsonl item 105b50b9f45f (PENDING since 2026-10-17)",
                gate.format(pk["fetmu"]["gate_status"], "; ".join(pk["fetmu"]["holds"]))],
               "Remove the workbook; restore the previous sentence (drafts/release_packages/fetmu/release_package.json)."),
        action("vkqogv", "Trademark DIY Filing Action Kit", "attach_file+reword", "REPAIR",
               "Live: 1 PDF (12,383 B). Listing promises 'a four-sheet docket tracker (...)'; no spreadsheet attached. "
               "Below the substance bar as live: 1,705 words for $69.",
               "Attach the tracker; listing: 'a four-sheet XLSX docket tracker (clearance search log, specimen file, "
               "docket tracker, fee math)'.",
               ["books/trademark_filing_tracker.xlsx"],
               ["named in books/trademark_diy_filing_kit_launch_kit.md", "sheet names match the listing promise",
                "sha256 equals cycle88 checksum record",
                gate.format(pk["vkqogv"]["gate_status"], "; ".join(pk["vkqogv"]["holds"]))],
               "Remove the workbook; restore the previous sentence."),
    ]
    for slug, wb in [("adyvd", "turo_guest_dispute_tracker"), ("ppsluq", "str_direct_booking_planner"),
                     ("pyzqa", "vendor_questionnaire_tracker"), ("gfsvu", "epr_packaging_register"),
                     ("dyjavs", "diminished_value_claim_pack")]:
        p = pk[slug]
        ev = ["named in the product's launch kit (books/*_launch_kit.md)", "sha256 equals cycle88 checksum record",
              "file test PASS", gate.format(p["gate_status"], "; ".join(p["holds"]))]
        if slug == "dyjavs":
            ev.append("data/c99_founder_actions.json: 'Optional: attach books/diminished_value_claim_pack.xlsx'")
        A.append(action(slug, p["name"], "attach_file", "REPAIR",
                        f"Live: PDF only {p['live_files']}. A working local workbook was never attached.",
                        "Attach the workbook; add one sentence naming it in the description (founder wording).",
                        [f"books/{wb}.xlsx"], ev, "Remove the attached workbook."))
    for slug, name, pdf, wb, live_proof in [
            ("ekhza", "FTC Consumer Review Rule Compliance Kit", "books/ftc_review_rule_compliance_kit.pdf",
             "books/ftc_review_rule_audit_tracker.xlsx", "live sha256 equals the LF-normalized pre-fix copy"),
            ("dvfvm", "Restaurant Health Inspection Readiness Kit", "books/restaurant_inspection_readiness_kit.pdf",
             "books/restaurant_inspection_logs.xlsx", "live sha256 equals the LF-normalized pre-fix copy"),
            ("palmdr", "ADA Demand-Letter Response & Triage Kit", "books/ada_demand_response_kit.pdf",
             "books/ada_triage_workbook.xlsx", "live size equals the LF-normalized pre-fix copy (no live hash on record)")]:
        A.append(action(slug, name, "replace_file+attach_file", "REPAIR",
                        "Live PDF is the pre-2026-10-17 version: page-1 title printed over the subtitle "
                        f"(file_testing_engine FAIL: text overlap); {live_proof}. No workbook attached.",
                        "Replace the PDF with the repaired file (title fix; file test PASS; same pages and words) "
                        "and attach the companion workbook.",
                        [pdf, wb],
                        ["reports/cleanup/PDF_REPLACEMENTS.md (2026-10-17) lists this re-upload as a pending founder action",
                         "workbook named in the launch kit; sha256 equals cycle88 record"],
                        f"Re-upload books/_rollback_2026-10-22/{os.path.basename(pdf)} (byte-identical to the "
                        "current live file) and remove the workbook."))
    A += [
        action("iaiyt", "EU AI Act Compliance Toolkit", "remove_file", "REPAIR",
               "Live: 2 PDFs -- full v2 (139,401 B, 31 pages) and 'eu_ai_act_compliance_toolkit_preview' "
               "(106,314 B, 3 pages, 209 words).",
               "Deliver the full v2 only; keep the excerpt as the listing preview, not as a deliverable.", [],
               ["preview: 3 pages / 209 words; 21 of its lines appear verbatim in v2 (a redundant excerpt)",
                "local v2 sha256 equals the live file (data/delivery_integrity.json)"],
               "Re-attach books/_rollback_2026-10-22/eu_ai_act_compliance_toolkit_preview.pdf (byte-identical to live)."),
        action("owtmpe", "[Unavailable] AI Workflow QA & Stress Test", "unpublish", "PROPOSE_UNPUBLISH",
               "Published at $0 with no file and a 9-character description: a 'purchase' delivers nothing.",
               "Unpublished.", [],
               ["Gumroad API: published=true, files=0, no custom delivery URL",
                "also targeted by founder_approvals.jsonl fd394165c746, whose second target (iaiyt) is wrong"],
               "Republish from the Gumroad dashboard."),
        action("vhofn", "The 5-Minute Context Reset Playbook (second listing)", "unpublish", "PROPOSE_UNPUBLISH",
               "Two published listings, same title, $15 each. vhofn: 10 pages / 501 words, not linked from the site; "
               "akxaae: 9 pages / 1,612 words, linked from the site. Different sha256.",
               "Keep akxaae; unpublish vhofn (the thinner variant).", [],
               ["data/delivery_integrity.json per-file words and sha256", "customer_site links akxaae only"],
               "Republish vhofn."),
        action("dxfwlu", "GALAXY FORGE API TEST - DO NOT BUY - DELETE ME", "delete", "PROPOSE_DELETE",
               "Unpublished test product (102-byte txt).", "Deleted from the account.", [],
               ["Gumroad API: published=false; title says DELETE ME"], "None needed (test artefact).", "NONE"),
    ]
    return A


def thin_review(handled):
    aud = {r["slug"]: r for r in json.loads(AUDIT.read_text(encoding="utf-8"))["rows"]}
    rec = json.loads(RECON.read_text(encoding="utf-8"))
    items = rec if isinstance(rec, list) else next(
        v for v in rec.values() if isinstance(v, list) and v and isinstance(v[0], dict) and "slug" in v[0])
    by = {i["slug"]: i for i in items}
    out = []
    for slug, a in aud.items():
        if slug in handled or not ({"THIN_DELIVERABLE", "PUBLISHED_WITHOUT_DELIVERABLE"} & set(a["issues"])):
            continue
        c = by.get(slug, {})
        words, price, types = c.get("words"), a.get("price_usd") or 0, a.get("attached_types")
        if not a["published"]:
            r, why = "KEEP (unpublished)", "not live"
        elif types == ["xlsx"]:
            r, why = "HOLD", "deliverable is a workbook; byte size is no content measure -- verify formulas on a downloaded copy"
        elif types == ["zip"]:
            r, why = "HOLD", "ZIP contents cannot be verified through the API"
        elif words is None:
            r, why = "HOLD", "word count UNKNOWN"
        elif price and words / price < 10:
            r, why = "PROPOSE_UNPUBLISH (or reprice/expand)", f"{words} words for ${price:g} = {words / price:.1f} words/$ (<10)"
        elif price and words / price < 25:
            r, why = "HOLD (expand or reprice)", f"{words} words for ${price:g} = {words / price:.1f} words/$ (<25)"
        else:
            r, why = "KEEP", f"{words} words for ${price:g}"
        if re.search(r"calculator|workbook", a["name"], re.I) and types == ["pdf"]:
            why += "; the title promises a calculator/workbook but only a PDF is attached"
        out.append({"slug": slug, "product": a["name"], "published": a["published"], "price_usd": price,
                    "live_bytes": a.get("attached_bytes"), "live_types": types, "local_file": c.get("local_file"),
                    "pages": c.get("pages"), "words": words, "recommendation": r, "basis": why})
    return sorted(out, key=lambda t: (t["recommendation"], -t["price_usd"]))


def queue_actions(actions):
    from gf_ops import founder_approval as fa
    covered = {(i.get("target"), i.get("action")) for i in fa.pending()}
    added = []
    for a in actions:
        target = f"gumroad:{a['slug']}"
        if (target, a["action"]) in covered:
            continue
        files = ", ".join(f"{f['path']} ({f['bytes']} B)" for f in a["required_files"]) or "none"
        item = fa.add_item(
            action=a["action"], target=target,
            change=f"{a['after']} Files: {files}.",
            reason=a["before"],
            expected_effect="The listing delivers exactly what it promises; release gate clears for this product.",
            risk=a["risk"],
            validation_plan="After the edit, rerun scripts/gumroad_delivery_audit.py and confirm this slug's issues are gone; "
                            "hashes in drafts/release_packages/REPAIR_MANIFEST.json.",
            rollback=a["rollback"])
        added.append(item["item_id"])
    return added


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", action="store_true", help="also file each action in the founder approval queue")
    args = ap.parse_args()
    actions = build_actions()
    thin = thin_review({a["slug"] for a in actions})
    manifest = {"generated_at": datetime.now(timezone.utc).isoformat(), "status": "PREPARED_NOT_APPLIED",
                "constraints": "No Gumroad write, upload, unpublish or delete was performed. "
                               "FACTORY_LIVE_PUBLISH=false. Spend $0.",
                "actions": actions, "thin_product_review": thin,
                "approval_queue": "data/founder_approvals.jsonl (gf_ops/founder_approval.py)"}
    (PKG / "REPAIR_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"actions": Counter(a["recommendation"] for a in actions),
                      "thin_review": Counter(t["recommendation"] for t in thin)}, ensure_ascii=False))
    if args.queue:
        print("queued:", queue_actions(actions))


if __name__ == "__main__":
    main()
