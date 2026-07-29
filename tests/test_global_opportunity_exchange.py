"""Tests for global_opportunity_exchange.py (Global Opportunity Exchange
directive, 2026-07-29). Every real source is mocked -- channels.registry/
decision_engine.ranking/channels.ledger each have their own isolated
unit tests elsewhere.

    python -m unittest tests.test_global_opportunity_exchange -v
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import global_opportunity_exchange as gox


def _arm(name):
    m = MagicMock()
    m.name = name
    return m


class TestMarketplaceCatalog(unittest.TestCase):
    def test_only_registered_arms_are_marked_real(self):
        with patch("channels.registry.all_arms", return_value=[_arm("gumroad"), _arm("etsy")]):
            result = gox.marketplace_catalog()
        self.assertEqual(result["catalog"]["Gumroad"]["status"], "REAL")
        self.assertEqual(result["catalog"]["Etsy"]["status"], "REAL")
        self.assertEqual(result["catalog"]["Amazon KDP"]["status"], "DISCOVERY")
        self.assertIsNone(result["catalog"]["Amazon KDP"]["real_arm"])

    def test_discovery_marketplaces_have_no_economics_platforms_by_default(self):
        with patch("channels.registry.all_arms", return_value=[]):
            result = gox.marketplace_catalog()
        self.assertIsNone(result["catalog"]["Creative Market"]["economics_platforms"])
        self.assertFalse(result["catalog"]["Creative Market"]["has_real_commission_config"])

    def test_kdp_has_real_commission_config_despite_no_real_arm(self):
        with patch("channels.registry.all_arms", return_value=[]):
            result = gox.marketplace_catalog()
        self.assertEqual(result["catalog"]["Amazon KDP"]["status"], "DISCOVERY")
        self.assertTrue(result["catalog"]["Amazon KDP"]["has_real_commission_config"])
        self.assertIn("kdp_ebook", result["catalog"]["Amazon KDP"]["economics_platforms"])

    def test_real_arms_not_named_in_the_directive_are_surfaced(self):
        with patch("channels.registry.all_arms", return_value=[_arm("gumroad"), _arm("payhip"), _arm("paddle")]):
            result = gox.marketplace_catalog()
        self.assertEqual(sorted(result["real_arms_not_named_in_directive"]), ["paddle", "payhip"])
        self.assertEqual(result["named_marketplaces_with_real_arm"], 1)


class TestProductFamilyDistribution(unittest.TestCase):
    def test_no_accepted_decisions_is_honestly_not_enough_evidence(self):
        with patch("decision_engine.ranking.rank_all", return_value=[]):
            result = gox.product_family_distribution()
        self.assertEqual(result["answer"], "NOT ENOUGH EVIDENCE")

    def test_accepted_decisions_with_no_product_family_is_honestly_not_enough_evidence(self):
        decisions = [{"niche": "n", "status": "ACCEPTED", "product_family": None}]
        with patch("decision_engine.ranking.rank_all", return_value=decisions):
            result = gox.product_family_distribution()
        self.assertEqual(result["answer"], "NOT ENOUGH EVIDENCE")
        self.assertEqual(result["total_accepted"], 1)

    def test_real_concentration_is_computed_from_real_decisions(self):
        decisions = [
            {"niche": "a", "status": "ACCEPTED", "product_family": "automation_systems"},
            {"niche": "b", "status": "ACCEPTED", "product_family": "automation_systems"},
            {"niche": "c", "status": "ACCEPTED", "product_family": "micro_saas"},
            {"niche": "d", "status": "REJECTED", "product_family": "automation_systems"},
        ]
        with patch("decision_engine.ranking.rank_all", return_value=decisions):
            result = gox.product_family_distribution()
        self.assertEqual(result["total_accepted"], 3)
        self.assertEqual(result["top_family"], "automation_systems")
        self.assertEqual(result["top_family_pct"], round(100 * 2 / 3, 1))


class TestRevenueDistribution(unittest.TestCase):
    def test_no_real_sales_is_honestly_not_enough_evidence(self):
        with patch("channels.ledger.read_events", return_value=iter([])):
            result = gox.revenue_distribution()
        self.assertEqual(result["answer"], "NOT ENOUGH EVIDENCE")

    def test_real_sales_are_grouped_by_real_platform(self):
        events = [
            {"platform": "gumroad", "raw": {"amount": "100"}},
            {"platform": "gumroad", "raw": {"amount": "50"}},
            {"platform": "etsy", "raw": {"amount": "50"}},
        ]
        with patch("channels.ledger.read_events", return_value=iter(events)), \
             patch("channels.ledger._extract_sale_amount", side_effect=lambda raw, platform: float(raw["amount"])):
            result = gox.revenue_distribution()
        self.assertEqual(result["total_revenue_usd"], 200.0)
        self.assertEqual(result["top_platform"], "gumroad")
        self.assertEqual(result["top_platform_pct"], 75.0)

    def test_events_with_no_extractable_amount_are_skipped_not_crashed_on(self):
        events = [{"platform": "gumroad", "raw": {}}]
        with patch("channels.ledger.read_events", return_value=iter(events)), \
             patch("channels.ledger._extract_sale_amount", return_value=None):
            result = gox.revenue_distribution()
        self.assertEqual(result["answer"], "NOT ENOUGH EVIDENCE")


class TestAiProviderConcentration(unittest.TestCase):
    def test_no_real_cost_data_is_honestly_not_enough_evidence(self):
        providers = [{"provider": "groq", "real_stats": None}, {"provider": "openai", "real_stats": None}]
        with patch("ai_capability.registry.list_providers", return_value=providers):
            result = gox.ai_provider_concentration()
        self.assertEqual(result["answer"], "NOT ENOUGH EVIDENCE")

    def test_single_real_provider_is_100pct_with_a_disclosed_note(self):
        providers = [
            {"provider": "groq", "real_stats": {"total_cost_usd": 0.5}},
            {"provider": "openai", "real_stats": None},
        ]
        with patch("ai_capability.registry.list_providers", return_value=providers):
            result = gox.ai_provider_concentration()
        self.assertEqual(result["top_provider"], "groq")
        self.assertEqual(result["top_provider_pct"], 100.0)
        self.assertIsNotNone(result["note"])

    def test_two_real_providers_split_the_percentage_and_have_no_note(self):
        providers = [
            {"provider": "groq", "real_stats": {"total_cost_usd": 75.0}},
            {"provider": "anthropic", "real_stats": {"total_cost_usd": 25.0}},
        ]
        with patch("ai_capability.registry.list_providers", return_value=providers):
            result = gox.ai_provider_concentration()
        self.assertEqual(result["top_provider"], "groq")
        self.assertEqual(result["top_provider_pct"], 75.0)
        self.assertIsNone(result["note"])


class TestCountryDependencyNote(unittest.TestCase):
    def test_always_returns_the_same_structural_discovery(self):
        result = gox.country_dependency_note()
        self.assertEqual(result["answer"], "DISCOVERY")
        self.assertTrue(result["structural"])
        self.assertIn("2026-07-23", result["reason"])


class TestMarketHealth(unittest.TestCase):
    def test_no_real_arm_state_is_honestly_not_enough_evidence(self):
        with patch("channels.publish_protection.list_publish_protection_status", return_value={"arms": {}, "global": {}}):
            result = gox.market_health()
        self.assertEqual(result["answer"], "NOT ENOUGH EVIDENCE")

    def test_a_real_currently_disallowed_arm_is_flagged_unhealthy(self):
        status = {
            "arms": {
                "gumroad": {"currently_allowed": True, "risk_score": 10, "consecutive_failures": 0, "has_ever_published_successfully": True},
                "etsy": {"currently_allowed": False, "risk_score": 90, "consecutive_failures": 3, "has_ever_published_successfully": False},
            },
            "global": {"emergency_stopped": False},
        }
        with patch("channels.publish_protection.list_publish_protection_status", return_value=status):
            result = gox.market_health()
        self.assertEqual(result["unhealthy_arms"], ["etsy"])


class TestConcentrationRiskReport(unittest.TestCase):
    def test_country_is_always_structural_discovery(self):
        with patch("global_opportunity_exchange.revenue_distribution", return_value={"answer": "NOT ENOUGH EVIDENCE", "reason": "x"}), \
             patch("global_opportunity_exchange.product_family_distribution", return_value={"answer": "NOT ENOUGH EVIDENCE", "reason": "x"}), \
             patch("global_opportunity_exchange.ai_provider_concentration", return_value={"answer": "NOT ENOUGH EVIDENCE", "reason": "x"}):
            result = gox.concentration_risk_report()
        self.assertEqual(result["country"]["exceeded"], "structural DISCOVERY")
        self.assertEqual(result["country"]["threshold_pct"], 25.0)

    def test_a_real_value_crossing_its_threshold_is_flagged_exceeded(self):
        family = {"top_family": "automation_systems", "top_family_pct": 100.0}
        with patch("global_opportunity_exchange.revenue_distribution", return_value={"answer": "NOT ENOUGH EVIDENCE", "reason": "x"}), \
             patch("global_opportunity_exchange.product_family_distribution", return_value=family), \
             patch("global_opportunity_exchange.ai_provider_concentration", return_value={"answer": "NOT ENOUGH EVIDENCE", "reason": "x"}):
            result = gox.concentration_risk_report()
        self.assertTrue(result["product_family"]["exceeded"])
        self.assertEqual(result["product_family"]["top"], "automation_systems")

    def test_a_real_value_under_its_threshold_is_not_exceeded(self):
        revenue = {"top_platform": "gumroad", "top_platform_pct": 35.0}
        with patch("global_opportunity_exchange.revenue_distribution", return_value=revenue), \
             patch("global_opportunity_exchange.product_family_distribution", return_value={"answer": "NOT ENOUGH EVIDENCE", "reason": "x"}), \
             patch("global_opportunity_exchange.ai_provider_concentration", return_value={"answer": "NOT ENOUGH EVIDENCE", "reason": "x"}):
            result = gox.concentration_risk_report()
        self.assertFalse(result["platform"]["exceeded"])


class TestBuildGlobalOpportunityExchangeDashboard(unittest.TestCase):
    def _profile(self, niche, priority_score=50.0):
        return {"niche": niche, "board_summary": {"priority_score": {"score": priority_score}}}

    def _patches(self, portfolio=None, catalog=None, revenue=None, health=None, risk=None):
        portfolio = portfolio if portfolio is not None else {"profiles": [self._profile("n")]}
        catalog = catalog if catalog is not None else {"catalog": {}}
        revenue = revenue if revenue is not None else {"answer": "NOT ENOUGH EVIDENCE", "reason": "x"}
        health = health if health is not None else {"answer": "NOT ENOUGH EVIDENCE", "reason": "x"}
        risk = risk if risk is not None else {
            "platform": {"threshold_pct": 40.0, "value_pct": None, "exceeded": "NOT ENOUGH EVIDENCE", "top": None, "reason": "x"},
            "product_family": {"threshold_pct": 30.0, "value_pct": None, "exceeded": "NOT ENOUGH EVIDENCE", "top": None, "reason": "x"},
            "country": {"threshold_pct": 25.0, "value_pct": None, "exceeded": "structural DISCOVERY", "top": None, "reason": "x"},
            "ai_provider": {"threshold_pct": 20.0, "value_pct": None, "exceeded": "NOT ENOUGH EVIDENCE", "top": None, "reason": "x"},
            "generated_at": "t",
        }
        return (
            patch("value_engine.build_value_engine_report", return_value=portfolio),
            patch("global_opportunity_exchange.marketplace_catalog", return_value=catalog),
            patch("global_opportunity_exchange.revenue_distribution", return_value=revenue),
            patch("global_opportunity_exchange.market_health", return_value=health),
            patch("global_opportunity_exchange.concentration_risk_report", return_value=risk),
        )

    def test_opportunity_ranking_cites_real_portfolio_order(self):
        portfolio = {"profiles": [self._profile("top", 90.0), self._profile("second", 50.0)]}
        patches = self._patches(portfolio=portfolio)
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            result = gox.build_global_opportunity_exchange_dashboard()
        self.assertEqual(result["opportunity_ranking"], [{"niche": "top", "priority_score": 90.0}, {"niche": "second", "priority_score": 50.0}])

    def test_no_diversification_recommendations_when_nothing_real_exceeds(self):
        patches = self._patches()
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            result = gox.build_global_opportunity_exchange_dashboard()
        self.assertEqual(result["diversification_recommendations"], [])

    def test_a_real_exceeded_check_produces_a_real_cited_recommendation(self):
        risk = {
            "platform": {"threshold_pct": 40.0, "value_pct": None, "exceeded": "NOT ENOUGH EVIDENCE", "top": None, "reason": "x"},
            "product_family": {"threshold_pct": 30.0, "value_pct": 100.0, "exceeded": True, "top": "automation_systems", "reason": None},
            "country": {"threshold_pct": 25.0, "value_pct": None, "exceeded": "structural DISCOVERY", "top": None, "reason": "x"},
            "ai_provider": {"threshold_pct": 20.0, "value_pct": 100.0, "exceeded": True, "top": "groq", "reason": None},
            "generated_at": "t",
        }
        patches = self._patches(risk=risk)
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            result = gox.build_global_opportunity_exchange_dashboard()
        dims = {r["dimension"] for r in result["diversification_recommendations"]}
        self.assertEqual(dims, {"product_family", "ai_provider"})
        for r in result["diversification_recommendations"]:
            self.assertIn(r["top"], r["recommendation"])

    def test_market_saturation_discloses_it_reuses_market_health_verbatim(self):
        health = {"by_arm": {"gumroad": {"currently_allowed": True}}, "unhealthy_arms": []}
        patches = self._patches(health=health)
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            result = gox.build_global_opportunity_exchange_dashboard()
        self.assertEqual(result["market_saturation"]["by_arm"], health["by_arm"])
        self.assertIn("note", result["market_saturation"])

    def test_founder_approval_note_is_always_present(self):
        patches = self._patches()
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            result = gox.build_global_opportunity_exchange_dashboard()
        self.assertIn("توصيات فقط", result["founder_approval_note"])


if __name__ == "__main__":
    unittest.main()
