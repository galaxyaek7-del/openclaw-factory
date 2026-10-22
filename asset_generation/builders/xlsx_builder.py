"""Real .xlsx asset builder (2026-10-22).

Root cause this closes: the only registered asset builders produced PDFs
(ai_book, techdoc_package). The untracked spreadsheet_systems manifest
pointed at techdoc_package, i.e. a PDF *about* a spreadsheet, and the live
catalog has "Workbook"/"Calculator" products whose only file is a 3-9 KB PDF.

This builder makes the workbook itself, from a declared spec (sheets,
columns, example rows, formulas) in the same format the cohort builders
already use, via cohort_workbook.build_xlsx -- the builder that was already
fixed and tested against shipped workbooks (cross-sheet Summary formulas,
date coercion, no overwrite of authored examples). It never asks an LLM to
invent a workbook, and it fails closed:

  * no workbook_spec, or a spec with no formulas  -> success False
  * output that is not a genuine OOXML zip         -> success False
  * file_testing_engine.test_xlsx not PASS         -> success False

Formula *recalculation* is not verified here: no native spreadsheet engine
(LibreOffice/Excel) is available in this environment. Results say so
explicitly rather than implying the computed values were checked.
"""
from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path

from .. import registry

RECALC_NOTE = "UNVERIFIED: no native spreadsheet engine available to recalculate formulas"
_OOXML_PARTS = ("[Content_Types].xml", "xl/workbook.xml")


def is_genuine_xlsx(path) -> bool:
    """True only for a real OOXML workbook (zip with the workbook part). A PDF
    or any other file renamed to .xlsx returns False."""
    p = Path(path)
    try:
        with open(p, "rb") as f:
            if f.read(4) != b"PK\x03\x04":
                return False
        with zipfile.ZipFile(p) as z:
            names = set(z.namelist())
    except (OSError, zipfile.BadZipFile):
        return False
    return all(part in names for part in _OOXML_PARTS)


def validate_workbook_spec(ws) -> list:
    problems = []
    sheets = (ws or {}).get("sheets") if isinstance(ws, dict) else None
    if not sheets:
        return ["workbook_spec has no sheets"]
    names = []
    for i, sh in enumerate(sheets):
        if not sh.get("name"):
            problems.append(f"sheet {i} has no name")
        if not sh.get("columns"):
            problems.append(f"sheet {sh.get('name', i)!r} has no columns")
        names.append(str(sh.get("name", ""))[:31])
    if len(set(names)) != len(names):
        problems.append("duplicate sheet names")
    if not any(sh.get("formulas") for sh in sheets):
        problems.append("workbook_spec declares no formulas: a spreadsheet product must compute something")
    return problems


class WorkbookAssetBuilder:
    name = "xlsx_workbook"

    def build(self, spec):
        import cohort_workbook
        import file_testing_engine as fte

        ws = spec.get("workbook_spec")
        problems = validate_workbook_spec(ws)
        if problems:
            return {"success": False, "kind": "xlsx", "path": None, "error": "; ".join(problems)}
        family_config = spec.get("family_config") or {}
        out = family_config.get("output") or spec.get("output")
        if not out or not str(out).lower().endswith(".xlsx"):
            return {"success": False, "kind": "xlsx", "path": None,
                    "error": "output path must be given and end in .xlsx"}
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        report = {}
        with tempfile.TemporaryDirectory() as td:
            spec_path = Path(td) / "workbook.json"
            spec_path.write_text(json.dumps(ws, ensure_ascii=False), encoding="utf-8")
            cohort_workbook.build_xlsx(spec_path, out, report)
        if not is_genuine_xlsx(out):
            return {"success": False, "kind": "xlsx", "path": str(out), "error": "output is not a genuine .xlsx"}
        qa = fte.test_xlsx(out)
        ok = qa.status == fte.PASS
        return {"success": ok, "kind": "xlsx", "path": str(out), "qa": qa.as_dict(),
                "build_report": report, "formula_recalculation": RECALC_NOTE,
                **({} if ok else {"error": "; ".join(qa.problems) or qa.status})}


registry.register(WorkbookAssetBuilder())
