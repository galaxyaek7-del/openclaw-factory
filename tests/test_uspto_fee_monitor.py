"""data_products/uspto_fee_monitor.py on synthetic pages: unchanged, changed,
a code missing, a combined-filing row that must not be read as a single fee,
and a fetch failure. Temp release and log; no network."""
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "data_products"))
import uspto_fee_monitor as m  # noqa: E402

COLS = ["item", "efile_fee_code", "efile_fee_usd", "paper_fee_code", "paper_fee_usd"]


def page(*rows, extra=""):
    cells = "".join("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % r for r in rows)
    return "<html><body><p>(Last revised August 14, 2026)</p><table>%s%s</table></body></html>" % (cells, extra)


class FeeMonitor(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        rel = Path(self.dir.name) / "releases" / "2026-10-29"
        rel.mkdir(parents=True)
        with open(rel / "uspto_trademark_fees.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(COLS)
            w.writerow(["Section 8 declaration", "7205", "325.00", "6205", "425.00"])
            w.writerow(["Base application", "7017", "350.00", "", ""])
        self.releases = rel.parent
        self.log = Path(self.dir.name) / "log.jsonl"

    def tearDown(self):
        self.dir.cleanup()

    def run_(self, html):
        return m.run(html, releases=self.releases, log=self.log)

    def test_unchanged_and_combined_rows_are_not_misread(self):
        combined = ("<tr><td>Combined Section 8 and 15</td><td>575.00</td><td>7205, 7208</td>"
                    "<td>775.00</td><td>6205, 6208</td></tr>")
        out = self.run_(page(("Section 8 declaration", "325.00", "7205", "425.00", "6205"),
                             ("Base application", "350.00", "7017", "n/a", "n/a"), extra=combined))
        self.assertEqual(out["status"], "UNCHANGED", out)
        self.assertEqual(out["page_last_revised"], "August 14, 2026")
        self.assertEqual(json.loads(self.log.read_text(encoding="utf-8").splitlines()[-1])["status"], "UNCHANGED")

    def test_a_changed_amount_is_reported(self):
        out = self.run_(page(("Section 8 declaration", "350.00", "7205", "425.00", "6205"),
                             ("Base application", "1,350.00", "7017", "n/a", "n/a")))
        self.assertEqual(out["status"], "CHANGED")
        self.assertEqual({(c["fee_code"], c["page"]) for c in out["changes"]}, {("7205", "350.00"), ("7017", "1350.00")})

    def test_a_missing_code_is_unreadable_not_guessed(self):
        out = self.run_(page(("Section 8 declaration", "325.00", "7205", "425.00", "6205")))
        self.assertEqual(out["status"], "UNREADABLE")
        self.assertEqual(out["codes_not_found"], ["7017"])

    def test_a_code_with_two_different_amounts_is_unreadable(self):
        out = self.run_(page(("Section 8 declaration", "325.00", "7205", "425.00", "6205"),
                             ("Section 8 (again)", "999.00", "7205", "n/a", "n/a"),
                             ("Base application", "350.00", "7017", "n/a", "n/a")))
        self.assertEqual(out["status"], "UNREADABLE")
        self.assertIn("7205", out["codes_not_found"])

    def test_a_fetch_failure_is_a_result_not_a_crash(self):
        orig = m.fetch
        m.fetch = lambda *a, **k: (_ for _ in ()).throw(OSError("offline"))
        try:
            out = m.run(None, releases=self.releases, log=self.log)
        finally:
            m.fetch = orig
        self.assertEqual((out["status"], out["error"]), ("UNREADABLE", "OSError"))

    def test_the_daily_step_checks_once_per_day(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import uspto_fee_monitor_daily as daily
        from datetime import datetime, timezone
        html = page(("Section 8 declaration", "325.00", "7205", "425.00", "6205"),
                    ("Base application", "350.00", "7017", "n/a", "n/a"))
        t = datetime(2026, 10, 30, 8, tzinfo=timezone.utc)
        first = daily.once(now=t, log=self.log, page_html=html, releases=self.releases)
        self.assertEqual(first["action"], "unchanged")
        again = daily.once(now=t.replace(hour=20), log=self.log, page_html=html, releases=self.releases)
        self.assertEqual(again["action"], "none")
        nxt = daily.once(now=t.replace(day=31), log=self.log, releases=self.releases,
                         page_html=page(("Section 8 declaration", "350.00", "7205", "425.00", "6205"),
                                        ("Base application", "350.00", "7017", "n/a", "n/a")))
        self.assertEqual(nxt["action"], "changed")
        self.assertIn("7205 325.00->350.00", nxt["detail"])

    def test_a_network_failure_is_retried_hourly_the_same_day(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import uspto_fee_monitor_daily as daily
        from datetime import datetime, timezone
        html = page(("Section 8 declaration", "325.00", "7205", "425.00", "6205"),
                    ("Base application", "350.00", "7017", "n/a", "n/a"))
        t = datetime(2026, 10, 31, 0, 4, tzinfo=timezone.utc)
        orig = m.fetch
        m.fetch = lambda *a, **k: (_ for _ in ()).throw(OSError("offline"))
        try:
            self.assertEqual(daily.once(now=t, log=self.log, releases=self.releases)["action"], "unreadable")
            self.assertEqual(daily.once(now=t.replace(minute=30), log=self.log, releases=self.releases)["action"], "none")
        finally:
            m.fetch = orig
        later = daily.once(now=t.replace(hour=1, minute=10), log=self.log, page_html=html, releases=self.releases)
        self.assertEqual(later["action"], "unchanged")
        self.assertEqual(daily.once(now=t.replace(hour=5), log=self.log, page_html=html, releases=self.releases)["action"], "none")

    def test_a_page_that_cannot_be_matched_counts_as_the_days_check(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import uspto_fee_monitor_daily as daily
        from datetime import datetime, timezone
        t = datetime(2026, 11, 2, 0, 4, tzinfo=timezone.utc)
        first = daily.once(now=t, log=self.log, page_html="<html>no table</html>", releases=self.releases)
        self.assertEqual(first["action"], "unreadable")
        again = daily.once(now=t.replace(hour=3), log=self.log, page_html="<html>no table</html>", releases=self.releases)
        self.assertEqual(again["action"], "none")

    def test_the_log_is_git_ignored(self):
        import subprocess
        r = subprocess.run(["git", "check-ignore", "-q", "--no-index", "data/uspto_fee_monitor.jsonl"], cwd=ROOT)
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
