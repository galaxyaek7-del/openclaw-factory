"""Paid product files are not in the public repository (founder decision
2026-10-23). On the factory machine they exist and every test that reads them
runs in full; in CI they are absent by design.

    require_paid_files(*paths)   skip the test in CI when a file is absent;
                                 outside CI a missing file still fails loudly
    paid_files_absent(*paths)    True when running in CI without the files, for
                                 tests that only need a file as a precondition
                                 and test other logic (they mock the
                                 precondition instead of skipping)
"""
import os
import unittest
from pathlib import Path


def _missing(paths):
    return [str(p) for p in paths if not Path(p).exists()]


def paid_files_absent(*paths):
    return bool(os.environ.get("CI")) and bool(_missing(paths))


def require_paid_files(*paths):
    missing = _missing(paths)
    if missing and os.environ.get("CI"):
        raise unittest.SkipTest("paid product file not in the public repository: " + ", ".join(missing))
