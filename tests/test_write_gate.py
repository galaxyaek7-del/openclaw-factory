"""Tests for the Phase 5 centralized write gate.

The property that matters is not "the gate raises". It is that a denied write
makes ZERO mutation requests -- no POST to Gumroad, and above all no S3
multipart upload session, which is the one that leaves state behind on
Gumroad's servers even when the product POST is refused.

Every network call is mocked and asserted un-called. Nothing here touches the
live API. TOTAL_NEW_SPEND stays $0.
"""
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import channels.write_gate as wg
from channels import gumroad_publisher as gp
from channels.write_gate import WriteNotAuthorized

TMP = Path(tempfile.gettempdir())


def _state(status="VERIFIED", age_s=0, fp="abc123def4567890", stamp=True):
    d = {"status": status, "reason": "test", "fingerprint_prefix": fp}
    if stamp:
        d["at"] = (datetime.now(timezone.utc)
                   - timedelta(seconds=age_s)).isoformat()
    return d


def _write_state(d):
    p = TMP / "gf_auth_state_test.json"
    p.write_text(__import__("json").dumps(d), encoding="utf-8")
    return str(p)


class TestDenialBranches(unittest.TestCase):
    """Every non-authorised condition must deny. None may fall through."""

    def _check(self, state, flag="true", fp="abc123def4567890"):
        """Run one decision with an explicitly controlled env + state."""
        path = _write_state(state)
        env = dict(os.environ)
        env.pop("FACTORY_LIVE_PUBLISH", None)
        if flag is not None:
            env["FACTORY_LIVE_PUBLISH"] = flag
        with patch.dict(os.environ, env, clear=True):
            return wg.check_write_authorization(
                "op", state_path=path, fingerprint_fn=lambda: fp)

    def _deny(self, state=None, flag="true", fp="abc123def4567890"):
        return self._check(state if state is not None else _state(),
                           flag=flag, fp=fp)

    def test_missing_live_publish_flag_denies(self):
        d = self._deny(flag=None)
        self.assertFalse(d.allowed)
        self.assertIn("FACTORY_LIVE_PUBLISH", d.reason)

    def test_flag_false_denies(self):
        self.assertFalse(self._deny(flag="false").allowed)

    def test_missing_state_file_denies(self):
        env = dict(os.environ)
        env["FACTORY_LIVE_PUBLISH"] = "true"
        with patch.dict(os.environ, env, clear=True):
            d = wg.check_write_authorization(
                "op", state_path=str(TMP / "definitely_absent.json"),
                fingerprint_fn=lambda: "x")
        self.assertFalse(d.allowed)
        self.assertEqual(d.state, "MISSING")

    def test_compromised_state_denies(self):
        d = self._deny(state=_state("UNVERIFIED_COMPROMISED"))
        self.assertFalse(d.allowed)
        self.assertEqual(d.state, "UNVERIFIED_COMPROMISED")

    def test_invalid_state_denies(self):
        self.assertFalse(self._deny(state=_state("INVALID")).allowed)

    def test_unknown_state_denies(self):
        self.assertFalse(self._deny(state=_state("UNKNOWN")).allowed)

    def test_stale_state_denies(self):
        d = self._deny(state=_state("VERIFIED", age_s=99999))
        self.assertFalse(d.allowed)
        self.assertEqual(d.state, "STALE")

    def test_missing_timestamp_denies(self):
        self.assertFalse(self._deny(state=_state("VERIFIED", stamp=False)).allowed)

    def test_fingerprint_drift_denies(self):
        """State says one credential; a different one is live now."""
        d = self._deny(fp="ZZZZZZZZZZZZZZZZ")
        self.assertFalse(d.allowed)
        self.assertFalse(d.fingerprint_match)

    def test_unreadable_credential_denies(self):
        self.assertFalse(self._deny(fp=None).allowed)

    def test_no_fingerprint_recorded_denies(self):
        s = _state()
        s.pop("fingerprint_prefix")
        self.assertFalse(self._deny(state=s).allowed)

    def test_require_raises_on_denial(self):
        with self.assertRaises(WriteNotAuthorized):
            wg.require_write_authorization(
                "op", state_path=str(TMP / "absent.json"),
                fingerprint_fn=lambda: "x")


class TestAuthorizedPath(unittest.TestCase):
    def test_verified_fresh_matching_allows(self):
        path = _write_state(_state("VERIFIED", age_s=5, fp="abc123def4567890"))
        env = dict(os.environ)
        env["FACTORY_LIVE_PUBLISH"] = "true"
        with patch.dict(os.environ, env, clear=True):
            d = wg.check_write_authorization(
                "op", state_path=path, fingerprint_fn=lambda: "abc123def4567890")
        self.assertTrue(d.allowed, d.reason)
        self.assertTrue(d.fingerprint_match)

    def test_gate_cannot_self_verify(self):
        """The gate must never be able to mark a credential verified itself."""
        src = Path("channels/write_gate.py").read_text(encoding="utf-8")
        for forbidden in ('"status"] = "VERIFIED"', "status'] = \"VERIFIED\"",
                          ".update({", "write_text"):
            self.assertNotIn(forbidden, src,
                             f"write_gate must never mutate auth state: {forbidden}")
        self.assertIn("auth.read_state", src,
                      "the authoritative source must be gumroad_auth_watch")


class TestEveryMutationIsGated(unittest.TestCase):
    """A denied call must make ZERO mutation requests."""

    MUTATIONS = ["create_product", "update_product", "update_product_file",
                 "enable_product"]

    def _args(self, fn, token="tok"):
        return {
            "create_product": (token, {"file_path": "x.pdf",
                                       "price_cents": 100, "title": "t"}),
            "update_product": (token, "pid", {"name": "t"}),
            "update_product_file": (token, "pid", "x.pdf"),
            "enable_product": (token, "pid"),
        }[fn]

    def test_all_four_functions_deny_when_gate_closed(self):
        os.environ.pop("FACTORY_LIVE_PUBLISH", None)
        for fn in self.MUTATIONS:
            with self.subTest(fn=fn):
                with self.assertRaises(WriteNotAuthorized):
                    getattr(gp, fn)(*self._args(fn))

    def test_denied_calls_make_zero_network_requests(self):
        os.environ.pop("FACTORY_LIVE_PUBLISH", None)
        for fn in self.MUTATIONS:
            with self.subTest(fn=fn):
                with patch("requests.post") as post, \
                     patch("requests.put") as put, \
                     patch("requests.get") as get, \
                     patch("channels.gumroad_publisher._upload_file") as up:
                    with self.assertRaises(WriteNotAuthorized):
                        getattr(gp, fn)(*self._args(fn))
                    # the critical assertion: nothing was transmitted, and no
                    # S3 multipart session was opened
                    self.assertEqual(post.call_count, 0, f"{fn} called POST")
                    self.assertEqual(put.call_count, 0, f"{fn} called PUT")
                    self.assertEqual(get.call_count, 0, f"{fn} called GET")
                    self.assertEqual(up.call_count, 0,
                                     f"{fn} started an upload session")

    def test_upload_helper_is_never_reached_when_denied(self):
        """create_product validates file_path before uploading; prove the gate
        fires first so no partial effect is possible."""
        os.environ.pop("FACTORY_LIVE_PUBLISH", None)
        with patch("channels.gumroad_publisher._upload_file") as up:
            with self.assertRaises(WriteNotAuthorized):
                gp.create_product("tok", {"file_path": "does_not_exist.pdf",
                                          "price_cents": 100, "title": "t"})
            up.assert_not_called()

    def test_source_shows_gate_is_first_statement(self):
        """
        Regression: the check must be the first EXECUTABLE statement.

        Measured from the `def` line rather than from the end of a docstring,
        because create_product() has no docstring and an earlier version of
        this test searched for the next triple-quote -- landing tens of
        thousands of characters away and failing on a correctly-gated
        function.
        """
        src = Path("channels/gumroad_publisher.py").read_text(encoding="utf-8")
        for fn in self.MUTATIONS:
            def_at = src.index("def " + fn + "(")
            marker = f'_require_write_authorization("{fn}")'
            gate_at = src.index(marker, def_at)
            between = src[def_at:gate_at]
            # Skip the FULL signature, which may wrap across several lines
            # (update_product_file's does), then any docstring. Starting the
            # scan at the first newline treated a wrapped signature's second
            # line as an executable statement.
            close = between.find("):")
            body = between[close + 2:] if close != -1 else between
            tq = chr(34) * 3
            stripped = body.lstrip()
            if stripped.startswith(tq):
                # the docstring may begin on the same line as its opening
                # quotes, so search for the CLOSING triple quote from just
                # past the opening one -- not from index 3, which finds the
                # opening quote again when the body is indented.
                open_at = len(body) - len(stripped)
                end = body.index(tq, open_at + 3) + 3
                body = body[end:]
            for line in body.splitlines():
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                self.fail(f"{fn}: executable statement precedes the gate: {s!r}")
            # No separate substring scan for requests.post / _upload_file here:
            # the line loop above already proves no executable statement
            # precedes the gate. A substring scan produced a false positive
            # because create_product's own explanatory COMMENT mentions
            # _upload_file() -- textually present, never executed.


class TestAlternateCallPaths(unittest.TestCase):
    """Aliases and partial imports must not bypass the gate."""

    def test_alias_still_gated(self):
        os.environ.pop("FACTORY_LIVE_PUBLISH", None)
        alias = gp.update_product
        with self.assertRaises(WriteNotAuthorized):
            alias("tok", "pid", {"name": "t"})

    def test_direct_module_import_path_gated(self):
        import importlib
        os.environ.pop("FACTORY_LIVE_PUBLISH", None)
        mod = importlib.import_module("channels.gumroad_publisher")
        with self.assertRaises(WriteNotAuthorized):
            mod.enable_product("tok", "pid")

    def test_every_mutation_function_is_wired(self):
        src = Path("channels/gumroad_publisher.py").read_text(encoding="utf-8")
        for fn in TestEveryMutationIsGated.MUTATIONS:
            self.assertIn(f'_require_write_authorization("{fn}")', src,
                          f"{fn} is not gated")


if __name__ == "__main__":
    unittest.main(verbosity=2)