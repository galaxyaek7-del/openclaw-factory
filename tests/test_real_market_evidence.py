"""Tests for real_market_evidence/ (ADR-058).

Runs with stdlib unittest. Never touches the real niche_reports/
directory or a live Amazon page of any kind — the "real" branch is
exercised entirely via profit_oracle._find_niche_report() mocked with a
fixture report shaped exactly like niche_validator_v2.py's own real
output.

    python -m unittest tests.test_real_market_evidence -v
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from real_market_evidence import evidence_collector
from real_market_evidence.types import METRICS

_FIXTURE_REPORT = {
    "status": "success",
    "keyword": "gratitude journal",
    "analyzed_at": "2026-07-01T00:00:00",
    "metrics": {
        "total_results": 8000,
        "books_analyzed": 18,
        "price": {"min": 6.99, "avg": 9.99, "max": 14.99},
        "reviews": {"avg": 120, "max": 900},
        "rating": {"avg": 4.3, "count": 18},
    },
}


class TestNoSavedReport(unittest.TestCase):
    @patch("profit_oracle._find_niche_report", return_value=None)
    def test_every_metric_is_unknown_with_zero_confidence(self, mock_find):
        evidence = evidence_collector.collect_evidence("a never-verified niche")
        for metric in METRICS:
            self.assertIn(metric, evidence)
            self.assertEqual(evidence[metric].confidence, 0)
            self.assertEqual(evidence[metric].source, "unavailable")
            self.assertIsNone(evidence[metric].raw_value)

    @patch("profit_oracle._find_niche_report", return_value={"status": "error"})
    def test_error_status_report_is_also_all_unknown(self, mock_find):
        evidence = evidence_collector.collect_evidence("a niche with a failed report")
        for metric in METRICS:
            self.assertEqual(evidence[metric].confidence, 0)


class TestRealSavedReport(unittest.TestCase):
    @patch("profit_oracle._find_niche_report", return_value=_FIXTURE_REPORT)
    def test_real_metrics_are_populated_with_real_values_and_confidence(self, mock_find):
        evidence = evidence_collector.collect_evidence("gratitude journal")

        self.assertEqual(evidence["amazon_search_result_count"].raw_value, 8000)
        self.assertGreater(evidence["amazon_search_result_count"].confidence, 0)
        self.assertEqual(evidence["amazon_search_result_count"].timestamp, "2026-07-01T00:00:00")

        self.assertEqual(evidence["competing_listings_count"].raw_value, 18)
        self.assertEqual(evidence["pricing_distribution"].raw_value["avg"], 9.99)
        self.assertEqual(evidence["review_count_distribution"].raw_value["avg"], 120)

    @patch("profit_oracle._find_niche_report", return_value=_FIXTURE_REPORT)
    def test_category_saturation_is_derived_from_the_factorys_own_existing_threshold(self, mock_find):
        import profit_oracle
        evidence = evidence_collector.collect_evidence("gratitude journal")
        expected = round(min(100, 100 * 8000 / profit_oracle.MAX_COMPETITION), 1)
        self.assertEqual(evidence["category_saturation"].normalized_value, expected)

    @patch("profit_oracle._find_niche_report", return_value=_FIXTURE_REPORT)
    def test_structurally_unavailable_metrics_remain_unknown_even_with_a_real_report(self, mock_find):
        """BSR, marketplace age, update frequency, seller concentration,
        revenue indicators are never captured by a single saved
        search-results snapshot — Unknown regardless of report quality."""
        evidence = evidence_collector.collect_evidence("gratitude journal")
        for metric in ("best_seller_rank", "marketplace_age", "update_frequency",
                        "seller_concentration", "revenue_indicators"):
            self.assertEqual(evidence[metric].confidence, 0)
            self.assertEqual(evidence[metric].source, "unavailable")

    @patch("profit_oracle._find_niche_report", return_value={"status": "success", "metrics": {}})
    def test_missing_individual_fields_degrade_to_unknown_never_crash(self, mock_find):
        evidence = evidence_collector.collect_evidence("a report with empty metrics")
        for metric in METRICS:
            self.assertIsNotNone(evidence[metric])
            self.assertEqual(evidence[metric].confidence, 0)


class TestEveryMetricHasFullContract(unittest.TestCase):
    @patch("profit_oracle._find_niche_report", return_value=_FIXTURE_REPORT)
    def test_every_evidence_object_has_all_six_required_fields(self, mock_find):
        evidence = evidence_collector.collect_evidence("gratitude journal")
        for metric, e in evidence.items():
            d = e.to_dict()
            for field in ("source", "timestamp", "confidence", "raw_value", "normalized_value", "explanation"):
                self.assertIn(field, d)


class TestEvidenceQualitySummary(unittest.TestCase):
    @patch("profit_oracle._find_niche_report", return_value=None)
    def test_zero_real_reports_gives_zero_percent_quality(self, mock_find):
        summary = evidence_collector.evidence_quality_summary(["niche a", "niche b"])
        self.assertEqual(summary["evidence_quality_pct"], 0.0)
        self.assertEqual(summary["aggregate_real_metrics"], 0)

    def test_mixed_real_and_unknown_reports_a_real_percentage(self):
        def fake_find(niche):
            return _FIXTURE_REPORT if niche == "niche with report" else None

        with patch("profit_oracle._find_niche_report", side_effect=fake_find):
            summary = evidence_collector.evidence_quality_summary(["niche with report", "niche without report"])

        self.assertGreater(summary["evidence_quality_pct"], 0.0)
        self.assertLess(summary["evidence_quality_pct"], 100.0)
        self.assertEqual(summary["per_niche"]["niche without report"]["real"], 0)
        self.assertGreater(summary["per_niche"]["niche with report"]["real"], 0)


if __name__ == "__main__":
    unittest.main()
