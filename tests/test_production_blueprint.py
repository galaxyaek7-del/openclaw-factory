"""Tests for production_blueprint.py (Global Product Factory, 2026-07-24):
the real 15-component Production Blueprint, 12-pipeline classification,
and 6-state production status, reusing portfolio_engine.py/value_engine.py
directly.

Runs with stdlib unittest. Every function reads only from temp-file-
isolated fixtures -- never the real data/*.jsonl files.

    python -m unittest tests.test_production_blueprint -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import production_blueprint as pb
from decision_engine import engine


def _temp_path():
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(path)
    return path


class TestClassifyProductionPipeline(unittest.TestCase):
    def test_ai_saas_maps_to_saas_pipeline(self):
        decision = {"ladder": "ai_saas", "product_family": None}
        self.assertEqual(pb.classify_production_pipeline(decision), "SaaS")

    def test_kdp_books_maps_to_ebook_pipeline(self):
        decision = {"ladder": "kdp_books", "product_family": None}
        self.assertEqual(pb.classify_production_pipeline(decision), "Ebook")

    def test_notion_family_disambiguates_templates(self):
        decision = {"ladder": None, "product_family": "notion_workspaces"}
        self.assertEqual(pb.classify_production_pipeline(decision), "Notion")

    def test_generic_templates_family_is_honestly_ambiguous(self):
        decision = {"ladder": None, "product_family": "professional_templates"}
        result = pb.classify_production_pipeline(decision)
        self.assertIsNone(result["value"])
        self.assertTrue(result["reason"])


class TestClassifyProductionStatus(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()
        self.timeline_path = _temp_path()
        self.outcomes_path = _temp_path()

    def tearDown(self):
        for p in (self.decisions_path, self.timeline_path, self.outcomes_path):
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

    def test_fresh_accepted_decision_is_ready_to_build(self):
        self._record("a fresh niche")
        result = pb.classify_production_status(
            "a fresh niche", decisions_path=self.decisions_path,
            timeline_path=self.timeline_path, outcomes_path=self.outcomes_path,
        )
        self.assertEqual(result["status"], "READY TO BUILD")

    def test_no_real_decision_is_honestly_none(self):
        result = pb.classify_production_status(
            "never scored", decisions_path=self.decisions_path,
            timeline_path=self.timeline_path, outcomes_path=self.outcomes_path,
        )
        self.assertIsNone(result["status"]["value"])


class TestBuildProductionBlueprint(unittest.TestCase):
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

    def _blueprint(self, niche):
        return pb.build_production_blueprint(
            niche, decisions_path=self.decisions_path, board_path=self.board_path, alerts_path=self.alerts_path,
            reopen_log_path=self.reopen_log_path, evidence_path=self.evidence_path,
            timeline_path=self.timeline_path, outcomes_path=self.outcomes_path,
        )

    def test_no_real_decision_is_honestly_none(self):
        self.assertIsNone(self._blueprint("never scored"))

    def test_all_15_named_components_are_present(self):
        self._record("a full blueprint niche")
        blueprint = self._blueprint("a full blueprint niche")
        for field in ("product_specification", "product_architecture", "customer_persona",
                      "customer_pain_map", "competitive_analysis", "unique_value_proposition",
                      "pricing_strategy", "brand_position", "production_checklist",
                      "required_ai_models", "required_human_review_points", "distribution_channels",
                      "marketing_assets", "sales_funnel", "revenue_projection"):
            self.assertIn(field, blueprint)

    def test_the_2_no_real_source_fields_are_honestly_unavailable(self):
        self._record("a no-source niche")
        blueprint = self._blueprint("a no-source niche")
        self.assertIsNone(blueprint["brand_position"]["value"])
        self.assertIsNone(blueprint["sales_funnel"]["value"])

    def test_product_spec_is_real_for_accepted_decision(self):
        self._record("a spec niche")
        blueprint = self._blueprint("a spec niche")
        self.assertEqual(blueprint["product_specification"]["niche"], "a spec niche")

    def test_pipeline_and_status_are_both_present(self):
        self._record("a pipeline status niche")
        blueprint = self._blueprint("a pipeline status niche")
        self.assertEqual(blueprint["production_pipeline"], "SaaS")
        self.assertEqual(blueprint["production_status"]["status"], "READY TO BUILD")


class TestBuildProductionMissionsBoard(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()
        self.timeline_path = _temp_path()
        self.outcomes_path = _temp_path()

    def tearDown(self):
        for p in (self.decisions_path, self.timeline_path, self.outcomes_path):
            if os.path.exists(p):
                os.remove(p)

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
        board = pb.build_production_missions_board(
            decisions_path=self.decisions_path, timeline_path=self.timeline_path, outcomes_path=self.outcomes_path,
        )
        self.assertEqual(board["total_real_accepted_opportunities"], 0)
        self.assertEqual(sum(board["counts"].values()), 0)

    def test_all_6_named_buckets_present(self):
        board = pb.build_production_missions_board(
            decisions_path=self.decisions_path, timeline_path=self.timeline_path, outcomes_path=self.outcomes_path,
        )
        for status in ("READY TO BUILD", "BUILDING", "QUALITY REVIEW", "READY TO SELL", "LIVE", "LEARNING"):
            self.assertIn(status, board["buckets"])

    def test_fresh_decision_lands_in_ready_to_build_bucket(self):
        self._record("a board niche", 85.0)
        board = pb.build_production_missions_board(
            decisions_path=self.decisions_path, timeline_path=self.timeline_path, outcomes_path=self.outcomes_path,
        )
        self.assertIn("a board niche", board["buckets"]["READY TO BUILD"])
        self.assertEqual(board["total_real_accepted_opportunities"], 1)


if __name__ == "__main__":
    unittest.main()
