"""PHASE 4 -- READ-ONLY live-state reconciliation.

Compares what commits 2af1b96 / bb6b31d / 03ea6f7 CLAIM happened against what
the live Gumroad API actually reports right now.

STRICTLY READ-ONLY. This script:
  - calls only list_products() (a read)
  - never calls create/update/delete/enable
  - never prints, stores, or transmits the credential
  - spends $0

Classification vocabulary, per the directive:
  MATCH          observed live state equals the expected/claimed state
  MISMATCH       observed live state contradicts the claim
  UNKNOWN        cannot be determined with the available read surface
  NOT_VERIFIABLE the API does not expose the field at all
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"C:\openclaw-dasgboard")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from channels import gumroad_publisher as gp

# Claims extracted from the three commits' registry/diff content.
CLAIMS = [
    {
        "claim_id": "C1",
        "product": "Etsy Suspension: Triage + Appeal Bundle (Both Steps)",
        "claim": "file replaced with repaired bundle 176,766 B; price unchanged $79",
        "expected_price": 79.0,
        "expected_file_size_hint": 176766,
        "match_slug": "bfhpzl",
        "commit": "2af1b96",
    },
    {
        "claim_id": "C2",
        "product": "Etsy Suspension Appeal Kit",
        "claim": "file replaced with repaired bundle 170,027 B; price $29",
        "expected_price": 29.0,
        "expected_file_size_hint": 170027,
        "match_slug": "fgruzn",
        "commit": "2af1b96",
    },
    {
        "claim_id": "C3",
        # NOTE: the live name uses an EM DASH, not a hyphen. A naive
        # substring search for "DO NOT BUY -" silently missed this product
        # and produced a false MISMATCH. Matching by slug removes that class
        # of error entirely.
        "product": "GALAXY FORGE API TEST — DO NOT BUY — DELETE ME",
        "claim": "unpublished, verified published=false",
        "expected_price": 1.0,
        "expected_published": False,
        "match_slug": "dxfwlu",
        "commit": "2af1b96",
    },
    {
        "claim_id": "C4",
        "product": "Landlord Move-In Inspection Pack",
        "claim": "pricing PROPOSAL $27, explicitly NOT applied",
        "expected_price": 49.0,   # unchanged, because the proposal was not applied
        "match_slug": "gzbdaz",
        "commit": "2af1b96",
    },
]

print("=" * 78)
print("PHASE 4 -- LIVE-STATE RECONCILIATION (READ-ONLY)")
print("=" * 78)

token = gp.load_token()
products = gp.list_products(token)

print(f"live catalog size      : {len(products)}")
print(f"published              : {sum(1 for p in products if p.get('published'))}")
print(f"unpublished            : {sum(1 for p in products if not p.get('published'))}")
print(f"total sales_count      : {sum(p.get('sales_count') or 0 for p in products)}")
print()

results = []
for c in CLAIMS:
    slug = c.get("match_slug")
    match = next((p for p in products
                  if (p.get("short_url") or "").rsplit("/", 1)[-1] == slug), None) \
        if slug else next((p for p in products
                           if c["product"].lower() in str(p.get("name", "")).lower()), None)
    print("=" * 78)
    print(f"{c['claim_id']}  {c['product']}")
    print(f"     claim ({c['commit']}): {c['claim']}")
    print("-" * 78)
    if not match:
        print("  OBSERVED   : NOT FOUND in live catalog")
        results.append({**c, "observed": None, "verdict": "MISMATCH",
                        "note": "product absent from live catalog"})
        continue

    live_price = round((match.get("price") or 0) / 100, 2)
    live_pub = bool(match.get("published"))
    live_sales = match.get("sales_count") or 0
    fi = match.get("file_info") or {}
    url = match.get("short_url")

    print(f"  OBSERVED id        : {match.get('id')}")
    print(f"  OBSERVED url       : {url}")
    print(f"  OBSERVED published : {live_pub}")
    print(f"  OBSERVED price     : ${live_price:.2f}")
    print(f"  OBSERVED sales     : {live_sales}")
    print(f"  OBSERVED file_info : {fi}")

    price_ok = abs(live_price - c["expected_price"]) < 0.01
    print(f"  PRICE      : expected ${c['expected_price']:.2f} | "
          f"observed ${live_price:.2f} -> {'MATCH' if price_ok else 'MISMATCH'}")

    pub_verdict = "NOT VERIFIABLE (no claim)"
    if "expected_published" in c:
        pub_ok = live_pub == c["expected_published"]
        pub_verdict = "MATCH" if pub_ok else "MISMATCH"
        print(f"  PUBLISHED  : expected {c['expected_published']} | "
              f"observed {live_pub} -> {pub_verdict}")

    # The API exposes only Size/Length, never filenames or hashes.
    size_txt = str(fi.get("Size", ""))
    print(f"  ATTACHMENT : {size_txt} -- {len(fi)} field(s) exposed by the API")
    print(f"               filenames : NOT VERIFIABLE (API exposes no filename)")
    print(f"               file hash  : NOT VERIFIABLE (API exposes no checksum)")
    print(f"               byte match : UNKNOWN -- Size field is a rounded string,")
    print(f"                            cannot be compared to a claimed byte count")
    hint = c.get("expected_file_size_hint")
    if hint:
        kib = hint / 1024
        print(f"                            claimed {hint:,} B = {kib:.1f} KiB vs "
              f"live '{size_txt}' -> PLAUSIBLE, not proof")

    results.append({
        "claim_id": c["claim_id"], "product": c["product"], "commit": c["commit"],
        "claim": c["claim"], "live_id": match.get("id"), "live_url": url,
        "live_published": live_pub, "live_price_usd": live_price,
        "live_sales": live_sales, "file_info_exposed": fi,
        "price_verdict": "MATCH" if price_ok else "MISMATCH",
        "published_verdict": pub_verdict,
        "attachment_verdict": "NOT VERIFIABLE",
        "file_content_match": "UNKNOWN",
    })

print()
print("=" * 78)
print("UNPUBLISHED LISTINGS (full list)")
print("=" * 78)
for p in products:
    if not p.get("published"):
        print(f"  ${(p.get('price') or 0)/100:>7.2f}  {p.get('short_url')}  "
              f"{str(p.get('name'))[:52]}")

print()
print("=" * 78)
print("VERDICT SUMMARY")
print("=" * 78)
for r in results:
    print(f"  {r['claim_id']}  price={r['price_verdict']:<9} "
          f"attachment={r['attachment_verdict']:<15} {r['product'][:40]}")
print()
print("  NO FILE OR PRICE CHANGE COULD BE INDEPENDENTLY CONFIRMED.")
print("  The API exposes only Size and Length for attachments -- never a")
print("  filename, never a checksum. A local file or a git-tracked file is")
print("  NOT evidence that it is attached live.")

Path("data/cycle90_live_reconciliation.json").write_text(
    json.dumps({"probe": "cycle90_live_reconciliation", "read_only": True,
                "cost_usd": 0, "writes_performed": 0,
                "catalog_size": len(products),
                "results": results}, indent=2, ensure_ascii=False),
    encoding="utf-8")
print("\nwrote data/cycle90_live_reconciliation.json")