"""Tests for golden_hunter/ (ADR-060).

Runs with stdlib unittest. Every network-calling function inherited from
market_intelligence_core/competitor_discovery/market_intelligence_engine
is mocked throughout.

    python -m unittest tests.test_golden_hunter -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from golden_hunter import evidence_package, hunt


def _temp_path(suffix=".jsonl"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


class TestNeverTriggersProduction(unittest.TestCase):
    def test_run_hunt_has_no_execute_production_parameter(self):
        import inspect
        sig = inspect.signature(hunt.run_hunt)
        self.assertNotIn("execute_production", sig.parameters)

    def test_module_source_never_contains_execute_production_true(self):
        """Structural guarantee, not a convention: read this module's own
        source and confirm the literal 'execute_production=True' never
        appears anywhere in it."""
        with open(hunt.__file__, encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("execute_production=True", content)
        self.assertIn("execute_production=False", content)


class TestEvidencePackageBuiltFromExistingData(unittest.TestCase):
    def _decision(self, **overrides):
        base = {
            "niche": "a golden hunter test niche", "status": "DEFERRED", "ai_ceo_decision": "WAIT",
            "opportunity_score": 55.0, "external_signal": None,
            "evaluation_snapshot": {
                "scores": {"market_demand": 60, "competition_favorability": 70, "profit_potential": 50},
                "risk": {"score": 90, "level": "low", "notes": []},
                "confidence": {"score": 55, "level": "medium", "note": "x"},
                "demand_pattern": {"pattern": "Evergreen (افتراضي)", "reason": "x"},
                "customer_pain": {"real_evidence": {"github_issues_found": 0, "hn_discussions_found": 0}},
                "competitors": {"total_found": 0, "by_category": {}},
                "pricing": {"recommended_price": "$9", "note": "x"},
                "dimension_scores": {"execution": {"normalized_score": 90, "explanation": "fits book_engine"}},
            },
        }
        base.update(overrides)
        return base

    def test_package_has_all_nine_required_fields(self):
        pkg = evidence_package.build_evidence_package(self._decision())
        for field in ("evidence_package", "demand_evidence", "competition_evidence", "profit_evidence",
                       "confidence", "risk", "estimated_implementation_difficulty",
                       "why_this_opportunity_exists_now", "recommended_action"):
            self.assertIn(field, pkg)

    def test_demand_competition_profit_are_read_not_recomputed(self):
        pkg = evidence_package.build_evidence_package(self._decision())
        self.assertEqual(pkg["demand_evidence"]["score"], 60)
        self.assertEqual(pkg["competition_evidence"]["score"], 70)
        self.assertEqual(pkg["profit_evidence"]["score"], 50)

    def test_high_execution_score_maps_to_low_difficulty(self):
        pkg = evidence_package.build_evidence_package(self._decision())
        self.assertIn("منخفضة", pkg["estimated_implementation_difficulty"]["level"])

    def test_low_execution_score_maps_to_high_difficulty(self):
        d = self._decision()
        d["evaluation_snapshot"]["dimension_scores"]["execution"]["normalized_score"] = 20
        pkg = evidence_package.build_evidence_package(d)
        self.assertIn("عالية", pkg["estimated_implementation_difficulty"]["level"])

    def test_missing_execution_dimension_is_honestly_unknown(self):
        d = self._decision()
        d["evaluation_snapshot"]["dimension_scores"] = {}
        pkg = evidence_package.build_evidence_package(d)
        self.assertEqual(pkg["estimated_implementation_difficulty"]["level"], "Unknown")

    def test_why_now_cites_real_external_signal_when_present(self):
        d = self._decision(external_signal={"source": "github", "stars": 500})
        pkg = evidence_package.build_evidence_package(d)
        self.assertIn("500", pkg["why_this_opportunity_exists_now"])

    def test_why_now_is_honest_when_no_evidence_justifies_timing(self):
        pkg = evidence_package.build_evidence_package(self._decision())
        self.assertIn("لا دليل حقيقي", pkg["why_this_opportunity_exists_now"])

    def test_recommended_action_reflects_existing_status_never_a_new_decision(self):
        accepted_pkg = evidence_package.build_evidence_package(self._decision(status="ACCEPTED", ai_ceo_decision="BUILD"))
        self.assertIn("طابور القرار", accepted_pkg["recommended_action"])
        rejected_pkg = evidence_package.build_evidence_package(self._decision(status="REJECTED", ai_ceo_decision="REJECT"))
        self.assertIn("لا تُتابَع", rejected_pkg["recommended_action"])


class TestRunHuntEndToEnd(unittest.TestCase):
    def setUp(self):
        self.timeline_path = _temp_path()
        self.decisions_path = _temp_path()
        self.analysis_db_path = _temp_path()
        self.competitor_db_path = _temp_path(".json")
        self.pain_db_path = _temp_path(".json")
        self.state_path = _temp_path(".json")
        for p in (
            patch("competitor_discovery._query_hn", return_value=[]),
            patch("competitor_discovery._query_github", return_value=[]),
            patch("market_intelligence_engine._query_hn_discussions", return_value=([], 0)),
            patch("market_intelligence_engine._query_github_issues", return_value=([], 0)),
            patch("competitor_discovery.COMPETITOR_DB_FILE", self.competitor_db_path),
            # Opportunity Rejection Investigation (2026-07-22): run_hunt()
            # calls orch.run_cycle() per signal, which reaches
            # analyze_customer_pain() -- reformulate_pain_query() now makes
            # a real Groq call and _query_stack_overflow_for_pain() a real
            # network call unless mocked.
            patch("market_intelligence_engine.reformulate_pain_query", return_value=("test", "literal_fallback", None)),
            patch("market_intelligence_engine._query_stack_overflow_for_pain", return_value=([], 0)),
            # Evidence Network (ADR-128, 2026-07-25): analyze_customer_pain()
            # now caches to data/pain_evidence_cache.json by default -- same
            # exact real bug class this class's own docstring above already
            # documents for COMPETITOR_DB_FILE. Found live: a real full
            # regression run wrote "hunt test low"/"hunt cap test 0-3"/etc.
            # into the real shared cache before this fix.
            patch("market_intelligence_engine.PAIN_EVIDENCE_DB_FILE", self.pain_db_path),
        ):
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        for p in (self.timeline_path, self.decisions_path, self.analysis_db_path,
                  self.competitor_db_path, self.pain_db_path, self.state_path):
            if os.path.exists(p):
                os.remove(p)

    def test_queue_is_ranked_by_the_existing_real_opportunity_score(self):
        fake_signals = [
            {"niche": "hunt test low", "external_signal": None, "source": "test"},
            {"niche": "hunt test high", "external_signal": {"source": "github", "stars": 5000}, "source": "test"},
        ]
        with patch("real_world_mode.signal_intake.collect_all_real_signals", return_value=fake_signals):
            queue = hunt.run_hunt(
                timeline_path=self.timeline_path, decisions_path=self.decisions_path,
                analysis_db_file=self.analysis_db_path, state_path=self.state_path,
            )
        scores = [item["opportunity_score"] for item in queue]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_max_items_caps_the_queue(self):
        fake_signals = [{"niche": f"hunt cap test {i}", "external_signal": None, "source": "test"} for i in range(4)]
        with patch("real_world_mode.signal_intake.collect_all_real_signals", return_value=fake_signals):
            queue = hunt.run_hunt(
                timeline_path=self.timeline_path, decisions_path=self.decisions_path,
                analysis_db_file=self.analysis_db_path, max_items=2, state_path=self.state_path,
            )
        self.assertLessEqual(len(queue), 2)

    def test_no_signals_gives_an_empty_queue_never_crashes(self):
        with patch("real_world_mode.signal_intake.collect_all_real_signals", return_value=[]):
            queue = hunt.run_hunt(
                timeline_path=self.timeline_path, decisions_path=self.decisions_path,
                analysis_db_file=self.analysis_db_path,
            )
        self.assertEqual(queue, [])


if __name__ == "__main__":
    unittest.main()
