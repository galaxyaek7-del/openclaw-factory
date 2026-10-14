"""Tests for source_grounding -- the Cycle 86 generator fix.

The critical test is TestRealShippedDefectIsCaught: it runs the check against
the ACTUAL text extracted from the shipped EU AI Act toolkit. If this gate
cannot catch the file that motivated it, it is decoration.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import source_grounding as sg


class TestClassification(unittest.TestCase):
    def test_detects_eu_ai_act(self):
        ok, m = sg.classify_regulatory("EU AI Act Compliance Toolkit")
        self.assertTrue(ok)
        self.assertIn("ai act", m)

    def test_detects_generic_regulatory(self):
        for t in ("GDPR essentials", "SOC 2 readiness", "CCPA compliance",
                  "FTC review rule", "consumer protection law"):
            with self.subTest(topic=t):
                self.assertTrue(sg.classify_regulatory(t)[0])

    def test_non_regulatory_is_not_flagged(self):
        ok, _ = sg.classify_regulatory("Budget Tracker for College Students")
        self.assertFalse(ok)

    def test_conservative_direction(self):
        """A false positive costs a grounded prompt; a false negative ships
        fabricated law. The rule must lean toward flagging."""
        ok, _ = sg.classify_regulatory("Freelancer Invoice Guide")
        self.assertFalse(ok)
        ok, _ = sg.classify_regulatory("Safety compliance checklist")
        self.assertTrue(ok)


class TestSourceRegistry(unittest.TestCase):
    def test_ai_act_has_real_sources(self):
        srcs = sg.get_sources("EU AI Act")
        self.assertTrue(srcs)
        self.assertTrue(all(s.get("url", "").startswith("http") for s in srcs))

    def test_sources_carry_verification_date(self):
        for s in sg.get_sources("EU AI Act"):
            self.assertIn("verified_on", s)

    def test_annex_iii_states_the_eight_real_categories(self):
        stmt = sg.AI_ACT_ANNEX_III["statement"].lower()
        for cat in ("biometrics", "critical infrastructure", "education",
                    "employment", "law enforcement", "migration", "justice"):
            self.assertIn(cat, stmt, f"missing real category: {cat}")

    def test_annex_iii_forbids_the_fabricated_framings(self):
        forb = " ".join(sg.AI_ACT_ANNEX_III["forbidden_framings"]).lower()
        for bad in ("part a", "autonomy", "creativity", "real-time data"):
            self.assertIn(bad, forb)

    def test_unknown_topic_gets_no_sources(self):
        self.assertEqual(sg.get_sources("meal planning"), [])


class TestGroundingInstruction(unittest.TestCase):
    def test_empty_for_no_sources(self):
        self.assertEqual(sg.grounding_instruction([]), "")

    def test_instructs_omission_over_invention(self):
        block = sg.grounding_instruction(sg.get_sources("EU AI Act"))
        self.assertIn("Omission is correct", block)
        self.assertIn("Invention is not", block)

    def test_carries_the_real_url(self):
        block = sg.grounding_instruction(sg.get_sources("EU AI Act"))
        self.assertIn("ai-act-service-desk.ec.europa.eu", block)

    def test_forbids_each_fabricated_framing(self):
        block = sg.grounding_instruction(sg.get_sources("EU AI Act"))
        self.assertIn("Annex III, Part A", block)


class TestViolationDetection(unittest.TestCase):
    """Every framing found in the shipped file must be caught here."""

    REAL_DEFECTS = [
        "Annex III, Part A, category 1: Autonomy",
        "Identify high-risk categories (Annex III, Part A)",
        "Limited-risk AI systems in Annex III, Part B",
        "Annex III lists categories of autonomy and creativity",
        "Prohibit the use of high-risk general-purpose AI models.",
    ]

    def test_each_real_defect_is_caught(self):
        for s in self.REAL_DEFECTS:
            with self.subTest(defect=s):
                v = sg.verify_no_unsourced_citations(s, sg.get_sources("EU AI Act"))
                self.assertTrue(v, f"must catch: {s}")

    def test_correct_annex_iii_wording_is_clean(self):
        good = ("High-risk AI systems referred to in Article 6(2) are listed in "
                "Annex III across eight areas: biometrics, critical "
                "infrastructure, education, employment, essential services, "
                "law enforcement, migration, and justice.")
        self.assertEqual(
            sg.verify_no_unsourced_citations(good, sg.get_sources("EU AI Act")), [])

    def test_unverified_placeholder_is_allowed(self):
        # Omission is the instructed behaviour, so a placeholder must pass.
        v = sg.verify_no_unsourced_citations(
            "[UNVERIFIED - REQUIRES PRIMARY SOURCE]", sg.get_sources("EU AI Act"))
        self.assertEqual(v, [])


class TestCheckGenerated(unittest.TestCase):
    def test_regulatory_product_with_defect_fails(self):
        r = sg.check_generated(
            title="EU AI Act Toolkit",
            topic="EU AI Act compliance",
            body="Annex III, Part A, category 1: Autonomy")
        self.assertTrue(r.is_regulatory)
        self.assertFalse(r.grounded)

    def test_regulatory_product_clean_passes(self):
        r = sg.check_generated(
            title="EU AI Act Toolkit",
            topic="EU AI Act compliance",
            body="Annex III covers biometrics, critical infrastructure and more.")
        self.assertTrue(r.grounded)

    def test_non_regulatory_is_not_grounding_checked(self):
        r = sg.check_generated(title="Meal Planner", topic="recipes",
                               body="Annex III, Part A")
        self.assertFalse(r.is_regulatory)
        self.assertTrue(r.grounded, "no sources means nothing to verify")


class TestLegalReviewStillRequired(unittest.TestCase):
    def test_always_true_even_when_grounded(self):
        r = sg.check_generated(title="EU AI Act", topic="AI Act", body="clean")
        self.assertTrue(r.grounded)
        self.assertTrue(sg.legal_review_required(),
                        "grounding is not clearance")


@unittest.skipUnless(Path("data/cycle86_toolkit_text.txt").exists(),
                     "real extracted product text not present")
class TestRealShippedDefectIsCaught(unittest.TestCase):
    """The end-to-end test that matters: the actual shipped file."""

    @classmethod
    def setUpClass(cls):
        cls.text = Path("data/cycle86_toolkit_text.txt").read_text(encoding="utf-8")

    def test_generator_gate_catches_the_real_shipped_file(self):
        r = sg.check_generated(
            title="EU AI Act Compliance Toolkit",
            topic="EU AI Act compliance for SMEs",
            body=self.text)
        self.assertFalse(r.grounded,
                         "source_grounding MUST catch the shipped product")
        self.assertGreaterEqual(len(r.violations), 3)

    def test_content_gate_catches_it_too(self):
        import product_content_integrity as pci
        res = pci.check_product("EU AI Act Compliance Toolkit", self.text, "2026-10-14")
        self.assertEqual(res.verdict, pci.FAIL)

    def test_both_gates_agree_on_the_real_file(self):
        """Independent agreement, not one gate trusting the other."""
        import product_content_integrity as pci
        r = sg.check_generated(title="EU AI Act Compliance Toolkit",
                               topic="EU AI Act compliance", body=self.text)
        res = pci.check_product("EU AI Act Compliance Toolkit", self.text, "2026-10-14")
        self.assertFalse(r.grounded)
        self.assertEqual(res.verdict, pci.FAIL)


class TestBookGeneratorWiring(unittest.TestCase):
    """The generator must actually call the grounding, not merely import it."""

    def test_generator_references_source_grounding(self):
        src = Path("book_generator.py").read_text(encoding="utf-8")
        self.assertIn("source_grounding", src)
        self.assertIn("grounding_instruction", src)

    def test_generator_verifies_its_own_output(self):
        src = Path("book_generator.py").read_text(encoding="utf-8")
        self.assertIn("check_generated", src,
                      "generator must verify output, not only the prompt")


if __name__ == "__main__":
    unittest.main(verbosity=2)