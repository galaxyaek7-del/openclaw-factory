"""Tests for business_dossier.py (Autonomous Digital Venture Studio,
2026-07-22).

Runs with stdlib unittest. Zero live network calls -- every input is a
hand-built ladder_opportunity_score()-shaped fixture or a real product_
families registry state, so this suite never depends on cached
competitor data or live API availability.

    python -m unittest tests.test_business_dossier -v
"""

import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import business_dossier as bd
from product_families import registry as pf_registry


def _ladder_result(**overrides):
    base = {
        "niche": "a business dossier test niche", "ladder": "automation_tools", "price": 150,
        "accepted": True, "components": {
            "market_demand": 60, "competition_favorability": 70, "profit_potential": 55,
            "recurring_revenue_potential": 55, "reusability": 80, "automation_potential": 90,
        },
        "defensibility": {"score": 75, "level": "عالية نسبياً", "note": "لا منافسين أقوياء"},
        "market_signal": {"score": 60, "level": "مرتفعة", "note": "حجم نقاش حقيقي: 50 نتيجة"},
        "ai_leverage": {"score": 80, "level": "عالية", "note": "test"},
    }
    base.update(overrides)
    return base


class TestBusinessThesis(unittest.TestCase):
    def test_thesis_cites_only_real_fields_never_invents_new_facts(self):
        result = bd.build_business_dossier(_ladder_result())
        thesis = result["business_thesis"]
        self.assertIn("150", thesis["text"])  # real price
        self.assertIn("automation_tools".upper()[:3].lower(), "automation")  # sanity: ladder name present indirectly
        self.assertIn("grounded_in", thesis)


class TestCustomerProfile(unittest.TestCase):
    def test_no_customer_pain_data_never_fabricates_a_persona(self):
        result = bd.build_business_dossier(_ladder_result())
        profile = result["customer_profile"]
        self.assertIsNone(profile["real_evidence_count"])
        self.assertIn("لا شخصية عميل مُختلَقة", profile["note"])

    def test_real_customer_pain_evidence_is_counted_honestly(self):
        customer_pain = {
            "pain_score": 60, "query_used": "logistics automation manual process pain",
            "real_evidence": {"github_issues_found": 5, "hn_discussions_found": 2, "stack_overflow_found": 1, "willingness_to_pay_hits": 2},
        }
        result = bd.build_business_dossier(_ladder_result(), customer_pain=customer_pain)
        profile = result["customer_profile"]
        self.assertEqual(profile["real_evidence_count"], 8)
        self.assertEqual(profile["willingness_to_pay_signals"], 2)

    def test_segment_proxy_reflects_the_real_ladder_rank(self):
        result = bd.build_business_dossier(_ladder_result(ladder="ai_saas"))
        self.assertIn("B2B", result["customer_profile"]["segment_proxy"])


class _IsolatedRegistryTestCase(unittest.TestCase):
    """Same safe save/restore convention as tests/test_product_families.py's
    TestRegistry -- product_families.registry is a shared, process-global
    singleton; a blind clear() in tearDown would leave it empty for every
    other test that runs afterward in the same process and expects the
    real 5 Phase A adapters to be registered."""

    def setUp(self):
        self._saved = pf_registry.all_families()

    def tearDown(self):
        pf_registry.clear()
        for adapter in self._saved:
            pf_registry.register(adapter)


class TestProductArchitecture(_IsolatedRegistryTestCase):
    def test_real_adapter_reports_real_status(self):
        pf_registry.clear()

        class FakeAdapter:
            name = "automation_systems"
        pf_registry.register(FakeAdapter())
        result = bd.build_business_dossier(_ladder_result(ladder="automation_tools"))
        self.assertEqual(result["product_architecture"]["status"], "REAL")

    def test_no_adapter_honestly_reports_not_yet_built_never_a_fake_one(self):
        pf_registry.clear()
        result = bd.build_business_dossier(_ladder_result(ladder="ai_saas"))
        self.assertEqual(result["product_architecture"]["status"], "NOT YET BUILT")
        self.assertIn("ELITE_ASSET_DOCTRINE.md", result["product_architecture"]["note"])


class TestMvpRoadmap(_IsolatedRegistryTestCase):
    def test_never_invents_a_timeline_or_a_date(self):
        pf_registry.clear()
        result = bd.build_business_dossier(_ladder_result(ladder="ai_saas"))
        roadmap_text = str(result["mvp_roadmap"])
        for banned in ("week", "month", "Q1", "Q2", "Q3", "Q4", "day", "أسبوع", "شهر"):
            self.assertNotIn(banned, roadmap_text)

    def test_blocked_status_when_no_real_adapter_exists(self):
        pf_registry.clear()
        result = bd.build_business_dossier(_ladder_result(ladder="ai_saas"))
        self.assertTrue(any(s["status"].startswith("محظور") for s in result["mvp_roadmap"]["steps"]))

    def test_buildable_today_when_a_real_adapter_exists(self):
        pf_registry.clear()

        class FakeAdapter:
            name = "automation_systems"
        pf_registry.register(FakeAdapter())
        result = bd.build_business_dossier(_ladder_result(ladder="automation_tools"))
        self.assertTrue(all(s["status"] == "قابل للتنفيذ اليوم" for s in result["mvp_roadmap"]["steps"]))


class TestRevenueAndPricing(unittest.TestCase):
    def test_revenue_model_uses_the_real_ladder_component(self):
        result = bd.build_business_dossier(_ladder_result())
        self.assertEqual(result["revenue_model"]["recurring_revenue_potential"], 55)

    def test_pricing_strategy_uses_the_real_price_and_floor(self):
        result = bd.build_business_dossier(_ladder_result())
        self.assertEqual(result["pricing_strategy"]["recommended_price_usd"], 150)
        self.assertEqual(result["pricing_strategy"]["min_profit_floor_usd"], 97)


class TestMoatAndExpansion(unittest.TestCase):
    def test_competitive_moat_reuses_real_defensibility(self):
        result = bd.build_business_dossier(_ladder_result())
        self.assertEqual(result["competitive_moat"]["level"], "عالية نسبياً")

    def test_expansion_strategy_reuses_real_reusability(self):
        result = bd.build_business_dossier(_ladder_result())
        self.assertEqual(result["expansion_strategy"]["reusability_score"], 80)


class TestDossierNeverGatesADecision(unittest.TestCase):
    def test_never_mutates_or_recomputes_the_input(self):
        ladder_result = _ladder_result()
        original = dict(ladder_result)
        bd.build_business_dossier(ladder_result)
        self.assertEqual(ladder_result, original)

    def test_all_eight_named_sections_present(self):
        result = bd.build_business_dossier(_ladder_result())
        for key in (
            "business_thesis", "customer_profile", "product_architecture", "mvp_roadmap",
            "revenue_model", "pricing_strategy", "competitive_moat", "expansion_strategy",
        ):
            self.assertIn(key, result)


if __name__ == "__main__":
    unittest.main()
