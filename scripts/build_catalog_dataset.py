"""Release the public catalog as a packaged dataset with a data card (backlog B20, 2026-10-29).

Input: customer_site/catalog.json (already public on the storefront; written from
the factory's own product registry). Output, under
data_products/releases/gf-public-catalog/<release date>/:
  catalog.csv      one row per catalog product
  datacard.json    the data card (sources, licence, columns, sha256, rows)
  validation.json  data_products.datacard.validate_card() result

All content is the factory's own: titles, summaries and prices it wrote, and links
to its own storefront. No third-party data and no personal data. This is a
format/provenance exercise for the Data Products arm; it is not offered for sale.
"""
import csv
import json
import os
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from data_products import datacard  # noqa: E402

SRC = "customer_site/catalog.json"
COLUMNS = [
    ("id", "string", "Factory product id (registry internal_id)"),
    ("title", "string", "Product title as listed"),
    ("price_usd_cents", "integer", "Recorded list price in US cents, before taxes"),
    ("url", "string", "Product page on the factory's own Gumroad storefront"),
    ("format", "string", "Delivery format"),
    ("featured", "boolean", "Shown in the storefront's featured section"),
    ("summary", "string", "Factory-written product summary (may be truncated with '...')"),
]


def build(root=ROOT, release=None):
    release = release or date.today().isoformat()
    with open(os.path.join(root, SRC), encoding="utf-8") as f:
        doc = json.load(f)["data"]
    products = doc["products"]
    rel_dir = os.path.join("data_products", "releases", "gf-public-catalog", release)
    out_dir = os.path.join(root, rel_dir)
    os.makedirs(out_dir, exist_ok=True)
    csv_rel = os.path.join(rel_dir, "catalog.csv").replace(os.sep, "/")
    with open(os.path.join(root, csv_rel), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([c[0] for c in COLUMNS])
        for p in products:
            w.writerow([p["id"], p["title"], int(p["price_cents"]), p["url"], p.get("format") or "",
                        "true" if p.get("featured") else "false", p.get("summary") or ""])
    card = {
        "dataset_id": "gf-public-catalog",
        "title": "Galaxy Forge public product catalog",
        "version": release,
        "description": f"{len(products)} digital products as listed on the Galaxy Forge storefront: id, "
                       "title, list price, link, format and summary.",
        "intended_use": "Internal reference format for the Data Products arm; a machine-readable copy of "
                        "the public catalog.",
        "out_of_scope_use": "Not a sales or demand dataset: it contains no sales, traffic or customer data.",
        "sources": [{
            "name": "storefront catalog snapshot",
            "origin": SRC,
            "generated_at": doc.get("generated_at"),
            "accessed_on": release,
            "access_method": "FACTORY_INTERNAL",
            "licence": {"name": "Galaxy Forge own content", "commercial_use": True,
                        "attribution_required": False, "share_alike": False},
        }],
        "collection_method": "Copied from the factory's own catalog file, which is generated from "
                             "data/product_registry.json (read-only Gumroad catalog reads).",
        "processing_steps": ["select listed fields", "price_cents -> price_usd_cents (no conversion)",
                             "featured -> true/false"],
        "columns": [{"name": n, "type": t, "description": d} for n, t, d in COLUMNS],
        "files": [{"path": csv_rel, "format": "csv", "sha256": datacard.sha256_file(os.path.join(root, csv_rel)),
                   "rows": len(products)}],
        "personal_data": {"contains": False},
        "licence_out": {"name": "Galaxy Forge proprietary", "note": "not licensed to third parties"},
        "refresh_days": 30,
        "last_refreshed": release,
        "known_limitations": ["summaries are truncated as on the storefront",
                              "prices are list prices; checkout totals may differ (taxes)",
                              "a snapshot: the live catalog changes after this date"],
    }
    with open(os.path.join(out_dir, "datacard.json"), "w", encoding="utf-8") as f:
        json.dump(card, f, ensure_ascii=False, indent=1)
    result = datacard.validate_card(card, root)
    with open(os.path.join(out_dir, "validation.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    return card, result


if __name__ == "__main__":
    card, result = build()
    sys.stdout.write(json.dumps({"release": card["version"], "rows": card["files"][0]["rows"],
                                 "status": result["status"], "findings": result["findings"]},
                                ensure_ascii=False, indent=1) + "\n")
