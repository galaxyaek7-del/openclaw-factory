"""Regression test for the zero-assumption audit's Medium-High finding:
book_generator.py's legacy create_book() dispatch branch (main(), reached
whenever a --json request has no "topic", no "chapters", and no
product_type == "printable" — exactly the shape CLAUDE.md documents for
plain journal/planner/habit/etc. types) never called
INSPECTORS.final_inspection() at all, violating CONSTITUTION.md section
17's explicit "zero tolerance, no product ships without both guardians'
approval" claim for any caller reaching this branch.

Fix: the legacy branch now runs the same Dual Inspection gate
generate_printable()/generate_book() already use, and logs to
books/_generation_log.jsonl like every other branch (previously it did
neither).

Runs the real CLI via subprocess, exactly how server.js invokes it.

    python -m unittest tests.test_book_generator_legacy_dual_inspection -v
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent


def _run_cli(payload, timeout=60):
    proc = subprocess.run(
        [sys.executable, str(_FACTORY_ROOT / "book_generator.py"), "--json"],
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True, text=True, encoding="utf-8", timeout=timeout,
        cwd=str(_FACTORY_ROOT),
    )
    return json.loads(proc.stdout.strip())


class TestLegacyBranchNowRunsDualInspection(unittest.TestCase):
    def setUp(self):
        self._produced_files = []

    def tearDown(self):
        for f in self._produced_files:
            p = _FACTORY_ROOT / "books" / f
            if p.exists():
                p.unlink()

    def test_legacy_journal_request_carries_a_real_inspection_verdict(self):
        result = _run_cli({
            "title": "Legacy Dual Inspection Test",
            "type": "journal",
            "pages": 2,  # deliberately thin -> should fail the page-count check
        })
        self._produced_files.append(result.get("file"))
        self.assertTrue(result.get("success"), result)
        # The whole point of this fix: these two keys must now be present,
        # not silently absent (which server.js's /generate-book handler
        # would otherwise treat as an unconditional, uninspected success).
        self.assertIn("published", result)
        self.assertIn("inspection", result)
        self.assertIn("technical", result["inspection"])
        self.assertIn("commercial", result["inspection"])

    def test_legacy_branch_now_logs_to_generation_log(self):
        log_path = _FACTORY_ROOT / "books" / "_generation_log.jsonl"
        before = log_path.read_text(encoding="utf-8").count("\n") if log_path.exists() else 0
        result = _run_cli({"title": "Legacy Logging Test", "type": "planner", "pages": 2})
        self._produced_files.append(result.get("file"))
        after = log_path.read_text(encoding="utf-8").count("\n")
        self.assertGreater(after, before, "the legacy branch must append a real entry to _generation_log.jsonl like every other branch")


if __name__ == "__main__":
    unittest.main()
