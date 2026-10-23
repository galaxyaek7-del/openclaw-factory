# -*- coding: utf-8 -*-
"""Tests for scripts/verify_gumroad_listing.py (Cycle 104).

Fully offline and mocked: no live Gumroad call, no token needed, no purchase.
The verifier's whole value is that it reports what the platform *actually*
returns, so these tests pin the decision logic around each kind of real answer
-- byte-identical attachment, wrong-size attachment, extra attachment, an
unauthorized live listing, and an API failure -- and guard the one invariant
that would silently make the tool lie: every `deliverables` path in PRODUCTS
must exist on disk, and every expected-absent product must carry no product id.

    python -m unittest tests.test_verify_gumroad_listing -v
"""

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

sys.path.insert(0, str(_ROOT / "scripts"))
import verify_gumroad_listing as vgl  # noqa: E402
import sys as _gf_sys  # noqa: E402
_gf_sys.path.insert(0, str(Path(__file__).resolve().parent))
from paid_artifacts import paid_files_absent, require_paid_files  # noqa: E402

_REAL_DELIVERABLE = "books/batch12/B12-001_freelancer_rate_raise_calculator.xlsx"
# The matching tests need a local file of known size, not the paid
# product itself: on CI (no paid files) a temp file stands in for it.
if paid_files_absent(_ROOT / _REAL_DELIVERABLE):
    import tempfile as _gf_tmp
    _fd, _stand_in = _gf_tmp.mkstemp(suffix=".xlsx")
    with open(_fd, "wb") as _f:
        _f.write(b"stand-in for a paid deliverable" * 300)
    _DELIVERABLE = _stand_in
else:
    _DELIVERABLE = _REAL_DELIVERABLE


def _spec(**over):
    base = {
        "title": "Test Product",
        "product_id": "PROD==",
        "url": "https://example.invalid/l/x",
        "expect_published": True,
        "price_cents": 1000,
        "deliverables": [_DELIVERABLE],
    }
    base.update(over)
    return base


def _detail(spec, files, published=True, price_moves=0, name=None):
    return {
        "id": spec["product_id"],
        "name": name if name is not None else spec["title"],
        "short_url": spec["url"],
        "published": published,
        "deleted": False,
        "price": spec["price_cents"] + price_moves,
        "currency": "usd",
        "sales_count": 0,
        "files": files,
    }


class TestAttachmentMatching(unittest.TestCase):
    def setUp(self):
        self._orig_http = vgl._http_get
        vgl._http_get = lambda url, timeout=25: (200, "i want this")

    def tearDown(self):
        vgl._http_get = self._orig_http

    def _run(self, spec, product):
        return vgl.verify_one("X", spec, "token", lambda tok, pid: product)

    def test_byte_identical_attachment_verifies(self):
        local = _ROOT / _spec()["deliverables"][0]
        size = local.stat().st_size
        rec = self._run(_spec(), _detail(_spec(), [{"name": None, "size": size,
                                                    "filetype": "xlsx", "url": "u"}]))
        self.assertEqual(rec["state"], "PUBLISHED_VERIFIED_WITH_REVIEW_ITEMS")
        self.assertFalse(any(c["status"] == "FAIL" for c in rec["checks"]))
        # names are null on this API; that is surfaced, never guessed
        self.assertTrue(any("names not exposed" in i["item"] for i in rec["review_items"]))

    def test_wrong_size_attachment_is_a_mismatch(self):
        rec = self._run(_spec(), _detail(_spec(), [{"name": None, "size": 1,
                                                    "filetype": "xlsx", "url": "u"}]))
        self.assertEqual(rec["state"], "PUBLICATION_MISMATCH")
        self.assertEqual(len(rec["deliverable_missing"]), 1)

    def test_extra_attachment_flags_review_only_when_allowed(self):
        local = _ROOT / _spec()["deliverables"][0]
        files = [{"name": None, "size": local.stat().st_size, "filetype": "xlsx", "url": "u"},
                 {"name": "second.pdf", "size": 5, "filetype": "pdf", "url": "u"}]
        strict = self._run(_spec(), _detail(_spec(), files))
        self.assertEqual(strict["state"], "PUBLICATION_MISMATCH")
        allowed = self._run(_spec(extras_allowed=True), _detail(_spec(), files))
        self.assertEqual(allowed["state"], "PUBLISHED_VERIFIED_WITH_REVIEW_ITEMS")

    def test_unpublished_is_a_mismatch_when_published_expected(self):
        rec = self._run(_spec(), _detail(_spec(), [], published=False))
        self.assertEqual(rec["state"], "PUBLICATION_MISMATCH")

    def test_price_drift_is_a_mismatch(self):
        local = _ROOT / _spec()["deliverables"][0]
        rec = self._run(_spec(), _detail(_spec(), [{"name": None, "size": local.stat().st_size,
                                                    "filetype": "xlsx", "url": "u"}],
                                         price_moves=1))
        self.assertEqual(rec["state"], "PUBLICATION_MISMATCH")

    def test_api_failure_blocks_and_never_claims_anything(self):
        def boom(tok, pid):
            raise RuntimeError("HTTP 401 unauthorized")
        rec = vgl.verify_one("X", _spec(), "token", boom)
        self.assertEqual(rec["state"], "BLOCKED_UNREACHABLE")
        self.assertNotIn("published", rec["observed"])


class TestExpectedAbsence(unittest.TestCase):
    def setUp(self):
        from channels import gumroad_publisher as gp
        self._orig = gp.list_products
        self.addCleanup(lambda: setattr(gp, "list_products", self._orig))

    def _with_catalog(self, catalog):
        from channels import gumroad_publisher as gp
        gp.list_products = lambda tok: catalog

    def test_absent_title_is_the_expected_pass(self):
        self._with_catalog([{"name": "Something Else", "deleted": False}])
        rec = vgl.verify_one("B12-002", vgl.PRODUCTS["B12-002"], "t", lambda *a: None)
        self.assertEqual(rec["state"], "NOT_PUBLISHED_AS_EXPECTED")

    def test_live_listing_where_none_was_expected_is_flagged(self):
        self._with_catalog([{"id": "Z==", "name": vgl.PRODUCTS["B12-002"]["title"],
                             "short_url": "https://x/l/y", "published": True,
                             "deleted": False}])
        rec = vgl.verify_one("B12-002", vgl.PRODUCTS["B12-002"], "t", lambda *a: None)
        self.assertEqual(rec["state"], "UNEXPECTED_LIVE_LISTING")


class TestRegistryInvariants(unittest.TestCase):
    def test_every_deliverable_path_exists(self):
        require_paid_files(*[_ROOT / rel for spec in vgl.PRODUCTS.values() for rel in spec["deliverables"]])
        for key, spec in vgl.PRODUCTS.items():
            for rel in spec["deliverables"]:
                self.assertTrue((_ROOT / rel).exists(),
                                "%s declares a missing artifact: %s" % (key, rel))

    def test_expected_absent_products_have_no_product_id(self):
        for key, spec in vgl.PRODUCTS.items():
            if spec["expect_published"]:
                self.assertTrue(spec.get("product_id"), "%s needs a product id" % key)
            else:
                self.assertIsNone(spec.get("product_id"),
                                  "%s must not carry an id if it should not be live" % key)

    def test_verifier_never_issues_a_write_method(self):
        src = (Path(__file__).resolve().parent.parent
               / "scripts" / "verify_gumroad_listing.py").read_text(encoding="utf-8")
        for verb in ('"POST"', '"PUT"', '"PATCH"', '"DELETE"', "'POST'", "'PUT'"):
            self.assertNotIn(verb, src)
        self.assertNotIn("create_product", src)
        self.assertNotIn("update_product", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
