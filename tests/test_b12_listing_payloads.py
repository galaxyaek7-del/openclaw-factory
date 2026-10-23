# -*- coding: utf-8 -*-
"""Tests for scripts/build_b12_listing_payloads.py (Cycle 104).

Offline and local: the builder itself makes no network call, so the tests focus
on the properties that would let it mislead a future reader -- a missing file
quietly listed as present, a copy file that is never parsed, a price that
disagrees with the registry, and the hard rule that this module must contain no
publish path at all.

    python -m unittest tests.test_b12_listing_payloads -v
"""

import json
import re
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "scripts"))

import build_b12_listing_payloads as bp  # noqa: E402
import sys as _gf_sys  # noqa: E402
_gf_sys.path.insert(0, str(Path(__file__).resolve().parent))
from paid_artifacts import paid_files_absent, require_paid_files  # noqa: E402


class TestCopyParsing(unittest.TestCase):
    def test_parses_the_real_section_shape(self):
        sample = (
            "B12-00X COPY-PASTE LISTING\n"
            "============================================================\n"
            "TITLE:\n"
            "Some Product\n\n"
            "PRICE:\n"
            "$12.00 USD one-time\n\n"
            "DESCRIPTION:\n"
            "First line.\n\nSecond paragraph.\n\n"
            "TAGS:\n"
            "alpha, beta\n\n"
            "FILES TO UPLOAD:\n"
            "books/batch12/thing.xlsx\n"
            "============================================================\n")
        sec = bp.parse_copy(sample)
        self.assertEqual(sec["title"], "Some Product")
        self.assertIn("$12.00", sec["price"])
        self.assertIn("Second paragraph.", sec["description"])
        self.assertEqual(sec["tags"].replace("\n", ","),
                         sec["tags"])  # single line preserved
        self.assertIn("thing.xlsx", sec["files_to_upload"])

    def test_a_status_header_is_not_mistaken_for_a_section(self):
        sec = bp.parse_copy("STATUS: READY FOR AUTHORIZATION\nTITLE:\nX\n")
        self.assertIn("title", sec)
        self.assertNotIn("status", sec)


class TestRegistryAgreement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        reg = json.loads(bp.REGISTRY.read_text(encoding="utf-8-sig"))
        cls.items = {it["id"]: it for it in reg["items"]}

    def test_every_configured_product_is_in_the_registry(self):
        for pid in bp.PRODUCTS:
            self.assertIn(pid, self.items)

    def test_every_copy_file_and_gate_and_cover_exists(self):
        for pid, spec in bp.PRODUCTS.items():
            for key in ("copy", "gate", "cover", "page"):
                self.assertTrue((_ROOT / spec[key]).exists(),
                                "%s: %s missing (%s)" % (pid, key, spec[key]))

    def test_every_declared_deliverable_exists(self):
        require_paid_files(*[_ROOT / "books" / "batch12" / rel for pid, it in self.items.items()
                             if pid in bp.PRODUCTS for rel in it.get("files") or []])
        for pid, item in self.items.items():
            if pid not in bp.PRODUCTS:
                continue
            for rel in item.get("files") or []:
                self.assertTrue((_ROOT / "books" / "batch12" / rel).exists(),
                                "%s declares a missing deliverable: %s" % (pid, rel))

    def test_authorization_phrase_names_the_product_and_price(self):
        for pid, item in bp.PRODUCTS.items():
            price = self.items[pid].get("proposed_price_usd")
            phrase = bp.AUTHORIZATION_TEMPLATE.format(
                id=pid, title=self.items[pid]["title"], price="%.2f" % price)
            self.assertIn(pid, phrase)
            self.assertIn("%.2f" % price, phrase)

    def test_prices_are_not_derived_by_this_module(self):
        # The builder must cite the registry price, never invent one.
        src = (_ROOT / "scripts" / "build_b12_listing_payloads.py").read_text(
            encoding="utf-8")
        self.assertIn('item.get("proposed_price_usd")', src)
        self.assertIsNone(re.search(r"price_usd\s*=\s*\d", src))


class TestNoPublishPath(unittest.TestCase):
    def test_source_contains_no_publish_or_gumroad_write(self):
        src = (_ROOT / "scripts" / "build_b12_listing_payloads.py").read_text(
            encoding="utf-8")
        for banned in ("create_product", "update_product", "enable_product",
                       "gumroad_publisher", "write_gate", "requests",
                       "distribute"):
            self.assertNotIn(banned, src, "builder must not reference %s" % banned)

    def test_output_is_flagged_unpublished(self):
        src = (_ROOT / "scripts" / "build_b12_listing_payloads.py").read_text(
            encoding="utf-8")
        self.assertIn('"published": False', src)
        self.assertIn("IT NEVER PUBLISHES", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
