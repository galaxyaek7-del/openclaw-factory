"""Tests for channels/gumroad_publisher.py (ADR-030, Gumroad-first arm
completion). No live Gumroad API call is ever made — requests.request is
patched in every test.

    python -m unittest tests.test_gumroad_publisher -v
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from channels import gumroad_publisher as gp


def _fake_response(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {"success": True}
    if status_code >= 400:
        resp.raise_for_status.side_effect = gp.requests.HTTPError(f"HTTP {status_code}")
    else:
        resp.raise_for_status.side_effect = None
    return resp


class TestRetryOnTransientFailure(unittest.TestCase):
    def test_get_sales_retries_after_one_5xx_then_succeeds(self):
        responses = [
            _fake_response(status_code=503),
            _fake_response(status_code=200, json_data={"success": True, "sales": [{"id": "s1"}]}),
        ]
        with patch.object(gp.requests, "request", side_effect=responses) as mock_req, \
             patch.object(gp.time, "sleep") as mock_sleep:
            sales = gp.get_sales("fake-token")
        self.assertEqual(sales, [{"id": "s1"}])
        self.assertEqual(mock_req.call_count, 2)
        mock_sleep.assert_called_once()

    def test_get_sales_gives_up_after_max_attempts(self):
        responses = [_fake_response(status_code=503)] * gp._RETRY_ATTEMPTS
        with patch.object(gp.requests, "request", side_effect=responses), \
             patch.object(gp.time, "sleep"):
            with self.assertRaises(RuntimeError):
                gp.get_sales("fake-token")

    def test_4xx_is_never_retried(self):
        responses = [_fake_response(status_code=401)]
        with patch.object(gp.requests, "request", side_effect=responses) as mock_req, \
             patch.object(gp.time, "sleep") as mock_sleep:
            with self.assertRaises(RuntimeError):
                gp.get_sales("fake-token")
        self.assertEqual(mock_req.call_count, 1)
        mock_sleep.assert_not_called()

    def test_create_product_is_never_retried_even_on_5xx(self):
        """create_product is a POST — never idempotent-safe to retry. A 5xx
        on the final product create must surface immediately as a single
        failed attempt, not be retried (a lost-response retry could otherwise
        double-create a paid listing on Gumroad's side). The presign flow that
        precedes it (presign -> S3 PUT -> complete) is mocked out; only the
        final create POST is exercised."""
        import tempfile, os
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.write(b"%PDF-1.4 fake")
        tmp.close()

        presign = _fake_response(status_code=200, json_data={
            "success": True,
            "upload_id": "u1",
            "key": "k1",
            "parts": [{"part_number": 1, "presigned_url": "https://s3/part1"}],
        })
        put_resp = _fake_response(status_code=200)
        put_resp.headers = {"ETag": '"etag-1"'}
        complete_ok = _fake_response(status_code=200, json_data={
            "success": True,
            "file_url": "https://s3/final.pdf",
        })

        try:
            with patch.object(gp.requests, "request", side_effect=[presign, put_resp]) as mock_req, \
                 patch.object(gp.time, "sleep"), \
                 patch.object(gp.requests, "post",
                              side_effect=[complete_ok, _fake_response(status_code=503)]) as mock_post:
                with self.assertRaises(RuntimeError):
                    gp.create_product("fake-token", {
                        "title": "Test",
                        "price_cents": 999,
                        "file_path": tmp.name,
                    })
            # complete (1) + the single, un-retried create POST (1) = 2.
            self.assertEqual(mock_post.call_count, 2)
            self.assertEqual(mock_req.call_count, 2)
        finally:
            os.unlink(tmp.name)


class TestTokenNeverLeaksInErrors(unittest.TestCase):
    def test_safe_err_redacts_token_from_exception_text(self):
        import os
        with patch.dict(os.environ, {"GUMROAD_ACCESS_TOKEN": "secret123"}):
            exc = Exception("request to https://api.gumroad.com/v2/sales?access_token=secret123 failed")
            text = gp._safe_err(exc)
        self.assertNotIn("secret123", text)
        self.assertIn("REDACTED", text)


class TestEnableProduct(unittest.TestCase):
    def test_enable_hits_the_real_enable_endpoint(self):
        ok = _fake_response(status_code=200, json_data={
            "success": True,
            "product": {"id": "p1", "published": True, "url": "https://aekraft.gumroad.com/l/x",
                        "formatted_price": "$155"},
        })
        with patch.object(gp.requests, "request", return_value=ok) as mock_req, \
             patch.object(gp.time, "sleep"):
            product = gp.enable_product("fake-token", "p1")
        self.assertTrue(product["published"])
        self.assertEqual(product["url"], "https://aekraft.gumroad.com/l/x")
        # Must hit /products/{id}/enable -- the real publish endpoint, not a
        # 'publish' field on the generic PUT.
        args, kwargs = mock_req.call_args
        self.assertTrue(args[1].endswith("/products/p1/enable"))
        self.assertEqual(kwargs["data"], {"access_token": "fake-token"})

    def test_enable_surfaces_payment_method_blocker_honestly(self):
        blocked = _fake_response(status_code=200, json_data={
            "success": False,
            "message": "You must connect at least one payment method before you can publish this product for sale.",
        })
        with patch.object(gp.requests, "request", return_value=blocked):
            with self.assertRaisesRegex(RuntimeError, "payment method"):
                gp.enable_product("fake-token", "p1")


class TestGetProduct(unittest.TestCase):
    def test_get_product_returns_real_state(self):
        ok = _fake_response(status_code=200, json_data={
            "success": True,
            "product": {"id": "p1", "published": False, "price": 15500, "short_url": "https://aekraft.gumroad.com/l/iaiyt"},
        })
        with patch.object(gp.requests, "request", return_value=ok):
            product = gp.get_product("fake-token", "p1")
        self.assertEqual(product["price"], 15500)
        self.assertFalse(product["published"])
        self.assertEqual(product["short_url"], "https://aekraft.gumroad.com/l/iaiyt")


class TestListProductsPagination(unittest.TestCase):
    """Regression guard for the real bug found 2026-10-13: GET /v2/products
    is paginated by Gumroad at 10 items/page via next_page_key, and
    list_products() used to return only that first page, silently (live-
    verified against the real account: 10 reported vs 77 real, across 8
    pages). No real HTTP call is ever made here -- requests.request is
    patched in every test, same convention as every other test in this
    file."""

    def test_single_page_with_no_next_key_returns_just_that_page(self):
        only_page = _fake_response(status_code=200, json_data={
            "success": True, "products": [{"id": "p1"}, {"id": "p2"}],
        })
        with patch.object(gp.requests, "request", return_value=only_page) as mock_req:
            products = gp.list_products("fake-token")
        self.assertEqual(products, [{"id": "p1"}, {"id": "p2"}])
        self.assertEqual(mock_req.call_count, 1)

    def test_follows_pagination_across_multiple_pages_and_accumulates_all(self):
        page1 = _fake_response(status_code=200, json_data={
            "success": True, "products": [{"id": "p1"}, {"id": "p2"}],
            "next_page_key": "CURSOR-A",
        })
        page2 = _fake_response(status_code=200, json_data={
            "success": True, "products": [{"id": "p3"}],
            "next_page_key": "CURSOR-B",
        })
        page3 = _fake_response(status_code=200, json_data={
            "success": True, "products": [{"id": "p4"}],
            # no next_page_key -- this is the last page
        })
        with patch.object(gp.requests, "request", side_effect=[page1, page2, page3]) as mock_req:
            products = gp.list_products("fake-token")
        self.assertEqual(products, [{"id": "p1"}, {"id": "p2"}, {"id": "p3"}, {"id": "p4"}])
        self.assertEqual(mock_req.call_count, 3)
        # The cursor from each page must be threaded into the NEXT request's
        # own params, exactly as Gumroad's own next_page_url implies.
        _, kwargs_call2 = mock_req.call_args_list[1]
        self.assertEqual(kwargs_call2["params"].get("page_key"), "CURSOR-A")
        _, kwargs_call3 = mock_req.call_args_list[2]
        self.assertEqual(kwargs_call3["params"].get("page_key"), "CURSOR-B")
        # The very first request must NOT carry a page_key at all.
        _, kwargs_call1 = mock_req.call_args_list[0]
        self.assertNotIn("page_key", kwargs_call1["params"])

    def test_safety_cap_raises_rather_than_looping_forever(self):
        # Each page returns a genuinely DIFFERENT cursor (a real API that
        # keeps progressing but somehow never terminates) -- isolates the
        # page-cap guard from the separate repeated-cursor guard below.
        responses = [
            _fake_response(status_code=200, json_data={
                "success": True, "products": [{"id": f"x{i}"}],
                "next_page_key": f"CURSOR-{i}",
            }) for i in range(10)
        ]
        with patch.object(gp, "_MAX_PAGES", 3), \
             patch.object(gp.requests, "request", side_effect=responses) as mock_req:
            with self.assertRaisesRegex(RuntimeError, "stopped after 3 pages"):
                gp.list_products("fake-token")
        self.assertEqual(mock_req.call_count, 3)

    def test_repeated_cursor_raises_immediately_as_a_cycle_not_a_slow_cap(self):
        """A real pagination cycle (the same page_key handed back again) is
        a distinct, more specific bug than merely 'many pages' -- it must
        be caught the moment it repeats, not only after _MAX_PAGES."""
        page1 = _fake_response(status_code=200, json_data={
            "success": True, "products": [{"id": "p1"}], "next_page_key": "CURSOR-A",
        })
        page2 = _fake_response(status_code=200, json_data={
            "success": True, "products": [{"id": "p2"}], "next_page_key": "CURSOR-A",  # repeats!
        })
        with patch.object(gp.requests, "request", side_effect=[page1, page2]) as mock_req:
            with self.assertRaisesRegex(RuntimeError, "cycling"):
                gp.list_products("fake-token")
        self.assertEqual(mock_req.call_count, 2)

    def test_duplicate_product_id_across_pages_is_never_double_counted(self):
        """Real-world case: the catalog shifts mid-walk (e.g. a product
        created between two fetches) and the same id reappears on a later
        page. It must be skipped, not duplicated in the final result."""
        page1 = _fake_response(status_code=200, json_data={
            "success": True, "products": [{"id": "p1"}, {"id": "p2"}], "next_page_key": "CURSOR-A",
        })
        page2 = _fake_response(status_code=200, json_data={
            "success": True, "products": [{"id": "p2"}, {"id": "p3"}],  # p2 repeats
        })
        with patch.object(gp.requests, "request", side_effect=[page1, page2]):
            products = gp.list_products("fake-token")
        self.assertEqual(products, [{"id": "p1"}, {"id": "p2"}, {"id": "p3"}])

    def test_empty_page_with_no_next_key_returns_empty_list_not_an_error(self):
        empty = _fake_response(status_code=200, json_data={"success": True, "products": []})
        with patch.object(gp.requests, "request", return_value=empty):
            products = gp.list_products("fake-token")
        self.assertEqual(products, [])

    def test_mid_walk_http_failure_reports_real_partial_progress_never_silent_truncation(self):
        page1 = _fake_response(status_code=200, json_data={
            "success": True, "products": [{"id": "p1"}, {"id": "p2"}], "next_page_key": "CURSOR-A",
        })
        # A real transient failure is retried _RETRY_ATTEMPTS times before
        # surfacing -- supply one exception per attempt, same convention as
        # TestRetryOnTransientFailure's own test_get_sales_gives_up_after_max_attempts.
        failures = [gp.requests.RequestException("boom")] * gp._RETRY_ATTEMPTS
        with patch.object(gp.requests, "request", side_effect=[page1, *failures]), \
             patch.object(gp.time, "sleep"):
            with self.assertRaisesRegex(RuntimeError, r"after 1 page\(s\) \(2 product\(s\) fetched so far -- inventory INCOMPLETE"):
                gp.list_products("fake-token")

    def test_mid_walk_success_false_reports_real_partial_progress(self):
        page1 = _fake_response(status_code=200, json_data={
            "success": True, "products": [{"id": "p1"}], "next_page_key": "CURSOR-A",
        })
        page2 = _fake_response(status_code=200, json_data={"success": False, "error": "rate limited"})
        with patch.object(gp.requests, "request", side_effect=[page1, page2]):
            with self.assertRaisesRegex(RuntimeError, r"after 1 page\(s\) \(1 product\(s\) fetched so far -- inventory INCOMPLETE"):
                gp.list_products("fake-token")


class TestUpdateProductVerification(unittest.TestCase):
    """Regression guard for the real bug found 2026-10-11 (Cycle 106):
    Gumroad's PUT /v2/products/:id can return success:true without the
    write actually persisting. update_product() must never again trust
    that response alone -- every test here drives the real post-write
    re-read path via an injected get_product_fn (never the real network),
    and no real product is ever touched. verify_delay_seconds=0 everywhere
    so tests run instantly."""

    def _put_ok(self, returned_product=None):
        return _fake_response(status_code=200, json_data={
            "success": True, "product": returned_product or {},
        })

    def test_success_and_proven_persistence_returns_the_fresh_reread(self):
        put_ok = self._put_ok()
        reread = {"id": "p1", "description": "new text", "tags": ["a", "b"]}
        with patch.object(gp.requests, "request", return_value=put_ok):
            result = gp.update_product(
                "fake-token", "p1", {"description": "new text", "tags": ["a", "b"]},
                verify_delay_seconds=0, get_product_fn=lambda token, pid: reread,
            )
        self.assertEqual(result, reread)

    def test_false_success_response_without_persistence_raises_verification_failed(self):
        """The exact Cycle 106 shape: PUT says success, re-read proves the
        field never changed."""
        put_ok = self._put_ok()
        reread_unchanged = {"id": "p1", "description": "OLD UNCHANGED TEXT"}
        with patch.object(gp.requests, "request", return_value=put_ok):
            with self.assertRaisesRegex(RuntimeError, "VERIFICATION_FAILED"):
                gp.update_product(
                    "fake-token", "p1", {"description": "new text"},
                    verify_delay_seconds=0, get_product_fn=lambda token, pid: reread_unchanged,
                )

    def test_partial_mismatch_among_several_fields_still_fails_not_partial_pass(self):
        put_ok = self._put_ok()
        reread_partial = {"id": "p1", "name": "New Name", "description": "OLD DESCRIPTION"}
        with patch.object(gp.requests, "request", return_value=put_ok):
            with self.assertRaisesRegex(RuntimeError, "VERIFICATION_FAILED"):
                gp.update_product(
                    "fake-token", "p1", {"name": "New Name", "description": "new description"},
                    verify_delay_seconds=0, get_product_fn=lambda token, pid: reread_partial,
                )

    def test_reread_failure_raises_verification_unknown_not_a_false_pass(self):
        put_ok = self._put_ok()

        def _broken_reread(token, pid):
            raise RuntimeError("Gumroad get_product request failed: timeout")

        with patch.object(gp.requests, "request", return_value=put_ok):
            with self.assertRaisesRegex(RuntimeError, "VERIFICATION_UNKNOWN"):
                gp.update_product(
                    "fake-token", "p1", {"description": "new text"},
                    verify_delay_seconds=0, get_product_fn=_broken_reread,
                )

    def test_reread_returning_non_dict_raises_verification_unknown(self):
        put_ok = self._put_ok()
        with patch.object(gp.requests, "request", return_value=put_ok):
            with self.assertRaisesRegex(RuntimeError, "VERIFICATION_UNKNOWN"):
                gp.update_product(
                    "fake-token", "p1", {"description": "new text"},
                    verify_delay_seconds=0, get_product_fn=lambda token, pid: None,
                )

    def test_invalid_api_response_body_raises_before_any_reread_attempt(self):
        """success:false (or a malformed body) is a real, immediate
        platform-side rejection -- BLOCKED, same as before this fix. No
        re-read should even be attempted."""
        put_blocked = _fake_response(status_code=200, json_data={
            "success": False, "message": "Name A tag is too long. Please try again with a shorter one, under 20 characters.",
        })
        reread_spy = MagicMock(side_effect=AssertionError("re-read must never be attempted on a blocked write"))
        with patch.object(gp.requests, "request", return_value=put_blocked):
            with self.assertRaisesRegex(RuntimeError, "Gumroad update_product failed"):
                gp.update_product(
                    "fake-token", "p1", {"tags": ["toolong-probe-tag-value"]},
                    verify_delay_seconds=0, get_product_fn=reread_spy,
                )
        reread_spy.assert_not_called()

    def test_no_update_requested_refuses_before_any_network_call(self):
        with patch.object(gp.requests, "request") as mock_req:
            with self.assertRaises(gp.ConfigError):
                gp.update_product("fake-token", "p1", {})
        mock_req.assert_not_called()

    def test_list_field_comparison_is_order_sensitive_matching_live_observed_behavior(self):
        """Live-verified 2026-10-13: a written tag list round-trips in the
        exact order sent. A re-read returning the same tags in a DIFFERENT
        order is therefore an honest mismatch, not a false pass."""
        put_ok = self._put_ok()
        reread_reordered = {"id": "p1", "tags": ["b", "a"]}
        with patch.object(gp.requests, "request", return_value=put_ok):
            with self.assertRaisesRegex(RuntimeError, "VERIFICATION_FAILED"):
                gp.update_product(
                    "fake-token", "p1", {"tags": ["a", "b"]},
                    verify_delay_seconds=0, get_product_fn=lambda token, pid: reread_reordered,
                )

    def test_only_requested_fields_are_compared_an_unrelated_platform_change_never_fails_the_write(self):
        """A legitimate platform-side change to a field this call never
        asked to update (e.g. Gumroad bumping its own updated_at) must
        never cause a false FAIL."""
        put_ok = self._put_ok()
        reread = {"id": "p1", "description": "new text", "updated_at": "2026-10-13T00:00:00Z"}
        with patch.object(gp.requests, "request", return_value=put_ok):
            result = gp.update_product(
                "fake-token", "p1", {"description": "new text"},
                verify_delay_seconds=0, get_product_fn=lambda token, pid: reread,
            )
        self.assertEqual(result, reread)


class TestNonInteractiveAuth(unittest.TestCase):
    """Regression guard (C99).

    A Git Credential Manager dialog appeared during a commercial-status check
    on 2026-10-11. Root cause: an ad-hoc shell command ran
    `git credential fill` against host=api.gumroad.com. Git Credential Manager
    does not know that host, so it fell back to an INTERACTIVE prompt and
    blocked a non-interactive session until timeout.

    Gumroad has no git remote. Asking git for its credentials is always wrong
    and can only ever escalate to a human dialog. These tests fail if any code
    path in this module regresses into shelling out to git (or any other
    subprocess) for authentication, and pin the two properties that keep the
    verification path non-interactive and secret-safe."""

    def test_module_never_imports_or_shells_out_to_subprocess(self):
        # A `git credential fill` regression would necessarily appear here.
        self.assertNotIn("subprocess", dir(gp))
        source = (_FACTORY_ROOT / "channels" / "gumroad_publisher.py").read_text(
            encoding="utf-8", errors="ignore"
        )
        for forbidden in ("git credential", "git-credential", "credential fill",
                          "git credential-manager", "GCM", "getpass", "input("):
            self.assertNotIn(
                forbidden, source,
                f"channels/gumroad_publisher.py must never reference {forbidden!r} — "
                "it opens an interactive credential dialog (C99)",
            )

    def test_api_base_is_official_gumroad_host(self):
        self.assertTrue(
            gp.GUMROAD_API_BASE.startswith("https://api.gumroad.com/"),
            f"GUMROAD_API_BASE must be the official Gumroad API host, got "
            f"{gp.GUMROAD_API_BASE!r}",
        )

    def test_get_sales_authenticates_directly_not_via_credential_helper(self):
        """Auth travels as an explicit credential on the request itself.
        Gumroad v2's documented scheme is the `access_token` parameter (which
        this module uses consistently); an Authorization header is equally
        valid. Either way the token is PRESENT on the call, so it can never be
        silently delegated to an OS credential helper that could prompt."""
        ok = _fake_response(status_code=200, json_data={"success": True, "sales": []})
        with patch.object(gp.requests, "request", return_value=ok) as mock_req:
            gp.get_sales("fake-token")
        _, kwargs = mock_req.call_args
        carried = kwargs.get("params", {}).get("access_token") or \
            kwargs.get("data", {}).get("access_token") or \
            kwargs.get("headers", {}).get("Authorization")
        self.assertEqual(carried, "fake-token")

    def test_token_never_appears_in_error_output(self):
        """A failed call must never echo the access token back to stdout/logs,
        including the requests exception text (which can embed the URL)."""
        secret = "super-secret-token-value"
        gp._LAST_LOADED_TOKEN = secret
        try:
            err = gp._safe_err(Exception(f"GET https://api.gumroad.com/v2/sales?access_token={secret} failed"))
            self.assertNotIn(secret, err)
            self.assertIn("REDACTED", err)
        finally:
            gp._LAST_LOADED_TOKEN = ""

    def test_pattern_redaction_covers_an_unknown_token(self):
        """C100: the token reached a terminal on 2026-10-11 because a
        requests exception carrying the full URL was printed unredacted.
        Known-value redaction alone is not enough - it only fires for a token
        this process loaded. This asserts the pattern layer, which blanks any
        access_token= value even when it was never loaded."""
        unknown = "zzz-never-loaded-zzz"
        err = gp._safe_err(Exception(
            f"Invalid URL 'https://api.gumroad.com/v2/sales?access_token={unknown}': No scheme"))
        self.assertNotIn(unknown, err)
        self.assertIn("access_token=***REDACTED***", err)

    def test_cli_catch_all_redacts_before_printing(self):
        """The main() catch-all used str(e) directly, bypassing redaction.
        Assert that path now routes through _safe_err."""
        source = (_FACTORY_ROOT / "channels" / "gumroad_publisher.py").read_text(
            encoding="utf-8", errors="ignore")
        catch_all = source.split("except Exception as e:", 1)[1]
        self.assertIn('"error": _safe_err(e)', catch_all,
                      "the CLI catch-all must redact via _safe_err(e), not str(e)")


if __name__ == "__main__":
    unittest.main()
