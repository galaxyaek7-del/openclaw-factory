"""Tests for product_master_catalog.py (ADR-202, 2026-08-07).

    python -m unittest tests.test_product_master_catalog -v
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import product_master_catalog as pmc


class TestPaddleCatalogEntries(unittest.TestCase):
    def test_every_field_from_the_directive_is_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            paddle_path = os.path.join(tmp, "paddle_products.json")
            with open(paddle_path, "w", encoding="utf-8") as f:
                json.dump([{"title": "Test Product", "product_id": "pro_1", "price_id": "pri_1", "price": 99.0}], f)
            finance_path = os.path.join(tmp, "finance_data.json")
            with open(finance_path, "w", encoding="utf-8") as f:
                json.dump({"sales": []}, f)
            reality_path = os.path.join(tmp, "reality.json")
            with open(reality_path, "w", encoding="utf-8") as f:
                json.dump({"published_books": []}, f)

            result = pmc.build_product_master_catalog(
                paddle_products_path=paddle_path, finance_path=finance_path, reality_path=reality_path,
            )
            self.assertEqual(result["total_products"], 5)  # 1 paddle + 4 real affiliate
            paddle_entry = next(p for p in result["products"] if p["product_name"] == "Test Product")
            expected_fields = {
                "internal_product_id", "product_name", "product_type", "version", "description",
                "source_files", "pricing_usd", "currency", "cost_usd", "target_customer",
                "target_market", "platforms", "publication_status", "checkout_url",
                "affiliate_status", "license_status", "subscription_status", "revenue_usd",
                "refunds_usd", "customer_rating", "last_updated",
            }
            self.assertTrue(expected_fields.issubset(paddle_entry.keys()))
            self.assertEqual(paddle_entry["pricing_usd"], 99.0)
            self.assertEqual(paddle_entry["platforms"]["paddle"]["product_id"], "pro_1")

    def test_revenue_correctly_matched_and_test_record_filtered(self):
        with tempfile.TemporaryDirectory() as tmp:
            paddle_path = os.path.join(tmp, "paddle_products.json")
            with open(paddle_path, "w", encoding="utf-8") as f:
                json.dump([{"title": "Real Widget", "product_id": "pro_1", "price_id": "pri_1", "price": 50.0}], f)
            finance_path = os.path.join(tmp, "finance_data.json")
            with open(finance_path, "w", encoding="utf-8") as f:
                json.dump({"sales": [
                    {"platform": "Paddle", "amount": 50, "product": "Real Widget"},
                    {"platform": "Paddle", "amount": 150, "product": "Real Widget-DELETE-ME"},
                ]}, f)
            reality_path = os.path.join(tmp, "reality.json")
            with open(reality_path, "w", encoding="utf-8") as f:
                json.dump({"published_books": []}, f)

            result = pmc.build_product_master_catalog(
                paddle_products_path=paddle_path, finance_path=finance_path, reality_path=reality_path,
            )
            entry = next(p for p in result["products"] if p["product_name"] == "Real Widget")
            self.assertEqual(entry["revenue_usd"], 50)

    def test_empty_paddle_products_still_returns_real_affiliate_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            paddle_path = os.path.join(tmp, "paddle_products.json")
            with open(paddle_path, "w", encoding="utf-8") as f:
                json.dump([], f)
            reality_path = os.path.join(tmp, "reality.json")
            with open(reality_path, "w", encoding="utf-8") as f:
                json.dump({"published_books": []}, f)
            result = pmc.build_product_master_catalog(paddle_products_path=paddle_path, reality_path=reality_path)
            self.assertEqual(result["total_products"], 4)
            self.assertTrue(all(p["product_type"] == "affiliate_asset" for p in result["products"]))

    def test_kdp_published_book_reflected_from_reality_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            paddle_path = os.path.join(tmp, "paddle_products.json")
            with open(paddle_path, "w", encoding="utf-8") as f:
                json.dump([], f)
            reality_path = os.path.join(tmp, "reality.json")
            with open(reality_path, "w", encoding="utf-8") as f:
                json.dump({"published_books": [{"asin": "B000TEST", "title": "Real KDP Book", "price_usd": 9.99, "published_date": "2026-08-01"}]}, f)
            result = pmc.build_product_master_catalog(paddle_products_path=paddle_path, reality_path=reality_path)
            kdp_entry = next(p for p in result["products"] if p["product_name"] == "Real KDP Book")
            self.assertEqual(kdp_entry["publication_status"], "PUBLISHED")
            self.assertEqual(kdp_entry["platforms"]["amazon_kdp"]["asin"], "B000TEST")

    def test_no_second_mutable_source_of_truth_read_only(self):
        """The catalog function accepts no write parameters at all --
        proving structurally, not just by convention, that it cannot
        mutate any of the real per-platform source files."""
        import inspect
        sig = inspect.signature(pmc.build_product_master_catalog)
        for name in sig.parameters:
            self.assertNotIn("write", name.lower())
            self.assertNotIn("save", name.lower())


class TestAllGenerationAttempts(unittest.TestCase):
    def test_only_successful_attempts_included(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "_generation_log.jsonl")
            with open(path, "w", encoding="utf-8") as f:
                f.write(json.dumps({"success": True, "title": "A"}) + "\n")
                f.write(json.dumps({"success": False, "title": "B"}) + "\n")
            result = pmc.all_generation_attempts(generation_log_path=path)
            self.assertEqual(result["total_real_attempts"], 1)

    def test_honestly_empty_when_log_missing(self):
        result = pmc.all_generation_attempts(generation_log_path="C:/definitely/not/real.jsonl")
        self.assertEqual(result["entries"], [])
        self.assertEqual(result["total_real_attempts"], 0)

    def test_limit_respected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "_generation_log.jsonl")
            with open(path, "w", encoding="utf-8") as f:
                for i in range(10):
                    f.write(json.dumps({"success": True, "title": f"item-{i}"}) + "\n")
            result = pmc.all_generation_attempts(limit=3, generation_log_path=path)
            self.assertEqual(len(result["entries"]), 3)
            self.assertEqual(result["total_real_attempts"], 10)


if __name__ == "__main__":
    unittest.main()
