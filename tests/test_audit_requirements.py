"""scripts/audit_requirements.py: HARD vs SOFT classification and local names.

Synthetic files in a temp dir; no git, no network.
"""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("audit_requirements", ROOT / "scripts" / "audit_requirements.py")
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)


class TestAuditRequirements(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "requirements.txt").write_text("requests==2.0\npython-docx==1.2.0\n# numpy==9\n", encoding="utf-8")

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return rel

    def run_audit(self, *files):
        return A.audit(root=str(self.root), tracked=list(files), req_path=str(self.root / "requirements.txt"))

    def test_classifies_hard_soft_and_declared(self):
        f = self.write("mod.py", "\n".join([
            "import os, json",                       # stdlib
            "import requests",                       # declared
            "import docx",                           # declared under its dist name python-docx
            "import numpy",                          # HARD, undeclared (commented out in requirements)
            "try:",
            "    import fitz",                       # guarded -> SOFT
            "except ImportError:",
            "    import PyPDF2",                     # fallback in the handler -> SOFT
            "def f():",
            "    import imageio_ffmpeg",             # lazy -> SOFT
            "try:",
            "    import pandas",                     # try without an import guard -> still HARD
            "except ValueError:",
            "    pass",
        ]))
        r = self.run_audit(f)
        self.assertEqual(set(r["hard"]), {"numpy", "pandas"})
        self.assertEqual(set(r["soft"]), {"fitz", "PyPDF2", "imageio_ffmpeg"})

    def test_local_packages_are_never_reported(self):
        # The bug in the first version: "golden_hunter/hunt.py" became "golden_hun".
        files = [self.write("golden_hunter/hunt.py", "x = 1\n"),
                 self.write("tests/network_guard.py", "x = 1\n"),
                 self.write("app.py", "import golden_hunter\nfrom golden_hunter import hunt\nimport network_guard\n")]
        r = self.run_audit(*files)
        self.assertEqual((r["hard"], r["soft"], r["untracked_local"]), ({}, {}, []))

    def test_untracked_local_code_is_named_as_such(self):
        # present on disk, absent from the tracked list -> missing from the repo
        self.write("helper_pkg/__init__.py", "")
        f = self.write("app.py", "import helper_pkg\n")
        r = self.run_audit(f)
        self.assertIn("helper_pkg", r["hard"])
        self.assertEqual(r["untracked_local"], ["helper_pkg"])

    def test_real_repository_has_no_hard_gaps(self):
        r = A.audit()
        self.assertEqual(r["hard"], {}, "undeclared hard imports: %s" % r["hard"])


if __name__ == "__main__":
    unittest.main()
