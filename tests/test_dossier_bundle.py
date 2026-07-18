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
            {"published": True}, changelog_path=self.tmp_path,
        )
        self.assertTrue(ok)
        with open(self.tmp_path, encoding="utf-8") as f:
            entry = json.loads(f.readline())
        self.assertEqual(entry["production_id"], "PROD-1")
        self.assertEqual(entry["product_family"], "digital_toolkits")
        self.assertTrue(entry["published"])

    def test_logging_failure_never_raises(self):
        ok = bb._append_changelog("PROD-1", {}, {}, changelog_path="\x00invalid\x00path")
        self.assertFalse(ok)


class TestBuildProductDossierBundle(unittest.TestCase):
    def setUp(self):
        self.tmp_path = tempfile.mktemp(suffix=".jsonl")

    def tearDown(self):
        if os.path.exists(self.tmp_path):
            os.remove(self.tmp_path)

    def test_full_bundle_shape_without_a_decision(self):
        spec = {
            "production_id": "PROD-1",
            "title": "Test Product",
            "niche": "test niche",
            "product_family": "digital_toolkits",
            "components": [{"title": "Overview", "content": "Real content."}],
        }
        generation_result = {"production_id": "PROD-1", "published": True, "price": 197.0, "cover": None}

        with patch.object(bg, "groq_chat", side_effect=RuntimeError("no network in test")):
            bundle = bb.build_product_dossier_bundle(spec, generation_result, changelog_path=self.tmp_path)

        self.assertEqual(bundle["production_id"], "PROD-1")
        self.assertIn("# Test Product", bundle["documentation"])
        self.assertEqual(bundle["metadata"]["product_family"], "digital_toolkits")
        self.assertIn("no Decision supplied", bundle["metadata"]["note"])
        self.assertFalse(bundle["marketing"]["ok"])
        self.assertFalse(bundle["support"]["ok"])
        self.assertTrue(bundle["changelog_appended"])

    def test_production_id_falls_back_to_spec_when_missing_from_result(self):
        spec = {"production_id": "PROD-spec-fallback", "title": "T"}
        with patch.object(bg, "groq_chat", side_effect=RuntimeError("no network in test")):
            bundle = bb.build_product_dossier_bundle(spec, {}, changelog_path=self.tmp_path)
        self.assertEqual(bundle["production_id"], "PROD-spec-fallback")

    def test_reuses_real_dossier_metadata_when_decision_supplied(self):
        fake_metadata = {"production_id": "PROD-1", "niche": "n"}
        spec = {"production_id": "PROD-1", "title": "T"}
        with patch.object(bg, "groq_chat", side_effect=RuntimeError("no network in test")), \
             patch.object(bb, "build_production_dossier", return_value=fake_metadata) as mocked:
            bundle = bb.build_product_dossier_bundle(spec, {}, decision={"decision_id": "x"}, changelog_path=self.tmp_path)
        mocked.assert_called_once_with({"decision_id": "x"})
        self.assertEqual(bundle["metadata"], fake_metadata)


if __name__ == "__main__":
    unittest.main()
