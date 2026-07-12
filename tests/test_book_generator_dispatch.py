"""Regression test for book_generator.py's --json CLI dispatch (code review
fix, 2026-07-12): an empty "chapters": [] must route to
generate_book_from_content() and fail with its own clear ValueError, never
fall through to the legacy create_book() cookbook-placeholder path.

Runs the real CLI via subprocess (matches how server.js/scripts/
process_approved_drafts.py invoke it) — no mocking, this is exactly the
malformed-draft scenario that motivated the fix.

    python -m unittest tests.test_book_generator_dispatch -v
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent


def _run_cli(payload, timeout=30):
    proc = subprocess.run(
        [sys.executable, str(_FACTORY_ROOT / "book_generator.py"), "--json"],
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True, text=True, encoding="utf-8", timeout=timeout,
        cwd=str(_FACTORY_ROOT),
    )
    return json.loads(proc.stdout.strip())


class TestChaptersDispatch(unittest.TestCase):
    def test_empty_chapters_list_fails_clearly_not_via_legacy_path(self):
        result = _run_cli({
            "title": "Regression Test Draft",
            "chapters": [],
            "price": 97,
            "product_type": "premium",
        })
        self.assertFalse(result["success"])
        self.assertIn("chapters", result["error"])
        # Must NOT look like the legacy create_book() success shape.
        self.assertNotIn("pages", result)

    def test_non_empty_chapters_routes_to_generate_book_from_content(self):
        result = _run_cli({
            "title": "Regression Test Draft With Content",
            "chapters": [{"title": "Ch1", "content": "Real content for the regression test."}],
            "price": 97,
            "product_type": "premium",
        })
        self.assertTrue(result["success"])
        # Only generate_book_from_content()'s result shape has these keys.
        self.assertEqual(result.get("content_source"), "human_claude_review")
        self.assertIn("published", result)


if __name__ == "__main__":
    unittest.main()
