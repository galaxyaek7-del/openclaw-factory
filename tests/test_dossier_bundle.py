"""Tests for dossier_bundle/build_bundle.py (Universal Production Engine
Roadmap Step 1, 2026-07-18): the mandatory per-product artifact bundle —
documentation, metadata, marketing, support, update history.

Real Groq calls are mocked (same discipline as every other AI-content
test in this suite); the changelog write always targets an isolated
temp path, never the real data/product_changelog.jsonl (Test Isolation
Discipline established during the Unified Recovery System's own review).

    python -m unittest tests.test_dossier_bundle -v
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import book_generator as bg
import dossier_bundle.build_bundle as bb


class TestBuildDocumentation(unittest.TestCase):
    def test_assembles_readme_from_real_components(self):
        spec = {
            "title": "Test Product",
            "subtitle": "A real subtitle",
            "components": [{"title": "Overview", "content": "Real overview content."}],
        }
        doc = bb._build_documentation(spec)
        self.assertIn("# Test Product", doc)
        self.assertIn("A real subtitle", doc)
        self.assertIn("## Overview", doc)
        self.assertIn("Real overview content.", doc)

    def test_missing_components_produces_honest_minimal_doc_not_filler(self):
        doc = bb._build_documentation({"title": "Bare Product"})
        self.assertEqual(doc, "# Bare Product\n")


class TestMarketingCopy(unittest.TestCase):
    def test_parses_real_groq_response_into_fields(self):
        raw = (
            "##HEADLINE##\nBuy This Now\n"
            "##DESCRIPTION##\nA real description.\n"
            "##KEYWORDS##\nkeyword1, keyword2"
        )
        with patch.object(bg, "groq_chat", return_value=raw):
            result = bb._generate_marketing_copy({"title": "T", "niche": "n"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["content"]["headline"], "Buy This Now")
        self.assertEqual(result["content"]["description"], "A real description.")
        self.assertEqual(result["content"]["keywords"], "keyword1, keyword2")

    def test_falls_back_honestly_on_groq_failure_never_raises(self):
        with patch.object(bg, "groq_chat", side_effect=RuntimeError("groq down")):
            result = bb._generate_marketing_copy({"title": "T", "niche": "n"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["source"], "fallback")
        self.assertIn("unavailable", result["content"]["description"])


class TestSupportCopy(unittest.TestCase):
    def test_returns_real_groq_content_on_success(self):
        with patch.object(bg, "groq_chat", return_value="Q: real question?\nA: real answer."):
            result = bb._generate_support_copy({"title": "T", "niche": "n"})
        self.assertTrue(result["ok"])
        self.assertIn("real question", result["content"])

    def test_falls_back_honestly_on_groq_failure_never_raises(self):
        with patch.object(bg, "groq_chat", side_effect=RuntimeError("groq down")):
            result = bb._generate_support_copy({"title": "T", "niche": "n"})
        self.assertFalse(result["ok"])
        self.assertIn("unavailable", result["content"])


class TestAppendChangelog(unittest.TestCase):
    def setUp(self):
        self.tmp_path = tempfile.mktemp(suffix=".jsonl")

    def tearDown(self):
        if os.path.exists(self.tmp_path):
            os.remove(self.tmp_path)

    def test_appends_a_real_jsonl_line_to_the_isolated_path(self):
        ok = bb._append_changelog(
            "PROD-1", {"title": "T", "product_family": "digital_toolkits"},
            {"published": True}, "1.0.0", changelog_path=self.tmp_path,
        )
        self.assertTrue(ok)
        with open(self.tmp_path, encoding="utf-8") as f:
            entry = json.loads(f.readline())
        self.assertEqual(entry["production_id"], "PROD-1")
        self.assertEqual(entry["product_family"], "digital_toolkits")
        self.assertEqual(entry["version"], "1.0.0")
        self.assertTrue(entry["published"])

    def test_logging_failure_never_raises(self):
        ok = bb._append_changelog("PROD-1", {}, {}, "1.0.0", changelog_path="\x00invalid\x00path")
        self.assertFalse(ok)


class TestNextVersion(unittest.TestCase):
    def setUp(self):
        self.tmp_path = tempfile.mktemp(suffix=".jsonl")

    def tearDown(self):
        if os.path.exists(self.tmp_path):
            os.remove(self.tmp_path)

    def test_no_prior_history_is_1_0_0(self):
        self.assertEqual(bb._next_version("PROD-new", self.tmp_path), "1.0.0")

    def test_no_production_id_is_1_0_0(self):
        self.assertEqual(bb._next_version(None, self.tmp_path), "1.0.0")

    def test_bumps_minor_for_each_real_prior_entry_with_the_same_id(self):
        with open(self.tmp_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"production_id": "PROD-1"}) + "\n")
            f.write(json.dumps({"production_id": "PROD-1"}) + "\n")
            f.write(json.dumps({"production_id": "PROD-other"}) + "\n")
        self.assertEqual(bb._next_version("PROD-1", self.tmp_path), "1.2.0")
        self.assertEqual(bb._next_version("PROD-other", self.tmp_path), "1.1.0")
        self.assertEqual(bb._next_version("PROD-never-seen", self.tmp_path), "1.0.0")


class TestBuildManifest(unittest.TestCase):
    def test_real_fields_assembled_honestly(self):
        spec = {"product_family": "automation_systems", "title": "T"}
        generation_result = {"path": "/x/out.pdf", "cover": {"path": "/x/cover.png"}}
        manifest = bb._build_manifest(
            spec, generation_result, "PROD-1", "1.0.0",
            content_generator="groq_techdoc", asset_builder="techdoc_package", packager="single_file",
        )
        self.assertEqual(manifest["production_id"], "PROD-1")
        self.assertEqual(manifest["version"], "1.0.0")
        self.assertEqual(manifest["product_family"], "automation_systems")
        self.assertEqual(manifest["files"], ["/x/out.pdf", "/x/cover.png"])
        self.assertEqual(manifest["content_generator"], "groq_techdoc")
        self.assertEqual(manifest["asset_builder"], "techdoc_package")
        self.assertEqual(manifest["packager"], "single_file")
        self.assertIn("spec_hash", manifest)

    def test_unspecified_registry_names_are_honestly_none_not_guessed(self):
        manifest = bb._build_manifest({}, {}, "PROD-1", "1.0.0")
        self.assertIsNone(manifest["content_generator"])
        self.assertIsNone(manifest["asset_builder"])
        self.assertIsNone(manifest["packager"])
        self.assertEqual(manifest["files"], [])


class TestRecoveryMetadata(unittest.TestCase):
    def setUp(self):
        self.tmp_state_path = tempfile.mktemp(suffix=".json")

    def tearDown(self):
        if os.path.exists(self.tmp_state_path):
            os.remove(self.tmp_state_path)

    def test_no_pending_retries_is_honestly_empty(self):
        result = bb._recovery_metadata("PROD-1", state_path=self.tmp_state_path)
        self.assertFalse(result["had_pending_retry"])
        self.assertEqual(result["pending_retries"], [])

    def test_finds_only_the_matching_production_id(self):
        import factory_state
        factory_state.enqueue_retry(
            "groq_generation", RuntimeError("x"),
            path=self.tmp_state_path, context={"production_id": "PROD-1"},
        )
        factory_state.enqueue_retry(
            "groq_generation", RuntimeError("y"),
            path=self.tmp_state_path, context={"production_id": "PROD-other"},
        )
        result = bb._recovery_metadata("PROD-1", state_path=self.tmp_state_path)
        self.assertTrue(result["had_pending_retry"])
        self.assertEqual(len(result["pending_retries"]), 1)
        self.assertEqual(result["pending_retries"][0]["context"]["production_id"], "PROD-1")


class TestBuildProductDossierBundle(unittest.TestCase):
    def setUp(self):
        self.tmp_path = tempfile.mktemp(suffix=".jsonl")
        self.tmp_state_path = tempfile.mktemp(suffix=".json")

    def tearDown(self):
        for p in (self.tmp_path, self.tmp_state_path):
            if os.path.exists(p):
                os.remove(p)

    def test_full_bundle_shape_without_a_decision(self):
        spec = {
            "production_id": "PROD-1",
            "title": "Test Product",
            "niche": "test niche",
            "product_family": "digital_toolkits",
            "components": [{"title": "Overview", "content": "Real content."}],
        }
        generation_result = {
            "production_id": "PROD-1", "published": True, "price": 197.0, "cover": None,
            "inspection": {"passed": True, "published": True},
        }

        with patch.object(bg, "groq_chat", side_effect=RuntimeError("no network in test")):
            bundle = bb.build_product_dossier_bundle(
                spec, generation_result, changelog_path=self.tmp_path, state_path=self.tmp_state_path,
            )

        self.assertEqual(bundle["production_id"], "PROD-1")
        self.assertEqual(bundle["version"], "1.0.0")
        self.assertIn("# Test Product", bundle["documentation"])
        self.assertEqual(bundle["metadata"]["product_family"], "digital_toolkits")
        self.assertIn("no Decision supplied", bundle["metadata"]["note"])
        self.assertFalse(bundle["marketing"]["ok"])
        self.assertFalse(bundle["support"]["ok"])
        self.assertEqual(bundle["qa_report"], {"passed": True, "published": True})
        self.assertFalse(bundle["recovery_metadata"]["had_pending_retry"])
        self.assertEqual(bundle["build_manifest"]["production_id"], "PROD-1")
        self.assertEqual(bundle["build_manifest"]["version"], "1.0.0")
        self.assertTrue(bundle["changelog_appended"])
        self.assertEqual(bundle["lifecycle_status"], "active")

    def test_second_build_of_the_same_production_id_bumps_the_version(self):
        spec = {"production_id": "PROD-repeat", "title": "T"}
        generation_result = {"production_id": "PROD-repeat", "published": True}
        with patch.object(bg, "groq_chat", side_effect=RuntimeError("no network in test")):
            first = bb.build_product_dossier_bundle(
                spec, generation_result, changelog_path=self.tmp_path, state_path=self.tmp_state_path,
            )
            second = bb.build_product_dossier_bundle(
                spec, generation_result, changelog_path=self.tmp_path, state_path=self.tmp_state_path,
            )
        self.assertEqual(first["version"], "1.0.0")
        self.assertEqual(second["version"], "1.1.0")

    def test_production_id_falls_back_to_spec_when_missing_from_result(self):
        spec = {"production_id": "PROD-spec-fallback", "title": "T"}
        with patch.object(bg, "groq_chat", side_effect=RuntimeError("no network in test")):
            bundle = bb.build_product_dossier_bundle(
                spec, {}, changelog_path=self.tmp_path, state_path=self.tmp_state_path,
            )
        self.assertEqual(bundle["production_id"], "PROD-spec-fallback")

    def test_reuses_real_dossier_metadata_when_decision_supplied(self):
        fake_metadata = {"production_id": "PROD-1", "niche": "n"}
        spec = {"production_id": "PROD-1", "title": "T"}
        with patch.object(bg, "groq_chat", side_effect=RuntimeError("no network in test")), \
             patch("production_factory.dossier.build_production_dossier", return_value=fake_metadata) as mocked:
            bundle = bb.build_product_dossier_bundle(
                spec, {}, decision={"decision_id": "x"},
                changelog_path=self.tmp_path, state_path=self.tmp_state_path,
            )
        mocked.assert_called_once_with({"decision_id": "x"})
        self.assertEqual(bundle["metadata"], fake_metadata)

    def test_passes_registry_names_through_to_the_build_manifest(self):
        spec = {"production_id": "PROD-1", "title": "T"}
        with patch.object(bg, "groq_chat", side_effect=RuntimeError("no network in test")):
            bundle = bb.build_product_dossier_bundle(
                spec, {}, changelog_path=self.tmp_path, state_path=self.tmp_state_path,
                content_generator="groq_techdoc", asset_builder="techdoc_package", packager="single_file",
            )
        self.assertEqual(bundle["build_manifest"]["content_generator"], "groq_techdoc")
        self.assertEqual(bundle["build_manifest"]["asset_builder"], "techdoc_package")
        self.assertEqual(bundle["build_manifest"]["packager"], "single_file")


if __name__ == "__main__":
    unittest.main()
