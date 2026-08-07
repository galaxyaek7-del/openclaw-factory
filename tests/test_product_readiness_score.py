import unittest
from unittest.mock import patch

import product_readiness_score as prs


class TestProductReadinessScore(unittest.TestCase):
    def test_technical_component_computes_ratio(self):
        fake_result = {"passed": True, "checks": [{"passed": True}, {"passed": True}, {"passed": False}]}
        with patch("inspectors.inspect_technical", return_value=fake_result):
            result = prs._technical_component("x.pdf")
            self.assertAlmostEqual(result["score"], 66.7, places=1)

    def test_technical_component_honest_on_exception(self):
        with patch("inspectors.inspect_technical", side_effect=RuntimeError("boom")):
            result = prs._technical_component("x.pdf")
            self.assertIsNone(result["score"])

    def test_commercial_component_separates_procedural_from_real_failures(self):
        fake_result = {
            "passed": False, "profit_score": 70,
            "failures": ["not_duplicate: matches a prior real product", "genuine_price_too_low: below floor"],
        }
        with patch("inspectors.audit_commercial", return_value=fake_result):
            result = prs._commercial_component("niche", 100)
            self.assertEqual(result["score"], 70)
            self.assertEqual(len(result["procedural_failures"]), 1)
            self.assertEqual(len(result["real_failures"]), 1)

    def test_commercial_component_all_procedural_still_reports_real_score(self):
        fake_result = {
            "passed": False, "profit_score": 66,
            "failures": ["not_duplicate: x", "not_previously_rejected: y"],
        }
        with patch("inspectors.audit_commercial", return_value=fake_result):
            result = prs._commercial_component("niche", 100)
            self.assertEqual(result["score"], 66)
            self.assertEqual(len(result["real_failures"]), 0)

    def test_strategic_component_averages_only_numeric_dimensions(self):
        fake_result = {
            "a": {"value": 80, "source": "s"}, "b": {"value": "Unknown", "source": "s"},
            "c": {"value": 40, "source": "s"},
        }
        with patch("strategic_intelligence_core.strategic_score", return_value=fake_result):
            result = prs._strategic_component("niche")
            self.assertEqual(result["score"], 60.0)

    def test_overall_excludes_unscored_dimensions(self):
        with patch.object(prs, "_technical_component", return_value={"score": 100, "evidence": "e", "source": "s"}), \
             patch.object(prs, "_commercial_component", return_value={"score": None, "evidence": "e", "source": "s"}), \
             patch.object(prs, "_strategic_component", return_value={"score": 50, "evidence": "e", "source": "s"}):
            result = prs.compute_product_readiness_score("x.pdf", 100, "niche")
            self.assertEqual(result["overall_readiness"], 75.0)

    def test_never_scores_customer_automation_or_security(self):
        with patch.object(prs, "_technical_component", return_value={"score": 100, "evidence": "e", "source": "s"}), \
             patch.object(prs, "_commercial_component", return_value={"score": 100, "evidence": "e", "source": "s"}), \
             patch.object(prs, "_strategic_component", return_value={"score": 100, "evidence": "e", "source": "s"}):
            result = prs.compute_product_readiness_score("x.pdf", 100, "niche")
            self.assertIn("customer", result["not_scored"])
            self.assertIn("automation", result["not_scored"])
            self.assertIn("security", result["not_scored"])
            self.assertNotIn("customer", result["dimensions"])

    def test_real_call_against_the_one_real_product_never_throws(self):
        result = prs.compute_product_readiness_score(
            "books/eu_ai_act_compliance_toolkit.pdf", 155.0, "EU AI Act Compliance Toolkit",
            cover_path="books/covers/eu_ai_act_compliance_toolkit_cover.png",
            title="EU AI Act Compliance Toolkit", platform="gumroad_premium", page_count=31,
        )
        self.assertIsInstance(result["overall_readiness"], float)


if __name__ == "__main__":
    unittest.main()
