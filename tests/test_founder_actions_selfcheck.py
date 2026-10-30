"""scripts/founder_actions_selfcheck.py: runs every check, records failures and
crashes as findings, and runs at most once per UTC day. Fake checks only; the
real dry runs (network) are not executed here."""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import founder_actions_selfcheck as sc  # noqa: E402

NOW = datetime(2026, 10, 30, 21, tzinfo=timezone.utc)


def ok(tmp):
    return "PASS", "fine"


def broken(tmp):
    return "FAIL", "approval revision mismatch"


def crash(tmp):
    raise KeyError("products")


class SelfCheck(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.out = Path(self.dir.name) / "selfcheck.json"

    def tearDown(self):
        self.dir.cleanup()

    def test_failures_and_crashes_are_findings(self):
        doc = sc.run(NOW, self.out, [("a", ok), ("b", broken), ("c", crash)])
        self.assertEqual(doc["failing"], ["b", "c"])
        self.assertIn("KeyError", doc["results"]["c"]["detail"])
        self.assertEqual(json.loads(self.out.read_text(encoding="utf-8"))["failing"], ["b", "c"])

    def test_once_per_day(self):
        first = sc.once(NOW, self.out, [("a", ok)])
        self.assertEqual(first["action"], "checked")
        self.assertEqual(sc.once(NOW.replace(hour=23), self.out, [("a", broken)])["action"], "none")
        nxt = sc.once(NOW.replace(day=31), self.out, [("a", broken)])
        self.assertEqual((nxt["action"], nxt["detail"]), ("failed", "failing: a"))

    def test_every_documented_section_has_a_check(self):
        names = [n for n, _ in sc.CHECKS]
        for n in ("publish_approved_products", "listing_repairs", "kids_channel_preflight", "accessibility_repair",
                  "analytics_install", "inquiry_queue"):
            self.assertIn(n, names)

    def test_the_result_file_is_git_ignored(self):
        import subprocess
        r = subprocess.run(["git", "check-ignore", "-q", "--no-index", "data/founder_actions_selfcheck.json"], cwd=ROOT)
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
