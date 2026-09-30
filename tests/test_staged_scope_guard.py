"""Tier-1 tests: staged-scope guard (the 139f32a-class mistake must not recur)."""
import os
import subprocess
import tempfile
import unittest

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import staged_scope_guard as g


def _git(cwd, *args):
    return subprocess.run(["git"] + list(args), capture_output=True, text=True, cwd=cwd)


class TestScopeGuard(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        _git(self.d, "init", "-q")
        _git(self.d, "config", "user.email", "t@t.t")
        _git(self.d, "config", "user.name", "t")
        open(os.path.join(self.d, "mine.txt"), "w").write("mine\n")
        open(os.path.join(self.d, "foreign.txt"), "w").write("foreign\n")
        _git(self.d, "add", "mine.txt", "foreign.txt")
        _git(self.d, "commit", "-qm", "init")

    def test_foreign_staged_file_aborts_commit(self):
        open(os.path.join(self.d, "mine.txt"), "a").write("more\n")
        open(os.path.join(self.d, "foreign.txt"), "a").write("more\n")
        _git(self.d, "add", "mine.txt", "foreign.txt")  # foreign staged, like 139f32a
        with self.assertRaises(g.ScopeMismatchError) as ctx:
            g.safe_commit("only mine", ["mine.txt"], cwd=self.d)
        self.assertIn("foreign.txt", str(ctx.exception))
        # No commit happened:
        log = _git(self.d, "log", "--oneline").stdout.strip().splitlines()
        self.assertEqual(len(log), 1)

    def test_exact_scope_commits_and_verifies(self):
        open(os.path.join(self.d, "mine.txt"), "a").write("more\n")
        _git(self.d, "add", "mine.txt")
        res = g.safe_commit("only mine", ["mine.txt"], cwd=self.d)
        self.assertEqual(res["scope"], ["mine.txt"])
        self.assertEqual(len(res["sha"]), 40)

    def test_missing_intended_aborts(self):
        with self.assertRaises(g.ScopeMismatchError):
            g.safe_commit("nothing staged", ["mine.txt"], cwd=self.d)

    def test_check_scope_reports_both_directions(self):
        open(os.path.join(self.d, "mine.txt"), "a").write("more\n")
        _git(self.d, "add", "mine.txt")
        c = g.check_scope(["mine.txt", "ghost.txt"], cwd=self.d)
        self.assertFalse(c["ok"])
        self.assertEqual(c["missing_intended"], ["ghost.txt"])


if __name__ == "__main__":
    unittest.main()
