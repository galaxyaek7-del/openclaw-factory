"""Repair already-shipped product files in place, with backups and a report.

  * PDFs with in-word black-box glyphs -> pdf_glyph_repair.repair_pdf()
  * workbooks that fail file_testing_engine (zero formulas) -> workbook_upgrader

Every original is copied to backups/product_repair_<date>/<same relative path>
BEFORE it is touched (/backups/ is gitignored: these are paid files and this
repo is served publicly). A file is only replaced after its repair verifies.
Each file is re-tested with file_testing_engine afterwards and the before/after
result is written to data/product_quality_repair_<date>.json.

Local files only. Copies already uploaded to Gumroad / Payhip are NOT changed
by this script -- re-uploading is a separate, founder-approved step.

    python scripts/repair_shipped_products.py            # dry run: report only
    python scripts/repair_shipped_products.py --apply
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
logging.getLogger("pypdf").setLevel(logging.ERROR)

import file_testing_engine as fte  # noqa: E402
import pdf_glyph_repair as pgr  # noqa: E402
import workbook_upgrader as wu  # noqa: E402

SKIP_DIRS = {"node_modules", "backups", ".git", "tests"}


def _candidates(pattern):
    for p in sorted(ROOT.rglob(pattern)):
        rel = p.relative_to(ROOT)
        if not SKIP_DIRS.intersection(rel.parts):
            yield p, rel


def main(apply: bool) -> dict:
    today = dt.date.today().isoformat()
    backup_root = ROOT / "backups" / f"product_repair_{today}"
    out = {"date": today, "applied": apply, "pdfs": [], "workbooks": [],
           "note": "Local files only; uploaded marketplace copies are unchanged."}

    def backup(p, rel):
        dst = backup_root / rel
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst)

    for p, rel in _candidates("*.pdf"):
        try:
            n = pgr.count_in_word_boxes(p)
        except Exception as exc:  # noqa: BLE001
            out["pdfs"].append({"file": str(rel), "error": f"{type(exc).__name__}: {exc}"})
            continue
        if not n:
            continue
        row = {"file": str(rel), "boxes_before": n}
        if apply:
            backup(p, rel)
            r = pgr.repair_pdf(p)
            row.update(written=r.written, boxes_after=r.boxes_after if r.written else n,
                       runs_rewritten=r.runs_rewritten, reason=r.reason,
                       test_after=fte.test_pdf(p).status)
        out["pdfs"].append(row)

    for p, rel in _candidates("*.xlsx"):
        before = fte.test_file(p)
        if before.status == fte.PASS:
            continue
        row = {"file": str(rel), "before": before.status, "problems_before": before.problems}
        if apply:
            backup(p, rel)
            r = wu.upgrade_workbook(p)
            after = fte.test_file(p)
            row.update(skipped=r.skipped, formulas_added=r.formulas_added,
                       validations_added=r.validations_added,
                       placeholders_moved=r.placeholders_moved,
                       column_kinds=r.sheets, after=after.status,
                       problems_after=after.problems)
        out["workbooks"].append(row)

    pd = [x for x in out["pdfs"] if "boxes_before" in x]
    out["summary"] = {
        "pdfs_with_boxes": len(pd),
        "boxes_before": sum(x["boxes_before"] for x in pd),
        "pdfs_repaired": sum(1 for x in pd if x.get("written")),
        "boxes_after": sum(x.get("boxes_after", x["boxes_before"]) for x in pd),
        "workbooks_failing": len(out["workbooks"]),
        "workbooks_passing_after": sum(1 for x in out["workbooks"] if x.get("after") == fte.PASS),
    }
    if apply:
        _write_verified_report(backup_root, today)
    return out


def _write_verified_report(backup_root: Path, today: str) -> dict:
    """The durable record: every backed-up original vs. its current file.

    Built from the backups rather than from one run's output, so repeated
    runs on the same day accumulate instead of overwriting each other.
    """
    rows = []
    for orig in sorted(backup_root.rglob("*")):
        if not orig.is_file():
            continue
        rel = orig.relative_to(backup_root)
        cur = ROOT / rel
        b, a = fte.test_file(orig), fte.test_file(cur)
        row = {"file": str(rel), "before": b.status, "after": a.status,
               "problems_before": b.problems, "problems_after": a.problems}
        if orig.suffix.lower() == ".pdf":
            row["boxes_before"] = pgr.count_in_word_boxes(orig)
            row["boxes_after"] = pgr.count_in_word_boxes(cur)
            row["pages"] = a.detail.get("pages")
        else:
            row["formulas_before"] = b.detail.get("formula_count")
            row["formulas_after"] = a.detail.get("formula_count")
        rows.append(row)
    pdfs = [r for r in rows if "boxes_before" in r]
    wbs = [r for r in rows if "formulas_before" in r]
    rep = {
        "date": today,
        "backups": str(backup_root.relative_to(ROOT)),
        "note": "Local files only; uploaded marketplace copies are unchanged.",
        "summary": {
            "pdfs": len(pdfs),
            "boxes_before": sum(r["boxes_before"] for r in pdfs),
            "boxes_after": sum(r["boxes_after"] for r in pdfs),
            "workbooks": len(wbs),
            "workbooks_pass_before": sum(r["before"] == fte.PASS for r in wbs),
            "workbooks_pass_after": sum(r["after"] == fte.PASS for r in wbs),
            "formulas_before": sum(r["formulas_before"] or 0 for r in wbs),
            "formulas_after": sum(r["formulas_after"] or 0 for r in wbs),
        },
        "files": rows,
    }
    (ROOT / "data" / f"product_quality_repair_{today}.json").write_text(
        json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    return rep


if __name__ == "__main__":
    res = main("--apply" in sys.argv)
    print(json.dumps(res["summary"], indent=1))
    for x in res["pdfs"]:
        if x.get("reason") or x.get("error"):
            print("PDF not repaired:", x)
    for x in res["workbooks"]:
        if res["applied"] and x.get("after") != fte.PASS:
            print("Workbook still failing:", x["file"], x.get("problems_after"))
