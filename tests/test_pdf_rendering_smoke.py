"""Smoke test for the actual PDF-rendering path (red-team audit follow-up,
MEDIUM finding: book_generator.py's 2600+-line rendering path had zero
automated verification that it produces a valid, non-corrupt PDF — only
pre-render parsing/dispatch logic was tested). Opens the real rendered
output with pypdf (already a pinned dependency, requirements.txt) and
asserts page count and non-zero size — a rendering regression (broken
layout, corrupt PDF, wrong page count) now fails CI, not just manual
inspection.

    python -m unittest tests.test_pdf_rendering_smoke -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import book_generator as bg


class TestCreateBookRendersAValidPdf(unittest.TestCase):
    def test_create_book_journal_produces_a_valid_readable_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_path = os.path.join(tmp, "smoke_test_journal.pdf")
            n_pages = bg.create_book(
                out_path,
                title="Smoke Test Journal",
                subtitle="Regression coverage for the rendering path",
                ptype="journal",
                theme="blue",
                pages=6,
                author="Regression Suite",
            )

            self.assertTrue(os.path.exists(out_path))
            self.assertGreater(os.path.getsize(out_path), 0, "rendered PDF must not be empty")

            reader = PdfReader(out_path)
            self.assertGreater(len(reader.pages), 0, "rendered PDF must have at least one real page")
            self.assertEqual(len(reader.pages), n_pages, "reported page count must match the actual PDF")

    def test_create_book_cookbook_produces_a_valid_readable_pdf(self):
        # cookbook routes through create_cookbook() internally (a separate
        # code path, see create_book()'s ptype=='cookbook' dispatch) — worth
        # covering directly since it's the historical original demo path.
        with tempfile.TemporaryDirectory() as tmp:
            out_path = os.path.join(tmp, "smoke_test_cookbook.pdf")
            n_pages = bg.create_book(
                out_path,
                title="Smoke Test Cookbook",
                subtitle="Regression coverage",
                ptype="cookbook",
                theme="orange",
                pages=6,
                author="Regression Suite",
            )

            self.assertTrue(os.path.exists(out_path))
            self.assertGreater(os.path.getsize(out_path), 0)

            reader = PdfReader(out_path)
            self.assertGreater(len(reader.pages), 0)
            self.assertEqual(len(reader.pages), n_pages)


if __name__ == "__main__":
    unittest.main()
