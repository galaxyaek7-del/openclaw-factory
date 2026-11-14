"""GF-ROS Milestone 7: lead funnel state machine.

Nothing here contacts a real person. Sends are gated twice (env + founder
approval) and still report NOT_CONNECTED because no transport exists.
"""
import json
import os
import tempfile
import unittest
from unittest import mock

import evidence_engine
import lead_discovery as ld


class FunnelCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "prospect_pipeline.jsonl")
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"schema_version": 1, "prospects": []}) + "\n")
        # transition_lead() records a CUSTOMER evidence row. Point the evidence
        # engine at this test's temp directory so the test never defaults to the
        # live data/evidence_ledger.jsonl (write_guard used to redirect it).
        self._evidence_ledger = evidence_engine.DEFAULT_LEDGER_PATH
        evidence_engine.DEFAULT_LEDGER_PATH = os.path.join(self.tmp.name, "evidence_ledger.jsonl")
        self.addCleanup(setattr, evidence_engine, "DEFAULT_LEDGER_PATH", self._evidence_ledger)

    def _approvals(self, status):
        p = os.path.join(self.tmp.name, "approvals.jsonl")
        with open(p, "w", encoding="utf-8") as f:
            f.write(json.dumps({"item_id": "APR-1", "status": status}) + "\n")
        return p


class TestTransitions(FunnelCase):
    def test_unknown_lead_has_no_stage(self):
        self.assertIsNone(ld.lead_stage("lead-x", path=self.path))

    def test_no_lead_without_a_real_source(self):
        with self.assertRaises(ld.MissingLeadSource):
            ld.transition_lead("lead-x", "QUALIFIED", path=self.path)

    def test_unknown_stage_rejected(self):
        with self.assertRaises(ValueError):
            ld.transition_lead("lead-x", "MAYBE", source_ref="hn:1", path=self.path)

    def test_illegal_transition_rejected(self):
        with self.assertRaises(ld.IllegalFunnelTransition):
            ld.transition_lead("lead-x", "WON", source_ref="hn:1", path=self.path)

    def test_full_happy_path(self):
        ld.transition_lead("lead-x", "QUALIFIED", source_ref="hn:1", path=self.path)
        for stage in ("CONTACTED", "REPLIED", "PROPOSAL", "WON"):
            ld.transition_lead("lead-x", stage, path=self.path)
        self.assertEqual(ld.lead_stage("lead-x", path=self.path), "WON")

    def test_terminal_stage_is_terminal(self):
        ld.transition_lead("lead-x", "LOST", source_ref="hn:1", path=self.path)
        with self.assertRaises(ld.IllegalFunnelTransition):
            ld.transition_lead("lead-x", "QUALIFIED", path=self.path)

    def test_lost_reachable_from_every_open_stage(self):
        for i, target in enumerate(("NEW", "QUALIFIED", "CONTACTED", "REPLIED", "PROPOSAL")):
            lead = f"lead-{i}"
            if target != "NEW":
                ld.transition_lead(lead, "QUALIFIED", source_ref="hn:1", path=self.path)
                for stage in ("CONTACTED", "REPLIED", "PROPOSAL"):
                    if ld.lead_stage(lead, path=self.path) == target:
                        break
                    ld.transition_lead(lead, stage, path=self.path)
            event = ld.transition_lead(lead, "LOST", source_ref="hn:1", path=self.path)
            self.assertEqual(event["to_stage"], "LOST")

    def test_every_transition_appends_evidence(self):
        event = ld.transition_lead("lead-x", "QUALIFIED", source_ref="hn:1",
                                   reason="public post, fresh", path=self.path)
        self.assertTrue(event["evidence_id"])
        self.assertEqual(event["from_stage"], "NEW")

    def test_schema_row_is_ignored(self):
        ld.transition_lead("lead-x", "QUALIFIED", source_ref="hn:1", path=self.path)
        summary = ld.funnel_summary(path=self.path)
        self.assertEqual(summary["total_leads"], 1)
        self.assertEqual(summary["counts"]["QUALIFIED"], 1)
        self.assertEqual(sum(summary["counts"].values()), 1)


class TestOutreach(FunnelCase):
    def test_draft_is_recorded_unsent(self):
        draft = ld.create_draft("lead-x", "hello", "body text", path=self.path)
        self.assertFalse(draft["sent"])
        self.assertTrue(draft["draft_id"])

    def test_send_blocked_by_env_gate(self):
        env = {k: v for k, v in os.environ.items() if k != "GF_ALLOW_OUTBOUND_MESSAGES"}
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(Exception) as ctx:
                ld.send_draft("lead-x", "d1", approvals_path=self._approvals("APPROVED"))
        self.assertIn("outbound", str(ctx.exception).lower())

    def test_send_blocked_without_founder_approval(self):
        with mock.patch.dict(os.environ, {"GF_ALLOW_OUTBOUND_MESSAGES": "true"}):
            with self.assertRaises(ld.FounderApprovalRequired):
                ld.send_draft("lead-x", "d1", approvals_path=self._approvals("PENDING"))

    def test_send_never_claims_delivery(self):
        with mock.patch.dict(os.environ, {"GF_ALLOW_OUTBOUND_MESSAGES": "true"}):
            result = ld.send_draft("lead-x", "d1", founder_approval_id="APR-1",
                                   approvals_path=self._approvals("APPROVED"))
        self.assertFalse(result["sent"])
        self.assertEqual(result["transport"], "NOT_CONNECTED")


if __name__ == "__main__":
    unittest.main()
