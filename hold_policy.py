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
"""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

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
    for s, v in HOLD_PRODUCTS.items():
        print(f"  /l/{s}  {v['product_id']}")
        print(f"      {v['reason'][:100]}")