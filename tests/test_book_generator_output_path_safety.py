"""Regression test for the Phase 10 red-team audit's Critical finding:
book_generator.py's legacy create_book() dispatch branch (reached whenever
a --json request has no "topic", no "chapters", and no
product_type == "printable" — exactly the shape server.js's /generate-book
sends for non-AI book types) built its output path via bare
os.path.abspath(data.get('output')), with no call to
_resolve_safe_output_path(). A caller-supplied "output" like
"../../some_file" or an absolute path could make create_book() write a
PDF over an arbitrary file outside books/.

Fix: the legacy branch now routes through _resolve_safe_output_path(),
same as the other three dispatch branches.

Runs the real CLI via subprocess, exactly how server.js invokes it.

    python -m unittest tests.test_book_generator_output_path_safety -v
"""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
_BOOKS_DIR = _FACTORY_ROOT / "books"


def _run_cli(payload, timeout=60):
    proc = subprocess.run(
        [sys.executable, str(_FACTORY_ROOT / "book_generator.py"), "--json"],
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True, text=True, encoding="utf-8", timeout=timeout,
        cwd=str(_FACTORY_ROOT),
    )
    return json.loads(proc.stdout.strip())


class TestLegacyDispatchOutputPathSafety(unittest.TestCase):
    def _assert_confined_to_books_dir(self, result, marker_outside_path):
        self.assertTrue(result.get("success"), result)
        filename = result.get("file")
        self.assertIsNotNone(filename)
        # The sanitized filename must never contain a path separator —
        # it's a bare name, confined by _resolve_safe_output_path().
        self.assertNotIn("/", filename)
        self.assertNotIn("\\", filename)
        produced_path = _BOOKS_DIR / filename
        self.assertTrue(produced_path.exists(), f"expected {produced_path} to exist")
        self.assertFalse(
            marker_outside_path.exists(),
            f"traversal escaped books/: {marker_outside_path} was created",
        )
        produced_path.unlink(missing_ok=True)

    def test_traversal_output_is_confined_to_books_dir(self):
        marker = _FACTORY_ROOT.parent / "red_team_traversal_marker.pdf"
        marker.unlink(missing_ok=True)
        try:
            result = _run_cli({
                "title": "Red Team Path Safety Test",
                "type": "journal",
                "pages": 2,
                "output": "../red_team_traversal_marker.pdf",
            })
            self._assert_confined_to_books_dir(result, marker)
        finally:
            marker.unlink(missing_ok=True)

    def test_absolute_path_output_is_confined_to_books_dir(self):
        # An absolute-looking path must be reduced to its basename and
        # confined to books/, never treated as a real absolute destination.
        marker = _FACTORY_ROOT / "red_team_absolute_marker_target.pdf"
        marker.unlink(missing_ok=True)
        try:
            fake_absolute = str(marker)
            result = _run_cli({
                "title": "Red Team Absolute Path Test",
                "type": "journal",
                "pages": 2,
                "output": fake_absolute,
            })
            self._assert_confined_to_books_dir(result, marker)
        finally:
            marker.unlink(missing_ok=True)

    def test_dotfile_style_output_is_sanitized_not_overwritten_in_place(self):
        # A caller asking for output ".env" must NOT resolve to the repo's
        # real .env — it must be sanitized into a safe name inside books/.
        real_env = _FACTORY_ROOT / ".env"
        before = real_env.read_bytes() if real_env.exists() else None
        result = _run_cli({
            "title": "Red Team Dotfile Test",
            "type": "journal",
            "pages": 2,
            "output": ".env",
        })
        self.assertTrue(result.get("success"), result)
        filename = result.get("file")
        produced_path = _BOOKS_DIR / filename
        self.assertTrue(produced_path.exists())
        after = real_env.read_bytes() if real_env.exists() else None
        self.assertEqual(before, after, "the real .env must be byte-identical after this call")
        produced_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
