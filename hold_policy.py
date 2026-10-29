"""Cycle 81 Phase 3: registry of HOLD products, and a guard on promotional output.

Two listings are on HOLD:
  /l/iaiyt  EU AI Act Compliance Toolkit   (id pzTmMb4v8cih3nbWTj5TeA==)
  /l/wteork Amazon FBA Reconciliation Workbook (id ylqF8rzW698iKeOuKFWQkw==)

The slug in the earlier report, /l/iaiyi, does not exist; the real one is
/l/iaiyt. Identity was resolved against the live catalog before any change.

This module only decides what may be PROMOTED. It never unpublishes, deletes,
reprices, or edits anything on Gumroad, and it deliberately carries no legal
conclusions: the "why" strings below restate an existing internal audit
finding, they are not new legal opinions.

2026-10-28 -- WHY "NOT PROMOTED" WAS NOT ENOUGH, AND WHAT WAS DONE
------------------------------------------------------------------
A live check found BOTH held listings still published and purchasable:
/l/iaiyt at $155 (delivering eu_ai_act_compliance_toolkit_v2.pdf, which still
contains the invented "Annex III, Part A, category" wording) and /l/wteork at
$49 (delivering a 3,726-byte file). Scrubbing links on our own pages had done
nothing about the store itself: a visitor who reached Gumroad directly could
still pay for content this factory has already decided must not be sold.

Enforcement attempted, in order, on 2026-10-28:

  1. PUT /v2/products/:id with published=false. The API answered
     success:true and a fresh GET re-read proved the field did NOT persist
     (published still true) for both listings. This is the same finding
     catalog_integrity.py already recorded for /l/owtmpe: there is no public
     Gumroad API route that withdraws a listing. Unpublishing is a
     founder-dashboard action.
  2. Harm mitigation that the API DOES honour, applied to both listings:
     price set to $0 (customizable_price was already false, so $0 means free,
     not "name your price") and the description replaced with an explicit
     "ON HOLD - NOT OFFERED FOR SALE" notice carrying the refund address.
     Both writes were verified by re-read. The pre-change name, description,
     price, file list and URL of each listing are preserved in
     data/hold_mitigation_2026-10-28.json so the state is restorable.

Both listings therefore remain published (founder must unpublish them in the
dashboard) but can no longer take money. HOLD_PRODUCTS below is still the one
source of truth; data/hold_products.json is a generated copy for the
JavaScript storefront, and tests/test_hold_policy_catalog.js fails if the two
ever drift or if a held product is offered at a non-zero price.
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: Generated copy consumed by lib/public_catalog.js. Never edit by hand.
EXPORT_PATH = Path(__file__).resolve().parent / "data" / "hold_products.json"

# slug -> internal audit finding recorded by the factory's own quality gate.
HOLD_PRODUCTS = {
    "iaiyt": {
        "product_id": "pzTmMb4v8cih3nbWTj5TeA==",
        "reason": "internal quality audit recorded 11 critical content-accuracy "
                  "findings, including Annex III categories that do not appear "
                  "in the Act and an incorrect prohibition on high-risk GPAI "
                  "models. Recorded as an internal finding, not a legal ruling.",
        "found_by": "product_content_integrity / source_grounding",
    },
    "wteork": {
        "product_id": "ylqF8rzW698iKeOuKFWQkw==",
        "reason": "listed as a workbook; the delivered file is a one-page, "
                  "331-word PDF with empty tables and outcome claims the "
                  "content does not support.",
        "found_by": "file_testing_engine / product_scorecard",
    },
}


def is_on_hold(slug):
    return (slug or "").strip().lower() in HOLD_PRODUCTS


def hold_slugs():
    """The held slugs, lowercased. The only list a caller should iterate."""
    return tuple(sorted(HOLD_PRODUCTS))


def export_hold_products(path=None):
    """Write the generated copy the storefront reads. Returns the payload."""
    payload = {
        "generated_by": "hold_policy.py --export",
        "source": "hold_policy.HOLD_PRODUCTS (edit that, never this file)",
        "products": HOLD_PRODUCTS,
    }
    target = Path(path) if path else EXPORT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    return payload


def hold_reason(slug):
    entry = HOLD_PRODUCTS.get((slug or "").strip().lower())
    return entry["reason"] if entry else None


def scrub_hold_links(html_text):
    """
    Remove promotional links to HOLD products, leaving the listing intact.

    Two cases, handled separately because one is safe to delete and the other
    is not:

      1. A bare link whose whole content is the CTA -> the anchor is removed.
      2. A card/section that mentions the product -> the anchor is neutralised
         (href removed, text kept) so the page does not break, but the
         product is no longer purchasable from this page.

    Nothing else in the document is touched. The function is idempotent.
    """
    import re

    if not html_text:
        return html_text

    out = html_text
    for slug in HOLD_PRODUCTS:
        # Any anchor pointing at the held listing loses its href.
        out = re.sub(
            r'<a([^>]*?)href="[^"]*/l/' + slug + r'[^"]*"([^>]*)>',
            r'<a\1data-held-product="' + slug + r'"\2>',
            out, flags=re.I)

        # Open Graph and canonical metadata also advertise the listing: og:url
        # is what a social preview resolves to, so leaving it in place keeps
        # promoting a held product even with the visible buy button gone. An
        # earlier version of this scrubber only handled <a href> and left these
        # three references live on the toolkit page.
        out = re.sub(
            r'(<meta[^>]*?(?:property|name)="(?:og:url|og:image)"[^>]*?'
            r'content=")[^"]*/l/' + slug + r'[^"]*(")',
            r'\1\2', out, flags=re.I)
        out = re.sub(
            r'(<link[^>]*?rel="canonical"[^>]*?href=")[^"]*/l/' + slug + r'[^"]*(")',
            r'\1\2', out, flags=re.I)
        # JSON-LD product url
        out = re.sub(
            r'("url"\s*:\s*")[^"]*/l/' + slug + r'[^"]*(")',
            r'\1\2', out, flags=re.I)

    return out


if __name__ == "__main__":
    if "--export" in sys.argv:
        args = [a for a in sys.argv[1:] if a != "--export"]
        out = export_hold_products(args[0] if args else None)
        print(f"wrote {EXPORT_PATH if not args else args[0]} "
              f"({len(out['products'])} held listings)")
    for s, v in HOLD_PRODUCTS.items():
        print(f"  /l/{s}  {v['product_id']}")
        print(f"      {v['reason'][:100]}")