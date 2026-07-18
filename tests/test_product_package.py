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
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import book_generator as bg

# ADR-077: generate_product_package() now makes a REAL Groq call for any
# plain-string section (ai_generate_techdoc_content()) — with a real
# GROQ_KEY configured, an unmocked test here would spend real money and
# real time on every run. groq_chat()/ai_generate_techdoc_content() are
# mocked in every test below except TestCliDispatchAutoFillsSectionsForTechdoc's
# subprocess test, which deliberately makes the one real Groq call this
# suite performs (can't mock across a process boundary) — same discipline
# this session already applied to Telegram/Paddle (verify live once, keep
# the rest of the suite fast/free/deterministic).
_FAKE_TECHDOC_RAW = (
    "##SECTION 1 TITLE##\nOverview\n##SECTION 1 CONTENT##\nReal test overview content.\n"
    "##SECTION 2 TITLE##\nGetting Started\n##SECTION 2 CONTENT##\nReal test getting-started content."
)


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


class TestAiGenerateTechdocContent(unittest.TestCase):
    """ADR-077 — the new real content-generation path. groq_chat() is
    mocked at the lowest level here (no network, no cost) so the
    prompt-building/parsing logic itself is what's actually tested."""

    def test_parses_real_marker_format_positionally(self):
        with patch.object(bg, "groq_chat", return_value=_FAKE_TECHDOC_RAW):
            result = bg.ai_generate_techdoc_content("Test Title", "test topic", ["Overview", "Getting Started"])
        self.assertEqual(result, [
            {"title": "Overview", "content": "Real test overview content."},
            {"title": "Getting Started", "content": "Real test getting-started content."},
        ])

    def test_never_returns_empty_content_even_if_model_drops_a_section(self):
        raw = "##SECTION 1 TITLE##\nOverview\n##SECTION 1 CONTENT##\nOnly this one section came back."
        with patch.object(bg, "groq_chat", return_value=raw):
            result = bg.ai_generate_techdoc_content("T", "topic", ["Overview", "Getting Started"])
        self.assertEqual(len(result), 2)
        self.assertTrue(all(c["content"] for c in result), "every section must have non-empty content, even a dropped one")

    def test_completely_unparseable_response_still_returns_one_entry_per_section(self):
        with patch.object(bg, "groq_chat", return_value="the model ignored the format entirely"):
            result = bg.ai_generate_techdoc_content("T", "topic", ["Overview", "Getting Started", "FAQ"])
        self.assertEqual(len(result), 3)
        self.assertTrue(all(c["content"] for c in result))

    def test_groq_failure_propagates_so_caller_can_fall_back(self):
        with patch.object(bg, "groq_chat", side_effect=RuntimeError("Groq down")):
            with self.assertRaises(RuntimeError):
                bg.ai_generate_techdoc_content("T", "topic", ["Overview"])

    def test_fallback_content_is_honestly_labeled_never_claims_to_be_ai_generated(self):
        result = bg._fallback_techdoc_content("test topic", ["Overview", "FAQ"])
        self.assertEqual(len(result), 2)
        for c in result:
            self.assertIn("unavailable", c["content"].lower())


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

    def _fake_generated(self, section_titles):
        return [{"title": t, "content": f"Real test content for {t}."} for t in section_titles]

    def test_default_sections_produce_a_real_pdf_priced_as_techdoc(self):
        with patch.object(bg, "ai_generate_techdoc_content", side_effect=lambda title, topic, titles: self._fake_generated(titles)):
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

    def test_production_id_is_threaded_into_the_result_when_given(self):
        """ADR-077 Requirement #5: an explicit production_id (the same
        f"PROD-{decision_id}" production_factory/dossier.py already
        computes) must reach the generated record."""
        with patch.object(bg, "ai_generate_techdoc_content", side_effect=lambda title, topic, titles: self._fake_generated(titles)):
            result = self._track(bg.generate_product_package(
                title="Test Production Id Package",
                sections=["Overview"],
                output="test_product_package_production_id.pdf",
                production_id="PROD-dec-test-1",
            ))
        self.assertEqual(result["production_id"], "PROD-dec-test-1")

    def test_production_id_is_omitted_entirely_when_not_given(self):
        with patch.object(bg, "ai_generate_techdoc_content", side_effect=lambda title, topic, titles: self._fake_generated(titles)):
            result = self._track(bg.generate_product_package(
                title="Test No Production Id Package",
                sections=["Overview"],
                output="test_product_package_no_production_id.pdf",
            ))
        self.assertNotIn("production_id", result)

    def test_custom_plain_string_sections_are_used_as_chapter_titles(self):
        with patch.object(bg, "ai_generate_techdoc_content", side_effect=lambda title, topic, titles: self._fake_generated(titles)):
            result = self._track(bg.generate_product_package(
                title="Test Custom Sections Package",
                sections=["Intro", "API Reference"],
                output="test_product_package_custom.pdf",
            ))
        self.assertTrue(result["success"])

    def test_groq_failure_falls_back_honestly_never_crashes(self):
        # Production Activation Phase audit (2026-07-19): generate_product_package()'s
        # own except block calls factory_state.enqueue_retry("groq_generation", e)
        # with no path override (book_generator.py exposes none) -- found live,
        # this test was writing a synthetic "groq_generation" entry into the
        # REAL data/factory_state.json on every run, which Mission Control's
        # /recovery view then reported as a real pending retry. Isolated here
        # via the same DEFAULT_STATE_PATH patch technique used elsewhere.
        import factory_state
        import tempfile
        tmp_state = tempfile.mktemp(suffix=".json")
        try:
            with patch.object(bg, "ai_generate_techdoc_content", side_effect=RuntimeError("Groq unavailable")), \
                 patch.object(factory_state, "DEFAULT_STATE_PATH", Path(tmp_state)):
                result = self._track(bg.generate_product_package(
                    title="Test Fallback Package",
                    sections=["Overview"],
                    output="test_product_package_fallback.pdf",
                ))
            self.assertTrue(result["success"], "a Groq failure must degrade to the honest fallback, never crash generation")
        finally:
            if os.path.exists(tmp_state):
                os.remove(tmp_state)

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
    """Runs the real CLI as a subprocess — cannot mock groq_chat() across a
    process boundary, so the first test below makes ONE real Groq call
    (ADR-077's real content generation). Deliberate, not an oversight: this
    is the single real-integration proof for the whole techdoc content
    path; every other test in this file mocks ai_generate_techdoc_content()
    to stay fast/free/deterministic."""

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
