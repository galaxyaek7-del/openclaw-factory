"""Tests for content_generation/ (Universal Production Engine Roadmap
Step 1, 2026-07-18): the registry + the two real Groq-backed generators
wrapping book_generator.py's already-tested content functions.

    python -m unittest tests.test_content_generation -v
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import book_generator as bg
import content_generation.generators.groq_generator as groq_gen
from content_generation import registry
import content_generation.generators  # noqa: F401 — self-registers


class TestRegistry(unittest.TestCase):
    def setUp(self):
        self._saved = registry.all_generators()

    def tearDown(self):
        registry.clear()
        for gen in self._saved:
            registry.register(gen)

    def test_real_generators_are_registered(self):
        names = {g.name for g in registry.all_generators()}
        self.assertEqual(names, {"groq_book", "groq_techdoc"})

    def test_unregistered_generator_returns_none_not_a_guess(self):
        registry.clear()
        self.assertIsNone(registry.get("groq_book"))

    def test_register_overrides_same_name_deliberately(self):
        class FakeGenerator:
            name = "groq_book"

            def generate(self, request):
                return {"fake": True}

        registry.register(FakeGenerator())
        result = registry.get("groq_book").generate({})
        self.assertTrue(result["fake"])


class TestGroqBookContentGenerator(unittest.TestCase):
    def test_returns_real_book_data_shape_on_success(self):
        fake_book_data = {
            "subtitle": "s", "introduction": "i",
            "chapters": [{"title": "C1", "content": "real content"}],
            "conclusion": "c",
        }
        with patch.object(bg, "ai_generate_book_content", return_value=fake_book_data) as mocked:
            result = registry.get("groq_book").generate(
                {"title": "T", "topic": "test topic", "chapter_count": 3, "audience": "devs"}
            )
        mocked.assert_called_once_with("T", "test topic", 3, "devs")
        self.assertEqual(result, fake_book_data)

    def test_falls_back_honestly_on_groq_failure_never_raises(self):
        with patch.object(bg, "ai_generate_book_content", side_effect=RuntimeError("groq down")), \
             patch.object(groq_gen.factory_state, "enqueue_retry") as mocked_retry:
            result = registry.get("groq_book").generate({"title": "T", "topic": "test topic", "production_id": "PROD-1"})
        self.assertIn("chapters", result)
        mocked_retry.assert_called_once()
        self.assertEqual(mocked_retry.call_args.kwargs["context"]["production_id"], "PROD-1")

    def test_defaults_topic_to_title_and_audience_when_omitted(self):
        with patch.object(bg, "ai_generate_book_content", return_value={"chapters": []}) as mocked:
            registry.get("groq_book").generate({"title": "Only Title"})
        mocked.assert_called_once_with("Only Title", "Only Title", 8, "القارئ العام")


class TestGroqTechdocContentGenerator(unittest.TestCase):
    def test_returns_components_shape_on_success(self):
        def _fake(title, topic, titles):
            return [{"title": t, "content": f"real content for {t}"} for t in titles]

        with patch.object(bg, "ai_generate_techdoc_content", side_effect=_fake):
            result = registry.get("groq_techdoc").generate(
                {"title": "T", "topic": "test topic", "section_titles": ["Overview", "Setup"]}
            )
        self.assertEqual(
            result,
            {"components": [
                {"title": "Overview", "content": "real content for Overview"},
                {"title": "Setup", "content": "real content for Setup"},
            ]},
        )

    def test_falls_back_honestly_on_groq_failure_never_raises(self):
        with patch.object(bg, "ai_generate_techdoc_content", side_effect=RuntimeError("groq down")), \
             patch.object(groq_gen.factory_state, "enqueue_retry") as mocked_retry:
            result = registry.get("groq_techdoc").generate(
                {"title": "T", "topic": "test topic", "section_titles": ["Overview"], "production_id": "PROD-2"}
            )
        self.assertEqual(len(result["components"]), 1)
        self.assertEqual(result["components"][0]["title"], "Overview")
        mocked_retry.assert_called_once()
        self.assertEqual(mocked_retry.call_args.kwargs["context"]["production_id"], "PROD-2")


if __name__ == "__main__":
    unittest.main()
