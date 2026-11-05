"""Tests for cohort_contract (backlog B9): cohort products behind the manifest contract."""
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cohort_contract as cc


def _make_product(root, pid="GF-T-01", slug="demo_kit", words=6000, pages=12):
    """A minimal cohort product on disk: dist/<id>/{pdf,xlsx,docx,README}, dist/<slug>_bundle.zip."""
    import docx
    import openpyxl
    cohort = Path(root) / "cohort_T"
    pdir = cohort / "dist" / pid
    pdir.mkdir(parents=True)
    (pdir / f"{slug}_guide.pdf").write_bytes(b"%PDF-1.4 fake but non-empty")
    wb = openpyxl.Workbook()
    wb.active["A1"] = "x"
    wb.save(pdir / f"{slug}_workbook.xlsx")
    d = docx.Document()
    d.add_paragraph("template")
    d.save(pdir / "signoff_form.docx")
    (pdir / "README.txt").write_text("readme", encoding="utf-8")
    bundle = cohort / "dist" / f"{slug}_bundle.zip"
    with zipfile.ZipFile(bundle, "w") as z:
        for f in sorted(pdir.iterdir()):
            z.write(f, f"{slug}/{f.name}")
    manifest = {"cohort": "T", "id": pid, "slug": slug, "name": "Demo Kit", "price_cents": 4900,
                "guide_words": words, "guide_pages": pages, "bundle": bundle.name,
                "bundle_bytes": bundle.stat().st_size,
                "files": sorted(f.name for f in pdir.iterdir())}
    (pdir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return cohort, pdir, bundle, manifest


class ContractShape(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cohort, self.pdir, self.bundle, self.man = _make_product(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_contract_has_the_batch14_shape_and_passes_qa(self):
        c = cc.to_contract(self.man, self.pdir, self.bundle, self.root)
        for key in ("id", "slug", "title", "price_cents", "files", "qa"):
            self.assertIn(key, c)
        self.assertEqual(c["title"], "Demo Kit")
        self.assertEqual({"guide", "workbook", "readme", "bundle"} <= set(c["files"]), True)
        self.assertTrue(any(r.startswith("template_") for r in c["files"]))
        for f in c["files"].values():
            self.assertEqual(set(f), {"path", "bytes", "sha256"})
            self.assertEqual(len(f["sha256"]), 64)
            self.assertNotIn("\\", f["path"])
        self.assertTrue(c["qa"]["ok"], c["qa"]["problems"])

    def test_manifest_json_is_not_listed_as_a_product_file(self):
        c = cc.to_contract(self.man, self.pdir, self.bundle, self.root)
        self.assertFalse(any(f["path"].endswith("manifest.json") for f in c["files"].values()))

    def test_contract_is_written_outside_the_zipped_folder_and_cohort_manifest_untouched(self):
        before = (self.pdir / "manifest.json").read_bytes()
        names_before = sorted(p.name for p in self.pdir.iterdir())
        cc.write_for_product(self.man, self.pdir, self.bundle, self.root)
        self.assertEqual((self.pdir / "manifest.json").read_bytes(), before)
        self.assertEqual(sorted(p.name for p in self.pdir.iterdir()), names_before)
        self.assertTrue((self.cohort / "contracts" / "GF-T-01.json").is_file())

    def test_same_files_give_the_same_contract(self):
        a = cc.to_contract(self.man, self.pdir, self.bundle, self.root)
        b = cc.to_contract(self.man, self.pdir, self.bundle, self.root)
        self.assertEqual(a, b)


class AdapterQaRefuses(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cohort, self.pdir, self.bundle, self.man = _make_product(self.root)
        self.c = cc.to_contract(self.man, self.pdir, self.bundle, self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_changed_file_after_manifest_fails(self):
        (self.pdir / "demo_kit_guide.pdf").write_bytes(b"%PDF tampered")
        rep = cc.qa(self.c, self.root)
        self.assertFalse(rep["ok"])
        self.assertEqual(rep["checks"]["file_guide"]["status"], "FAIL")

    def test_missing_file_fails(self):
        (self.pdir / "README.txt").unlink()
        rep = cc.qa(self.c, self.root)
        self.assertFalse(rep["ok"])
        self.assertEqual(rep["checks"]["file_readme"]["status"], "FAIL")

    def test_thin_guide_fails(self):
        thin = dict(self.c, guide_words=1200)
        self.assertFalse(cc.qa(thin, self.root)["ok"])
        short = dict(self.c, guide_pages=3)
        self.assertFalse(cc.qa(short, self.root)["ok"])

    def test_missing_role_fails(self):
        c = json.loads(json.dumps(self.c))
        del c["files"]["workbook"]
        rep = cc.qa(c, self.root)
        self.assertFalse(rep["ok"])
        self.assertEqual(rep["checks"]["has_workbook"]["status"], "FAIL")

    def test_bundle_without_a_workbook_fails(self):
        with zipfile.ZipFile(self.bundle, "w") as z:
            z.writestr("demo_kit/demo_kit_guide.pdf", b"x")
            z.writestr("demo_kit/README.txt", b"x")
        c = cc.to_contract(self.man, self.pdir, self.bundle, self.root)  # re-hash the new zip
        self.assertEqual(c["qa"]["checks"]["bundle_contents"]["status"], "FAIL")

    def test_unopenable_workbook_fails(self):
        (self.pdir / "demo_kit_workbook.xlsx").write_bytes(b"not a workbook")
        c = cc.to_contract(self.man, self.pdir, self.bundle, self.root)
        self.assertEqual(c["qa"]["checks"]["workbook_opens"]["status"], "FAIL")
        self.assertFalse(c["qa"]["ok"])

    def test_non_positive_price_fails(self):
        self.assertFalse(cc.qa(dict(self.c, price_cents=0), self.root)["ok"])

    def test_verify_existing_detects_a_later_change(self):
        cc.write_for_product(self.man, self.pdir, self.bundle, self.root)
        path = self.cohort / "contracts" / "GF-T-01.json"
        self.assertTrue(cc.verify_existing(path, self.root)["ok"])
        (self.pdir / "README.txt").write_text("edited after the contract was written", encoding="utf-8")
        self.assertFalse(cc.verify_existing(path, self.root)["ok"])


class RealCohortWiring(unittest.TestCase):
    """Every cohort build.py must call the adapter and check it in --qa."""

    def test_each_cohort_build_script_is_wired(self):
        root = Path(__file__).resolve().parent.parent
        scripts = sorted(root.glob("cohort_GF_*/build.py"))
        self.assertGreaterEqual(len(scripts), 2)
        for s in scripts:
            text = s.read_text(encoding="utf-8")
            self.assertIn("cohort_contract.write_for_product", text, s.parent.name)
            self.assertIn("cohort_contract.verify_existing", text, s.parent.name)


if __name__ == "__main__":
    unittest.main()
