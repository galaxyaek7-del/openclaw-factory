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

    def test_a_product_awaiting_only_approval_is_not_a_failure(self):
        from unittest import mock
        root = Path(self.dir.name) / "root"
        (root / "data").mkdir(parents=True)
        (root / "data" / "product_registry.json").write_text(json.dumps({"products": [
            {"internal_id": "B16-008", "primary_state": "READY_FOR_AUTHORIZATION"},
            {"internal_id": "B17-001", "primary_state": "READY_FOR_AUTHORIZATION"}]}), encoding="utf-8")
        held = {"authorization": ["authorization: no approval record exists for product 'B17-001'"],
                "files": ["workbook: missing", "authorization: no approval record exists"]}

        def fake(case):
            def run(args, timeout=300):
                report = Path(args[args.index("--report") + 1])
                if "batch16" in args:
                    doc = {"summary": {"pass": 1}, "products": [{"id": "B16-008", "status": "PASS"}]}
                else:
                    doc = {"summary": {"pass": 0, "hold": 1},
                           "products": [{"id": "B17-001", "status": "HOLD", "missing_prerequisites": held[case]}]}
                report.write_text(json.dumps(doc), encoding="utf-8")
                return 0, "", ""
            return run

        with mock.patch.object(sc, "ROOT", root), mock.patch.object(sc, "_run", fake("authorization")):
            status, detail = sc.check_publish(self.dir.name)
        self.assertEqual(status, "PASS")
        self.assertIn("awaiting your approval: B17-001", detail)
        with mock.patch.object(sc, "ROOT", root), mock.patch.object(sc, "_run", fake("files")):
            self.assertEqual(sc.check_publish(self.dir.name)[0], "FAIL")

    def test_the_result_file_is_git_ignored(self):
        import subprocess
        r = subprocess.run(["git", "check-ignore", "-q", "--no-index", "data/founder_actions_selfcheck.json"], cwd=ROOT)
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
