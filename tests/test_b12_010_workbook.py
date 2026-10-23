# -*- coding: utf-8 -*-
"""Contract tests for the shipped B12-010 Nonprofit Grant Pipeline Tracker.

These test the *files that would be uploaded*, not a rebuild: the workbook and
guide are canonical artifacts whose hashes are recorded in the manifest and in
data/product_batch_12.json. If either is legitimately rebuilt, the manifest and
these hashes must be updated together -- that is the point.

The deadline/reporting rules are additionally re-derived in plain Python so the
documented behaviour (which the guide explains in words) cannot silently drift
away from the shipped formulas.
"""
import datetime as dt
import hashlib
import json
import math
import re
import unittest
from pathlib import Path, PureWindowsPath

import openpyxl
from PIL import Image
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
XLSX = ROOT / "books" / "batch12" / "B12-010_grant_pipeline_tracker.xlsx"
PDF = ROOT / "books" / "batch12" / "B12-010_grant_pipeline_guide.pdf"
COVER = ROOT / "books" / "covers" / "B12-010.png"
MANIFEST = ROOT / "reports" / "B12-010" / "MANIFEST_2026-10-19.json"
PAGE = ROOT / "customer_site" / "b12-grant-pipeline-tracker.html"
REGISTRY = ROOT / "data" / "product_batch_12.json"

EXPECTED = {
    "B12-010_grant_pipeline_tracker.xlsx": (
        38765,
        "df49cecaf704cb06dec3b48c9f826c94cfdae9e2bf91d3a2b76fc670593b8574",
    ),
    "B12-010_grant_pipeline_guide.pdf": (
        45453,
        "b7ad0849a7d248db821c79873a8cdc3c42399a6ce054083eaf650298e97f0a49",
    ),
    "B12-010.png": (
        42566,
        "c17de7066cbd9bf22affa138881fc67ed3d64e7598756277b807836eaaf122ec",
    ),
}

SHEETS = ["Opportunities", "Docs", "Budget", "Timeline", "Dashboard",
          "Stages", "Eligibility", "DocLibrary", "README"]

OPPORTUNITY_HEADERS = [
    "ID", "Funder", "Program", "Focus area", "Geography",
    "Award min (USD)", "Award max (USD)", "Deadline", "Status", "Owner",
    "Source URL", "Next action", "Submitted", "Decision", "Awarded (USD)",
    "Docs ready", "Docs gap", "Days to deadline", "Deadline state",
    "Duplicate?", "Row check", "Open deadline (helper)",
]


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def deadline_state(today, deadline, status):
    """The rule the guide describes, re-derived independently of Excel."""
    if status in ("Awarded", "Declined", "Withdrawn"):
        return "CLOSED"
    if deadline is None:
        return "NO DEADLINE SET"
    days = (deadline - today).days
    if days < 0:
        return "OVERDUE %d DAYS" % -days
    if days <= 14:
        return "DUE IN %d DAYS" % days
    return "OPEN"


def next_report_due(today, first_due, repeat_days):
    if first_due is None or not repeat_days or repeat_days <= 0:
        return None
    steps = max(0, math.ceil((today - first_due).days / repeat_days))
    return first_due + dt.timedelta(days=steps * repeat_days)


class TestCanonicalArtifacts(unittest.TestCase):
    def test_files_exist_at_the_recorded_size_and_hash(self):
        for name, (size, digest) in EXPECTED.items():
            path = ROOT / "books" / "batch12" / name
            if name.endswith(".png"):
                path = COVER
            self.assertTrue(path.exists(), path)
            self.assertEqual(path.stat().st_size, size, name)
            self.assertEqual(_sha256(path), digest, name)

    def test_manifest_agrees_with_the_files_on_disk(self):
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        # The manifest was written on Windows ("books\batch12\..."); PureWindowsPath
        # splits both separators, so this also holds on CI's Linux runner.
        recorded = {PureWindowsPath(f["path"]).name: f for f in data["files"]}
        for name, (size, digest) in EXPECTED.items():
            self.assertIn(name, recorded, name)
            self.assertEqual(recorded[name]["bytes"], size, name)
            self.assertEqual(recorded[name]["sha256"], digest, name)
        self.assertEqual(data["status"], "READY_FOR_AUTHORIZATION")
        self.assertFalse(data["publication"]["published"])
        self.assertIsNone(data["publication"]["listing_url"])
        self.assertTrue(data["authorization_required"])
        self.assertIsNone(data["authorization_phrase"])


class TestWorkbook(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wb = openpyxl.load_workbook(XLSX)
        cls.ws = cls.wb["Opportunities"]

    def test_sheet_inventory(self):
        self.assertEqual(self.wb.sheetnames, SHEETS)

    def test_formula_and_validation_counts(self):
        formulas = 0
        validations = 0
        for ws in self.wb.worksheets:
            for row in ws.iter_rows():
                for cell in row:
                    if isinstance(cell.value, str) and cell.value.startswith("="):
                        formulas += 1
            validations += len(ws.data_validations.dataValidation)
        self.assertEqual(formulas, 427)
        self.assertEqual(validations, 11)

    def test_opportunity_header_contract(self):
        header = [self.ws.cell(1, c).value for c in range(1, 23)]
        self.assertEqual(header, OPPORTUNITY_HEADERS)

    def test_example_rows_are_real_dates_with_two_deliberate_duplicates(self):
        ids = [self.ws.cell(r, 1).value for r in range(2, 6)]
        self.assertEqual(ids, ["EX-001", "EX-002", "EX-003", "EX-004"])
        for r in (2, 3, 4, 5):
            self.assertIsInstance(self.ws.cell(r, 8).value, dt.datetime)
        pairs = [(self.ws.cell(r, 2).value, self.ws.cell(r, 3).value)
                 for r in range(2, 6)]
        self.assertEqual(pairs[0], pairs[3])

    def test_deadline_formula_tokens_cannot_silently_change_rule(self):
        s2 = self.ws["S2"].value
        for token in ('"OVERDUE "', '"DUE IN "', '"CLOSED"', '"NO DEADLINE SET"',
                      "<=14", '"Awarded"', '"Declined"', '"Withdrawn"'):
            self.assertIn(token, s2)
        self.assertIn("TODAY()", s2)
        v2 = self.ws["V2"].value
        self.assertIn('$I2<>"Awarded"', v2)
        self.assertIn('$I2<>"Declined"', v2)
        self.assertIn('$I2<>"Withdrawn"', v2)

    def test_row_check_names_concrete_problems(self):
        u2 = self.ws["U2"].value
        for phrase in ("No funder name", "Award max is below award min",
                       "no submitted date", "no awarded amount",
                       "no deadline date", "above the award max"):
            self.assertIn(phrase, u2)

    def test_document_and_eligibility_libraries_are_twelve_each(self):
        self.assertEqual(sum(1 for r in range(2, 14)
                             if self.wb["DocLibrary"].cell(r, 1).value), 12)
        self.assertEqual(sum(1 for r in range(2, 14)
                             if self.wb["Eligibility"].cell(r, 1).value), 12)
        self.assertEqual(sum(1 for r in range(2, 9)
                             if self.wb["Stages"].cell(r, 1).value), 7)

    def test_dashboard_reads_only_from_the_real_sheets(self):
        d = self.wb["Dashboard"]
        for r in (2, 3, 8, 11):
            self.assertIn("Opportunities!", d.cell(r, 2).value)
        for r in (17, 18):
            self.assertIn("Timeline!", d.cell(r, 2).value)

    def test_number_formats_match_the_kind_of_number_they_show(self):
        """Cycle 101: a real Excel recalc exposed formats applied one row off.

        Values were right and text was wrong -- 100% for a count, $1 for a
        rate, 3000000% for money, 1900-01-01 for a count, 46328 for a date.
        A value-only re-derivation cannot catch that, so assert the formats.
        """
        d = self.wb["Dashboard"]
        expected = {
            "B6": "0",              # Awarded (count)
            "B7": "0%",             # Award rate
            "B8": '"$"#,##0',       # Total awarded (USD)
            "B9": '"$"#,##0',       # Total requested (USD)
            "B10": "0%",            # Awarded against requested
            "B12": "0",             # Deadlines due within 14 days
            "B13": "yyyy-mm-dd",    # Next deadline (open rows only)
        }
        for coord, fmt in expected.items():
            self.assertEqual(d[coord].number_format, fmt, coord)
        for r in list(range(14, 19)) + list(range(22, 31)):
            self.assertIn(d.cell(r, 2).number_format, ("0", "General"), "B%d" % r)
        self.assertEqual(self.ws["V2"].number_format, "yyyy-mm-dd")


class TestRulesRederived(unittest.TestCase):
    """Independent of Excel: the behaviour the guide promises in words."""

    def test_deadline_states(self):
        today = dt.date(2026, 12, 15)
        self.assertEqual(deadline_state(today, dt.date(2027, 3, 15), "Drafting"), "OPEN")
        self.assertEqual(deadline_state(today, dt.date(2026, 12, 29), "Drafting"), "DUE IN 14 DAYS")
        self.assertEqual(deadline_state(today, dt.date(2026, 12, 30), "Drafting"), "OPEN")
        self.assertEqual(deadline_state(today, dt.date(2026, 12, 14), "Drafting"), "OVERDUE 1 DAYS")
        self.assertEqual(deadline_state(today, dt.date(2026, 12, 14), "Awarded"), "CLOSED")
        self.assertEqual(deadline_state(today, None, "Research"), "NO DEADLINE SET")

    def test_post_award_reports_step_forward_never_land_in_the_past(self):
        today = dt.date(2026, 12, 15)
        quarterly = next_report_due(today, dt.date(2026, 1, 31), 90)
        self.assertGreaterEqual(quarterly, today)
        # four whole 90-day intervals from 31 Jan, because three still land in the past
        self.assertEqual(quarterly, dt.date(2027, 1, 26))
        annual = next_report_due(today, dt.date(2026, 1, 31), 365)
        self.assertEqual(annual, dt.date(2027, 1, 31))
        self.assertIsNone(next_report_due(today, None, 365))
        self.assertIsNone(next_report_due(today, dt.date(2026, 1, 31), 0))

    def test_the_documented_14_day_window_matches_the_two_thresholds(self):
        # Opportunities warns at 14 days, post-award reports at 30.
        wb = openpyxl.load_workbook(XLSX)
        self.assertIn("<=14", wb["Opportunities"]["S2"].value)
        self.assertIn("<=30", wb["Timeline"]["F2"].value)


class TestGuide(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = PdfReader(str(PDF))
        cls.text = "\n".join((p.extract_text() or "") for p in cls.reader.pages)

    def test_page_and_word_count_support_the_price(self):
        self.assertEqual(len(self.reader.pages), 17)
        words = len(self.text.split())
        self.assertGreaterEqual(words, 8100)
        self.assertGreaterEqual(words, 15 * 100)  # depth rule at $15.00

    def test_no_placeholders_or_encoding_damage(self):
        for bad in ("TODO", "TBD", "lorem ipsum", "[insert", "{{", "placeholder", "xxx"):
            self.assertNotIn(bad.lower(), self.text.lower(), bad)
        self.assertNotIn("\u00d9\u00a0", self.text)
        self.assertEqual(self.text.count("\ufffd"), 0)

    def test_disclaimer_and_honest_limits_are_present(self):
        flat = " ".join(self.text.split())
        self.assertIn("ORGANISING TOOL ONLY", flat)
        self.assertIn("Not legal, tax, accounting or financial advice", flat)
        self.assertIn("does not find funding opportunities", flat)


class TestPackaging(unittest.TestCase):
    def test_cover_is_a_real_listing_image(self):
        with Image.open(COVER) as img:
            self.assertEqual(img.size, (1280, 720))
            self.assertEqual(img.mode, "RGB")
            self.assertGreater(len(img.convert("RGB").getcolors(maxcolors=100000)), 100)

    def test_public_page_shows_the_gated_price_and_both_files(self):
        html = PAGE.read_text(encoding="utf-8")
        self.assertIn("$15", html)
        self.assertIn("B12-010_grant_pipeline_tracker.xlsx", html)
        self.assertIn("B12-010_grant_pipeline_guide.pdf", html)
        for claim in ("guarantee", "limited time", "act now", "24/7", "our platform"):
            self.assertNotIn(claim, html.lower(), claim)
        self.assertNotIn("$39", html)

    def test_registry_records_the_derived_price_without_claiming_authorization(self):
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
        item = next(p for p in data["products"] if p["id"] == "B12-010")
        self.assertEqual(item["price_usd"], 15.0)
        self.assertEqual(item["previous_price"], 39.0)
        self.assertEqual(len(item["files"]), 2)
        self.assertEqual(item["gate_verdict"], "APPROVED")
        self.assertIsNone(item["publication_authorization"])
        self.assertFalse(item["ready_to_publish"])
        self.assertIn("DERIVED", item["price_status"])


if __name__ == "__main__":
    unittest.main()
