"""Galaxy Forge -- shared workbook builder for the cohort generators.

WHY THIS EXISTS
---------------
All four cohort build.py files carried an identical build_xlsx() with three
defects, found 2026-10-14 by opening the shipped workbooks:

  1. A formula addressed to another sheet ("Summary!B2") was written to the
     CURRENT sheet when that sheet did not exist -- and the Summary sheet was
     never created. So "total deals" landed in the Brand cell of the first
     example deal, overwriting its brand name. Six live workbooks are
     affected; the specs themselves were right.
  2. Specs say "copy down" for per-row formulas (=B2*E2, =E2+F2), but only
     row 2 ever received the formula. Rows below held hand-typed numbers that
     drift from the method the guide teaches.
  3. Example dates were written as text ("2026-09-10"), so date arithmetic
     on them depends on how a given Excel install coerces text.

What this builder does differently, and nothing more:
  * creates any sheet a formula is addressed to, and labels each summary
    formula with the spec's own `note`
  * moves an aggregate formula that the spec placed inside a tracker's own
    data column (e.g. =COUNTA(A2:A20) at A8, where the buyer's 7th deal will
    go) onto the Summary sheet, rewriting its references to stay correct
  * fills same-row formulas into empty cells and the entry rows below the
    examples; an authored example value is never overwritten, it is reported
    (`mismatches`) so a person can correct the spec
  * writes ISO example dates as real dates
  * writes sheet notes to a Notes sheet instead of under the table

The spec files are never modified.
"""
from __future__ import annotations

import datetime as _dt
import json
import re
from pathlib import Path

ENTRY_ROWS = 200
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_RANGE_FN = re.compile(r"\b(COUNTA|COUNTIF|COUNTIFS|SUMIF|SUMIFS|SUM|AVERAGE|AVERAGEIF|MAX|MIN)\s*\(", re.I)
_REF = re.compile(r"(?<![A-Za-z0-9_!'.$])(\$?[A-Z]{1,3}\$?\d+(?::\$?[A-Z]{1,3}\$?\d+)?)(?![A-Za-z0-9_(])")


def _q(name):
    return "'" + name.replace("'", "''") + "'"


def _split_strings(formula):
    """Yield (is_string_literal, chunk) so references inside "text" are never touched."""
    for i, part in enumerate(re.split(r'("(?:[^"]|"")*")', formula)):
        yield i % 2 == 1, part


def qualify(formula, sheet):
    """Prefix unqualified cell/range references with 'sheet'! (for moving a formula)."""
    out = []
    for is_str, part in _split_strings(formula):
        out.append(part if is_str else _REF.sub(lambda m: f"{_q(sheet)}!{m.group(1)}", part))
    return "".join(out)


def _row_refs(formula):
    refs = []
    for is_str, part in _split_strings(formula):
        if not is_str:
            refs += _REF.findall(part)
    return refs


def is_row_formula(formula, row):
    """Same-row only: every reference -- a cell, or a range like B2:G2 -- lies
    on `row`, with no sheet hops. =SUM(B2:G2) is a row total and fills down;
    =SUM(B2:B9) spans rows and is a summary."""
    if "!" in formula:
        return False
    refs = _row_refs(formula)

    def rows_of(ref):
        return {int(re.sub(r"[^0-9]", "", part)) for part in ref.split(":")}

    return bool(refs) and all(rows_of(r) == {row} for r in refs)


def shift_row(formula, src, dst):
    out = []
    for is_str, part in _split_strings(formula):
        out.append(part if is_str else _REF.sub(
            lambda m: re.sub(r"(\$?[A-Z]{1,3})\$?%d\b" % src, lambda n: f"{n.group(1)}{dst}", m.group(1)), part))
    return "".join(out)


def _coerce(v):
    if isinstance(v, str) and _ISO.match(v):
        try:
            return _dt.date.fromisoformat(v)
        except ValueError:
            return v
    return v


def build_xlsx(spec_path, xlsx_path, report=None):
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import column_index_from_string, get_column_letter

    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    rep = report if report is not None else {}
    rep.update(moved=[], filled=[], mismatches=[], dates=0, created_sheets=[])
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    hdr_fill = PatternFill("solid", fgColor="1F3864")
    hdr_font = Font(bold=True, color="FFFFFF")
    shapes = {}

    for sh in spec["sheets"]:
        ws = wb.create_sheet(sh["name"][:31])
        for c, col in enumerate(sh["columns"], 1):
            cell = ws.cell(row=1, column=c, value=col)
            cell.font, cell.fill = hdr_font, hdr_fill
            cell.alignment = Alignment(wrap_text=True, vertical="center")
        rows = sh.get("example_rows", [])
        for r, row in enumerate(rows, 2):
            for c, val in enumerate(row, 1):
                if c <= len(sh["columns"]):
                    v = _coerce(val)
                    if v is not val:
                        rep["dates"] += 1
                    cell = ws.cell(row=r, column=c, value=v if v != "" else None)
                    if isinstance(v, _dt.date):
                        cell.number_format = "yyyy-mm-dd"
        for c in range(1, len(sh["columns"]) + 1):
            ws.column_dimensions[get_column_letter(c)].width = 22
        ws.freeze_panes = "A2"
        shapes[ws.title] = (len(sh["columns"]), 1 + len(rows))

    def summary_ws():
        if "Summary" not in wb.sheetnames:
            s = wb.create_sheet("Summary", 0)
            s["A1"], s["B1"] = "Key figure", "Value"
            s["A1"].font = s["B1"].font = Font(bold=True)
            s.column_dimensions["A"].width = 60
            s.column_dimensions["B"].width = 18
            rep["created_sheets"].append("Summary")
        return wb["Summary"]

    def put_summary(label, formula):
        s = summary_ws()
        r = s.max_row + 1
        s.cell(row=r, column=1, value=label)
        s.cell(row=r, column=2, value=formula)

    for sh in spec["sheets"]:
        home = sh["name"][:31]
        ncols, last_example = shapes[home]
        for f in sh.get("formulas", []):
            coord, formula, note = f["cell"], f["formula"], f.get("note") or ""
            target = home
            if "!" in coord:
                target, coord = coord.split("!", 1)
                target = target.strip("'")
            m = re.match(r"([A-Z]+)(\d+)$", coord)
            col, row = column_index_from_string(m.group(1)), int(m.group(2))
            if target != home and target == "Summary":
                put_summary(note or f"{home} figure", formula)
                continue
            if target not in wb.sheetnames:
                wb.create_sheet(target)
                rep["created_sheets"].append(target)
            ws = wb[target]
            inside_table = target == home and col <= ncols and row >= 2
            if inside_table and _RANGE_FN.search(formula) and not is_row_formula(formula, row):
                put_summary(note or f"{home}: {formula}", qualify(formula, home))
                rep["moved"].append(f"{home}!{coord}")
                continue
            ws.cell(row=row, column=col, value=formula)
            if target == home and is_row_formula(formula, row):
                for r in range(row + 1, max(last_example, row) + ENTRY_ROWS + 1):
                    cell = ws.cell(row=r, column=col)
                    old = cell.value
                    new = shift_row(formula, row, r)
                    if isinstance(old, str) and old.startswith("="):
                        continue
                    if r <= last_example and old not in (None, ""):
                        # Never overwrite an authored example value: 18 of 171
                        # checkable ones disagreed with their own formula, and
                        # the guide may quote them. Report instead; fix in spec.
                        rep["mismatches"].append({"cell": f"{home}!{cell.coordinate}", "example_value": old, "formula": new})
                        continue
                    cell.value = new
                rep["filled"].append(f"{home}!{coord}")

    notes = [(sh["name"], sh["notes"]) for sh in spec["sheets"] if sh.get("notes")]
    if notes:
        ns = wb.create_sheet("Notes")
        ns.column_dimensions["A"].width = 28
        ns.column_dimensions["B"].width = 110
        for i, (name, text) in enumerate(notes, 1):
            ns.cell(row=i, column=1, value=name).font = Font(bold=True)
            c = ns.cell(row=i, column=2, value=text)
            c.alignment = Alignment(wrap_text=True, vertical="top")
    wb.save(xlsx_path)
    return rep
