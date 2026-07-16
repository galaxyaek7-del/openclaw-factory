"""Tests for production_evidence/ (ADR-055).

Runs with stdlib unittest. Every function reads only from temp-file-
isolated stores passed explicitly — never the real data/*.jsonl files.

    python -m unittest tests.test_production_evidence -v
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from decision_engine import store as decision_store
from decision_engine.types import Decision, Outcome, make_decision_id
from orchestrator import timeline as orch_timeline
from orchestrator.orchestrator import make_idempotency_key
from orchestrator.types import ExecutionResult

from production_evidence import catalog, record


def _temp_path(suffix=".jsonl"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


def _decision(niche, status, decided_at=None, tier="tier4"):
    decided_at = decided_at or datetime.now(timezone.utc).isoformat()
    return Decision(
        decision_id=make_decision_id(niche, tier, decided_at), niche=niche, tier=tier,
        decided_at=decided_at, status=status, ai_ceo_decision="BUILD" if status == "ACCEPTED" else "WAIT",
        opportunity_score=80, opportunity_score_accepted=(status == "ACCEPTED"),
        reasoning=["real evidence"], evaluation_snapshot={"dimension_scores": {}, "ai_ceo": {"decision": "BUILD"}},
    )


def _exec_result(engine, niche, tier, status, started_at, finished_at, output=None):
    key = make_idempotency_key(engine, niche, tier)
    return ExecutionResult(
        engine=engine, status=status, started_at=started_at, finished_at=finished_at,
        attempts=1, idempotency_key=key, output=output or {},
    )


class TestBuildEvidenceRecord(unittest.TestCase):
    def setUp(self):
        self.timeline_path = _temp_path()
        self.decisions_path = _temp_path()
        self.outcomes_path = _temp_path()

    def tearDown(self):
        for p in (self.timeline_path, self.decisions_path, self.outcomes_path):
            if os.path.exists(p):
                os.remove(p)

    def test_never_seen_niche_is_honestly_not_yet_evaluated(self):
        r = record.build_evidence_record(
            "never seen niche", timeline_path=self.timeline_path,
            decisions_path=self.decisions_path, outcomes_path=self.outcomes_path,
        )
        self.assertEqual(r["final_outcome"], "NOT_YET_EVALUATED")
        self.assertEqual(r["decision"]["status"], "Unknown")
        self.assertIsNone(r["discovery_timestamp"])

    def test_rejected_decision_is_classified_rejected(self):
        decision_store.append_decision(_decision("rejected niche", "REJECTED"), path=self.decisions_path)
        r = record.build_evidence_record(
            "rejected niche", timeline_path=self.timeline_path,
            decisions_path=self.decisions_path, outcomes_path=self.outcomes_path,
        )
        self.assertEqual(r["final_outcome"], "REJECTED")

    def test_accepted_with_no_execution_is_pending_execution(self):
        decision_store.append_decision(_decision("accepted niche", "ACCEPTED"), path=self.decisions_path)
        r = record.build_evidence_record(
            "accepted niche", timeline_path=self.timeline_path,
            decisions_path=self.decisions_path, outcomes_path=self.outcomes_path,
        )
        self.assertEqual(r["final_outcome"], "ACCEPTED_PENDING_EXECUTION")

    def test_produced_and_published_but_not_sold(self):
        niche = "produced niche"
        decision_store.append_decision(_decision(niche, "ACCEPTED"), path=self.decisions_path)
        orch_timeline.append_execution(_exec_result("production", niche, "tier4", "SUCCESS", "t1", "t2"), path=self.timeline_path)
        orch_timeline.append_execution(
            _exec_result("publishing", niche, "tier4", "SUCCESS", "t3", "t4", output={"outcomes": [{"arm": "gumroad", "attempted": True, "ok": True}]}),
            path=self.timeline_path,
        )
        r = record.build_evidence_record(
            niche, timeline_path=self.timeline_path, decisions_path=self.decisions_path, outcomes_path=self.outcomes_path,
        )
        self.assertEqual(r["final_outcome"], "PRODUCED_AND_PUBLISHED_NOT_YET_SOLD")
        self.assertEqual(r["platform"]["succeeded"], ["gumroad"])

    def test_real_revenue_event_classifies_as_sold(self):
        niche = "sold niche"
        decided_at = datetime.now(timezone.utc).isoformat()
        decision_store.append_decision(_decision(niche, "ACCEPTED", decided_at=decided_at), path=self.decisions_path)
        decision_id = make_decision_id(niche, "tier4", decided_at)
        decision_store.append_outcome(
            Outcome(outcome_id="o1", decision_id=decision_id, niche=niche, recorded_at="t", matched=True, match_method="x", raw_sale_event={"raw": {"price": 999}}),
            path=self.outcomes_path,
        )
        r = record.build_evidence_record(
            niche, timeline_path=self.timeline_path, decisions_path=self.decisions_path, outcomes_path=self.outcomes_path,
        )
        self.assertEqual(r["final_outcome"], "SOLD")
        self.assertEqual(len(r["revenue_events"]), 1)

    def test_customer_feedback_unknown_without_a_real_review_field(self):
        niche = "sold niche no review"
        decided_at = datetime.now(timezone.utc).isoformat()
        decision_store.append_decision(_decision(niche, "ACCEPTED", decided_at=decided_at), path=self.decisions_path)
        decision_id = make_decision_id(niche, "tier4", decided_at)
        decision_store.append_outcome(
            Outcome(outcome_id="o1", decision_id=decision_id, niche=niche, recorded_at="t", matched=True, match_method="x", raw_sale_event={"raw": {"price": 999}}),
            path=self.outcomes_path,
        )
        r = record.build_evidence_record(
            niche, timeline_path=self.timeline_path, decisions_path=self.decisions_path, outcomes_path=self.outcomes_path,
        )
        self.assertEqual(r["customer_feedback"]["answer"], "Unknown")

    def test_customer_feedback_extracted_when_a_real_field_is_present(self):
        niche = "sold niche with review"
        decided_at = datetime.now(timezone.utc).isoformat()
        decision_store.append_decision(_decision(niche, "ACCEPTED", decided_at=decided_at), path=self.decisions_path)
        decision_id = make_decision_id(niche, "tier4", decided_at)
        decision_store.append_outcome(
            Outcome(outcome_id="o1", decision_id=decision_id, niche=niche, recorded_at="t", matched=True, match_method="x",
                    raw_sale_event={"raw": {"price": 999, "rating": 5}}),
            path=self.outcomes_path,
        )
        r = record.build_evidence_record(
            niche, timeline_path=self.timeline_path, decisions_path=self.decisions_path, outcomes_path=self.outcomes_path,
        )
        self.assertNotEqual(r["customer_feedback"]["answer"], "Unknown")

    def test_evidence_snapshot_is_the_real_stored_snapshot_not_recomputed(self):
        niche = "snapshot niche"
        d = _decision(niche, "ACCEPTED")
        decision_store.append_decision(d, path=self.decisions_path)
        r = record.build_evidence_record(
            niche, timeline_path=self.timeline_path, decisions_path=self.decisions_path, outcomes_path=self.outcomes_path,
        )
        self.assertEqual(r["evidence_snapshot"], d.evaluation_snapshot)


class TestCatalog(unittest.TestCase):
    def setUp(self):
        self.timeline_path = _temp_path()
        self.decisions_path = _temp_path()
        self.outcomes_path = _temp_path()

    def tearDown(self):
        for p in (self.timeline_path, self.decisions_path, self.outcomes_path):
            if os.path.exists(p):
                os.remove(p)

    def test_empty_store_gives_empty_catalog(self):
        result = catalog.list_all_evidence_records(
            timeline_path=self.timeline_path, decisions_path=self.decisions_path, outcomes_path=self.outcomes_path,
        )
        self.assertEqual(result, [])

    def test_catalog_has_one_record_per_distinct_niche(self):
        decision_store.append_decision(_decision("niche a", "ACCEPTED"), path=self.decisions_path)
        decision_store.append_decision(_decision("niche b", "REJECTED"), path=self.decisions_path)
        result = catalog.list_all_evidence_records(
            timeline_path=self.timeline_path, decisions_path=self.decisions_path, outcomes_path=self.outcomes_path,
        )
        self.assertEqual(len(result), 2)
        niches = {r["niche"] for r in result}
        self.assertEqual(niches, {"niche a", "niche b"})


class TestLifecycleEnrichmentIsBackwardCompatible(unittest.TestCase):
    """ADR-055's one change to validation_layer/lifecycle.py (adding a
    real 'output' key to each stage event) must never remove or alter any
    of the keys that existed before it — proving the additive-only claim."""

    def test_existing_keys_are_all_still_present(self):
        from validation_layer import lifecycle as lifecycle_module
        timeline_path = _temp_path()
        try:
            orch_timeline.append_execution(
                _exec_result("decision", "x", "tier4", "SUCCESS", "t1", "t2"), path=timeline_path,
            )
            lc = lifecycle_module.build_lifecycle("x", timeline_path=timeline_path)
            event = lc["decision"][0]
            for key in ("status", "started_at", "finished_at", "duration_seconds", "error"):
                self.assertIn(key, event)
            self.assertIn("output", event)
        finally:
            if os.path.exists(timeline_path):
                os.remove(timeline_path)


if __name__ == "__main__":
    unittest.main()
