"""Tests for investment_pipeline.py (Global Revenue Discovery Engine,
2026-07-24): the real, unified Investment Pipeline across the 10 named
ranking dimensions and 12 named per-opportunity fields.

Runs with stdlib unittest. Every function reads only from temp-file-
isolated fixtures -- never the real data/*.jsonl files.

    python -m unittest tests.test_investment_pipeline -v
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import investment_pipeline as ip
import market_alerts
from decision_engine import engine


def _temp_path():
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(path)
    return path


class TestUrgencySignal(unittest.TestCase):
    def test_no_alerts_is_honestly_none_level(self):
        result = ip._urgency_signal(None)
        self.assertEqual(result["value"], "none")

    def test_critical_alert_is_high_urgency(self):
        result = ip._urgency_signal({"total": 1, "by_severity_counts": {"Critical": 1, "High": 0}})
        self.assertEqual(result["value"], "high")

    def test_high_alert_without_critical_is_medium_urgency(self):
        result = ip._urgency_signal({"total": 1, "by_severity_counts": {"Critical": 0, "High": 1}})
        self.assertEqual(result["value"], "medium")

    def test_only_low_medium_alerts_is_low_urgency(self):
        result = ip._urgency_signal({"total": 1, "by_severity_counts": {"Critical": 0, "High": 0, "Medium": 1}})
        self.assertEqual(result["value"], "low")


class TestBuildInvestmentPipelineEntry(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()
        self.board_path = _temp_path()
        self.alerts_path = _temp_path()
        self.reopen_log_path = _temp_path()
        self.evidence_path = _temp_path()

    def tearDown(self):
        for p in (self.decisions_path, self.board_path, self.alerts_path, self.reopen_log_path, self.evidence_path):
            if os.path.exists(p):
                os.remove(p)

    def _record(self, niche, ladder="ai_saas", accepted=True, score=85.0, price=250):
        ladder_result = {
            "accepted": accepted, "ladder_score": score, "price": price, "reason": "test",
            "components": {
                "market_demand": 60, "competition_favorability": 70, "profit_potential": 50,
                "recurring_revenue_potential": 90, "reusability": 85, "automation_potential": 40,
            },
            "risk": {"score": 90, "level": "low", "notes": []},
            "confidence": {"score": 55, "level": "متوسطة", "note": "test"},
            "defensibility": {"score": 75, "level": "عالية نسبياً", "note": "test"},
            "market_signal": {"score": 60, "level": "مرتفعة", "note": "test"},
            "ai_leverage": {"score": 80, "level": "عالية", "note": "test"},
        }
        engine.record_ladder_decision(niche, ladder, ladder_result, decisions_path=self.decisions_path)

    def _entry(self, niche):
        return ip.build_investment_pipeline_entry(
            niche, decisions_path=self.decisions_path, board_path=self.board_path, alerts_path=self.alerts_path,
            reopen_log_path=self.reopen_log_path, evidence_path=self.evidence_path,
        )

    def test_no_real_decision_is_honestly_none(self):
        self.assertIsNone(self._entry("never scored"))

    def test_all_10_ranking_dimensions_are_present(self):
        self._record("a full dimensions niche")
        entry = self._entry("a full dimensions niche")
        dims = entry["ranking_dimensions"]
        for dim in ("market_size", "competition", "urgency", "willingness_to_pay", "production_difficulty",
                    "long_term_strategic_value", "defensibility", "recurring_revenue_potential",
                    "global_scalability", "ai_leverage"):
            self.assertIn(dim, dims)

    def test_all_12_named_fields_are_present(self):
        self._record("a full fields niche")
        entry = self._entry("a full fields niche")
        for field in ("commercial_score", "business_model", "estimated_revenue", "estimated_profit",
                      "risk_analysis", "country_priority", "customer_profile", "recommended_product",
                      "recommended_price", "recommended_distribution", "recommended_marketing"):
            self.assertIn(field, entry)

    def test_country_priority_is_always_honestly_deferred(self):
        self._record("a country priority niche")
        entry = self._entry("a country priority niche")
        self.assertIsNone(entry["country_priority"]["value"])
        self.assertTrue(entry["country_priority"]["reason"])

    def test_recommended_product_requires_accepted_status(self):
        self._record("a rejected niche for ip", accepted=False, score=10.0)
        entry = self._entry("a rejected niche for ip")
        self.assertIsNone(entry["recommended_product"]["value"])

    def test_recommended_price_and_distribution_are_real(self):
        self._record("a priced niche")
        entry = self._entry("a priced niche")
        self.assertEqual(entry["recommended_price"], 250)
        self.assertEqual(entry["recommended_distribution"], "paddle")

    def test_urgency_reflects_a_real_active_alert(self):
        self._record("a niche with a real alert")
        alert = {
            "niche": "a niche with a real alert", "event_type": "new_competitor_detected",
            "source": "manual", "evidence": {"competitor": "x"}, "severity": "Critical",
            "confidence": "high", "occurred_at": "2026-07-24T00:00:00+00:00", "dedupe_key": "k1",
        }
        market_alerts._append_alert(alert, alerts_path=self.alerts_path)
        entry = self._entry("a niche with a real alert")
        self.assertEqual(entry["ranking_dimensions"]["urgency"]["value"], "high")


class TestBuildInvestmentPipeline(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.decisions_path):
            os.remove(self.decisions_path)

    def _record(self, niche, score):
        ladder_result = {
            "accepted": True, "ladder_score": score, "price": 200, "reason": "test",
            "components": {
                "market_demand": 60, "competition_favorability": 70, "profit_potential": 50,
                "recurring_revenue_potential": 90, "reusability": 85, "automation_potential": 40,
            },
            "risk": {"score": 90, "level": "low", "notes": []},
            "confidence": {"score": 55, "level": "متوسطة", "note": "test"},
        }
        engine.record_ladder_decision(niche, "ai_saas", ladder_result, decisions_path=self.decisions_path)

    def test_empty_factory_reports_honestly(self):
        result = ip.build_investment_pipeline(decisions_path=self.decisions_path)
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["total_real_decisions"], 0)

    def test_ranked_by_real_opportunity_score_descending(self):
        self._record("low", 40.0)
        self._record("high", 95.0)
        result = ip.build_investment_pipeline(decisions_path=self.decisions_path)
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["entries"][0]["niche"], "high")

    def test_limit_caps_entries_built(self):
        self._record("low", 40.0)
        self._record("high", 95.0)
        result = ip.build_investment_pipeline(decisions_path=self.decisions_path, limit=1)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["total_real_decisions"], 2)
        self.assertEqual(result["entries"][0]["niche"], "high")


if __name__ == "__main__":
    unittest.main()
