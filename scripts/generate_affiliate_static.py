"""Generate the static affiliate catalog for the Pages host (GF-19).

Reads the real affiliate_commerce.products dataset, writes
customer_site/affiliate-products.json. Re-run after any dataset or tag
change. Writes nothing else.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from affiliate_commerce.static_catalog import build_static_catalog

OUT = Path(__file__).resolve().parent.parent / "customer_site" / "affiliate-products.json"


def main():
    catalog = build_static_catalog()
    OUT.write_text(json.dumps(catalog, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), "count": catalog["count"],
                      "tag_configured": catalog["tag_configured"]}, indent=1))


if __name__ == "__main__":
    main()
