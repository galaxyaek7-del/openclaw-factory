"""Cycle 82 — scan every live listing's social share card (Open Graph).

Real, confirmed defect found while choosing the Cycle 82 test product: the
Turo listing's og:image is

    https://assets.gumroad.com/images/opengraph_image.png

which is Gumroad's GENERIC placeholder, not a product image. Every share of
that link on X, Facebook, LinkedIn, Slack or iMessage therefore renders as a
blank Gumroad card instead of something that shows what is being sold. This is
a sales-page defect, not a cosmetic one: it suppresses the click at exactly
the moment a prospective buyer decides whether to look.

Only one listing checked so far carries a real image -- iaiyt (the EU AI Act
Toolkit), the one product created with a cover.

This script measures the share card for every live listing so the fix is
quantified rather than asserted. Read-only: it fetches PUBLIC product pages,
touches no API, writes nothing, costs nothing.

Run:  python scripts/cycle82_share_card_scan.py
Out:  data/cycle82_share_cards.json
"""

from __future__ import annotations

import io
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

SNAPSHOT = "data/cycle81_delivery_audit.json"
OUT = "data/cycle82_share_cards.json"

GENERIC_OG_MARKERS = ("assets.gumroad.com/images/opengraph_image",)

OG_PATTERNS = {
    "og_title": r'property="og:title"\s+content="(.*?)"',
    "og_description": r'property="og:description"\s+content="(.*?)"',
    "og_image": r'property="og:image"\s+content="(.*?)"',
    "og_url": r'property="og:url"\s+content="(.*?)"',
    "twitter_card": r'name="twitter:card"\s+content="(.*?)"',
    "twitter_image": r'name="twitter:image"\s+content="(.*?)"',
}


def _fetch(url: str, timeout: int = 25):
    # A social-bot UA: this is what X/Facebook/Slack actually send, and it is
    # the response that decides the preview card.
    req = urllib.request.Request(
        url, headers={"User-Agent": "facebookexternalhit/1.1 "
                                     "(+http://www.facebook.com/externalhit_uatext.php)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:  # noqa: BLE001
        return 0, f"{type(e).__name__}: {e}"


def main() -> int:
    snap = json.load(io.open(SNAPSHOT, encoding="utf-8"))
    rows = []

    for meta in snap["products"]:
        url = meta.get("url")
        short = meta.get("short_id")
        if not url or not short:
            continue
        st, html = _fetch(url)
        card = {}
        for k, pat in OG_PATTERNS.items():
            m = re.search(pat, html, re.IGNORECASE | re.DOTALL)
            card[k] = m.group(1).strip() if m else None
        og_image = card.get("og_image") or ""
        generic = any(mk in og_image for mk in GENERIC_OG_MARKERS)
        rows.append({
            "short_id": short,
            "name": meta.get("name"),
            "price_usd": meta.get("price_usd"),
            "url": url,
            "http_status": st,
            "og_image": og_image or None,
            "og_image_is_generic_placeholder": generic,
            "og_title": card.get("og_title"),
            "has_og_description": bool(card.get("og_description")),
            "twitter_card": card.get("twitter_card"),
        })
        time.sleep(0.1)

    ok = [r for r in rows if r["http_status"] == 200]
    generic = [r for r in ok if r["og_image_is_generic_placeholder"]]
    real = [r for r in ok if not r["og_image_is_generic_placeholder"]
            and r["og_image"]]
    no_image = [r for r in ok if not r["og_image"]]

    out = {
        "probe": "cycle82_share_card_scan",
        "read_only": True,
        "cost": 0,
        "method": "GET on each public product page with a social-bot UA",
        "checked": len(rows),
        "reachable": len(ok),
        "verdicts": {
            "GENERIC_PLACEHOLDER_OG_IMAGE": len(generic),
            "REAL_PRODUCT_OG_IMAGE": len(real),
            "NO_OG_IMAGE_AT_ALL": len(no_image),
            "FETCH_FAILED": len(rows) - len(ok),
        },
        "with_real_image": [{"short_id": r["short_id"], "name": r["name"],
                             "og_image": r["og_image"]} for r in real],
        "all": rows,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)

    print(json.dumps({k: out[k] for k in
                      ("checked", "reachable", "verdicts")},
                     indent=2, ensure_ascii=False))
    print("\nListings that DO have a real share image:")
    for r in real:
        print(f"  {r['short_id']}  {r['name'][:55]}")
    print(f"\nA share of any of the other {len(generic)} listings renders as "
          f"Gumroad's generic placeholder card.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())