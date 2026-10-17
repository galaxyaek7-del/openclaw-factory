"""scripts/research_b12_competitors.py: records only founder-checked, sourced prices."""
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("research_b12", ROOT / "scripts" / "research_b12_competitors.py")
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)


class TestResearchB12(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_nothing_recorded_means_nothing_saved(self):
        self.assertEqual(R.COMPETITORS, [])                       # ships empty: never pre-filled
        res = R.run([], out=self.tmp / "c.json", inspect=False)
        self.assertFalse(res["saved"])
        self.assertFalse((self.tmp / "c.json").exists())

    def test_only_sourced_positive_prices_are_kept(self):
        entries = [R.record_competitor("A", "https://a.example/x", 39),
                   R.record_competitor("B", "not a url", 19),
                   R.record_competitor("C", "https://c.example/y", 0),
                   R.record_competitor("D", "https://d.example/z", 49)]
        res = R.run(entries, out=self.tmp / "c.json", inspect=False)
        self.assertEqual((res["saved"], res["valid"], len(res["rejected"])), (True, 2, 2))
        self.assertFalse(res["ready_for_pricing"])                # fewer than 3
        saved = json.loads((self.tmp / "c.json").read_text(encoding="utf-8"))
        self.assertEqual([c["name"] for c in saved["competitors"]], ["A", "D"])
        self.assertTrue(all(c["verified_by"] == "Founder" for c in saved["competitors"]))


if __name__ == "__main__":
    unittest.main()
