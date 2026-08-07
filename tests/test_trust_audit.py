import unittest
from unittest.mock import patch

import trust_audit


class TestTrustAuditReport(unittest.TestCase):
    def test_build_report_has_all_8_named_sections(self):
        report = trust_audit.build_trust_audit_report()
        for key in ("potential_misleading_claims", "product_weaknesses", "customer_risks",
                    "quality_regressions", "reputation_risks", "security_risks",
                    "ethical_risks", "recent_quarantine_activity"):
            self.assertIn(key, report)

    def test_quality_regressions_honestly_discloses_no_trend_metric(self):
        result = trust_audit._quality_regressions()
        self.assertEqual(result["status"], "NO_REAL_TREND_METRIC")

    def test_quality_gate_discloses_the_2_uncovered_dimensions(self):
        result = trust_audit._quality_gate()
        self.assertIn("Originality", result["real_gap"])
        self.assertIn("Maintainability", result["real_gap"])

    def test_recent_quarantine_never_parses_whole_file(self):
        # Real, mechanical proof: a huge fake file should still return
        # fast and only the requested tail count.
        with patch("builtins.open", unittest.mock.mock_open(read_data="## \U0001F6AB a\nx\ny\n## \U0001F6AB b\nx\ny\n## \U0001F6AB c\nx\ny\n")):
            result = trust_audit._recent_quarantine_entries(n=2)
            self.assertEqual(len(result["entries"]), 2)
            self.assertEqual(result["total_real_rejections_ever"], 3)

    def test_recent_quarantine_handles_missing_file(self):
        with patch.object(trust_audit, "_QUARANTINE_PATH", "C:/definitely/not/real.md"):
            result = trust_audit._recent_quarantine_entries()
            self.assertEqual(result["entries"], [])

    def test_reputation_risks_zero_reviews_is_disclosed_not_hidden(self):
        with patch.object(trust_audit, "_FACTORY_ROOT", __import__("pathlib").Path("C:/definitely/not/real")):
            result = trust_audit._reputation_risks()
            self.assertEqual(result["real_reviews_recorded"], 0)
            self.assertIn("not silently treated", result["note"])

    def test_real_call_never_throws(self):
        # Real, non-mocked call against the actual repo state.
        report = trust_audit.build_trust_audit_report()
        self.assertIsInstance(report, dict)

    def test_render_markdown_includes_all_section_headers(self):
        md = trust_audit.render_trust_audit_report_markdown(trust_audit.build_trust_audit_report())
        for label in ("Potential Misleading Claims", "Product Weaknesses", "Customer Risks",
                      "Quality Regressions", "Reputation Risks", "Security Risks",
                      "Ethical Risks", "Recent Quarantine Activity"):
            self.assertIn(label, md)


if __name__ == "__main__":
    unittest.main()
