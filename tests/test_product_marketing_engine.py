"""Tests for product_marketing_engine.py (Commercial Execution Engine v1,
ADR-180, 2026-08-06). Every real AI call (ai_capability.orchestrator.
generate()) is mocked -- this suite never depends on live Groq
availability, matching this project's established convention (see
tests/test_autonomous_business_builder.py's own identical discipline).

    python -m unittest tests.test_product_marketing_engine -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import product_marketing_engine as pme


def _temp_path(suffix=".jsonl"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


_SAMPLE_RAW_OUTPUT = """## 1. POSITIONING
Real positioning text for the test niche.

## 2. PRICING_STRATEGY
Real pricing text.

## 3. GUMROAD_PAGE
Real Gumroad page copy.

## 4. SALES_PAGE
Real sales page copy.

## 5. SEO_PACKAGE
Real SEO package.

## 6. TAGS
tag1, tag2, tag3

## 7. LAUNCH_CHECKLIST
- step one
- step two

## 8. MARKETING_ASSETS
Real marketing asset copy.

## 9. EMAIL_CAMPAIGN
Real email campaign copy.

## 10. SOCIAL_MEDIA_CAMPAIGN
Real social copy.

## 11. CUSTOMER_ACQUISITION_PLAN
Real acquisition plan.

## 12. CONTINUOUS_OPTIMIZATION_PLAN
Real optimization plan.
"""


class TestParseCommercialKitSections(unittest.TestCase):
    def test_all_12_named_sections_are_parsed(self):
        sections = pme._parse_commercial_kit_sections(_SAMPLE_RAW_OUTPUT)
        self.assertEqual(set(sections.keys()), set(pme.SECTION_NAMES))
        for name in pme.SECTION_NAMES:
            self.assertTrue(sections[name], f"{name} should not be empty")

    def test_missing_section_is_honestly_empty_never_a_crash(self):
        partial = "## 1. POSITIONING\nOnly this one section exists.\n"
        sections = pme._parse_commercial_kit_sections(partial)
        self.assertEqual(sections["positioning"], "Only this one section exists.")
        for name in pme.SECTION_NAMES:
            if name != "positioning":
                self.assertEqual(sections[name], "")

    def test_completely_unparseable_text_never_raises(self):
        sections = pme._parse_commercial_kit_sections("no headers at all, just prose")
        self.assertEqual(set(sections.keys()), set(pme.SECTION_NAMES))
        self.assertTrue(all(v == "" for v in sections.values()))


class TestGatherRealProductFacts(unittest.TestCase):
    def test_honestly_none_price_when_no_signal_exists(self):
        with patch("commercial_intelligence.build_commercial_intelligence_report", return_value=None):
            facts = pme._gather_real_product_facts("a niche with no decision")
        self.assertIsNone(facts["price"])
        self.assertIsNone(facts["commercial_intelligence"])

    def test_explicit_price_always_wins_over_any_real_signal(self):
        fake_intel = {"price_ranges": {"this_decision_price": 19.99}}
        with patch("commercial_intelligence.build_commercial_intelligence_report", return_value=fake_intel):
            facts = pme._gather_real_product_facts("a niche", price=349)
        self.assertEqual(facts["price"], 349)

    def test_real_signal_price_used_when_no_explicit_price_given(self):
        fake_intel = {"price_ranges": {"this_decision_price": 39.0}}
        with patch("commercial_intelligence.build_commercial_intelligence_report", return_value=fake_intel):
            facts = pme._gather_real_product_facts("a niche")
        self.assertEqual(facts["price"], 39.0)


class TestGenerateCommercialKit(unittest.TestCase):
    def test_real_generation_call_never_a_second_ai_calling_mechanism(self):
        """Must dispatch through ai_capability.orchestrator.generate() --
        this factory's one real, named multi-model routing entrypoint --
        never a direct/duplicate Groq call."""
        fake_result = {"content": _SAMPLE_RAW_OUTPUT, "provider": "groq", "selection": {}}
        fake_brand_check = {"passed": True, "failed_checks": [], "results": {}}
        with patch("commercial_intelligence.build_commercial_intelligence_report", return_value=None), \
             patch("ai_capability.orchestrator.generate", return_value=fake_result) as mock_gen, \
             patch("brand_dna.validate_customer_facing_text", return_value=fake_brand_check):
            kit = pme.generate_commercial_kit("a niche", price=349, title="Test Product")
        mock_gen.assert_called_once()
        self.assertEqual(mock_gen.call_args[0][0], "writing")
        self.assertEqual(kit["provider"], "groq")
        self.assertTrue(kit["brand_check"]["passed"])
        self.assertEqual(len(kit["sections"]), 12)

    def test_brand_check_is_always_run_never_skipped(self):
        fake_result = {"content": _SAMPLE_RAW_OUTPUT, "provider": "groq", "selection": {}}
        fake_brand_check = {"passed": False, "failed_checks": ["fake_urgency"], "results": {}}
        with patch("commercial_intelligence.build_commercial_intelligence_report", return_value=None), \
             patch("ai_capability.orchestrator.generate", return_value=fake_result), \
             patch("brand_dna.validate_customer_facing_text", return_value=fake_brand_check) as mock_brand:
            kit = pme.generate_commercial_kit("a niche", price=349, title="Test Product")
        mock_brand.assert_called_once()
        self.assertFalse(kit["brand_check"]["passed"])
        self.assertIn("fake_urgency", kit["brand_check"]["failed_checks"])


class TestRenderCommercialKitMarkdown(unittest.TestCase):
    def test_renders_all_12_sections_and_never_crashes_on_a_missing_one(self):
        kit = {
            "facts": {"title": "Test Product"},
            "generated_at": "2026-08-06T00:00:00Z",
            "provider": "groq",
            "brand_check": {"passed": True, "failed_checks": []},
            "sections": {"positioning": "real text"},  # only 1 of 12 present
        }
        md = pme.render_commercial_kit_markdown(kit)
        self.assertIn("real text", md)
        self.assertIn("not generated", md)  # honest placeholder for the other 11

    def test_failed_brand_check_is_visibly_reported(self):
        kit = {
            "facts": {"title": "Test Product"},
            "generated_at": "2026-08-06T00:00:00Z",
            "provider": "groq",
            "brand_check": {"passed": False, "failed_checks": ["fake_urgency"]},
            "sections": {},
        }
        md = pme.render_commercial_kit_markdown(kit)
        self.assertIn("FAILED", md)
        self.assertIn("fake_urgency", md)


class TestReadGeneratedKitNiches(unittest.TestCase):
    def test_missing_file_is_an_empty_set(self):
        path = _temp_path()
        self.assertEqual(pme._read_generated_kit_niches(path), set())

    def test_reads_niches_and_skips_blank_and_malformed_lines(self):
        path = _temp_path()
        with open(path, "w", encoding="utf-8") as f:
            f.write('{"niche": "a", "decision_id": "d1"}\n')
            f.write("\n")
            f.write("not json\n")
            f.write('{"niche": "b", "decision_id": "d2"}\n')
        try:
            self.assertEqual(pme._read_generated_kit_niches(path), {"a", "b"})
        finally:
            os.remove(path)


class TestRecordGeneratedKit(unittest.TestCase):
    def test_appends_a_record_without_overwriting_existing_ones(self):
        path = _temp_path()
        try:
            pme._record_generated_kit("a", "d1", path)
            pme._record_generated_kit("b", "d2", path)
            self.assertEqual(pme._read_generated_kit_niches(path), {"a", "b"})
        finally:
            os.remove(path)


class TestGeneratePendingCommercialKits(unittest.TestCase):
    def test_generates_up_to_limit_and_records_them(self):
        accepted = [
            {"decision_id": "d1", "niche": "n1", "status": "ACCEPTED"},
            {"decision_id": "d2", "niche": "n2", "status": "ACCEPTED"},
            {"decision_id": "d3", "niche": "n3", "status": "ACCEPTED"},
        ]
        path = _temp_path()
        try:
            with patch("decision_engine.ranking.rank_all", return_value=accepted), \
                 patch("product_marketing_engine.generate_commercial_kit", return_value={"niche": "x"}) as mock_gen:
                result = pme.generate_pending_commercial_kits(limit=2, ledger_path=path)
            self.assertEqual(result["total_accepted"], 3)
            self.assertEqual(len(result["generated"]), 2)
            self.assertEqual(result["remaining_pending"], 1)
            self.assertEqual(pme._read_generated_kit_niches(path), {"n1", "n2"})
            self.assertEqual(mock_gen.call_count, 2)
        finally:
            os.remove(path)

    def test_never_regenerates_an_already_covered_niche(self):
        accepted = [
            {"decision_id": "d1", "niche": "n1", "status": "ACCEPTED"},
            {"decision_id": "d2", "niche": "n2", "status": "ACCEPTED"},
        ]
        path = _temp_path()
        try:
            pme._record_generated_kit("n1", "d1", path)
            with patch("decision_engine.ranking.rank_all", return_value=accepted), \
                 patch("product_marketing_engine.generate_commercial_kit", return_value={"niche": "x"}) as mock_gen:
                result = pme.generate_pending_commercial_kits(limit=2, ledger_path=path)
            mock_gen.assert_called_once()
            self.assertEqual(result["generated"], [{"niche": "n2", "decision_id": "d2"}])
            self.assertEqual(result["remaining_pending"], 0)
        finally:
            os.remove(path)

    def test_zero_or_negative_limit_generates_nothing(self):
        accepted = [{"decision_id": "d1", "niche": "n1", "status": "ACCEPTED"}]
        path = _temp_path()
        try:
            with patch("decision_engine.ranking.rank_all", return_value=accepted), \
                 patch("product_marketing_engine.generate_commercial_kit") as mock_gen:
                result_zero = pme.generate_pending_commercial_kits(limit=0, ledger_path=path)
                result_negative = pme.generate_pending_commercial_kits(limit=-1, ledger_path=path)
            mock_gen.assert_not_called()
            self.assertEqual(result_zero["generated"], [])
            self.assertEqual(result_zero["remaining_pending"], 1)
            self.assertEqual(result_negative["generated"], [])
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_non_accepted_decisions_are_never_considered(self):
        mixed = [
            {"decision_id": "d1", "niche": "n1", "status": "DEFERRED"},
            {"decision_id": "d2", "niche": "n2", "status": "REJECTED"},
            {"decision_id": "d3", "niche": "n3", "status": "ACCEPTED"},
        ]
        path = _temp_path()
        try:
            with patch("decision_engine.ranking.rank_all", return_value=mixed), \
                 patch("product_marketing_engine.generate_commercial_kit", return_value={"niche": "x"}) as mock_gen:
                result = pme.generate_pending_commercial_kits(limit=5, ledger_path=path)
            self.assertEqual(result["total_accepted"], 1)
            mock_gen.assert_called_once()
            self.assertEqual(result["generated"], [{"niche": "n3", "decision_id": "d3"}])
        finally:
            os.remove(path)


class TestListGeneratedCommercialKits(unittest.TestCase):
    def test_missing_file_is_honestly_empty(self):
        path = _temp_path()
        result = pme.list_generated_commercial_kits(ledger_path=path)
        self.assertEqual(result, {"entries": [], "count": 0})

    def test_most_recent_first(self):
        path = _temp_path()
        try:
            pme._record_generated_kit("a", "d1", path)
            pme._record_generated_kit("b", "d2", path)
            result = pme.list_generated_commercial_kits(ledger_path=path)
            self.assertEqual(result["count"], 2)
            self.assertEqual(result["entries"][0]["niche"], "b")
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
