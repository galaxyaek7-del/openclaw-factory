"""Tests for text_sanitizer -- the black-box fix.

Cycle 87 measured 40,259 black-box glyphs across 44 of 114 shipped PDFs. These
tests pin the cause and the fix, and they assert that the substitution table
covers EVERY codepoint that actually fails, so the table cannot silently fall
behind the font.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import text_sanitizer as ts

UNSAFE = ["\u2010", "\u2011", "\u2012", "\u2015", "\u2016",
          "\u2017", "\u201b", "\u201f", "\u00a0", "\ufffd"]


class TestSubstitution(unittest.TestCase):
    def test_unicode_hyphen_becomes_ascii_hyphen(self):
        r = ts.sanitize_for_pdf("Post\u2010Removal and 30\u2011day")
        self.assertEqual(r.text, "Post-Removal and 30-day")

    def test_invisible_chars_removed(self):
        invisible = ["\u200b", "\u200c", "\u200d", "\ufeff", "\ufffd"]
        s = "".join("a" + c for c in invisible) + "z"
        r = ts.sanitize_for_pdf(s)
        self.assertEqual(r.text, "a" * len(invisible) + "z")
        self.assertEqual(r.removed, len(invisible))

    def test_nbsp_becomes_space(self):
        self.assertEqual(ts.sanitize_for_pdf("a\u00a0b").text, "a b")

    def test_real_dashes_are_preserved(self):
        """Em/en dash DO render. Rewriting them would be a regression."""
        for ch in ("\u2013", "\u2014"):
            r = ts.sanitize_for_pdf(f"a{ch}b")
            self.assertEqual(r.text, f"a{ch}b")
            self.assertFalse(r.changed)

    def test_clean_text_unchanged(self):
        s = "Normal text with an em—dash and plain ASCII."
        r = ts.sanitize_for_pdf(s)
        self.assertEqual(r.text, s)
        self.assertFalse(r.changed)

    def test_empty_input_safe(self):
        self.assertEqual(ts.sanitize_for_pdf("").text, "")
        self.assertEqual(ts.sanitize_for_pdf(None).text, "")

    def test_report_counts_codepoints(self):
        r = ts.sanitize_for_pdf("\u2010\u2010\u2011")
        self.assertEqual(r.substitutions.get("U+2010"), 2)
        self.assertIn("U+2011", r.substitutions)


class TestTableCoversMeasuredFailures(unittest.TestCase):
    """The table must cover every codepoint that actually fails to render."""

    def test_no_uncovered_failing_codepoint(self):
        measured = ts.unsafe_codepoints()
        failing = [k for k, ok in measured.items() if not ok]
        self.assertTrue(failing, "measurement itself returned nothing")
        uncovered = []
        for key in failing:
            ch = chr(int(key[2:], 16))
            if ch not in ts.SUBSTITUTIONS:
                uncovered.append(key)
        self.assertEqual(uncovered, [],
                         f"measured-failing codepoints with no substitution: {uncovered}")

    def test_every_known_unsafe_char_is_covered(self):
        for ch in UNSAFE:
            self.assertIn(ch, ts.SUBSTITUTIONS,
                          f"U+{ord(ch):04X} is known-unsafe but unmapped")


class TestSanitizeStructure(unittest.TestCase):
    def test_walks_nested_book_data(self):
        data = {
            "title": "Post\u2010Removal",
            "chapters": [{"title": "A\u2011B", "content": "c\u00a0d"}],
            "introduction": "intro \u2015 dash",
            "meta": {"note": "nested \u2010 dash"},
        }
        out, report = ts.sanitize_structure(data)
        self.assertEqual(out["title"], "Post-Removal")
        self.assertEqual(out["chapters"][0]["title"], "A-B")
        self.assertEqual(out["chapters"][0]["content"], "c d")
        self.assertEqual(out["introduction"], "intro - dash")
        self.assertEqual(out["meta"]["note"], "nested - dash")
        self.assertTrue(report.changed)

    def test_numbers_and_none_pass_through(self):
        out, _ = ts.sanitize_structure({"price": 15500, "x": None, "f": 1.5})
        self.assertEqual(out["price"], 15500)
        self.assertIsNone(out["x"])
        self.assertEqual(out["f"], 1.5)

    def test_original_object_not_mutated_in_place(self):
        data = {"title": "A\u2010B"}
        ts.sanitize_structure(data)
        self.assertEqual(data["title"], "A\u2010B",
                         "caller's object must not be mutated")


class TestGeneratorIntegration(unittest.TestCase):
    """The fix must be live in the real pipeline, not just the module."""

    def test_create_ai_book_references_sanitizer(self):
        src = Path("book_generator.py").read_text(encoding="utf-8")
        self.assertIn("text_sanitizer", src)
        self.assertIn("sanitize_structure", src)

    def test_generated_pdf_has_no_black_boxes(self):
        import book_generator as bg
        from pypdf import PdfReader
        out = Path(tempfile.gettempdir()) / "gf_sanitize_proof.pdf"
        chapters = [
            {"title": "Post\u2010Removal",
             "content": "30\u2011day window\u00a0dash \u2015 end."},
            {"title": "Plain", "content": "Ordinary ascii content here."},
        ]
        bg.create_ai_book(str(out), "Proof", "", "blue", "GF",
                          {"chapters": chapters, "introduction": ""}, topic="t")
        text = "\n".join((p.extract_text() or "") for p in PdfReader(str(out)).pages)
        import re
        self.assertEqual(re.findall(r"[\u25a0\ufffd]", text), [],
                         "the generated PDF still contains black boxes")
        out.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)