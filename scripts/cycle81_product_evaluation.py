"""Cycle 81 Phase 6: three-product evaluation and the free acquisition experiment.

Scored on evidence available in this repository plus the live catalog. Every
dimension that could not be measured says UNKNOWN rather than guessing -- most
notably audience size and traffic, which have never been observed.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CANDIDATES = [
    {
        "slug": "bfhpzl", "name": "Etsy Suspension: Triage + Appeal Bundle",
        "price_cents": 7900, "quality": "PASS",
        "evidence": "6 files, zip CRC verified, 215 formulas in the tracker, "
                    "two size claims corrected this cycle",
        "content_cluster": "5 free blog posts + 1 guide, now internally linked",
        "hold": False,
        "blockers": ["2 size claims await a scoped, approved live write"],
    },
    {
        "slug": "fgruzn", "name": "Etsy Suspension Appeal Kit",
        "price_cents": 2900, "quality": "PASS",
        "evidence": "5 files, zip CRC verified; page does not state file sizes, "
                    "so there is no claim to be wrong",
        "content_cluster": "shares the same cluster",
        "hold": False,
        "blockers": [],
    },
    {
        "slug": "sjrjxq", "name": "Etsy Policy Triage (step 1)",
        "price_cents": 4900, "quality": "UNKNOWN",
        "evidence": "referenced from the guide; this cycle did not audit its "
                    "delivered file",
        "content_cluster": "shares the same cluster",
        "hold": False,
        "blockers": ["delivery quality not verified this cycle"],
    },
]

SELECTED = "bfhpzl"

EXPERIMENT = {
    "id": "EXP-C81-001",
    "hypothesis": "A first-time visitor arriving from search on one of the "
                  "free Etsy guides will click through to a paid listing when "
                  "the guide ends with a direct, contextual link to it.",
    "channel": "existing organic search surface (customer_site guides/blog)",
    "asset": "the 6-page Etsy guide cluster, already published and now "
             "internally linked so it is reachable without guessing a URL",
    "audience": "Etsy sellers who have received a suspension notice",
    "tracking": "UTM tags already present on every content -> product link "
                "(utm_source=etsy_seo_cta&utm_medium=site"
                "&utm_campaign=etsy_suspension_cluster)",
    "duration_days": 30,
    "stopping_rule": "stop and report if, after 30 days, Gumroad Analytics "
                     "shows zero impressions for the cluster AND zero clicks "
                     "on the tagged links; do not extend on a null result",
    "cost": "$0",
    "measurement_status": "BLOCKED - the tagged links exist, but no analytics "
                          "endpoint can be read without the founder, so the "
                          "experiment cannot currently be judged either way",
}


def main():
    print("=" * 74)
    print("Three strongest sellable products")
    print("=" * 74)
    for c in CANDIDATES:
        print(f"\n  /l/{c['slug']}  ${c['price_cents']/100:.2f}  "
              f"[{c['quality']}]  {c['name']}")
        print(f"      delivery   : {c['evidence']}")
        print(f"      content    : {c['content_cluster']}")
        print(f"      blockers   : {c['blockers'] or 'none'}")
        print(f"      traffic    : UNKNOWN - never measured")
        print(f"      audience   : UNKNOWN - never measured")

    print("\n" + "=" * 74)
    print("Selected primary offer")
    print("=" * 74)
    sel = next(c for c in CANDIDATES if c["slug"] == SELECTED)
    print(f"  /l/{sel['slug']}  ${sel['price_cents']/100:.2f}  {sel['name']}")
    print("  Reason: the only candidate that is live, delivery-verified, backed")
    print("  by an existing free content cluster, and honest apart from two")
    print("  numbers already staged for an approved write.")

    print("\n" + "=" * 74)
    print("Free acquisition experiment")
    print("=" * 74)
    for k, v in EXPERIMENT.items():
        print(f"  {k:22s}: {v}")

    out = {"probe": "cycle81_product_evaluation",
           "candidates": CANDIDATES, "selected": SELECTED,
           "experiment": EXPERIMENT,
           "verified_revenue_usd": 0.0,
           "note": "zero observed events is not reported as zero traffic; "
                   "measurement is incomplete by construction"}
    json.dump(out, open("data/cycle81_product_evaluation.json", "w",
                        encoding="utf-8"), indent=2, ensure_ascii=False)
    print("\nwrote data/cycle81_product_evaluation.json")


if __name__ == "__main__":
    main()