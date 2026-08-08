"""Phase 30.5.1 cleanup, ADR-222: negative-case tests proving the
finance_data.json smoke-test record removal is correct, complete, and
does not silently convert simulation data into production data."""

import json
import os
import unittest

import institutional_truth_dashboard as itd

_FACTORY_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FINANCE_PATH = os.path.join(_FACTORY_ROOT, "finance_data.json")


class TestFinanceDataHasNoSyntheticRecord(unittest.TestCase):
    def _load(self):
        with open(_FINANCE_PATH, encoding="utf-8") as f:
            return json.load(f)

    def test_no_delete_me_or_smoke_test_records(self):
        data = self._load()
        for sale in data.get("sales", []):
            self.assertNotIn("DELETE-ME", str(sale.get("product", "")))

    def test_zero_revenue_is_represented_correctly(self):
        data = self._load()
        self.assertEqual(data.get("totalSales", None), 0)
        self.assertEqual(data.get("totalPaddle", None), 0)

    def test_zero_orders_is_represented_correctly(self):
        data = self._load()
        self.assertEqual(data.get("sales", None), [])

    def test_by_ladder_rollup_is_all_zero(self):
        data = self._load()
        for rank, total in data.get("byLadder", {}).items():
            self.assertEqual(total, 0, f"byLadder[{rank}] is not zero")

    def test_deleting_the_record_did_not_break_the_file_shape(self):
        # Every key financeDefault()/loadFin() expect must still be present.
        data = self._load()
        for key in ("sales", "totalKDP", "totalEtsy", "totalGumroad", "totalPaddle", "totalSales", "byLadder"):
            self.assertIn(key, data)


class TestDashboardsDoNotManufactureRevenue(unittest.TestCase):
    def test_real_revenue_state_reports_zero(self):
        state = itd._real_revenue_state()
        self.assertEqual(state["real_revenue_usd"], 0)
        self.assertEqual(state["smoke_test_records_included_in_raw_total"], 0)
        self.assertEqual(state["finance_data_raw_total_usd"], 0)

    def test_executive_truth_dashboard_reports_zero_real_revenue_and_orders(self):
        result = itd.build_executive_truth_dashboard()
        self.assertEqual(result["commercial_reality"]["real_revenue_usd"], 0)
        self.assertEqual(result["commercial_reality"]["real_orders"], 0)
        self.assertEqual(result["real_customers"], 0)


class TestSimulationNeverConvertsToProduction(unittest.TestCase):
    def test_simulation_events_never_write_to_finance_data_json(self):
        import tempfile
        import commercial_simulation_lab as csl

        before = os.path.getmtime(_FINANCE_PATH)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "events.jsonl")
            csl.record_simulation_event(product="P", customer="C", price=999, ledger_path=path)
        after = os.path.getmtime(_FINANCE_PATH)
        self.assertEqual(before, after, "finance_data.json was touched by a simulation write")

    def test_simulation_event_is_never_read_back_as_real_revenue(self):
        import tempfile
        import commercial_simulation_lab as csl

        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "events.jsonl")
            csl.record_simulation_event(product="P", customer="C", price=999, ledger_path=path)
        # Real revenue state must be computed only from finance_data.json,
        # never from any simulation ledger.
        state = itd._real_revenue_state()
        self.assertEqual(state["real_revenue_usd"], 0)


if __name__ == "__main__":
    unittest.main()
