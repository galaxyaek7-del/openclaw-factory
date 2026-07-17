"""Tests for path_safety.py — the shared safe-output-path confinement
extracted from book_generator.py/cover_designer_v2.py's two previously
independent (and subtly different) implementations (standing-charter
continuous-improvement follow-up, zero-assumption audit Section C).

    python -m unittest tests.test_path_safety -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import path_safety as ps


class TestSanitizeFilenameComponent(unittest.TestCase):
    def test_preserves_arabic_and_ascii_word_characters(self):
        self.assertEqual(ps.sanitize_filename_component("My Book"), "my_book")
        self.assertEqual(ps.sanitize_filename_component("كتابي الجميل"), "كتابي_الجميل")

    def test_collapses_special_characters_to_a_single_underscore(self):
        self.assertEqual(ps.sanitize_filename_component("a/../../b"), "a_b")
        self.assertEqual(ps.sanitize_filename_component("weird!!!name???"), "weird_name")

    def test_empty_or_none_falls_back(self):
        self.assertEqual(ps.sanitize_filename_component(""), "file")
        self.assertEqual(ps.sanitize_filename_component(None), "file")
        self.assertEqual(ps.sanitize_filename_component("", fallback="custom"), "custom")

    def test_truncates_to_max_length(self):
        long_text = "a" * 200
        result = ps.sanitize_filename_component(long_text)
        self.assertLessEqual(len(result), 80)

    def test_idempotent_on_an_already_sanitized_string(self):
        once = ps.sanitize_filename_component("My Weird Title!!")
        twice = ps.sanitize_filename_component(once)
        self.assertEqual(once, twice)


class TestConfineToDirectory(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        for f in os.listdir(self.tmpdir):
            os.remove(os.path.join(self.tmpdir, f))
        os.rmdir(self.tmpdir)

    def test_no_candidate_name_uses_the_sanitized_fallback_stem(self):
        out_path, filename = ps.confine_to_directory(self.tmpdir, None, "My Title", ".pdf")
        self.assertEqual(filename, "my_title.pdf")
        self.assertTrue(out_path.startswith(os.path.realpath(self.tmpdir)))

    def test_traversal_attempt_in_candidate_name_is_confined(self):
        out_path, filename = ps.confine_to_directory(self.tmpdir, "../../../etc/passwd", "fallback", ".pdf")
        self.assertNotIn("..", filename)
        real_dir = os.path.realpath(self.tmpdir)
        self.assertEqual(os.path.commonpath([out_path, real_dir]), real_dir)

    def test_absolute_path_candidate_name_is_confined(self):
        fake_absolute = os.path.join(self.tmpdir, "..", "escaped.pdf")
        out_path, filename = ps.confine_to_directory(self.tmpdir, fake_absolute, "fallback", ".pdf")
        real_dir = os.path.realpath(self.tmpdir)
        self.assertEqual(os.path.commonpath([out_path, real_dir]), real_dir)

    def test_candidate_names_extension_is_replaced_with_the_given_ext(self):
        _, filename = ps.confine_to_directory(self.tmpdir, "my_file.txt", "fallback", ".pdf")
        self.assertEqual(filename, "my_file.pdf")

    def test_empty_candidate_name_falls_back_cleanly(self):
        _, filename = ps.confine_to_directory(self.tmpdir, "", "My Title", ".png")
        self.assertEqual(filename, "my_title.png")


if __name__ == "__main__":
    unittest.main()
