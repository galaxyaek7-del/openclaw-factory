"""GF-19: static affiliate catalog must be valid, honest, and Pages-safe.

unittest.TestCase style (no pytest import): CI runs unittest discovery in an
environment without pytest installed (see requirements.txt discipline), so a
top-level `import pytest` here breaks the whole group. These tests run under
both unittest and pytest.
"""
import json
import math
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from affiliate_commerce.static_catalog import StaticCatalogError, build_static_catalog


class TestStaticCatalog(unittest.TestCase):
    def test_schema_and_ranking(self):
        c = build_static_catalog()
        self.assertEqual(c["category"], "standing_desk_converters")
        self.assertEqual(c["count"], len(c["products"]))
        self.assertEqual(len(c["products"]), 4)
        for p in c["products"]:
            for f in ("id", "name", "description", "price_usd", "rating",
                      "rating_count", "url", "affiliate_attributed"):
                self.assertIn(f, p, f)
            self.assertTrue(p["url"].startswith("https://www.amazon.com/dp/"))
            self.assertIsInstance(p["price_usd"], (int, float))
        scores = [p["rating"] * math.log10(p["rating_count"] + 1) for p in c["products"]]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_no_tag_invented_while_unset(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AMAZON_ASSOCIATE_TAG", None)
            c = build_static_catalog()
        self.assertFalse(c["tag_configured"])
        for p in c["products"]:
            self.assertNotIn("tag=", p["url"])
            self.assertFalse(p["affiliate_attributed"])

    def test_empty_category_yields_empty_not_error(self):
        c = build_static_catalog(category="no_such_category")
        self.assertEqual(c["products"], [])
        self.assertEqual(c["count"], 0)

    def test_malformed_product_raises(self):
        import affiliate_commerce.products as prod
        bad = {"id": "X", "name": "Bad", "category": "standing_desk_converters"}
        with patch.object(prod, "PRODUCTS", [bad]):
            with self.assertRaises(StaticCatalogError):
                build_static_catalog()

    def test_page_contract_fields_present(self):
        c = build_static_catalog()
        self.assertTrue(c["ranking_method"] and c["source"] and c["verified_at"])
        for p in c["products"]:
            self.assertTrue(isinstance(p["list_price_usd"], (int, float))
                            or p["list_price_usd"] is None)

    def test_page_has_no_server_product_dependency(self):
        text = (ROOT / "customer_site" / "affiliate-standing-desks.html").read_text(encoding="utf-8")
        self.assertNotIn("fetch('/api/affiliate", text)
        self.assertNotIn('fetch("/api/affiliate', text)
        self.assertNotIn("'/api/affiliate/click/' +", text)
        self.assertIn("affiliate-products.json", text)


if __name__ == "__main__":
    unittest.main()
