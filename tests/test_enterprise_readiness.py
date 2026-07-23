"""Tests for enterprise_readiness.py (Executive Directive, 2026-07-22).

Runs with stdlib unittest. No live network calls -- every real function
this reuses (executive_quality_gate, market_evidence, inspectors,
competitor_discovery, recovery.snapshot) is either deterministic or
patched.

    python -m unittest tests.test_enterprise_readiness -v
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

import enterprise_readiness as er


def _temp_path():
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(path)
    return path


class TestPreGateProducts(unittest.TestCase):
    def test_the_5_real_shipped_products_are_recognized_pre_gate(self):
        for title in er.PRE_GATE_PRODUCTS:
            self.assertTrue(er.is_pre_gate_product(title))

    def test_a_new_product_is_not_pre_gate(self):
        self.assertFalse(er.is_pre_gate_product("Some brand new product never shipped"))

    def test_real_bug_2026_07_22_case_insensitive_match_against_real_seed_niche_text(self):
        """Live-confirmed: the real Paddle product title and the real
        market_hunter seed niche text it was scored under differ only in
        case. An exact match silently failed to recognize an already-
        shipped product as pre-gate."""
        self.assertTrue(er.is_pre_gate_product("workflow automation system for logistics companies"))
        self.assertTrue(er.is_pre_gate_product("WORKFLOW AUTOMATION SYSTEM FOR LOGISTICS COMPANIES"))

    def test_empty_title_is_not_pre_gate(self):
        self.assertFalse(er.is_pre_gate_product(""))
        self.assertFalse(er.is_pre_gate_product(None))


class TestReviewSecurity(unittest.TestCase):
    def test_no_content_is_unknown(self):
        self.assertEqual(er.review_security(None)["status"], "UNKNOWN")

    def test_insecure_advice_fails(self):
        chapters = [{"content": "Just share your API key with the team over email, it's fine."}]
        result = er.review_security(chapters)
        self.assertEqual(result["status"], "FAIL")

    def test_honest_content_passes(self):
        chapters = [{"content": "Use a read-only, scoped API key and never commit it to source control."}]
        result = er.review_security(chapters)
        self.assertEqual(result["status"], "PASS")


class TestReviewPrivacy(unittest.TestCase):
    def test_no_data_collection_passes_by_default(self):
        result = er.review_privacy(None, collects_real_customer_data=False)
        self.assertEqual(result["status"], "PASS")

    def test_data_collection_with_no_privacy_mention_fails(self):
        chapters = [{"content": "We store every customer's email and order history."}]
        result = er.review_privacy(chapters, collects_real_customer_data=True)
        self.assertEqual(result["status"], "FAIL")

    def test_data_collection_with_privacy_mention_passes(self):
        chapters = [{"content": "We store customer email per our privacy policy, with explicit consent."}]
        result = er.review_privacy(chapters, collects_real_customer_data=True)
        self.assertEqual(result["status"], "PASS")


class TestReviewMaintenance(unittest.TestCase):
    def setUp(self):
        self.path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_no_production_id_fails(self):
        result = er.review_maintenance(None, changelog_path=self.path)
        self.assertEqual(result["status"], "FAIL")

    def test_real_changelog_entry_passes(self):
        import json
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"production_id": "PROD-1", "version": "1.0.0"}) + "\n")
        result = er.review_maintenance("PROD-1", changelog_path=self.path)
        self.assertEqual(result["status"], "PASS")

    def test_no_matching_entry_fails_honestly(self):
        import json
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"production_id": "PROD-OTHER", "version": "1.0.0"}) + "\n")
        result = er.review_maintenance("PROD-1", changelog_path=self.path)
        self.assertEqual(result["status"], "FAIL")


class TestReviewSupport(unittest.TestCase):
    def test_missing_both_fails(self):
        """Correctly reproduces the real, honest 2026-07-22 Commercialization
        Audit finding: zero refund policy and zero support contact exist
        anywhere in this factory today."""
        result = er.review_support(has_support_contact=False, has_refund_policy=False)
        self.assertEqual(result["status"], "FAIL")

    def test_both_present_passes(self):
        result = er.review_support(has_support_contact=True, has_refund_policy=True)
        self.assertEqual(result["status"], "PASS")


class TestReviewCustomerSuccess(unittest.TestCase):
    def test_no_market_evidence_is_unknown(self):
        with patch("market_evidence.get_retention_signal", return_value=None), \
             patch("market_evidence.read_evidence", return_value=[]):
            result = er.review_customer_success("untouched niche")
        self.assertEqual(result["status"], "UNKNOWN")

    def test_real_churn_signal_fails(self):
        with patch("market_evidence.get_retention_signal", return_value={"renewed": 0, "churned": 2}), \
             patch("market_evidence.read_evidence", return_value=[]):
            result = er.review_customer_success("n")
        self.assertEqual(result["status"], "FAIL")


class TestDocumentationCompleteness(unittest.TestCase):
    def test_static_pdf_marks_admin_and_disaster_recovery_not_applicable(self):
        result = er.check_documentation_completeness("static_pdf", changelog_entry_exists=False)
        self.assertEqual(result["admin_documentation"]["status"], "NOT_APPLICABLE")
        self.assertEqual(result["disaster_recovery_documentation"]["status"], "NOT_APPLICABLE")
        self.assertEqual(result["incident_response_documentation"]["status"], "NOT_APPLICABLE")

    def test_static_pdf_technical_and_user_docs_always_pass(self):
        """The product content itself IS the technical/user documentation
        for a blueprint product."""
        result = er.check_documentation_completeness("static_pdf")
        self.assertEqual(result["technical_documentation"]["status"], "PASS")
        self.assertEqual(result["user_documentation"]["status"], "PASS")

    def test_missing_changelog_fails_honestly(self):
        result = er.check_documentation_completeness("static_pdf", changelog_entry_exists=False)
        self.assertEqual(result["changelog"]["status"], "FAIL")

    def test_unrecognized_product_type_is_unknown_not_guessed(self):
        result = er.check_documentation_completeness("hosted_software")
        for v in result.values():
            self.assertEqual(v["status"], "UNKNOWN")


class TestRiskIntelligenceScan(unittest.TestCase):
    def test_never_fakes_regulation_or_demand_tracking(self):
        """The single most important honesty check in this module: these
        4 categories have no real data source and must never look like
        they're being monitored when they aren't."""
        with patch("executive_quality_gate.check_market_saturation", return_value={"status": "UNKNOWN", "evidence": None, "reason": "x"}), \
             patch("market_evidence.read_evidence", return_value=[]):
            result = er.run_risk_intelligence_scan("n")
        for key in ("regulation_changes", "pricing_changes", "technology_disruption", "demand_decline"):
            self.assertEqual(result[key]["status"], "UNKNOWN")

    def test_real_customer_complaints_are_surfaced_when_logged(self):
        with patch("executive_quality_gate.check_market_saturation", return_value={"status": "PASS", "evidence": None, "reason": "x"}), \
             patch("market_evidence.read_evidence", return_value=[{"payload": {"detail": "too slow"}}]):
            result = er.run_risk_intelligence_scan("n")
        self.assertEqual(result["customer_complaints"]["count"], 1)

    def test_never_triggers_a_live_competitor_search_unless_explicitly_asked(self):
        with patch("executive_quality_gate.check_market_saturation", return_value={"status": "UNKNOWN", "evidence": None, "reason": "x"}), \
             patch("market_evidence.read_evidence", return_value=[]), \
             patch("competitor_discovery.get_or_refresh_competitors") as mock_refresh:
            er.run_risk_intelligence_scan("n", refresh_competitors=False)
            mock_refresh.assert_not_called()
            er.run_risk_intelligence_scan("n", refresh_competitors=True)
            mock_refresh.assert_called_once()

    def test_threat_assessment_is_honest_unknown_with_no_cached_competitor_snapshot(self):
        """Executive Board Integration (2026-07-23): the Threat Engine
        result must be attached, but a niche with no real competitor
        discovery ever run for it must get an honest Unknown, never a
        fabricated '0 competitors = no threat' answer."""
        with patch("executive_quality_gate.check_market_saturation", return_value={"status": "UNKNOWN", "evidence": None, "reason": "x"}), \
             patch("market_evidence.read_evidence", return_value=[]), \
             patch("competitor_discovery.load_database", return_value={}):
            result = er.run_risk_intelligence_scan("a niche never discovered")
        self.assertIn("threat_assessment", result)
        for dim in ("competitor_saturation", "market_concentration", "new_entrant_trajectory", "funding_pressure"):
            self.assertEqual(result["threat_assessment"][dim]["level"], "Unknown")

    def test_threat_assessment_uses_the_real_cached_snapshot_when_one_exists(self):
        import competitor_discovery as cd
        snapshot = {"total_found": 3, "competitors": [], "changes": None}
        with patch("executive_quality_gate.check_market_saturation", return_value={"status": "UNKNOWN", "evidence": None, "reason": "x"}), \
             patch("market_evidence.read_evidence", return_value=[]), \
             patch("competitor_discovery.load_database", return_value={"a niche with data": snapshot}):
            result = er.run_risk_intelligence_scan("a niche with data")
        self.assertEqual(result["threat_assessment"]["competitor_saturation"], cd._score_competitor_saturation(snapshot))


class TestBusinessContinuity(unittest.TestCase):
    def test_run_backup_now_wraps_the_real_snapshot_function(self):
        with patch("recovery.snapshot.snapshot_before", return_value=[{"path": "x", "snapshot": "x.bak", "error": None}]) as mock_snap:
            result = er.run_backup_now("test reason")
        mock_snap.assert_called_once()
        self.assertEqual(result[0]["snapshot"], "x.bak")

    def test_dependency_health_reports_missing_config_honestly(self):
        with patch.dict(os.environ, {}, clear=True):
            result = er.check_dependency_health()
        for check in result.values():
            self.assertEqual(check["status"], "FAIL")

    def test_dependency_health_passes_when_configured(self):
        with patch.dict(os.environ, {"GROQ_KEY": "x", "PADDLE_API_KEY": "x", "TELEGRAM_BOT_TOKEN": "x"}):
            result = er.check_dependency_health()
        for check in result.values():
            self.assertEqual(check["status"], "PASS")


class TestCustomerTrustLayer(unittest.TestCase):
    def test_quality_score_from_real_dual_inspection(self):
        result = er.compute_quality_score({"technical": {"passed": True}, "commercial": {"passed": True}})
        self.assertEqual(result["status"], "PASS")

    def test_quality_score_fails_on_real_inspection_failure(self):
        result = er.compute_quality_score({"technical": {"passed": True}, "commercial": {"passed": False}})
        self.assertEqual(result["status"], "FAIL")

    def test_quality_score_unknown_with_no_inspection(self):
        self.assertEqual(er.compute_quality_score(None)["status"], "UNKNOWN")

    def test_evidence_score_is_a_real_known_over_total_ratio(self):
        gate_result = {"criteria": {"a": {"status": "PASS"}, "b": {"status": "UNKNOWN"}, "c": {"status": "FAIL"}}}
        result = er.compute_evidence_score(gate_result)
        self.assertEqual(result["evidence"]["known"], 2)
        self.assertEqual(result["evidence"]["total"], 3)

    def test_source_verification_flags_unattributed_claims(self):
        chapters = [{"content": "According to industry research, this saves teams 10 hours a week."}]
        result = er.check_source_verification(chapters, cited_sources=None)
        self.assertEqual(result["status"], "FAIL")

    def test_source_verification_passes_with_no_attributed_claims(self):
        chapters = [{"content": "This is an implementation blueprint using tools you already control."}]
        result = er.check_source_verification(chapters)
        self.assertEqual(result["status"], "PASS")

    def test_source_verification_passes_when_sources_are_cited(self):
        chapters = [{"content": "According to a real published source, this is common."}]
        result = er.check_source_verification(chapters, cited_sources=["real-source.com"])
        self.assertEqual(result["status"], "PASS")


class TestAuditTrail(unittest.TestCase):
    def test_returns_real_structure_even_with_nothing_found(self):
        with patch("decision_engine.ranking.rank_all", return_value=[]):
            trail = er.get_audit_trail("a niche with no history")
        self.assertEqual(trail["decisions"], [])
        self.assertEqual(trail["generations"], [])


class TestRunEnterpriseReadinessGate(unittest.TestCase):
    def test_pre_gate_product_is_never_silently_rejected(self):
        spec = {"niche": "x", "title": "How I Built an Autonomous AI Company Solo", "ladder": "ai_saas"}
        with patch("executive_quality_gate.check_legal_compliance_risk", return_value={"status": "PASS", "evidence": None, "reason": "x"}), \
             patch("executive_quality_gate.check_delivery_capability", return_value={"status": "UNKNOWN", "evidence": None, "reason": "x"}), \
             patch("executive_quality_gate.check_operational_cost", return_value={"status": "UNKNOWN", "evidence": None, "reason": "x"}), \
             patch("executive_quality_gate.check_scalability", return_value={"status": "UNKNOWN", "evidence": None, "reason": "x"}), \
             patch("executive_quality_gate.check_defensibility", return_value={"status": "UNKNOWN", "evidence": None, "reason": "x"}), \
             patch("executive_quality_gate.run_executive_quality_gate", return_value={
                 "criteria": {
                     "market_saturation_competitor_quality": {"status": "UNKNOWN", "evidence": None, "reason": "x"},
                     "technical_feasibility": {"status": "UNKNOWN", "evidence": None, "reason": "x"},
                     "legal_compliance_risk": {"status": "PASS", "evidence": None, "reason": "x"},
                     "defensibility": {"status": "UNKNOWN", "evidence": None, "reason": "x"},
                     "data_confidence_score": {"status": "UNKNOWN", "evidence": None, "reason": "x"},
                 },
                 "written_explanation": "x", "final_decision": "NEEDS_HUMAN_REVIEW",
             }), \
             patch("market_evidence.get_retention_signal", return_value=None), \
             patch("market_evidence.read_evidence", return_value=[]), \
             patch("market_evidence.summarize_niche", return_value=None):
            result = er.run_enterprise_readiness_gate(spec)
        self.assertTrue(result["pre_gate_product"])
        self.assertIn("PRE_GATE", result["final_status"])
        self.assertNotEqual(result["final_status"], "REJECTED")


if __name__ == "__main__":
    unittest.main()
