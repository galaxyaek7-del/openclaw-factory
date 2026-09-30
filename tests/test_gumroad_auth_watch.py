"""Tier-1 tests: gumroad auth watch. No real tokens, no network, no secret values."""
import hashlib
import json
import os
import tempfile
import unittest
from unittest.mock import patch

import gumroad_auth_watch as w


class TestWatch(unittest.TestCase):
    def test_exposed_fingerprint_recognized(self):
        with patch.object(w, "credential_fingerprint",
                          return_value=w.KNOWN_EXPOSED_FP + "deadbeef"):
            st = w.poll(state_path=tempfile.mktemp(suffix=".json"),
                        record_evidence=False)
            self.assertEqual(st["status"], w.UNVERIFIED_COMPROMISED)

    def test_rotated_credential_verified(self):
        new_fp = hashlib.sha256(b"brand-new-token").hexdigest()
        with patch.object(w, "credential_fingerprint", return_value=new_fp), \
             patch.object(w, "redacted_connectivity_check",
                          return_value=(True, 10)):
            p = tempfile.mktemp(suffix=".json")
            st = w.poll(state_path=p, record_evidence=False)
            self.assertEqual(st["status"], w.VERIFIED)
            saved = json.load(open(p, encoding="utf-8"))
            self.assertEqual(saved["status"], w.VERIFIED)

    def test_rejected_credential_invalid(self):
        new_fp = hashlib.sha256(b"bad-token").hexdigest()
        with patch.object(w, "credential_fingerprint", return_value=new_fp), \
             patch.object(w, "redacted_connectivity_check",
                          return_value=(False, "401")):
            st = w.poll(state_path=tempfile.mktemp(suffix=".json"),
                        record_evidence=False)
            self.assertEqual(st["status"], w.INVALID)

    def test_unloadable_is_unknown(self):
        with patch.object(w, "credential_fingerprint", return_value=None):
            st = w.poll(state_path=tempfile.mktemp(suffix=".json"),
                        record_evidence=False)
            self.assertEqual(st["status"], w.UNKNOWN)

    def test_no_secret_in_state(self):
        new_fp = hashlib.sha256(b"rot-token").hexdigest()
        with patch.object(w, "credential_fingerprint", return_value=new_fp), \
             patch.object(w, "redacted_connectivity_check",
                          return_value=(True, 5)):
            p = tempfile.mktemp(suffix=".json")
            w.poll(state_path=p, record_evidence=False)
            raw = open(p, encoding="utf-8").read()
            self.assertNotIn("rot-token", raw)
            self.assertNotIn("brand-new", raw)

    def test_read_state_missing(self):
        self.assertEqual(w.read_state("/nonexistent/path.json"), {})


if __name__ == "__main__":
    unittest.main()
