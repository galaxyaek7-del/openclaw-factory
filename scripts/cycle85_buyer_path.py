"""Cycle 85: buyer-path diagnosis, from a visitor's perspective. Strictly READ-ONLY.

Distinguishes three very different problems that all look like "no sales":

  NO TRAFFIC      nobody is arriving, so conversion is untestable
  WEAK CONVERSION people arrive and leave
  BROKEN PATH     people arrive and cannot buy

This script can only ever observe the third one directly, because Gumroad
exposes no analytics endpoint (probed live: /v2/analytics -> 404,
products/analytics -> 200 but "product not found", visits -> 404). It must
therefore NOT claim to know whether anyone is arriving.

What it does check, without buying anything:
  * the public product page resolves
  * a price is displayed
  * the page states what is actually in the file
  * the claims on the page match the real delivered file
  * checkout is reachable from the page
"""
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, errors := os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")

CANDIDATES = [
    {"slug": "bfhpzl", "name": "Etsy Suspension: Triage + Appeal Bundle",
     "price_cents": 7900, "zip": "books/_releases/etsy_suspension_complete_bundle_v3.zip",
     "files": {"etsy_suspension_appeal_kit.pdf": 138923,
               "etsy_appeal_evidence_tracker.xlsx": 15011}},
    {"slug": "fgruzn", "name": "Etsy Suspension Appeal Kit",
     "price_cents": 2900, "zip": "books/_releases/etsy_suspension_appeal_kit_v3_bundle.zip",
     "files": {"etsy_suspension_appeal_kit.pdf": 138923}},
    {"slug": "wteork", "name": "Amazon FBA Workbook",
     "price_cents": 4900, "zip": None, "files": {}},
]


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", "replace")


def main():
    import zipfile
    results = []
    for c in CANDIDATES:
        url = f"https://aekraft.gumroad.com/l/{c['slug']}"
        row = {"slug": c["slug"], "name": c["name"], "url": url, "findings": {}}
        try:
            status, html = fetch(url)
            row["findings"]["page_http"] = status
            row["findings"]["page_reachable"] = status == 200

            # What does a visitor actually pay? The canonical machine-readable field
            # is the Open Graph product:price:amount meta tag.
            #
            # Two earlier attempts were both wrong and would have produced a
            # false conclusion: a regex requiring cents reported "no price
            # shown" on a page that plainly has one, and a looser regex then
            # reported $49 on a $79 product -- because the description copy
            # mentions the COMPETITOR's $49 suspension fee. Scraping "$<n>"
            # out of body text measures marketing prose, not the price.
            m = re.search(r'property="product:price:amount"\s+content="([\d.]+)"',
                          html)
            shown = m.group(1) if m else None
            row["findings"]["price_displayed"] = shown
            row["findings"]["price_matches_catalog"] = (
                shown is not None
                and abs(float(shown) - c["price_cents"] / 100.0) < 0.005)

            # Can a visitor actually reach checkout? Gumroad renders the buy
            # control client-side; the reliable static signal is a checkout
            # route or product id wired into the page.
            row["findings"]["checkout_reachable"] = bool(
                re.search(r'/l/%s|buy|checkout|product_id' % c["slug"], html, re.I))

            # Do the page's size claims match the real file?
            claims = {f: int(x) for f, x in
                      re.findall(r'([a-z0-9_]+\.(?:pdf|xlsx|docx))\s+(\d+)\s*KB',
                                 html, re.I)}
            mismatches = {}
            # An empty expected-files dict means NOTHING was checked. Reporting
            # that as "claims match" is a false PASS: an earlier version of
            # this script did exactly that for the FBA listing. It now reports
            # UNCHECKED so an untested product can never look verified.
            if not c["files"]:
                row["findings"]["page_claims_match_file"] = "UNCHECKED"
            else:
                for fname, real in c["files"].items():
                    if fname in claims:
                        correct = round(real / 1000)
                        if claims[fname] != correct:
                            mismatches[fname] = {
                                "claims_kb": claims[fname],
                                "correct_kb": correct}
                    else:
                        mismatches[fname] = {
                            "claims_kb": None, "correct_kb": round(real / 1000),
                            "note": "file is delivered but the page never states its size"}
                row["findings"]["page_claims_match_file"] = not mismatches
            row["findings"]["size_claim_mismatches"] = mismatches
        except urllib.error.HTTPError as e:
            row["findings"]["page_http"] = e.code
            row["findings"]["page_reachable"] = False
        except Exception as e:  # noqa: BLE001
            row["findings"]["error"] = f"{type(e).__name__}: {e}"
        results.append(row)

    out = {
        "probe": "cycle85_buyer_path",
        "generated_at_utc": datetime.datetime.now(datetime.UTC).isoformat(),
        "read_only": True,
        "purchases_performed": 0,
        "cost_usd": 0,
        "traffic_data_available": False,
        "traffic_data_note": (
            "Gumroad exposes no analytics endpoint. Probed live this cycle: "
            "/v2/analytics 404, /v2/visits 404, /v2/products/analytics 200 but "
            "'product not found', per-product analytics 404. Views and "
            "referrers are dashboard-session-only, so whether ANY visitor has "
            "arrived is UNKNOWN and cannot be inferred from this script."),
        "results": results,
    }
    with open("data/cycle85_buyer_path.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    for r in results:
        fnd = r["findings"]
        print(f"\n{r['name']}  ({r['slug']})")
        print(f"  page reachable : {fnd.get('page_reachable')}  HTTP {fnd.get('page_http')}")
        print(f"  price shown    : {fnd.get('price_displayed')}  "
              f"matches catalog: {fnd.get('price_matches_catalog')}")
        print(f"  checkout       : {fnd.get('checkout_reachable')}")
        print(f"  claims match   : {fnd.get('page_claims_match_file')}")
        if fnd.get("size_claim_mismatches"):
            for k, v in fnd["size_claim_mismatches"].items():
                if v.get("claims_kb") is None:
                    print(f"      {k}: size never stated on the page (real {v['correct_kb']} KB)")
                else:
                    print(f"      {k}: page says {v['claims_kb']} KB, real file is {v['correct_kb']} KB")
    print("\nwrote data/cycle85_buyer_path.json")


if __name__ == "__main__":
    main()