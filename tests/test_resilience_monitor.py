"""Tests for resilience_monitor.py (Continuous Trust & Resilience
Monitoring, 2026-07-29): the real Monitor + Classify aggregator over
existing signals -- every real signal function mocked here; each one's
own logic has its own isolated unit tests elsewhere (test_safe_mode.py,
test_publish_protection.py, test_customer_pipeline.py, test_health_trend.py).

    python -m unittest tests.test_resilience_monitor -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import resilience_monitor as rm


def _temp_path():
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(path)
    return path


def _finding(area, severity, detail="d", evidence=None):
    return {"area": area, "severity": severity, "detail": detail, "evidence": evidence or {}, "data_available": True}

_STABLE_SAFE_MODE = {
    "ai_generation": {"unstable": False, "reason": None, "since": None, "triggered_by": None},
    "market_intelligence": {"unstable": False, "reason": None, "since": None, "triggered_by": None},
    "marketplace_publishing": {"unstable": False, "reason": None, "since": None, "triggered_by": None},
    "any_subsystem_unstable": False,
}

_HEALTHY_PUBLISH_PROTECTION = {"arms": {}, "global": {"emergency_stopped": False, "emergency_reason": None}}

_EMPTY_PIPELINE_OVERVIEW = {"total_requests": 0, "needs_attention": [], "stage_distribution": {}, "requests": []}

_CLEAN_PINNING = {"checked": 0, "pinned": 0, "unpinned": []}

_NO_HEALTH_DATA = {"degrading": False, "reason": "not enough data", "window": []}


class TestClassifySafeMode(unittest.TestCase):
    @patch("safe_mode.list_safe_mode_status")
    def test_all_stable_is_all_informational(self, mock_status):
        mock_status.return_value = _STABLE_SAFE_MODE
        findings = rm._classify_safe_mode()
        self.assertTrue(all(f["severity"] == "informational" for f in findings))

    @patch("safe_mode.list_safe_mode_status")
    def test_an_unstable_subsystem_is_critical(self, mock_status):
        mock_status.return_value = {
            **_STABLE_SAFE_MODE,
            "ai_generation": {"unstable": True, "reason": "real failure", "since": "t", "triggered_by": "system"},
            "any_subsystem_unstable": True,
        }
        findings = rm._classify_safe_mode()
        ai_finding = next(f for f in findings if f["area"] == "safe_mode:ai_generation")
        self.assertEqual(ai_finding["severity"], "critical")


class TestClassifyPublishProtection(unittest.TestCase):
    @patch("channels.publish_protection.list_publish_protection_status")
    def test_emergency_stop_is_emergency(self, mock_status):
        mock_status.return_value = {"arms": {}, "global": {"emergency_stopped": True, "emergency_reason": "x"}}
        findings = rm._classify_publish_protection()
        global_finding = next(f for f in findings if f["area"] == "publish_protection:global")
        self.assertEqual(global_finding["severity"], "emergency")

    @patch("channels.publish_protection.list_publish_protection_status")
    def test_no_arms_is_honestly_no_data(self, mock_status):
        mock_status.return_value = _HEALTHY_PUBLISH_PROTECTION
        findings = rm._classify_publish_protection()
        arms_finding = next(f for f in findings if f["area"] == "publish_protection:arms")
        self.assertFalse(arms_finding["data_available"])

    @patch("channels.publish_protection.list_publish_protection_status")
    def test_high_risk_score_arm_is_critical(self, mock_status):
        mock_status.return_value = {
            "arms": {"kdp": {"risk_score": 90, "consecutive_failures": 0, "currently_allowed": False}},
            "global": {"emergency_stopped": False, "emergency_reason": None},
        }
        findings = rm._classify_publish_protection()
        arm_finding = next(f for f in findings if f["area"] == "publish_protection:kdp")
        self.assertEqual(arm_finding["severity"], "critical")

    @patch("channels.publish_protection.list_publish_protection_status")
    def test_healthy_arm_is_informational(self, mock_status):
        mock_status.return_value = {
            "arms": {"gumroad": {"risk_score": 5, "consecutive_failures": 0, "currently_allowed": True}},
            "global": {"emergency_stopped": False, "emergency_reason": None},
        }
        findings = rm._classify_publish_protection()
        arm_finding = next(f for f in findings if f["area"] == "publish_protection:gumroad")
        self.assertEqual(arm_finding["severity"], "informational")


class TestClassifyCustomerRisk(unittest.TestCase):
    @patch("customer_pipeline.list_pipeline_overview")
    def test_no_real_requests_is_honestly_no_data(self, mock_overview):
        mock_overview.return_value = _EMPTY_PIPELINE_OVERVIEW
        findings = rm._classify_customer_risk()
        self.assertEqual(len(findings), 1)
        self.assertFalse(findings[0]["data_available"])

    @patch("customer_pipeline.list_pipeline_overview")
    def test_payment_blocked_request_is_critical(self, mock_overview):
        mock_overview.return_value = {
            "total_requests": 1,
            "needs_attention": [{"request_id": "r1", "stage": "PAYMENT_BLOCKED_PADDLE_ONBOARDING", "recovery": "x"}],
        }
        findings = rm._classify_customer_risk()
        self.assertEqual(findings[0]["severity"], "critical")

    @patch("customer_pipeline.list_pipeline_overview")
    def test_stuck_new_request_is_warning(self, mock_overview):
        mock_overview.return_value = {
            "total_requests": 1,
            "needs_attention": [{"request_id": "r1", "stage": "NEW", "recovery": "x"}],
        }
        findings = rm._classify_customer_risk()
        self.assertEqual(findings[0]["severity"], "warning")

    @patch("customer_pipeline.list_pipeline_overview")
    def test_no_attention_needed_is_informational(self, mock_overview):
        mock_overview.return_value = {"total_requests": 3, "needs_attention": []}
        findings = rm._classify_customer_risk()
        self.assertEqual(findings[0]["severity"], "informational")


class TestClassifySecurityDrift(unittest.TestCase):
    @patch("ai_doctor._check_node_pinning")
    @patch("ai_doctor._check_python_pinning")
    def test_no_dependencies_is_honestly_no_data(self, mock_py, mock_node):
        mock_py.return_value = _CLEAN_PINNING
        mock_node.return_value = _CLEAN_PINNING
        findings = rm._classify_security_drift()
        self.assertTrue(all(not f["data_available"] for f in findings))

    @patch("ai_doctor._check_node_pinning")
    @patch("ai_doctor._check_python_pinning")
    def test_low_pinning_ratio_is_warning(self, mock_py, mock_node):
        mock_py.return_value = {"checked": 10, "pinned": 2, "unpinned": []}
        mock_node.return_value = _CLEAN_PINNING
        findings = rm._classify_security_drift()
        py_finding = next(f for f in findings if f["area"] == "security_drift:python")
        self.assertEqual(py_finding["severity"], "warning")

    @patch("ai_doctor._check_node_pinning")
    @patch("ai_doctor._check_python_pinning")
    def test_high_pinning_ratio_is_informational(self, mock_py, mock_node):
        mock_py.return_value = {"checked": 10, "pinned": 9, "unpinned": []}
        mock_node.return_value = _CLEAN_PINNING
        findings = rm._classify_security_drift()
        py_finding = next(f for f in findings if f["area"] == "security_drift:python")
        self.assertEqual(py_finding["severity"], "informational")


class TestClassifyHealthTrend(unittest.TestCase):
    @patch("health_trend.detect_health_degradation")
    def test_no_window_is_honestly_no_data(self, mock_detect):
        mock_detect.return_value = _NO_HEALTH_DATA
        findings = rm._classify_health_trend()
        self.assertFalse(findings[0]["data_available"])

    @patch("health_trend.detect_health_degradation")
    def test_degrading_with_critical_latest_reading_escalates(self, mock_detect):
        mock_detect.return_value = {"degrading": True, "reason": "x", "window": [{"status": "degraded"}, {"status": "critical"}]}
        findings = rm._classify_health_trend()
        self.assertEqual(findings[0]["severity"], "critical")

    @patch("health_trend.detect_health_degradation")
    def test_degrading_with_non_critical_latest_reading_is_warning(self, mock_detect):
        mock_detect.return_value = {"degrading": True, "reason": "x", "window": [{"status": "healthy"}, {"status": "degraded"}]}
        findings = rm._classify_health_trend()
        self.assertEqual(findings[0]["severity"], "warning")

    @patch("health_trend.detect_health_degradation")
    def test_stable_is_informational(self, mock_detect):
        mock_detect.return_value = {"degrading": False, "reason": "x", "window": [{"status": "healthy"}] * 3}
        findings = rm._classify_health_trend()
        self.assertEqual(findings[0]["severity"], "informational")


class TestAssessResilience(unittest.TestCase):
    @patch("health_trend.detect_health_degradation")
    @patch("ai_doctor._check_node_pinning")
    @patch("ai_doctor._check_python_pinning")
    @patch("customer_pipeline.list_pipeline_overview")
    @patch("channels.publish_protection.list_publish_protection_status")
    @patch("safe_mode.list_safe_mode_status")
    def test_all_clean_signals_produce_a_perfect_transparent_score(
        self, mock_safe_mode, mock_publish, mock_pipeline, mock_py, mock_node, mock_health,
    ):
        mock_safe_mode.return_value = _STABLE_SAFE_MODE
        mock_publish.return_value = {
            "arms": {"gumroad": {"risk_score": 0, "consecutive_failures": 0, "currently_allowed": True}},
            "global": {"emergency_stopped": False, "emergency_reason": None},
        }
        mock_pipeline.return_value = {"total_requests": 1, "needs_attention": []}
        mock_py.return_value = {"checked": 5, "pinned": 5, "unpinned": []}
        mock_node.return_value = {"checked": 5, "pinned": 5, "unpinned": []}
        mock_health.return_value = {"degrading": False, "reason": "x", "window": [{"status": "healthy"}] * 3}

        result = rm.assess_resilience()
        self.assertEqual(result["resilience_score"], 100)
        self.assertEqual(result["active_alerts"], [])

    @patch("health_trend.detect_health_degradation")
    @patch("ai_doctor._check_node_pinning")
    @patch("ai_doctor._check_python_pinning")
    @patch("customer_pipeline.list_pipeline_overview")
    @patch("channels.publish_protection.list_publish_protection_status")
    @patch("safe_mode.list_safe_mode_status")
    def test_zero_real_data_anywhere_is_honestly_unknown_never_a_fabricated_score(
        self, mock_safe_mode, mock_publish, mock_pipeline, mock_py, mock_node, mock_health,
    ):
        mock_safe_mode.return_value = _STABLE_SAFE_MODE  # safe_mode always has real data (defaults are real)
        mock_publish.return_value = _HEALTHY_PUBLISH_PROTECTION  # no arms -> no data
        mock_pipeline.return_value = _EMPTY_PIPELINE_OVERVIEW  # no requests -> no data
        mock_py.return_value = _CLEAN_PINNING  # no deps -> no data
        mock_node.return_value = _CLEAN_PINNING
        mock_health.return_value = _NO_HEALTH_DATA  # no window -> no data

        result = rm.assess_resilience()
        # safe_mode findings are always real (3 subsystems always reported) --
        # so resilience_score is real, not "Unknown", but scored count is low.
        self.assertIsInstance(result["resilience_score"], int)
        self.assertIn("بلا بيانات حقيقية", result["resilience_score_note"])

    @patch("health_trend.detect_health_degradation")
    @patch("ai_doctor._check_node_pinning")
    @patch("ai_doctor._check_python_pinning")
    @patch("customer_pipeline.list_pipeline_overview")
    @patch("channels.publish_protection.list_publish_protection_status")
    @patch("safe_mode.list_safe_mode_status")
    def test_a_real_critical_finding_appears_in_active_alerts(
        self, mock_safe_mode, mock_publish, mock_pipeline, mock_py, mock_node, mock_health,
    ):
        mock_safe_mode.return_value = {
            **_STABLE_SAFE_MODE,
            "ai_generation": {"unstable": True, "reason": "real failure", "since": "t", "triggered_by": "system"},
            "any_subsystem_unstable": True,
        }
        mock_publish.return_value = _HEALTHY_PUBLISH_PROTECTION
        mock_pipeline.return_value = _EMPTY_PIPELINE_OVERVIEW
        mock_py.return_value = _CLEAN_PINNING
        mock_node.return_value = _CLEAN_PINNING
        mock_health.return_value = _NO_HEALTH_DATA

        result = rm.assess_resilience()
        alert_areas = {f["area"] for f in result["active_alerts"]}
        self.assertIn("safe_mode:ai_generation", alert_areas)


class TestRecordIncident(unittest.TestCase):
    """Learn (2026-07-29): real incident recording -- append-only,
    dedup by real open/closed state per area, never a fabricated field."""

    def setUp(self):
        self.path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_an_informational_finding_with_no_open_incident_records_nothing(self):
        result = rm.record_incident(_finding("security_drift:python", "informational"), incidents_path=self.path)
        self.assertIsNone(result)
        self.assertEqual(rm.list_incidents(self.path), [])

    def test_a_critical_finding_opens_a_real_incident(self):
        finding = _finding("safe_mode:ai_generation", "critical", detail="real failure", evidence={"x": 1})
        record = rm.record_incident(finding, incidents_path=self.path)
        self.assertIsNotNone(record)
        self.assertEqual(record["event"], "opened")
        self.assertEqual(record["area"], "safe_mode:ai_generation")
        self.assertIn("real failure", record["root_cause"])
        self.assertIsNotNone(record["prevention_rule"])
        self.assertEqual(record["rollback_guidance"], "POST /api/v1/actions/clear-subsystem-unstable { name: 'ai_generation' }")

    def test_the_same_ongoing_critical_finding_is_never_recorded_twice(self):
        finding = _finding("safe_mode:ai_generation", "critical")
        first = rm.record_incident(finding, incidents_path=self.path)
        second = rm.record_incident(finding, incidents_path=self.path)
        self.assertIsNotNone(first)
        self.assertIsNone(second)
        self.assertEqual(len(rm.list_incidents(self.path)), 1)

    def test_a_real_resolution_closes_the_incident(self):
        rm.record_incident(_finding("safe_mode:ai_generation", "critical"), incidents_path=self.path)
        resolved = rm.record_incident(_finding("safe_mode:ai_generation", "informational"), incidents_path=self.path)
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved["event"], "resolved")
        # After resolution, a new critical finding opens a genuinely new incident.
        reopened = rm.record_incident(_finding("safe_mode:ai_generation", "critical"), incidents_path=self.path)
        self.assertIsNotNone(reopened)

    def test_unknown_area_family_gets_an_honest_root_cause_not_a_fabricated_one(self):
        finding = _finding("some_new_area:x", "critical")
        record = rm.record_incident(finding, incidents_path=self.path)
        self.assertIn("Unknown", record["root_cause"])
        self.assertIsNone(record["prevention_rule"])

    def test_no_data_available_finding_is_never_recorded_as_an_incident(self):
        finding = {"area": "customer_risk:pipeline", "severity": "informational", "detail": "no data", "evidence": {}, "data_available": False}
        result = rm.record_incident(finding, incidents_path=self.path)
        self.assertIsNone(result)


class TestMatchingProposalId(unittest.TestCase):
    @patch("tool_intelligence.proposals.list_proposals")
    def test_real_matching_proposal_is_cited(self, mock_list):
        mock_list.return_value = [{"id": "resolve_stuck_customer_requests"}]
        self.assertEqual(rm._matching_proposal_id("customer_risk:pipeline"), "resolve_stuck_customer_requests")

    @patch("tool_intelligence.proposals.list_proposals")
    def test_no_real_matching_proposal_is_honestly_none(self, mock_list):
        mock_list.return_value = [{"id": "fix_detected_bottlenecks"}]
        self.assertIsNone(rm._matching_proposal_id("customer_risk:pipeline"))

    def test_area_family_with_no_candidate_proposals_is_none_without_a_live_call(self):
        self.assertIsNone(rm._matching_proposal_id("safe_mode:ai_generation"))


class TestListIncidents(unittest.TestCase):
    def setUp(self):
        self.path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_empty_is_honestly_empty(self):
        self.assertEqual(rm.list_incidents(self.path), [])

    def test_newest_first(self):
        rm.record_incident(_finding("safe_mode:ai_generation", "critical"), incidents_path=self.path)
        rm.record_incident(_finding("safe_mode:market_intelligence", "critical"), incidents_path=self.path)
        incidents = rm.list_incidents(self.path)
        self.assertEqual(incidents[0]["area"], "safe_mode:market_intelligence")


if __name__ == "__main__":
    unittest.main()
