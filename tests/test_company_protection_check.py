"""scripts/company_protection_check.py: each check reads an existing signal;
failures are findings, a crash is a finding, once per day. Temp paths only."""
import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import company_protection_check as pc  # noqa: E402

NOW = datetime(2026, 10, 31, 15, tzinfo=timezone.utc)


class Protection(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "data").mkdir()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_live_switch_left_on_fails(self):
        (self.root / ".env").write_text("A=1\nFACTORY_LIVE_PUBLISH=true\n", encoding="utf-8")
        self.assertEqual(pc.check_live_write_switch(self.root)[0], "FAIL")
        (self.root / ".env").write_text("FACTORY_LIVE_PUBLISH=false\n", encoding="utf-8")
        self.assertEqual(pc.check_live_write_switch(self.root)[0], "PASS")

    def test_held_listing_still_published_fails(self):
        d = self.root / "data"
        (d / "hold_products.json").write_text(json.dumps({"products": {"x": {"product_id": "P1"}}}), encoding="utf-8")
        reg = {"products": [{"published": True, "url": "https://g/l/x", "external_ids": {"gumroad": "P1"}}]}
        (d / "product_registry.json").write_text(json.dumps(reg), encoding="utf-8")
        status, detail = pc.check_withdrawn_listings(self.root)
        self.assertEqual(status, "FAIL")
        self.assertIn("https://g/l/x", detail)
        reg["products"][0]["published"] = False
        (d / "product_registry.json").write_text(json.dumps(reg), encoding="utf-8")
        self.assertEqual(pc.check_withdrawn_listings(self.root)[0], "PASS")

    def test_backup_missing_stale_or_fresh(self):
        self.assertEqual(pc.check_backup(self.root, NOW.date())[0], "FAIL")
        import backup_local_data as b
        (self.root / "data" / "x.jsonl").write_bytes(b"1\n")
        b.run(datetime(2026, 10, 25, tzinfo=timezone.utc), self.root, self.root / "data" / "_backups", ["data/x.jsonl"])
        self.assertIn("days old", pc.check_backup(self.root, NOW.date())[1])
        b.run(NOW, self.root, self.root / "data" / "_backups", ["data/x.jsonl"])
        self.assertEqual(pc.check_backup(self.root, NOW.date())[0], "PASS")

    def test_crash_is_a_finding_and_once_per_day(self):
        out = self.root / "p.json"

        def boom():
            raise KeyError("x")
        checks = [("ok", lambda: ("PASS", "fine")), ("broken", boom)]
        r = pc.once(NOW, out, checks)
        self.assertEqual((r["action"], r["detail"]), ("failed", "failing: broken"))
        self.assertEqual(pc.once(NOW.replace(hour=20), out, checks)["action"], "none")

    def test_result_file_is_git_ignored(self):
        import subprocess
        r = subprocess.run(["git", "check-ignore", "-q", "--no-index", "data/company_protection.json"], cwd=ROOT)
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
