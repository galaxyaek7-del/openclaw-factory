"""Tests for executive_questions.py (Executive Intelligence Layer,
ADR-154, 2026-07-31): a citation-only layer answering 8 named strategic
questions -- every answer traces to an already-real function, never a
second, competing computation.

    python -m unittest tests.test_executive_questions -v
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import executive_questions


class TestAnswerStrategicQuestions(unittest.TestCase):
    def test_returns_all_8_named_questions_plus_timestamp(self):
        result = executive_questions.answer_strategic_questions()
        expected_keys = {
            "what_deserves_attention_today", "which_division_is_slowing_the_company",
            "where_is_expected_revenue_highest", "which_automations_are_underutilized",
            "what_should_be_built_next", "what_should_be_paused",
            "what_creates_the_highest_roi", "which_bottleneck_blocks_future_scaling",
            "generated_at",
        }
        self.assertEqual(set(result.keys()), expected_keys)

    def test_revenue_and_roi_cite_the_same_real_source_never_computed_twice(self):
        result = executive_questions.answer_strategic_questions()
        self.assertEqual(
            result["where_is_expected_revenue_highest"]["answer"],
            result["what_creates_the_highest_roi"]["answer"],
        )

    def test_automation_utilization_is_honestly_waiting_for_real_source(self):
        result = executive_questions.answer_strategic_questions()
        self.assertEqual(
            result["which_automations_are_underutilized"]["answer"],
            executive_questions.WAITING_FOR_REAL_SOURCE,
        )

    def test_every_answer_carries_a_real_source_citation_or_reason(self):
        result = executive_questions.answer_strategic_questions()
        for key, val in result.items():
            if key == "generated_at":
                continue
            self.assertTrue(val.get("source") or val.get("reason"), f"{key} missing a source/reason citation")

    def test_injected_brief_gox_cap_avoid_redundant_computation(self):
        # Enterprise Operations Center (ADR-155, 2026-07-31): a real bug
        # this test guards against regressing -- enterprise_operations.py
        # ::company_pulse() computes brief/gox/cap once and passes them
        # in; without this injection path, answer_strategic_questions()
        # would recompute all three internally a second time (a real,
        # confirmed timeout caught during live verification).
        fake_brief = {
            "company_health": {}, "top_risks": {"stop": [], "cancel": []}, "top_opportunities": [],
            "top_bottlenecks": {"bottlenecks": {"detected": False}, "customer_success_bottleneck": {"detected": False}},
            "recommended_priorities": {}, "products_to_accelerate": [], "products_to_pause": [],
            "wins": [], "research_needed": [], "founder_decisions_required": {}, "generated_at": "t",
        }
        fake_gox = {"market_health": {}}
        fake_cap = {"top_roi_initiatives": []}
        with patch("strategic_intelligence_core.build_executive_brief") as mock_brief, \
             patch("global_opportunity_exchange.build_global_opportunity_exchange_dashboard") as mock_gox, \
             patch("capital_allocation_engine.build_capital_allocation_dashboard") as mock_cap:
            executive_questions.answer_strategic_questions(brief=fake_brief, gox=fake_gox, cap=fake_cap)
        mock_brief.assert_not_called()
        mock_gox.assert_not_called()
        mock_cap.assert_not_called()


class TestWhichDivisionIsSlowing(unittest.TestCase):
    def test_no_matching_real_alert_area_is_honest_waiting_for_real_source(self):
        resilience = {"active_alerts": [{"area": "security_drift:node", "severity": "warning"}]}
        readiness = {"divisions": {"affiliate_commerce": {"division": "Affiliate Commerce", "dimensions": {}}}}
        result = executive_questions._which_division_is_slowing(resilience, readiness)
        self.assertEqual(result["answer"], executive_questions.WAITING_FOR_REAL_SOURCE)

    def test_matching_real_alert_area_is_cited_directly(self):
        resilience = {"active_alerts": [{"area": "affiliate commerce outage", "severity": "critical"}]}
        readiness = {"divisions": {"affiliate_commerce": {"division": "Affiliate Commerce", "dimensions": {}}}}
        result = executive_questions._which_division_is_slowing(resilience, readiness)
        self.assertNotEqual(result["answer"], executive_questions.WAITING_FOR_REAL_SOURCE)
        self.assertEqual(len(result["answer"]), 1)


if __name__ == "__main__":
    unittest.main()
