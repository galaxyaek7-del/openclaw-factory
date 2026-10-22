"""Tier-1 test (s10): no committed source may depend on Temp/session paths.

A production process that only runs because a script exists in Temp is not
reproducible after session loss. Tracked .py/.js files must not reference
absolute Temp/AppData locations. (Patterns built piecewise so this file
does not match itself.)
"""
import subprocess
import unittest

ROOT_PATTERNS = ["C:" + chr(92) + "Users", "AppData",
                 chr(92) + "Temp" + chr(92), "/tmp/", "$TEMP", "%TEMP%"]


class TestNoTempDependencies(unittest.TestCase):
    def test_no_absolute_temp_paths_in_tracked_source(self):
        files = subprocess.run(
            ["git", "ls-files", "*.py", "*.js"],
            capture_output=True, text=True).stdout.splitlines()
        hits = []
        for rel in files:
            if rel.startswith("tests/test_no_temp_dependencies"):
                continue
            try:
                with open(rel, encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except OSError:
                continue
            for pat in ROOT_PATTERNS:
                if pat in text:
                    hits.append("%s contains %r" % (rel, pat))
        self.assertEqual(hits, [])

    def test_tracked_tests_never_point_at_an_absolute_repo_root(self):
        # 2026-10-22: four tests did sys.path.insert(0, <absolute repo path>).
        # On any machine where that path holds a different working copy (the
        # founder's machine, while a clean checkout is being verified) every
        # later import in the run resolved there, so a clean-copy CI replay
        # silently tested uncommitted code and failed for reasons that did
        # not exist in the commit. Tests must derive the root from __file__.
        repo_root = ["C:" + chr(92) + "openclaw-dasgboard", "C:/openclaw-dasgboard"]
        files = subprocess.run(
            ["git", "ls-files", "tests/*.py"],
            capture_output=True, text=True).stdout.splitlines()
        hits = []
        for rel in files:
            if rel.startswith("tests/test_no_temp_dependencies"):
                continue
            try:
                with open(rel, encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except OSError:
                continue
            hits.extend("%s contains %r" % (rel, p) for p in repo_root if p in text)
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
