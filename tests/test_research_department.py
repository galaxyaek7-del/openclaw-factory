"""Tests for research_department.py (EOS Phase 2, 2026-07-19): pure
assembly of already-real analysis under 7 named research categories.

Runs with stdlib unittest. Every function reads only from temp-file-
isolated fixtures -- never the real data/*.jsonl files, and never
triggers a live niche-specific analysis call.

    python -m unittest tests.test_research_department -v
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import research_department as rd


def _write_jsonl(records):
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return path


def _write_json(data):
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return path


class TestMarketResearch(unittest.TestCase):
    def tearDown(self):
        for p in getattr(self, "_paths", []):
            if os.path.exists(p):
                os.remove(p)

    def test_missing_file_returns_unknown_honestly(self):
        result = rd._market_research("/no/such/analyses.jsonl")
        self.assertEqual(result["answer"], "Unknown")

    def test_real_entries_return_a_recent_findings_list(self):
        path = _write_jsonl([
            {"niche": "a", "opportunity_gap": 50, "customer_pain": {"pain_score": 10}, "analyzed_at": "t1"},
            {"niche": "b", "opportunity_gap": 70, "customer_pain": {"pain_score": 20}, "analyzed_at": "t2"},
        ])
        self._paths = [path]
        result = rd._market_research(path, limit=5)
        self.assertEqual(len(result["recent_findings"]), 2)
        self.assertEqual(result["recent_findings"][1]["niche"], "b")

    def test_limit_respected(self):
        path = _write_jsonl([{"niche": str(i), "opportunity_gap": i, "customer_pain": {}, "analyzed_at": "t"} for i in range(10)])
        self._paths = [path]
        result = rd._market_research(path, limit=3)
        self.assertEqual(len(result["recent_findings"]), 3)


class TestCompetitorResearch(unittest.TestCase):
    def tearDown(self):
        for p in getattr(self, "_paths", []):
            if os.path.exists(p):
                os.remove(p)

    def test_empty_database_returns_unknown_honestly(self):
        path = _write_json({})
        self._paths = [path]
        result = rd._competitor_research(path)
        self.assertEqual(result["answer"], "Unknown")

    def test_real_database_reports_tracked_count(self):
        path = _write_json({"niche a": {"market_saturation": 50}, "niche b": {"market_saturation": 30}})
        self._paths = [path]
        result = rd._competitor_research(path)
        self.assertEqual(result["tracked_niches"], 2)


class TestPricingResearch(unittest.TestCase):
    def test_real_constants_never_throws(self):
        result = rd._pricing_research()
        self.assertIn("kdp_book_ceiling_usd", result)
        self.assertIn("ladder_price_band", result)


class TestBuildResearchReport(unittest.TestCase):
    def test_real_call_against_real_data_never_throws(self):
        report = rd.build_research_report()
        for key in ("market", "competitor", "pricing", "publishing", "automation", "technology", "customer"):
            self.assertIn(key, report)

    def test_technology_and_customer_are_honestly_unknown(self):
        report = rd.build_research_report()
        self.assertEqual(report["technology"]["answer"], "Unknown")
        self.assertEqual(report["customer"]["answer"], "Unknown")

    def test_render_markdown_never_throws(self):
        report = rd.build_research_report()
        md = rd.render_markdown(report)
        self.assertIsInstance(md, str)
        self.assertIn("قسم الأبحاث", md)


if __name__ == "__main__":
    unittest.main()
