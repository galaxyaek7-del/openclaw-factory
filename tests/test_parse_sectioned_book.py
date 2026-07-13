"""Regression test for book_generator._parse_sectioned_book() (code review
fix, 2026-07-13): a chapter's TITLE and CONTENT markers must pair into one
chapter entry, not two separate half-empty ones. Pre-existing bug, found
while generating today's demo products — not introduced by the English-
prompt translation, but blocking it in practice.

    python -m unittest tests.test_parse_sectioned_book -v
"""

import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import book_generator as bg


SAMPLE = """##SUBTITLE##
A compelling subtitle
##INTRODUCTION##
A real introduction paragraph.
##CHAPTER 1 TITLE##
Getting Started
##CHAPTER 1 CONTENT##
This is the real content of chapter one, at some length.
##CHAPTER 2 TITLE##
Going Deeper
##CHAPTER 2 CONTENT##
This is the real content of chapter two, at some length.
##CONCLUSION##
A real conclusion.
"""


class TestParseSectionedBook(unittest.TestCase):
    def test_chapter_count_matches_requested_not_doubled(self):
        result = bg._parse_sectioned_book(SAMPLE, expected_chapters=2)
        self.assertEqual(len(result["chapters"]), 2)

    def test_title_and_content_are_paired_correctly(self):
        result = bg._parse_sectioned_book(SAMPLE, expected_chapters=2)
        self.assertEqual(result["chapters"][0]["title"], "Getting Started")
        self.assertIn("chapter one", result["chapters"][0]["content"])
        self.assertEqual(result["chapters"][1]["title"], "Going Deeper")
        self.assertIn("chapter two", result["chapters"][1]["content"])

    def test_subtitle_introduction_conclusion_extracted(self):
        result = bg._parse_sectioned_book(SAMPLE, expected_chapters=2)
        self.assertEqual(result["subtitle"], "A compelling subtitle")
        self.assertIn("real introduction", result["introduction"])
        self.assertIn("real conclusion", result["conclusion"])

    def test_loose_single_marker_chapter_still_works(self):
        """A model that ignores the TITLE/CONTENT sub-tags and just emits
        one '##CHAPTER N##' header per chapter must still produce one
        chapter entry, not crash or drop content."""
        loose = """##SUBTITLE##
Sub
##CHAPTER 1##
Some real chapter content here.
"""
        result = bg._parse_sectioned_book(loose, expected_chapters=1)
        self.assertEqual(len(result["chapters"]), 1)
        self.assertIn("Some real chapter content", result["chapters"][0]["content"])


if __name__ == "__main__":
    unittest.main()
