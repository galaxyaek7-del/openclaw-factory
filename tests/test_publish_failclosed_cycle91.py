"""Cycle 91 security recovery: every prohibited live Gumroad operation is
blocked at the real boundary (channels/gumroad_publisher.py, channels/write_gate.py,
channels/write_scope.py, channels/publish_protection.py).

Behaviour, not source text: each test calls the real function and asserts that
no network request was made (requests and _request_with_retry are patched to
fail the test if reached). Scopes and protection state live in temp dirs.
"""
import hashlib
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from channels import gumroad_publisher as gp  # noqa: E402
from channels import publish_protection as pp  # noqa: E402
from channels import write_scope  # noqa: E402
from channels.write_gate import WriteNotAuthorized  # noqa: E402


def _no_network(*a, **k):
    raise AssertionError("a network call was attempted")


class _Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.file = self.tmp / "deliverable.xlsx"
        self.file.write_bytes(b"PK\x03\x04 real workbook bytes")
        for target in ("requests.request", "requests.post", "requests.put", "requests.get"):
            p = patch(f"channels.gumroad_publisher.{target}", side_effect=_no_network)
            p.start(); self.addCleanup(p.stop)
        p = patch.object(gp, "_request_with_retry", side_effect=_no_network)
        p.start(); self.addCleanup(p.stop)
        p = patch.dict(os.environ, {"FACTORY_WRITE_SCOPE_DIR": str(self.tmp / "scopes")})
        p.start(); self.addCleanup(p.stop)

    def spec(self, **kw):
        s = {"title": "Freelancer Rate & Raise Calculator", "price_cents": 1499, "file_path": str(self.file)}
        s.update(kw)
        return s


class TestLiveSwitchOff(_Base):
    """FACTORY_LIVE_PUBLISH unset: every create/update/enable/upload is denied."""

    def setUp(self):
        super().setUp()
        p = patch.dict(os.environ, {"FACTORY_LIVE_PUBLISH": ""})
        p.start(); self.addCleanup(p.stop)

    def test_create_update_enable_and_file_update_are_all_denied(self):
        with self.assertRaises(WriteNotAuthorized):
            gp.create_product("tok", self.spec())
        with self.assertRaises(WriteNotAuthorized):
            gp.update_product("tok", "pid", {"price": 1})
        with self.assertRaises(WriteNotAuthorized):
            gp.enable_product("tok", "pid")
        with self.assertRaises(WriteNotAuthorized):
            gp.update_product_file("tok", "pid", str(self.file))

    def test_upload_without_scope_is_denied(self):
        with self.assertRaises(WriteNotAuthorized):
            gp._upload_file("tok", str(self.file), product_id=gp.NEW_PRODUCT)


class TestCreateProductPreconditions(_Base):
    """Write authorization granted (the gate is tested above); everything the
    create still requires is checked before any network call."""

    def setUp(self):
        super().setUp()
        p = patch.object(gp, "_require_write_authorization", return_value=None)
        p.start(); self.addCleanup(p.stop)

    def test_missing_attachment(self):
        with self.assertRaises(gp.ConfigError):
            gp.create_product("tok", self.spec(file_path=None))
        with self.assertRaises(gp.ConfigError):
            gp.create_product("tok", self.spec(file_path=str(self.tmp / "nope.xlsx")))

    def test_unreadable_and_empty_attachment(self):
        empty = self.tmp / "empty.xlsx"; empty.write_bytes(b"")
        with self.assertRaises(gp.ConfigError):
            gp.create_product("tok", self.spec(file_path=str(empty)))
        with patch.object(Path, "read_bytes", side_effect=OSError("permission denied")):
            with self.assertRaises(gp.ConfigError) as cm:
                gp.create_product("tok", self.spec())
        self.assertIn("unreadable", str(cm.exception))

    def test_missing_or_invalid_price(self):
        for bad in (None, 0, -5, "abc"):
            with self.assertRaises(gp.ConfigError):
                gp.create_product("tok", self.spec(price_cents=bad))

    def test_wrong_file_identity(self):
        with self.assertRaises(gp.ConfigError) as cm:
            gp.create_product("tok", self.spec(expected_sha256="0" * 64))
        self.assertIn("identity mismatch", str(cm.exception))

    def test_duplicate_title_is_refused_before_upload(self):
        live = [{"name": "freelancer rate &  raise calculator", "short_url": "https://x/l/abc", "deleted": False}]
        with patch.object(gp, "list_products", return_value=live), \
             patch.object(gp, "_upload_file", side_effect=_no_network) as up:
            with self.assertRaises(gp.DuplicateListing):
                gp.create_product("tok", self.spec(expected_sha256=hashlib.sha256(self.file.read_bytes()).hexdigest()))
        self.assertFalse(up.called)

    def test_deleted_listing_is_not_a_duplicate_but_unreadable_catalog_blocks(self):
        with patch.object(gp, "list_products", return_value=[{"name": "Freelancer Rate & Raise Calculator", "deleted": True}]):
            self.assertIsNone(gp._find_duplicate_listing("tok", "Freelancer Rate & Raise Calculator"))
        with patch.object(gp, "list_products", side_effect=RuntimeError("HTTP 500")):
            with self.assertRaises(gp.DuplicateListing):
                gp._find_duplicate_listing("tok", "anything")

    def test_create_without_upload_scope_is_denied_after_all_checks(self):
        with patch.object(gp, "list_products", return_value=[]):
            with self.assertRaises(WriteNotAuthorized):
                gp.create_product("tok", self.spec())


class TestUploadScopes(_Base):
    def test_invalid_scope_id_is_denied(self):
        with self.assertRaises(WriteNotAuthorized):
            gp._upload_file("tok", str(self.file), scope_id="not-a-real-scope", product_id=gp.NEW_PRODUCT)

    def test_scope_for_another_file_or_product_is_denied(self):
        other = self.tmp / "other.xlsx"; other.write_bytes(b"other")
        sid = write_scope.issue_scope(product_id=gp.NEW_PRODUCT, slug="t", payload={"file_path": str(other)},
                                      operation="upload_file", note="test").scope_id
        with self.assertRaises(WriteNotAuthorized):
            gp._upload_file("tok", str(self.file), scope_id=sid, product_id=gp.NEW_PRODUCT)
        sid2 = write_scope.issue_scope(product_id="PRODUCT-A", slug="t", payload={"file_path": str(self.file)},
                                       operation="upload_file", note="test").scope_id
        with self.assertRaises(WriteNotAuthorized):
            gp._upload_file("tok", str(self.file), scope_id=sid2, product_id="PRODUCT-B")

    def test_scope_is_single_use(self):
        sid = write_scope.issue_scope(product_id=gp.NEW_PRODUCT, slug="t", payload={"file_path": str(self.file)},
                                      operation="upload_file", note="test").scope_id
        with self.assertRaises(AssertionError):     # first use passes the gate, then hits the network stub
            gp._upload_file("tok", str(self.file), scope_id=sid, product_id=gp.NEW_PRODUCT)
        with self.assertRaises(WriteNotAuthorized):  # second use: already consumed
            gp._upload_file("tok", str(self.file), scope_id=sid, product_id=gp.NEW_PRODUCT)

    def test_malformed_scope_file_is_refused(self):
        sid = write_scope.issue_scope(product_id=gp.NEW_PRODUCT, slug="t", payload={"file_path": str(self.file)},
                                      operation="upload_file", note="test").scope_id
        store = write_scope._store_path(sid)
        store.write_text("{not json", encoding="utf-8")          # corrupted on disk
        with self.assertRaises(WriteNotAuthorized) as cm:
            gp._upload_file("tok", str(self.file), scope_id=sid, product_id=gp.NEW_PRODUCT)
        self.assertIn("unreadable", str(cm.exception))

    def test_approval_for_another_operation_cannot_authorize_an_upload(self):
        """A general approval (here: a description edit) must not authorize an
        unrelated action such as a file upload for a new product."""
        sid = write_scope.issue_scope(product_id=gp.NEW_PRODUCT, slug="t", payload={"description": "x"},
                                      operation="update_description", note="test").scope_id
        with self.assertRaises(WriteNotAuthorized):
            gp._upload_file("tok", str(self.file), scope_id=sid, product_id=gp.NEW_PRODUCT)


class TestDailyLimit(unittest.TestCase):
    def test_gumroad_daily_cap_blocks(self):
        """Real counters: record the cap's worth of successful publishes across
        one day (one per hour, so the hourly cap and spacing are not the
        reason), then the next attempt that day is refused for the daily cap."""
        from datetime import datetime, timezone
        tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        state = str(tmp / "protection.json")
        cap = pp.PLATFORM_PROFILES["gumroad"]["max_per_day"]
        day = datetime(2026, 10, 17, tzinfo=timezone.utc)
        for h in range(cap):
            pp.note_publish_outcome("gumroad", True, state_path=state, now=day.replace(hour=h % 24))
        d = pp.check_publish_allowed("gumroad", state_path=state, now=day.replace(hour=23))
        self.assertFalse(d["allowed"], d)
        self.assertIn("daily publish cap", d["reason"])

if __name__ == "__main__":
    unittest.main()
