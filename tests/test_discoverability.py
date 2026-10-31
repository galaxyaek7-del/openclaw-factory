"""scripts/apply_discoverability_20261031.py: categories only from ids this account
already uses, personal tools stay in Other, held/broken listings untouched,
tags only copied from the product's own manifest. Fakes only, no network."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import apply_discoverability_20261031 as dsc  # noqa: E402

TAX = {"Accounting": 162, "Real Estate": 171, "Resources": 174, "Security & Compliance": 351}


def live(slug, name, category="other", tags=(), pid=None, published=True):
    return {"id": pid or slug.upper(), "short_url": f"https://g/l/{slug}", "name": name, "published": published,
            "category": category, "category_label": "Other" if category == "other" else "Accounting",
            "taxonomy_id": 266 if category == "other" else 162, "tags": list(tags)}


class Discoverability(unittest.TestCase):
    def test_categories(self):
        self.assertEqual(dsc.choose_category("13-Week Cash Flow Forecast", [], TAX), ("Accounting", 162))
        self.assertEqual(dsc.choose_category("PCI SAQ Readiness Kit", [], TAX), ("Security & Compliance", 351))
        # a non-software compliance kit is not filed under software security
        self.assertEqual(dsc.choose_category("Cottage Food Compliance Kit", [], TAX), ("Resources", 174))
        # personal finance stays in Other rather than business Accounting
        self.assertEqual(dsc.choose_category("Wedding Budget & Vendor Payment Planner", [], TAX), (None, None))
        # a category this account has never used is never invented
        self.assertEqual(dsc.choose_category("Gulf ATS CV System", [], TAX), (None, None))

    def test_observed_taxonomies_ignore_other(self):
        got = dsc.observed_taxonomies([live("a", "A"), live("b", "B", category="business-and-money/accounting")])
        self.assertEqual(got, {"Accounting": 162})

    def test_plan_skips_held_and_copies_manifest_tags(self):
        root = Path(tempfile.mkdtemp())
        try:
            (root / "data").mkdir()
            (root / "data" / "hold_products.json").write_text(json.dumps({"products": {"held": {"product_id": "H"}}}),
                                                              encoding="utf-8")
            (root / "m.json").write_text(json.dumps({"tags": ["cash flow", "excel template"]}), encoding="utf-8")
            reg = {"products": [{"external_ids": {"gumroad": "CASH"}, "manifest": "m.json"}]}
            items = [live("cash", "Cash Flow Forecast", pid="CASH"), live("held", "Held Budget Kit", pid="H"),
                     live("acc", "Ledger", category="business-and-money/accounting", tags=["x"])]
            doc = dsc.plan(items, reg, root)
            by = {a["slug"]: a for a in doc["actions"]}
            self.assertEqual(by["cash"]["updates"], {"tags": ["cash flow", "excel template"], "taxonomy_id": 162})
            self.assertEqual(by["held"]["skipped"], "on hold")
            self.assertNotIn("updates", by["held"])
            self.assertNotIn("acc", by)  # tagged and categorised already: nothing to do
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_apply_writes_only_planned_updates(self):
        calls = []

        class GP:
            def update_product(self, token, pid, updates):
                calls.append((pid, updates))
        out = dsc.apply("t", GP(), [{"product_id": "A", "updates": {"taxonomy_id": 162}},
                                    {"product_id": "B", "skipped": "on hold"}, {"product_id": "C", "notes": ["stays"]}])
        self.assertEqual(calls, [("A", {"taxonomy_id": 162})])
        self.assertEqual([o["result"] for o in out], ["PASS", "SKIPPED", "NOTHING_TO_WRITE"])


if __name__ == "__main__":
    unittest.main()
