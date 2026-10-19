# -*- coding: utf-8 -*-
"""Cycle 98 regression: the Batch-12 page/QA helper must never destroy
authoritative product data or hand-authored pages.

Root cause this guards: `main()` used to rebuild the whole registry from a
hardcoded template (dropping price_usd/price_basis/gate_*/hashes added by
later cycles) and unconditionally overwrite every sales page. A routine QA run
therefore wiped the B12-001 authorized price basis and the B12-002/B12-004
authored pages.
"""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MOD_PATH = ROOT / "scripts" / "build_batch12_pages_qa.py"


def _load():
    spec = importlib.util.spec_from_file_location("bb12qa", MOD_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestBatch12RegistryMerge(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="b12qa_"))
        self.mod = _load()
        self.mod.DATA = self.tmp
        self.mod.SITE = self.tmp / "site"
        self.mod.SITE.mkdir()
        self.authoritative = {
            "id": "B12-002",
            "title": "Client Project Handoff Pack",
            "price": 11.99,
            "price_usd": 11.99,
            "price_basis": "FOUNDER_APPROVED_BELOW_COMPARABLE_2026-10-18",
            "pricing_date": "2026-10-18",
            "gate_verdict": "APPROVED",
            "deliverable_hashes": {"x": {"sha256": "abc", "size": 1}},
            "state": "STALE",
            "issues": ["stale"],
        }
        (self.tmp / "product_batch_12.json").write_text(json.dumps(
            {"generated_at": "old", "batch": "B12", "products": [self.authoritative]}),
            encoding="utf-8")

    def _results(self):
        return [{"id": p["id"], "state": "READY_FOR_REVIEW", "issues": []}
                for p in self.mod.PRODUCTS]

    def test_merge_preserves_authoritative_fields(self):
        reg = self.mod.merge_registry(self._results(), "now")
        b2 = next(p for p in reg["products"] if p["id"] == "B12-002")
        for k, v in self.authoritative.items():
            if k in ("state", "issues"):
                continue
            self.assertEqual(b2[k], v, k)
        # only the QA verdict fields are updated
        self.assertEqual(b2["state"], "READY_FOR_REVIEW")
        self.assertEqual(b2["issues"], [])
        # template records are added for ids not in the old registry
        self.assertEqual(len(reg["products"]), len(self.mod.PRODUCTS))

    def test_hardcoded_template_prices_match_authorized_prices(self):
        prices = {p["id"]: p["price"] for p in self.mod.PRODUCTS}
        self.assertEqual(prices["B12-001"], 14.99)
        self.assertEqual(prices["B12-002"], 11.99)
        self.assertEqual(prices["B12-004"], 11.99)

    def _run_main(self, argv):
        called = {"pages": 0}
        self.mod.build_pages = lambda: called.__setitem__("pages", called["pages"] + 1)
        self.mod.qa = lambda: self._results()
        old = sys.argv
        try:
            sys.argv = ["build_batch12_pages_qa.py"] + argv
            self.mod.main()
        finally:
            sys.argv = old
        return called["pages"]

    def test_main_never_rebuilds_pages_by_default(self):
        self.assertEqual(self._run_main([]), 0)

    def test_main_rebuilds_pages_only_with_the_explicit_flag(self):
        self.assertEqual(self._run_main(["--rebuild-pages"]), 1)


if __name__ == "__main__":
    unittest.main()
