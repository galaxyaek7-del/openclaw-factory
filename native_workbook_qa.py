"""Galaxy Forge — NATIVE WORKBOOK QA.

Turns the Cycle 101 discovery into a reusable factory capability: a workbook
is really recalculated by the installed spreadsheet engine, and both the
underlying values and the user-visible number formats are checked against an
explicit, product-specific expectation spec.

Why this exists: a value-only check compared what Excel *stored* (1, 30000,
46328) without noticing that the cell *displayed* "100%", "$0", "1900-01-01".
A buyer reads the displayed text, so the display is part of correctness.
Seven such defects were found and fixed in B12-010 in Cycle 101.

Layering:
  scripts/excel_recalc_probe.ps1   -> runs Excel, dumps what it displays
  native_workbook_qa.py            -> decides pass/fail (no Excel needed here)
  reports/<id>/WORKBOOK_QA_*.json  -> the expectation spec + the evidence

The decision logic is deliberately separated from Excel so it is unit-tested
without an Office installation. If Excel automation is unavailable, this
module reports that limitation and does not substitute a Python-only estimate
for a native recalculation.

Usage:
    python native_workbook_qa.py --product B12-010
    python native_workbook_qa.py --product B12-010 --write-evidence --json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent
PROBE = ROOT / "scripts" / "excel_recalc_probe.ps1"

SEVERITY_CRITICAL = "CRITICAL"
SEVERITY_WARNING = "WARNING"

DATE_PATTERNS = (
    re.compile(r"^\d{4}-\d{1,2}-\d{1,2}$"),
    re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}$"),
    re.compile(r"^\d{1,2}-[A-Za-z]{3}-\d{2,4}$"),
)


class EngineUnavailable(RuntimeError):
    """Raised when the native spreadsheet engine cannot be used."""


# ---------------------------------------------------------------------------
# Expectation specs
# ---------------------------------------------------------------------------

B12_010_SPEC: Dict[str, Any] = {
    "product_id": "B12-010",
    "artifact": "books/batch12/B12-010_grant_pipeline_tracker.xlsx",
    "artifact_sha256": "df49cecaf704cb06dec3b48c9f826c94cfdae9e2bf91d3a2b76fc670593b8574",
    "formula_sheets": ["Opportunities", "Timeline", "Dashboard"],
    "scan_sheets": [
        "Opportunities", "Docs", "Budget", "Timeline", "Dashboard",
        "Stages", "Eligibility", "DocLibrary", "README",
    ],
    "tables": [
        {"sheet": "Dashboard", "key_column": 1, "value_column": 2, "first_row": 2, "last_row": 30},
    ],
    "columns": [
        {
            "name": "Opportunities!V (deadline helper)",
            "sheet": "Opportunities", "column": 22, "first_row": 2, "last_row": 41,
            "kind": "date", "format": "yyyy-mm-dd",
        },
    ],
    # Integer counts are checked by kind (a count must not render as a
    # percentage, a currency amount or a date) rather than by an exact format
    # string: "General" and "0" both display a whole number correctly.
    "expect": [
        {"sheet": "Dashboard", "label": "Awarded (count)", "kind": "integer"},
        {"sheet": "Dashboard", "label": "Award rate", "kind": "percent", "format": "0%"},
        {"sheet": "Dashboard", "label": "Awarded against requested", "kind": "percent", "format": "0%"},
        {"sheet": "Dashboard", "label": "Total awarded (USD)", "kind": "currency", "format_contains": "$"},
        {"sheet": "Dashboard", "label": "Total requested (USD)", "kind": "currency", "format_contains": "$"},
        {"sheet": "Dashboard", "label": "Deadlines due within 14 days", "kind": "integer"},
        {"sheet": "Dashboard", "label": "Next deadline (open rows only)", "kind": "date", "format": "yyyy-mm-dd"},
        {"sheet": "Dashboard", "label": "Overdue deadlines", "kind": "integer"},
        {"sheet": "Dashboard", "label": "Duplicate rows to merge", "kind": "integer"},
        {"sheet": "Dashboard", "label": "Rows with a data problem", "kind": "integer"},
        {"sheet": "Dashboard", "label": "Opportunities tracked", "kind": "integer"},
        {"sheet": "Dashboard", "label": "Pipeline verdict", "kind": "text"},
    ],
}

B12_006_SPEC: Dict[str, Any] = {
    "product_id": "B12-006",
    "artifact": "books/batch12/B12-006_home_office_expense_log.xlsx",
    "artifact_sha256": "e4abe2866a470bfaf00999ce96d44f415522abb15693b5e72638e5821510e911",
    "formula_sheets": ["Expenses2026", "SpaceMeasure", "MethodCompare", "AnnualSummary"],
    "scan_sheets": [
        "Expenses2026", "SpaceMeasure", "MethodCompare", "AnnualSummary",
        "Categories", "Checklist", "README",
    ],
    # Each sheet's label/value table. A single value column per sheet, so the
    # annual summary is checked on column C, which carries its computed figures.
    "tables": [
        {"sheet": "SpaceMeasure", "key_column": 1, "value_column": 2, "first_row": 2, "last_row": 13},
        {"sheet": "MethodCompare", "key_column": 1, "value_column": 2, "first_row": 2, "last_row": 15},
        {"sheet": "AnnualSummary", "key_column": 1, "value_column": 3, "first_row": 2, "last_row": 14},
    ],
    # The Value column of SpaceMeasure is intentionally heterogeneous (square
    # feet, a percentage, a method name, currency), so its cells are formatted
    # individually and no whole-column rule is asserted for it.
    "columns": [
        {
            "name": "Expenses2026!D (Amount)",
            "sheet": "Expenses2026", "column": 4, "first_row": 2, "last_row": 41,
            "kind": "currency", "format_contains": "$", "require_rows": True,
        },
        {
            "name": "Expenses2026!E (Home share)",
            "sheet": "Expenses2026", "column": 5, "first_row": 2, "last_row": 41,
            "kind": "percent", "format": "0.00%", "require_rows": True,
        },
        {
            "name": "Expenses2026!F (Deductible est.)",
            "sheet": "Expenses2026", "column": 6, "first_row": 2, "last_row": 41,
            "kind": "currency", "format_contains": "$", "require_rows": True,
        },
    ],
    "expect": [
        {"sheet": "SpaceMeasure", "label": "Total home sq ft (livable area)", "kind": "integer"},
        {"sheet": "SpaceMeasure", "label": "Qualifying space sq ft (regular + exclusive use)", "kind": "integer"},
        {"sheet": "SpaceMeasure", "label": "Home % (qualifying ÷ total) — USED BY THE LOG",
         "kind": "percent", "format": "0.00%"},
        {"sheet": "SpaceMeasure", "label": "Simplified deduction (est.)", "kind": "currency", "format_contains": "$"},
        {"sheet": "MethodCompare", "label": "Rent (if you rent)", "kind": "currency", "format_contains": "$"},
        {"sheet": "MethodCompare", "label": "Eligible costs total", "kind": "currency", "format_contains": "$"},
        {"sheet": "MethodCompare", "label": "Home % (from SpaceMeasure)", "kind": "percent", "format": "0.00%"},
        {"sheet": "MethodCompare", "label": "ACTUAL method estimate", "kind": "currency", "format_contains": "$"},
        {"sheet": "MethodCompare", "label": "SIMPLIFIED method estimate", "kind": "currency", "format_contains": "$"},
        {"sheet": "MethodCompare", "label": "Difference (actual minus simplified)", "kind": "currency", "format_contains": "$"},
        {"sheet": "MethodCompare", "label": "Which is higher", "kind": "text"},
        {"sheet": "AnnualSummary", "label": "Internet/utilities", "kind": "currency", "format_contains": "$"},
        {"sheet": "AnnualSummary", "label": "Total logged", "kind": "currency", "format_contains": "$"},
        {"sheet": "AnnualSummary", "label": "Simplified method estimate (for comparison)", "kind": "currency", "format_contains": "$"},
        {"sheet": "AnnualSummary", "label": "Higher figure in this log", "kind": "text"},
    ],
}

SPECS = {
    B12_010_SPEC["product_id"]: B12_010_SPEC,
    B12_006_SPEC["product_id"]: B12_006_SPEC,
}


# ---------------------------------------------------------------------------
# Validation (pure — no Excel, no filesystem)
# ---------------------------------------------------------------------------

def _is_date_like(text: str) -> bool:
    return any(pattern.match(text.strip()) for pattern in DATE_PATTERNS)


def _finding(severity: str, code: str, where: str, detail: str) -> Dict[str, str]:
    return {"severity": severity, "code": code, "where": where, "detail": detail}


def _cells_by_sheet(dump: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for cell in dump.get("cells") or []:
        grouped.setdefault(cell.get("sheet", ""), []).append(cell)
    return grouped


def _lookup(cells: List[Dict[str, Any]], sheet: str, key_column: int, value_column: int,
            first_row: int, last_row: int) -> Dict[str, Dict[str, Any]]:
    keys: Dict[str, Dict[str, Any]] = {}
    values: Dict[int, List[Dict[str, Any]]] = {}
    for cell in cells:
        if cell.get("sheet") != sheet:
            continue
        row = cell.get("row")
        if not isinstance(row, int) or row < first_row or row > last_row:
            continue
        if cell.get("column") == key_column and str(cell.get("text", "")).strip():
            keys[str(cell["text"]).strip()] = {"row": row}
        values.setdefault(row, []).append(cell)

    table: Dict[str, Dict[str, Any]] = {}
    for label, info in keys.items():
        row = info["row"]
        match = next((c for c in values.get(row, []) if c.get("column") == value_column), None)
        table[label] = match or {}
    return table


def _check_kind(kind: str, fmt: str, text: str) -> Optional[str]:
    stripped = text.strip()
    if kind == "percent":
        if "%" not in fmt:
            return f"format {fmt!r} does not render a percentage"
        if not stripped.endswith("%"):
            return f"displayed text {stripped!r} is not a percentage"
    elif kind == "currency":
        if "$" not in fmt:
            return f"format {fmt!r} does not render currency"
        if stripped and "$" not in stripped:
            return f"displayed text {stripped!r} is not a currency amount"
    elif kind == "date":
        if not any(code in fmt.lower() for code in ("y", "d")):
            return f"format {fmt!r} does not render a date"
        if stripped and not _is_date_like(stripped):
            return f"displayed text {stripped!r} is not a readable date"
    elif kind == "integer":
        lowered = fmt.lower()
        if any(code in lowered for code in ("%", "$", "yy", "dd", "mm")):
            return f"format {fmt!r} is not a plain integer format"
        if stripped and not re.fullmatch(r"-?\d[\d,]*", stripped):
            return f"displayed text {stripped!r} is not a whole number"
    return None


def _is_numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_dump(dump: Dict[str, Any], spec: Dict[str, Any]) -> Dict[str, Any]:
    findings: List[Dict[str, str]] = []

    expected_hash = spec.get("artifact_sha256")
    if expected_hash and dump.get("artifact_sha256") != expected_hash:
        findings.append(_finding(
            SEVERITY_CRITICAL, "ARTIFACT_HASH_MISMATCH", spec.get("artifact", "?"),
            f"recalculated artifact hash {dump.get('artifact_sha256')} does not match the recorded "
            f"release hash {expected_hash}",
        ))

    for error in dump.get("error_cells") or []:
        findings.append(_finding(
            SEVERITY_CRITICAL, "FORMULA_ERROR",
            f"{error.get('sheet')}!{error.get('address')}",
            f"Excel shows the error value {error.get('text')!r}",
        ))

    grouped = _cells_by_sheet(dump)
    all_cells = dump.get("cells") or []

    for table in spec.get("tables") or []:
        rows = _lookup(
            all_cells, table["sheet"], table["key_column"], table["value_column"],
            table.get("first_row", 1), table.get("last_row", 1000),
        )
        for expectation in spec.get("expect") or []:
            if expectation.get("sheet") != table["sheet"]:
                continue
            label = expectation["label"]
            cell = rows.get(label)
            where = f"{table['sheet']} {label!r}"
            if not cell:
                findings.append(_finding(
                    SEVERITY_CRITICAL, "EXPECTED_CELL_MISSING", where,
                    "the expected labelled row was not found in the recalculated workbook",
                ))
                continue
            fmt = str(cell.get("format", ""))
            text = str(cell.get("text", ""))
            if "format" in expectation and fmt != expectation["format"]:
                findings.append(_finding(
                    SEVERITY_CRITICAL, "FORMAT_MISMATCH", where,
                    f"format is {fmt!r}, expected {expectation['format']!r} (displays {text!r})",
                ))
            if "format_contains" in expectation and expectation["format_contains"] not in fmt:
                findings.append(_finding(
                    SEVERITY_CRITICAL, "FORMAT_MISMATCH", where,
                    f"format {fmt!r} does not contain {expectation['format_contains']!r} (displays {text!r})",
                ))
            problem = _check_kind(expectation.get("kind", "text"), fmt, text)
            if problem:
                findings.append(_finding(SEVERITY_CRITICAL, "FORMAT_MISMATCH", where, problem))

    for column in spec.get("columns") or []:
        seen = 0
        for cell in all_cells:
            if cell.get("sheet") != column["sheet"] or cell.get("column") != column["column"]:
                continue
            row = cell.get("row")
            if not isinstance(row, int) or row < column.get("first_row", 1) or row > column.get("last_row", 1000):
                continue
            if not str(cell.get("text", "")).strip() and cell.get("value") in (None, ""):
                continue
            seen += 1
            fmt = str(cell.get("format", ""))
            text = str(cell.get("text", ""))
            where = f"{column['name']} row {row}"
            if "format" in column and fmt != column["format"]:
                findings.append(_finding(
                    SEVERITY_CRITICAL, "FORMAT_MISMATCH", where,
                    f"format is {fmt!r}, expected {column['format']!r} (displays {text!r})",
                ))
            problem = _check_kind(column.get("kind", "text"), fmt, text)
            if problem:
                findings.append(_finding(SEVERITY_CRITICAL, "FORMAT_MISMATCH", where, problem))
        if seen == 0 and column.get("require_rows"):
            findings.append(_finding(
                SEVERITY_WARNING, "COLUMN_EMPTY", column["name"],
                "no populated cells were found in the expected column range",
            ))

    # A number format only affects how a numeric cell is displayed. A text cell
    # (e.g. an ID column, or a formula that returns an instruction string
    # instead of a date) ignores its format entirely, so those are not defects.
    for cell in all_cells:
        fmt = str(cell.get("format", ""))
        text = str(cell.get("text", "")).strip()
        numeric = _is_numeric(cell.get("value"))
        where = f"{cell.get('sheet')}!{cell.get('address')}"
        if not numeric:
            continue
        if "%" in fmt and text and not text.endswith("%"):
            findings.append(_finding(
                SEVERITY_CRITICAL, "PERCENT_DISPLAY_BROKEN", where,
                f"format {fmt!r} renders a percentage but the cell displays {text!r}",
            ))
        if "$" in fmt and text and "$" not in text:
            findings.append(_finding(
                SEVERITY_CRITICAL, "CURRENCY_DISPLAY_BROKEN", where,
                f"format {fmt!r} renders currency but the cell displays {text!r}",
            ))
        if fmt and any(code in fmt.lower() for code in ("yyyy", "dd")) and text and not _is_date_like(text):
            findings.append(_finding(
                SEVERITY_CRITICAL, "DATE_DISPLAY_BROKEN", where,
                f"format {fmt!r} renders a date but the cell displays {text!r}",
            ))

    critical = [f for f in findings if f["severity"] == SEVERITY_CRITICAL]
    return {
        "product_id": spec.get("product_id"),
        "artifact": spec.get("artifact"),
        "artifact_sha256": dump.get("artifact_sha256"),
        "engine": dump.get("engine"),
        "calculated_at_utc": dump.get("calculated_at_utc"),
        "formula_cells": dump.get("formula_cells"),
        "formula_sheets": dump.get("formula_sheets"),
        "scanned_sheets": dump.get("scanned_sheets"),
        "verdict": "FAIL" if critical else "PASS",
        "findings": findings,
        "critical_count": len(critical),
        "warning_count": len(findings) - len(critical),
    }


# ---------------------------------------------------------------------------
# Probe execution
# ---------------------------------------------------------------------------

def run_probe(spec: Dict[str, Any], root: Path = ROOT,
              workdir: Optional[Path] = None) -> Dict[str, Any]:
    if not PROBE.exists():
        raise EngineUnavailable(f"probe script not found: {PROBE}")
    if shutil.which("powershell") is None:
        raise EngineUnavailable("powershell is not on PATH")

    workdir = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="gf_wbqa_"))
    workdir.mkdir(parents=True, exist_ok=True)
    spec_path = workdir / "spec.json"
    out_path = workdir / "dump.json"
    probe_spec = {
        "artifact": spec["artifact"],
        "formula_sheets": spec.get("formula_sheets", []),
        "scan_sheets": spec.get("scan_sheets", []),
    }
    spec_path.write_text(json.dumps(probe_spec, indent=1), encoding="utf-8")

    completed = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(PROBE),
         "-Spec", str(spec_path), "-Out", str(out_path), "-Root", str(root)],
        capture_output=True, text=True, timeout=600,
    )
    if completed.returncode != 0 or not out_path.exists():
        raise EngineUnavailable(
            "Excel COM recalculation failed"
            + (f": {completed.stderr.strip()[:400]}" if completed.stderr else "")
        )
    return json.loads(out_path.read_text(encoding="utf-8-sig"))


def run_product_qa(product_id: str, root: Path = ROOT,
                   workdir: Optional[Path] = None) -> Dict[str, Any]:
    spec = SPECS.get(product_id)
    if spec is None:
        raise KeyError(f"no workbook QA spec is registered for {product_id}")
    dump = run_probe(spec, root=root, workdir=workdir)
    return validate_dump(dump, spec)


def write_evidence(result: Dict[str, Any], root: Path = ROOT) -> Path:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    target = root / "reports" / str(result["product_id"]) / f"WORKBOOK_QA_{day}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(result)
    payload["schema"] = "workbook_qa/v1"
    payload["recorded_at_utc"] = datetime.now(timezone.utc).isoformat()
    payload["limitations"] = [
        "The probe runs against a temporary read-only copy; it never opens the release file for write.",
        "Number-format and value checks are limited to the sheets and cells named in the spec.",
        "Excel is the only supported native engine; no other spreadsheet engine is installed here.",
    ]
    with open(target, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=1, ensure_ascii=False)
        handle.write("\n")
    return target


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Native workbook recalculation QA.")
    parser.add_argument("--product", required=True, help="product id with a registered spec")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write-evidence", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    try:
        result = run_product_qa(args.product, root=root)
    except EngineUnavailable as exc:
        print(f"native workbook QA limited: {exc}", file=sys.stderr)
        return 2
    except KeyError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.write_evidence:
        path = write_evidence(result, root=root)
        result["evidence_path"] = str(path.relative_to(root)).replace("\\", "/")

    if args.json:
        print(json.dumps(result, indent=1, ensure_ascii=False))
    else:
        engine = result.get("engine") or {}
        print(
            f"{args.product}: {result['verdict']} "
            f"({result['critical_count']} critical, {result['warning_count']} warning) "
            f"on {engine.get('name')} {engine.get('version')} build {engine.get('build')}"
        )
        for finding in result["findings"]:
            print(f"  [{finding['severity']}] {finding['code']} {finding['where']}: {finding['detail']}")

    return 1 if result["verdict"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
