"""scripts/export_public_solutions.py --check compares the snapshot with the
catalogue rebuilt as of the snapshot's own generated_at, so a correct
snapshot does not go "stale" in CI just because days pass (freshness labels
and the 45-day cut are date-dependent). Writes only to a temporary file."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))
import export_public_solutions as eps  # noqa: E402


class AsOfCheck(unittest.TestCase):
    def test_the_catalogue_depends_on_the_date(self):
        a = datetime(2026, 10, 29, tzinfo=timezone.utc)
        early, late = eps.build(now=a), eps.build(now=a + timedelta(days=120))
        self.assertNotEqual(eps._comparable(early), eps._comparable(late))

    def test_check_uses_the_snapshot_date_not_today(self):
        old = datetime.now(timezone.utc) - timedelta(days=60)
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "solutions.json"
            out.write_text(eps.render(eps.build(now=old)), encoding="utf-8")
            snap = json.loads(out.read_text(encoding="utf-8"))
            self.assertTrue(snap["generated_at"].startswith(old.date().isoformat()))
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / "export_public_solutions.py"),
                                "--check", "--out", str(out)], capture_output=True, text=True, cwd=ROOT,
                               env=dict(os.environ, PYTHONIOENCODING="utf-8"), timeout=120)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            snap["solutions"] = snap["solutions"][:-1] if snap["solutions"] else [{"x": 1}]
            out.write_text(json.dumps(snap), encoding="utf-8")
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / "export_public_solutions.py"),
                                "--check", "--out", str(out)], capture_output=True, text=True, cwd=ROOT,
                               env=dict(os.environ, PYTHONIOENCODING="utf-8"), timeout=120)
            self.assertEqual(r.returncode, 1, "a changed snapshot must still be reported")


if __name__ == "__main__":
    unittest.main()
