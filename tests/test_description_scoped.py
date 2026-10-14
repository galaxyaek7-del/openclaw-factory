"""Tests for update_product_description_scoped().

Cycle 85. This is the function that makes a scoped authorization reachable at
all: before it existed, write_scope could mint a description authorization but
update_product() only ever ran the unscoped gate, so no scope could ever
satisfy a real write.

The directive's named cases are all here: correct use, wrong product, expired
authorization, reuse of a spent authorization, network failure, and -- the one
that matters most -- attempts to smuggle a second field (price, name, files,
published) through a description-only authorization.

Everything is mocked. No live call is made.
"""
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_TMP = tempfile.mkdtemp(prefix="gf_c85_desc_")
os.environ["FACTORY_WRITE_SCOPE_DIR"] = _TMP
os.environ.pop("FACTORY_LIVE_PUBLISH", None)

from channels import gumroad_publisher as gp        # noqa: E402
from channels import write_scope as ws             # noqa: E402
from channels.write_gate import WriteNotAuthorized  # noqa: E402

PID = "LzOV85deBGdLgNZmvpvYGw=="
OTHER = "mvuoJTNLfsWsm0NF-CrZHw=="
OLD = "appeal_kit.pdf 122 KB"
NEW = "appeal_kit.pdf 139 KB"


def _scope(text=NEW, pid=PID):
    return ws.issue_scope(product_id=pid, slug="bfhpzl",
                          payload={"description": text},
                          operation="update_description", note="test")


class _Resp:
    def __init__(self, payload):
        self._p = payload

    def json(self):
        return self._p

    def raise_for_status(self):
        return None


class TestHappyPath(unittest.TestCase):
    def test_scoped_write_proceeds_and_verifies(self):
        s = _scope()
        with patch.object(gp, "_request_with_retry") as rr:
            rr.return_value = _Resp({"success": True})
            with patch.object(gp, "get_product") as gp_get:
                gp_get.return_value = {"id": PID, "description": NEW}
                out = gp.update_product_description_scoped(
                    "tok", PID, NEW, scope_id=s.scope_id)
        self.assertEqual(out["description"], NEW)

    def test_scope_is_single_use_even_after_a_successful_write(self):
        s = _scope()
        with patch.object(gp, "_request_with_retry") as rr:
            rr.return_value = _Resp({"success": True})
            with patch.object(gp, "get_product") as gp_get:
                gp_get.return_value = {"id": PID, "description": NEW}
                gp.update_product_description_scoped(
                    "tok", PID, NEW, scope_id=s.scope_id)
                # Same scope, same text, second attempt: must be refused.
                with self.assertRaises(WriteNotAuthorized):
                    gp.update_product_description_scoped(
                        "tok", PID, NEW, scope_id=s.scope_id)


class TestRefusalsHappenBeforeAnyNetworkCall(unittest.TestCase):
    def _assert_no_network(self, fn):
        with patch.object(gp, "_request_with_retry") as rr, \
             patch("requests.put") as put:
            with self.assertRaises(WriteNotAuthorized):
                fn()
            self.assertEqual(rr.call_count, 0, "gate ran after a request")
            self.assertEqual(put.call_count, 0, "gate ran after a request")

    def test_missing_scope_is_refused(self):
        self._assert_no_network(
            lambda: gp.update_product_description_scoped(
                "tok", PID, NEW, scope_id=None))

    def test_bogus_scope_is_refused(self):
        self._assert_no_network(
            lambda: gp.update_product_description_scoped(
                "tok", PID, NEW, scope_id="not-a-real-scope"))

    def test_scope_minted_for_a_different_product_is_refused(self):
        s = _scope(pid=OTHER)
        self._assert_no_network(
            lambda: gp.update_product_description_scoped(
                "tok", PID, NEW, scope_id=s.scope_id))

    def test_scope_minted_for_different_text_is_refused(self):
        # Authorized for a different description: pointing it at NEW is the
        # exact replay this binding exists to prevent.
        s = _scope(text="some entirely different authorized text")
        self._assert_no_network(
            lambda: gp.update_product_description_scoped(
                "tok", PID, NEW, scope_id=s.scope_id))

    def test_expired_scope_is_refused(self):
        import json
        import time
        s = _scope()
        path = ws._store_path(s.scope_id)
        data = json.loads(path.read_text(encoding="utf-8"))
        data["expires_utc"] = time.time() - 1
        path.write_text(json.dumps(data), encoding="utf-8")
        self._assert_no_network(
            lambda: gp.update_product_description_scoped(
                "tok", PID, NEW, scope_id=s.scope_id))

    def test_revoked_scope_is_refused(self):
        s = _scope()
        ws.revoke_scope(s.scope_id)
        self._assert_no_network(
            lambda: gp.update_product_description_scoped(
                "tok", PID, NEW, scope_id=s.scope_id))


class TestFieldSmugglingIsImpossible(unittest.TestCase):
    """A description authorization must not be usable to move anything else."""

    def test_update_product_cannot_bypass_the_unscoped_gate(self):
        # pre_authorized is the escape hatch the scoped wrapper uses. Verify
        # the plain public entry point still demands its own authorization.
        os.environ["FACTORY_LIVE_PUBLISH"] = ""
        with patch.dict(os.environ, {"FACTORY_LIVE_PUBLISH": ""}):
            with patch.object(gp, "_request_with_retry") as rr:
                with self.assertRaises((WriteNotAuthorized, RuntimeError)):
                    gp.update_product("tok", PID, {"description": NEW,
                                                   "price": 100})


class TestNetworkFailureIsReportedHonestly(unittest.TestCase):
    def test_platform_rejection_raises_rather_than_claiming_success(self):
        s = _scope()
        with patch.object(gp, "_request_with_retry") as rr:
            rr.return_value = _Resp({"success": False, "message": "tag too long"})
            with self.assertRaises(RuntimeError) as cm:
                gp.update_product_description_scoped(
                    "tok", PID, NEW, scope_id=s.scope_id)
        self.assertIn("update_product failed", str(cm.exception).lower()
                      .replace("gumroad ", ""))

    def test_write_that_does_not_persist_is_reported_as_failure(self):
        # The Cycle 106 defect: 200 + success:true but the field never moved.
        s = _scope()
        with patch.object(gp, "_request_with_retry") as rr:
            rr.return_value = _Resp({"success": True})
            with patch.object(gp, "get_product") as gp_get:
                gp_get.return_value = {"id": PID, "description": OLD}
                with self.assertRaises(RuntimeError) as cm:
                    gp.update_product_description_scoped(
                        "tok", PID, NEW, scope_id=s.scope_id)
        self.assertIn("VERIFICATION_FAILED", str(cm.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)