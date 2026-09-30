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


if __name__ == "__main__":
    unittest.main()
