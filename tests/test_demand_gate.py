import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import demand_gate as dg  # noqa: E402


def _write(root, rel, text):
    p = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)


def _jsonl(rows):
    return "\n".join(json.dumps(r) for r in rows) + "\n"


class DemandGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = self.tmp.name

    def ev(self, env=None):
        # external clicks read the repo's own ledger path via the package; keep the temp root pure
        from unittest import mock
        with mock.patch.object(dg, "external_click_signal", return_value=0):
            return dg.evaluate(root=self.root, environ=env or {})

    def test_empty_factory_is_closed_and_says_waiting(self):
        r = self.ev()
        self.assertFalse(r["open"])
        self.assertEqual(0, r["daily_cap"])
        self.assertIn("WAITING FOR REAL DATA", r["why"])

    def test_a_published_sale_opens_it(self):
        _write(self.root, "data/product_registry.json",
               json.dumps({"products": [{"published": True, "sales_count": 1}, {"published": True, "sales_count": 0}]}))
        r = self.ev()
        self.assertTrue(r["open"])
        self.assertEqual(1, r["signals"]["SALE"])
        self.assertEqual(dg.DEFAULT_DAILY_CAP, r["daily_cap"])

    def test_a_polled_sale_in_finance_data_opens_it_without_waiting_for_the_daily_registry(self):
        _write(self.root, "finance_data.json", json.dumps({"sales": [{"amount": 15, "platform": "gumroad"}]}))
        r = self.ev()
        self.assertTrue(r["open"])
        self.assertEqual(1, r["signals"]["SALE"])

    def test_test_sales_in_finance_data_never_count(self):
        _write(self.root, "finance_data.json", json.dumps({"sales": [
            {"amount": 1, "environment": "TEST"}, {"amount": 2, "simulation": True}, {"amount": 3, "note": "synthetic probe"}]}))
        self.assertFalse(self.ev()["open"])

    def test_sales_on_unpublished_rows_do_not_count(self):
        _write(self.root, "data/product_registry.json", json.dumps({"products": [{"published": False, "sales_count": 5}]}))
        self.assertFalse(self.ev()["open"])

    def test_test_rows_and_example_addresses_never_open_it(self):
        _write(self.root, "data/customer_interest.jsonl", _jsonl([
            {"email": "nobody@t.com", "message": "hi"},
            {"email": "real@gmail.com", "message": "TEST_EVENT timing check"},
            {"email": "", "message": "no address"},
        ]))
        self.assertFalse(self.ev()["open"])

    def test_a_real_interest_row_opens_it(self):
        _write(self.root, "data/customer_interest.jsonl", _jsonl([{"email": "owner@agence.dz", "message": "je veux un devis"}]))
        r = self.ev()
        self.assertTrue(r["open"])
        self.assertEqual(1, r["signals"]["BUYER_INTEREST"])

    def test_research_and_competitor_rows_are_not_demand(self):
        _write(self.root, "data/market_evidence.jsonl", _jsonl([
            {"event_type": "complaining_review", "niche": "x"},
            {"event_type": "freelancer_agency_pricing", "niche": "x"},
            {"event_type": "competitor_pricing_change", "niche": "x"},
        ]))
        self.assertFalse(self.ev()["open"])

    def test_a_buyer_side_market_row_opens_it_unless_it_is_a_test(self):
        _write(self.root, "data/market_evidence.jsonl", _jsonl([
            {"event_type": "demo_request", "payload": {"who": "TEST_EVENT"}},
        ]))
        self.assertFalse(self.ev()["open"])
        _write(self.root, "data/market_evidence.jsonl", _jsonl([
            {"event_type": "demo_request", "payload": {"who": "real agency"}},
        ]))
        self.assertTrue(self.ev()["open"])

    def test_daily_cap_comes_from_env_and_bad_values_fall_back(self):
        _write(self.root, "data/product_registry.json", json.dumps({"products": [{"published": True, "sales_count": 2}]}))
        self.assertEqual(7, self.ev({"GF_DEMAND_GATE_DAILY_CAP": "7"})["daily_cap"])
        self.assertEqual(dg.DEFAULT_DAILY_CAP, self.ev({"GF_DEMAND_GATE_DAILY_CAP": "abc"})["daily_cap"])
        self.assertEqual(0, self.ev({"GF_DEMAND_GATE_DAILY_CAP": "0"})["daily_cap"])


if __name__ == "__main__":
    unittest.main()
