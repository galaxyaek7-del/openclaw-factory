import json
import os
import tempfile
import unittest
from unittest.mock import patch

import commercial_simulation_lab as csl


class TestRecordSimulationEvent(unittest.TestCase):
    def test_event_carries_the_required_schema(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "events.jsonl")
            event = csl.record_simulation_event(product="P", customer="C", price=100, ledger_path=path)
            for field in ("SIMULATION_ID", "SIMULATION_ONLY", "SOURCE", "DATE", "PRODUCT", "CUSTOMER",
                          "PRICE", "FEES", "COMMISSION", "REVENUE", "COST", "CONTRIBUTION"):
                self.assertIn(field, event)
            self.assertTrue(event["SIMULATION_ONLY"])
            self.assertEqual(event["SOURCE"], "TEST")

    def test_never_writes_to_the_default_path_when_an_override_is_given(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "events.jsonl")
            default_existed_before = csl.DEFAULT_SIMULATION_LEDGER.exists()
            csl.record_simulation_event(product="P", customer="C", price=100, ledger_path=path)
            self.assertEqual(csl.DEFAULT_SIMULATION_LEDGER.exists(), default_existed_before)


class TestEndToEndSimulation(unittest.TestCase):
    def test_never_writes_to_a_real_ledger(self):
        from channels import ledger as sales_ledger
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "events.jsonl")
            with patch.object(sales_ledger, "append_event") as mock_append:
                csl.run_end_to_end_commercial_simulation(ledger_path=path)
                mock_append.assert_not_called()

    def test_every_stage_is_labeled(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "events.jsonl")
            result = csl.run_end_to_end_commercial_simulation(ledger_path=path)
            for stage_name, stage in result["stages"].items():
                label = stage.get("label") if isinstance(stage, dict) else None
                self.assertIsNotNone(label, f"stage {stage_name} has no label")


class TestFailureSimulations(unittest.TestCase):
    def test_covers_all_fifteen_named_scenarios(self):
        result = csl.run_failure_simulations()
        for scenario in csl.FAILURE_SCENARIOS:
            self.assertIn(scenario, result["scenarios"])

    def test_never_fabricates_a_missing_mechanism_as_real(self):
        result = csl.run_failure_simulations()
        for scenario, data in result["scenarios"].items():
            if data["detection"] == "MISSING":
                self.assertIn(scenario, result["gaps_found"])


class TestFalseSuccessTest(unittest.TestCase):
    def test_covers_all_six_named_scenarios(self):
        result = csl.run_false_success_test()
        for scenario in csl.FALSE_SUCCESS_SCENARIOS:
            self.assertIn(scenario, result["findings"])


if __name__ == "__main__":
    unittest.main()
