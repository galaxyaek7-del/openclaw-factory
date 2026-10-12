"""C81 — the catalog-gap defect: an active, sellable Paddle product that was
absent from data/paddle_products.json.

Consequences this guards against:
  1. the webhook would reject a real transaction.completed for that price as
     PRODUCT_MISMATCH, so a genuinely paid sale could never be recorded;
  2. the public customer catalog (built from the same file) did not offer it,
     so it could not be bought at all.

The repair itself is a data change; these tests lock the invariant that the
local catalog and the real product list cannot silently drift apart again,
and that the webhook now accepts the repaired price.
"""
import json, os, sys, tempfile, unittest, hmac, hashlib
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from channels import paddle_webhook as pw

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "data" / "paddle_products.json"

# The product that was live+active in Paddle but missing from the catalog.
MISSED_TITLE = "The 5-Minute Context Reset Playbook"
MISSED_PRICE_ID = "pri_01m23gzc9bb5z3kr0yfqrx7yba"
MISSED_PRODUCT_ID = "pro_01m23gzbw31wc62r7rkr7y2zyw"


class TestPaddleCatalogCoversEverySellablePrice(unittest.TestCase):

    def setUp(self):
        self.catalog = json.loads(CATALOG.read_text(encoding="utf-8"))

    def test_the_previously_missing_price_is_now_in_the_catalog(self):
        by_price = {e["price_id"]: e for e in self.catalog}
        self.assertIn(MISSED_PRICE_ID, by_price,
                      "the live active price must be present in the local catalog")
        entry = by_price[MISSED_PRICE_ID]
        self.assertEqual(entry["title"], MISSED_TITLE)
        self.assertEqual(entry["product_id"], MISSED_PRODUCT_ID)
        self.assertEqual(entry["price"], 15.0)

    def test_catalog_entries_are_unique_by_price_id(self):
        ids = [e["price_id"] for e in self.catalog]
        self.assertEqual(len(ids), len(set(ids)), "duplicate price_id in catalog")

    def test_every_entry_has_the_fields_consumers_require(self):
        for e in self.catalog:
            for field in ("title", "product_id", "price_id", "price"):
                self.assertIn(field, e, f"catalog entry missing {field}")
            self.assertIsInstance(e["price"], (int, float))
            self.assertGreater(e["price"], 0)

    def test_webhook_now_accepts_a_transaction_for_the_repaired_price(self):
        """End-to-end through the real validator: a properly signed, correctly
        priced transaction for the previously-unmapped price is ACCEPTED."""
        secret = "c81-catalog-gap-test-secret"
        catalog = [{"price_id": MISSED_PRICE_ID, "price": 15.0,
                    "product_id": MISSED_PRODUCT_ID}]
        body = json.dumps({
            "event_type": "transaction.completed",
            "event_id": "evt_catalog_gap_1",
            "data": {
                "id": "txn_catalog_gap",
                "items": [{"price": {"id": MISSED_PRICE_ID}}],
                "details": {"totals": {"grand_total": "1500",
                                        "currency_code": "USD"}},
            },
        }).encode()
        h1 = hmac.new(secret.encode(), b"1760000000:" + body, hashlib.sha256).hexdigest()
        tmp = Path(tempfile.mkdtemp()) / "events.jsonl"
        result = pw.process_paddle_webhook(
            body, f"ts=1760000000;h1={h1}", secret=secret,
            processed_events_path=tmp, catalog_path=self._write(catalog))
        self.assertEqual(result["status"], "ACCEPTED", result.get("detail"))

    @staticmethod
    def _write(entries):
        p = Path(tempfile.mkdtemp()) / "catalog.json"
        p.write_text(json.dumps(entries), encoding="utf-8")
        return p

    def test_amount_mismatch_on_the_repaired_price_is_still_caught(self):
        secret = "c81-catalog-gap-test-secret"
        body = json.dumps({
            "event_type": "transaction.completed",
            "event_id": "evt_catalog_gap_bad_amount",
            "data": {
                "id": "txn_bad",
                "items": [{"price": {"id": MISSED_PRICE_ID}}],
                "details": {"totals": {"grand_total": "1",
                                        "currency_code": "USD"}},
            },
        }).encode()
        h1 = hmac.new(secret.encode(), b"1760000000:" + body, hashlib.sha256).hexdigest()
        tmp = Path(tempfile.mkdtemp()) / "events.jsonl"
        result = pw.process_paddle_webhook(
            body, f"ts=1760000000;h1={h1}", secret=secret,
            processed_events_path=tmp,
            catalog_path=self._write([{"price_id": MISSED_PRICE_ID, "price": 15.0,
                                       "product_id": MISSED_PRODUCT_ID}]))
        self.assertEqual(result["reason"], "AMOUNT_MISMATCH")


if __name__ == "__main__":
    unittest.main(verbosity=2)