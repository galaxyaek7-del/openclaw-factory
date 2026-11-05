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

    def test_reads_real_factory_state_per_product(self):
        records = [dict(_REAL_RECORD, production_id="PROD-1", topic="real niche", timestamp="2026-07-18T00:00:00")]
        state_path = os.path.join(self.tmp, "state.json")
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump({
                "pending_retries": [
                    {"task": "regenerate", "attempt": 2,
                     "context": {"production_id": "PROD-1"}},
                ],
                "last_successful_checkpoint": "2026-07-18T00:00:00",
            }, f)
        view = pos.product_lifecycle_view(
            limit=10, classify_limit=0,
            generation_log_path=_write_genlog(self.tmp, records),
            changelog_path=os.path.join(self.tmp, "changelog.jsonl"),
            state_path=state_path,
        )
        fs = view["products"][0]["factory_state"]
        self.assertTrue(fs["had_pending_retry"])
        self.assertEqual(len(fs["pending_retries"]), 1)
        self.assertEqual(fs["factory_last_successful_checkpoint"], "2026-07-18T00:00:00")

    def test_factory_state_never_invents_retry_for_other_products(self):
        records = [dict(_REAL_RECORD, production_id="PROD-1", topic="real niche", timestamp="2026-07-18T00:00:00")]
        state_path = os.path.join(self.tmp, "state.json")
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump({
                "pending_retries": [
                    {"task": "regenerate", "attempt": 1,
                     "context": {"production_id": "PROD-other"}},
                ],
            }, f)
        view = pos.product_lifecycle_view(
            limit=10, classify_limit=0,
            generation_log_path=_write_genlog(self.tmp, records),
            changelog_path=os.path.join(self.tmp, "changelog.jsonl"),
            state_path=state_path,
        )
        fs = view["products"][0]["factory_state"]
        self.assertFalse(fs["had_pending_retry"])
        self.assertEqual(fs["pending_retries"], [])

    def test_factory_state_missing_file_reads_as_safe_empty(self):
        records = [dict(_REAL_RECORD, production_id="PROD-1", topic="real niche", timestamp="2026-07-18T00:00:00")]
        view = pos.product_lifecycle_view(
            limit=10, classify_limit=0,
            generation_log_path=_write_genlog(self.tmp, records),
            changelog_path=os.path.join(self.tmp, "changelog.jsonl"),
            state_path=os.path.join(self.tmp, "does-not-exist.json"),
        )
        fs = view["products"][0]["factory_state"]
        self.assertFalse(fs["had_pending_retry"])
        self.assertIn("factory_state", view["note"])


def _write_ledger(tmp_dir, events):
    from datetime import datetime, timezone
    path = os.path.join(tmp_dir, "sales_ledger.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for e in events:
            e = dict(e)
            e.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    return path


_NOW = __import__("datetime").datetime(2026, 9, 19, tzinfo=__import__("datetime").timezone.utc)


def _publish(pid, title, ts, ok=True, dry=False):
    return {"event_type": "publish_attempt", "platform": "gumroad", "ok": ok,
            "dry_run": dry, "product_id": "p1", "url": "https://x",
            "error": None, "product_title": title, "product_source_id": pid,
            "timestamp": ts}


def _sale(name, price):
    return {"event_type": "sale", "platform": "gumroad",
            "raw": {"id": "s1", "product_name": name, "price": price}}


class TestLearnFeedback(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def _genlog(self, records):
        return _write_genlog(self.tmp, records)

    def test_empty_inputs_yield_zero_kpis_and_unknowns(self):
        fb = pos.learn_feedback(
            limit=10, generation_log_path=self._genlog([]),
            ledger_path=os.path.join(self.tmp, "no-ledger.jsonl"), now=_NOW)
        self.assertEqual(fb["products"], [])
        self.assertEqual(fb["kpis"]["verified_revenue_usd"], 0)
        self.assertEqual(fb["kpis"]["verified_transactions"], 0)
        self.assertIsNone(fb["kpis"]["distribution_efficiency"]["ok_rate"])
        self.assertEqual(fb["kpis"]["pain_economic_value"]["status"], "UNKNOWN")

    def test_old_live_publish_without_sales_diagnoses_never_fails(self):
        rec = dict(_REAL_RECORD, production_id="PROD-1", topic="niche alpha",
                   timestamp="2026-07-01T00:00:00")
        fb = pos.learn_feedback(
            limit=10, generation_log_path=self._genlog([rec]),
            ledger_path=_write_ledger(self.tmp, [
                _publish("PROD-1", "niche alpha", "2026-08-01T00:00:00")]),
            now=_NOW)
        p = fb["products"][0]
        self.assertEqual(p["directive"]["signal"], "DIAGNOSE_BEFORE_SCALE")
        self.assertTrue(p["do_not_clone_without_evidence"])
        self.assertEqual(p["commercial"]["days_since_live_publish"], 49)
        # traffic/clicks/checkout are never numbers
        for stage in ("traffic", "clicks", "checkout"):
            self.assertEqual(p["commercial"][stage]["status"], "UNKNOWN")
            self.assertIsNone(p["commercial"][stage]["value"])

    def test_attributed_sale_marks_scale_candidate(self):
        rec = dict(_REAL_RECORD, production_id="PROD-1", topic="niche alpha",
                   timestamp="2026-09-01T00:00:00")
        fb = pos.learn_feedback(
            limit=10, generation_log_path=self._genlog([rec]),
            ledger_path=_write_ledger(self.tmp, [
                _publish("PROD-1", "niche alpha", "2026-09-05T00:00:00"),
                _sale("niche alpha", 29)]),
            now=_NOW)
        p = fb["products"][0]
        self.assertEqual(p["directive"]["signal"], "SCALE_CANDIDATE")
        self.assertEqual(p["commercial"]["attributed_transactions"], 1)
        self.assertEqual(p["commercial"]["attributed_revenue_usd"], 29)
        self.assertFalse(p["do_not_clone_without_evidence"])
        self.assertEqual(fb["kpis"]["verified_revenue_usd"], 29)
        self.assertEqual(fb["kpis"]["verified_transactions"], 1)
        self.assertEqual(fb["kpis"]["willingness_to_pay_evidence"]["real_amounts_usd"], [29])

    def test_unattributed_sale_counts_factory_only(self):
        rec = dict(_REAL_RECORD, production_id="PROD-1", topic="niche alpha",
                   timestamp="2026-09-01T00:00:00")
        fb = pos.learn_feedback(
            limit=10, generation_log_path=self._genlog([rec]),
            ledger_path=_write_ledger(self.tmp, [
                _publish("PROD-1", "niche alpha", "2026-09-05T00:00:00"),
                _sale("something else entirely", 10)]),
            now=_NOW)
        p = fb["products"][0]
        self.assertEqual(p["commercial"]["attributed_transactions"], 0)
        self.assertIsNotNone(p["commercial"]["attribution_note"])
        self.assertEqual(p["directive"]["signal"], "IN_MEASUREMENT_WINDOW")
        # factory KPIs still count the real sale -- never dropped
        self.assertEqual(fb["kpis"]["verified_transactions"], 1)
        self.assertEqual(fb["kpis"]["verified_revenue_usd"], 10)

    def test_learn_never_writes(self):
        rec = dict(_REAL_RECORD, production_id="PROD-1", topic="niche alpha",
                   timestamp="2026-09-01T00:00:00")
        genlog = self._genlog([rec])
        ledger = _write_ledger(self.tmp, [_publish("PROD-1", "niche alpha",
                                                  "2026-09-05T00:00:00")])
        before = sorted(os.listdir(self.tmp))
        pos.learn_feedback(limit=10, generation_log_path=genlog,
                           ledger_path=ledger, now=_NOW)
        pos.product_lifecycle_view(
            limit=10, classify_limit=0, generation_log_path=genlog,
            changelog_path=os.path.join(self.tmp, "changelog.jsonl"),
            ledger_path=ledger)
        self.assertEqual(sorted(os.listdir(self.tmp)), before)

    def test_view_carries_learn_block_per_product(self):
        rec = dict(_REAL_RECORD, production_id="PROD-1", topic="niche alpha",
                   timestamp="2026-09-01T00:00:00")
        view = pos.product_lifecycle_view(
            limit=10, classify_limit=0,
            generation_log_path=self._genlog([rec]),
            changelog_path=os.path.join(self.tmp, "changelog.jsonl"),
            ledger_path=_write_ledger(self.tmp, [
                _publish("PROD-1", "niche alpha", "2026-09-05T00:00:00")]))
        learn = view["products"][0]["learn"]
        self.assertIn("commercial", learn)
        self.assertIn("directive", learn)
        self.assertIn("do_not_clone_without_evidence", learn)
        self.assertIn("learn_kpis", view)
        self.assertIn("verified_revenue_usd", view["learn_kpis"])


class TestProductLifecycleSnapshot(unittest.TestCase):
    """record_product_lifecycle_snapshot() (restored 2026-10-28): the ONE real
    write path for data/product_lifecycle_snapshots.jsonl. Isolated temp paths
    only -- the real ledger is never touched by a test."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def _genlog(self, records):
        return _write_genlog(self.tmp, records)

    def _record(self, path=None, **overrides):
        kwargs = dict(
            limit=10, classify_limit=0,
            changelog_path=os.path.join(self.tmp, "changelog.jsonl"),
            decisions_path=os.path.join(self.tmp, "decisions.jsonl"),
            timeline_path=os.path.join(self.tmp, "timeline.jsonl"),
            outcomes_path=os.path.join(self.tmp, "outcomes.jsonl"),
            state_path=os.path.join(self.tmp, "factory_state.json"),
            ledger_path=os.path.join(self.tmp, "sales_ledger.jsonl"),
        )
        kwargs.update(overrides)
        if "generation_log_path" not in kwargs:
            kwargs["generation_log_path"] = self._genlog([dict(_REAL_RECORD)])
        return pos.record_product_lifecycle_snapshot(
            path=path or os.path.join(self.tmp, "snapshots.jsonl"), **kwargs)

    def test_appends_one_real_row_per_call(self):
        snap = self._record()
        self.assertEqual(snap["shown_products"], 1)
        path = os.path.join(self.tmp, "snapshots.jsonl")
        with open(path, encoding="utf-8") as f:
            rows = [json.loads(line) for line in f if line.strip()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["shown_products"], 1)
        self.assertIn("generated_at", rows[0])

        self._record()
        with open(path, encoding="utf-8") as f:
            self.assertEqual(len([l for l in f if l.strip()]), 2)

    def test_creates_the_ledger_directory_when_missing(self):
        nested = os.path.join(self.tmp, "nested", "dir", "snapshots.jsonl")
        self._record(path=nested)
        self.assertTrue(os.path.exists(nested))

    def test_an_empty_log_records_an_honest_zero_not_an_error(self):
        snap = self._record(generation_log_path=self._genlog([]))
        self.assertEqual(snap["shown_products"], 0)
        self.assertEqual(snap["total_real_production_ids_in_log"], 0)


if __name__ == "__main__":
    unittest.main()