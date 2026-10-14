"""Cycle 87 -- apply the file testing engine to the founder's audit sample.

Sample named in the directive:
  1. EU AI Act Compliance Toolkit ($155)
  2. Amazon FBA Reconciliation Workbook
  3. Etsy Suspension Appeal Kit ($29)

The directive says this is an AUDIT SAMPLE, not a prior judgement. So every
product is opened and tested, and the result follows the file -- not the name,
the price, or the fact that it is listed on Gumroad.

Read-only. Costs $0.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import file_testing_engine as fte

SAMPLE = [
    ("EU AI Act Compliance Toolkit", "$155", [
        "books/eu_ai_act_compliance_toolkit_v2.pdf",
        "books/eu_ai_act_compliance_toolkit_preview.pdf",
    ]),
    ("Amazon FBA Reconciliation Workbook", "$49", [
        "books/amazon_fba_reconciliation_workbook.xlsx",
        "books/ccpa_compliance_tracker.xlsx",   # nearest local workbook
    ]),
    ("Etsy Suspension Appeal Kit", "$29", [
        "books/etsy_suspension_appeal_kit.pdf",
        "books/etsy_appeal_tracker.xlsx",
    ]),
]

# Bundles in the catalog that ship as ZIP -- checked because a corrupt bundle
# is the single most damaging thing that can happen to a buyer.
EXTRA_ZIPS = sorted(Path("books").glob("*bundle*.zip"))[:6]


def main() -> int:
    print("=" * 78)
    print("CYCLE 87 -- FILE TESTING ON THE AUDIT SAMPLE")
    print("=" * 78)
    print("Every file is opened with a real parser. Names and sizes are never")
    print("evidence on their own. A file that cannot be parsed is UNKNOWN.")
    print()

    results = []
    for product, price, files in SAMPLE:
        print(f"-" * 78)
        print(f"{product}   {price}")
        print("-" * 78)
        for f in files:
            p = Path(f)
            if not p.exists():
                print(f"  [UNKNOWN] {f}")
                print("           file not present locally -- content cannot be")
                print("           inspected. Absence is not a pass.")
                results.append({"product": product, "file": f,
                                "status": "UNKNOWN",
                                "problems": ["not present locally"]})
                continue
            r = fte.test_file(p)
            results.append({"product": product, "file": f,
                            "status": r.status, "detail": r.detail,
                            "problems": r.problems})
            print(f"  [{r.status}] {p.name}  ({r.detail.get('bytes', 0):,} B)")
            for k, v in r.detail.items():
                if k != "bytes":
                    sv = str(v)
                    print(f"        {k:<20} {sv[:88]}")
            for pr in r.problems:
                print(f"        PROBLEM: {pr[:100]}")
        print()

    print("=" * 78)
    print("ZIP BUNDLES (highest blast radius if corrupt)")
    print("=" * 78)
    for z in EXTRA_ZIPS:
        r = fte.test_file(z)
        results.append({"product": "bundle", "file": str(z),
                        "status": r.status, "detail": r.detail,
                        "problems": r.problems})
        flag = "FAIL" if r.status == "FAIL" else r.status
        print(f"  [{flag:<7}] {z.name:<52} members={r.detail.get('member_count', '?')}")
        for pr in r.problems:
            print(f"           {pr[:96]}")
    print()

    tally = {}
    for r in results:
        tally[r["status"]] = tally.get(r["status"], 0) + 1
    print("=" * 78)
    print("TALLY")
    print("=" * 78)
    for k in ("PASS", "FAIL", "UNKNOWN"):
        print(f"  {k:<9} {tally.get(k, 0)}")
    print()
    print("A file passing here proves the FILE is usable. It does not prove the")
    print("product is commercially sound or legally accurate -- a separate gate.")

    Path("data/cycle87_file_tests.json").write_text(
        json.dumps({"probe": "cycle87_file_tests", "read_only": True,
                    "cost_usd": 0, "results": results, "tally": tally},
                   indent=2, ensure_ascii=False),
        encoding="utf-8")
    print("\nwrote data/cycle87_file_tests.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())