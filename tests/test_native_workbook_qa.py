# -*- coding: utf-8 -*-
"""Regression tests for the reusable native workbook QA capability.

Cycle 101 found seven number-format defects in B12-010 that a value-only check
could not see: Excel displayed 100% for a count, $1 for a rate, 3000000% for a
currency total, an Excel serial for a date, and so on. These tests prove the
validator catches every one of those classes if it is reintroduced, using
synthetic recalculation dumps -- the production workbook is never modified.

The Excel automation itself is deliberately not exercised here: the decision
logic is separated from Excel so it runs in any environment, and
`run_product_qa` is the thin layer that requires a real Excel installation.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import native_workbook_qa as wbqa  # noqa: E402

MANIFEST = ROOT / "reports" / "B12-010" / "MANIFEST_2026-10-19.json"
ARTIFACT = ROOT / "books" / "batch12" / "B12-010_grant_pipeline_tracker.xlsx"

HASH = "df49cecaf704cb06dec3b48c9f826c94cfdae9e2bf91d3a2b76fc670593b8574"


def cell(sheet, address, row, column, text, value, fmt, formula=None):
    return {
        "sheet": sheet, "address": address, "row": row, "column": column,
        "text": text, "value": value, "format": fmt, "formula": formula,
    }


DASHBOARD_ROWS = [
    (2, "Opportunities tracked", "4", 4, "General"),
    (3, "Active (not awarded, declined or withdrawn)", "3", 3, "General"),
    (4, "Submitted, awaiting a decision", "0", 0, "General"),
    (5, "Decisions received (awarded + declined)", "1", 1, "General"),
    (6, "Awarded (count)", "1", 1, "0"),
    (7, "Award rate", "100%", 1, "0%"),
    (8, "Total awarded (USD)", "$15,000", 15000, '"$"#,##0'),
    (9, "Total requested (USD)", "$30,000", 30000, '"$"#,##0'),
    (10, "Awarded against requested", "50%", 0.5, "0%"),
    (11, "Overdue deadlines", "0", 0, "0"),
    (12, "Deadlines due within 14 days", "1", 1, "0"),
    (13, "Next deadline (open rows only)", "2026-11-02", 46328, "yyyy-mm-dd"),
    (14, "Applications with required documents not ready", "1", 1, "0"),
    (15, "Duplicate rows to merge", "2", 2, "0"),
    (16, "Rows with a data problem", "0", 0, "0"),
    (17, "Post-award reports overdue", "0", 0, "0"),
    (18, "Post-award reports due within 30 days", "0", 0, "0"),
    (19, "Pipeline verdict", "MERGE OR DELETE THE DUPLICATE ROWS", "MERGE OR DELETE THE DUPLICATE ROWS", "General"),
    (21, "Stage", "Count", "Count", "General"),
    (22, "Research", "2", 2, "0"),
    (23, "Eligibility", "0", 0, "0"),
    (24, "Drafting", "1", 1, "0"),
    (25, "Internal review", "0", 0, "0"),
    (26, "Submitted", "0", 0, "0"),
    (27, "Awarded", "1", 1, "0"),
    (28, "Declined", "0", 0, "0"),
    (29, "Withdrawn", "0", 0, "0"),
    (30, "Rows with no status yet", "0", 0, "0"),
]


def base_dump():
    cells = []
    for row, label, text, value, fmt in DASHBOARD_ROWS:
        cells.append(cell("Dashboard", f"A{row}", row, 1, label, label, "General"))
        cells.append(cell("Dashboard", f"B{row}", row, 2, text, value, fmt))
    for row in (2, 4):
        cells.append(cell("Opportunities", f"V{row}", row, 22, "2027-03-15", 46461, "yyyy-mm-dd", "=H2"))
    return {
        "schema": "native_recalc_probe/v1",
        "engine": {"name": "Microsoft Excel", "version": "16.0", "build": "19127"},
        "artifact": "books/batch12/B12-010_grant_pipeline_tracker.xlsx",
        "artifact_sha256": HASH,
        "calculated_at_utc": "2026-10-19T12:34:07Z",
        "formula_cells": 148,
        "formula_sheets": ["Opportunities", "Timeline", "Dashboard"],
        "scanned_sheets": ["Dashboard", "Opportunities"],
        "error_cells": [],
        "cells": cells,
    }


def mutate(dump, sheet, address, **changes):
    for entry in dump["cells"]:
        if entry["sheet"] == sheet and entry["address"] == address:
            entry.update(changes)
            return dump
    raise AssertionError(f"cell {sheet}!{address} not present in the fixture")


class TestValidatorAcceptsCorrectWorkbook(unittest.TestCase):
    def test_clean_dump_passes(self):
        result = wbqa.validate_dump(base_dump(), wbqa.B12_010_SPEC)
        self.assertEqual("PASS", result["verdict"], result["findings"])

    def test_text_cell_carrying_a_date_format_is_not_a_defect(self):
        dump = base_dump()
        dump["cells"].append(cell("Docs", "A2", 2, 1, "EX-001", "EX-001", "yyyy-mm-dd"))
        result = wbqa.validate_dump(dump, wbqa.B12_010_SPEC)
        self.assertEqual("PASS", result["verdict"], result["findings"])

    def test_header_text_of_hash_is_not_an_error(self):
        dump = base_dump()
        dump["cells"].append(cell("Stages", "A1", 1, 1, "#", "#", "General"))
        result = wbqa.validate_dump(dump, wbqa.B12_010_SPEC)
        self.assertEqual("PASS", result["verdict"], result["findings"])


class TestCycle101DefectsAreCaught(unittest.TestCase):
    """Each of the seven Cycle 101 defects, reintroduced one at a time."""

    def _assert_caught(self, dump, needle):
        result = wbqa.validate_dump(dump, wbqa.B12_010_SPEC)
        self.assertEqual("FAIL", result["verdict"])
        joined = json.dumps(result["findings"], ensure_ascii=False)
        self.assertIn(needle, joined, joined)

    def test_count_rendered_as_a_percentage(self):
        # Original defect: Awarded (count) had format 0% and displayed 100%.
        self._assert_caught(mutate(base_dump(), "Dashboard", "B6", format="0%", text="100%"), "Awarded (count)")

    def test_rate_rendered_as_currency(self):
        # Original defect: Award rate had format "$"#,##0 and displayed $1.
        self._assert_caught(mutate(base_dump(), "Dashboard", "B7", format='"$"#,##0', text="$1"), "Award rate")

    def test_currency_total_rendered_as_a_percentage(self):
        # Original defect: Total requested had format 0% and displayed 3000000%.
        self._assert_caught(
            mutate(base_dump(), "Dashboard", "B9", format="0%", text="3000000%"),
            "Total requested (USD)",
        )

    def test_share_rendered_as_a_plain_number(self):
        # Original defect: Awarded against requested had format 0 and displayed 1.
        self._assert_caught(
            mutate(base_dump(), "Dashboard", "B10", format="0", text="1"),
            "Awarded against requested",
        )

    def test_count_rendered_as_a_date(self):
        # Original defect: Deadlines due within 14 days had a date format and
        # displayed 1900-01-01 (the serial 1 formatted as a date).
        self._assert_caught(
            mutate(base_dump(), "Dashboard", "B12", format="yyyy-mm-dd", text="1900-01-01"),
            "Deadlines due within 14 days",
        )

    def test_date_rendered_as_an_excel_serial(self):
        # Original defect: Next deadline had format 0 and displayed 46328.
        self._assert_caught(
            mutate(base_dump(), "Dashboard", "B13", format="0", text="46328"),
            "Next deadline (open rows only)",
        )

    def test_helper_column_rendered_as_an_excel_serial(self):
        # Original defect: Opportunities!V had General format and displayed 46461.
        self._assert_caught(
            mutate(base_dump(), "Opportunities", "V2", format="General", text="46461"),
            "Opportunities!V",
        )


class TestOtherSafeguards(unittest.TestCase):
    def test_artifact_hash_mismatch_is_critical(self):
        dump = base_dump()
        dump["artifact_sha256"] = "0" * 64
        result = wbqa.validate_dump(dump, wbqa.B12_010_SPEC)
        self.assertEqual("FAIL", result["verdict"])
        self.assertIn("ARTIFACT_HASH_MISMATCH", json.dumps(result["findings"]))

    def test_formula_error_is_critical(self):
        dump = base_dump()
        dump["error_cells"] = [{"sheet": "Dashboard", "address": "B7", "text": "#DIV/0!"}]
        result = wbqa.validate_dump(dump, wbqa.B12_010_SPEC)
        self.assertEqual("FAIL", result["verdict"])
        self.assertIn("FORMULA_ERROR", json.dumps(result["findings"]))

    def test_missing_expected_label_is_critical(self):
        dump = base_dump()
        dump["cells"] = [c for c in dump["cells"] if not (c["sheet"] == "Dashboard" and c["row"] == 7)]
        result = wbqa.validate_dump(dump, wbqa.B12_010_SPEC)
        self.assertEqual("FAIL", result["verdict"])
        self.assertIn("EXPECTED_CELL_MISSING", json.dumps(result["findings"]))

    def test_numeric_percent_format_without_percent_text_is_critical(self):
        dump = base_dump()
        dump["cells"].append(cell("Timeline", "D2", 2, 4, "0.5", 0.5, "0%"))
        result = wbqa.validate_dump(dump, wbqa.B12_010_SPEC)
        self.assertEqual("FAIL", result["verdict"])
        self.assertIn("PERCENT_DISPLAY_BROKEN", json.dumps(result["findings"]))

    def test_unregistered_product_is_rejected(self):
        with self.assertRaises(KeyError):
            wbqa.run_product_qa("B12-999")


class TestSpecMatchesTheRelease(unittest.TestCase):
    def test_spec_hash_matches_the_manifest_and_the_artifact_on_disk(self):
        spec_hash = wbqa.B12_010_SPEC["artifact_sha256"]
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        xlsx = next(f for f in manifest["files"] if f["path"].lower().endswith(".xlsx"))
        self.assertEqual(spec_hash, xlsx["sha256"])

        import hashlib
        on_disk = hashlib.sha256(ARTIFACT.read_bytes()).hexdigest()
        self.assertEqual(spec_hash, on_disk)

    def test_every_cycle101_defect_label_has_an_expectation(self):
        labels = {e["label"] for e in wbqa.B12_010_SPEC["expect"]}
        for label in (
            "Awarded (count)", "Award rate", "Total requested (USD)",
            "Awarded against requested", "Deadlines due within 14 days",
            "Next deadline (open rows only)",
        ):
            self.assertIn(label, labels)
        self.assertTrue(any(c["name"].startswith("Opportunities!V") for c in wbqa.B12_010_SPEC["columns"]))


if __name__ == "__main__":
    unittest.main()
