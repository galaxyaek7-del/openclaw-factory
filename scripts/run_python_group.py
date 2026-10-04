#!/usr/bin/env python3
"""Run one group of the Python test suite and report failures as GitHub
Actions annotations.

Why this exists (2026-10-04): CI could only ever say "Python tests failed".
The job log is not readable from an unauthenticated API, and the Actions
Checks API exposes annotations -- so emitting `::error::` lines makes the
actual failing test and its assertion visible in the GitHub UI, in the PR
"Files changed" annotations, and through the API.

Usage:
    python scripts/run_python_group.py --pattern "test_a*.py"
    python scripts/run_python_group.py tests.test_x.TestY.test_z

Behaviour is otherwise identical to
`python -m unittest discover -s tests -p "<pattern>"`: same discovery, same
exit-code semantics (0 = all green).
"""
import argparse
import io
import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _annotation(message):
    """One `::error::` line. Newlines must be escaped or the workflow command
    is truncated at the first one."""
    text = " ".join(str(message).split())
    print("::error::%s" % text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="*", help="dotted unittest targets")
    ap.add_argument("--pattern")
    args = ap.parse_args()

    if REPO_ROOT not in sys.path:
        sys.path.insert(0, REPO_ROOT)

    if args.targets:
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromNames(args.targets)
    else:
        if not args.pattern:
            ap.error("need --pattern or explicit targets")
        # Mirrors `python -m unittest discover -s tests -p "<pattern>"` exactly:
        # a relative start dir with no top_level_dir, because tests/ has no
        # __init__.py and forcing the repo root as top level raises.
        os.chdir(REPO_ROOT)
        suite = unittest.TestLoader().discover(
            start_dir="tests", pattern=args.pattern)

    buf = io.StringIO()
    result = unittest.TextTestRunner(stream=buf, verbosity=1).run(suite)

    # Always show the tail of the run so counts are visible in the log.
    tail = buf.getvalue().strip().splitlines()[-3:]
    for line in tail:
        print(line)

    print("::group::failure details (%d failed, %d errored)"
          % (len(result.failures), len(result.errors)))

    for kind, entries in (("FAIL", result.failures), ("ERROR", result.errors)):
        for test, tb in entries:
            # unittest's str() for a TestCase carries the docstring; use the id.
            tid = test.id() if hasattr(test, "id") else str(test)
            last = [l for l in tb.strip().splitlines() if l.strip()]
            assertion = last[-1] if last else "(no detail)"
            _annotation("%s %s :: %s" % (kind, tid, assertion[:600]))

    print("::endgroup::")

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())