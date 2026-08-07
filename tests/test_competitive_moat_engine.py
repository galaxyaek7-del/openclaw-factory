"""Tests for competitive_moat_engine.py (ADR-207, Phase 17, 2026-08-08).

    python -m unittest tests.test_competitive_moat_engine -v
"""

import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import competitive_moat_engine as cme


class TestAssessEuAiActToolkitMoat(unittest.TestCase):
    def test_all_12_named_mechanisms_present(self):
        r = cme.assess_eu_ai_act_toolkit_moat()
        self.assertEqual(set(r["mechanisms"].keys()), set(cme.MOAT_MECHANISMS))

    def test_every_mechanism_has_a_valid_level(self):
        r = cme.assess_eu_ai_act_toolkit_moat()
        for name, m in r["mechanisms"].items():
            self.assertIn(m["level"], cme.MOAT_LEVELS, name)

    def test_every_mechanism_cites_real_evidence(self):
        r = cme.assess_eu_ai_act_toolkit_moat()
        for name, m in r["mechanisms"].items():
            self.assertGreater(len(m["evidence"]), 20, name)

    def test_no_mechanism_is_strong_today(self):
        """Honest, real finding -- must not silently drift to an
        inflated claim in a future edit without a real reason."""
        r = cme.assess_eu_ai_act_toolkit_moat()
        strong = [name for name, m in r["mechanisms"].items() if m["level"] == "STRONG"]
        self.assertEqual(strong, [])

    def test_development_recommendations_exclude_strong_mechanisms(self):
        r = cme.assess_eu_ai_act_toolkit_moat()
        strong_mechanisms = {name for name, m in r["mechanisms"].items() if m["level"] == "STRONG"}
        self.assertTrue(strong_mechanisms.isdisjoint(r["development_recommendations"].keys()))

    def test_market_crowding_is_a_real_citation_not_duplicated_logic(self):
        r = cme.assess_eu_ai_act_toolkit_moat()
        self.assertIn("profit_oracle.py", r["market_crowding"]["source"])


class TestAssessMoatForNicheWithNoRealEvidence(unittest.TestCase):
    def test_all_mechanisms_default_to_non_existent(self):
        r = cme.assess_moat_for_niche_with_no_real_evidence("Some Other Real Niche")
        for m in r["mechanisms"].values():
            self.assertEqual(m["level"], "NON-EXISTENT")

    def test_never_copies_the_eu_ai_act_assessment(self):
        eu = cme.assess_eu_ai_act_toolkit_moat()
        other = cme.assess_moat_for_niche_with_no_real_evidence("Some Other Real Niche")
        self.assertNotEqual(eu["mechanisms"]["unique_intelligence"]["level"], other["mechanisms"]["unique_intelligence"]["level"])


if __name__ == "__main__":
    unittest.main()
