"""Tests for market_intelligence_engine.py (ADR-043).

Runs with stdlib unittest. All network-calling functions
(_query_github_issues, _query_hn_discussions, and competitor_discovery's
_query_hn/_query_github) are mocked throughout — this suite never depends
on live API availability.

    python -m unittest tests.test_market_intelligence_engine -v
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import market_intelligence_engine as mie


class TestCustomerPainIntelligence(unittest.TestCase):
    """Opportunity Rejection Investigation (2026-07-22): every test here
    mocks reformulate_pain_query() to return the niche verbatim
    ("literal_fallback"), so this class keeps testing the existing GitHub/
    HN/Stack-Overflow aggregation logic in isolation from the new
    reformulation step (covered separately in TestReformulatePainQuery
    below) -- and never depends on live Groq availability."""

    def setUp(self):
        patcher = patch("market_intelligence_engine.reformulate_pain_query", return_value=("niche", "literal_fallback", None))
        self.mock_reformulate = patcher.start()
        self.addCleanup(patcher.stop)
        so_patcher = patch("market_intelligence_engine._query_stack_overflow_for_pain", return_value=([], 0))
        self.mock_so = so_patcher.start()
        self.addCleanup(so_patcher.stop)
        # Evidence Network (ADR-128, 2026-07-25): analyze_customer_pain()
        # now caches to data/pain_evidence_cache.json by default -- every
        # test here calls it without a db_file override, which would
        # otherwise write real fixture entries ("niche", "a totally
        # obscure niche") into the real shared cache on every test run.
        # Redirects the module-level default path for this whole class,
        # same isolation technique test_automation_systems_e2e.py already
        # uses for other real shared paths (patch.object on the module
        # constant, not a per-call-site db_file argument).
        import tempfile
        import os
        self.tmp_pain_db = tempfile.mktemp(suffix=".json")
        db_patcher = patch.object(mie, "PAIN_EVIDENCE_DB_FILE", self.tmp_pain_db)
        db_patcher.start()
        self.addCleanup(db_patcher.stop)
        self.addCleanup(lambda: os.path.exists(self.tmp_pain_db) and os.remove(self.tmp_pain_db))

    @patch("market_intelligence_engine._query_hn_discussions")
    @patch("market_intelligence_engine._query_github_issues")
    def test_no_real_results_gives_no_score_not_a_guess(self, mock_issues, mock_hn):
        mock_issues.return_value = ([], 0)
        mock_hn.return_value = ([], 0)
        result = mie.analyze_customer_pain("a totally obscure niche")
        self.assertIsNone(result["pain_score"])
        self.assertEqual(result["confidence"], "low")

    @patch("market_intelligence_engine._query_hn_discussions")
    @patch("market_intelligence_engine._query_github_issues")
    def test_real_pain_language_increases_score(self, mock_issues, mock_hn):
        mock_hn.return_value = ([], 0)
        mock_issues.return_value = (
            [{"title": "This is so frustrating, wish there was a tool", "body": "", "reactions": {"total_count": 10}, "comments": 5}],
            50,
        )
        result = mie.analyze_customer_pain("niche")
        self.assertGreater(result["real_evidence"]["pain_language_hits"], 0)
        self.assertIsNotNone(result["pain_score"])

    @patch("market_intelligence_engine._query_hn_discussions")
    @patch("market_intelligence_engine._query_github_issues")
    def test_willingness_to_pay_language_is_detected(self, mock_issues, mock_hn):
        mock_hn.return_value = ([], 0)
        mock_issues.return_value = (
            [{"title": "shut up and take my money for this", "body": "", "reactions": {"total_count": 1}, "comments": 1}],
            10,
        )
        result = mie.analyze_customer_pain("niche")
        self.assertGreater(result["real_evidence"]["willingness_to_pay_hits"], 0)

    @patch("market_intelligence_engine._query_hn_discussions")
    @patch("market_intelligence_engine._query_github_issues")
    def test_reddit_and_product_hunt_always_explicitly_unknown(self, mock_issues, mock_hn):
        mock_issues.return_value = ([], 0)
        mock_hn.return_value = ([], 0)
        result = mie.analyze_customer_pain("niche")
        self.assertIn("reddit", result["unknown_sources"])
        self.assertIn("product_hunt", result["unknown_sources"])

    @patch("market_intelligence_engine._query_hn_discussions")
    @patch("market_intelligence_engine._query_github_issues")
    def test_stack_overflow_is_a_real_third_source_not_just_github_hn(self, mock_issues, mock_hn):
        mock_issues.return_value = ([], 0)
        mock_hn.return_value = ([], 0)
        self.mock_so.return_value = (
            [{"title": "so frustrating, no good solution for this", "view_count": 500, "answer_count": 3, "score": 2}],
            20,
        )
        result = mie.analyze_customer_pain("niche")
        self.assertEqual(result["real_evidence"]["stack_overflow_found"], 1)
        self.assertEqual(result["real_evidence"]["stack_overflow_total"], 20)
        self.assertIsNotNone(result["pain_score"])
        self.assertGreater(result["real_evidence"]["pain_language_hits"], 0)

    @patch("market_intelligence_engine._query_hn_discussions")
    @patch("market_intelligence_engine._query_github_issues")
    def test_query_used_and_method_are_always_reported(self, mock_issues, mock_hn):
        """Full explainability (mission point 4): every analysis states
        exactly what was searched and how that query was produced."""
        mock_issues.return_value = ([], 0)
        mock_hn.return_value = ([], 0)
        result = mie.analyze_customer_pain("niche")
        self.assertEqual(result["query_used"], "niche")
        self.assertEqual(result["query_method"], "literal_fallback")
        self.assertIn("query_note", result)


class TestReformulatePainQuery(unittest.TestCase):
    """Opportunity Rejection Investigation (2026-07-22): the actual fix for
    the confirmed root cause -- literal branded product names never match
    how a real person describes a problem. Never fabricates a query;
    degrades honestly through 3 named methods."""

    @patch("book_generator.groq_chat")
    def test_groq_semantic_reformulation_used_when_available(self, mock_groq):
        mock_groq.return_value = "freelance pentester manual reporting is slow and error-prone"
        query, method, note = mie.reformulate_pain_query("AI Agent Blueprint for Freelance Security Pentesting Automation")
        self.assertEqual(method, "groq_semantic")
        self.assertIn("pentester", query)
        self.assertIsNone(note)

    @patch("book_generator.groq_chat")
    def test_falls_back_to_deterministic_stripping_when_groq_fails(self, mock_groq):
        mock_groq.side_effect = RuntimeError("فشل استدعاء Groq بعد 3 محاولات: no key")
        query, method, note = mie.reformulate_pain_query("AI Agent Blueprint for Freelance Security Pentesting Automation")
        self.assertEqual(method, "deterministic_fallback")
        self.assertNotIn("blueprint", query.lower())
        self.assertIn("freelance security pentesting", query)
        self.assertIsNotNone(note)

    @patch("book_generator.groq_chat")
    def test_falls_back_to_deterministic_stripping_when_groq_returns_junk(self, mock_groq):
        mock_groq.return_value = "ok"  # too short to be a real reformulation
        query, method, note = mie.reformulate_pain_query("AI Agent Blueprint for SOC 2 Compliance Automation")
        self.assertEqual(method, "deterministic_fallback")

    def test_deterministic_fallback_strips_template_words_never_invents_meaning(self):
        query = mie._deterministic_query_fallback("AI Agent Blueprint for EU AI Act Compliance Audit Logging")
        self.assertNotIn("blueprint", query)
        self.assertIn("eu ai act compliance audit logging", query)

    def test_empty_niche_degrades_honestly(self):
        query, method, note = mie.reformulate_pain_query("")
        self.assertEqual(method, "literal_fallback")

    @patch("book_generator.groq_chat")
    def test_never_raises_even_on_unexpected_groq_error_shape(self, mock_groq):
        mock_groq.side_effect = Exception("unexpected")
        query, method, note = mie.reformulate_pain_query("some niche")
        self.assertEqual(method, "deterministic_fallback")
        self.assertIsInstance(query, str)


class TestLowLevelPainQueries(unittest.TestCase):
    @patch("market_intelligence_engine._http_get_json")
    def test_query_github_issues_never_raises_on_network_failure(self, mock_get):
        mock_get.side_effect = Exception("network down")
        items, total = mie._query_github_issues("x")
        self.assertEqual(items, [])
        self.assertEqual(total, 0)

    @patch("market_intelligence_engine._http_get_json")
    def test_query_hn_discussions_never_raises_on_network_failure(self, mock_get):
        mock_get.side_effect = Exception("network down")
        items, total = mie._query_hn_discussions("x")
        self.assertEqual(items, [])
        self.assertEqual(total, 0)


class TestDemandPatternClassification(unittest.TestCase):
    def test_seasonal_keyword_match_is_real_not_guessed(self):
        from datetime import datetime
        result = mie.classify_demand_pattern("back to school planner", now=datetime(2026, 8, 1))
        self.assertEqual(result["pattern"], "Seasonal")
        self.assertEqual(result["confidence"], "high")

    def test_no_seasonal_match_is_evergreen_with_honest_unknown_for_trend_direction(self):
        result = mie.classify_demand_pattern("a totally generic niche")
        self.assertIn("Evergreen", result["pattern"])
        self.assertIn("Unknown", result["pattern"])
        self.assertIn("Exploding/Declining", result["reason"])


class TestAiCeoDecision(unittest.TestCase):
    def _base(self, **overrides):
        base = {
            "risk": {"level": "low", "notes": []},
            "scores": {"competition": 70},
            "customer_pain": {"pain_score": 40, "confidence": "low"},
            "opportunity_gap": 50,
            "confidence": {"score": 60},
        }
        base.update(overrides)
        return base

    def test_high_risk_always_rejects_regardless_of_everything_else(self):
        analysis = self._base(risk={"level": "blocked", "notes": ["safety_filter flagged it"]}, opportunity_gap=95)
        result = mie.ai_ceo_decision(analysis)
        self.assertEqual(result["decision"], "REJECT")
        self.assertIn("safety_filter", result["evidence"][0])

    def test_low_overall_confidence_waits_instead_of_guessing(self):
        analysis = self._base(confidence={"score": 10}, customer_pain={"pain_score": 90, "confidence": "low"})
        result = mie.ai_ceo_decision(analysis)
        self.assertEqual(result["decision"], "WAIT")

    def test_pain_confidence_uses_the_same_numeric_scale_as_profit_oracle_confidence(self):
        """Regression test for a self-audit finding (2026-07-15): pain's
        'medium' confidence was previously mapped to 100 (the theoretical
        ceiling), which could single-handedly drag a genuinely low overall
        confidence above the WAIT gate. 'medium' must map to a moderate
        value (55, matching profit_oracle._score_confidence()'s own scale),
        not the maximum."""
        # confidence.score=10 (very low) + pain 'medium' must NOT be enough
        # to escape the < 40 WAIT gate on its own.
        analysis = self._base(confidence={"score": 10}, customer_pain={"pain_score": 50, "confidence": "medium"}, opportunity_gap=80)
        result = mie.ai_ceo_decision(analysis)
        self.assertEqual(result["decision"], "WAIT", f"avg confidence should stay below 40, got: {result}")
        self.assertLess(result["confidence_gate"], 40)

    def test_high_opportunity_gap_and_real_pain_builds(self):
        analysis = self._base(opportunity_gap=80, customer_pain={"pain_score": 70, "confidence": "medium"}, confidence={"score": 70})
        result = mie.ai_ceo_decision(analysis)
        self.assertEqual(result["decision"], "BUILD")

    def test_very_high_competition_pivots(self):
        analysis = self._base(scores={"competition": 15}, confidence={"score": 70})
        result = mie.ai_ceo_decision(analysis)
        self.assertEqual(result["decision"], "PIVOT")

    def test_moderate_gap_improves(self):
        analysis = self._base(opportunity_gap=50, confidence={"score": 70})
        result = mie.ai_ceo_decision(analysis)
        self.assertEqual(result["decision"], "IMPROVE")

    def test_every_decision_cites_real_evidence_not_just_a_number(self):
        for analysis in [
            self._base(risk={"level": "blocked", "notes": ["x"]}),
            self._base(confidence={"score": 5}),
            self._base(opportunity_gap=80, customer_pain={"pain_score": 70, "confidence": "medium"}, confidence={"score": 70}),
        ]:
            result = mie.ai_ceo_decision(analysis)
            self.assertTrue(len(result["evidence"]) > 0)
            self.assertTrue(all(isinstance(e, str) and len(e) > 10 for e in result["evidence"]))

    def test_decision_is_always_one_of_the_five_valid_values(self):
        analysis = self._base()
        result = mie.ai_ceo_decision(analysis)
        self.assertIn(result["decision"], mie.DECISIONS)


class TestAnalyzeOpportunityOrchestration(unittest.TestCase):
    """The one integrated entry point — every network-calling function
    across both modules is mocked, so this never makes a real call.
    analysis_db_file is always redirected to a temp path — this must never
    write into the real data/market_intelligence_analyses.jsonl.

    competitor_discovery.COMPETITOR_DB_FILE is also redirected (2026-07-16
    fix): get_or_refresh_competitors() still calls save_database() even
    when the network query is mocked to return [] — without this, every
    run of this test class was silently appending a real (if empty)
    result to the live data/competitor_database.json, confirmed by
    finding this suite's own niche strings inside that file."""

    def setUp(self):
        import tempfile
        fd, self.db_path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        os.remove(self.db_path)
        fd, self.competitor_db_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.remove(self.competitor_db_path)
        patcher = patch("competitor_discovery.COMPETITOR_DB_FILE", self.competitor_db_path)
        patcher.start()
        self.addCleanup(patcher.stop)
        # Opportunity Rejection Investigation (2026-07-22): reformulate_pain_
        # query() now makes a real Groq call and _query_stack_overflow_for_pain()
        # a real network call unless mocked -- both redirected here so this
        # class's own "every network-calling function is mocked" guarantee
        # (see class docstring) still holds.
        reformulate_patcher = patch("market_intelligence_engine.reformulate_pain_query", return_value=("test niche xyz", "literal_fallback", None))
        reformulate_patcher.start()
        self.addCleanup(reformulate_patcher.stop)
        so_patcher = patch("market_intelligence_engine._query_stack_overflow_for_pain", return_value=([], 0))
        so_patcher.start()
        self.addCleanup(so_patcher.stop)
        # Evidence Network (ADR-128, 2026-07-25): analyze_opportunity()
        # calls analyze_customer_pain() internally, which now caches to
        # data/pain_evidence_cache.json by default -- same exact real bug
        # class this class's own docstring already documents fixing once
        # for competitor_discovery.COMPETITOR_DB_FILE above. Redirected
        # here for the same reason: without this, every run of this class
        # would silently write this suite's fixture niches into the real
        # shared pain-evidence cache.
        fd, self.pain_db_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.remove(self.pain_db_path)
        pain_patcher = patch("market_intelligence_engine.PAIN_EVIDENCE_DB_FILE", self.pain_db_path)
        pain_patcher.start()
        self.addCleanup(pain_patcher.stop)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        if os.path.exists(self.competitor_db_path):
            os.remove(self.competitor_db_path)
        if os.path.exists(self.pain_db_path):
            os.remove(self.pain_db_path)

    def test_empty_niche_degrades_honestly_never_crashes(self):
        """Regression test for a self-audit finding (2026-07-15):
        analyze_opportunity('') used to raise an uncaught ValueError from
        profit_oracle — every other function here degrades (None/Unknown)
        instead of crashing; this one must too."""
        for bad_niche in ('', '   ', None):
            result = mie.analyze_opportunity(bad_niche, analysis_db_file=self.db_path)
            self.assertIn("error", result)
            self.assertEqual(result["ai_ceo"]["decision"], "WAIT")

    @patch("competitor_discovery._query_github")
    @patch("competitor_discovery._query_hn")
    @patch("market_intelligence_engine._query_hn_discussions")
    @patch("market_intelligence_engine._query_github_issues")
    def test_full_analysis_combines_every_real_engine(self, mock_issues, mock_hn_disc, mock_cd_hn, mock_cd_gh):
        mock_issues.return_value = ([], 0)
        mock_hn_disc.return_value = ([], 0)
        mock_cd_hn.return_value = []
        mock_cd_gh.return_value = []

        result = mie.analyze_opportunity("a test niche xyz", max_results=3, analysis_db_file=self.db_path)
        self.assertIn("scores", result)
        self.assertIn("risk", result)
        self.assertIn("confidence", result)
        # Opportunity Intelligence Round 2 (2026-07-22): was silently
        # discarded before the fix, same pattern as risk/confidence above.
        self.assertIn("defensibility", result)
        # Strategic Opportunity Intelligence Engine (2026-07-22): persisted
        # proactively this time.
        self.assertIn("market_signal", result)
        self.assertIn("ai_leverage", result)
        self.assertIn("customer_pain", result)
        self.assertIn("demand_pattern", result)
        self.assertIn("competitors", result)
        self.assertIn("opportunity_gap", result)
        self.assertIn("pricing", result)

    @patch("competitor_discovery._query_github")
    @patch("competitor_discovery._query_hn")
    @patch("market_intelligence_engine._query_hn_discussions")
    @patch("market_intelligence_engine._query_github_issues")
    @patch("market_intelligence_engine.PROFIT_ORACLE.opportunity_score")
    def test_opportunity_gap_uses_competition_favorability_correctly_not_double_inverted(
        self, mock_score, mock_issues, mock_hn_disc, mock_cd_hn, mock_cd_gh,
    ):
        """Strategic Autonomy / Evidence Governance follow-up: analyze_opportunity()
        used to pass competition_favorability (already high=favorable)
        directly into compute_opportunity_gap(demand, competition), whose
        own contract expects raw competition INTENSITY (high=bad) — see
        its own tests (test_high_demand_low_competition_is_high_gap passes
        competition_score=10 for a LOW-competition case). This double-
        inverted every real evaluation, suppressing opportunity_gap by
        ~20-30 points and confirmed (verified against all 1,344 real
        historical decisions, zero mismatches) to be the reason
        opportunity_gap had never once reached the BUILD threshold (65) in
        this factory's real history.

        Uses the EXACT real values from one of those historical records
        (market_demand=63, competition_favorability=70, which recorded a
        buggy opportunity_gap of 50) to prove the fix: the corrected
        value must be ~66 (0.6*63 + 0.4*70 = 65.8), not the old ~50
        (0.6*63 + 0.4*(100-70) = 49.8)."""
        mock_issues.return_value = ([], 0)
        mock_hn_disc.return_value = ([], 0)
        mock_cd_hn.return_value = []
        mock_cd_gh.return_value = []
        mock_score.return_value = {
            "components": {
                "market_demand": 63,
                "competition_favorability": 70,
                "profit_potential": 78,
            },
            "risk": {"level": "low", "notes": []},
            "confidence": {"score": 30, "level": "منخفضة", "note": "test"},
            "recommended_price": "$19",
        }

        result = mie.analyze_opportunity("a real-shaped historical test niche", analysis_db_file=self.db_path)

        self.assertEqual(result["opportunity_gap"], 66, result)
        self.assertNotEqual(result["opportunity_gap"], 50, "must never reproduce the old double-inverted value")
        self.assertIn("ai_ceo", result)
        self.assertIn(result["ai_ceo"]["decision"], mie.DECISIONS)

    @patch("competitor_discovery._query_github")
    @patch("competitor_discovery._query_hn")
    @patch("market_intelligence_engine._query_hn_discussions")
    @patch("market_intelligence_engine._query_github_issues")
    def test_pricing_never_invents_a_competitor_price(self, mock_issues, mock_hn_disc, mock_cd_hn, mock_cd_gh):
        mock_issues.return_value = ([], 0)
        mock_hn_disc.return_value = ([], 0)
        mock_cd_hn.return_value = []
        mock_cd_gh.return_value = []
        result = mie.analyze_opportunity("a test niche xyz", max_results=3, analysis_db_file=self.db_path)
        self.assertIn("Unknown", result["pricing"]["note"])


if __name__ == "__main__":
    unittest.main()
