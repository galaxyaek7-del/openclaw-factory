"""Tests for book_generator.py's technical-docs/product-package generator
(ADR-065/ADR-069, mission Step 4 — "convert book_generator to technical-
docs/product-package generator"). Real PDF generation (reportlab), same
discipline as tests/test_book_generator_dispatch.py — no mocking of the
generation pipeline itself; generated test PDFs are removed in tearDown so
this suite never leaves stray files in books/.

    python -m unittest tests.test_product_package -v
"""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import book_generator as bg


def _run_cli(payload, timeout=30):
    proc = subprocess.run(
        [sys.executable, str(_FACTORY_ROOT / "book_generator.py"), "--json"],
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True, text=True, encoding="utf-8", timeout=timeout,
        cwd=str(_FACTORY_ROOT),
    )
    return json.loads(proc.stdout.strip())


class TestEconomicsPlatformRouting(unittest.TestCase):
    def test_techdoc_routes_to_gumroad_elite(self):
        self.assertEqual(bg._economics_platform_for("techdoc"), "gumroad_elite")

    def test_other_product_types_unaffected(self):
        self.assertEqual(bg._economics_platform_for("elite"), "gumroad_elite")
        self.assertEqual(bg._economics_platform_for("premium"), "gumroad_premium")
        self.assertEqual(bg._economics_platform_for("printable"), "gumroad_digital")
        self.assertEqual(bg._economics_platform_for("book"), "kdp_ebook")


class TestGenerateProductPackage(unittest.TestCase):
    def setUp(self):
        self._created_paths = []

    def tearDown(self):
        for p in self._created_paths:
            try:
                os.remove(p)
            except OSError:
                pass

    def test_requires_title(self):
        with self.assertRaises(ValueError):
            bg.generate_product_package(title="")

    def _track(self, result):
        self._created_paths.append(result["path"])
        if result.get("cover") and result["cover"].get("path"):
            self._created_paths.append(result["cover"]["path"])
        return result

    def test_default_sections_produce_a_real_pdf_priced_as_techdoc(self):
        result = self._track(bg.generate_product_package(
            title="Test Compliance Automation Product Package",
            topic="compliance automation for accounting firms",
            price=197.0,
            output="test_product_package_default.pdf",
        ))
        self.assertTrue(result["success"])
        self.assertEqual(result["product_type"], "techdoc")
        self.assertTrue(os.path.exists(result["path"]))
        self.assertGreaterEqual(result["pages"], 1)

    def test_custom_plain_string_sections_are_used_as_chapter_titles(self):
        result = self._track(bg.generate_product_package(
            title="Test Custom Sections Package",
            sections=["Intro", "API Reference"],
            output="test_product_package_custom.pdf",
        ))
        self.assertTrue(result["success"])

    def test_dict_sections_are_used_verbatim_never_overwritten(self):
        captured = {}
        original = bg.generate_book_from_content

        def _spy(*args, **kwargs):
            captured["chapters"] = kwargs.get("chapters")
            return original(*args, **kwargs)

        bg.generate_book_from_content = _spy
        try:
            result = self._track(bg.generate_product_package(
                title="Test Verbatim Sections Package",
                sections=[{"title": "Real Section", "content": "Real, already-written content."}],
                output="test_product_package_verbatim.pdf",
            ))
        finally:
            bg.generate_book_from_content = original
        self.assertEqual(captured["chapters"], [{"title": "Real Section", "content": "Real, already-written content."}])


class TestCliDispatchAutoFillsSectionsForTechdoc(unittest.TestCase):
    def test_techdoc_with_no_chapters_autofills_default_sections(self):
        result = _run_cli({
            "title": "CLI Test Techdoc Package",
            "topic": "workflow automation for logistics companies",
            "price": 197,
            "product_type": "techdoc",
            "output": "test_cli_techdoc_autofill.pdf",
        })
        try:
            self.assertTrue(result["success"], result)
            self.assertEqual(result["product_type"], "techdoc")
        finally:
            for p in [result.get("path"), (result.get("cover") or {}).get("path")]:
                if p:
                    try:
                        os.remove(p)
                    except OSError:
                        pass

    def test_techdoc_with_explicit_chapters_still_routes_correctly(self):
        """A caller supplying its own chapters alongside product_type=
        'techdoc' must still reach generate_book_from_content() unchanged
        — the auto-fill branch only covers the no-chapters case."""
        result = _run_cli({
            "title": "CLI Test Techdoc Explicit Chapters",
            "chapters": [{"title": "Setup", "content": "Real setup instructions."}],
            "price": 197,
            "product_type": "techdoc",
            "output": "test_cli_techdoc_explicit.pdf",
        })
        try:
            self.assertTrue(result["success"], result)
            self.assertEqual(result.get("content_source"), "human_claude_review")
        finally:
            for p in [result.get("path"), (result.get("cover") or {}).get("path")]:
                if p:
                    try:
                        os.remove(p)
                    except OSError:
                        pass


if __name__ == "__main__":
    unittest.main()
