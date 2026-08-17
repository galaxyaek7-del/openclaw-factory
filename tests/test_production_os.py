"""Tests for production_os.py (Production OS, ADR-203, 2026-08-17):
Build 1 -- the real caller of build_product_dossier_bundle(); Build 2 --
the read-only Product Lifecycle view.

Real Groq calls are mocked (same discipline as every other AI-content
test); the changelog/state writes always target isolated temp paths,
never the real data/product_changelog.jsonl or factory_state.json.

    python -m unittest tests.test_production_os -v
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
import production_os as pos


def _write_genlog(tmp_dir, records):
    path = Path(tmp_dir) / "generation_log.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return str(path)


_REAL_RECORD = {
    "production_id": "PROD-abc123",
    "topic": "automated compliance workflow system for mid-size logistics firms",
    "price": 327,
    "pages": 8,
    "path": "/books/out.pdf",
    "cover": {"path": "/books/cover.png"},
    "inspection": {"passed": True, "published": True},
    "published": True,
    "success": True,
    "timestamp": "2026-07-18T23:44:00",
}


class TestBuildProductBundle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.changelog = os.path.join(self.tmp, "changelog.jsonl")
        self.state = os.path.join(self.tmp, "state.json")

    def test_is_the_real_caller_of_build_product_dossier_bundle(self):
        with patch.object(bg, "groq_chat", side_effect=RuntimeError("no network in test")):
            bundle = pos.build_product_bundle(
                "PROD-abc123",
                generation_log_path=_write_genlog(self.tmp, [_REAL_RECORD]),
                changelog_path=self.changelog, state_path=self.state,
            )
        self.assertEqual(bundle["production_id"], "PROD-abc123")
        self.assertEqual(bundle["version"], "1.0.0")
        self.assertEqual(bundle["qa_report"], {"passed": True, "published": True})
        self.assertTrue(bundle["changelog_appended"])
        self.assertIn("automated compliance workflow system", bundle["documentation"])
        self.assertEqual(bundle["build_manifest"]["files"], ["/books/out.pdf", "/books/cover.png"])

    def test_writes_real_changelog_version_entry(self):
        with patch.object(bg, "groq_chat", side_effect=RuntimeError("no network in test")):
            first = pos.build_product_bundle(
                "PROD-abc123",
                generation_log_path=_write_genlog(self.tmp, [_REAL_RECORD]),
                changelog_path=self.changelog, state_path=self.state,
            )
            second = pos.build_product_bundle(
                "PROD-abc123",
                generation_log_path=_write_genlog(self.tmp, [_REAL_RECORD]),
                changelog_path=self.changelog, state_path=self.state,
            )
        self.assertEqual(first["version"], "1.0.0")
        self.assertEqual(second["version"], "1.1.0")

    def test_no_real_record_returns_honest_not_found(self):
        result = pos.build_product_bundle(
            "PROD-unknown-xyz",
            generation_log_path=_write_genlog(self.tmp, []),
            changelog_path=self.changelog, state_path=self.state,
        )
        self.assertFalse(result["bundle_built"])
        self.assertIn("no real books/_generation_log.jsonl record", result["reason"])

    def test_latest_record_wins_when_multiple_exist(self):
        older = dict(_REAL_RECORD, timestamp="2026-07-18T00:00:00", price=100)
        newer = dict(_REAL_RECORD, timestamp="2026-07-19T00:00:00", price=250)
        with patch.object(bg, "groq_chat", side_effect=RuntimeError("no network in test")):
            bundle = pos.build_product_bundle(
                "PROD-abc123",
                generation_log_path=_write_genlog(self.tmp, [older, newer]),
                changelog_path=self.changelog, state_path=self.state,
            )
        self.assertEqual(bundle["metadata"]["pricing_strategy"]["recommended_price"], 250)

    def test_accepts_only_real_accepted_decision_for_full_metadata(self):
        real_decision = {"decision_id": "abc123", "niche": "x", "status": "ACCEPTED"}
        with patch.object(bg, "groq_chat", side_effect=RuntimeError("no network in test")), \
             patch("factory_orchestrator.find_decision", return_value=real_decision) as mocked:
            bundle = pos.build_product_bundle(
                "PROD-abc123",
                generation_log_path=_write_genlog(self.tmp, [_REAL_RECORD]),
                changelog_path=self.changelog, state_path=self.state,
            )
        mocked.assert_called_once()
        # full production dossier was built (not the reduced no-decision shape)
        self.assertIn("market_positioning", bundle["metadata"])
        self.assertIn("customer_profile", bundle["metadata"])


class TestProductLifecycleView(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_reads_real_log_and_groups_by_production_id(self):
        records = [
            dict(_REAL_RECORD, production_id="PROD-1", topic="niche alpha", timestamp="2026-07-18T00:00:00"),
            dict(_REAL_RECORD, production_id="PROD-1", topic="niche alpha", timestamp="2026-07-19T00:00:00", pages=9),
            dict(_REAL_RECORD, production_id="PROD-2", topic="niche beta", timestamp="2026-07-20T00:00:00"),
        ]
        view = pos.product_lifecycle_view(
            limit=10, classify_limit=0,
            generation_log_path=_write_genlog(self.tmp, records),
            changelog_path=os.path.join(self.tmp, "changelog.jsonl"),
            decisions_path=os.path.join(self.tmp, "d.jsonl"),
            timeline_path=os.path.join(self.tmp, "t.jsonl"),
            outcomes_path=os.path.join(self.tmp, "o.jsonl"),
        )
        self.assertEqual(view["total_real_production_ids_in_log"], 2)
        by_pid = {p["production_id"]: p for p in view["products"]}
        self.assertEqual(by_pid["PROD-1"]["pages"], 9)
        self.assertEqual(by_pid["PROD-1"]["price"], 327)
        self.assertEqual(by_pid["PROD-2"]["topic"], "niche beta")

    def test_test_markers_are_excluded(self):
        records = [
            dict(_REAL_RECORD, production_id="PROD-1", topic="real niche", timestamp="2026-07-18T00:00:00"),
            dict(_REAL_RECORD, production_id="PROD-dec-test-1", topic="test niche", timestamp="2026-07-19T00:00:00"),
            dict(_REAL_RECORD, production_id="PROD-demo-config-only", topic="demo niche", timestamp="2026-07-20T00:00:00"),
        ]
        view = pos.product_lifecycle_view(
            limit=10, classify_limit=0,
            generation_log_path=_write_genlog(self.tmp, records),
            changelog_path=os.path.join(self.tmp, "changelog.jsonl"),
        )
        self.assertEqual(view["total_real_production_ids_in_log"], 1)
        self.assertEqual(view["products"][0]["production_id"], "PROD-1")

    def test_classify_limit_bounds_real_classification(self):
        records = [
            dict(_REAL_RECORD, production_id=f"PROD-{i}", topic=f"distinct niche {i}",
                 timestamp=f"2026-07-2{i}T00:00:00")
            for i in range(6)
        ]
        with patch("value_engine.classify_lifecycle_stage", return_value={"current_stage": "prototype", "stages": {}}) as mocked:
            view = pos.product_lifecycle_view(
                limit=10, classify_limit=2,
                generation_log_path=_write_genlog(self.tmp, records),
                changelog_path=os.path.join(self.tmp, "changelog.jsonl"),
                decisions_path=os.path.join(self.tmp, "d.jsonl"),
                timeline_path=os.path.join(self.tmp, "t.jsonl"),
                outcomes_path=os.path.join(self.tmp, "o.jsonl"),
            )
        self.assertEqual(mocked.call_count, 2)
        self.assertEqual(view["classified_distinct_niches"], 2)
        classified = [p for p in view["products"] if p["lifecycle_stage"] == "prototype"]
        self.assertEqual(len(classified), 2)
        unclassified = [p for p in view["products"] if isinstance(p["lifecycle_stage"], dict)]
        self.assertEqual(len(unclassified), 4)
        self.assertIn("not classified in this call", unclassified[0]["lifecycle_stage"]["reason"])

    def test_reuses_real_classifier_not_a_second_implementation(self):
        records = [dict(_REAL_RECORD, production_id="PROD-1", topic="real niche", timestamp="2026-07-18T00:00:00")]
        view = pos.product_lifecycle_view(
            limit=10, classify_limit=1,
            generation_log_path=_write_genlog(self.tmp, records),
            changelog_path=os.path.join(self.tmp, "changelog.jsonl"),
            decisions_path=os.path.join(self.tmp, "d.jsonl"),
            timeline_path=os.path.join(self.tmp, "t.jsonl"),
            outcomes_path=os.path.join(self.tmp, "o.jsonl"),
        )
        self.assertEqual(view["classified_distinct_niches"], 1)
        # real classifier: no evidence -> current_stage None (honest)
        self.assertEqual(view["products"][0]["lifecycle_stage"], None)

    def test_never_writes_any_ledger(self):
        records = [dict(_REAL_RECORD, production_id="PROD-1", topic="real niche", timestamp="2026-07-18T00:00:00")]
        genlog = _write_genlog(self.tmp, records)
        before = sorted(os.listdir(self.tmp))
        pos.product_lifecycle_view(
            limit=10, classify_limit=0,
            generation_log_path=genlog,
            changelog_path=os.path.join(self.tmp, "changelog.jsonl"),
        )
        self.assertEqual(sorted(os.listdir(self.tmp)), before)


if __name__ == "__main__":
    unittest.main()