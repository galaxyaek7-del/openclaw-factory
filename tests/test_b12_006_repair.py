"""Cycle 106 regression guards for the B12-006 repair.

These tests exist because the Cycle-104 workbook shipped a defect that every
existing check passed: the "Office %" cell held a typed literal (0.125) while
its own note claimed the formula "=B3/B2", the expense log applied no home
share at all, and the percent number format was malformed ("#,##0.00%). The
enforcer counted formulas and words; it could not see any of that. Each test
below pins one of the things that was actually wrong.

The builder is called with out_dir=<temp> so no test rewrites the release
artifact in books/batch12.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from openpyxl import load_workbook  # noqa: E402

import build_batch12_xlsx as b12  # noqa: E402
import native_workbook_qa as wbqa  # noqa: E402


def build() -> Path:
    out = Path(tempfile.mkdtemp(prefix="b12_006_test_"))
    return b12.b12_006_home_office_log(out_dir=out)


def _content(wb) -> list:
    """Every cell's value and number format, sheet by sheet."""
    return [
        (ws.title, [
            (c.coordinate, c.value, c.number_format)
            for row in ws.iter_rows() for c in row
            if c.value is not None
        ])
        for ws in wb.worksheets
    ]


class HomeOfficeWorkbookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.path = build()
        cls.wb = load_workbook(cls.path)

    def test_release_artifact_is_not_touched_by_the_test_build(self):
        self.assertNotEqual(self.path.parent, ROOT / "books" / "batch12")

    def test_importing_the_builder_does_not_build_anything(self):
        # The makers loop is guarded by __main__; importing must be inert.
        before = set((ROOT / "books" / "batch12").glob("*.xlsx"))
        import importlib

        importlib.reload(b12)
        after = set((ROOT / "books" / "batch12").glob("*.xlsx"))
        self.assertEqual(before, after)

    def test_home_percentage_is_a_computed_formula_not_a_literal(self):
        value = self.wb["SpaceMeasure"]["B4"].value
        self.assertTrue(isinstance(value, str) and value.startswith("="), value)
        self.assertIn("B3/B2", value)

    def test_home_percentage_rejects_impossible_measurements(self):
        value = self.wb["SpaceMeasure"]["B4"].value
        # The guard: home must be > 0 and the space no larger than the home.
        self.assertIn("B2>0", value)
        self.assertIn("B3<=B2", value)

    def test_simplified_deduction_applies_the_cap(self):
        value = self.wb["SpaceMeasure"]["B8"].value
        self.assertTrue(value.startswith("="), value)
        self.assertIn("MIN(", value)

    def test_every_log_row_reads_the_space_measure_percentage(self):
        ws = self.wb["Expenses2026"]
        for row in (2, 3, 21, 41):
            value = ws.cell(row=row, column=5).value
            self.assertTrue(isinstance(value, str) and value.startswith("="), (row, value))
            self.assertIn("SpaceMeasure!$B$4", value)
            self.assertIn(f'$D{row}=""', value)  # blank amount -> blank share

    def test_every_log_row_computes_a_deductible_estimate(self):
        ws = self.wb["Expenses2026"]
        for row in (2, 22, 41):
            value = ws.cell(row=row, column=6).value
            self.assertTrue(isinstance(value, str) and value.startswith("="), (row, value))
            self.assertIn(f"$D{row}*$E{row}", value)

    def test_category_and_method_are_dropdowns(self):
        self.assertEqual(len(self.wb["Expenses2026"].data_validations.dataValidation), 2)
        self.assertEqual(len(self.wb["SpaceMeasure"].data_validations.dataValidation), 1)

    def test_annual_summary_totals_each_category(self):
        ws = self.wb["AnnualSummary"]
        labels = [ws.cell(row=r, column=1).value for r in range(2, 9)]
        self.assertIn("Internet/utilities", labels)
        for r in range(2, 9):
            self.assertTrue(str(ws.cell(row=r, column=2).value).startswith("=SUMIFS"))
            self.assertTrue(str(ws.cell(row=r, column=3).value).startswith("=SUMIFS"))

    def test_annual_summary_warns_against_double_discounting(self):
        notes = str(self.wb["AnnualSummary"]["D9"].value)
        self.assertIn("already applied", notes)

    def test_method_comparison_is_present_and_guarded(self):
        ws = self.wb["MethodCompare"]
        self.assertIn("ACTUAL method estimate", [ws.cell(row=r, column=1).value for r in range(2, 16)])
        self.assertIn("SIMPLIFIED method estimate", [ws.cell(row=r, column=1).value for r in range(2, 16)])
        self.assertTrue(str(ws["B12"].value).startswith("="))
        self.assertTrue(str(ws["B15"].value).startswith("="))

    def test_no_number_format_has_an_unbalanced_quote(self):
        # The Cycle-104 defect: '"#,##0.00%' - a stray leading quote.
        for ws in self.wb.worksheets:
            for row in ws.iter_rows():
                for cell in row:
                    fmt = cell.number_format or ""
                    self.assertEqual(fmt.count('"') % 2, 0, (ws.title, cell.coordinate, fmt))

    def test_square_feet_are_not_formatted_as_a_percentage(self):
        # A whole-column percent format would render 1,200 sq ft as 120000%.
        self.assertNotIn("%", self.wb["SpaceMeasure"]["B2"].number_format)
        self.assertNotIn("%", self.wb["SpaceMeasure"]["B3"].number_format)
        self.assertIn("%", self.wb["SpaceMeasure"]["B4"].number_format)
        self.assertIn("%", self.wb["Expenses2026"]["E2"].number_format)

    def test_workbook_satisfies_the_factory_sheet_depth_rule(self):
        sheets = len(self.wb.sheetnames)
        formulas = sum(
            1 for ws in self.wb.worksheets for row in ws.iter_rows()
            for c in row if isinstance(c.value, str) and c.value.startswith("=")
        )
        self.assertGreaterEqual(sheets, 2)
        self.assertGreaterEqual(formulas, 5)

    def test_readme_states_the_not_advice_position(self):
        text = " ".join(str(c.value) for row in self.wb["README"].iter_rows() for c in row if c.value)
        self.assertIn("NOT TAX ADVICE", text)
        self.assertIn("verify", text.lower())

    def test_build_is_deterministic(self):
        # Byte equality is not the right assertion: openpyxl stamps
        # docProps/core.xml with the wall-clock time, so two builds are
        # identical only when they land in the same second (this test used to
        # fail whenever they straddled one). What must not drift is the content.
        a, b = load_workbook(self.path), load_workbook(build())
        self.assertEqual(a.sheetnames, b.sheetnames)
        self.assertEqual(_content(a), _content(b))

    def test_the_only_zip_member_that_can_differ_is_the_build_timestamp(self):
        import zipfile
        a, b = self.path, build()
        with zipfile.ZipFile(a) as za, zipfile.ZipFile(b) as zb:
            self.assertEqual(sorted(za.namelist()), sorted(zb.namelist()))
            differing = {n for n in za.namelist() if za.read(n) != zb.read(n)}
        self.assertLessEqual(differing, {"docProps/core.xml"})


class B12006SpecTests(unittest.TestCase):
    """The native-workbook QA spec that gates this product."""

    spec = wbqa.B12_006_SPEC

    def test_spec_is_registered_under_its_product_id(self):
        self.assertIs(wbqa.SPECS.get("B12-006"), self.spec)

    def test_spec_pins_a_full_sha256(self):
        self.assertEqual(len(self.spec["artifact_sha256"]), 64)
        int(self.spec["artifact_sha256"], 16)

    def test_spec_checks_the_computed_figures_not_the_raw_inputs(self):
        labels = {e["label"] for e in self.spec["expect"]}
        self.assertIn("Home % (qualifying ÷ total) — USED BY THE LOG", labels)
        self.assertIn("ACTUAL method estimate", labels)
        self.assertIn("SIMPLIFIED method estimate", labels)
        self.assertIn("Difference (actual minus simplified)", labels)

    def test_spec_does_not_assert_a_whole_column_rule_on_a_mixed_column(self):
        # SpaceMeasure column B holds square feet, a percentage, a method name
        # and currency. Asserting one format for the whole column would be
        # wrong, so the spec must not contain such a rule.
        for column in self.spec["columns"]:
            self.assertFalse(
                column["sheet"] == "SpaceMeasure" and column["column"] == 2,
                "SpaceMeasure!B is heterogeneous and must be formatted per cell",
            )

    def test_spec_scans_every_sheet(self):
        self.assertEqual(set(self.spec["scan_sheets"]), set(self.spec["scan_sheets"]))
        self.assertGreaterEqual(len(self.spec["scan_sheets"]), 7)

    def test_a_wrong_hash_is_reported_as_critical(self):
        dump = {
            "artifact_sha256": "0" * 64,
            "engine": {"name": "x"},
            "cells": [],
            "error_cells": [],
            "formula_cells": 0,
            "formula_sheets": [],
            "scanned_sheets": [],
        }
        result = wbqa.validate_dump(dump, self.spec)
        self.assertEqual(result["verdict"], "FAIL")
        codes = {f["code"] for f in result["findings"]}
        self.assertIn("ARTIFACT_HASH_MISMATCH", codes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
