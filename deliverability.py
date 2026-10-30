"""A listing that cannot deliver must not be advertised.

2026-10-30: a live read of every published Gumroad listing found two priced,
published listings with an empty `file_info` and no `custom_delivery_url`:

    /l/svlky   Founder Access Continuity Organizer   $8.00
    /l/ieashv  Meeting Cost & ROI Calculator         $11.99

A buyer could pay and receive nothing. The first check that looked for a
deliverable was wrong, not the data: Gumroad returns `file_info` with
capitalised keys ({"Size": "17.6 KB"}), so a `name`/`size` lookup reported all
109 published listings as fileless. Re-reading those two products one at a
time through `get_product` confirmed the empty result is real, not a list-view
truncation.

Gumroad's public API cannot withdraw a listing (`published=false` answers
success and does not persist -- proven in hold_policy.py), so the storefront
half is what this module owns: stop advertising a listing that cannot deliver,
until a real file is attached or the founder unpublishes it.

This module is read-only over Gumroad. It never uploads, edits, reprices, or
unpublishes anything, and it fabricates no deliverable: a product with no file
stays undeliverable until a human supplies the real artifact.
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: Generated copy consumed by lib/public_catalog.js. Never edit by hand.
EXPORT_PATH = Path(__file__).resolve().parent / "data" / "undeliverable_products.json"


def _field(product, name):
    """Read a Gumroad field case-insensitively.

    The list and single-product endpoints disagree on key casing for
    `file_info` ({"Size": ...} vs {"size": ...}), and a case-sensitive lookup
    is what made the first audit report every product as fileless.
    """
    wanted = name.lower()
    for key, value in (product or {}).items():
        if str(key).lower() == wanted:
            return value
    return None


def file_info(product):
    info = _field(product, "file_info")
    return info if isinstance(info, dict) else {}


def delivers(product):
    """True when a buyer would actually receive something.

    A real file (any non-empty file_info, whatever its key casing) or an
    explicit delivery URL. An empty dict is the failure this module exists for.
    """
    if file_info(product):
        return True
    return bool(_field(product, "custom_delivery_url"))


def audit_products(products):
    """Published, not-deleted listings a buyer could pay for and get nothing."""
    found = []
    for p in products or []:
        if not isinstance(p, dict):
            continue
        if not p.get("published") or p.get("deleted"):
            continue
        if delivers(p):
            continue
        url = str(p.get("short_url") or p.get("url") or "")
        slug = url.rstrip("/").split("/")[-1].lower()
        found.append({
            "slug": slug,
            "title": str(p.get("name") or p.get("title") or "")[:120],
            "price_cents": int(p.get("price") or p.get("price_cents") or 0),
        })
    return sorted(found, key=lambda e: e["slug"])


def export_undeliverable(products, path=None):
    """Write the generated copy the storefront reads. Returns the payload."""
    payload = {
        "generated_by": "deliverability.py --export",
        "source": "live Gumroad listings: published, priced, no file and no delivery URL",
        "products": {e["slug"]: {k: v for k, v in e.items() if k != "slug"}
                     for e in audit_products(products)},
    }
    target = Path(path) if path else EXPORT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    return payload


def undeliverable_slugs(path=None):
    """The slugs the storefront must not advertise. Empty when the file is absent."""
    target = Path(path) if path else EXPORT_PATH
    try:
        doc = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ()
    return tuple(sorted((doc.get("products") or {}).keys()))


if __name__ == "__main__":
    if "--export" in sys.argv:
        from channels.gumroad_publisher import load_token, list_products

        payload = export_undeliverable(list_products(load_token()))
        print("wrote %s (%d undeliverable listing(s))"
              % (EXPORT_PATH, len(payload["products"])))
        for slug, entry in payload["products"].items():
            print("  /l/%s  $%.2f  %s"
                  % (slug, entry["price_cents"] / 100.0, entry["title"][:60]))
    else:
        print("undeliverable: %s" % (", ".join(undeliverable_slugs()) or "none"))
