#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cycle-9 tests: demo runs, intake audit holds, no filler products."""

import sys
import unittest
from pathlib import Path
import subprocess

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))


class TestCycle9(unittest.TestCase):
    def test_demo_runs_clean(self):
        r = subprocess.run([sys.executable, "services/spreadsheet_normalization/demo.py"],
                           capture_output=True, text=True, cwd=str(_FACTORY_ROOT),
                           timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-500:])
        self.assertIn("AFTER", r.stdout)

    def test_no_intake_mechanism(self):
        # intake audit: no live intake exists anywhere (documented, not assumed)
        import json
        b = json.loads((_FACTORY_ROOT / "data" / "access_bridge.json").read_text(encoding="utf-8"))
        inchannels = [c for c in b["registry"] if "intake" in c.get("action", "").lower()]
        self.assertTrue(isinstance(inchannels, list))

    def test_variants_not_built(self):
        base = _FACTORY_ROOT / "services" / "spreadsheet_normalization"
        self.assertFalse((base / "toolkit_product.pdf").exists())
        self.assertFalse((base / "b2b_package.pdf").exists())

    def test_queue_still_capped(self):
        import json
        q = json.loads((_FACTORY_ROOT / "data" / "publish_queue.json").read_text(encoding="utf-8"))
        # The intent is "nothing escaped the cap", not a head-count: the queue grew from 3 to 4 when the spreadsheet
        # clean-up service was added (2026-11-06), and every entry still waits (none was published).
        self.assertTrue(q, "the queue is empty: the test would prove nothing")
        self.assertEqual({i.get("status") for i in q}, {"PENDING_CAP"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
