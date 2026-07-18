"""Tests for recovery/snapshot.py (Unified Recovery System §7,
2026-07-18): the backup-snapshot-before-a-critical-operation helper.

    python -m unittest tests.test_snapshot -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from recovery import snapshot


def _temp_file(content="hello"):
    fd, path = tempfile.mkstemp()
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    return path


class TestSnapshotBefore(unittest.TestCase):
    def setUp(self):
        self._created = []

    def tearDown(self):
        for p in self._created:
            if os.path.exists(p):
                os.remove(p)

    def test_existing_file_is_copied_with_a_snapshot_suffix(self):
        p = _temp_file("real content")
        self._created.append(p)
        results = snapshot.snapshot_before("test reason", paths=[Path(p)])
        self.assertEqual(len(results), 1)
        self.assertIsNotNone(results[0]["snapshot"])
        self.assertIsNone(results[0]["error"])
        self._created.append(results[0]["snapshot"])
        with open(results[0]["snapshot"], encoding="utf-8") as f:
            self.assertEqual(f.read(), "real content")

    def test_missing_file_is_skipped_not_an_error(self):
        results = snapshot.snapshot_before("test reason", paths=[Path("/no/such/file.json")])
        self.assertEqual(results[0]["snapshot"], None)
        self.assertEqual(results[0]["error"], None)

    def test_multiple_targets_each_get_their_own_snapshot(self):
        p1 = _temp_file("a")
        p2 = _temp_file("b")
        self._created.extend([p1, p2])
        results = snapshot.snapshot_before("test reason", paths=[Path(p1), Path(p2)])
        self.assertEqual(len(results), 2)
        for r in results:
            if r["snapshot"]:
                self._created.append(r["snapshot"])
        self.assertTrue(all(r["snapshot"] for r in results))

    def test_never_raises_even_with_a_completely_invalid_path(self):
        try:
            snapshot.snapshot_before("test reason", paths=[Path("")])
        except Exception as e:
            self.fail(f"snapshot_before must never raise, got: {e}")


if __name__ == "__main__":
    unittest.main()
