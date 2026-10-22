"""Cycle 105 -- EU AI Act Toolkit revision safeguard.

BACKGROUND (OBSERVED 2026-10-19)
--------------------------------
Cycle 104 reported a PUBLICATION_MISMATCH for this product by comparing the
live Gumroad attachment against the local file named
`books/eu_ai_act_compliance_toolkit.pdf`. That was a false alarm caused by a
stale canonical name, but it exposed a real trap:

  * `books/eu_ai_act_compliance_toolkit.pdf`      (v1, 139,121 B) carries an
    unsupported "ensure compliance" guarantee and is superseded;
  * `books/eu_ai_act_compliance_toolkit_v2.pdf`   (v2, 139,401 B) is the
    repaired revision (Cycle 86) and is what the live listing serves;
  * `data/asset_registry.json` GF-001 pointed at v1, so any future re-upload
    driven by that registry would have silently regressed the product.

These tests make the trap permanently detectable offline. They never call the
network -- the live byte count is cited as recorded evidence, not re-fetched.
"""
import hashlib
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

V1 = ROOT / "books" / "eu_ai_act_compliance_toolkit.pdf"
V2 = ROOT / "books" / "eu_ai_act_compliance_toolkit_v2.pdf"
ASSET_REGISTRY = ROOT / "data" / "asset_registry.json"

# Recorded evidence, not recomputed here:
#   live Gumroad listing for this product (id pzTmMb4v8cih3nbWTj5TeA==, /l/iaiyt)
#   serves a 139,401-byte deliverable and a 106,314-byte preview
#   (reports/CYCLE104/GUMROAD_LISTING_VERIFICATION.json; data/c105_execution_record.json).
LIVE_DELIVERABLE_BYTES = 139401
V1_SHA256 = "c22671a674141e734c4862cfcac871ec697d621693c5457cce4f738d9618c7af"
V2_SHA256 = "18c4158342c7f8a290a4386507e1d6bb7cfdc92420e485d76108d4102a40f6bf"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _gf001():
    registry = json.loads(ASSET_REGISTRY.read_text(encoding="utf-8-sig"))
    for asset in registry["assets"]:
        if asset["asset_id"] == "GF-001":
            return asset
    raise AssertionError("GF-001 is missing from data/asset_registry.json")


def require_v2():
    """v2 is the paid deliverable the live listing serves. books/*.pdf is
    gitignored because this repository is public, so v2 can never exist in
    CI's checkout. Skip there; anywhere else a missing v2 must still fail."""
    if not V2.exists() and os.environ.get("CI"):
        raise unittest.SkipTest("paid deliverable not in public repo: " + str(V2))


class TestRevisionsExist(unittest.TestCase):
    def test_both_revisions_are_present_as_an_audit_trail(self):
        self.assertTrue(V1.exists(), "the superseded revision must be kept, not deleted")
        require_v2()
        self.assertTrue(V2.exists())

    def test_hashes_match_the_recorded_evidence(self):
        self.assertEqual(_sha256(V1), V1_SHA256)
        require_v2()
        self.assertEqual(_sha256(V2), V2_SHA256)

    def test_v2_is_the_revision_the_live_listing_serves(self):
        require_v2()
        self.assertEqual(V2.stat().st_size, LIVE_DELIVERABLE_BYTES)

    def test_v1_is_not_the_revision_the_live_listing_serves(self):
        self.assertNotEqual(V1.stat().st_size, LIVE_DELIVERABLE_BYTES)


class TestContentDifference(unittest.TestCase):
    """The two revisions must remain distinguishable by the text that
    actually changed -- otherwise the safeguard is vacuous."""

    @classmethod
    def setUpClass(cls):
        require_v2()
        from pypdf import PdfReader

        def text(path):
            return "\n".join((p.extract_text() or "") for p in PdfReader(str(path)).pages)

        cls.v1_text = text(V1).lower()
        cls.v2_text = text(V2).lower()

    def test_superseded_revision_carries_the_unsupported_guarantee(self):
        self.assertIn("ensure compliance", self.v1_text)

    def test_served_revision_carries_the_reworded_claim(self):
        self.assertIn("pursue compliance", self.v2_text)

    def test_served_revision_keeps_the_liability_disclaimer(self):
        self.assertIn("not legal advice", self.v2_text)


class TestRegistryPointsAtTheServedRevision(unittest.TestCase):
    def test_asset_registry_gf001_names_the_served_revision(self):
        recorded = _gf001()["product_genome"]["file"].replace("\\", "/")
        self.assertEqual(
            recorded, "books/eu_ai_act_compliance_toolkit_v2.pdf",
            "GF-001 must point at the revision the live listing serves; "
            "pointing at v1 risks silently republishing an unsupported claim",
        )

    def test_asset_registry_gf001_file_exists_and_matches_live_bytes(self):
        recorded = ROOT / _gf001()["product_genome"]["file"]
        require_v2()
        self.assertTrue(recorded.exists(), f"GF-001 points at a missing file: {recorded}")
        self.assertEqual(recorded.stat().st_size, LIVE_DELIVERABLE_BYTES)

    def test_asset_registry_gf001_does_not_point_at_the_superseded_revision(self):
        recorded = ROOT / _gf001()["product_genome"]["file"]
        self.assertNotEqual(recorded.resolve(), V1.resolve())


if __name__ == "__main__":
    unittest.main()
