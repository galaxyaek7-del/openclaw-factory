"""Guards the byte-exactness of deliverables against git's line-ending
conversion (found 2026-10-22).

With core.autocrlf=true (this machine's system git config) and no
.gitattributes, git took reportlab's uncompressed PDFs for text and inserted a
CR before every LF on checkout. Six tracked PDFs then differed from their
committed blobs and failed a strict parse ("Broken xref table"). These tests
fail if the attributes that prevent that are removed.

    python -m pytest tests/test_gitattributes_binary.py -q
"""

import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BINARY_SAMPLES = [
    "books/batch12/B12-003_access_continuity_organizer.pdf",
    "any/new/file.pdf",
    "any/new/file.xlsx",
    "any/new/file.docx",
    "any/new/file.zip",
    "any/new/file.png",
]


def _git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")


@unittest.skipUnless(shutil.which("git") and (ROOT / ".git").exists(), "needs a git checkout")
class TestBinaryAttributes(unittest.TestCase):
    def test_gitattributes_exists(self):
        self.assertTrue((ROOT / ".gitattributes").is_file())

    def test_deliverable_types_are_binary(self):
        out = _git("check-attr", "binary", "text", "--", *BINARY_SAMPLES).stdout
        for path in BINARY_SAMPLES:
            self.assertIn(f"{path}: binary: set", out, path)
            self.assertIn(f"{path}: text: unset", out, path)

    def test_tracked_pdfs_on_disk_match_committed_blobs(self):
        # A PDF that differs from its blob only by inserted CRs is the
        # exact defect this file guards against. Genuine edits (different
        # bytes after removing CRs) are not this test's business.
        # Bytes + explicit UTF-8: some tracked paths are non-ASCII, and text
        # mode decodes with the Windows console codepage and returns None.
        raw = subprocess.run(["git", "-c", "core.quotepath=false", "ls-files", "-z", "--", "*.pdf"],
                             cwd=ROOT, capture_output=True).stdout
        listed = raw.decode("utf-8", errors="replace").split("\0")
        damaged = []
        for rel in filter(None, listed):
            path = ROOT / rel
            if not path.is_file():
                continue
            work = path.read_bytes()
            blob = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=ROOT,
                                  capture_output=True).stdout
            if work != blob and work.replace(b"\r\n", b"\n") == blob:
                damaged.append(rel)
        self.assertEqual(damaged, [], "CR bytes inserted into tracked PDFs")


if __name__ == "__main__":
    unittest.main()
