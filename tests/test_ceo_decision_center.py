"""Tests for ceo_decision_center.py (Global CEO Decision Center,
2026-07-24): pure orchestration answering the 10 named CEO questions,
plus a real capital allocation snapshot and CEO dashboard -- reuses
investment_pipeline.py/scheduler.py/production_blueprint.py/
competitor_discovery.py/ai_capability.orchestrator.py directly.

Runs with stdlib unittest. Every function reads only from temp-file-
isolated fixtures -- never the real data/*.jsonl files.

    python -m unittest tests.test_ceo_decision_center -v
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

import ceo_decision_center as cdc
from decision_engine import engine


def _temp_path():
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(path)
    return path


def _temp_json_path():
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.remove(path)
    return path


class TestMarketSaturationAndStrength(unittest.TestCase):
    def setUp(self):
        self.db_file = _temp_json_path()

    def tearDown(self):
        if os.path.exists(self.db_file):
            os.remove(self.db_file)

    def test_no_cached_scan_is_honestly_unavailable(self):
        result = cdc._market_saturation_and_strength("never scanned niche", db_file=self.db_file)
        self.assertFalse(result["has_real_data"])
        self.assertTrue(result["reason"])

    def test_real_cached_snapshot_produces_real_scores(self):
        import competitor_discovery as cd
        db = {cd._normalize_key("a scanned niche"): {
            "total_found": 3, "competitors": [], "changes": None,
        }}
        with open(self.db_file, "w", encoding="utf-8") as f:
            json.dump(db, f)
        result = cdc._market_saturation_and_strength("a scanned niche", db_file=self.db_file)
        self.assertTrue(result["has_real_data"])
        self.assertIn("level", result["saturation"])
        self.assertIn("level", result["trajectory"])


class TestAnswerCeoQuestions(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()
        self.board_path = _temp_path()
        self.alerts_path = _temp_path()
        self.reopen_log_path = _temp_path()
        self.evidence_path = _temp_path()
        self.timeline_path = _temp_path()
        self.outcomes_path = _temp_path()
        self.db_file = _temp_json_path()

    def tearDown(self):
        for p in (self.decisions_path, self.board_path, self.alerts_path, self.reopen_log_path,
                  self.evidence_path, self.timeline_path, self.outcomes_path, self.db_file):
            if os.path.exists(p):
                os.remove(p)

    def _record(self, niche, score=85.0):
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

    def _answers(self):
        return cdc.answer_ceo_questions(
            decisions_path=self.decisions_path, board_path=self.board_path, alerts_path=self.alerts_path,
            reopen_log_path=self.reopen_log_path, evidence_path=self.evidence_path,
            timeline_path=self.timeline_path, outcomes_path=self.outcomes_path, db_file=self.db_file,
        )

    def test_all_10_named_questions_are_present(self):
        self._record("a ceo questions niche")
        answers = self._answers()
        for key in (
            "1_most_profitable_opportunity_now", "2_opportunity_to_abandon", "3_deserves_more_investment",
            "4_country_to_prioritize", "5_market_becoming_saturated", "6_niche_becoming_stronger",
            "7_best_ai_model_per_department", "8_highest_real_roi_products", "9_pipelines_wasting_resources",
            "10_next_commercial_experiment",
        ):
            self.assertIn(key, answers)

    def test_empty_factory_reports_honestly(self):
        answers = self._answers()
        self.assertIsNone(answers["1_most_profitable_opportunity_now"])
        self.assertIsNone(answers["2_opportunity_to_abandon"])

    def test_country_question_is_always_deferred(self):
        self._record("a country deferral niche")
        answers = self._answers()
        self.assertIsNone(answers["4_country_to_prioritize"]["value"])
        self.assertTrue(answers["4_country_to_prioritize"]["reason"])

    def test_most_profitable_reflects_real_top_priority(self):
        self._record("low priority ceo", 40.0)
        self._record("high priority ceo", 95.0)
        answers = self._answers()
        self.assertEqual(answers["1_most_profitable_opportunity_now"]["niche"], "high priority ceo")


class TestCapitalAllocationSnapshot(unittest.TestCase):
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

    def test_all_10_named_functions_present(self):
        snapshot = cdc.capital_allocation_snapshot(
            decisions_path=self.decisions_path, board_path=self.board_path, alerts_path=self.alerts_path,
            reopen_log_path=self.reopen_log_path, evidence_path=self.evidence_path,
        )
        for name in ("Research", "Production", "Automation", "Marketing", "Publishing", "Sales",
                     "Commercial Intelligence", "China Division", "Enterprise Division", "Premium Products"):
            self.assertIn(name, snapshot)

    def test_china_division_is_always_honestly_zero(self):
        snapshot = cdc.capital_allocation_snapshot(
            decisions_path=self.decisions_path, board_path=self.board_path, alerts_path=self.alerts_path,
            reopen_log_path=self.reopen_log_path, evidence_path=self.evidence_path,
        )
        self.assertEqual(snapshot["China Division"]["count"], 0)

    def test_never_reports_a_fabricated_dollar_amount(self):
        snapshot = cdc.capital_allocation_snapshot(
            decisions_path=self.decisions_path, board_path=self.board_path, alerts_path=self.alerts_path,
            reopen_log_path=self.reopen_log_path, evidence_path=self.evidence_path,
        )
        for name, entry in snapshot.items():
            if name == "evaluated_at":
                continue
            self.assertNotIn("dollars", str(entry).lower())
            self.assertNotIn("budget_usd", entry if isinstance(entry, dict) else {})


class TestCeoDashboard(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()
        self.board_path = _temp_path()
        self.alerts_path = _temp_path()
        self.reopen_log_path = _temp_path()
        self.evidence_path = _temp_path()
        self.timeline_path = _temp_path()
        self.outcomes_path = _temp_path()
        self.db_file = _temp_json_path()

    def tearDown(self):
        for p in (self.decisions_path, self.board_path, self.alerts_path, self.reopen_log_path,
                  self.evidence_path, self.timeline_path, self.outcomes_path, self.db_file):
            if os.path.exists(p):
                os.remove(p)

    def _dashboard(self):
        return cdc.ceo_dashboard(
            decisions_path=self.decisions_path, board_path=self.board_path, alerts_path=self.alerts_path,
            reopen_log_path=self.reopen_log_path, evidence_path=self.evidence_path,
            timeline_path=self.timeline_path, outcomes_path=self.outcomes_path, db_file=self.db_file,
        )

    def test_all_8_named_fields_present(self):
        result = self._dashboard()
        for field in ("company_health", "capital_allocation", "growth_rate", "revenue_trend",
                      "top_opportunities", "top_risks", "current_strategic_priority", "next_executive_decision"):
            self.assertIn(field, result)

    def test_company_health_is_not_re_derived(self):
        result = self._dashboard()
        self.assertIsNone(result["company_health"]["value"])
        self.assertTrue(result["company_health"]["reason"])


if __name__ == "__main__":
    unittest.main()
