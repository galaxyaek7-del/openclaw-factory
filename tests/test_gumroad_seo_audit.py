"""scripts/gumroad_seo_audit.py: scoring on the fields Gumroad really returns.

Offline: synthetic product dicts shaped like the API response. No network.
"""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("gumroad_seo_audit", ROOT / "scripts" / "gumroad_seo_audit.py")
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)

GOOD = {"id": "1", "name": "Etsy Suspension Appeal Kit for Sellers", "published": True,
        "description": "<p>" + "Real, specific description text. " * 20 + "</p>",
        "tags": ["etsy", "appeal", "seller", "suspension", "policy"], "price": 2900,
        "covers": [{"url": "https://public-files.gumroad.com/x"}], "taxonomy_id": "123"}


class TestGumroadSeoAudit(unittest.TestCase):
    def test_complete_listing_scores_100(self):
        r = A.audit_product_seo(GOOD)
        self.assertEqual((r["seo_score"], r["issues"], r["priority"]), (100, [], "LOW"))
        self.assertEqual(r["price_usd"], 29.0)                      # cents -> dollars

    def test_price_is_read_in_cents(self):
        cheap = A.audit_product_seo(dict(GOOD, price=300))           # $3
        self.assertIn("Price very low (<$5)", cheap["issues"])
        fine = A.audit_product_seo(dict(GOOD, price=500))            # $5, not "very low"
        self.assertNotIn("Price very low (<$5)", fine["issues"])
        self.assertIn("Free product - no revenue", A.audit_product_seo(dict(GOOD, price=0))["issues"])

    def test_missing_cover_tags_and_short_text_are_penalised(self):
        bare = dict(GOOD, covers=[], tags=["a", "b"], description="<p>Short.</p>", name="Kit")
        r = A.audit_product_seo(bare)
        self.assertIn("No cover image", r["issues"])
        self.assertIn("Only 2 tags (need 5+)", r["issues"])
        self.assertIn("Title too short (<20 chars)", r["issues"])
        self.assertEqual(r["seo_score"], 100 - 15 - 20 - 15 - 20)
        self.assertEqual(r["priority"], "HIGH")
        self.assertTrue(A.audit_product_seo(dict(GOOD, covers=[], preview_url="https://x"))["has_cover"])

    def test_fields_the_api_did_not_return_are_unknown_not_empty(self):
        p = {k: v for k, v in GOOD.items() if k not in ("tags", "taxonomy_id")}
        r = A.audit_product_seo(p)
        self.assertIsNone(r["tags"])
        self.assertEqual(r["seo_score"], 100)

    def test_report_summarises_published_listings_only(self):
        rep = A.run([GOOD, dict(GOOD, id="2", published=False, covers=[]), dict(GOOD, id="3", deleted=True)])
        self.assertEqual((rep["products"], rep["published"]), (2, 1))
        self.assertEqual(rep["average_score_published"], 100.0)


if __name__ == "__main__":
    unittest.main()
