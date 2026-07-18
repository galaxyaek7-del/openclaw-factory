"""Tests for product_families/ (Packaging Architecture Plan, Phase A,
2026-07-18): the registry, the common ProductSpecification builder, the
ladder->default-family mapping, and the 4 Phase A family adapters.

Real Groq calls are mocked the same way tests/test_product_package.py
already established (ai_generate_techdoc_content()/ai_generate_book_content())
except knowledge_bases, whose adapter never calls Groq at all (verbatim-only
content, by design — see product_families/families/knowledge_bases.py).

    python -m unittest tests.test_product_families -v
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
from product_families import registry
from product_families.mapping import ALL_PRODUCT_FAMILIES, resolve_product_family
from product_families.spec import (
    build_product_specification, components_to_sections, components_to_verbatim_chapters,
)

# Importing families registers the 4 real Phase A adapters as a side effect.
import product_families.families  # noqa: F401


class TestRegistry(unittest.TestCase):
    def setUp(self):
        self._saved = registry.all_families()

    def tearDown(self):
        registry.clear()
        for adapter in self._saved:
            registry.register(adapter)

    def test_phase_a_families_are_all_registered(self):
        names = {a.name for a in registry.all_families()}
        self.assertEqual(
            names,
            {"kdp_books", "professional_templates", "digital_toolkits", "knowledge_bases", "automation_systems"},
        )

    def test_unregistered_family_returns_none_not_a_guess(self):
        registry.clear()
        self.assertIsNone(registry.get("spreadsheet_systems"))

    def test_register_overrides_same_name_deliberately(self):
        class FakeAdapter:
            name = "kdp_books"

            def generate(self, spec):
                return {"success": True, "fake": True}

        registry.register(FakeAdapter())
        result = registry.get("kdp_books").generate({})
        self.assertTrue(result["fake"])


class TestLadderToFamilyMapping(unittest.TestCase):
    def test_explicit_family_always_wins(self):
        self.assertEqual(resolve_product_family("kdp_books", explicit_family="ai_saas"), "ai_saas")

    def test_default_table_applies_when_no_explicit_family(self):
        self.assertEqual(resolve_product_family("ai_saas"), "ai_saas")
        self.assertEqual(resolve_product_family("b2b_systems"), "automation_systems")
        self.assertEqual(resolve_product_family("automation_tools"), "automation_systems")
        self.assertEqual(resolve_product_family("reusable_assets"), "professional_templates")
        self.assertEqual(resolve_product_family("educational"), "knowledge_bases")
        self.assertEqual(resolve_product_family("kdp_books"), "kdp_books")

    def test_unknown_ladder_resolves_to_none_never_a_guess(self):
        self.assertIsNone(resolve_product_family("not_a_real_ladder"))
        self.assertIsNone(resolve_product_family(None))

    def test_all_default_mapping_targets_are_real_families(self):
        from product_families.mapping import DEFAULT_FAMILY_BY_LADDER
        for family in DEFAULT_FAMILY_BY_LADDER.values():
            self.assertIn(family, ALL_PRODUCT_FAMILIES)


class TestProductSpecification(unittest.TestCase):
    def test_builds_full_shape_with_defaults(self):
        spec = build_product_specification(niche="test niche", product_family="kdp_books")
        self.assertEqual(spec["niche"], "test niche")
        self.assertEqual(spec["product_family"], "kdp_books")
        self.assertEqual(spec["title"], "test niche")  # defaults to niche
        self.assertEqual(spec["topic"], "test niche")
        self.assertEqual(spec["language"], "ar")
        self.assertEqual(spec["components"], [])
        self.assertEqual(spec["family_config"], {})

    def test_explicit_title_overrides_niche_default(self):
        spec = build_product_specification(niche="n", product_family="kdp_books", title="Real Title")
        self.assertEqual(spec["title"], "Real Title")


class TestComponentsToSections(unittest.TestCase):
    def test_empty_returns_none_so_caller_falls_to_default_skeleton(self):
        self.assertIsNone(components_to_sections(None))
        self.assertIsNone(components_to_sections([]))

    def test_plain_string_component_passes_through_for_ai_generation(self):
        self.assertEqual(components_to_sections(["Overview"]), ["Overview"])

    def test_dict_with_content_is_used_verbatim(self):
        result = components_to_sections([{"title": "Intro", "content": "real text"}])
        self.assertEqual(result, [{"title": "Intro", "content": "real text"}])

    def test_dict_without_content_is_treated_as_ai_generate_title(self):
        result = components_to_sections([{"title": "Setup"}])
        self.assertEqual(result, ["Setup"])


class TestComponentsToVerbatimChapters(unittest.TestCase):
    def test_verbatim_dicts_pass_through(self):
        result = components_to_verbatim_chapters([{"title": "Article 1", "content": "real content"}])
        self.assertEqual(result, [{"title": "Article 1", "content": "real content"}])

    def test_missing_content_raises_never_fabricates(self):
        with self.assertRaises(ValueError):
            components_to_verbatim_chapters([{"title": "Article 1"}])

    def test_plain_string_component_raises_no_ai_generation_path_yet(self):
        with self.assertRaises(ValueError):
            components_to_verbatim_chapters(["Article 1"])


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


class TestKdpBooksAdapter(_CleanupPdfMixin, unittest.TestCase):
    def test_generates_a_real_pdf_via_generate_book(self):
        fake_book_data = {"introduction": "x", "chapters": [{"title": "C1", "content": "real content"}], "subtitle": ""}
        with patch.object(bg, "ai_generate_book_content", return_value=fake_book_data):
            spec = build_product_specification(
                niche="test kdp niche", product_family="kdp_books",
                family_config={"output": "test_family_kdp_books.pdf"},
            )
            result = self._track(registry.get("kdp_books").generate(spec))
        self.assertTrue(result["success"])
        self.assertTrue(os.path.exists(result["path"]))


class TestProfessionalTemplatesAdapter(_CleanupPdfMixin, unittest.TestCase):
    def test_generates_a_real_pdf_via_generate_product_package(self):
        def _fake_generated(title, topic, titles):
            return [{"title": t, "content": f"real content for {t}"} for t in titles]

        import tempfile
        tmp_changelog = tempfile.mktemp(suffix=".jsonl")
        tmp_state = tempfile.mktemp(suffix=".json")
        self.addCleanup(lambda: os.path.exists(tmp_changelog) and os.remove(tmp_changelog))
        self.addCleanup(lambda: os.path.exists(tmp_state) and os.remove(tmp_state))

        # Universal Production Engine Roadmap Step 3 (2026-07-18): this
        # family is now manifest-driven and routes through dossier_bundle,
        # which makes its own real Groq calls for marketing/support copy —
        # unmocked, this hit the REAL Groq API during a routine test run
        # (found live: real cost logged to data/ai_cost_log.jsonl). Must
        # always be mocked, same discipline as every other AI content path.
        with patch.object(bg, "ai_generate_techdoc_content", side_effect=_fake_generated), \
             patch.object(bg, "groq_chat", side_effect=RuntimeError("no network in test")), \
             patch.object(bg, "_record_rejected_niche"), \
             patch.object(bg.INSPECTORS, "_log_quarantine"):
            spec = build_product_specification(
                niche="test professional templates niche", product_family="professional_templates",
                components=["Overview", "Setup"],
                family_config={
                    "output": "test_family_professional_templates.pdf",
                    "changelog_path": tmp_changelog, "state_path": tmp_state,
                },
            )
            result = self._track(registry.get("professional_templates").generate(spec))
        self.assertTrue(result["success"])
        self.assertEqual(result["product_type"], "techdoc")
        self.assertIsNotNone(result["dossier_bundle"])


class TestDigitalToolkitsAdapter(_CleanupPdfMixin, unittest.TestCase):
    def test_generates_a_real_pdf_via_generate_product_package(self):
        def _fake_generated(title, topic, titles):
            return [{"title": t, "content": f"real content for {t}"} for t in titles]

        import tempfile
        tmp_changelog = tempfile.mktemp(suffix=".jsonl")
        tmp_state = tempfile.mktemp(suffix=".json")
        self.addCleanup(lambda: os.path.exists(tmp_changelog) and os.remove(tmp_changelog))
        self.addCleanup(lambda: os.path.exists(tmp_state) and os.remove(tmp_state))

        with patch.object(bg, "ai_generate_techdoc_content", side_effect=_fake_generated), \
             patch.object(bg, "groq_chat", side_effect=RuntimeError("no network in test")), \
             patch.object(bg, "_record_rejected_niche"), \
             patch.object(bg.INSPECTORS, "_log_quarantine"):
            spec = build_product_specification(
                niche="test digital toolkits niche", product_family="digital_toolkits",
                components=[{"title": "Checklist", "content": "real verbatim checklist content"}],
                family_config={
                    "output": "test_family_digital_toolkits.pdf",
                    "changelog_path": tmp_changelog, "state_path": tmp_state,
                },
            )
            result = self._track(registry.get("digital_toolkits").generate(spec))
        self.assertTrue(result["success"])
        self.assertIsNotNone(result["dossier_bundle"])


class TestKnowledgeBasesAdapter(_CleanupPdfMixin, unittest.TestCase):
    def test_generates_a_real_pdf_from_verbatim_components_no_groq_call(self):
        spec = build_product_specification(
            niche="test knowledge base niche", product_family="knowledge_bases",
            components=[
                {"title": "Article 1", "content": "Real article content, written verbatim."},
                {"title": "Article 2", "content": "More real article content."},
            ],
            family_config={"output": "test_family_knowledge_bases.pdf"},
        )
        result = self._track(registry.get("knowledge_bases").generate(spec))
        self.assertTrue(result["success"])
        self.assertEqual(result["content_source"], "human_claude_review")

    def test_missing_content_fails_honestly_never_a_real_pdf(self):
        spec = build_product_specification(
            niche="test knowledge base failure niche", product_family="knowledge_bases",
            components=[{"title": "Article With No Content"}],
        )
        with self.assertRaises(ValueError):
            registry.get("knowledge_bases").generate(spec)


class TestAutomationSystemsAdapter(_CleanupPdfMixin, unittest.TestCase):
    """Universal Production Engine Roadmap Step 2 (2026-07-18) — the
    first family routed through content_generation/asset_generation/
    product_packaging instead of calling book_generator.py directly."""

    def _isolated_path(self, suffix):
        import tempfile
        path = tempfile.mktemp(suffix=suffix)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        return path

    def _isolated_changelog(self):
        return self._isolated_path(".jsonl")

    def test_generates_a_real_pdf_via_the_upe_registries(self):
        def _fake_generated(title, topic, titles):
            return [{"title": t, "content": f"real content for {t}"} for t in titles]

        with patch.object(bg, "ai_generate_techdoc_content", side_effect=_fake_generated), \
             patch.object(bg, "groq_chat", side_effect=RuntimeError("no network in test")), \
             patch.object(bg, "_record_rejected_niche"), \
             patch.object(bg.INSPECTORS, "_log_quarantine"):
            spec = build_product_specification(
                # Deliberately NOT market_hunter.py's real seed niche text
                # ("workflow automation system for logistics companies") --
                # this test's thin fake content fails real Dual Inspection
                # every run, and doing that against a real, shared seed
                # niche pollutes REJECTED_NICHES.md's circuit-breaker memory
                # for a niche real Discovery actually uses (found live,
                # 2026-07-18: it broke tests/test_unified_pipeline_e2e.py).
                niche="test automation systems niche",
                product_family="automation_systems",
                production_id="PROD-automation-test-1",
                family_config={
                    "output": "test_family_automation_systems.pdf",
                    "changelog_path": self._isolated_changelog(),
                    "state_path": self._isolated_path(".json"),
                },
            )
            result = self._track(registry.get("automation_systems").generate(spec))

        self.assertTrue(result["success"])
        self.assertEqual(result["product_type"], "techdoc")
        self.assertEqual(len(result["components"]), 6)  # DEFAULT_AUTOMATION_SECTIONS
        self.assertEqual(result["package"], {
            "artifact_path": result["path"], "method": "single_file", "file_count": 1,
        })
        self.assertEqual(result["dossier_bundle"]["production_id"], "PROD-automation-test-1")
        self.assertEqual(result["dossier_bundle"]["version"], "1.0.0")
        self.assertEqual(result["dossier_bundle"]["build_manifest"]["content_generator"], "groq_techdoc")
        self.assertEqual(result["dossier_bundle"]["build_manifest"]["asset_builder"], "techdoc_package")
        self.assertEqual(result["dossier_bundle"]["build_manifest"]["packager"], "single_file")
        self.assertIsNotNone(result["dossier_bundle"]["qa_report"])
        self.assertFalse(result["dossier_bundle"]["recovery_metadata"]["had_pending_retry"])

    def test_uses_its_own_real_section_skeleton_not_the_generic_techdoc_one(self):
        from product_families.families.automation_systems import DEFAULT_AUTOMATION_SECTIONS
        self.assertEqual(
            DEFAULT_AUTOMATION_SECTIONS,
            [
                "System Overview", "Workflow Architecture", "Setup & Integration Guide",
                "Automation Triggers & Logic", "Maintenance & Troubleshooting", "ROI & Time Savings",
            ],
        )

    def test_verbatim_components_are_never_regenerated(self):
        with patch.object(bg, "ai_generate_techdoc_content") as mocked, \
             patch.object(bg, "groq_chat", side_effect=RuntimeError("no network in test")), \
             patch.object(bg, "_record_rejected_niche"), \
             patch.object(bg.INSPECTORS, "_log_quarantine"):
            spec = build_product_specification(
                niche="test automation verbatim niche", product_family="automation_systems",
                components=[{"title": "Custom Section", "content": "Already-written real content."}],
                family_config={
                    "output": "test_family_automation_systems_verbatim.pdf",
                    "changelog_path": self._isolated_changelog(),
                    "state_path": self._isolated_path(".json"),
                },
            )
            result = self._track(registry.get("automation_systems").generate(spec))
        mocked.assert_not_called()
        self.assertEqual(result["components"], [{"title": "Custom Section", "content": "Already-written real content."}])


if __name__ == "__main__":
    unittest.main()
