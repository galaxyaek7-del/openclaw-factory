"""scripts/apply_listing_repairs_20261029.py: re-running the repair is safe.

A fake Gumroad and fake write-scope module stand in for the real ones; no
product file, network call or live write is involved."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import apply_listing_repairs_20261029 as rep  # noqa: E402


class FakeGumroad:
    def __init__(self, products, files=None):
        self.products, self.files, self.writes = products, files or {}, []

    def list_products(self, token):
        return self.products

    def get_product(self, token, pid):
        return {"files": self.files.get(pid, [])}

    def update_product_file(self, token, pid, path, upload_scope_id=None):
        self.writes.append(("file", pid))

    def update_product_description_scoped(self, token, pid, text, scope_id=None):
        self.writes.append(("description", pid))


class FakeScope:
    def issue_scope(self, **kw):
        return type("S", (), {"scope_id": "s1"})()


class Repairs(unittest.TestCase):
    def setUp(self):
        self._bundles, self._build = rep.BUNDLES, rep.build_bundle
        rep.BUNDLES = {"kit": ("kit.zip", [])}
        rep.build_bundle = lambda slug: {"path": "x.zip", "bytes": 500, "sha256": "0" * 64, "members": [],
                                         "member_file_tests": {}, "ok": True}

    def tearDown(self):
        rep.BUNDLES, rep.build_bundle = self._bundles, self._build

    def products(self, desc):
        return [{"id": "P1", "short_url": "https://x/l/kit", "description": "<p>files</p>", "published": True},
                {"id": "P2", "short_url": "https://x/l/tool", "description": desc, "published": True}]

    def test_first_run_plans_attach_and_description(self):
        gp = FakeGumroad(self.products("<p>You get: a.xlsx and this guide.</p>"), {"P1": [{"size": 120}]})
        kinds = sorted(a["kind"] for a in rep.plan("t", gp))
        self.assertEqual(kinds, ["attach_bundle", "update_description"])

    def test_second_run_writes_nothing(self):
        # After a successful run: the attachment has the bundle's size and the
        # description no longer contains the old phrase.
        gp = FakeGumroad(self.products("<p>You get: a.xlsx and a PDF guide.</p>"), {"P1": [{"size": 500}]})
        actions = rep.plan("t", gp)
        self.assertEqual([a["kind"] for a in actions], ["attach_bundle"])
        self.assertTrue(actions[0]["already_applied"])
        done = rep.apply("t", gp, FakeScope(), actions)
        self.assertEqual([d["result"] for d in done], ["ALREADY_APPLIED"])
        self.assertEqual(gp.writes, [])

    def test_a_failed_bundle_is_never_uploaded(self):
        rep.build_bundle = lambda slug: {"path": "x.zip", "bytes": 500, "sha256": "0" * 64, "members": [],
                                         "member_file_tests": {"a.xlsx": "FAIL"}, "ok": False}
        gp = FakeGumroad(self.products("<p>nothing to fix</p>"), {"P1": [{"size": 120}]})
        done = rep.apply("t", gp, FakeScope(), rep.plan("t", gp))
        self.assertEqual(done[0]["result"], "SKIPPED")
        self.assertEqual(gp.writes, [])


if __name__ == "__main__":
    unittest.main()
