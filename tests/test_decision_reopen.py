"""Tests for decision_reopen.py (Decision Re-open Trigger, Live
Competitive Intelligence Layer, 2026-07-23).

Runs with stdlib unittest. Zero live network calls -- every dependency
(executive_board, market_alerts, factory_orchestrator, decision_engine)
is exercised through temp-file-isolated real data, or mocked at the
exact seam ADR-094's own test suite already established.

    python -m unittest tests.test_decision_reopen -v
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import decision_reopen as dr
import executive_board as eb
import market_alerts
import market_evidence as me
from decision_engine import store
from decision_engine.types import Decision, make_decision_id


def _temp_path(suffix=".jsonl"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


def _iso(days_ago=0):
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


class TestMaterialityHelpers(unittest.TestCase):
    def test_no_new_alerts_is_never_material(self):
        material, reason = dr._is_material_change([])
        self.assertFalse(material)

    def test_a_single_critical_alert_is_material(self):
        material, reason = dr._is_material_change([{"severity": "Critical"}])
        self.assertTrue(material)
        self.assertIn("حرج", reason)

    def test_a_single_high_alert_alone_is_not_material(self):
        material, reason = dr._is_material_change([{"severity": "High"}])
        self.assertFalse(material)

    def test_two_high_alerts_are_material(self):
        material, reason = dr._is_material_change([{"severity": "High"}, {"severity": "High"}])
        self.assertTrue(material)
        self.assertIn("عالية", reason)

    def test_any_number_of_medium_or_low_alerts_is_never_material(self):
        alerts = [{"severity": "Medium"}] * 10 + [{"severity": "Low"}] * 10
        material, reason = dr._is_material_change(alerts)
        self.assertFalse(material)

    def test_new_alerts_since_excludes_alerts_before_the_cutoff(self):
        alerts = [
            {"severity": "Critical", "occurred_at": _iso(days_ago=10)},
            {"severity": "Critical", "occurred_at": _iso(days_ago=1)},
        ]
        new = dr._new_alerts_since(alerts, _iso(days_ago=5))
        self.assertEqual(len(new), 1)

    def test_new_alerts_since_excludes_alerts_with_no_parseable_timestamp(self):
        """Never speculate: an alert with no real timestamp is honestly
        excluded, never assumed to be new."""
        alerts = [{"severity": "Critical", "occurred_at": None}]
        new = dr._new_alerts_since(alerts, _iso(days_ago=5))
        self.assertEqual(new, [])

    def test_new_alerts_since_with_no_previous_timestamp_treats_all_as_current(self):
        alerts = [{"severity": "Critical", "occurred_at": _iso(days_ago=100)}]
        new = dr._new_alerts_since(alerts, None)
        self.assertEqual(len(new), 1)


class TestCheckForReopenTrigger(unittest.TestCase):
    def setUp(self):
        self.board_path = _temp_path()
        self.alerts_path = _temp_path()

    def tearDown(self):
        for p in (self.board_path, self.alerts_path):
            if os.path.exists(p):
                os.remove(p)

    def test_no_prior_meeting_never_triggers(self):
        result = dr.check_for_reopen_trigger("never convened niche", board_path=self.board_path, alerts_path=self.alerts_path)
        self.assertFalse(result["should_reopen"])
        self.assertIn("لا اجتماع", result["reason"])

    def _write_meeting(self, niche, convened_at, confidence=0.8, board_decision="APPROVED"):
        meeting = {
            "niche": niche, "convened_at": convened_at, "decision_type": "production",
            "tally": {"board_decision": board_decision},
            "decision_summary": {"decision": board_decision, "confidence": confidence},
        }
        with open(self.board_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(meeting) + "\n")

    def test_prior_meeting_with_no_new_alerts_never_triggers(self):
        self._write_meeting("n", _iso(days_ago=5))
        result = dr.check_for_reopen_trigger("n", board_path=self.board_path, alerts_path=self.alerts_path)
        self.assertFalse(result["should_reopen"])

    def test_prior_meeting_with_a_real_new_critical_alert_triggers(self):
        self._write_meeting("n", _iso(days_ago=5))
        db_path = _temp_path(suffix=".json")
        try:
            import competitor_discovery as cd
            db = {cd._normalize_key("n"): {
                "total_found": 1,
                "changes": {
                    "has_history": True, "compared_at": _iso(days_ago=1),
                    "new_competitors": [{"name": "BigCo", "category": "Enterprise Leader"}],
                    "disappeared_competitors": [], "growth_signals": [],
                },
            }}
            cd.save_database(db, db_file=db_path)
            market_alerts.scan_market_alerts("n", db_file=db_path, alerts_path=self.alerts_path)
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

        result = dr.check_for_reopen_trigger("n", board_path=self.board_path, alerts_path=self.alerts_path)
        self.assertTrue(result["should_reopen"])
        self.assertEqual(len(result["trigger_alerts"]), 1)
        self.assertEqual(result["previous_board_decision"], "APPROVED")
        self.assertEqual(result["previous_confidence"], 0.8)

    def test_a_stale_alert_from_before_the_last_meeting_never_triggers(self):
        self._write_meeting("n", _iso(days_ago=1))
        db_path = _temp_path(suffix=".json")
        try:
            import competitor_discovery as cd
            db = {cd._normalize_key("n"): {
                "total_found": 1,
                "changes": {
                    "has_history": True, "compared_at": _iso(days_ago=10),  # BEFORE the meeting
                    "new_competitors": [{"name": "BigCo", "category": "Enterprise Leader"}],
                    "disappeared_competitors": [], "growth_signals": [],
                },
            }}
            cd.save_database(db, db_file=db_path)
            market_alerts.scan_market_alerts("n", db_file=db_path, alerts_path=self.alerts_path)
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

        result = dr.check_for_reopen_trigger("n", board_path=self.board_path, alerts_path=self.alerts_path)
        self.assertFalse(result["should_reopen"])


class TestExecuteReopen(unittest.TestCase):
    def setUp(self):
        self.board_path = _temp_path()
        self.alerts_path = _temp_path()
        self.reopen_log_path = _temp_path()
        self.decisions_path = _temp_path()

    def tearDown(self):
        for p in (self.board_path, self.alerts_path, self.reopen_log_path, self.decisions_path):
            if os.path.exists(p):
                os.remove(p)

    def _write_meeting(self, niche, convened_at, confidence=0.8, board_decision="APPROVED"):
        meeting = {
            "niche": niche, "convened_at": convened_at, "decision_type": "production",
            "tally": {"board_decision": board_decision},
            "decision_summary": {"decision": board_decision, "confidence": confidence},
        }
        with open(self.board_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(meeting) + "\n")

    def test_refuses_when_not_material_never_reconvenes(self):
        self._write_meeting("n", _iso(days_ago=5))
        with patch("executive_board.convene_board") as mock_convene:
            result = dr.execute_reopen("n", decisions_path=self.decisions_path, board_path=self.board_path, alerts_path=self.alerts_path, reopen_log_path=self.reopen_log_path)
        self.assertFalse(result["reopened"])
        mock_convene.assert_not_called()
        self.assertFalse(os.path.exists(self.reopen_log_path))

    def test_refuses_honestly_when_no_real_decision_exists_to_rebuild_a_spec_from(self):
        self._write_meeting("n", _iso(days_ago=5))
        db_path = _temp_path(suffix=".json")
        try:
            import competitor_discovery as cd
            db = {cd._normalize_key("n"): {
                "total_found": 1,
                "changes": {
                    "has_history": True, "compared_at": _iso(days_ago=1),
                    "new_competitors": [{"name": "BigCo", "category": "Enterprise Leader"}],
                    "disappeared_competitors": [], "growth_signals": [],
                },
            }}
            cd.save_database(db, db_file=db_path)
            market_alerts.scan_market_alerts("n", db_file=db_path, alerts_path=self.alerts_path)
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

        # no decision recorded in self.decisions_path -- decisions.jsonl is real but empty
        result = dr.execute_reopen("n", decisions_path=self.decisions_path, board_path=self.board_path, alerts_path=self.alerts_path, reopen_log_path=self.reopen_log_path)
        self.assertFalse(result["reopened"])
        self.assertTrue(result["should_reopen"])
        self.assertFalse(os.path.exists(self.reopen_log_path))

    def _record_real_decision(self, niche):
        decided_at = "2026-07-16T10:00:00+00:00"
        d = Decision(
            decision_id=make_decision_id(niche, "tier4", decided_at), niche=niche, tier="tier4",
            decided_at=decided_at, status="ACCEPTED", ai_ceo_decision="BUILD",
            opportunity_score=80.0, opportunity_score_accepted=True,
            reasoning=["real evidence"], evaluation_snapshot={"pricing": {"recommended_price": "$97"}},
        )
        store.append_decision(d, path=self.decisions_path)

    def test_a_material_change_reconvenes_the_board_and_records_a_full_reopen_event(self):
        self._record_real_decision("n")
        self._write_meeting("n", _iso(days_ago=5), confidence=0.3, board_decision="NOT_APPROVED")

        me_evidence_path = _temp_path()
        try:
            me.record_evidence(
                "n", "competitor_customer_migration",
                {"competitor": "Acme", "source_url": "https://example.com/case-study"},
                evidence_path=me_evidence_path,
            )
            market_alerts.scan_market_alerts("n", evidence_path=me_evidence_path, alerts_path=self.alerts_path)
        finally:
            if os.path.exists(me_evidence_path):
                os.remove(me_evidence_path)

        fake_new_meeting = {
            "convened_at": _iso(),
            "tally": {"board_decision": "APPROVED"},
            "decision_summary": {"confidence": 0.9},
        }
        with patch("executive_board.convene_board", return_value=fake_new_meeting) as mock_convene:
            result = dr.execute_reopen(
                "n", decisions_path=self.decisions_path, board_path=self.board_path,
                alerts_path=self.alerts_path, reopen_log_path=self.reopen_log_path,
            )

        self.assertTrue(result["reopened"])
        mock_convene.assert_called_once()
        self.assertEqual(result["confidence_delta"], 0.6)
        self.assertTrue(result["decision_changed"])
        self.assertEqual(result["previous_decision"]["board_decision"], "NOT_APPROVED")
        self.assertEqual(result["new_decision"]["board_decision"], "APPROVED")
        self.assertIn("reopened_at", result)
        self.assertGreaterEqual(len(result["trigger_alerts"]), 1)

        history = dr.get_reopen_history("n", reopen_log_path=self.reopen_log_path)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["niche"], "n")

    def test_decision_changed_is_false_when_the_new_verdict_matches_the_old_one(self):
        self._record_real_decision("n")
        self._write_meeting("n", _iso(days_ago=5), confidence=0.8, board_decision="APPROVED")

        db_path = _temp_path(suffix=".json")
        try:
            import competitor_discovery as cd
            db = {cd._normalize_key("n"): {
                "total_found": 1,
                "changes": {
                    "has_history": True, "compared_at": _iso(days_ago=1),
                    "new_competitors": [{"name": "BigCo", "category": "Enterprise Leader"}],
                    "disappeared_competitors": [], "growth_signals": [],
                },
            }}
            cd.save_database(db, db_file=db_path)
            market_alerts.scan_market_alerts("n", db_file=db_path, alerts_path=self.alerts_path)
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

        fake_new_meeting = {
            "convened_at": _iso(),
            "tally": {"board_decision": "APPROVED"},
            "decision_summary": {"confidence": 0.85},
        }
        with patch("executive_board.convene_board", return_value=fake_new_meeting):
            result = dr.execute_reopen(
                "n", decisions_path=self.decisions_path, board_path=self.board_path,
                alerts_path=self.alerts_path, reopen_log_path=self.reopen_log_path,
            )
        self.assertFalse(result["decision_changed"])
        self.assertAlmostEqual(result["confidence_delta"], 0.05)

    def test_the_previous_meeting_is_never_mutated_full_audit_trail(self):
        """Rollback capability, honestly scoped: the prior real board
        meeting stays fully intact and readable after a reopen."""
        self._record_real_decision("n")
        self._write_meeting("n", _iso(days_ago=5), confidence=0.3, board_decision="NOT_APPROVED")
        with open(self.board_path, encoding="utf-8") as f:
            before = f.read()

        db_path = _temp_path(suffix=".json")
        try:
            import competitor_discovery as cd
            db = {cd._normalize_key("n"): {
                "total_found": 1,
                "changes": {
                    "has_history": True, "compared_at": _iso(days_ago=1),
                    "new_competitors": [{"name": "BigCo", "category": "Enterprise Leader"}],
                    "disappeared_competitors": [], "growth_signals": [],
                },
            }}
            cd.save_database(db, db_file=db_path)
            market_alerts.scan_market_alerts("n", db_file=db_path, alerts_path=self.alerts_path)
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

        fake_new_meeting = {"convened_at": _iso(), "tally": {"board_decision": "APPROVED"}, "decision_summary": {"confidence": 0.9}}
        with patch("executive_board.convene_board", return_value=fake_new_meeting):
            dr.execute_reopen(
                "n", decisions_path=self.decisions_path, board_path=self.board_path,
                alerts_path=self.alerts_path, reopen_log_path=self.reopen_log_path,
            )

        with open(self.board_path, encoding="utf-8") as f:
            after = f.read()
        self.assertTrue(after.startswith(before), "the previous real meeting record must be preserved byte-for-byte, never mutated")


class TestGetReopenHistory(unittest.TestCase):
    def setUp(self):
        self.reopen_log_path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.reopen_log_path):
            os.remove(self.reopen_log_path)

    def test_no_log_file_yet_is_honestly_empty(self):
        self.assertEqual(dr.get_reopen_history("n", reopen_log_path=self.reopen_log_path), [])

    def test_scoped_to_the_requested_niche_only(self):
        with open(self.reopen_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"niche": "a", "reopened_at": "x"}) + "\n")
            f.write(json.dumps({"niche": "b", "reopened_at": "y"}) + "\n")
        self.assertEqual(len(dr.get_reopen_history("a", reopen_log_path=self.reopen_log_path)), 1)
        self.assertEqual(len(dr.get_reopen_history("c", reopen_log_path=self.reopen_log_path)), 0)

    def test_corrupt_line_is_skipped_not_fatal(self):
        with open(self.reopen_log_path, "a", encoding="utf-8") as f:
            f.write("{not valid json\n")
            f.write(json.dumps({"niche": "a", "reopened_at": "x"}) + "\n")
        self.assertEqual(len(dr.get_reopen_history("a", reopen_log_path=self.reopen_log_path)), 1)


class TestScanAndMaybeReopen(unittest.TestCase):
    def setUp(self):
        self.board_path = _temp_path()
        self.alerts_path = _temp_path()
        self.reopen_log_path = _temp_path()
        self.decisions_path = _temp_path()
        self.db_path = _temp_path(suffix=".json")
        self.evidence_path = _temp_path()

    def tearDown(self):
        for p in (self.board_path, self.alerts_path, self.reopen_log_path,
                  self.decisions_path, self.db_path, self.evidence_path):
            if os.path.exists(p):
                os.remove(p)

    def test_runs_a_real_scan_first_then_checks_the_trigger(self):
        meeting = {
            "niche": "n", "convened_at": _iso(days_ago=5), "decision_type": "production",
            "tally": {"board_decision": "APPROVED"}, "decision_summary": {"decision": "APPROVED", "confidence": 0.8},
        }
        with open(self.board_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(meeting) + "\n")

        result = dr.scan_and_maybe_reopen(
            "n", decisions_path=self.decisions_path, board_path=self.board_path,
            alerts_path=self.alerts_path, reopen_log_path=self.reopen_log_path,
            evidence_path=self.evidence_path, db_file=self.db_path,
        )
        self.assertFalse(result["reopened"])  # nothing real to find -> no material change


if __name__ == "__main__":
    unittest.main()
