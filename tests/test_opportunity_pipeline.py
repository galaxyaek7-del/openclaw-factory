"""Tests for opportunity_pipeline.py (Opportunity Intelligence Round 2,
2026-07-22).

Runs with stdlib unittest. Zero live network calls -- reads only
already-recorded decisions from a temp-file-isolated data/decisions.jsonl,
via the exact same real decision_engine.engine.record_ladder_decision()
every real candidate goes through.

    python -m unittest tests.test_opportunity_pipeline -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from decision_engine import engine
import opportunity_pipeline as op


def _temp_path(suffix=".jsonl"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


class TestBuildOpportunityPipeline(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.decisions_path):
            os.remove(self.decisions_path)

    def _record(self, *args, **kwargs):
        kwargs["decisions_path"] = self.decisions_path
        ladder_result = {
            "accepted": kwargs.pop("accepted"), "ladder_score": kwargs.pop("score"), "price": kwargs.pop("price"),
            "reason": "test", "components": {
                "market_demand": 60, "competition_favorability": 70, "profit_potential": 50,
                "recurring_revenue_potential": kwargs.pop("recurring", 90), "reusability": kwargs.pop("reusability", 90),
                "automation_potential": kwargs.pop("automation_potential", 40),
            },
            "risk": {"score": 90, "level": "low", "notes": []},
            "confidence": {"score": 55, "level": "متوسطة", "note": "test"},
        }
        defensibility = kwargs.pop("defensibility", None)
        if defensibility is not None:
            ladder_result["defensibility"] = defensibility
        market_signal = kwargs.pop("market_signal", None)
        if market_signal is not None:
            ladder_result["market_signal"] = market_signal
        ai_leverage = kwargs.pop("ai_leverage", None)
        if ai_leverage is not None:
            ladder_result["ai_leverage"] = ai_leverage
        niche, ladder = args
        decisions_path = kwargs.pop("decisions_path")
        return engine.record_ladder_decision(niche, ladder, ladder_result, decisions_path=decisions_path)

    def test_accepted_decisions_land_in_product_laboratory(self):
        self._record("real ai saas niche", "ai_saas", accepted=True, score=85.0, price=250,
                     defensibility={"score": 75, "level": "عالية نسبياً", "note": "test"})
        result = op.build_opportunity_pipeline(decisions_path=self.decisions_path)
        self.assertEqual(result["product_laboratory_count"], 1)
        self.assertEqual(result["product_laboratory"][0]["niche"], "real ai saas niche")
        self.assertEqual(result["product_laboratory"][0]["status"], "ACCEPTED")

    def test_rejected_decisions_land_in_backlog_never_product_laboratory(self):
        self._record("weak niche", "kdp_books", accepted=False, score=30.0, price=15)
        result = op.build_opportunity_pipeline(decisions_path=self.decisions_path)
        self.assertEqual(result["product_laboratory_count"], 0)
        self.assertEqual(result["backlog_count"], 1)
        self.assertEqual(result["backlog"][0]["niche"], "weak niche")

    def test_never_invents_a_new_acceptance_threshold(self):
        """Product Laboratory membership must come from the real status
        field alone -- never a locally recomputed score comparison."""
        self._record("borderline high score but rejected on price", "kdp_books", accepted=False, score=90.0, price=10)
        result = op.build_opportunity_pipeline(decisions_path=self.decisions_path)
        self.assertEqual(result["product_laboratory_count"], 0, "a high score with accepted=False must never land in Product Laboratory")

    def test_defensibility_surfaced_when_present(self):
        self._record("niche with real defensibility", "b2b_systems", accepted=True, score=80.0, price=200,
                     defensibility={"score": 75, "level": "عالية نسبياً", "note": "real"})
        result = op.build_opportunity_pipeline(decisions_path=self.decisions_path)
        entry = result["product_laboratory"][0]
        self.assertEqual(entry["defensibility"]["level"], "عالية نسبياً")

    def test_defensibility_honestly_unknown_for_older_decisions_without_it(self):
        self._record("older niche pre-defensibility", "b2b_systems", accepted=True, score=80.0, price=200)
        result = op.build_opportunity_pipeline(decisions_path=self.decisions_path)
        entry = result["product_laboratory"][0]
        self.assertEqual(entry["defensibility"]["answer"], "Unknown")

    def test_time_to_mvp_is_always_honestly_unknown(self):
        """No real dev-time-estimation model exists anywhere in this
        factory -- must never be fabricated."""
        self._record("any niche", "automation_tools", accepted=True, score=70.0, price=150)
        result = op.build_opportunity_pipeline(decisions_path=self.decisions_path)
        entry = result["product_laboratory"][0]
        self.assertEqual(entry["time_to_mvp"]["answer"], "Unknown")

    def test_market_size_honestly_unknown_when_not_recorded(self):
        self._record("a niche with no market signal", "automation_tools", accepted=True, score=70.0, price=150)
        result = op.build_opportunity_pipeline(decisions_path=self.decisions_path)
        entry = result["product_laboratory"][0]
        self.assertEqual(entry["market_size"]["answer"], "Unknown")

    def test_market_size_real_when_market_signal_recorded(self):
        """Strategic Opportunity Intelligence Engine (2026-07-22): market
        size is a real discussion-volume proxy, never a fabricated TAM."""
        self._record(
            "a niche with real market signal", "automation_tools", accepted=True, score=70.0, price=150,
            market_signal={"score": 60, "level": "مرتفعة", "note": "حجم نقاش حقيقي: 50 نتيجة"},
        )
        result = op.build_opportunity_pipeline(decisions_path=self.decisions_path)
        entry = result["product_laboratory"][0]
        self.assertEqual(entry["market_size"]["level"], "مرتفعة")

    def test_ai_leverage_and_automation_potential_surfaced_when_present(self):
        self._record(
            "a niche with real ai leverage", "ai_saas", accepted=True, score=90.0, price=300,
            ai_leverage={"score": 80, "level": "عالية", "note": "test"}, automation_potential=40,
        )
        result = op.build_opportunity_pipeline(decisions_path=self.decisions_path)
        entry = result["product_laboratory"][0]
        self.assertEqual(entry["ai_leverage"]["level"], "عالية")
        self.assertEqual(entry["automation_potential"], 40)

    def test_business_dossier_auto_generated_only_for_accepted_opportunities(self):
        """Autonomous Digital Venture Studio (2026-07-22): 'every accepted
        opportunity must automatically generate' the 8 named sections --
        never for backlog items."""
        self._record(
            "an accepted niche for dossier test", "automation_tools", accepted=True, score=90.0, price=150,
            defensibility={"score": 75, "level": "عالية نسبياً", "note": "test"},
        )
        self._record("a rejected niche for dossier test", "kdp_books", accepted=False, score=30.0, price=10)
        result = op.build_opportunity_pipeline(decisions_path=self.decisions_path)
        accepted_entry = result["product_laboratory"][0]
        rejected_entry = result["backlog"][0]
        self.assertIsNotNone(accepted_entry["business_dossier"])
        self.assertIsNone(rejected_entry["business_dossier"])

    def test_business_dossier_has_all_eight_sections(self):
        self._record(
            "a dossier completeness test niche", "ai_saas", accepted=True, score=90.0, price=300,
            defensibility={"score": 75, "level": "عالية نسبياً", "note": "test"},
        )
        result = op.build_opportunity_pipeline(decisions_path=self.decisions_path)
        dossier = result["product_laboratory"][0]["business_dossier"]
        for key in (
            "business_thesis", "customer_profile", "product_architecture", "mvp_roadmap",
            "revenue_model", "pricing_strategy", "competitive_moat", "expansion_strategy",
        ):
            self.assertIn(key, dossier)

    def test_strategic_investment_layer_present_for_ladder_tagged_decisions(self):
        self._record(
            "a niche for strategic layer test", "ai_saas", accepted=True, score=90.0, price=300,
            defensibility={"score": 75, "level": "عالية نسبياً", "note": "test"},
            market_signal={"score": 60, "level": "مرتفعة", "note": "test"},
            ai_leverage={"score": 80, "level": "عالية", "note": "test"},
        )
        result = op.build_opportunity_pipeline(decisions_path=self.decisions_path)
        entry = result["product_laboratory"][0]
        self.assertIsNotNone(entry["strategic_investment"])
        self.assertIn("can_become_premium_digital_asset", entry["strategic_investment"])
        self.assertIn("can_create_a_product_ecosystem", entry["strategic_investment"])

    def test_customer_type_uses_ladder_as_an_honest_proxy(self):
        self._record("a b2b niche", "b2b_systems", accepted=True, score=75.0, price=180)
        result = op.build_opportunity_pipeline(decisions_path=self.decisions_path)
        entry = result["product_laboratory"][0]
        self.assertEqual(entry["customer_type"]["value"], "b2b_systems")

    def test_recurring_revenue_and_scalability_come_from_real_ladder_components(self):
        self._record("a recurring niche", "ai_saas", accepted=True, score=90.0, price=300, recurring=100, reusability=95)
        result = op.build_opportunity_pipeline(decisions_path=self.decisions_path)
        entry = result["product_laboratory"][0]
        self.assertEqual(entry["recurring_revenue_potential"], 100)
        self.assertEqual(entry["global_scalability"], 95)

    def test_backlog_is_truncated_but_count_stays_honest(self):
        for i in range(5):
            self._record(f"backlog niche {i}", "kdp_books", accepted=False, score=30.0, price=10)
        result = op.build_opportunity_pipeline(decisions_path=self.decisions_path, backlog_limit=2)
        self.assertEqual(len(result["backlog"]), 2)
        self.assertEqual(result["backlog_count"], 5)
        self.assertTrue(result["backlog_truncated"])

    def test_empty_decisions_file_reports_honestly_zero(self):
        result = op.build_opportunity_pipeline(decisions_path=self.decisions_path)
        self.assertEqual(result["total_opportunities"], 0)
        self.assertEqual(result["product_laboratory"], [])
        self.assertEqual(result["backlog"], [])

    def test_latest_decision_per_niche_only_not_full_history(self):
        self._record("evolving niche", "kdp_books", accepted=False, score=30.0, price=10)
        self._record("evolving niche", "ai_saas", accepted=True, score=90.0, price=300)
        result = op.build_opportunity_pipeline(decisions_path=self.decisions_path)
        matches = [a for a in (result["product_laboratory"] + result["backlog"]) if a["niche"] == "evolving niche"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["status"], "ACCEPTED")


if __name__ == "__main__":
    unittest.main()
