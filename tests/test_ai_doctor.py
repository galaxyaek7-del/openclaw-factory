"""Tests for ai_doctor.py (EOS Phase 2, 2026-07-19): the real,
non-fabricated engineering-health system replacing quality_doctor.py's
confirmed-fake pattern.

Runs with stdlib unittest. Every function reads only from temp-file-
isolated fixtures or mocked subprocess calls -- never assumes a
specific real npm/pip result.

    python -m unittest tests.test_ai_doctor -v
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import ai_doctor


def _write_file(content):
    fd, path = tempfile.mkstemp()
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


class TestCheckPythonPinning(unittest.TestCase):
    def tearDown(self):
        for p in getattr(self, "_paths", []):
            if os.path.exists(p):
                os.remove(p)

    def test_pinned_and_unpinned_correctly_classified(self):
        path = _write_file("reportlab==5.0.0\nrequests>=2.0\n# comment\n\nflask\n")
        self._paths = [path]
        result = ai_doctor._check_python_pinning(path)
        self.assertEqual(result["pinned"], 1)
        self.assertEqual(set(result["unpinned"]), {"requests", "flask"})

    def test_missing_file_returns_honest_zero(self):
        result = ai_doctor._check_python_pinning("/no/such/requirements.txt")
        self.assertEqual(result["checked"], 0)


class TestCheckNodePinning(unittest.TestCase):
    def tearDown(self):
        for p in getattr(self, "_paths", []):
            if os.path.exists(p):
                os.remove(p)

    def test_pinned_and_unpinned_correctly_classified(self):
        path = _write_file(json.dumps({"dependencies": {"express": "5.2.1", "cors": "^2.8.6"}}))
        self._paths = [path]
        result = ai_doctor._check_node_pinning(path)
        self.assertEqual(result["pinned"], 1)
        self.assertEqual(result["unpinned"], ["cors"])

    def test_missing_file_returns_honest_zero(self):
        result = ai_doctor._check_node_pinning("/no/such/package.json")
        self.assertEqual(result["checked"], 0)


class TestCheckNpmAudit(unittest.TestCase):
    def test_npm_not_found_reports_honestly(self):
        with patch("shutil.which", return_value=None):
            result = ai_doctor._check_npm_audit()
        self.assertFalse(result["available"])

    def test_real_registry_error_surfaces_the_real_message_not_fabricated(self):
        import subprocess
        fake_result = subprocess.CompletedProcess(
            args=[], returncode=1,
            stdout=json.dumps({"message": "404 Not Found - registry mirror error"}),
        )
        with patch("shutil.which", return_value="/usr/bin/npm"), patch("subprocess.run", return_value=fake_result):
            result = ai_doctor._check_npm_audit()
        self.assertFalse(result["available"])
        self.assertIn("404", result["reason"])

    def test_real_success_shape_reports_vulnerabilities(self):
        import subprocess
        fake_result = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout=json.dumps({"metadata": {"vulnerabilities": {"high": 0, "low": 1}}}),
        )
        with patch("shutil.which", return_value="/usr/bin/npm"), patch("subprocess.run", return_value=fake_result):
            result = ai_doctor._check_npm_audit()
        self.assertTrue(result["available"])
        self.assertEqual(result["vulnerabilities"]["low"], 1)

    def test_subprocess_exception_reports_honestly_never_throws(self):
        with patch("shutil.which", return_value="/usr/bin/npm"), patch("subprocess.run", side_effect=OSError("boom")):
            result = ai_doctor._check_npm_audit()
        self.assertFalse(result["available"])


class TestBuildAiDoctorReport(unittest.TestCase):
    def test_real_call_against_real_data_never_throws(self):
        report = ai_doctor.build_ai_doctor_report()
        for key in ("evolution", "infrastructure", "dependency_risk"):
            self.assertIn(key, report)

    def test_render_markdown_never_throws(self):
        report = ai_doctor.build_ai_doctor_report()
        md = ai_doctor.render_markdown(report)
        self.assertIsInstance(md, str)
        self.assertIn("AI Doctor", md)
        self.assertIn("مخاطر التبعيات", md)


if __name__ == "__main__":
    unittest.main()
