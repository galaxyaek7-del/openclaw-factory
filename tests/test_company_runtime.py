"""Tests for company_runtime.py (Autonomous Company Runtime, ADR-157,
2026-07-31): citation-only functions -- no daemon, no event bus, no
queue, no new auto-restart mechanism. company_state() is read-only,
SCALING is defined but never real.

    python -m unittest tests.test_company_runtime -v
"""

import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import company_runtime as cr


class TestExecutiveReplay(unittest.TestCase):
    def test_returns_real_entries_and_source_citation(self):
        result = cr.executive_replay(limit=5)
        self.assertIn("entries", result)
        self.assertIn("gfos.py", result["source"])
        self.assertLessEqual(len(result["entries"]), 5)

    def test_from_date_filters_entries(self):
        result = cr.executive_replay(from_date="2099-01-01", limit=50)
        self.assertEqual(result["entries"], [])

    def test_decision_id_threads_in_real_explain_detail(self):
        result = cr.executive_replay(decision_id="not-a-real-id", limit=1)
        self.assertIn("explained_decision", result)

    def test_no_decision_id_omits_explained_decision(self):
        result = cr.executive_replay(limit=1)
        self.assertNotIn("explained_decision", result)


class TestAutonomousDailyCycleStatus(unittest.TestCase):
    def test_covers_all_9_named_stages(self):
        result = cr.autonomous_daily_cycle_status()
        expected = {
            "morning_review", "opportunity_scan", "production", "qa", "publishing",
            "affiliate_updates", "analytics", "knowledge_update", "executive_report",
        }
        self.assertEqual(set(result["stages"].keys()), expected)

    def test_morning_review_and_affiliate_updates_are_honestly_not_architected(self):
        result = cr.autonomous_daily_cycle_status()
        self.assertEqual(result["stages"]["morning_review"]["status"], cr.NOT_ARCHITECTED)
        self.assertEqual(result["stages"]["affiliate_updates"]["status"], cr.NOT_ARCHITECTED)

    def test_never_claims_a_cron_or_daemon(self):
        result = cr.autonomous_daily_cycle_status()
        self.assertIn("no cron/systemd", result["note"])


class TestCompanyState(unittest.TestCase):
    def test_returns_one_of_the_named_states(self):
        result = cr.company_state()
        self.assertIn(result["state"], cr.STATES)

    def test_never_returns_scaling(self):
        # SCALING is a defined state per the directive but never real --
        # no real scale-out signal exists anywhere in this factory.
        result = cr.company_state()
        self.assertNotEqual(result["state"], "SCALING")

    def test_never_returns_boot(self):
        # BOOT is deliberately not computed here -- Python runs as a
        # fresh, stateless subprocess per call, so it has no real
        # process uptime to measure. The Node server layer overrides
        # this separately.
        result = cr.company_state()
        self.assertNotEqual(result["state"], "BOOT")

    def test_carries_a_real_reason_for_every_possible_state(self):
        result = cr.company_state()
        self.assertTrue(result.get("reason"))


if __name__ == "__main__":
    unittest.main()
