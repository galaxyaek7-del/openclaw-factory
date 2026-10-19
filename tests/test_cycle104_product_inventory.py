"""Tests for scripts/cycle104_product_inventory.py (Cycle 104, 2026-10-19).

    python -m unittest tests.test_cycle104_product_inventory -v

The generator merges real sources; these tests drive it entirely from
fixtures so they never depend on live account state.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import scripts.cycle104_product_inventory as cpi


def _write(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


class TestReleaseState(unittest.TestCase):
    def test_highest_verified_milestone_wins_regardless_of_dict_order(self):
        record = {"milestones": {
            "CHECKOUT_VERIFIED": {"status": "VERIFIED"},
            "BUILD_COMPLETE": {"status": "VERIFIED"},
        }}
        self.assertEqual(cpi._release_state(record)["state"], "CHECKOUT_VERIFIED")

    def test_unverified_milestones_are_ignored(self):
        record = {"milestones": {
            "BUILD_COMPLETE": {"status": "VERIFIED"},
            "FIRST_SALE_VERIFIED": {"status": "NOT_VERIFIED"},
        }}
        state = cpi._release_state(record)
        self.assertEqual(state["state"], "BUILD_COMPLETE")
        self.assertNotIn("FIRST_SALE_VERIFIED", state["verified_milestones"])

    def test_no_record_is_unknown_never_assumed(self):
        self.assertEqual(cpi._release_state(None)["state"], "UNKNOWN")
        self.assertEqual(cpi._release_state({"milestones": {}})["state"], "UNKNOWN")

    def test_unrecognised_milestone_names_are_disclosed(self):
        record = {"milestones": {"SOMETHING_NEW": {"status": "VERIFIED"}}}
        state = cpi._release_state(record)
        self.assertEqual(state["state"], "UNKNOWN")
        self.assertEqual(state["unrecognised_milestones"], ["SOMETHING_NEW"])


class TestInventoryBuild(unittest.TestCase):
    def _fixtures(self, tmp, cq_status="PASS", artifact_exists=True):
        books = Path(tmp) / "books" / "batch12"
        books.mkdir(parents=True, exist_ok=True)
        if artifact_exists:
            (books / "B12-001_thing.xlsx").write_bytes(b"real-bytes")
        catalog = {"products": [{
            "internal_product_id": "W9FpZXpQB==",
            "product_name": "Real Product",
            "product_type": "gumroad_digital_product",
            "source_files": ["books/batch12/B12-001_thing.xlsx"],
            "pricing_usd": 14.99,
            "platforms": {"gumroad": {"status": "PUBLISHED"}},
            "publication_status": "PUBLISHED",
            "checkout_url": "https://example.test/l/x",
            "revenue_usd": 0, "refunds_usd": 0,
        }]}
        operational = {"products": [{"product_id": "B12-001", "milestones": {
            "BUILD_COMPLETE": {"status": "VERIFIED"},
            "CHECKOUT_VERIFIED": {"status": "VERIFIED"},
        }}]}
        verification = {"verified_at": "2026-10-19T18:58:16+00:00", "results": [
            {"product": "B12-001", "state": "PUBLISHED_VERIFIED_WITH_REVIEW_ITEMS",
             "review_items": ["attachment names not exposed"]}]}
        qa = {"generated_at": "2026-10-19T19:05:35+00:00", "results": [{
            "id": "B12-001",
            "gate": {"file": "reports/B12-001/GATE_FINAL.json", "verdict": "APPROVED"},
            "enforcer_verdict": "BLOCKED_MISSING_DATA",
            "layers": {"content_quality": {"status": cq_status, "score": 100}},
            "artifacts_tracked_in_git": {"books/batch12/B12-001_thing.xlsx": True},
        }]}
        paths = {}
        for name, data in (("catalog", catalog), ("operational", operational),
                           ("verification", verification), ("qa", qa)):
            p = os.path.join(tmp, f"{name}.json")
            _write(p, data)
            paths[name] = p
        return paths, Path(tmp) / "books"

    def test_merges_real_sources_and_never_claims_purchasable(self):
        with tempfile.TemporaryDirectory() as tmp:
            p, books = self._fixtures(tmp)
            inv = cpi.build_digital_product_inventory(
                catalog=json.load(open(p["catalog"], encoding="utf-8")),
                verification_path=p["verification"], qa_path=p["qa"],
                operational_path=p["operational"], books_root=books)
            self.assertEqual(inv["totals"]["products"], 1)
            self.assertEqual(inv["totals"]["published"], 1)
            self.assertEqual(inv["totals"]["revenue_usd"], 0)
            self.assertEqual(inv["products"][0]["local_id"], "B12-001")
            self.assertEqual(inv["products"][0]["release_state"]["state"], "CHECKOUT_VERIFIED")
            self.assertEqual(inv["products"][0]["purchasable"], "UNKNOWN")
            self.assertEqual(inv["totals"]["purchasable"], "UNKNOWN")
            self.assertEqual(inv["products"][0]["listing_verification"]["state"],
                             "PUBLISHED_VERIFIED_WITH_REVIEW_ITEMS")
            self.assertEqual(inv["products"][0]["qa"]["gate_verdict"], "APPROVED")

    def test_real_artifact_bytes_are_measured_not_trusted(self):
        with tempfile.TemporaryDirectory() as tmp:
            p, books = self._fixtures(tmp)
            inv = cpi.build_digital_product_inventory(
                catalog=json.load(open(p["catalog"], encoding="utf-8")),
                verification_path=p["verification"], qa_path=p["qa"],
                operational_path=p["operational"], books_root=books)
            art = inv["products"][0]["local_artifacts"][0]
            self.assertTrue(art["exists"])
            self.assertEqual(art["size_bytes"], len(b"real-bytes"))
            self.assertEqual(len(art["sha256"]), 64)

    def test_missing_artifact_becomes_a_disclosed_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            p, books = self._fixtures(tmp, artifact_exists=False)
            inv = cpi.build_digital_product_inventory(
                catalog=json.load(open(p["catalog"], encoding="utf-8")),
                verification_path=p["verification"], qa_path=p["qa"],
                operational_path=p["operational"], books_root=books)
            self.assertFalse(inv["products"][0]["local_artifacts"][0]["exists"])
            self.assertTrue(any("missing on disk" in g for g in inv["gaps"]))

    def test_content_quality_failure_becomes_a_disclosed_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            p, books = self._fixtures(tmp, cq_status="FAIL")
            inv = cpi.build_digital_product_inventory(
                catalog=json.load(open(p["catalog"], encoding="utf-8")),
                verification_path=p["verification"], qa_path=p["qa"],
                operational_path=p["operational"], books_root=books)
            self.assertTrue(any("content-quality layer FAIL" in g for g in inv["gaps"]))

    def test_harness_verdict_is_reported_but_never_drives_a_gap(self):
        """BLOCKED_MISSING_DATA is a harness limitation, not a product verdict."""
        with tempfile.TemporaryDirectory() as tmp:
            p, books = self._fixtures(tmp)
            inv = cpi.build_digital_product_inventory(
                catalog=json.load(open(p["catalog"], encoding="utf-8")),
                verification_path=p["verification"], qa_path=p["qa"],
                operational_path=p["operational"], books_root=books)
            self.assertEqual(inv["products"][0]["qa"]["harness_verdict"],
                             "BLOCKED_MISSING_DATA")
            self.assertFalse(any("BLOCKED_MISSING_DATA" in g for g in inv["gaps"]))

    def test_missing_source_files_do_not_crash_the_inventory(self):
        inv = cpi.build_digital_product_inventory(
            catalog={"products": []}, verification_path="C:/nope.json",
            qa_path="C:/nope.json", operational_path="C:/nope.json")
        self.assertEqual(inv["totals"]["products"], 0)
        self.assertEqual(inv["totals"]["purchasable"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
