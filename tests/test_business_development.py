import json
import os
import tempfile
import unittest
from unittest.mock import patch

import business_development as bd

_FAKE_REGISTRY = {
    "real_program": {
        "display_name": "Real Program Platform",
        "program_confirmed": True, "joinable_by_small_business": True, "strategic_fit": True,
        "opportunities": {
            "affiliate": {"status": "REAL", "commission": "20%", "source": "https://example.com/affiliate"},
            "api_integration": {"status": "REAL", "source": "https://example.com/api"},
        },
        "evidence": ["https://example.com/affiliate"],
    },
    "no_program": {
        "display_name": "No Program Platform",
        "program_confirmed": False, "joinable_by_small_business": False, "strategic_fit": False,
        "opportunities": {},
        "evidence": [],
    },
}


class TestBusinessDevelopment(unittest.TestCase):
    def test_advance_partnership_rejects_unknown_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "pipeline.jsonl")
            with self.assertRaises(ValueError):
                bd.advance_partnership("x", "NOT_A_REAL_STAGE", pipeline_path=path)

    def test_advance_partnership_appends_real_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "pipeline.jsonl")
            bd.advance_partnership("amazon_associates", "PREPARATION", note="real product data live", pipeline_path=path)
            with open(path, encoding="utf-8") as f:
                lines = f.readlines()
            self.assertEqual(len(lines), 1)
            record = json.loads(lines[0])
            self.assertEqual(record["stage"], "PREPARATION")

    def test_evaluate_platform_unknown_raises(self):
        with patch.object(bd, "PLATFORM_REGISTRY", _FAKE_REGISTRY):
            with self.assertRaises(ValueError):
                bd.evaluate_platform("does_not_exist")

    def test_evaluate_platform_defaults_to_discovery_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "pipeline.jsonl")
            with patch.object(bd, "PLATFORM_REGISTRY", _FAKE_REGISTRY):
                result = bd.evaluate_platform("real_program", pipeline_path=path)
                self.assertEqual(result["current_stage"], "DISCOVERY")

    def test_evaluate_platform_reflects_real_pipeline_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "pipeline.jsonl")
            bd.advance_partnership("real_program", "NEGOTIATION", pipeline_path=path)
            with patch.object(bd, "PLATFORM_REGISTRY", _FAKE_REGISTRY):
                result = bd.evaluate_platform("real_program", pipeline_path=path)
                self.assertEqual(result["current_stage"], "NEGOTIATION")

    def test_unconfirmed_opportunity_types_are_honestly_discovery(self):
        with patch.object(bd, "PLATFORM_REGISTRY", _FAKE_REGISTRY):
            result = bd.evaluate_platform("no_program")
            for opp_type in bd.OPPORTUNITY_TYPES:
                self.assertEqual(result["opportunities"][opp_type]["status"], "DISCOVERY")

    def test_score_ranks_confirmed_program_above_no_program(self):
        with patch.object(bd, "PLATFORM_REGISTRY", _FAKE_REGISTRY):
            top = bd.top_partnership_opportunities(n=2)
            self.assertEqual(top[0]["platform"], "Real Program Platform")
            self.assertGreater(top[0]["score"], top[1]["score"])

    def test_top_affiliate_excludes_platforms_with_no_real_affiliate_program(self):
        with patch.object(bd, "PLATFORM_REGISTRY", _FAKE_REGISTRY):
            top = bd.top_affiliate_opportunities()
            self.assertEqual(len(top), 1)
            self.assertEqual(top[0]["platform"], "Real Program Platform")

    def test_pipeline_board_covers_all_stages(self):
        with patch.object(bd, "PLATFORM_REGISTRY", _FAKE_REGISTRY):
            board = bd.build_partnership_pipeline_board(pipeline_path="C:/definitely/not/real.jsonl")
            for stage in bd.STAGES:
                self.assertIn(stage, board)
            self.assertEqual(len(board["DISCOVERY"]), 2)

    def test_never_fabricates_expected_revenue_when_no_signal(self):
        with patch.object(bd, "PLATFORM_REGISTRY", _FAKE_REGISTRY):
            result = bd.evaluate_platform("no_program")
            self.assertIn("Unknown", result["expected_recurring_revenue"])

    def test_dashboard_computes_evaluations_exactly_once(self):
        with patch.object(bd, "PLATFORM_REGISTRY", _FAKE_REGISTRY), \
             patch.object(bd, "_all_evaluations", wraps=bd._all_evaluations) as mock_evals:
            bd.build_business_development_dashboard()
            self.assertEqual(mock_evals.call_count, 1)

    def test_dashboard_excludes_discovery_only_from_affiliate_top10(self):
        with patch.object(bd, "PLATFORM_REGISTRY", _FAKE_REGISTRY):
            dashboard = bd.build_business_development_dashboard()
            self.assertEqual(len(dashboard["top_10_affiliate_opportunities"]), 1)

    def test_real_registry_loads_and_evaluates_without_error(self):
        # Real, non-mocked call against the actual researched registry --
        # proves every entry's shape is internally consistent.
        dashboard = bd.build_business_development_dashboard()
        self.assertGreaterEqual(dashboard["total_platforms_evaluated"], 15)
        for platform_eval in dashboard["top_20_partnership_opportunities"]:
            self.assertIn("evidence", platform_eval)


class TestSection6AttributionFields(unittest.TestCase):
    """Global Commercial Revenue OS, Section 6 (ADR-202, 2026-08-07)."""

    def test_amazon_has_real_researched_values(self):
        result = bd.evaluate_platform("amazon")
        self.assertIn("24-hour", result["cookie_attribution_rules"])
        self.assertNotIn("not yet researched", result["payment_method"])

    def test_platform_with_no_real_research_defaults_honestly(self):
        with patch.object(bd, "PLATFORM_REGISTRY", _FAKE_REGISTRY):
            result = bd.evaluate_platform("real_program")
            self.assertIn("not yet researched", result["cookie_attribution_rules"])
            self.assertIn("not yet researched", result["geographic_restrictions"])
            self.assertIn("not yet researched", result["minimum_payout"])

    def test_confidence_field_present_and_honest(self):
        result = bd.evaluate_platform("amazon")
        self.assertIn("confidence", result)


class TestSection7StageVocabulary(unittest.TestCase):
    """Global Commercial Revenue OS, Section 7 (ADR-202, 2026-08-07)."""

    def test_rejected_and_archived_are_valid_stages(self):
        self.assertIn("REJECTED", bd.STAGES)
        self.assertIn("ARCHIVED", bd.STAGES)

    def test_advance_partnership_accepts_new_terminal_stages(self):
        path = os.path.join(tempfile.mkdtemp(), "pipeline.jsonl")
        record = bd.advance_partnership("gumroad", "REJECTED", pipeline_path=path)
        self.assertEqual(record["stage"], "REJECTED")

    def test_v2_board_never_loses_real_entries(self):
        with patch.object(bd, "PLATFORM_REGISTRY", _FAKE_REGISTRY):
            path = os.path.join(tempfile.mkdtemp(), "pipeline.jsonl")
            bd.advance_partnership("real_program", "ACTIVE", pipeline_path=path)
            v2 = bd.build_partnership_pipeline_board_v2(pipeline_path=path)
            self.assertEqual(len(v2["board"]["Active"]), 1)

    def test_v2_board_covers_every_real_stage(self):
        v2 = bd.build_partnership_pipeline_board_v2()
        mapped_real_stages = set(bd.STAGE_V2_MAPPING.keys())
        self.assertEqual(mapped_real_stages, set(bd.STAGES))


if __name__ == "__main__":
    unittest.main()
