"""G2 — product_type → platform centralization tests."""
import unittest

class TestG2CentralMappingExists(unittest.TestCase):
    def test_authoritative_mapping_exists(self):
        import economics
        # ADR-065: the one canonical table is book_generator._economics_platform_for();
        # economics.platform_for_product_type() is the central entry point and delegates to it
        # (no second copy). The old PLATFORM_FOR_PRODUCT_TYPE dict no longer exists by design.
        self.assertTrue(callable(getattr(economics, 'platform_for_product_type', None)))
        self.assertFalse(hasattr(economics, 'PLATFORM_FOR_PRODUCT_TYPE'))
        import pathlib
        self.assertIn("from book_generator import _economics_platform_for",
                      pathlib.Path("economics.py").read_text(encoding="utf-8"))

    def test_all_supported_combinations_unchanged(self):
        import economics
        cases = {
            "elite": "gumroad_elite",
            "techdoc": "gumroad_elite",
            "premium": "gumroad_premium",
            "printable": "gumroad_digital",
            "book": "kdp_ebook",
            None: "kdp_ebook",
            "": "kdp_ebook",
            "unknown_xyz": "kdp_ebook",
        }
        for inp, expected in cases.items():
            with self.subTest(product_type=inp):
                self.assertEqual(economics.platform_for_product_type(inp), expected)

class TestG2MigratedCallers(unittest.TestCase):
    def test_book_generator_uses_central(self):
        import pathlib, inspect
        # book_generator owns the canonical table (ADR-065); callers inside it use that function
        func_src = inspect.getsource(__import__("book_generator")._economics_platform_for)
        for platform in ("gumroad_elite", "gumroad_premium", "gumroad_digital", "kdp_ebook"):
            self.assertIn(platform, func_src)
        self.assertIn("_economics_platform_for(", pathlib.Path("book_generator.py").read_text(encoding="utf-8"))

    def test_schemas_product_uses_central(self):
        import pathlib
        # schemas/product.py keeps its own copy of the mapping (it must stay import-light), so the
        # guard against drift is a parity check: for every product type the platform it evaluates
        # against must equal the canonical one.
        from unittest import mock
        import economics
        import schemas.product as sp
        from book_generator import _economics_platform_for
        seen = {}

        def fake_evaluate(price, platform, config, page_count=None):
            seen["platform"] = platform
            return {"approved": False}

        with mock.patch.object(economics, "evaluate", fake_evaluate):
            for pt in ("elite", "techdoc", "premium", "printable", "book"):
                seen.clear()
                sp.Product.from_jsonl_record({"product_type": pt, "price": 10, "title": "t"})
                self.assertEqual(seen.get("platform"), _economics_platform_for(pt), pt)

    def test_previous_drift_eliminated(self):
        # techdoc must route to gumroad_elite via central — previously drifted to kdp_ebook in schemas/product
        import economics
        from book_generator import _economics_platform_for
        self.assertEqual(_economics_platform_for("techdoc"), "gumroad_elite")
        self.assertEqual(economics.platform_for_product_type("techdoc"), "gumroad_elite")
        # Simulate old bug: schemas/product previously would have returned kdp_ebook for techdoc
        # Now it must match book_generator
        import schemas.product as sp
        # Test via the helper directly — both should agree
        self.assertEqual(economics.platform_for_product_type("techdoc"), _economics_platform_for("techdoc"))

    def test_invalid_unknown_fail_safely(self):
        import economics
        # Unknown product_type must fail-closed to kdp_ebook (legacy), not crash
        self.assertEqual(economics.platform_for_product_type("bogus"), "kdp_ebook")
        self.assertEqual(economics.platform_for_product_type(""), "kdp_ebook")
        self.assertEqual(economics.platform_for_product_type(None), "kdp_ebook")

class TestG2NoRegression(unittest.TestCase):
    def test_d6_still_verified(self):
        import pathlib
        self.assertIn("abs(rate - t) < 1e-9", pathlib.Path("economics.py").read_text(encoding="utf-8"))

    def test_d8_still_verified(self):
        import pathlib
        self.assertIn('platform="gumroad_digital"', pathlib.Path("profit_oracle.py").read_text(encoding="utf-8"))

    def test_d10_still_verified(self):
        import pathlib
        self.assertIn("astimezone(timezone.utc)", pathlib.Path("profit_oracle.py").read_text(encoding="utf-8"))

    def test_economics_evaluate_still_works(self):
        import economics, json
        cfg = json.load(open('config/economics.json', encoding='utf-8'))
        for pt, expected_platform in [("book","kdp_ebook"),("printable","gumroad_digital"),("premium","gumroad_premium"),("elite","gumroad_elite"),("techdoc","gumroad_elite")]:
            plat = economics.platform_for_product_type(pt)
            self.assertEqual(plat, expected_platform)
            # Evaluate with that platform must not crash
            result = economics.evaluate(50, plat, cfg, page_count=50)
            self.assertIn("approved", result)
