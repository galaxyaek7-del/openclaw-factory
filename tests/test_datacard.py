"""Data card provenance checks (backlog B20, 2026-10-29). Temp files only."""
import copy
import csv
import os
import shutil
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from data_products import datacard as dc  # noqa: E402

TODAY = date(2026, 10, 29)


class DataCard(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.write([["a1", "Title one", "1500"], ["a2", "Title two", "900"]])

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def write(self, rows, header=("id", "title", "price_cents")):
        p = os.path.join(self.root, "d.csv")
        with open(p, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)
        self.rows = len(rows)

    def card(self, **over):
        c = {
            "dataset_id": "t", "title": "T", "version": "1", "description": "d", "intended_use": "u",
            "out_of_scope_use": "o", "collection_method": "c", "processing_steps": ["s"],
            "sources": [{"name": "own", "origin": "data/x.json", "accessed_on": "2026-10-29",
                         "licence": {"name": "own", "commercial_use": True}}],
            "columns": [{"name": "id", "type": "string", "description": "id"},
                        {"name": "title", "type": "string", "description": "t"},
                        {"name": "price_cents", "type": "integer", "description": "p"}],
            "files": [{"path": "d.csv", "sha256": dc.sha256_file(os.path.join(self.root, "d.csv")),
                       "rows": self.rows}],
            "personal_data": {"contains": False}, "licence_out": {"name": "own"},
            "refresh_days": 30, "last_refreshed": "2026-10-20", "known_limitations": ["l"],
        }
        c.update(over)
        return c

    def check(self, card):
        return dc.validate_card(card, self.root, TODAY)

    def test_valid_card_passes(self):
        r = self.check(self.card())
        self.assertEqual("PASS", r["status"], r["findings"])

    def test_missing_fields_block(self):
        c = self.card()
        del c["known_limitations"]
        c["intended_use"] = ""
        r = self.check(c)
        self.assertEqual("BLOCK", r["status"])
        self.assertIn("intended_use", r["findings"][0]["finding"])

    def test_changed_file_blocks(self):
        c = self.card()
        self.write([["a1", "Title one", "1500"], ["a2", "Title two", "901"]])
        r = self.check(c)
        self.assertEqual("BLOCK", r["status"])
        self.assertTrue(any("sha256" in f["finding"] for f in r["findings"]))

    def test_row_count_and_columns_must_match(self):
        c = self.card()
        c["files"][0]["rows"] = 3
        c["columns"] = c["columns"][:2] + [{"name": "price", "type": "integer", "description": "p"}]
        r = self.check(c)
        texts = " ".join(f["finding"] for f in r["findings"])
        self.assertIn("2 rows, card says 3", texts)
        self.assertIn("undeclared: ['price_cents']", texts)

    def test_missing_file_blocks(self):
        c = self.card(files=[{"path": "nope.csv", "sha256": "x", "rows": 1}])
        self.assertEqual("BLOCK", self.check(c)["status"])

    def test_licences(self):
        nc = self.card()
        nc["sources"][0]["licence"] = {"name": "CC BY-NC 4.0", "commercial_use": False}
        self.assertEqual("BLOCK", self.check(nc)["status"])
        none = self.card()
        none["sources"][0]["licence"] = {}
        self.assertEqual("BLOCK", self.check(none)["status"])
        sa = self.card()
        sa["sources"][0]["licence"] = {"name": "CC BY-SA 4.0", "commercial_use": True, "share_alike": True,
                                       "attribution_required": True}
        sa["attribution"] = "Contains data from X, CC BY-SA 4.0"
        self.assertEqual("REVIEW", self.check(sa)["status"])
        sa["licence_out"] = {"name": "CC BY-SA 4.0"}
        self.assertEqual("PASS", self.check(sa)["status"])
        sa["attribution"] = ""
        self.assertEqual("BLOCK", self.check(sa)["status"])

    def test_source_needs_origin_and_real_date(self):
        c = self.card()
        c["sources"][0]["origin"] = ""
        c["sources"][0]["accessed_on"] = "recently"
        self.assertEqual(2, len(self.check(c)["findings"]))

    def test_personal_data_blocks_unless_declared(self):
        self.write([["a1", "Contact jane@example.com", "1500"], ["a2", "Call +1 415 555 0134", "900"]])
        r = self.check(self.card())
        self.assertEqual("BLOCK", r["status"])
        text = " ".join(f["finding"] for f in r["findings"])
        self.assertIn("email", text)
        self.assertIn("phone", text)
        declared = self.card(personal_data={"contains": True, "lawful_basis": "consent, form v2"})
        self.assertEqual("REVIEW", self.check(declared)["status"])

    def test_ids_and_prices_are_not_phone_numbers(self):
        self.write([["1234567890123", "Plain title", "1234567890"]])
        self.assertEqual("PASS", self.check(self.card())["status"])

    def test_freshness(self):
        self.assertEqual("REVIEW", self.check(self.card(last_refreshed="2026-08-01"))["status"])
        self.assertEqual("BLOCK", self.check(self.card(last_refreshed="2026-11-30"))["status"])
        self.assertEqual("BLOCK", self.check(self.card(last_refreshed="last week"))["status"])


class CatalogRelease(unittest.TestCase):
    def test_build_from_a_fixture_catalog(self):
        root = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(root, "customer_site"))
            Path(root, "customer_site", "catalog.json").write_text(
                '{"data": {"generated_at": "2026-10-29T00:00:00Z", "products": ['
                '{"id": "P-1", "title": "A tool", "price_cents": 900, "url": "https://example.gumroad.com/l/a",'
                ' "format": "Gumroad digital download", "featured": true, "summary": "Does a thing."}]}}',
                encoding="utf-8")
            sys.path.insert(0, str(ROOT / "scripts"))
            import build_catalog_dataset as b
            card, result = b.build(root=root, release="2026-10-29")
            self.assertEqual("PASS", result["status"], result["findings"])
            self.assertEqual(1, card["files"][0]["rows"])
            self.assertTrue(os.path.exists(os.path.join(root, "data_products", "releases", "gf-public-catalog",
                                                        "2026-10-29", "validation.json")))
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
