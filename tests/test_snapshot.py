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


class TestDefaultSnapshotTargets(unittest.TestCase):
    """Full Factory Integrity Audit (2026-07-22) + CTO+COO audit closure
    (2026-08-15, GAP-BACK-007): confirms the real data files that exist on
    disk and carry corruption risk are covered by the snapshot system.
    The prior assertion referenced paddle_checkout_notifications.json, which
    was verified to never exist on disk (silently skipped); it has been
    replaced by the real revenue/affiliate/state ledgers."""

    def test_all_session_data_files_are_covered(self):
        names = {p.name for p in snapshot.DEFAULT_SNAPSHOT_TARGETS}
        for expected in ("market_evidence.jsonl", "board_meetings.jsonl",
                         "paddle_products.json", "commission_ledger.jsonl",
                         "affiliate_clicks.jsonl", "safe_mode_state.json",
                         "publish_protection_state.json"):
            self.assertIn(expected, names)

    def test_env_secret_config_is_covered_by_default_targets(self):
        """Security P1 C2 (2026-08-18): the real API keys live in .env and
        had zero snapshot coverage. Its snapshot copy is gitignored
        (plaintext secrets must never reach git)."""
        names = {p.name for p in snapshot.DEFAULT_SNAPSHOT_TARGETS}
        self.assertIn(".env", names)

    # Targets that are deliberately absent on a fresh checkout. `.env` holds the
    # real API keys, is gitignored, and CI step 11 ("Verify .env is never tracked
    # in git") fails the build if it ever is. It is a snapshot target precisely
    # BECAUSE it is local-only, so requiring it to exist in a clean checkout
    # contradicts the repo's own security rule -- the test directly above asserts
    # it must be covered.
    INTENTIONALLY_ABSENT_ON_FRESH_CHECKOUT = {".env"}

    def test_no_target_is_a_non_existent_file(self):
        """Real correction 2026-10-03: this failed in CI on two counts.

        Five targets (factory_state.json, board_meetings.jsonl,
        commission_ledger.jsonl, affiliate_clicks.jsonl, safe_mode_state.json,
        publish_protection_state.json) were simply untracked, so they silently
        did not exist on a fresh checkout -- the exact GAP-BACK-007 failure this
        guard exists to catch. Those are now tracked.

        The remaining target is `.env`, which can never exist on a fresh
        checkout by design. The guard still holds for everything real: any
        target that is neither present nor explicitly declared local-only is
        still a stale entry.
        """
        for p in snapshot.DEFAULT_SNAPSHOT_TARGETS:
            if p.name in self.INTENTIONALLY_ABSENT_ON_FRESH_CHECKOUT:
                continue
            self.assertTrue(p.exists(), f"stale snapshot target: {p}")

    def test_every_absent_target_is_explicitly_justified(self):
        """Keeps the exemption list honest: nothing may silently vanish."""
        for p in snapshot.DEFAULT_SNAPSHOT_TARGETS:
            if p.exists():
                continue
            self.assertIn(
                p.name, self.INTENTIONALLY_ABSENT_ON_FRESH_CHECKOUT,
                f"{p} does not exist and has no recorded justification",
            )

    def test_env_is_actually_gitignored(self):
        """The exemption above is only safe while .env really is untracked."""
        import subprocess
        root = str(snapshot._FACTORY_ROOT)
        result = subprocess.run(
            ["git", "check-ignore", "-q", ".env"],
            cwd=root, capture_output=True,
        )
        self.assertEqual(result.returncode, 0, ".env must stay gitignored")


if __name__ == "__main__":
    unittest.main()
