#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cycle 104 -- build uniform, validated listing payloads for B12-002/005/010.

WHY
---
All three products are gate-approved and unpublished, and real paste-ready copy
already exists in `drafts/b12_00X_listing_copy.txt`. But the *registry* is the
only machine-readable surface and its `listing_copy` field is inconsistent:
B12-002 inlines a full dict, B12-005 omits the field entirely (its copy exists
only as a draft file), and B12-010 stores the 31-character string
`"drafts/b12_010_listing_copy.txt"` where a reader expects copy. Any automated
listing step would therefore read nothing for two of the three products.

This produces one uniform payload per product, from the real draft copy, with
real file hashes, the real price source, the real gate citation, and a Trust
Framework validation pass -- so publication becomes a single founder-authorized
action instead of three bespoke ones.

IT NEVER PUBLISHES. No Gumroad call is made at all. Output is a local report.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

FACTORY = Path(__file__).resolve().parent.parent
if str(FACTORY) not in sys.path:
    sys.path.insert(0, str(FACTORY))

REGISTRY = FACTORY / "data" / "product_batch_12_gumroad_prep.json"
OUT_DIR = FACTORY / "reports" / "CYCLE104"

PRODUCTS = {
    "B12-002": {"copy": "drafts/b12_002_listing_copy.txt",
                "gate": "reports/B12-002/GATE_FINAL_2026-10-18.json",
                "cover": "reports/B12-002/cover.png",
                "page": "customer_site/b12-client-handoff-pack.html"},
    "B12-005": {"copy": "drafts/b12_005_listing_copy.txt",
                "gate": "reports/B12-005/GATE_FINAL_2026-10-19.json",
                "cover": "reports/B12-005/cover.png",
                "page": "customer_site/b12-podcast-guest-kit.html"},
    "B12-010": {"copy": "drafts/b12_010_listing_copy.txt",
                "gate": "reports/B12-010/GATE_FINAL_2026-10-19.json",
                "cover": "books/covers/B12-010.png",
                "page": "customer_site/b12-grant-pipeline-tracker.html"},
}

#: The exact phrase the founder must approve, one line per product. Kept
#: product-specific on purpose: a generic "publish stuff" approval would not
#: satisfy the standing rule that authorization is per-listing.
AUTHORIZATION_TEMPLATE = ("I authorize publishing {id} \u2014 {title} \u2014 to Gumroad at "
                          "{price} USD with the exact files listed in "
                          "reports/CYCLE104/LISTING_PAYLOADS_B12.json")


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def parse_copy(text: str) -> dict:
    """Split the copy-paste file on its own 'LABEL:' section headers."""
    lines = text.replace("\r\n", "\n").split("\n")
    sections: dict[str, list[str]] = {}
    current = None
    for ln in lines:
        m = re.match(r"^([A-Z][A-Z /]+):\s*$", ln)
        if m:
            current = m.group(1).strip()
            sections[current] = []
            continue
        if current is not None:
            sections[current].append(ln)
    out = {}
    for key, body in sections.items():
        joined = "\n".join(body).strip()
        out[key.lower().replace(" ", "_")] = joined
    return out


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    import brand_dna

    reg = json.loads(REGISTRY.read_text(encoding="utf-8-sig"))
    items = {it["id"]: it for it in reg["items"]}

    payloads = []
    for pid, spec in PRODUCTS.items():
        item = items[pid]
        copy_path = FACTORY / spec["copy"]
        raw = copy_path.read_text(encoding="utf-8-sig")
        sec = parse_copy(raw)

        title = sec.get("title", "").strip()
        description = sec.get("description", "").strip()
        tags = [t.strip() for t in sec.get("tags", "").replace("\n", ",").split(",")
                if t.strip()]
        copy_files = [ln.strip() for ln in sec.get("files_to_upload", "").split("\n")
                      if ln.strip() and ln.strip().endswith((".xlsx", ".pdf", ".png"))]

        files = []
        for rel in item.get("files") or []:
            fp = FACTORY / "books" / "batch12" / rel
            files.append({"path": "books/batch12/%s" % rel, "exists": fp.exists(),
                          "bytes": fp.stat().st_size if fp.exists() else None,
                          "sha256": sha256(fp) if fp.exists() else None})
        for rel in copy_files:
            fp = FACTORY / rel
            if fp.exists() and all(f["path"] != rel for f in files):
                files.append({"path": rel, "exists": True, "bytes": fp.stat().st_size,
                              "sha256": sha256(fp), "from": "copy file list"})

        cover = FACTORY / spec["cover"]
        page = FACTORY / spec["page"]
        gate = FACTORY / spec["gate"]

        cover_dims = None
        if cover.exists():
            try:
                from PIL import Image
                with Image.open(cover) as im:
                    cover_dims = [im.width, im.height]
            except Exception as exc:  # noqa: BLE001
                cover_dims = "UNREADABLE: %r" % (exc,)

        validation = brand_dna.validate_customer_facing_text(
            (title + "\n\n" + description).strip())
        price_usd = item.get("proposed_price_usd")

        problems = []
        if not title:
            problems.append("no TITLE parsed from the copy file")
        if not description:
            problems.append("no DESCRIPTION parsed from the copy file")
        if not tags:
            problems.append("no TAGS parsed from the copy file")
        if any(not f["exists"] for f in files):
            problems.append("a declared deliverable file is missing")
        if not cover.exists():
            problems.append("cover image missing: %s" % spec["cover"])
        m_dims = re.search(r"(\d{3,4})x(\d{3,4})", raw)
        if cover_dims and m_dims:
            claimed = [int(m_dims.group(1)), int(m_dims.group(2))]
            if isinstance(cover_dims, list) and cover_dims != claimed:
                problems.append("cover dimensions %s do not match the copy's claim %s"
                                % (cover_dims, claimed))
        if not page.exists():
            problems.append("customer page missing: %s" % spec["page"])
        if not gate.exists():
            problems.append("gate record missing: %s" % spec["gate"])
        if not validation["passed"]:
            problems.append("Trust Framework validation failed: %s"
                            % validation["failed_checks"])
        if "$%.2f" % (price_usd or 0) not in sec.get("price", ""):
            problems.append("copy PRICE (%r) does not match registry price %s"
                            % (sec.get("price", "").splitlines()[:1], price_usd))

        if problems:
            state = "NOT_READY"
        else:
            state = "READY_TO_PUBLISH__AWAITS_FOUNDER_AUTHORIZATION"

        payloads.append({
            "id": pid,
            "title": title,
            "registry_title": item.get("title"),
            "description": description,
            "tags": tags,
            "price_usd": price_usd,
            "price_cents": int(round((price_usd or 0) * 100)),
            "price_basis": item.get("price_status"),
            "copy_source": spec["copy"],
            "registry_listing_copy_shape": type(item.get("listing_copy")).__name__,
            "files": files,
            "cover": spec["cover"],
            "cover_exists": cover.exists(),
            "cover_dimensions": cover_dims,
            "customer_page": spec["page"],
            "customer_page_exists": page.exists(),
            "gate": spec["gate"],
            "gate_exists": gate.exists(),
            "trust_validation": {"passed": validation["passed"],
                                 "failed_checks": validation["failed_checks"]},
            "state": state,
            "problems": problems,
            "authorization_required": AUTHORIZATION_TEMPLATE.format(
                id=pid, title=title or item.get("title"), price="%.2f" % (price_usd or 0)),
            "published": False,
        })

    doc = {
        "schema": "galaxy_forge.b12_listing_payloads.v1",
        "generated_at": datetime.datetime.now(
            datetime.timezone.utc).isoformat(timespec="seconds"),
        "cost_usd": 0,
        "gumroad_calls_made": 0,
        "published_anything": False,
        "note": ("Local preparation only. Nothing here creates or publishes a listing; "
                 "every product stays unpublished until the founder authorizes it "
                 "explicitly and the publication gate is opened."),
        "products": payloads,
        "ready_count": sum(1 for p in payloads
                           if p["state"].startswith("READY_TO_PUBLISH")),
    }

    if a.write:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "LISTING_PAYLOADS_B12.json").write_text(
            json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
        md = ["# Cycle 104 \u2014 listing preparation for B12-002 / B12-005 / B12-010", "",
              "Local only. No Gumroad call was made. Nothing was published.", "",
              "| id | state | price | files | cover | page | gate | trust |",
              "|---|---|---|---|---|---|---|---|"]
        for p in payloads:
            md.append("| %s | %s | $%.2f | %d | %s | %s | %s | %s |" % (
                p["id"], p["state"], p["price_usd"] or 0, len(p["files"]),
                "Y" if p["cover_exists"] else "N",
                "Y" if p["customer_page_exists"] else "N",
                "Y" if p["gate_exists"] else "N",
                "PASS" if p["trust_validation"]["passed"] else "FAIL"))
        md += ["", "## Exact authorization needed", ""]
        for p in payloads:
            md.append("- `%s`" % p["authorization_required"])
        md += ["", "## Registry shape drift found", "",
               "The machine-readable `listing_copy` field is not uniform across these "
               "products, which is why an automated listing step could not read two of "
               "them:", ""]
        for p in payloads:
            md.append("- %s: `listing_copy` is a %s"
                      % (p["id"], p["registry_listing_copy_shape"]))
        md.append("")
        if any(p["problems"] for p in payloads):
            md += ["## Blocking problems", ""]
            for p in payloads:
                for pr in p["problems"]:
                    md.append("- %s: %s" % (p["id"], pr))
            md.append("")
        (OUT_DIR / "LISTING_PREP_B12.md").write_text("\n".join(md), encoding="utf-8")

    for p in payloads:
        print("%-8s %-42s price=$%-6s files=%d trust=%s problems=%s"
              % (p["id"], p["state"], p["price_usd"], len(p["files"]),
                 "PASS" if p["trust_validation"]["passed"] else "FAIL",
                 p["problems"] or "none"))
    print("\nready: %d/%d" % (doc["ready_count"], len(payloads)))
    if a.write:
        print("written: %s" % (OUT_DIR / "LISTING_PAYLOADS_B12.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
