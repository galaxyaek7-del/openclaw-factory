# -*- coding: utf-8 -*-
"""A stale local snapshot may never assert that Gumroad is blocked (c109).

Root cause this guards against
------------------------------
`commercial_monitor.check_checkout_readiness()` computed its "Gumroad status"
from a local asset registry snapshot and then emitted a hard verdict from it:

    products=20  published=0
    status="BLOCKED"
    blocking_note="All channels blocked - founder action required"

while the live Gumroad API returned published=True for every product checked,
with real delivery files attached. Every one of the 20 registry entries was
still at production_status="PRODUCED" and the file was 21.6 days stale, so
`is_published` was False BY CONSTRUCTION - it could not be anything else, no
matter what was actually live on the platform.

That is the worst class of bug in this factory: it invents a blocker and points
the founder at a channel that is working.

What is asserted here
---------------------
1. The gumroad block declares it is a local snapshot, with its age.
2. It explicitly states it is not evidence about the live platform.
3. The blocking note may not tell the founder to act on stale-snapshot grounds.
4. The verdict may never be driven by the snapshot's staleness alone.
"""
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import commercial_monitor as cm


class TestSnapshotCannotAssertBlocker(unittest.TestCase):
    def _stale_registry(self, tmpdir, days_old):
        path = os.path.join(tmpdir, "asset_registry.json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write('{"assets": [%s]}' % ", ".join(
                '{"asset_id": "GF-%d", "product_name": "P%d",'
                ' "production_status": "PRODUCED",'
                ' "product_genome": {"platform": "gumroad_digital"}}' % (i, i)
                for i in range(5)))
        old = time.time() - days_old * 86400
        os.utime(path, (old, old))
        return path

    def _run(self, days_old):
        tmpdir = tempfile.mkdtemp(prefix="c109_")
        reg = self._stale_registry(tmpdir, days_old)
        paddle = os.path.join(tmpdir, "paddle.json")
        with open(paddle, "w", encoding="utf-8") as fh:
            fh.write('{"products": []}')
        with mock.patch.object(cm, "ASSET_REGISTRY_PATH", Path(reg)), \
             mock.patch.object(cm, "PADDLE_PRODUCTS_PATH", Path(paddle)):
            return cm.check_checkout_readiness()

    def test_block_declares_itself_a_local_snapshot(self):
        out = self._run(days_old=21.6)
        g = out["gumroad"]
        self.assertEqual(g["evidence_source"], "LOCAL_SNAPSHOT_ONLY")
        self.assertIsInstance(g["registry_age_days"], float)
        self.assertTrue(g["snapshot_is_stale"])

    def test_block_refuses_to_claim_live_platform_state(self):
        g = self._run(days_old=21.6)["gumroad"]
        self.assertIn("NOT the live Gumroad API", g["snapshot_caveat"])
        self.assertIn("UNKNOWN", g["live_platform_state"])

    def test_blocking_note_never_blames_the_founder_on_a_stale_snapshot(self):
        out = self._run(days_old=21.6)
        note = out.get("blocking_note") or ""
        self.assertNotIn("founder action required", note.lower())
        self.assertIn("stale local file", note)

    def test_a_fresh_snapshot_is_not_flagged_stale(self):
        g = self._run(days_old=0.0)["gumroad"]
        self.assertFalse(g["snapshot_is_stale"])

    def test_published_count_still_comes_from_the_snapshot(self):
        # The snapshot is still reported truthfully as what it records; only its
        # authority to assert a blocker was removed.
        out = self._run(days_old=21.6)
        self.assertEqual(out["gumroad"]["total_products"], 5)
        self.assertEqual(out["gumroad"]["published"], 0)


if __name__ == "__main__":
    unittest.main()
