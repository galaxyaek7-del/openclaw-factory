"""scripts/delivery_audit_weekly.py: weekly gate around the GET-only delivery
audit. The real audit and the real reports folder are never touched."""
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import delivery_audit_weekly as daw  # noqa: E402


class WeeklyGate(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.reports = Path(self.dir.name)

    def tearDown(self):
        self.dir.cleanup()

    def touch(self, day):
        (self.reports / f"GUMROAD_DELIVERY_AUDIT_{day}.json").write_text("{}")

    def test_recent_report_means_no_run(self):
        self.touch("2026-10-29")
        out = daw.run_once(today=date(2026, 11, 4), reports=self.reports, runner=lambda: self.fail("ran"))
        self.assertEqual(out["action"], "none")

    def test_week_old_report_triggers_a_run(self):
        self.touch("2026-10-22")
        self.touch("2026-10-29")
        out = daw.run_once(today=date(2026, 11, 5), reports=self.reports,
                           runner=lambda: {"published": 109, "issue_counts": {"THIN_DELIVERABLE": 21}})
        self.assertEqual(out["action"], "recorded")
        self.assertIn("109 published", out["detail"])

    def test_no_report_at_all_triggers_a_run(self):
        out = daw.run_once(today=date(2026, 11, 5), reports=self.reports, runner=lambda: {"published": 1})
        self.assertEqual(out["action"], "recorded")

    def test_audit_error_is_reported_not_raised(self):
        def boom():
            raise RuntimeError("gumroad down")
        out = daw.run_once(today=date(2026, 11, 5), reports=self.reports, runner=boom)
        self.assertEqual(out["action"], "failed")

    def test_without_once_flag_it_does_nothing(self):
        self.assertEqual(daw.main([]), 2)


if __name__ == "__main__":
    unittest.main()
