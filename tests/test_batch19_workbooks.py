# -*- coding: utf-8 -*-
"""Batch 19 must stay honest: every workbook is re-evaluated, not trusted.

The first build of batch 19 wrote correct numbers into the guide and dead
formulas into the workbook (#VALUE! on the first cell, circular references on
the next two). The manifests said qa.ok=true because the QA only checked the
Python model against itself. This test evaluates the saved .xlsx with
lib/xlsx_eval.py -- a different engine -- and requires agreement with the
manifest's own model, so a decorative formula can never ship again.
"""
import glob
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from lib import xlsx_eval  # noqa: E402

MANIFESTS = sorted(glob.glob(os.path.join(ROOT, "books", "batch19", "*", "manifest.json")))
OUTPUT_ROW = 2  # Model!B2 is the first output


def model_values(manifest):
    """Recompute the workbook's outputs from the expression text it ships."""
    import build_batch19 as b19
    spec = next(s for s in b19.SPECS if s["id"] == manifest["id"])
    return b19.compute_values(spec)


@unittest.skipUnless(MANIFESTS, "books/batch19 is a paid payload and is never committed; run scripts/build_batch19.py to produce it locally")
class Batch19WorkbooksAgreeWithTheirModels(unittest.TestCase):
    def test_the_batch_is_present(self):
        self.assertEqual(len(MANIFESTS), 10, "batch 19 should ship ten products")

    def test_every_output_evaluates_and_matches(self):
        for path in MANIFESTS:
            m = json.load(open(path, encoding="utf-8"))
            wb_path = os.path.join(ROOT, m["files"]["workbook"]["path"])
            self.assertTrue(os.path.exists(wb_path), wb_path)
            ev = xlsx_eval.Workbook(wb_path)
            values = model_values(m)
            for idx, (key, _label, _f, _fn, _kind) in enumerate(
                    [(o[0], o[1], o[2], o[3], o[4]) for o in
                     next(s for s in __import__("build_batch19").SPECS if s["id"] == m["id"])["outputs"]],
                    start=OUTPUT_ROW):
                got = ev.evaluate("Model!B%d" % idx)
                self.assertNotIsInstance(got, str, "%s %s returned %r" % (m["id"], key, got))
                want = values[key]
                self.assertLess(abs(got - want) / max(abs(want), 1e-9), 0.005,
                                "%s %s: workbook %.4f vs model %.4f" % (m["id"], key, got, want))

    def test_manifests_record_a_real_recalculation(self):
        for path in MANIFESTS:
            m = json.load(open(path, encoding="utf-8"))
            recalc = m["qa"]["recalc"]
            self.assertGreater(recalc["checked"], 0, m["id"])
            self.assertEqual(recalc["failed"], [], m["id"])
            self.assertTrue(m["qa"]["ok"], m["id"])
            self.assertTrue(m["qa"]["listing"]["description_html"], m["id"])

    def test_prices_are_in_the_high_value_band(self):
        for path in MANIFESTS:
            m = json.load(open(path, encoding="utf-8"))
            self.assertGreaterEqual(m["price_cents"], 4900, m["id"])
            self.assertLessEqual(m["price_cents"], 9900, m["id"])

    def test_every_file_is_listed_with_a_digest(self):
        import hashlib
        for path in MANIFESTS:
            m = json.load(open(path, encoding="utf-8"))
            for name, f in m["files"].items():
                full = os.path.join(ROOT, f["path"])
                self.assertTrue(os.path.exists(full), "%s %s" % (m["id"], name))
                h = hashlib.sha256(open(full, "rb").read()).hexdigest()
                self.assertEqual(h, f["sha256"], "%s %s digest drifted" % (m["id"], name))


if __name__ == "__main__":
    unittest.main()
