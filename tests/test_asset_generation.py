"""Tests for asset_generation/ (Universal Production Engine Roadmap Step
1, 2026-07-18): the registry + the two real PDF builders wrapping
book_generator.py's already-tested full generation pipelines.

Real Groq calls are mocked the same way tests/test_product_families.py
already established; the real PDF/cover rendering pipeline runs for
real, and produced files are cleaned up afterward.

    python -m unittest tests.test_asset_generation -v
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import book_generator as bg
from asset_generation import registry
import asset_generation.builders  # noqa: F401 — self-registers


class TestRegistry(unittest.TestCase):
    def setUp(self):
        self._saved = registry.all_builders()

    def tearDown(self):
        registry.clear()
        for builder in self._saved:
            registry.register(builder)

    def test_real_builders_are_registered(self):
        names = {b.name for b in registry.all_builders()}
        self.assertEqual(names, {"ai_book", "techdoc_package"})

    def test_unregistered_builder_returns_none_not_a_guess(self):
        registry.clear()
        self.assertIsNone(registry.get("ai_book"))

    def test_register_overrides_same_name_deliberately(self):
        class FakeBuilder:
            name = "ai_book"

            def build(self, spec):
                return {"fake": True}

        registry.register(FakeBuilder())
        result = registry.get("ai_book").build({})
        self.assertTrue(result["fake"])


class _CleanupPdfMixin:
    def setUp(self):
        self._created_paths = []

    def tearDown(self):
        for p in self._created_paths:
            try:
                os.remove(p)
            except OSError:
                pass

    def _track(self, result):
        if result.get("path"):
            self._created_paths.append(result["path"])
        if result.get("cover") and result["cover"].get("path"):
            self._created_paths.append(result["cover"]["path"])
        return result


class TestAiBookAssetBuilder(_CleanupPdfMixin, unittest.TestCase):
    def test_generates_a_real_pdf_via_generate_book(self):
        fake_book_data = {"introduction": "x", "chapters": [{"title": "C1", "content": "real content"}], "subtitle": ""}
        with patch.object(bg, "ai_generate_book_content", return_value=fake_book_data):
            spec = {
                "title": "test asset ai_book niche",
                "topic": "test asset ai_book niche",
                "price_hint": 9.99,
                "family_config": {"output": "test_asset_ai_book.pdf"},
            }
            result = self._track(registry.get("ai_book").build(spec))
        self.assertTrue(result["success"])
        self.assertTrue(os.path.exists(result["path"]))

    def test_defaults_match_kdp_books_adapter(self):
        with patch.object(bg, "generate_book") as mocked:
            mocked.return_value = {"success": True}
            registry.get("ai_book").build({"title": "T"})
        mocked.assert_called_once_with(
            title="T", topic="", chapters=8, audience="القارئ العام",
            price=9.99, theme="blue", author="Galaxy Forge Press", output=None,
        )


class TestTechdocPackageAssetBuilder(_CleanupPdfMixin, unittest.TestCase):
    def test_generates_a_real_pdf_via_generate_product_package(self):
        def _fake_generated(title, topic, titles):
            return [{"title": t, "content": f"real content for {t}"} for t in titles]

        with patch.object(bg, "ai_generate_techdoc_content", side_effect=_fake_generated):
            spec = {
                "title": "test asset techdoc niche",
                "components": ["Overview", "Setup"],
                "price_hint": 197.0,
                "family_config": {"output": "test_asset_techdoc_package.pdf"},
            }
            result = self._track(registry.get("techdoc_package").build(spec))
        self.assertTrue(result["success"])
        self.assertEqual(result["product_type"], "techdoc")

    def test_passes_production_id_through(self):
        with patch.object(bg, "generate_product_package") as mocked:
            mocked.return_value = {"success": True}
            registry.get("techdoc_package").build({"title": "T", "production_id": "PROD-x"})
        self.assertEqual(mocked.call_args.kwargs["production_id"], "PROD-x")


if __name__ == "__main__":
    unittest.main()
