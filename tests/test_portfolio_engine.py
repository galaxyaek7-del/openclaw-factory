"""Tests for portfolio_engine.py (Global Product Portfolio Engine,
2026-07-24): real 13-class classification + NOW/NEXT/LATER/REJECT,
reusing investment_pipeline.py and scheduler.py directly.

Runs with stdlib unittest. Every function reads only from temp-file-
isolated fixtures -- never the real data/*.jsonl files.

    python -m unittest tests.test_portfolio_engine -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import portfolio_engine as pe
from decision_engine import engine


def _temp_path():
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(path)
    return path


class TestClassifyPortfolioClass(unittest.TestCase):
    def test_explicit_product_family_wins(self):
        decision = {"ladder": "kdp_books", "product_family": "api_products"}
        self.assertEqual(pe.classify_portfolio_class(decision), "AI APIs")

    def test_ladder_fallback_when_no_family(self):
        decision = {"ladder": "ai_saas", "product_family": None}
        self.assertEqual(pe.classify_portfolio_class(decision), "Premium SaaS")

    def test_books_ladder_maps_to_books(self):
        decision = {"ladder": "kdp_books", "product_family": None}
        self.assertEqual(pe.classify_portfolio_class(decision), "Books")

    def test_neither_present_is_honestly_unclassified(self):
        decision = {"ladder": None, "product_family": None}
        self.assertEqual(pe.classify_portfolio_class(decision), "Unclassified")


class TestClassFamilyStatus(unittest.TestCase):
    def test_real_family_class_reports_real_status(self):
        result = pe.class_family_status("Premium SaaS")
        self.assertEqual(result["families"][0]["family"], "ai_saas")
        self.assertIn(result["families"][0]["status"], ("REAL", "NOT YET BUILT"))

    def test_no_distinct_family_class_is_honest(self):
        result = pe.class_family_status("AI Agents")
        self.assertIsNone(result["families"])
        self.assertEqual(result["status"], "NO DISTINCT REAL FAMILY")

    def test_templates_class_covers_all_3_real_families(self):
        result = pe.class_family_status("Templates (Notion/Excel/Canva)")
        names = {f["family"] for f in result["families"]}
        self.assertEqual(names, {"professional_templates", "notion_workspaces", "spreadsheet_systems"})


class TestB2bB2cSignal(unittest.TestCase):
    def test_ai_saas_is_b2b(self):
        result = pe._b2b_b2c_signal("ai_saas")
        self.assertTrue(result["b2b"])
        self.assertFalse(result["b2c"])

    def test_kdp_books_is_b2c(self):
        result = pe._b2b_b2c_signal("kdp_books")
        self.assertFalse(result["b2b"])
        self.assertTrue(result["b2c"])

    def test_no_ladder_is_honestly_none(self):
        result = pe._b2b_b2c_signal(None)
        self.assertIsNone(result["b2b"])


class TestDiversificationImpact(unittest.TestCase):
    def test_first_in_class_is_high_impact(self):
        result = pe._diversification_impact("Premium SaaS", {"Premium SaaS": 1})
        self.assertEqual(result["impact"], "high")
        self.assertEqual(result["sibling_count"], 0)

    def test_many_siblings_is_low_impact(self):
        result = pe._diversification_impact("Premium SaaS", {"Premium SaaS": 5})
        self.assertEqual(result["impact"], "low")
        self.assertEqual(result["sibling_count"], 4)


class TestBuildPortfolioEntry(unittest.TestCase):
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

    def _record(self, niche, ladder="ai_saas", score=85.0, price=250):
        ladder_result = {
            "accepted": True, "ladder_score": score, "price": price, "reason": "test",
            "components": {
                "market_demand": 60, "competition_favorability": 70, "profit_potential": 50,
                "recurring_revenue_potential": 90, "reusability": 77, "automation_potential": 40,
            },
            "risk": {"score": 90, "level": "low", "notes": []},
            "confidence": {"score": 55, "level": "متوسطة", "note": "test"},
            "defensibility": {"score": 75, "level": "عالية نسبياً", "note": "test"},
            "market_signal": {"score": 60, "level": "مرتفعة", "note": "test"},
            "ai_leverage": {"score": 80, "level": "عالية", "note": "test"},
        }
        engine.record_ladder_decision(niche, ladder, ladder_result, decisions_path=self.decisions_path)

    def _entry(self, niche):
        return pe.build_portfolio_entry(
            niche, decisions_path=self.decisions_path, board_path=self.board_path, alerts_path=self.alerts_path,
            reopen_log_path=self.reopen_log_path, evidence_path=self.evidence_path,
        )

    def test_no_real_decision_is_honestly_none(self):
        self.assertIsNone(self._entry("never scored"))

    def test_real_fields_and_honest_gaps_both_present(self):
        self._record("a full portfolio niche")
        entry = self._entry("a full portfolio niche")
        self.assertEqual(entry["portfolio_class"], "Premium SaaS")
        self.assertEqual(entry["reusability_inside_company"], 77)
        self.assertEqual(entry["expected_monthly_recurring_revenue"]["value"], 0)
        self.assertIsNone(entry["time_to_market"]["value"])
        self.assertIsNone(entry["country_priority"]["value"])
        self.assertIsNone(entry["china_suitability"]["value"])

    def test_expected_annual_revenue_is_real_revenue_to_date_never_a_projection(self):
        import market_evidence
        self._record("a revenue niche")
        market_evidence.record_evidence("a revenue niche", "closed_sale", {
            "commercial_event": {"platform": "gumroad", "selling_price": 250.0, "season": "summer"},
        }, evidence_path=self.evidence_path)
        entry = self._entry("a revenue niche")
        self.assertEqual(entry["expected_annual_revenue"]["value"], 250.0)
        self.assertIn("توقّعاً", entry["expected_annual_revenue"]["basis"])


class TestBuildPortfolioReport(unittest.TestCase):
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

    def _record(self, niche, ladder, score):
        ladder_result = {
            "accepted": True, "ladder_score": score, "price": 200, "reason": "test",
            "components": {
                "market_demand": 60, "competition_favorability": 70, "profit_potential": 50,
                "recurring_revenue_potential": 90, "reusability": 85, "automation_potential": 40,
            },
            "risk": {"score": 90, "level": "low", "notes": []},
            "confidence": {"score": 55, "level": "متوسطة", "note": "test"},
        }
        engine.record_ladder_decision(niche, ladder, ladder_result, decisions_path=self.decisions_path)

    def _report(self):
        return pe.build_portfolio_report(
            decisions_path=self.decisions_path, board_path=self.board_path, alerts_path=self.alerts_path,
            reopen_log_path=self.reopen_log_path, evidence_path=self.evidence_path,
            timeline_path=self.timeline_path, outcomes_path=self.outcomes_path,
        )

    def test_empty_factory_reports_honestly(self):
        report = self._report()
        self.assertEqual(report["total_real_opportunities"], 0)
        self.assertEqual(report["top_100_worldwide"], [])

    def test_china_is_always_honestly_empty(self):
        self._record("a niche", "ai_saas", 85.0)
        report = self._report()
        self.assertEqual(report["top_50_china"]["entries"], [])
        self.assertTrue(report["top_50_china"]["reason"])

    def test_class_priority_orders_ai_software_above_books(self):
        self._record("a books niche", "kdp_books", 95.0)  # higher raw score
        self._record("an ai saas niche", "ai_saas", 40.0)  # lower raw score
        report = self._report()
        classes_in_order = [e["portfolio_class"] for e in report["top_100_worldwide"]]
        self.assertLess(classes_in_order.index("Premium SaaS"), classes_in_order.index("Books"))

    def test_enterprise_slice_only_includes_enterprise_classes(self):
        self._record("an enterprise niche", "b2b_systems", 85.0)
        self._record("a books niche for enterprise test", "kdp_books", 85.0)
        report = self._report()
        for e in report["top_25_enterprise"]:
            self.assertIn(e["portfolio_class"], {"Enterprise Automation", "AI APIs", "Premium SaaS"})

    def test_execution_bucket_is_present_on_every_entry(self):
        self._record("a bucketed niche", "ai_saas", 85.0)
        report = self._report()
        for e in report["top_100_worldwide"]:
            self.assertIn(e["execution_bucket"], {"NOW", "NEXT", "LATER", "REJECT"})


if __name__ == "__main__":
    unittest.main()
