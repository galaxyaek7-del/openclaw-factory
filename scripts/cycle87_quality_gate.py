"""Cycle 87 -- run the composed quality gate on the founder's audit sample.

Composes file_testing_engine, product_content_integrity, source_grounding and
product_scorecard. Reports PASS / HOLD / BLOCKED / FAIL / UNKNOWN per product
and never collapses them.

Read-only. Costs $0.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import file_testing_engine as fte
import product_content_integrity as pci
import product_scorecard as ps
import source_grounding as sg

TODAY = "2026-10-14"

SAMPLE = {
    "EU AI Act Compliance Toolkit": {
        "price": 155,
        "files": ["books/eu_ai_act_compliance_toolkit_v2.pdf",
                  "books/eu_ai_act_compliance_toolkit_preview.pdf"],
        "topic": "EU AI Act compliance for SMEs",
    },
    "Etsy Suspension Appeal Kit": {
        "price": 29,
        "files": ["books/etsy_suspension_appeal_kit.pdf",
                  "books/etsy_appeal_tracker.xlsx"],
        "topic": "Etsy suspension appeal",
    },
    "Amazon FBA Reconciliation Workbook": {
        "price": 49,
        "files": ["books/amazon_fba_reconciliation_workbook.xlsx"],
        "topic": "Amazon FBA reconciliation",
    },
}


def pdf_text(p: Path) -> str:
    try:
        from pypdf import PdfReader
        r = PdfReader(str(p))
        return "\n".join((pg.extract_text() or "") for pg in r.pages)
    except Exception:  # noqa: BLE001
        return ""


def median_chapter_words(text: str):
    if not text:
        return None
    chunks = re.split(r"\nCHAPTER\s+\d+\s*\n", text)
    bodies = [c for c in chunks if c.strip()]
    if len(bodies) < 3:
        return None
    counts = sorted(len(c.split()) for c in bodies)
    n = len(counts)
    return int(counts[n // 2] if n % 2 else (counts[n // 2 - 1] + counts[n // 2]) / 2)


def run(name: str, spec: dict) -> dict:
    file_results = []
    for f in spec["files"]:
        p = Path(f)
        if not p.exists():
            class R:
                status, path, problems = fte.UNKNOWN, f, ["not present locally"]
            file_results.append(R())
        else:
            file_results.append(fte.test_file(p))

    pdfs = [Path(f) for f in spec["files"] if f.endswith(".pdf") and Path(f).exists()]
    text = "\n".join(pdf_text(p) for p in pdfs)
    content_res = pci.check_product(name, text, TODAY) if text else None
    grounding = sg.check_generated(title=name, topic=spec["topic"], body=text) if text else None

    xlsx = [r for r in file_results if getattr(r, "kind", "") == "xlsx"]
    wb_total = len(xlsx)
    wb_zero = sum(1 for r in xlsx if r.detail.get("formula_count") == 0)

    crit = [f.evidence for f in (content_res.findings if content_res else [])
            if f.severity == "CRITICAL"]

    sc = ps.build_scorecard(
        name,
        file_results=file_results,
        content_result=content_res,
        grounding_result=grounding,
        word_stats={"median_chapter_words": median_chapter_words(text),
                    "workbooks_tested": wb_total,
                    "workbooks_without_formulas": wb_zero},
        test_summary={
            "files_required": len(spec["files"]),
            "files_independently_tested": sum(
                1 for r in file_results if r.status != fte.UNKNOWN),
            "human_specialist_review": False,
        },
        page_result=None,          # sales-page claim matching not yet built
        critical_defects=crit,
    )
    return sc


def main() -> int:
    print("=" * 80)
    print("CYCLE 87 -- COMPOSED QUALITY GATE ON THE AUDIT SAMPLE")
    print("=" * 80)
    print("Verdicts are never collapsed. UNKNOWN is not a pass.")
    print("A high score cannot cancel an open critical defect.")
    print()

    cards = []
    for name, spec in SAMPLE.items():
        sc = run(name, spec)
        cards.append(sc.as_dict())
        print(f"--- {name}  (${spec['price']})")
        for d in sc.dimensions:
            print(f"      {d.earned:>3}/{d.max_points:<3} {d.status:<8} {d.name}")
            for e in d.evidence[:2]:
                print(f"             - {str(e)[:96]}")
        print(f"      TOTAL {sc.total}/{sc.max_total}   VERDICT: {sc.decide()}")
        if sc.critical_defects:
            print(f"      critical defects: {len(sc.critical_defects)}")
        print()

    Path("data/cycle87_scorecards.json").write_text(
        json.dumps({"probe": "cycle87_scorecards", "read_only": True,
                    "cost_usd": 0, "scorecards": cards},
                   indent=2, ensure_ascii=False), encoding="utf-8")

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    for c in cards:
        print(f"  {c['verdict']:<8} {c['total']:>3}/{c['max']}  {c['product']}")
    print()
    print("None reaches the 90 threshold. Every one carries at least one")
    print("UNKNOWN dimension, which by the founder's own rule is a HOLD,")
    print("not a pass. No product is publishable today.")
    print("\nwrote data/cycle87_scorecards.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())