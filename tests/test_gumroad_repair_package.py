"""drafts/release_packages/REPAIR_MANIFEST.json and its builder (2026-10-22).

Checks the committed manifest's shape and that the builder can never write
to a platform. Reads files only; no network.

    python -m pytest tests/test_gumroad_repair_package.py -q
"""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "drafts" / "release_packages" / "REPAIR_MANIFEST.json"
BUILDER = ROOT / "scripts" / "build_gumroad_repair_package.py"


class TestRepairManifest(unittest.TestCase):
    def setUp(self):
        self.m = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_nothing_is_marked_applied(self):
        self.assertEqual(self.m["status"], "PREPARED_NOT_APPLIED")
        for a in self.m["actions"]:
            self.assertEqual(a["status"], "PREPARED_NOT_APPLIED")
            self.assertTrue(a["founder_approval_required"])

    def test_every_action_has_before_after_evidence_and_rollback(self):
        for a in self.m["actions"]:
            for k in ("before", "after", "rollback"):
                self.assertTrue(a[k].strip(), f"{a['slug']}: empty {k}")
            self.assertTrue(a["evidence"], a["slug"])

    def test_required_files_are_hashed_and_pass_their_file_test(self):
        files = [f for a in self.m["actions"] for f in a["required_files"]]
        self.assertGreaterEqual(len(files), 10)
        for f in files:
            self.assertEqual(len(f["sha256"]), 64, f["path"])
            self.assertEqual(f["file_test"], "PASS", f["path"])

    def test_one_recommendation_per_product_no_bulk_targets(self):
        slugs = [a["slug"] for a in self.m["actions"]] + [t["slug"] for t in self.m["thin_product_review"]]
        self.assertEqual(len(slugs), len(set(slugs)))
        for a in self.m["actions"]:
            self.assertNotIn(",", a["slug"])

    def test_the_strongest_product_is_never_proposed_for_unpublishing(self):
        unpublish = {a["slug"] for a in self.m["actions"] if a["action"] in ("unpublish", "delete")}
        self.assertNotIn("iaiyt", unpublish)

    def test_builder_has_no_platform_write_path(self):
        src = BUILDER.read_text(encoding="utf-8")
        for forbidden in ("urlopen", "requests.", "gumroad_publisher", "enable_product", "disable_product",
                          "api.gumroad.com"):
            self.assertNotIn(forbidden, src)


if __name__ == "__main__":
    unittest.main()
