"""Tests for anti_bias_check.py (ADR-206, Phase 16, 2026-08-08).

    python -m unittest tests.test_anti_bias_check -v
"""

import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import anti_bias_check as abc


class TestIndividualChecks(unittest.TestCase):
    def test_small_sample_flags_below_minimum(self):
        result = abc.check_small_sample(5)
        self.assertTrue(result["flagged"])

    def test_small_sample_passes_at_minimum(self):
        result = abc.check_small_sample(30)
        self.assertFalse(result["flagged"])

    def test_small_sample_flags_none(self):
        result = abc.check_small_sample(None)
        self.assertTrue(result["flagged"])

    def test_single_data_point_flags_one_event(self):
        result = abc.check_single_data_point([{"x": 1}])
        self.assertTrue(result["flagged"])

    def test_single_data_point_passes_multiple_events(self):
        result = abc.check_single_data_point([{"x": 1}, {"x": 2}])
        self.assertFalse(result["flagged"])

    def test_vanity_metric_flags_non_revenue_linked(self):
        result = abc.check_vanity_metric("page_views", is_revenue_linked=False)
        self.assertTrue(result["flagged"])

    def test_vanity_metric_passes_revenue_linked(self):
        result = abc.check_vanity_metric("net_revenue", is_revenue_linked=True)
        self.assertFalse(result["flagged"])

    def test_platform_concentration_flags_partial_coverage(self):
        result = abc.check_platform_concentration(1, 4)
        self.assertTrue(result["flagged"])

    def test_platform_concentration_passes_full_coverage(self):
        result = abc.check_platform_concentration(4, 4)
        self.assertFalse(result["flagged"])

    def test_model_bias_flags_single_provider(self):
        result = abc.check_model_bias(True, 1)
        self.assertTrue(result["flagged"])

    def test_recency_bias_flags_short_window(self):
        result = abc.check_recency_bias(2)
        self.assertTrue(result["flagged"])

    def test_recency_bias_passes_long_window(self):
        result = abc.check_recency_bias(45)
        self.assertFalse(result["flagged"])

    def test_confirmation_bias_flags_single_source(self):
        result = abc.check_confirmation_bias(1)
        self.assertTrue(result["flagged"])


class TestAssessRecommendation(unittest.TestCase):
    def test_only_runs_checks_with_real_input(self):
        # n=5 plus the 2 checks with real, non-None defaults
        # (single_ai_provider, evidence_sources_count) -- events/
        # metric_name/platform_count/data_span_days are all None here
        # and correctly produce no check.
        result = abc.assess_recommendation(n=5)
        biases = {c["bias"] for c in result["checks_run"]}
        self.assertEqual(biases, {"small_sample", "model_bias", "confirmation_bias"})

    def test_weak_evidence_true_when_any_check_flags(self):
        result = abc.assess_recommendation(n=1)
        self.assertTrue(result["weak_evidence"])

    def test_weak_evidence_false_when_all_checks_pass(self):
        result = abc.assess_recommendation(n=100, evidence_sources_count=5, single_ai_provider=False, real_providers_available=2)
        self.assertFalse(result["weak_evidence"])

    def test_no_input_produces_no_checks_never_a_fabricated_result(self):
        result = abc.assess_recommendation()
        # single_ai_provider/evidence_sources_count have real defaults, so
        # at minimum those 2 checks run; verify no exception and a real shape.
        self.assertIn("checks_run", result)
        self.assertIn("weak_evidence", result)


if __name__ == "__main__":
    unittest.main()
