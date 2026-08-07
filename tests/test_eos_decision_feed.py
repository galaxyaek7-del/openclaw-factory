import unittest
from unittest.mock import patch

import eos_decision_feed as edf


class TestEosDecisionFeed(unittest.TestCase):
    def test_card_always_has_all_nine_fields(self):
        card = edf._card("p", "e", "b", "f", "c", "a", "r", "t", "pr", "s")
        for key in ("problem", "evidence", "business_impact", "financial_impact",
                    "confidence", "recommended_action", "estimated_roi",
                    "time_to_execute", "priority", "source"):
            self.assertIn(key, card)

    def test_todays_directive_card_honest_when_ledger_empty(self):
        with patch.object(edf, "_EXECUTIVE_DIRECTIVES_PATH", "C:/definitely/not/real.jsonl"):
            self.assertIsNone(edf._todays_directive_card())

    def test_todays_directive_card_never_fabricates_roi(self):
        with patch.object(edf, "_read_jsonl", return_value=[{"current_mission": "x", "tier": "1"}]):
            card = edf._todays_directive_card()
            self.assertEqual(card["estimated_roi"], "Unknown")
            self.assertEqual(card["time_to_execute"], "Unknown")

    def test_risk_cards_only_include_critical_or_emergency(self):
        fake_result = {"findings": [
            {"area": "a", "severity": "informational", "detail": "fine", "data_available": True},
            {"area": "b", "severity": "critical", "detail": "bad", "data_available": True},
        ]}
        with patch("resilience_monitor.assess_resilience", return_value=fake_result):
            cards = edf._risk_cards()
            self.assertEqual(len(cards), 1)
            self.assertIn("b", cards[0]["problem"])

    def test_opportunity_cards_never_fabricate_dollar_roi(self):
        fake_ranking = {"build_next": [{
            "niche": "x", "prior_status": "DEFERRED", "confidence_score": "low",
            "evidence_sources": ["a"], "expected_roi": {"value": 50, "source": "s"},
            "time_to_first_revenue": {"value": "NOT_MEASURABLE", "source": "s"},
        }]}
        with patch("goos.rank_build_candidates", return_value=fake_ranking):
            cards = edf._opportunity_cards()
            self.assertEqual(cards[0]["estimated_roi"], 50)
            self.assertEqual(cards[0]["time_to_execute"], "NOT_MEASURABLE")

    def test_build_feed_never_raises_on_empty_sources(self):
        with patch.object(edf, "_EXECUTIVE_DIRECTIVES_PATH", "C:/definitely/not/real.jsonl"), \
             patch("resilience_monitor.assess_resilience", return_value={"findings": []}), \
             patch("goos.rank_build_candidates", return_value={"build_next": []}), \
             patch("commercial_readiness.commercial_readiness_score", return_value={
                 "bottleneck": "financial", "overall": 0,
                 "dimensions": {"financial": {"score": 0, "evidence": "none"}},
             }):
            result = edf.build_eos_decision_feed()
            self.assertEqual(result["total"], 1)  # only the commercial priority card


if __name__ == "__main__":
    unittest.main()
