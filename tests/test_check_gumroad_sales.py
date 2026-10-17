"""scripts/check_gumroad_sales.py: read-only, every page counted. No network."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("check_gumroad_sales", ROOT / "scripts" / "check_gumroad_sales.py")
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)


class TestCheckGumroadSales(unittest.TestCase):
    def test_follows_every_page_and_counts_refunds_separately(self):
        pages = {
            C.API: {"success": True, "sales": [{"price": 1499, "product_name": "A"}],
                    "next_page_url": "/v2/sales?page_key=p2"},
            "https://api.gumroad.com/v2/sales?page_key=p2": {
                "success": True, "sales": [{"price": 2900, "product_name": "B", "refunded": True}]},
        }
        seen = []
        r = C.fetch_sales("tok", get=lambda u, t: (seen.append(u), pages[u])[1])
        self.assertEqual((r["pages"], r["complete"], len(seen)), (2, True, 2))
        s = C.summarize(r)
        self.assertEqual((s["count"], s["paid_count"], s["refunded_count"], s["gross_usd"]), (2, 1, 1, 14.99))

    def test_a_failed_page_is_reported_not_counted(self):
        r = C.fetch_sales("tok", get=lambda u, t: {"success": False, "message": "bad token"})
        self.assertFalse(r["success"])
        self.assertNotIn("sales", r)


if __name__ == "__main__":
    unittest.main()
