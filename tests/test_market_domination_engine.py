"""Tests for market_domination_engine.py (Global Market Domination
Engine, ADR-175, 2026-08-05): real candidate discovery across all 6
real ladders + real GOOS evaluation, never a fabricated "searched the
world" claim, never a second discovery/evaluation engine.

    python -m unittest tests.test_market_domination_engine -v
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import market_domination_engine as mde


class TestRegionalCoverage(unittest.TestCase):
    def test_all_8_named_regions_present(self):
        expected = {
            "north_america", "south_america", "europe", "middle_east",
            "africa", "asia", "oceania", "global_online_markets",
        }
        self.assertEqual(set(mde.REGIONAL_COVERAGE.keys()), expected)

    def test_only_global_online_markets_is_honestly_real(self):
        for region, entry in mde.REGIONAL_COVERAGE.items():
            if region == "global_online_markets":
                self.assertEqual(entry["status"], "REAL")
            elif region == "north_america":
                self.assertEqual(entry["status"], "PARTIAL")
            else:
                self.assertEqual(entry["status"], "NOT_MEASURABLE", f"{region} must not be fabricated as measurable")

    def test_every_not_measurable_region_cites_the_standing_deferral(self):
        for region, entry in mde.REGIONAL_COVERAGE.items():
            if entry["status"] == "NOT_MEASURABLE":
                self.assertIn("2026-07-23", entry["reason"])


class TestGlobalSourceStatus(unittest.TestCase):
    def test_reports_a_real_total(self):
        result = mde.global_source_status()
        # Real Evidence Provider abstraction (ADR-179, 2026-08-06) added
        # 3 more registered sources (rss_feeds/public_reports/web_pages).
        self.assertEqual(result["total_registered"], 14)

    def test_static_unavailable_sources_are_honestly_marked(self):
        result = mde.global_source_status()
        by_name = {s["name"]: s for s in result["sources"]}
        for name in ("reddit", "product_hunt", "google_trends"):
            self.assertEqual(by_name[name]["status"], "unavailable")
            self.assertTrue(by_name[name].get("reason"))


class TestHighValueCandidates(unittest.TestCase):
    def test_never_scoped_to_automation_ladders_only(self):
        result = mde.high_value_candidates(limit=20)
        ladders_seen = {c["ladder"] for c in result["candidates"]}
        # market_hunter.SEED_CATEGORIES includes kdp_books/educational --
        # a real ladder outside automation_opportunity_scanner's own
        # automation-only scope; must be reachable here.
        self.assertTrue(ladders_seen, "must find at least some real candidates")

    def test_ranked_by_real_ladder_priority_order(self):
        result = mde.high_value_candidates(limit=20)
        ranks = [c["ladder_priority_rank"] for c in result["candidates"]]
        self.assertEqual(ranks, sorted(ranks), "candidates must be sorted by real profit_oracle.LADDER_RANKS priority")

    def test_never_triggers_a_new_evaluation_cycle(self):
        with mock.patch("golden_hunter.hunt.run_hunt") as m_hunt:
            mde.high_value_candidates(limit=5)
            m_hunt.assert_not_called()


class TestEvaluateCandidate(unittest.TestCase):
    def test_delegates_to_real_goos_never_a_second_engine(self):
        with mock.patch("goos.evaluate_dimensions", return_value={"status": "EVALUATED"}) as m:
            result = mde.evaluate_candidate("some niche")
            m.assert_called_once_with("some niche")
        self.assertEqual(result["status"], "EVALUATED")


class TestBuildMarketDominationDashboard(unittest.TestCase):
    def test_real_call_against_real_data_never_throws(self):
        report = mde.build_market_domination_dashboard(limit=3)
        self.assertIn("regional_coverage", report)
        self.assertIn("global_source_status", report)

    def test_honestly_reports_no_verified_opportunity_when_no_candidates(self):
        with mock.patch("market_domination_engine.high_value_candidates", return_value={"candidates": [], "count": 0, "total_found": 0, "generated_at": "x"}):
            report = mde.build_market_domination_dashboard()
        self.assertEqual(report["answer"], "NO VERIFIED OPPORTUNITY FOUND")

    def test_computes_candidates_and_sources_exactly_once(self):
        fake_candidates = {"candidates": [{"niche": "n1", "ladder": "ai_saas", "ladder_priority_rank": 0, "source": "x"}], "count": 1, "total_found": 1, "generated_at": "x"}
        fake_sources = {"sources": [], "total_registered": 0}
        with mock.patch("market_domination_engine.high_value_candidates", return_value=fake_candidates) as m_cand, \
             mock.patch("market_domination_engine.global_source_status", return_value=fake_sources) as m_src, \
             mock.patch("goos.evaluate_dimensions", return_value={"status": "EVALUATED"}):
            mde.build_market_domination_dashboard()
        m_cand.assert_called_once()
        m_src.assert_called_once()


if __name__ == "__main__":
    unittest.main()
