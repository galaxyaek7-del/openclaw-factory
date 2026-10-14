"""Tests for product_content_integrity -- the Cycle 86 content gate.

Deliberately per-rule, not one generic "does it pass" test. A gate that only
gets a happy-path test cannot tell whether a rule works or merely never
fires -- which is exactly how the first draft of check_content_padding passed
silently on the real document it was written for.

Each test asserts a rule FIRES on a known-bad sample, because a rule that
never fires looks identical to a working one.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import product_content_integrity as pci

TODAY = "2026-10-14"


class TestFabricatedAnnexCitation(unittest.TestCase):
    """The defect that motivated this entire module."""

    BAD = "Annex III, Part A, category 1: Autonomy - system documentation"
    GOOD = ("Annex III lists high-risk systems in areas including biometrics, "
            "critical infrastructure, and law enforcement.")

    def test_fires_on_real_fabricated_category(self):
        f = pci.check_fabricated_annex_citation(self.BAD)
        self.assertTrue(f, "must fire on a fabricated Annex III category")
        self.assertEqual(f[0].rule, "FABRICATED_CITATION")
        self.assertEqual(f[0].severity, "CRITICAL")

    def test_fires_on_each_non_annex_term(self):
        for term in pci.NON_ANNEX_III_TERMS:
            with self.subTest(term=term):
                f = pci.check_fabricated_annex_citation(f"Annex III covers {term}")
                self.assertTrue(f, f"must fire on {term!r}")

    def test_quiet_on_real_categories(self):
        self.assertEqual(pci.check_fabricated_annex_citation(self.GOOD), [])

    def test_real_categories_would_not_be_flagged(self):
        for cat in pci.EU_AI_ACT_ANNEX_III_CATEGORIES:
            with self.subTest(category=cat):
                self.assertEqual(
                    pci.check_fabricated_annex_citation(f"Annex III: {cat}"), [])

    def test_plain_text_without_annex_reference_is_quiet(self):
        self.assertEqual(pci.check_fabricated_annex_citation("hello world"), [])


class TestInventedAnnexStructure(unittest.TestCase):
    def test_fires_on_part_a(self):
        self.assertTrue(pci.check_invented_annex_structure("Annex III, Part A")["::"] if False
                        else pci.check_invented_annex_structure("Annex III, Part A"))

    def test_fires_on_part_b(self):
        f = pci.check_invented_annex_structure("limited-risk in Annex III, Part B")
        self.assertTrue(f)
        self.assertEqual(f[0].rule, "INVENTED_STRUCTURE")

    def test_quiet_on_plain_annex_iii(self):
        self.assertEqual(pci.check_invented_annex_structure("see Annex III"), [])


class TestFalseProhibition(unittest.TestCase):
    BAD = "1. Prohibit the use of high-risk general-purpose AI models."

    def test_fires_on_the_real_defect(self):
        f = pci.check_false_prohibition(self.BAD)
        self.assertTrue(f)
        self.assertEqual(f[0].severity, "CRITICAL")

    def test_quiet_on_correct_gpai_wording(self):
        self.assertEqual(
            pci.check_false_prohibition(
                "GPAI models carry the obligations set out in Chapter V."),
            [])


class TestMarkdownLeakage(unittest.TestCase):
    def test_fires_on_literal_bold(self):
        f = pci.check_markdown_leakage("**Provider** -- the organisation")
        self.assertTrue(f)
        self.assertEqual(f[0].severity, "MINOR")

    def test_quiet_on_plain_text(self):
        self.assertEqual(pci.check_markdown_leakage("Provider -- the org"), [])

    def test_counts_multiple(self):
        f = pci.check_markdown_leakage("**a** and **b** and **c**")
        self.assertIn("3 literal", f[0].evidence)


class TestTruncatedHeading(unittest.TestCase):
    def test_fires_on_mid_word_cut(self):
        f = pci.check_truncated_headings("A Decision-Tree Chec")
        self.assertTrue(f)

    def test_quiet_on_complete_heading(self):
        self.assertEqual(pci.check_truncated_headings("A Decision-Tree Checklist"), [])


class TestContentPadding(unittest.TestCase):
    """
    Regression test for the rule that silently never fired. Its first draft
    used the mean, which the long reference chapters inflated to 112 words on
    the real product, so it reported nothing. The median is 72. This test
    pins the behaviour so it cannot silently regress again.
    """

    @staticmethod
    def _doc(sizes):
        parts = []
        for i, w in enumerate(sizes):
            parts.append(f"\nCHAPTER {i}\n" + ("word " * w))
        return "".join(parts)

    def test_fires_when_median_is_thin_despite_long_references(self):
        # 4 long reference chapters + 19 thin ones == the real document's shape
        doc = self._doc([300, 250, 340, 240] + [60] * 19)
        f = pci.check_content_padding(doc)
        self.assertTrue(f, "must fire on a mostly-thin document")
        self.assertEqual(f[0].rule, "CONTENT_PADDING")

    def test_mean_only_rule_would_have_missed_this(self):
        """Proves the old mean-based logic fails on exactly this shape."""
        doc = self._doc([300, 250, 340, 240] + [60] * 19)
        counts = sorted(len(c.split()) for c in
                        doc.split("\nCHAPTER")[1:] if c.strip())
        mean = sum(counts) / len(counts)
        self.assertGreater(mean, 60, "mean sits above the old 60-word floor")
        self.assertTrue(pci.check_content_padding(doc), "median rule still fires")

    def test_quiet_when_chapters_are_substantial(self):
        doc = self._doc([400] * 10)
        self.assertEqual(pci.check_content_padding(doc), [])

    def test_reports_non_evaluation_on_too_short_a_document(self):
        """Changed in the Cycle 86 repair: this used to return []. Silence is
        not a pass -- a rule that cannot evaluate must say so."""
        f = pci.check_content_padding("CHAPTER 1\ntiny")
        self.assertTrue(f)
        self.assertIn("NOT EVALUATED", f[0].evidence)


class TestStaleVerification(unittest.TestCase):
    def test_fires_when_old(self):
        f = pci.check_stale_verification("verified 2026-08-06", TODAY)
        self.assertTrue(f)
        self.assertEqual(f[0].severity, "MAJOR")

    def test_quiet_when_recent(self):
        self.assertEqual(
            pci.check_stale_verification("verified 2026-10-10", TODAY), [])


class TestAiArtifacts(unittest.TestCase):
    def test_fires_on_llm_marker(self):
        self.assertTrue(pci.check_ai_artifacts("Certainly! Here is the answer"))

    def test_quiet_on_clean_text(self):
        self.assertEqual(pci.check_ai_artifacts("A normal compliance sentence."), [])


class TestGuaranteeLanguage(unittest.TestCase):
    def test_fires_on_compliance_guarantee(self):
        f = pci.check_guarantee_language("We guarantee compliance for your firm.")
        self.assertTrue(f)
        self.assertEqual(f[0].severity, "CRITICAL")

    def test_quiet_on_proper_hedging(self):
        self.assertEqual(
            pci.check_guarantee_language(
                "This is not legal advice and does not guarantee compliance."),
            [])


class TestVerdictLogic(unittest.TestCase):
    def test_critical_forces_fail(self):
        res = pci.check_product("p", "Annex III, Part A, category 1: Autonomy", TODAY)
        self.assertEqual(res.verdict, pci.FAIL)
        self.assertGreater(res.critical_count, 0)

    def test_clean_text_passes(self):
        """A genuine PASS requires a document the rules CAN evaluate --
        i.e. real chapters, so CONTENT_PADDING is not 'NOT EVALUATED'."""
        doc = "\n".join(
            # 80 x 2 words = 160, comfortably above the 150-word padding floor
            f"CHAPTER {i}\n" + ("substantive content " * 80)
            for i in range(1, 6))
        res = pci.check_product("p", doc, TODAY)
        self.assertEqual(res.verdict, pci.PASS,
                         "a fully clean, evaluable document may pass")

    def test_short_clean_document_does_not_earn_a_pass(self):
        """The repair's whole point: no findings produced because a rule
        could not run is not the same as no findings because all is well."""
        res = pci.check_product("p", "A short clean document.", TODAY)
        self.assertNotEqual(res.verdict, pci.PASS)

    def test_legal_review_always_required(self):
        res = pci.check_product("p", "clean text", TODAY)
        self.assertTrue(pci.legal_review_required(res),
                        "a mechanical pass is never clearance")


class TestGateCannotDeclarePassEarly(unittest.TestCase):
    """
    Cycle 86 repair: the gate must never report PASS for work it did not
    actually complete. Two real fail-open paths existed and are now closed.
    """

    def test_padding_rule_reports_when_it_cannot_evaluate(self):
        """It used to return an EMPTY list -- indistinguishable from a pass."""
        f = pci.check_content_padding("CHAPTER 1\ntiny")
        self.assertTrue(f, "must report non-evaluation, not silence")
        self.assertIn("NOT EVALUATED", f[0].evidence)

    def test_unevaluable_document_is_never_a_clean_pass(self):
        res = pci.check_product("p", "one chapter only\nCHAPTER 1\nshort", TODAY)
        self.assertNotEqual(res.verdict, pci.PASS)

    def test_a_crashing_rule_becomes_critical_not_silence(self):
        """If any rule raises, the gate must record it as unchecked."""
        original = pci.check_guarantee_language

        def boom(_text):
            raise RuntimeError("simulated rule failure")

        pci.check_guarantee_language = boom
        try:
            res = pci.check_product("p", "clean text entirely", TODAY)
        finally:
            pci.check_guarantee_language = original

        rules = {f.rule for f in res.findings}
        self.assertIn("RULE_ERROR", rules)
        self.assertNotEqual(res.verdict, pci.PASS,
                            "a partial run must never read as a clean pass")

    def test_every_rule_is_invoked_even_when_one_fails(self):
        """A crash in rule 1 must not skip rules 2-9."""
        calls = []
        originals = {}
        for name in ("check_fabricated_annex_citation", "check_invented_annex_structure",
                     "check_false_prohibition", "check_ai_artifacts",
                     "check_markdown_leakage", "check_truncated_headings",
                     "check_content_padding", "check_stale_verification"):
            originals[name] = getattr(pci, name)

        def wrap(fn):
            def inner(t, *a, **k):
                calls.append(fn.__name__)
                return fn(t, *a, **k)
            return inner

        for name, fn in list(originals.items()):
            setattr(pci, name, wrap(fn))
        pci.check_fabricated_annex_citation = lambda t: (_ for _ in ()).throw(
            RuntimeError("first rule dies"))
        try:
            res = pci.check_product("p", "text", TODAY)
        finally:
            for name, fn in originals.items():
                setattr(pci, name, fn)

        # 9 rules run in total; one is deliberately replaced with a thrower,
        # leaving 7 wrapped rules that must still execute after it dies.
        self.assertEqual(len(calls), 7,
                         "all remaining rules must still run after one dies")
        self.assertEqual(len(set(calls)), 7, "no rule ran twice")
        self.assertNotEqual(res.verdict, pci.PASS)


class TestRealProductIsHeld(unittest.TestCase):
    """The end-to-end regression that matters most."""

    @unittest.skipUnless(
        Path("data/cycle86_toolkit_text.txt").exists(),
        "real extracted product text not present")
    def test_real_toolkit_is_on_hold(self):
        text = Path("data/cycle86_toolkit_text.txt").read_text(encoding="utf-8")
        res = pci.check_product("EU AI Act Compliance Toolkit", text, TODAY)
        self.assertEqual(res.verdict, pci.FAIL,
                         "the shipped product must fail until content is fixed")
        rules = {f.rule for f in res.findings}
        self.assertIn("FABRICATED_CITATION", rules)
        self.assertIn("FALSE_PROHIBITION", rules)


if __name__ == "__main__":
    unittest.main(verbosity=2)