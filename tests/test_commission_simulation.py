import json
import os
import tempfile
import unittest
from unittest.mock import patch

import commission_ledger as cl
import commission_simulation as cs


class TestFullVoyageSimulation(unittest.TestCase):
    def test_generates_the_directive_specified_counts(self):
        with tempfile.TemporaryDirectory() as d:
            ledger_path = os.path.join(d, "ledger.jsonl")
            result = cs.run_full_commercial_voyage_simulation(ledger_path=ledger_path)
        self.assertEqual(result["partners"], 10)
        self.assertEqual(result["customers"], 50)
        self.assertEqual(result["leads"], 100)
        self.assertEqual(result["qualified_leads"], 20)
        self.assertEqual(result["outreach_responses"], 10)
        self.assertEqual(result["referrals"], 5)
        self.assertEqual(result["deals"], 3)

    def test_every_generated_record_is_tagged_simulation_only(self):
        partners = cs.generate_synthetic_partners(3)
        customers = cs.generate_synthetic_customers(3)
        leads = cs.generate_synthetic_leads(3, customers=customers)
        for record in partners + customers + leads:
            self.assertTrue(record["SIMULATION_ONLY"])

    def test_deals_only_ever_write_simulation_environment(self):
        with tempfile.TemporaryDirectory() as d:
            ledger_path = os.path.join(d, "ledger.jsonl")
            partners = cs.generate_synthetic_partners(3)
            referrals = [{"lead_id": f"L{i}"} for i in range(3)]
            cs.simulate_deals(referrals, partners, n=3, ledger_path=ledger_path)
            records = cl.load_ledger(ledger_path=ledger_path)
            for r in records:
                self.assertEqual(r["environment"], "SIMULATION")

    def test_real_finance_data_untouched_by_simulation(self):
        finance_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "finance_data.json")
        before = os.path.getmtime(finance_path)
        with tempfile.TemporaryDirectory() as d:
            ledger_path = os.path.join(d, "ledger.jsonl")
            cs.run_full_commercial_voyage_simulation(ledger_path=ledger_path)
        after = os.path.getmtime(finance_path)
        self.assertEqual(before, after)

    def test_real_commission_ledger_untouched_by_simulation(self):
        real_summary_before = cl.real_commission_summary()
        with tempfile.TemporaryDirectory() as d:
            ledger_path = os.path.join(d, "ledger.jsonl")
            cs.run_full_commercial_voyage_simulation(ledger_path=ledger_path)
        real_summary_after = cl.real_commission_summary()
        self.assertEqual(real_summary_before["real_commission_records"], real_summary_after["real_commission_records"])

    def test_never_calls_real_sales_ledger(self):
        from channels import ledger as sales_ledger
        with patch.object(sales_ledger, "append_event") as mock_append:
            with tempfile.TemporaryDirectory() as d:
                ledger_path = os.path.join(d, "ledger.jsonl")
                cs.run_full_commercial_voyage_simulation(ledger_path=ledger_path)
            mock_append.assert_not_called()


class TestFailureScenarios(unittest.TestCase):
    def test_all_scenarios_handled_safely(self):
        with tempfile.TemporaryDirectory() as d:
            ledger_path = os.path.join(d, "ledger.jsonl")
            result = cs.simulate_failure_scenarios(ledger_path=ledger_path)
        for scenario, data in result["scenarios"].items():
            self.assertTrue(data["handled"], f"{scenario} was not handled safely")

    def test_refund_status_is_real_refunded_not_invented(self):
        with tempfile.TemporaryDirectory() as d:
            ledger_path = os.path.join(d, "ledger.jsonl")
            result = cs.simulate_failure_scenarios(ledger_path=ledger_path)
        self.assertEqual(result["scenarios"]["refund"]["status"], "REFUNDED")

    def test_duplicate_event_actually_reaches_duplicate_detection(self):
        with tempfile.TemporaryDirectory() as d:
            ledger_path = os.path.join(d, "ledger.jsonl")
            result = cs.simulate_failure_scenarios(ledger_path=ledger_path)
        dup = result["scenarios"]["duplicate_event"]
        self.assertEqual(dup["first_status"], "ACCEPTED")
        self.assertEqual(dup["second_reason"], "DUPLICATE_EVENT")

    def test_ai_failure_falls_back_to_template_never_fabricates(self):
        with tempfile.TemporaryDirectory() as d:
            ledger_path = os.path.join(d, "ledger.jsonl")
            result = cs.simulate_failure_scenarios(ledger_path=ledger_path)
        self.assertTrue(result["scenarios"]["ai_failure_fallback"]["used_template_fallback"])

    def test_never_writes_to_real_default_paddle_webhook_ledger(self):
        real_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "paddle_webhook_events.jsonl")
        existed_before = os.path.exists(real_path)
        with tempfile.TemporaryDirectory() as d:
            ledger_path = os.path.join(d, "ledger.jsonl")
            cs.simulate_failure_scenarios(ledger_path=ledger_path)
        self.assertEqual(os.path.exists(real_path), existed_before)

    def test_never_writes_to_real_default_pipeline_events(self):
        real_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "commission_pipeline_events.jsonl")
        existed_before = os.path.exists(real_path)
        with tempfile.TemporaryDirectory() as d:
            ledger_path = os.path.join(d, "ledger.jsonl")
            cs.simulate_failure_scenarios(ledger_path=ledger_path)
        self.assertEqual(os.path.exists(real_path), existed_before)

    def test_never_writes_to_real_default_outreach_log(self):
        # Phase 34 regression: the ai_failure_fallback scenario originally
        # called draft_outreach_message() without an isolated log_path,
        # silently polluting data/outreach_log.jsonl on every test run.
        real_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "outreach_log.jsonl")
        existed_before = os.path.exists(real_path)
        with tempfile.TemporaryDirectory() as d:
            ledger_path = os.path.join(d, "ledger.jsonl")
            cs.simulate_failure_scenarios(ledger_path=ledger_path)
        self.assertEqual(os.path.exists(real_path), existed_before)


class TestOutreachSimulation(unittest.TestCase):
    def test_matches_section_8_named_counts(self):
        result = cs.run_outreach_simulation()
        self.assertEqual(result["prospects"], 20)
        self.assertEqual(result["qualified"], 10)
        self.assertEqual(result["messages"], 5)
        self.assertEqual(result["responses"], 3)
        self.assertEqual(result["follow_ups"], 2)

    def test_failed_send_is_honest_never_fabricated_sent(self):
        result = cs.run_outreach_simulation()
        self.assertEqual(result["failed_send_state"], "BLOCKED_NO_CREDENTIAL")
        self.assertNotEqual(result["failed_send_state"], "SENT")

    def test_never_writes_to_real_default_outreach_log(self):
        real_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "outreach_log.jsonl")
        existed_before = os.path.exists(real_path)
        cs.run_outreach_simulation()
        self.assertEqual(os.path.exists(real_path), existed_before)

    def test_never_writes_to_real_default_prospect_events(self):
        real_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "prospect_pipeline_events.jsonl")
        existed_before = os.path.exists(real_path)
        cs.run_outreach_simulation()
        self.assertEqual(os.path.exists(real_path), existed_before)

    def test_never_creates_real_customer_deal_revenue_or_commission(self):
        import commission_ledger as cl
        before = cl.real_commission_summary()
        cs.run_outreach_simulation()
        after = cl.real_commission_summary()
        self.assertEqual(before["real_commission_records"], after["real_commission_records"])


if __name__ == "__main__":
    unittest.main()
