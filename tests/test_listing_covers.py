"""scripts/generate_listing_covers.py: size, match rule, unique files. Temp dirs only.

(Named test_listing_covers.py: tests/test_cover_generator.py belongs to the
parallel session's separate scripts/generate_all_covers.py.)
"""
import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("generate_listing_covers", ROOT / "scripts" / "generate_listing_covers.py")
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)


class TestListingCovers(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.covers = self.tmp / "covers"
        self.covers.mkdir()
        Image.new("RGB", (160, 256), "navy").save(self.covers / "mechanics_lien_filing_kit_cover.png")
        Image.new("RGB", (160, 256), "white").save(self.covers / "test_mechanics_lien_cover.png")

    def test_cover_is_1280x720_and_long_titles_fit(self):
        out = self.tmp / "c.png"
        res = G.make_cover("Etsy Suspension: Triage + Appeal Bundle (Both Steps, 25+ Pages) for Sellers", out)
        with Image.open(out) as im:
            self.assertEqual(im.size, (1280, 720))
        self.assertTrue(res["fits"])
        self.assertGreaterEqual(res["title_font_px"], 40)

    def test_match_needs_strong_overlap_and_never_uses_test_covers(self):
        cands = [p for p in self.covers.glob("*.png") if not G._SKIP_COVER.match(p.name)]
        self.assertEqual([p.name for p in cands], ["mechanics_lien_filing_kit_cover.png"])
        m = G.match_cover("Mechanics Lien Filing Kit for Contractors", cands)
        self.assertEqual(m[0].name, "mechanics_lien_filing_kit_cover.png")
        self.assertIsNone(G.match_cover("Lien Waiver Tracker", cands))      # 1 shared word: too weak

    def test_run_skips_unavailable_and_keeps_duplicate_titles_apart(self):
        rows = [
            {"product_id": "AAA111", "name": "Daily Focus Playbook", "published": True, "has_cover": False},
            {"product_id": "BBB222", "name": "Daily Focus Playbook", "published": True, "has_cover": False},
            {"product_id": "CCC333", "name": "[Unavailable] Old Service", "published": True, "has_cover": False},
            {"product_id": "DDD444", "name": "Has Cover Already", "published": True, "has_cover": True},
        ]
        rep = G.run(rows, covers_dir=self.covers, out_dir=self.tmp / "out")
        self.assertEqual(rep["listings_without_cover"], 2)
        self.assertEqual(len({i["cover_file"] for i in rep["items"]}), 2)
        self.assertEqual([s["product_id"] for s in rep["skipped"]], ["CCC333"])
        self.assertEqual(rep["duplicate_live_titles"], ["Daily Focus Playbook"])


if __name__ == "__main__":
    unittest.main()
