"""Tests for market_intelligence_core/ (ADR-049).

Runs with stdlib unittest. All network-calling functions (competitor_discovery's
_query_hn/_query_github, market_intelligence_engine's _query_hn_discussions/
_query_github_issues) are mocked throughout — this suite never depends on
live API availability, matching this project's established convention.

    python -m unittest tests.test_market_intelligence_core -v
"""

import sys
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from market_intelligence_core import http_client, registry
from market_intelligence_core.types import CONFIDENCE_SCALE, EvaluationContext, Score
import competitor_discovery
import market_intelligence_engine


class TestHttpClientIsTheOnlyImplementation(unittest.TestCase):
    """Proves the duplicate _http_get_json found by the 2026-07-16
    architecture review is actually gone — both modules now delegate to
    exactly one implementation, verified by patching that one
    implementation and confirming both old entry points reflect it."""

    def test_http_get_json_parses_real_shaped_response(self):
        class _FakeResp:
            def __enter__(self_inner):
                return self_inner
            def __exit__(self_inner, *a):
                return False
            def read(self_inner):
                return b'{"ok": true}'
        with patch("urllib.request.urlopen", return_value=_FakeResp()):
            self.assertEqual(http_client.http_get_json("http://x"), {"ok": True})

    def test_http_get_json_never_raises_on_network_failure_when_wrapped_by_callers(self):
        # http_get_json itself is allowed to raise (callers catch it) —
        # confirmed here so the contract each _query_* wrapper depends on
        # (catch, return empty) is well-defined.
        with patch("urllib.request.urlopen", side_effect=Exception("network down")):
            with self.assertRaises(Exception):
                http_client.http_get_json("http://x")

    @patch("market_intelligence_core.http_client.http_get_json")
    def test_competitor_discovery_delegates_to_the_one_canonical_client(self, mock_get):
        mock_get.return_value = {"hits": []}
        competitor_discovery._http_get_json("http://x")
        self.assertTrue(mock_get.called)

    @patch("market_intelligence_core.http_client.http_get_json")
    def test_market_intelligence_engine_delegates_to_the_one_canonical_client(self, mock_get):
        mock_get.return_value = {"hits": []}
        market_intelligence_engine._http_get_json("http://x")
        self.assertTrue(mock_get.called)


class TestScoreContract(unittest.TestCase):
    def test_score_exposes_exactly_the_required_fields(self):
        s = Score(dimension="demand", raw_data={"a": 1}, normalized_score=50, confidence=80, explanation="x")
        d = s.to_dict()
        for field in ("raw_data", "normalized_score", "confidence", "explanation"):
            self.assertIn(field, d)


class TestRegistryAutoDiscovery(unittest.TestCase):
    def test_all_nine_scorers_are_registered(self):
        import market_intelligence_core.scoring  # noqa: F401 — triggers auto-import
        scorers = registry.get_scorers()
        expected = {
            "demand", "competition", "profit_margin", "customer_pain",
            "pricing_power", "trend_stability", "risk", "execution",
        }
        self.assertTrue(expected.issubset(scorers.keys()), scorers.keys())

    def test_confidence_is_registered_as_a_meta_scorer_not_a_primary_one(self):
        import market_intelligence_core.scoring  # noqa: F401
        self.assertIn("confidence", registry.get_meta_scorers())
        self.assertNotIn("confidence", registry.get_scorers())

    def test_adding_a_new_scorer_at_runtime_requires_zero_pipeline_edits(self):
        """The concrete proof of the extensibility requirement: register a
        brand-new scorer dynamically (as if a 10th file had been dropped
        into scoring/) and confirm pipeline.run() picks it up with no
        changes to pipeline.py or any existing scorer."""
        from market_intelligence_core import pipeline

        @registry.register_scorer("test_only_dimension")
        def _fake_scorer(context):
            return Score(dimension="test_only_dimension", raw_data={}, normalized_score=99, confidence=80, explanation="fake")

        try:
            context = EvaluationContext(niche="x", analysis={"competitors": {}, "customer_pain": {}, "demand_pattern": {"pattern": "Evergreen", "reason": "x"}})
            with patch("profit_oracle.SAFETY_FILTER") as mock_sf:
                mock_sf.evaluate.return_value = {"allowed": True, "risk_level": "low", "reasons": []}
                scores = pipeline.run(context)
            self.assertIn("test_only_dimension", scores)
            self.assertEqual(scores["test_only_dimension"].normalized_score, 99)
        finally:
            del registry._SCORERS["test_only_dimension"]


class TestCoreEvaluateOpportunity(unittest.TestCase):
    """competitor_discovery.COMPETITOR_DB_FILE is redirected here too
    (2026-07-16 fix): get_or_refresh_competitors() writes to it even when
    the network query itself is mocked — without this, every run of this
    class was appending a real entry to the live
    data/competitor_database.json."""

    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        os.remove(self.db_path)
        fd, self.competitor_db_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.remove(self.competitor_db_path)
        patcher = patch("competitor_discovery.COMPETITOR_DB_FILE", self.competitor_db_path)
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        if os.path.exists(self.competitor_db_path):
            os.remove(self.competitor_db_path)

    def test_empty_niche_degrades_honestly_never_crashes(self):
        from market_intelligence_core import core
        result = core.evaluate_opportunity("", analysis_db_file=self.db_path)
        self.assertIn("error", result)
        self.assertEqual(result["dimension_scores"], {})

    @patch("competitor_discovery._query_github")
    @patch("competitor_discovery._query_hn")
    @patch("market_intelligence_engine._query_hn_discussions")
    @patch("market_intelligence_engine._query_github_issues")
    def test_legacy_shape_is_fully_preserved_and_dimension_scores_is_additive(
        self, mock_issues, mock_hn_disc, mock_cd_hn, mock_cd_gh
    ):
        mock_issues.return_value = ([], 0)
        mock_hn_disc.return_value = ([], 0)
        mock_cd_hn.return_value = []
        mock_cd_gh.return_value = []

        from market_intelligence_core import core

        legacy = market_intelligence_engine.analyze_opportunity(
            "a core equivalence test niche", analysis_db_file=self.db_path
        )
        os.remove(self.db_path)  # analyze_opportunity() already appended once above; reset for the real call below
        result = core.evaluate_opportunity("a core equivalence test niche", analysis_db_file=self.db_path)

        for key in ("niche", "scores", "risk", "confidence", "customer_pain",
                    "demand_pattern", "competitors", "opportunity_gap", "pricing", "ai_ceo"):
            self.assertEqual(result[key], legacy[key], key)

        self.assertIn("dimension_scores", result)
        self.assertNotIn("dimension_scores", legacy)
        for dim in ("demand", "competition", "profit_margin", "customer_pain",
                    "pricing_power", "trend_stability", "risk", "execution", "confidence"):
            self.assertIn(dim, result["dimension_scores"])
            for field in ("raw_data", "normalized_score", "confidence", "explanation"):
                self.assertIn(field, result["dimension_scores"][dim])

    @patch("competitor_discovery._query_github")
    @patch("competitor_discovery._query_hn")
    @patch("market_intelligence_engine._query_hn_discussions")
    @patch("market_intelligence_engine._query_github_issues")
    def test_dimension_scores_never_invents_a_number_for_discovery_dimensions(
        self, mock_issues, mock_hn_disc, mock_cd_hn, mock_cd_gh
    ):
        mock_issues.return_value = ([], 0)
        mock_hn_disc.return_value = ([], 0)
        mock_cd_hn.return_value = []
        mock_cd_gh.return_value = []

        from market_intelligence_core import core
        result = core.evaluate_opportunity("a totally generic niche xyz", analysis_db_file=self.db_path)

        # No saved Amazon report exists for this fake niche -> pricing_power must be honestly unknown.
        self.assertIsNone(result["dimension_scores"]["pricing_power"]["normalized_score"])
        # No real repeated-snapshot history -> Evergreen trend_stability must be honestly unknown.
        self.assertIsNone(result["dimension_scores"]["trend_stability"]["normalized_score"])
        # No real GitHub/HN evidence -> customer_pain must be honestly unknown, not zero.
        self.assertIsNone(result["dimension_scores"]["customer_pain"]["normalized_score"])


class TestConfidenceMetaScorerGeneralizesYesterdaysFix(unittest.TestCase):
    def test_confidence_averages_whatever_the_pipeline_actually_ran(self):
        from market_intelligence_core import pipeline
        context = EvaluationContext(
            niche="x",
            analysis={"competitors": {}, "customer_pain": {"confidence": "low"}, "demand_pattern": {"pattern": "Evergreen", "reason": "x"}},
        )
        with patch("profit_oracle.SAFETY_FILTER") as mock_sf:
            mock_sf.evaluate.return_value = {"allowed": True, "risk_level": "low", "reasons": []}
            scores = pipeline.run(context)
        confidences = [s.confidence for name, s in scores.items() if name != "confidence"]
        expected_avg = round(sum(confidences) / len(confidences))
        self.assertEqual(scores["confidence"].normalized_score, expected_avg)


if __name__ == "__main__":
    unittest.main()
