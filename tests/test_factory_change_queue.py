"""Tier-1 tests: change queue tiers; auto-run executes whitelist only."""
import json
import os
import tempfile
import unittest

import factory_change_queue as cq


class TestChangeQueue(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl")
        self.tmp.close()
        self._orig = cq.QUEUE_PATH
        cq.QUEUE_PATH = self.tmp.name

    def tearDown(self):
        cq.QUEUE_PATH = self._orig
        os.unlink(self.tmp.name)

    def test_tier_classification(self):
        self.assertEqual(cq.classify_change("drift_snapshot"), "TIER_1_AUTO")
        self.assertEqual(cq.classify_change("health_check"), "TIER_1_AUTO")
        self.assertEqual(cq.classify_change("refactor", "server.js"), "TIER_2_PREPARE")
        self.assertEqual(cq.classify_change("publish", "gumroad"), "TIER_3_FOUNDER_GATE")
        self.assertEqual(cq.classify_change("spend", "$10 ads"), "TIER_3_FOUNDER_GATE")

    def test_enqueue_and_list(self):
        e = cq.enqueue("drift_snapshot", detail="t")
        self.assertEqual(e["tier"], "TIER_1_AUTO")
        self.assertEqual(len(cq.list_queue()), 1)

    def test_run_tier1_skips_non_whitelist(self):
        cq.enqueue("publish", "gumroad", detail="must not run")
        res = cq.run_tier1(limit=5)
        self.assertEqual(res, [])  # TIER_3 entry untouched
        queued = cq.list_queue()
        self.assertEqual(queued[0]["state"], "QUEUED")

    def test_run_tier1_executes_whitelist(self):
        cq.enqueue("consistency_check", detail="t")
        res = cq.run_tier1(limit=5)
        self.assertEqual(len(res), 1)
        self.assertIn(res[0]["state"], ("EXECUTED", "FAILED"))


if __name__ == "__main__":
    unittest.main()
