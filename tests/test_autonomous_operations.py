import json
import os
import tempfile
import unittest
from unittest.mock import patch

import autonomous_operations as ao


def _temp_jsonl(records):
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return path


class TestAutonomyLevels(unittest.TestCase):
    def test_seven_named_levels_zero_through_six(self):
        self.assertEqual(set(ao.AUTONOMY_LEVELS.keys()), set(range(7)))
        self.assertEqual(ao.AUTONOMY_LEVELS[0]["name"], "OBSERVE ONLY")
        self.assertEqual(ao.AUTONOMY_LEVELS[6]["name"], "NEVER AUTOMATE")

    def test_every_category_maps_to_a_valid_level(self):
        for category, entry in ao.ACTION_CATEGORY_AUTONOMY.items():
            self.assertIn(entry["level"], ao.AUTONOMY_LEVELS, f"{category} maps to an undefined level")
            self.assertTrue(entry["citation"], f"{category} has no real citation")


class TestClassifyActionAutonomy(unittest.TestCase):
    def test_known_category_returns_entry(self):
        entry = ao.classify_action_autonomy("evolution_approve_execute")
        self.assertEqual(entry["level"], 5)

    def test_unknown_category_returns_none(self):
        self.assertIsNone(ao.classify_action_autonomy("something_never_defined"))


class TestAuthorizeAction(unittest.TestCase):
    def test_unknown_category_always_refuses(self):
        result = ao.authorize_action("not_a_real_category")
        self.assertEqual(result["decision"], "REFUSE")

    def test_level_0_to_4_allowed_by_design(self):
        result = ao.authorize_action("proven_channel_publish")
        self.assertEqual(result["required_level"], 4)
        self.assertEqual(result["decision"], "ALLOW")

    def test_level_5_refuses_without_approval(self):
        result = ao.authorize_action("evolution_approve_execute")
        self.assertEqual(result["decision"], "REFUSE")

    def test_level_5_allows_with_explicit_real_approval(self):
        result = ao.authorize_action(
            "evolution_approve_execute",
            context={"founder_approved": True, "approval_reference": "proposal-123"},
        )
        self.assertEqual(result["decision"], "ALLOW")

    def test_level_5_refuses_with_approved_flag_but_no_reference(self):
        result = ao.authorize_action("evolution_approve_execute", context={"founder_approved": True})
        self.assertEqual(result["decision"], "REFUSE")

    def test_level_6_never_authorizes_even_with_explicit_approval(self):
        """The one rule this module must never break: Level 6 refuses
        unconditionally, regardless of anything a caller supplies."""
        result = ao.authorize_action(
            "real_payment_or_transaction",
            context={"founder_approved": True, "approval_reference": "anything", "override": True},
        )
        self.assertEqual(result["decision"], "REFUSE")

    def test_all_four_protected_gates_are_level_5(self):
        for category in ("evolution_approve_execute", "capital_reallocation",
                          "business_retirement", "new_or_elevated_risk_publish"):
            entry = ao.classify_action_autonomy(category)
            self.assertEqual(entry["level"], 5, f"{category} must stay Level 5 -- never loosened")

    def test_phase34_commission_categories_are_level_5(self):
        # ADR-227, Phase 34: the 4 new commission-commerce CEO approval
        # gates -- classified in anticipation, same precedent as
        # business_retirement, never loosened below Level 5.
        for category in ("high_value_commercial_outreach", "high_value_deal_approval",
                          "new_partner_financial_or_legal_risk", "unusual_commission_arrangement"):
            entry = ao.classify_action_autonomy(category)
            self.assertEqual(entry["level"], 5, f"{category} must be Level 5")

    def test_phase34_commission_categories_allow_with_real_approval(self):
        for category in ("high_value_commercial_outreach", "high_value_deal_approval",
                          "new_partner_financial_or_legal_risk", "unusual_commission_arrangement"):
            result = ao.authorize_action(category, context={"founder_approved": True, "approval_reference": "ref-1"})
            self.assertEqual(result["decision"], "ALLOW", f"{category} should allow with real approval")


class TestAutomationCandidateReport(unittest.TestCase):
    def test_empty_ledger_produces_no_verification_candidate(self):
        empty_path = _temp_jsonl([])
        report = ao.automation_candidate_report(verification_attempts_path=empty_path)
        tasks = [c["task"] for c in report["candidates"]]
        self.assertNotIn("Manual web-evidence verification for the Proof of Payment gate", tasks)
        os.remove(empty_path)

    def test_real_blocked_attempts_classify_keep_human(self):
        path = _temp_jsonl([
            {"status": "BLOCKED", "status_code": 403},
            {"status": "BLOCKED", "status_code": 403},
            {"status": "VERIFIED"},
        ])
        report = ao.automation_candidate_report(verification_attempts_path=path)
        verification = next(c for c in report["candidates"] if "verification" in c["task"])
        self.assertEqual(verification["classification"], "KEEP_HUMAN")
        self.assertEqual(verification["frequency"], 3)
        os.remove(path)

    def test_founder_approval_task_is_always_present_and_keep_human(self):
        report = ao.automation_candidate_report(verification_attempts_path=_temp_jsonl([]))
        approval = next(c for c in report["candidates"] if "approval" in c["task"])
        self.assertEqual(approval["classification"], "KEEP_HUMAN")


class TestIncidentLifecycleView(unittest.TestCase):
    @patch("resilience_monitor.list_incidents")
    def test_opened_maps_to_detected(self, mock_list):
        mock_list.return_value = [{"incident_id": "x:1", "area": "x", "event": "opened", "root_cause": None}]
        view = ao.incident_lifecycle_view()
        self.assertEqual(view["incidents"][0]["real_stage"], "DETECTED")

    @patch("resilience_monitor.list_incidents")
    def test_resolved_maps_to_closed(self, mock_list):
        mock_list.return_value = [{"incident_id": "x:1", "area": "x", "event": "resolved", "root_cause": None}]
        view = ao.incident_lifecycle_view()
        self.assertEqual(view["incidents"][0]["real_stage"], "CLOSED")

    @patch("resilience_monitor.list_incidents")
    def test_never_fabricates_the_six_untracked_stages(self, mock_list):
        mock_list.return_value = [{"incident_id": "x:1", "area": "x", "event": "opened", "root_cause": None}]
        view = ao.incident_lifecycle_view()
        self.assertEqual(len(view["incidents"][0]["unmeasured_stages"]), 6)

    @patch("resilience_monitor.list_incidents")
    def test_empty_is_honest_empty(self, mock_list):
        mock_list.return_value = []
        view = ao.incident_lifecycle_view()
        self.assertEqual(view["total"], 0)


class TestUnifiedOperationsQueue(unittest.TestCase):
    @patch("founder_console.build_founder_queue_partial")
    @patch("evolution_queue.list_evolution_queue")
    @patch("resilience_monitor.list_incidents")
    @patch("adaptive_priority_queue.build_adaptive_priority_queue")
    def test_merges_all_real_sources_with_no_source_crashing_the_whole_queue(
        self, mock_apq, mock_incidents, mock_evo, mock_fq,
    ):
        mock_apq.return_value = {"queue": [{"priority": 1, "recommended_action": "do X", "status": "OPEN"}]}
        mock_incidents.return_value = [{"incident_id": "a:1", "area": "a", "event": "opened", "severity": "critical", "detail": "d"}]
        mock_evo.return_value = {"awaiting_approval": [{"proposal_id": "p1", "stage_history": []}]}
        mock_fq.return_value = {"pending_decisions": [{"niche": "n1"}]}

        queue = ao.unified_operations_queue(verification_attempts_path=_temp_jsonl([]))
        self.assertGreaterEqual(queue["total_items"], 4)
        for item in queue["queue"]:
            self.assertIn("authorization", item)
            self.assertIn(item["type"], (
                "recommendation", "incident", "approval_pending",
                "decision_pending", "automation_candidate",
            ))

    @patch("founder_console.build_founder_queue_partial", side_effect=RuntimeError("boom"))
    @patch("evolution_queue.list_evolution_queue")
    @patch("resilience_monitor.list_incidents")
    @patch("adaptive_priority_queue.build_adaptive_priority_queue")
    def test_one_source_failing_never_crashes_the_whole_queue(
        self, mock_apq, mock_incidents, mock_evo, mock_fq,
    ):
        mock_apq.return_value = {"queue": []}
        mock_incidents.return_value = []
        mock_evo.return_value = {"awaiting_approval": []}
        queue = ao.unified_operations_queue(verification_attempts_path=_temp_jsonl([]))
        statuses = [i.get("status") for i in queue["queue"]]
        self.assertIn("SOURCE_UNAVAILABLE", statuses)


class TestAutonomousDailyScore(unittest.TestCase):
    def test_never_produces_a_single_fabricated_composite_number(self):
        result = ao.autonomous_daily_score()
        self.assertNotIn("composite_score", result)
        self.assertNotIn("overall_score", result)
        self.assertIn("dimensions", result)

    def test_every_dimension_has_a_real_value_or_an_honest_gap(self):
        result = ao.autonomous_daily_score()
        for name, dim in result["dimensions"].items():
            self.assertIn("value", dim, f"{name} missing a value field")


if __name__ == "__main__":
    unittest.main()
