"""Tests for value_engine.py (OpenClaw Value Engine, 2026-07-23).

Runs with stdlib unittest. Pure helper functions are tested with zero
I/O. Integration tests use real, temp-file-isolated decisions (via
decision_engine.engine.record_ladder_decision(), the same real path
every real candidate goes through) — but do NOT assert on exact
cost/ROI numeric values, since revenue_pipeline.plan.estimate_
production_cost()/compare_ladder_variants() read the real default
data/ai_cost_log.jsonl with no override param exposed here (the same
pre-existing, already-shipped pattern revenue_pipeline/pipeline.py's
own process_opportunity() already uses) — real, accumulating log state,
not deterministic across machines/runs. Structure (key presence, honest
Unknown where expected) is asserted instead.

    python -m unittest tests.test_value_engine -v
"""

import os
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from decision_engine import engine
import value_engine as ve


def _temp_path(suffix=".jsonl"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


class TestKnowledgeAccumulation(unittest.TestCase):
    def test_zero_sources_is_low(self):
        result = ve._score_knowledge_accumulation(None, None, None)
        self.assertEqual(result["score"], 0)
        self.assertEqual(result["level"], "منخفضة")

    def test_all_three_real_sources_is_high(self):
        board_brief = {"has_meeting": True}
        active_alerts = {"total": 2}
        market_evidence_summary = {"total_events": 5}
        result = ve._score_knowledge_accumulation(board_brief, active_alerts, market_evidence_summary)
        self.assertEqual(result["score"], 3)
        self.assertEqual(result["level"], "مرتفعة")

    def test_one_real_source_is_medium(self):
        result = ve._score_knowledge_accumulation({"has_meeting": True}, None, None)
        self.assertEqual(result["score"], 1)
        self.assertEqual(result["level"], "متوسطة")


class TestSynergyAndBundle(unittest.TestCase):
    def test_no_ladder_is_honestly_unknown_for_both(self):
        synergy, bundle = ve._score_synergy_and_bundle(None, Counter())
        self.assertEqual(synergy["answer"], "Unknown")
        self.assertEqual(bundle["answer"], "Unknown")

    def test_no_real_siblings_not_bundle_eligible(self):
        synergy, bundle = ve._score_synergy_and_bundle("ai_saas", Counter({"ai_saas": 1}))
        self.assertEqual(synergy["sibling_count"], 0)
        self.assertFalse(bundle["eligible"])

    def test_two_or_more_real_siblings_is_bundle_eligible(self):
        synergy, bundle = ve._score_synergy_and_bundle("ai_saas", Counter({"ai_saas": 3}))
        self.assertEqual(synergy["sibling_count"], 2)
        self.assertTrue(bundle["eligible"])


class TestUpgradePotential(unittest.TestCase):
    def test_missing_inputs_is_honestly_unknown(self):
        result = ve._score_upgrade_potential(None, 97, {"variants": []})
        self.assertEqual(result["answer"], "Unknown")

    def test_no_real_higher_priced_variant_available(self):
        variants = {"variants": [{"ladder": "kdp_books", "price": 15}]}
        result = ve._score_upgrade_potential("kdp_books", 97, variants)
        self.assertFalse(result["available"])

    def test_a_real_higher_priced_variant_computes_a_real_price_delta(self):
        variants = {"variants": [
            {"ladder": "kdp_books", "price": 15},
            {"ladder": "ai_saas", "price": 388},
            {"ladder": "b2b_systems", "price": 250},
        ]}
        result = ve._score_upgrade_potential("kdp_books", 97, variants)
        self.assertTrue(result["available"])
        self.assertEqual(result["best_upgrade_ladder"], "ai_saas")
        self.assertEqual(result["price_delta"], 291)

    def test_a_ladder_with_an_error_is_never_picked(self):
        variants = {"variants": [
            {"ladder": "ai_saas", "error": "unknown ladder"},
            {"ladder": "b2b_systems", "price": 250},
        ]}
        result = ve._score_upgrade_potential("kdp_books", 97, variants)
        self.assertEqual(result["best_upgrade_ladder"], "b2b_systems")


class TestAtRiskFlag(unittest.TestCase):
    def test_clean_evidence_is_not_flagged(self):
        result = ve._compute_at_risk_flag({"has_meeting": False}, {"by_severity_counts": {}}, [])
        self.assertFalse(result["flagged"])
        self.assertEqual(result["retirement_recommendation"]["answer"], "Unknown")

    def test_a_real_not_approved_board_decision_is_flagged(self):
        board_brief = {"has_meeting": True, "board_decision": "NOT_APPROVED"}
        result = ve._compute_at_risk_flag(board_brief, {}, [])
        self.assertTrue(result["flagged"])
        self.assertTrue(any("مجلس" in r for r in result["reasons"]))

    def test_a_real_critical_alert_is_flagged(self):
        active_alerts = {"by_severity_counts": {"Critical": 2}}
        result = ve._compute_at_risk_flag(None, active_alerts, [])
        self.assertTrue(result["flagged"])

    def test_a_real_negative_reopen_is_flagged(self):
        reopen_history = [{"decision_changed": True, "new_decision": {"board_decision": "NOT_APPROVED"}}]
        result = ve._compute_at_risk_flag(None, {}, reopen_history)
        self.assertTrue(result["flagged"])

    def test_never_produces_a_definitive_retirement_recommendation(self):
        """The single most important honesty check for this dimension:
        no matter how many real risk signals fire, this must never
        become a real 'retire' verdict -- zero real sales-performance
        data exists anywhere in this factory to justify that."""
        board_brief = {"has_meeting": True, "board_decision": "NOT_APPROVED"}
        active_alerts = {"by_severity_counts": {"Critical": 5}}
        result = ve._compute_at_risk_flag(board_brief, active_alerts, [])
        self.assertTrue(result["flagged"])
        self.assertEqual(result["retirement_recommendation"]["answer"], "Unknown")


class TestStrategicValueComposite(unittest.TestCase):
    def test_no_numeric_dimensions_is_honestly_unknown(self):
        result = ve._compute_strategic_value_composite({}, {})
        self.assertEqual(result["answer"], "Unknown")

    def test_real_numeric_average_computed_correctly(self):
        reused = {"recurring_revenue_potential": 80, "scalability": 60, "automation_potential": 40}
        result = ve._compute_strategic_value_composite(reused, {})
        self.assertEqual(result["score"], 60.0)
        self.assertEqual(result["based_on_n_dimensions"], 3)

    def test_dict_shaped_and_raw_number_dimensions_both_count(self):
        reused = {"recurring_revenue_potential": 100, "defensibility": {"score": 50}}
        result = ve._compute_strategic_value_composite(reused, {})
        self.assertEqual(result["score"], 75.0)


class TestPriorityScore(unittest.TestCase):
    def test_no_real_inputs_is_honestly_unknown(self):
        result = ve._compute_priority_score(None, ve._unknown("x"))
        self.assertEqual(result["answer"], "Unknown")

    def test_real_average_of_opportunity_score_and_strategic_value(self):
        result = ve._compute_priority_score(80, {"score": 60})
        self.assertEqual(result["score"], 70.0)
        self.assertEqual(set(result["based_on"]), {"opportunity_score", "strategic_value"})

    def test_only_opportunity_score_available_still_produces_a_real_score(self):
        result = ve._compute_priority_score(90, ve._unknown("x"))
        self.assertEqual(result["score"], 90.0)
        self.assertEqual(result["based_on"], ["opportunity_score"])


class TestRecommendation(unittest.TestCase):
    def test_at_risk_produces_an_urgent_review_action(self):
        priority = {"score": 80}
        at_risk = {"flagged": True, "reasons": ["قرار مجلس حقيقي: غير موافَق عليه"]}
        actions = ve._build_recommendation(priority, at_risk, ve._unknown("x"), ve._unknown("x"))
        self.assertTrue(any("مراجعة عاجلة" in a for a in actions))

    def test_high_priority_score_recommends_continued_investment(self):
        actions = ve._build_recommendation({"score": 85}, {"flagged": False, "reasons": []}, ve._unknown("x"), ve._unknown("x"))
        self.assertTrue(any("أولوية استثمار عالية" in a for a in actions))

    def test_low_priority_score_recommends_no_further_investment(self):
        actions = ve._build_recommendation({"score": 10}, {"flagged": False, "reasons": []}, ve._unknown("x"), ve._unknown("x"))
        self.assertTrue(any("أولوية منخفضة" in a for a in actions))

    def test_a_real_upgrade_opportunity_is_surfaced(self):
        upgrade = {"available": True, "best_upgrade_ladder": "ai_saas", "price_delta": 200}
        actions = ve._build_recommendation({"score": 50}, {"flagged": False, "reasons": []}, upgrade, ve._unknown("x"))
        self.assertTrue(any("ai_saas" in a for a in actions))

    def test_a_real_bundle_opportunity_is_surfaced(self):
        bundle = {"eligible": True, "sibling_count": 3}
        actions = ve._build_recommendation({"score": 50}, {"flagged": False, "reasons": []}, ve._unknown("x"), bundle)
        self.assertTrue(any("حزمة" in a for a in actions))


class TestComputeValueProfileIntegration(unittest.TestCase):
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

    def _record(self, niche, ladder, accepted=True, score=85.0, price=250):
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

    def _profile(self, niche, **kwargs):
        kwargs.setdefault("decisions_path", self.decisions_path)
        kwargs.setdefault("board_path", self.board_path)
        kwargs.setdefault("alerts_path", self.alerts_path)
        kwargs.setdefault("reopen_log_path", self.reopen_log_path)
        kwargs.setdefault("evidence_path", self.evidence_path)
        return ve.compute_value_profile(niche, **kwargs)

    def test_no_real_decision_is_honestly_none(self):
        self.assertIsNone(self._profile("a niche that was never scored"))

    def test_a_rejected_decision_is_honestly_none_not_evaluated(self):
        self._record("a rejected niche", "kdp_books", accepted=False, score=20.0)
        self.assertIsNone(self._profile("a rejected niche"))

    def test_an_accepted_decision_produces_a_full_profile_with_all_17_dimensions(self):
        self._record("a real accepted niche for value engine test", "ai_saas")
        profile = self._profile("a real accepted niche for value engine test")
        self.assertIsNotNone(profile)
        expected_dimensions = (
            "recurring_revenue_potential", "scalability", "defensibility", "ai_leverage", "automation_potential",
            "competitive_moat", "long_term_strategic_value", "global_demand", "platform_potential", "enterprise_potential",
            "knowledge_accumulation", "synergy_with_existing_products", "bundle_potential", "upgrade_potential",
            "expected_customer_value", "lifetime_revenue_potential", "brand_building_impact",
        )
        for dim in expected_dimensions:
            self.assertIn(dim, profile["dimensions"], f"missing dimension: {dim}")

    def test_the_3_no_real_source_dimensions_are_always_honest_unknown(self):
        self._record("a niche for unknown-dims test", "ai_saas")
        profile = self._profile("a niche for unknown-dims test")
        for dim in ("expected_customer_value", "lifetime_revenue_potential", "brand_building_impact"):
            self.assertEqual(profile["dimensions"][dim]["answer"], "Unknown")

    def test_board_summary_carries_all_7_required_fields(self):
        self._record("a niche for board summary test", "ai_saas")
        profile = self._profile("a niche for board summary test")
        for field in ("priority_score", "expected_roi", "strategic_value", "estimated_build_cost",
                      "estimated_maintenance_cost", "estimated_lifetime_value", "recommendation"):
            self.assertIn(field, profile["board_summary"], f"missing board_summary field: {field}")

    def test_estimated_maintenance_cost_is_always_honest_unknown(self):
        self._record("a niche for maintenance cost test", "ai_saas")
        profile = self._profile("a niche for maintenance cost test")
        self.assertEqual(profile["board_summary"]["estimated_maintenance_cost"]["answer"], "Unknown")

    def test_synergy_reflects_real_sibling_decisions_sharing_a_ladder(self):
        self._record("sibling niche one", "b2b_systems")
        self._record("sibling niche two", "b2b_systems")
        self._record("sibling niche three", "b2b_systems")
        profile = self._profile("sibling niche one")
        self.assertEqual(profile["dimensions"]["synergy_with_existing_products"]["sibling_count"], 2)
        self.assertTrue(profile["dimensions"]["bundle_potential"]["eligible"])

    def test_at_risk_flag_reflects_a_real_persisted_board_rejection(self):
        import json
        self._record("a niche with a real board rejection", "ai_saas")
        meeting = {
            "niche": "a niche with a real board rejection", "convened_at": "2026-07-23T00:00:00+00:00",
            "tally": {"board_decision": "NOT_APPROVED"}, "decision_summary": {"decision": "NOT_APPROVED", "confidence": 0.2},
        }
        with open(self.board_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(meeting) + "\n")
        profile = self._profile("a niche with a real board rejection")
        self.assertTrue(profile["at_risk"]["flagged"])


class TestBuildValueEngineReport(unittest.TestCase):
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

    def _record(self, niche, ladder, score):
        ladder_result = {
            "accepted": True, "ladder_score": score, "price": 250, "reason": "test",
            "components": {
                "market_demand": 60, "competition_favorability": 70, "profit_potential": 50,
                "recurring_revenue_potential": 90, "reusability": 85, "automation_potential": 40,
            },
            "risk": {"score": 90, "level": "low", "notes": []},
            "confidence": {"score": 55, "level": "متوسطة", "note": "test"},
        }
        engine.record_ladder_decision(niche, ladder, ladder_result, decisions_path=self.decisions_path)

    def test_empty_portfolio_reports_honestly(self):
        result = ve.build_value_engine_report(
            decisions_path=self.decisions_path, board_path=self.board_path, alerts_path=self.alerts_path,
            reopen_log_path=self.reopen_log_path, evidence_path=self.evidence_path,
        )
        self.assertEqual(result["total_evaluated"], 0)
        self.assertEqual(result["profiles"], [])

    def test_real_portfolio_is_ranked_by_priority_score_descending(self):
        self._record("low score niche", "kdp_books", 40.0)
        self._record("high score niche", "ai_saas", 95.0)
        result = ve.build_value_engine_report(
            decisions_path=self.decisions_path, board_path=self.board_path, alerts_path=self.alerts_path,
            reopen_log_path=self.reopen_log_path, evidence_path=self.evidence_path,
        )
        self.assertEqual(result["total_evaluated"], 2)
        scores = [p["board_summary"]["priority_score"]["score"] for p in result["profiles"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(result["profiles"][0]["niche"], "high score niche")


if __name__ == "__main__":
    unittest.main()
