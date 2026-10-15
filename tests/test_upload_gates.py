"""Tests for the Cycle 85 Phase 3 upload/abort gates.

These two helpers hold their own requests.post and had no gate until now. The
tests that matter assert not merely that they raise, but that they make ZERO
network calls when refused -- an abort that posts without authorization could
cancel an upload session the caller does not own, and an upload that posts
without one leaves a dangling S3 multipart session on the platform side.

All network is mocked. No live call is ever made.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_TMP = tempfile.mkdtemp(prefix="gf_c85_")
os.environ["FACTORY_WRITE_SCOPE_DIR"] = _TMP
os.environ.pop("FACTORY_LIVE_PUBLISH", None)

from channels import gumroad_publisher as gp      # noqa: E402
from channels import write_scope as ws           # noqa: E402
from channels.write_gate import WriteNotAuthorized  # noqa: E402

PID = "LzOV85deBGdLgNZmvpvYGw=="
REAL_FILE = "books/eu_ai_act_compliance_toolkit_v2.pdf"


def _up_scope(path=REAL_FILE, pid=PID):
    return ws.issue_scope(product_id=pid, slug="bfhpzl",
                          payload={"file_path": str(path)},
                          operation="upload_file", note="test")


def _abort_scope(uid="UP_12345", pid=PID):
    return ws.issue_scope(product_id=pid, slug="bfhpzl",
                          payload={"upload_id": str(uid)},
                          operation="abort_upload", note="test")


class TestFailClosedWithoutAuthorization(unittest.TestCase):
    def test_upload_without_scope_denies_and_sends_nothing(self):
        with patch("requests.post") as post:
            with self.assertRaises(WriteNotAuthorized):
                gp._upload_file("tok", REAL_FILE)
            self.assertEqual(post.call_count, 0)

    def test_abort_without_scope_denies_and_sends_nothing(self):
        with patch("requests.post") as post:
            with self.assertRaises(WriteNotAuthorized):
                gp._abort_upload("tok", "UP_12345")
            self.assertEqual(post.call_count, 0)

    def test_denial_precedes_file_validation(self):
        """A nonexistent path must not become a probe oracle."""
        with patch("requests.post") as post:
            with self.assertRaises(WriteNotAuthorized):
                gp._upload_file("tok", "no_such_file.pdf")
            self.assertEqual(post.call_count, 0)


class TestUploadBinding(unittest.TestCase):
    def test_valid_scope_reaches_network(self):
        # _upload_file issues its presign through _request_with_retry, not
        # requests.post directly. An earlier version of this test patched
        # requests.post and so asserted a call count that could never move.
        #
        # It also pointed at a real book in books/, which is gitignored. That
        # passed locally and FAILED in CI, where the file does not exist: the
        # gate is consumed first, then file validation raises, and the presign
        # is never reached. Use a real temporary file so the test depends on
        # nothing outside the test itself.
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as fh:
            fh.write(b"%PDF-1.4 test")
            real = fh.name
        self.addCleanup(lambda: os.path.exists(real) and os.unlink(real))
        s = _up_scope(path=real)
        with patch("channels.gumroad_publisher._request_with_retry") as rr:
            rr.return_value = _Resp({"success": True, "url": "https://x/y"})
            try:
                gp._upload_file("tok", real, scope_id=s.scope_id,
                                product_id=PID)
            except Exception:  # noqa: BLE001 - later failure is not the gate's job
                pass
        self.assertGreater(rr.call_count, 0,
                           "a valid authorization must actually be usable")

    def test_scope_bound_to_a_different_file_is_refused(self):
        s = _up_scope(path="some/other/file.pdf")
        with patch("channels.gumroad_publisher._request_with_retry") as rr:
            with self.assertRaises(WriteNotAuthorized):
                gp._upload_file("tok", REAL_FILE, scope_id=s.scope_id,
                                product_id=PID)
            self.assertEqual(rr.call_count, 0)

    def test_scope_bound_to_a_different_product_is_refused(self):
        s = _up_scope(pid="OTHER_PRODUCT==")
        with patch("requests.post") as post:
            with self.assertRaises(WriteNotAuthorized):
                gp._upload_file("tok", REAL_FILE, scope_id=s.scope_id,
                                product_id=PID)
            self.assertEqual(post.call_count, 0)

    def test_upload_scope_cannot_authorize_an_abort(self):
        s = _up_scope()
        with patch("requests.post") as post:
            with self.assertRaises(WriteNotAuthorized):
                gp._abort_upload("tok", "UP_12345", scope_id=s.scope_id,
                                 product_id=PID)
            self.assertEqual(post.call_count, 0)

    def test_replay_of_an_upload_scope_is_refused(self):
        s = _up_scope()
        with patch("channels.gumroad_publisher._request_with_retry") as rr:
            rr.return_value = _Resp({"success": True, "url": "https://x/y"})
            with patch("requests.post") as post:
                post.return_value = _Resp({"success": True})
                try:
                    gp._upload_file("tok", REAL_FILE, scope_id=s.scope_id,
                                    product_id=PID)
                except Exception:  # noqa: BLE001
                    pass
                with self.assertRaises(WriteNotAuthorized):
                    gp._upload_file("tok", REAL_FILE, scope_id=s.scope_id,
                                    product_id=PID)


class TestAbortBinding(unittest.TestCase):
    def test_abort_scope_bound_to_a_different_session_is_refused(self):
        s = _abort_scope(uid="SOMEONE_ELSES_SESSION")
        with patch("requests.post") as post:
            with self.assertRaises(WriteNotAuthorized):
                gp._abort_upload("tok", "UP_12345", scope_id=s.scope_id,
                                 product_id=PID)
            self.assertEqual(post.call_count, 0,
                             "a session id the caller does not own must never "
                             "be cancellable through this path")

    def test_replay_of_an_abort_scope_is_refused(self):
        s = _abort_scope()
        with patch("requests.post") as post:
            post.return_value = _Resp({"success": True, "status": "already_gone"})
            gp._abort_upload("tok", "UP_12345", scope_id=s.scope_id,
                             product_id=PID)
            with self.assertRaises(WriteNotAuthorized):
                gp._abort_upload("tok", "UP_12345", scope_id=s.scope_id,
                                 product_id=PID)

    def test_expired_abort_scope_is_refused(self):
        """Consume is checked against wall-clock expiry inside the gate, so
        the gate-level refusal is proven by a scope that has already timed
        out on disk. An earlier version of this test first CONSUMED a valid
        scope and then asserted it raised -- which can never be true, so the
        test was proving nothing."""
        import time
        s = _abort_scope(uid="UP_EXPIRED")
        # fast-forward past its TTL by rewriting the stored expiry
        from channels import write_scope as _ws
        path = _ws._store_path(s.scope_id)
        import json as _json
        data = _json.loads(path.read_text(encoding="utf-8"))
        data["expires_utc"] = time.time() - 1
        path.write_text(_json.dumps(data), encoding="utf-8")

        with patch("requests.post") as post:
            with self.assertRaises(WriteNotAuthorized):
                gp._abort_upload("tok", "UP_EXPIRED", scope_id=s.scope_id,
                                 product_id=PID)
            self.assertEqual(post.call_count, 0)


class TestScopeCannotBeMintedForUnsafeOperations(unittest.TestCase):
    def test_price_and_files_cannot_be_scoped(self):
        for field in ("price", "files", "published", "name"):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    ws.issue_scope(product_id=PID, slug="bfhpzl",
                                   payload={field: "x"},
                                   operation="upload_file",
                                   allowed_fields=("file_path", field))

    def test_unknown_operation_is_refused(self):
        with self.assertRaises(ValueError):
            ws.issue_scope(product_id=PID, slug="bfhpzl", payload={},
                           operation="delete_product")

    def test_upload_fields_are_operation_specific(self):
        self.assertEqual(set(ws.operation_fields("upload_file")), {"file_path"})
        self.assertEqual(set(ws.operation_fields("abort_upload")), {"upload_id"})
        self.assertEqual(set(ws.operation_fields("update_description")),
                         {"description"})


class _Resp:
    """Minimal requests.Response stand-in."""

    def __init__(self, payload):
        self._p = payload

    def json(self):
        return self._p

    def raise_for_status(self):
        return None


if __name__ == "__main__":
    unittest.main(verbosity=2)

class TestPayloadKeySmuggling(unittest.TestCase):
    """Cycle 86: the mint must refuse a payload carrying an unauthorized field.

    consume_scope already refused these, so this was never exploitable. The
    probe that found it only tested the mint, which is why it first looked
    alarming. Hardening the mint removes the dependence on a downstream check.
    """

    def test_price_payload_cannot_be_minted(self):
        for field in ("price", "name", "files", "published", "tags"):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    ws.issue_scope(product_id=PID, slug="bfhpzl",
                                   payload={field: "x"},
                                   operation="update_description")

    def test_mixed_payload_is_refused_rather_than_partly_honoured(self):
        with self.assertRaises(ValueError):
            ws.issue_scope(product_id=PID, slug="bfhpzl",
                           payload={"description": "ok", "price": 1},
                           operation="update_description")

    def test_permitted_field_still_mints_normally(self):
        s = ws.issue_scope(product_id=PID, slug="bfhpzl",
                           payload={"description": "text"},
                           operation="update_description")
        self.assertEqual(s.allowed_fields, ("description",))

    def test_upload_and_abort_payloads_are_unaffected(self):
        ws.issue_scope(product_id=PID, slug="bfhpzl",
                       payload={"file_path": "a.pdf"},
                       operation="upload_file")
        ws.issue_scope(product_id=PID, slug="bfhpzl",
                       payload={"upload_id": "UP_1"},
                       operation="abort_upload")
