#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Assemble a bundle zip from products that are ALREADY built and QA-passed (2026-11-06). Publishes nothing.

    python scripts/build_bundle.py B14        # all live B14-* products -> books/bundles/B14_bundle/

Why a bundle: raises the order value of a visitor who is already interested, costs no new production and no new model calls.
The bundle contains each product's own existing *_bundle.zip (workbook + guide), unchanged, a README and a manifest with
SHA-256 of every file. Price rule: 60% of the sum of the individual prices (rounded down to a whole dollar), never an
invented "was" price: the page shows the real individual prices. The listing text is written to the output folder for the
normal gated publishing path (Quality Gate + approval); this script never touches Gumroad.
"""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "customer_site" / "catalog.json"


def sha(path):
    h = hashlib.sha256()
    h.update(Path(path).read_bytes())
    return h.hexdigest()


def pick(prefix, catalog_products):
    return sorted((p for p in catalog_products if p["id"].startswith(prefix + "-")), key=lambda p: p["id"])


def price_for(prods):
    return int(sum(p["price_cents"] for p in prods) / 100 * 0.6)


def build(prefix, root=ROOT, products=None, out_dir=None):
    products = products if products is not None else json.loads(CATALOG.read_text(encoding="utf-8"))["data"]["products"]
    chosen = pick(prefix, products)
    out = Path(out_dir) if out_dir else root / "books" / "bundles" / f"{prefix}_bundle"
    out.mkdir(parents=True, exist_ok=True)
    members, missing = [], []
    for p in chosen:
        folder = root / "books" / ("batch" + prefix[1:]) / p["id"]
        zips = sorted(folder.glob("*_bundle.zip"))
        if not zips:
            missing.append(p["id"])
            continue
        members.append((p, zips[0]))
    if not members:
        return {"ok": False, "reason": "no product files found", "missing": missing}
    zpath = out / f"{prefix}_money_decisions_bundle.zip"
    manifest = []
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p, zp in members:
            arc = f"{p['id']}_{zp.name}"
            z.write(zp, arc)
            manifest.append({"id": p["id"], "title": p["title"], "price_usd": p["price_cents"] / 100, "file": arc, "sha256": sha(zp)})
        z.writestr("README.txt", "Each folder-less zip inside is one complete tool: an Excel workbook plus its short PDF guide.\n"
                   "Open the zip you need, read the guide first, then enter your own numbers in the workbook's input cells.\n"
                   "Files are unchanged copies of the individually sold products.\n")
        z.writestr("MANIFEST.json", json.dumps(manifest, indent=1))
    total = sum(m["price_usd"] for m in manifest)
    price = price_for([p for p, _ in members])
    listing = {"title": f"Money Decisions Bundle: {len(manifest)} Excel Tools for Small Business and Personal Finance", "price_usd": price,
               "individual_total_usd": total, "included": [m["title"] for m in manifest],
               "description": f"{len(manifest)} complete Excel workbooks with short PDF guides for money decisions (cash flow, pricing, taxes, debt, budgeting, investing), in one download. "
                              f"Bought separately they cost ${total:.0f}; the bundle is ${price}. Each tool is the same file sold on its own page."}
    (out / "listing.json").write_text(json.dumps(listing, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"ok": True, "zip": str(zpath), "size_mb": round(zpath.stat().st_size / 1048576, 2), "members": len(manifest), "missing": missing,
            "price_usd": price, "individual_total_usd": total}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    r = build(argv[0] if argv else "B14")
    sys.stdout.write(json.dumps(r, ensure_ascii=False) + "\n")
    return 0 if r.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
