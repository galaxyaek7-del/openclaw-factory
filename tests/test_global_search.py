import json
import os
import tempfile
import unittest
from unittest.mock import patch

import global_search as gs


class TestGlobalSearch(unittest.TestCase):
    def test_empty_query_returns_empty_honestly(self):
        result = gs.search("")
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["results"], [])

    def test_discloses_unindexed_sources(self):
        result = gs.search("x")
        self.assertIn("customers (0 real records exist)", result["sources_not_indexed"])

    def test_knowledge_graph_match_case_insensitive(self):
        with tempfile.TemporaryDirectory() as tmp:
            kg_path = os.path.join(tmp, "kg.json")
            with open(kg_path, "w", encoding="utf-8") as f:
                json.dump({"generated_at": "2026-08-07", "nodes": [{"id": "niche:X", "type": "Niche", "label": "EU AI Act Toolkit"}]}, f)
            with patch.object(gs, "_KG_SNAPSHOT_PATH", kg_path), \
                 patch.object(gs, "_COMPETITOR_DB_PATH", os.path.join(tmp, "nope.json")), \
                 patch.object(gs, "_GENERATION_LOG_PATH", os.path.join(tmp, "nope.jsonl")):
                result = gs.search("eu ai act")
                self.assertEqual(result["total"], 1)
                self.assertEqual(result["results"][0]["source"], "knowledge_graph")

    def test_no_relevance_score_invented(self):
        result = gs.search("compliance")
        for r in result["results"]:
            self.assertNotIn("relevance_score", r)
            self.assertNotIn("confidence", r)

    def test_generated_products_dedupes_by_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "gen.jsonl")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(json.dumps({"title": "Widget Toolkit", "price": 100, "file": "a.pdf"}) + "\n")
                f.write(json.dumps({"title": "Widget Toolkit", "price": 155, "file": "b.pdf"}) + "\n")
            with patch.object(gs, "_KG_SNAPSHOT_PATH", os.path.join(tmp, "nope.json")), \
                 patch.object(gs, "_COMPETITOR_DB_PATH", os.path.join(tmp, "nope2.json")), \
                 patch.object(gs, "_GENERATION_LOG_PATH", log_path):
                result = gs.search("widget")
                self.assertEqual(result["total"], 1)

    def test_truncates_and_reports_truncation(self):
        with tempfile.TemporaryDirectory() as tmp:
            kg_path = os.path.join(tmp, "kg.json")
            nodes = [{"id": f"niche:{i}", "type": "Niche", "label": f"match item {i}"} for i in range(5)]
            with open(kg_path, "w", encoding="utf-8") as f:
                json.dump({"generated_at": "2026-08-07", "nodes": nodes}, f)
            with patch.object(gs, "_KG_SNAPSHOT_PATH", kg_path), \
                 patch.object(gs, "_COMPETITOR_DB_PATH", os.path.join(tmp, "nope.json")), \
                 patch.object(gs, "_GENERATION_LOG_PATH", os.path.join(tmp, "nope.jsonl")):
                result = gs.search("match", limit=2)
                self.assertEqual(len(result["results"]), 2)
                self.assertEqual(result["total"], 5)
                self.assertTrue(result["truncated"])


if __name__ == "__main__":
    unittest.main()
