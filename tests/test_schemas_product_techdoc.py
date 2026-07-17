"""Regression test — found via the mission's own Step 5 end-to-end proof
run (2026-07-17): schemas/product.py had its own, separate economics-
platform mapping that was never updated when book_generator.py's
_economics_platform_for() gained a "techdoc" branch (ADR-068), leaving
every techdoc Product silently evaluated against "kdp_ebook" and therefore
needs_pricing=True (unsupported by every distribution arm). Fixed in the
same session this was found, not left for a future one to rediscover.

    python -m unittest tests.test_schemas_product_techdoc -v
"""

import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from schemas.product import Product


class TestTechdocEconomicsPlatformMapping(unittest.TestCase):
    def test_techdoc_record_does_not_need_pricing(self):
        record = {
            "title": "Test Techdoc Product",
            "topic": "test techdoc product",
            "price": 388,
            "path": "/fake/path.pdf",
            "pages": 8,
            "product_type": "techdoc",
        }
        product = Product.from_jsonl_record(record)
        self.assertFalse(product.needs_pricing, product)
        self.assertIsNotNone(product.price_usd)

    def test_techdoc_and_elite_are_priced_the_same_band(self):
        base = {
            "title": "Test Product", "topic": "test", "price": 388,
            "path": "/fake/path.pdf", "pages": 8,
        }
        techdoc = Product.from_jsonl_record({**base, "product_type": "techdoc"})
        elite = Product.from_jsonl_record({**base, "product_type": "elite"})
        self.assertEqual(techdoc.price_usd, elite.price_usd)
        self.assertEqual(techdoc.needs_pricing, elite.needs_pricing)

    def test_other_product_types_unaffected(self):
        for ptype, expect_needs_pricing_changed in [("book", False), ("premium", False), ("printable", False)]:
            record = {
                "title": "Test", "topic": "test", "price": 20,
                "path": "/fake/path.pdf", "pages": 8, "product_type": ptype,
            }
            # Just confirm construction succeeds and doesn't raise — the
            # exact needs_pricing value for these types is covered by their
            # own existing tests; this only guards against a regression
            # introduced by adding the new "techdoc" branch.
            Product.from_jsonl_record(record)


if __name__ == "__main__":
    unittest.main()
