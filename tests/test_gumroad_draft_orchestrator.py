# -*- coding: utf-8 -*-
"""Cycle 115/116 -- tests for the guarded B12-001 Gumroad draft orchestrator.

Everything is local: no network. All network/page functions are injected mocks,
so the suite proves the orchestrator NEVER performs a real create on any
reachable path and fails closed on ambiguity. Cycle 116 adds the capability
contract + the narrow `create_draft_live()` safety matrix.
"""
import inspect
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

FACTORY_DIR = Path(__file__).resolve().parent.parent
MOD_PATH = FACTORY_DIR / "scripts" / "gumroad_draft_orchestrator.py"


def _load():
    spec = importlib.util.spec_from_file_location("gumroad_draft_orchestrator", MOD_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gumroad_draft_orchestrator"] = mod
    spec.loader.exec_module(mod)
    return mod


od = _load()


def _ok_post(url, data):
    return {"success": True, "product": {"id": "prod_1", "published": False}}


def _fresh(product=None):
    base = {"id": "prod_1", "name": od.TITLE, "price": od.PRICE_CENTS, "published": False}
    if product:
        base.update(product)
    return base


class _AllowAuth:
    def __call__(self, op):
        return None


class TestPackageValidation(unittest.TestCase):
    def test_real_workbook_is_ready(self):
        report = od.validate_package()
        self.assertTrue(report["ready"], [c for c in report["checks"] if c["status"] != "PASS"])
        names = {c["check"]: c["status"] for c in report["checks"]}
        self.assertEqual(names["workbook sha256"], "PASS")
        self.assertEqual(names["workbook size"], "PASS")
        self.assertEqual(names["price = $14.99"], "PASS")

    def test_missing_workbook_fails_closed(self):
        report = od.validate_package(workbook=Path("does/not/exist.xlsx"))
        self.assertFalse(report["ready"])
        self.assertEqual(
            [c["status"] for c in report["checks"] if c["check"] == "workbook exists"], ["FAIL"])

    def test_build_spec_is_deterministic(self):
        self.assertEqual(od.build_spec(), od.build_spec())


class TestCapabilityContract(unittest.TestCase):
    def test_state_is_capability_unknown_not_supported(self):
        cap = od.draft_creation_capability()
        self.assertEqual(cap["state"], od.CAP_CAPABILITY_UNKNOWN)
        self.assertTrue(cap["platform_documented"])
        self.assertFalse(cap["live_verified"])
        self.assertIn(cap["authorization"], ("AVAILABLE", "BLOCKED"))

    def test_authorization_blocked_when_flag_false(self):
        saved = os.environ.pop("FACTORY_LIVE_PUBLISH", None)
        try:
            cap = od.draft_creation_capability()
            self.assertEqual(cap["authorization"], "BLOCKED")
            self.assertIn("FACTORY_LIVE_PUBLISH is false", cap["blockers"])
        finally:
            if saved is not None:
                os.environ["FACTORY_LIVE_PUBLISH"] = saved

    def test_required_guarantees_named(self):
        cap = od.draft_creation_capability()
        joined = " ".join(cap["required_guarantees"])
        self.assertIn("published=false", joined)
        self.assertIn("read-back", joined)
        self.assertIn("PUT /v2/products/:id/disable", cap["documented_reversibility"])

    def test_safe_draft_creation_shim_still_false(self):
        supported, reason = od.safe_draft_creation_supported()
        self.assertFalse(supported)
        self.assertIn(od.CAP_CAPABILITY_UNKNOWN, reason)


class TestLegacyCreateDraftGuard(unittest.TestCase):
    def test_create_draft_never_calls_create_fn(self):
        create_fn = mock.Mock(side_effect=AssertionError("must never be called"))
        list_fn = mock.Mock(return_value=[])
        with self.assertRaises(od.DraftBlocked) as ctx:
            od.create_draft("tok", od.build_spec(), list_products_fn=list_fn, create_fn=create_fn)
        self.assertIn("no live-verified draft-creation path", str(ctx.exception))
        create_fn.assert_not_called()

    def test_create_draft_blocks_even_with_authorization(self):
        create_fn = mock.Mock(side_effect=AssertionError("must never be called"))
        with self.assertRaises(od.DraftBlocked):
            od.create_draft("tok", od.build_spec(), list_products_fn=lambda: [],
                            create_fn=create_fn, draft_authorized=True)
        create_fn.assert_not_called()

    def test_duplicate_scan_runs_before_any_create(self):
        order = []

        def list_fn():
            order.append("scan")
            return []

        create_fn = mock.Mock(side_effect=lambda *a, **k: order.append("create"))
        with self.assertRaises(od.DraftBlocked):
            od.create_draft("tok", od.build_spec(), list_products_fn=list_fn, create_fn=create_fn)
        self.assertEqual(order, ["scan"])


class TestDuplicateGuard(unittest.TestCase):
    def test_duplicate_scan_finds_same_title(self):
        catalog = [{"id": "abc", "name": "  freelancer RATE & raise calculator ",
                    "short_url": "https://gum.co/x", "deleted": False}]
        out = od.duplicate_scan(od.build_spec(), lambda: catalog)
        self.assertTrue(out["found"])

    def test_duplicate_scan_ignores_deleted(self):
        catalog = [{"id": "abc", "name": od.TITLE, "deleted": True}]
        self.assertFalse(od.duplicate_scan(od.build_spec(), lambda: catalog)["found"])

    def test_duplicate_scan_fails_closed_when_catalog_unreadable(self):
        with self.assertRaises(od.DraftBlocked) as ctx:
            od.duplicate_scan(od.build_spec(), lambda: (_ for _ in ()).throw(RuntimeError("429")))
        self.assertIn("catalog unreadable", str(ctx.exception))

    def test_create_draft_refuses_duplicate(self):
        catalog = [{"id": "abc", "name": od.TITLE, "short_url": "https://gum.co/x", "deleted": False}]
        with self.assertRaises(od.DraftBlocked) as ctx:
            od.create_draft("tok", od.build_spec(), list_products_fn=lambda: catalog)
        self.assertIn("already exists", str(ctx.exception))


class TestPriceGuard(unittest.TestCase):
    def test_price_mismatch_refused(self):
        spec = od.build_spec()
        spec["price_cents"] = 2900
        with self.assertRaises(od.DraftBlocked) as ctx:
            od.create_draft("tok", spec, list_products_fn=lambda: [])
        self.assertIn("price mismatch", str(ctx.exception))


class TestRealWriteGateFailsClosed(unittest.TestCase):
    def setUp(self):
        self._saved = os.environ.pop("FACTORY_LIVE_PUBLISH", None)

    def tearDown(self):
        if self._saved is not None:
            os.environ["FACTORY_LIVE_PUBLISH"] = self._saved

    def test_write_scope_has_no_create_operation(self):
        from channels import write_scope
        self.assertNotIn("create_product", write_scope.ALLOWED_OPERATIONS)

    def test_create_product_denied_before_network(self):
        from channels import gumroad_publisher as gp
        tmp = Path(tempfile.gettempdir()) / "c116_draft_probe.xlsx"
        tmp.write_bytes(b"probe-not-a-real-product")
        try:
            with mock.patch("requests.post") as post, mock.patch("requests.request") as req:
                with self.assertRaises(Exception) as ctx:
                    gp.create_product("fake-token", {
                        "name": "x", "price": 1499, "file_path": str(tmp),
                    }, upload_scope_id=None)
                self.assertIn("WriteNotAuthorized", type(ctx.exception).__name__)
                post.assert_not_called()
                req.assert_not_called()
        finally:
            tmp.unlink(missing_ok=True)


class TestCreatePayloadHasNoDraftControl(unittest.TestCase):
    """Pins the exact gap in the REAL wrapper (not the orchestrator)."""

    def test_create_product_payload_omits_published_field(self):
        from channels import gumroad_publisher as gp
        captured = {}

        class _Resp:
            def raise_for_status(self):
                pass

            def json(self):
                return {"success": True, "product": {"id": "p", "published": True}}

        def fake_post(url, data=None, timeout=None):
            captured["url"] = url
            captured["data"] = dict(data or {})
            return _Resp()

        tmp = Path(tempfile.gettempdir()) / "c116_payload_probe.xlsx"
        tmp.write_bytes(b"probe")
        try:
            with mock.patch.object(gp, "_require_write_authorization", lambda *a, **k: None), \
                 mock.patch.object(gp, "_check_attachment", lambda *a, **k: None), \
                 mock.patch.object(gp, "_find_duplicate_listing", lambda *a, **k: None), \
                 mock.patch.object(gp, "_upload_file", lambda *a, **k: "https://files.example/x"), \
                 mock.patch("requests.post", side_effect=fake_post):
                gp.create_product("tok", {
                    "title": od.TITLE, "price_cents": od.PRICE_CENTS,
                    "file_path": str(tmp), "description": "d"}, upload_scope_id="scope")
        finally:
            tmp.unlink(missing_ok=True)

        self.assertTrue(captured["url"].endswith("/products"))
        self.assertNotIn("published", captured["data"])
        self.assertNotIn("publish", captured["data"])
        self.assertEqual(captured["data"]["price"], od.PRICE_CENTS)


class TestDraftLiveSafetyMatrix(unittest.TestCase):
    """The 15-case Phase-4 safety matrix for `create_draft_live()`."""

    def _call(self, **over):
        kw = dict(
            token="tok",
            spec=over.pop("spec", od.build_spec()),
            list_products_fn=over.pop("list_products_fn", lambda: []),
            get_product_fn=over.pop("get_product_fn", lambda t, pid: _fresh()),
            post_fn=over.pop("post_fn", _ok_post),
            upload_fn=over.pop("upload_fn", lambda t, s: "https://files.example/x"),
            authorize_fn=over.pop("authorize_fn", _AllowAuth()),
            disable_fn=over.pop("disable_fn", None),
            draft_authorized=over.pop("draft_authorized", True),
        )
        kw.update(over)
        return od.create_draft_live(**kw)

    # 1 -- unpublished create succeeds and verifies
    def test_01_unpublished_create_succeeds(self):
        out = self._call()
        self.assertEqual(out["state"], od.CAP_CREATED_AND_UNPUBLISHED_STATE_VERIFIED)
        self.assertIs(out["product"]["published"], False)

    # 2 -- refused when capability state is unknown (unauthorized)
    def test_02_refused_when_unauthorized(self):
        authorize = mock.Mock(side_effect=RuntimeError("WriteNotAuthorized"))
        post = mock.Mock(side_effect=AssertionError("must not reach network"))
        with self.assertRaises(RuntimeError):
            self._call(authorize_fn=authorize, post_fn=post)
        post.assert_not_called()

    # 3 -- create response says published=true -> blocked + disable
    def test_03_response_published_true_is_blocked(self):
        disable = mock.Mock()
        post = lambda u, d: {"success": True, "product": {"id": "p1", "published": True}}
        with self.assertRaises(od.DraftBlocked) as ctx:
            self._call(post_fn=post, disable_fn=disable)
        self.assertIn("not a draft", str(ctx.exception))
        disable.assert_called_once_with("tok", "p1")

    # 4 -- create response omits published -> blocked + disable
    def test_04_response_missing_published_is_blocked(self):
        disable = mock.Mock()
        post = lambda u, d: {"success": True, "product": {"id": "p1"}}
        with self.assertRaises(od.DraftBlocked) as ctx:
            self._call(post_fn=post, disable_fn=disable)
        self.assertIn(od.CAP_CREATED_BUT_STATE_UNVERIFIED, str(ctx.exception))
        disable.assert_called_once_with("tok", "p1")

    # 5 -- read-back reports published=true -> blocked + disable
    def test_05_readback_published_true_is_blocked(self):
        disable = mock.Mock()
        with self.assertRaises(od.DraftBlocked) as ctx:
            self._call(get_product_fn=lambda t, pid: _fresh({"published": True}), disable_fn=disable)
        self.assertIn("read-back published != false", str(ctx.exception))
        disable.assert_called_once()

    # 6 -- read-back id/title/price mismatch -> blocked
    def test_06_readback_field_mismatch_is_blocked(self):
        disable = mock.Mock()
        with self.assertRaises(od.DraftBlocked) as ctx:
            self._call(get_product_fn=lambda t, pid: _fresh({"price": 999}), disable_fn=disable)
        self.assertIn("price mismatch", str(ctx.exception))
        disable.assert_called_once()

    # 7 -- network error -> UNCERTAIN, no blind retry (post called once)
    def test_07_network_error_is_uncertain_no_retry(self):
        post = mock.Mock(side_effect=TimeoutError("timed out"))
        with self.assertRaises(od.DraftBlocked) as ctx:
            self._call(post_fn=post)
        self.assertIn("UNCERTAIN", str(ctx.exception))
        self.assertEqual(post.call_count, 1)

    # 8 -- recovery finds the landed listing, never re-POSTs
    def test_08_recovery_detects_landed_listing(self):
        catalog = [{"id": "p1", "name": od.TITLE, "deleted": False}]
        out = od.recover_after_uncertain_create(od.build_spec(), list_products_fn=lambda: catalog,
                                                draft_authorized=True)
        self.assertTrue(out["found"])
        self.assertIn("do NOT re-POST", out["advice"])

    def test_08b_recovery_reports_absent_listing(self):
        out = od.recover_after_uncertain_create(od.build_spec(), list_products_fn=lambda: [],
                                                draft_authorized=True)
        self.assertFalse(out["found"])

    def test_08c_recovery_requires_authorization(self):
        with self.assertRaises(od.DraftBlocked):
            od.recover_after_uncertain_create(od.build_spec(), list_products_fn=lambda: [])

    # 9 -- expired auth -> blocked before network
    def test_09_expired_auth_blocked_before_network(self):
        post = mock.Mock(side_effect=AssertionError("must not reach network"))
        with self.assertRaises(RuntimeError):
            self._call(authorize_fn=mock.Mock(side_effect=RuntimeError("auth expired")), post_fn=post)
        post.assert_not_called()

    # 10 -- real write gate disabled -> blocked before network
    def test_10_real_write_gate_blocks_when_flag_off(self):
        saved = os.environ.pop("FACTORY_LIVE_PUBLISH", None)
        post = mock.Mock(side_effect=AssertionError("must not reach network"))
        try:
            with self.assertRaises(Exception) as ctx:
                od.create_draft_live("tok", od.build_spec(),
                                     list_products_fn=lambda: [],
                                     get_product_fn=lambda t, pid: _fresh(),
                                     post_fn=post,
                                     upload_fn=lambda t, s: "u",
                                     draft_authorized=True)  # default authorize_fn = real gate
            self.assertIn("WriteNotAuthorized", type(ctx.exception).__name__)
            post.assert_not_called()
        finally:
            if saved is not None:
                os.environ["FACTORY_LIVE_PUBLISH"] = saved

    # 11 -- unexpected schema/status -> blocked
    def test_11_unexpected_response_blocked(self):
        with self.assertRaises(od.DraftBlocked):
            self._call(post_fn=lambda u, d: {"success": False, "message": "boom"})
        with self.assertRaises(od.DraftBlocked):
            self._call(post_fn=lambda u, d: "not-a-dict")

    # 12 -- corrupt/incomplete package -> blocked before network
    def test_12_corrupt_package_blocked_before_network(self):
        post = mock.Mock(side_effect=AssertionError("must not reach network"))
        spec = od.build_spec()
        spec["file_path"] = str(Path(tempfile.gettempdir()) / "does-not-exist.xlsx")
        with self.assertRaises(od.DraftBlocked):
            self._call(spec=spec, post_fn=post)
        post.assert_not_called()

    # 13 -- the draft interface cannot publish
    def test_13_draft_interface_cannot_publish(self):
        disable = mock.Mock()
        self._call(disable_fn=disable)
        disable.assert_not_called()
        src = inspect.getsource(od.create_draft_live).lower()
        self.assertNotIn("enable_product", src)
        self.assertNotIn("enable_fn", src)
        self.assertNotIn("publish_fn", src)

    # 14 -- no network when preconditions fail (duplicate)
    def test_14_no_network_on_duplicate(self):
        post = mock.Mock(side_effect=AssertionError("must not reach network"))
        catalog = [{"id": "p1", "name": od.TITLE, "deleted": False}]
        with self.assertRaises(od.DraftBlocked):
            self._call(list_products_fn=lambda: catalog, post_fn=post)
        post.assert_not_called()

    # 15 -- explicit draft flags + price/title guardrails
    def test_15_explicit_flags_and_guardrails(self):
        captured = {}

        def post(url, data):
            captured["url"] = url
            captured["data"] = dict(data)
            return {"success": True, "product": {"id": "prod_1", "published": False}}

        self._call(post_fn=post)
        self.assertTrue(captured["url"].endswith("/products"))
        self.assertEqual(captured["data"]["published"], "false")
        self.assertEqual(captured["data"]["draft"], "true")
        self.assertEqual(captured["data"]["price"], od.PRICE_CENTS)

    def test_15b_requires_draft_authorized(self):
        post = mock.Mock(side_effect=AssertionError("must not reach network"))
        with self.assertRaises(od.DraftBlocked) as ctx:
            self._call(post_fn=post, draft_authorized=False)
        self.assertIn("draft_authorized", str(ctx.exception))
        post.assert_not_called()

    # 16 -- a two-file (B12-004) spec sends BOTH file urls as repeated fields
    def test_16_multifile_create_sends_repeated_file_urls(self):
        captured = {}
        urls = ["https://files.example/a", "https://files.example/b"]

        def post(url, data):
            captured["data"] = data
            return {"success": True, "product": {"id": "p1", "published": False}}

        def upload_many(tok, spec, paths):
            self.assertEqual(len(paths), 2)
            return list(urls)

        def fresh(tok, pid):
            return {"id": "p1", "name": "Meeting Cost & ROI Calculator",
                    "price": 1199, "published": False}

        out = self._call(spec=od.build_spec("B12-004"), post_fn=post,
                         get_product_fn=fresh, upload_fn=None, upload_many_fn=upload_many)
        self.assertEqual(out["state"], od.CAP_CREATED_AND_UNPUBLISHED_STATE_VERIFIED)
        sent = [v for k, v in captured["data"] if k == "files[][url]"]
        self.assertEqual(sent, urls)

    # 17 -- multiple declared files with no upload_many_fn: refuse a partial create
    def test_17_multifile_without_upload_many_refuses_partial(self):
        post = mock.Mock(side_effect=AssertionError("must not reach network"))
        with self.assertRaises(od.DraftBlocked) as ctx:
            self._call(spec=od.build_spec("B12-004"), post_fn=post, upload_fn=None)
        self.assertIn("no file_url", str(ctx.exception))
        post.assert_not_called()


class TestPreflightReport(unittest.TestCase):
    def test_preflight_reports_ready_and_blocked(self):
        rep = od.preflight()
        self.assertTrue(rep["package_ready"])
        self.assertFalse(rep["safe_draft_creation_supported"])
        self.assertEqual(rep["price_cents"], 1499)
        self.assertEqual(rep["capability"]["state"], od.CAP_CAPABILITY_UNKNOWN)

    def test_preflight_with_reader_includes_scan(self):
        rep = od.preflight(list_products_fn=lambda: [])
        self.assertEqual(rep["duplicate_scan"], {"found": False, "match": None})


if __name__ == "__main__":
    unittest.main()
