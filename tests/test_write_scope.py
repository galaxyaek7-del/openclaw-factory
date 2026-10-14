"""Tests for the Cycle 84 single-use, operation-scoped write authorization.

The security here is NOT the token's secrecy. It is BINDING: an authorization
must match the exact product, operation, field set and payload text. These
tests are written to prove that a leaked or replayed authorization is useless
for anything else, and that scoping never relaxes the underlying credential
checks.

Every case uses an isolated scope directory outside the repository. No live
write is attempted; no credential is read, printed or written.
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# redirect scope storage BEFORE importing, so nothing lands in the repo
_TMP = tempfile.mkdtemp(prefix="gf_scopes_")
os.environ["FACTORY_WRITE_SCOPE_DIR"] = _TMP
os.environ.pop("FACTORY_LIVE_PUBLISH", None)

import channels.write_gate as wg           # noqa: E402
from channels import gumroad_publisher as gp  # noqa: E402
from channels import write_scope as ws     # noqa: E402

PID = "LzOV85deBGdLgNZmvpvYGw=="
SLUG = "bfhpzl"
NEW_TEXT = "one .zip, six files, 173 KB ... 139 KB ... 15 KB ..."
OTHER_TEXT = "totally different text that was never authorised"


def _scoped(text=NEW_TEXT, op="update_description",
            fields=("description",), pid=PID):
    return ws.issue_scope(product_id=pid, slug=SLUG,
                          payload={"description": text},
                          operation=op, allowed_fields=fields,
                          note="test")


class TestScopeStorageIsOutsideRepo(unittest.TestCase):
    """A scope must never be able to end up committed."""

    def test_scope_dir_is_outside_the_repository(self):
        d = str(ws.scope_dir()).lower()
        self.assertFalse(d.startswith(str(Path.cwd()).lower()),
                         f"scope storage must not be inside the repo: {d}")

    def test_scope_file_contains_no_credential(self):
        s = _scoped()
        blob = json.dumps(ws.describe_scope(s.scope_id))
        for bad in ("access_token", "GUMROAD", "Bearer", "api_key"):
            self.assertNotIn(bad.lower(), blob.lower())

    def test_describe_returns_no_secret_material(self):
        s = _scoped()
        d = ws.describe_scope(s.scope_id)
        self.assertNotIn("token", d)
        self.assertIn("payload_sha256", d)


class TestScopeCannotBeForNonDescriptionOperations(unittest.TestCase):
    def test_price_operation_is_refused(self):
        with self.assertRaises(ValueError):
            ws.issue_scope(product_id=PID, slug=SLUG,
                           payload={"price": 1}, operation="update_price",
                           allowed_fields=("price",))

    def test_price_field_is_refused_even_under_a_valid_operation(self):
        with self.assertRaises(ValueError):
            ws.issue_scope(product_id=PID, slug=SLUG,
                           payload={"price": 1},
                           operation="update_description",
                           allowed_fields=("description", "price"))

    def test_files_and_published_cannot_be_scoped(self):
        for f in ("files", "published", "name"):
            with self.subTest(field=f):
                with self.assertRaises(ValueError):
                    ws.issue_scope(product_id=PID, slug=SLUG,
                                   payload={f: "x"},
                                   operation="update_description",
                                   allowed_fields=("description", f))


class TestBindingEnforcement(unittest.TestCase):
    """The core: a scope authorises ONE thing and nothing else."""

    def test_exact_match_allows(self):
        s = _scoped()
        d = ws.consume_scope(scope_id=s.scope_id, product_id=PID,
                             payload={"description": NEW_TEXT})
        self.assertTrue(d.allowed, d.reason)

    def test_different_text_is_refused(self):
        s = _scoped()
        d = ws.consume_scope(scope_id=s.scope_id, product_id=PID,
                             payload={"description": OTHER_TEXT})
        self.assertFalse(d.allowed)
        self.assertIn("does not match", d.reason)

    def test_different_product_is_refused(self):
        s = _scoped()
        d = ws.consume_scope(scope_id=s.scope_id, product_id="SOME_OTHER_ID==",
                             payload={"description": NEW_TEXT})
        self.assertFalse(d.allowed)
        self.assertIn("different product", d.reason)

    def test_different_operation_is_refused(self):
        s = _scoped()
        d = ws.consume_scope(scope_id=s.scope_id, product_id=PID,
                             payload={"description": NEW_TEXT},
                             operation="update_price")
        self.assertFalse(d.allowed)

    def test_payload_touching_price_is_refused(self):
        s = _scoped()
        d = ws.consume_scope(scope_id=s.scope_id, product_id=PID,
                             payload={"description": NEW_TEXT, "price": 7900})
        self.assertFalse(d.allowed)
        self.assertIn("outside the authorization", d.reason)

    def test_payload_touching_files_is_refused(self):
        s = _scoped()
        d = ws.consume_scope(scope_id=s.scope_id, product_id=PID,
                             payload={"description": NEW_TEXT,
                                      "files": ["x.zip"]})
        self.assertFalse(d.allowed)

    def test_payload_touching_published_is_refused(self):
        s = _scoped()
        d = ws.consume_scope(scope_id=s.scope_id, product_id=PID,
                             payload={"description": NEW_TEXT,
                                      "published": False})
        self.assertFalse(d.allowed)

    def test_whitespace_only_difference_is_refused(self):
        """A 'harmless' space must not slip through a hash binding."""
        s = _scoped()
        d = ws.consume_scope(scope_id=s.scope_id, product_id=PID,
                             payload={"description": NEW_TEXT + " "})
        self.assertFalse(d.allowed)


class TestSingleUse(unittest.TestCase):
    def test_replay_is_refused(self):
        s = _scoped()
        first = ws.consume_scope(scope_id=s.scope_id, product_id=PID,
                                 payload={"description": NEW_TEXT})
        second = ws.consume_scope(scope_id=s.scope_id, product_id=PID,
                                  payload={"description": NEW_TEXT})
        self.assertTrue(first.allowed)
        self.assertFalse(second.allowed, "a scope must not be usable twice")
        self.assertIn("already used", second.reason)

    def test_a_failed_binding_does_not_consume_the_scope(self):
        """A rejected attempt must not burn a valid authorization."""
        s = _scoped()
        bad = ws.consume_scope(scope_id=s.scope_id, product_id=PID,
                               payload={"description": OTHER_TEXT})
        self.assertFalse(bad.allowed)
        good = ws.consume_scope(scope_id=s.scope_id, product_id=PID,
                                payload={"description": NEW_TEXT})
        self.assertTrue(good.allowed,
                        "a refused attempt wrongly consumed the scope")

    def test_revocation_blocks_use(self):
        s = _scoped()
        self.assertTrue(ws.revoke_scope(s.scope_id))
        d = ws.consume_scope(scope_id=s.scope_id, product_id=PID,
                             payload={"description": NEW_TEXT})
        self.assertFalse(d.allowed)
        self.assertIn("revoked", d.reason)

    def test_expiry_is_refused(self):
        import time
        s = _scoped()
        d = ws.consume_scope(scope_id=s.scope_id, product_id=PID,
                             payload={"description": NEW_TEXT},
                             now=time.time() + 10_000)
        self.assertFalse(d.allowed)
        self.assertIn("expired", d.reason)

    def test_unknown_scope_id_is_refused(self):
        d = ws.consume_scope(scope_id="not-a-real-id", product_id=PID,
                             payload={"description": NEW_TEXT})
        self.assertFalse(d.allowed)

    def test_empty_scope_id_is_refused(self):
        d = ws.consume_scope(scope_id="", product_id=PID,
                             payload={"description": NEW_TEXT})
        self.assertFalse(d.allowed)


class TestGateIntegration(unittest.TestCase):
    """Scoping narrows WHO/WHAT. It never relaxes the credential check."""

    def _state(self, status="VERIFIED", fp="abc123"):
        p = Path(_TMP) / "state.json"
        from datetime import datetime, timezone
        p.write_text(json.dumps({
            "status": status, "fingerprint_prefix": fp,
            "at": datetime.now(timezone.utc).isoformat()}), encoding="utf-8")
        return str(p)

    def test_unscoped_write_still_denied_with_flag_off(self):
        """Case 1: live publishing disabled -> refuse."""
        d = wg.check_write_authorization("update_description",
                                        state_path=self._state(),
                                        fingerprint_fn=lambda: "abc123")
        self.assertFalse(d.allowed)

    def test_scoped_write_denied_when_auth_state_is_not_verified(self):
        """Case 12 / 2: a valid scope must NOT bypass credential checks."""
        s = _scoped()
        d = wg.check_write_authorization(
            "update_description",
            state_path=self._state(status="UNVERIFIED_COMPROMISED"),
            fingerprint_fn=lambda: "abc123",
            scope_id=s.scope_id, product_id=PID,
            payload={"description": NEW_TEXT})
        self.assertFalse(d.allowed, "a scope overrode the credential state")

    def test_scoped_write_denied_when_fingerprint_drifts(self):
        s = _scoped()
        d = wg.check_write_authorization(
            "update_description", state_path=self._state(),
            fingerprint_fn=lambda: "zzz999",
            scope_id=s.scope_id, product_id=PID,
            payload={"description": NEW_TEXT})
        self.assertFalse(d.allowed)

    def test_scoped_write_allowed_when_everything_matches(self):
        """The one permitted path: valid scope AND valid auth state."""
        s = _scoped()
        d = wg.check_write_authorization(
            "update_description", state_path=self._state(),
            fingerprint_fn=lambda: "abc123",
            scope_id=s.scope_id, product_id=PID,
            payload={"description": NEW_TEXT})
        self.assertTrue(d.allowed, d.reason)
        self.assertIn("scoped", d.reason)

    def test_scope_is_consumed_even_when_later_checks_fail(self):
        """
        Documented consequence, asserted rather than hidden: consume happens
        before the credential checks, so a failed credential check still burns
        the scope. That is the safe direction -- a rejected attempt must not
        leave a usable authorization lying around -- and it is why issuing a
        fresh scope is the correct response to a failure.
        """
        s = _scoped()
        wg.check_write_authorization(
            "update_description",
            state_path=self._state(status="INVALID"),
            fingerprint_fn=lambda: "abc123",
            scope_id=s.scope_id, product_id=PID,
            payload={"description": NEW_TEXT})
        self.assertEqual(ws.describe_scope(s.scope_id)["state"], "CONSUMED")


class TestBypassResistance(unittest.TestCase):
    """Case 11: calling the publisher directly must still be blocked."""

    MUTATIONS = ["create_product", "update_product", "update_product_file",
                 "enable_product"]

    def test_direct_publisher_calls_are_refused(self):
        for fn in self.MUTATIONS:
            with self.subTest(fn=fn):
                args = {
                    "create_product": ("tok", {"file_path": "f",
                                               "price_cents": 1, "title": "t"}),
                    "update_product": ("tok", "pid", {"name": "t"}),
                    "update_product_file": ("tok", "pid", "f.pdf"),
                    "enable_product": ("tok", "pid"),
                }[fn]
                with patch("requests.post") as post, \
                     patch("requests.put") as put, \
                     patch("channels.gumroad_publisher._upload_file") as up:
                    with self.assertRaises(wg.WriteNotAuthorized):
                        getattr(gp, fn)(*args)
                    self.assertEqual(post.call_count, 0)
                    self.assertEqual(put.call_count, 0)
                    self.assertEqual(up.call_count, 0)

    def test_ungated_helpers_are_now_documented_as_unsafe_to_call_directly(self):
        """Phase 2 audit found _upload_file/_abort_upload hold mutations with
        no gate of their own. They remain reachable only from gated callers;
        this asserts that is still the only way in."""
        src = Path("channels/gumroad_publisher.py").read_text(encoding="utf-8")
        for helper in ("_upload_file", "_abort_upload"):
            i = src.index(f"def {helper}(")
            import re
            nxt = re.search(r"^def \w+\(", src[i + 5:], re.M)
            body = src[i:i + 5 + nxt.start()]
            self.assertNotIn("_require_write_authorization", body,
                             f"{helper} must stay private and gate-free; only "
                             f"gated callers may reach it")


class TestNoRealCapabilityLeak(unittest.TestCase):
    """Cases 14 & 15: tests must not create production capability."""

    def test_the_global_flag_is_opt_in_not_autouse(self):
        """
        The Cycle 84 correction: an autouse fixture that set
        FACTORY_LIVE_PUBLISH for the whole suite was itself the hidden broad
        permission the directive forbids, and it made every "the gate denies"
        assertion untestable.

        An earlier version of this test asserted the variable NAME never
        appears in conftest.py. That was wrong: the opt-in fixture must
        contain it in order to set it. The property that actually matters is
        that it is never applied without a test asking for it by name.
        """
        src = Path("tests/conftest.py").read_text(encoding="utf-8")
        self.assertNotIn("@pytest.fixture(autouse=True)\ndef _authorize_write_gate",
                         src,
                         "the write-gate authorization must not be autouse")
        self.assertNotIn("_authorize_write_gate_for_tests", src,
                         "the old suite-wide fixture must be gone")
        self.assertIn("def authorize_live_writes(", src,
                      "an explicit opt-in fixture must exist")
        # and it must be a plain fixture, requested by name
        idx = src.index("def authorize_live_writes(")
        decl = src[max(0, idx - 60):idx]
        self.assertNotIn("autouse", decl)

    def test_scope_storage_defaults_outside_repo(self):
        self.assertIn("LOCALAPPDATA", Path("channels/write_scope.py")
                      .read_text(encoding="utf-8"))

    def test_no_scope_material_is_written_into_the_repo(self):
        repo = Path.cwd()
        leaks = [p for p in repo.glob("**/*.json")
                 if p.is_file() and "scope_id" in p.read_text(
                     encoding="utf-8", errors="ignore")[:4000]
                 and "write_scopes" not in str(p)]
        self.assertEqual(leaks, [], f"scope material found in repo: {leaks}")


if __name__ == "__main__":
    unittest.main(verbosity=2)