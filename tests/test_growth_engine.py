"""Tests for growth_engine.py (Global Growth Engine, 2026-07-24): the
real, honest Product Multiplication + Channel Expansion evaluation.

Runs with stdlib unittest. Every function reads only from temp-file-
isolated fixtures -- never the real data/*.jsonl files.

    python -m unittest tests.test_growth_engine -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import growth_engine
import market_evidence
from decision_engine import engine


def _temp_path():
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(path)
    return path


class TestEvaluateProductMultiplication(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()
        self.board_path = _temp_path()
        self.alerts_path = _temp_path()
        self.reopen_log_path = _temp_path()
        self.evidence_path = _temp_path()
        self.timeline_path = _temp_path()
        self.outcomes_path = _temp_path()

    def tearDown(self):
        for p in (self.decisions_path, self.board_path, self.alerts_path, self.reopen_log_path,
                  self.evidence_path, self.timeline_path, self.outcomes_path):
            if os.path.exists(p):
                os.remove(p)

    def _record(self, niche, ladder="ai_saas", score=85.0, price=250):
        ladder_result = {
            "accepted": True, "ladder_score": score, "price": price, "reason": "test",
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

    def _evaluate(self, niche, **kwargs):
        kwargs.setdefault("decisions_path", self.decisions_path)
        kwargs.setdefault("board_path", self.board_path)
        kwargs.setdefault("alerts_path", self.alerts_path)
        kwargs.setdefault("reopen_log_path", self.reopen_log_path)
        kwargs.setdefault("evidence_path", self.evidence_path)
        kwargs.setdefault("timeline_path", self.timeline_path)
        kwargs.setdefault("outcomes_path", self.outcomes_path)
        return growth_engine.evaluate_product_multiplication(niche, **kwargs)

    def test_no_real_decision_is_honestly_none(self):
        self.assertIsNone(self._evaluate("never scored"))

    def test_intelligence_validated_only_by_default(self):
        self._record("a fresh niche")
        result = self._evaluate("a fresh niche")
        self.assertEqual(result["validation_strength"], "intelligence_validated_only")
        self.assertEqual(result["market_memory_sample_size"], 0)

    def test_market_validated_once_a_real_sale_exists(self):
        self._record("a sold niche")
        market_evidence.record_evidence("a sold niche", "closed_sale", {
            "commercial_event": {"platform": "gumroad", "selling_price": 29.0, "season": "summer"},
        }, evidence_path=self.evidence_path)
        result = self._evaluate("a sold niche")
        self.assertEqual(result["validation_strength"], "market_validated")
        self.assertEqual(result["market_memory_sample_size"], 1)

    def test_all_10_named_candidates_are_present(self):
        self._record("a full candidates niche")
        result = self._evaluate("a full candidates niche")
        for candidate in ("premium_version", "enterprise_version", "subscription_version",
                           "bundle_opportunities", "regional_versions", "industry_specific_versions",
                           "language_localized_versions", "api_version", "saas_version", "ai_agent_version"):
            self.assertIn(candidate, result["candidates"])

    def test_the_5_no_real_source_candidates_are_always_honestly_unavailable(self):
        self._record("a no-source candidates niche")
        result = self._evaluate("a no-source candidates niche")
        for candidate in ("enterprise_version", "regional_versions", "language_localized_versions",
                           "industry_specific_versions", "ai_agent_version"):
            self.assertFalse(result["candidates"][candidate]["available"])
            self.assertTrue(result["candidates"][candidate]["reason"])

    def test_subscription_is_a_real_capability_with_no_real_precedent(self):
        self._record("a subscription niche")
        result = self._evaluate("a subscription niche")
        sub = result["candidates"]["subscription_version"]
        self.assertTrue(sub["structurally_available"])
        self.assertFalse(sub["real_precedent"])

    def test_api_and_saas_candidates_report_real_family_adapter_status(self):
        self._record("an api saas niche")
        result = self._evaluate("an api saas niche")
        self.assertIn(result["candidates"]["api_version"]["status"], ("REAL", "NOT YET BUILT"))
        self.assertIn(result["candidates"]["saas_version"]["status"], ("REAL", "NOT YET BUILT"))

    def test_premium_candidate_handles_the_real_unknown_shape_never_crashes(self):
        """Regression: upgrade_potential's real Unknown shape is
        {"answer": "Unknown", "reason": ...}, not {"value": None, ...} —
        a niche with no real ladder must not crash this evaluation."""
        from decision_engine.types import Decision, make_decision_id
        from decision_engine import store
        decision = Decision(
            decision_id=make_decision_id("no ladder niche", "tier4", "2026-07-24T00:00:00"),
            niche="no ladder niche", tier="tier4", decided_at="2026-07-24T00:00:00",
            status="ACCEPTED", ai_ceo_decision="BUILD", opportunity_score=80, opportunity_score_accepted=True,
            reasoning=["test"], evaluation_snapshot={"dimension_scores": {}},
        )
        store.append_decision(decision, path=self.decisions_path)
        result = self._evaluate("no ladder niche")
        self.assertFalse(result["candidates"]["premium_version"]["available"])


class TestEvaluateChannelExpansion(unittest.TestCase):
    def test_real_live_arms_and_catalog_entries_both_present(self):
        result = growth_engine.evaluate_channel_expansion()
        self.assertIsInstance(result["live_arms"], list)
        catalog_names = {c["name"] for c in result["catalog_entries"]}
        for name in ("GPT Store", "Enterprise Sales", "Affiliate Network",
                     "Subscription Platform", "B2B Licensing", "White Label", "Direct Website"):
            self.assertIn(name, catalog_names)

    def test_no_credential_concept_channels_are_honestly_none_not_false(self):
        result = growth_engine.evaluate_channel_expansion()
        by_name = {c["name"]: c for c in result["catalog_entries"]}
        self.assertIsNone(by_name["Enterprise Sales"]["configured"])


class TestBuildGrowthReport(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.decisions_path):
            os.remove(self.decisions_path)

    def test_no_real_decision_is_honestly_none(self):
        self.assertIsNone(growth_engine.build_growth_report("never scored", decisions_path=self.decisions_path))

    def test_real_decision_combines_multiplication_and_channels(self):
        ladder_result = {
            "accepted": True, "ladder_score": 85.0, "price": 250, "reason": "test",
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
        engine.record_ladder_decision("a combined report niche", "ai_saas", ladder_result, decisions_path=self.decisions_path)
        report = growth_engine.build_growth_report("a combined report niche", decisions_path=self.decisions_path)
        self.assertIn("candidates", report)
        self.assertIn("channel_expansion", report)


class TestPortfolioGrowthSummary(unittest.TestCase):
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

    def _record(self, niche, automation_potential=40):
        ladder_result = {
            "accepted": True, "ladder_score": 85.0, "price": 250, "reason": "test",
            "components": {
                "market_demand": 60, "competition_favorability": 70, "profit_potential": 50,
                "recurring_revenue_potential": 90, "reusability": 85, "automation_potential": automation_potential,
            },
            "risk": {"score": 90, "level": "low", "notes": []},
            "confidence": {"score": 55, "level": "متوسطة", "note": "test"},
        }
        engine.record_ladder_decision(niche, "ai_saas", ladder_result, decisions_path=self.decisions_path)

    def test_zero_accepted_reports_honestly(self):
        result = growth_engine.portfolio_growth_summary(
            decisions_path=self.decisions_path, board_path=self.board_path, alerts_path=self.alerts_path,
            reopen_log_path=self.reopen_log_path, evidence_path=self.evidence_path,
        )
        self.assertEqual(result["total_accepted_opportunities"], 0)

    def test_real_automation_potential_is_averaged_across_the_portfolio(self):
        self._record("a", automation_potential=40)
        self._record("b", automation_potential=80)
        result = growth_engine.portfolio_growth_summary(
            decisions_path=self.decisions_path, board_path=self.board_path, alerts_path=self.alerts_path,
            reopen_log_path=self.reopen_log_path, evidence_path=self.evidence_path,
        )
        self.assertEqual(result["total_accepted_opportunities"], 2)
        self.assertEqual(result["automation_potential_average"], 60.0)
        self.assertEqual(result["automation_potential_sample_size"], 2)

    def test_api_saas_family_status_is_real_not_fabricated(self):
        self._record("a")
        result = growth_engine.portfolio_growth_summary(
            decisions_path=self.decisions_path, board_path=self.board_path, alerts_path=self.alerts_path,
            reopen_log_path=self.reopen_log_path, evidence_path=self.evidence_path,
        )
        self.assertIn(result["api_product_family_status"], ("REAL", "NOT YET BUILT"))
        self.assertIn(result["saas_product_family_status"], ("REAL", "NOT YET BUILT"))


class TestProductionCapacitySummary(unittest.TestCase):
    def test_missing_log_reports_honestly(self):
        result = growth_engine.production_capacity_summary(days=30, log_path="/no/such/log.jsonl")
        self.assertEqual(result["real_productions_in_window"], 0)
        self.assertIn("reason", result)

    def test_real_recent_entries_are_counted_old_entries_excluded(self):
        import json
        from datetime import datetime, timedelta

        fd, path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        try:
            recent = (datetime.now() - timedelta(days=1)).isoformat()
            old = (datetime.now() - timedelta(days=90)).isoformat()
            with open(path, "w", encoding="utf-8") as f:
                f.write(json.dumps({"success": True, "timestamp": recent}) + "\n")
                f.write(json.dumps({"success": False, "timestamp": recent}) + "\n")
                f.write(json.dumps({"success": True, "timestamp": old}) + "\n")
            result = growth_engine.production_capacity_summary(days=30, log_path=path)
            self.assertEqual(result["real_productions_in_window"], 2)
            self.assertEqual(result["real_successes_in_window"], 1)
        finally:
            os.remove(path)


class TestGrowthForecast(unittest.TestCase):
    def test_insufficient_real_evidence_never_projects_a_number(self):
        evidence_path = _temp_path()
        try:
            result = growth_engine.growth_forecast(evidence_path=evidence_path)
            self.assertEqual(result["maturity"], "DISCOVERY")
            self.assertIsNone(result["forecast"])
        finally:
            if os.path.exists(evidence_path):
                os.remove(evidence_path)


if __name__ == "__main__":
    unittest.main()
