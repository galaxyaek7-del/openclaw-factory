"""Regression tests for the arXiv TLS failure (Cycle 105, 2026-10-18).

Observed root cause: this interpreter's default CA bundle
(``C:\\Program Files\\Common Files\\SSL\\cert.pem``) does not contain the
issuer arXiv's chain needs, so ``urllib`` raised
``CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate``.
certifi's bundle verifies arXiv. ``http_client.get_ssl_context()`` now
prefers certifi while always keeping verification enabled.

    python -m unittest tests.test_http_client_tls -v
"""

import os
import ssl
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from market_intelligence_core import http_client


class _FakeResp:
    def __init__(self, body=b"ok"):
        self._body = body
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False
    def read(self):
        return self._body


class TestSslContextIsVerifying(unittest.TestCase):
    def test_context_always_verifies(self):
        ctx = http_client.get_ssl_context()
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(ctx.check_hostname)

    def test_context_is_cached(self):
        self.assertIs(http_client.get_ssl_context(), http_client.get_ssl_context())

    def test_prefers_certifi_bundle_when_present(self):
        if http_client._certifi is None:
            self.skipTest("certifi not installed")
        cafile = http_client._certifi.where()
        self.assertTrue(os.path.exists(cafile), "certifi bundle path must exist")
        with patch("market_intelligence_core.http_client.ssl.create_default_context") as mock_ctx:
            http_client._SSL_CONTEXT = None
            try:
                http_client.get_ssl_context()
            finally:
                http_client._SSL_CONTEXT = None
        mock_ctx.assert_called_once_with(cafile=cafile)

    def test_missing_certifi_falls_back_to_verifying_default(self):
        with patch.object(http_client, "_certifi", None):
            http_client._SSL_CONTEXT = None
            try:
                ctx = http_client.get_ssl_context()
            finally:
                http_client._SSL_CONTEXT = None
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)


class TestRequestsCarryTheContext(unittest.TestCase):
    def test_http_get_text_passes_verifying_context(self):
        captured = {}
        def fake_urlopen(req, timeout=None, context=None):
            captured["context"] = context
            return _FakeResp(b"<xml/>")
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            out = http_client.http_get_text("https://export.arxiv.org/api/query?x=1")
        self.assertEqual(out, "<xml/>")
        self.assertIsNotNone(captured["context"])
        self.assertEqual(captured["context"].verify_mode, ssl.CERT_REQUIRED)

    def test_http_get_json_passes_verifying_context(self):
        captured = {}
        def fake_urlopen(req, timeout=None, context=None):
            captured["context"] = context
            return _FakeResp(b'{"ok": true}')
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            self.assertEqual(http_client.http_get_json("https://example.com/x"), {"ok": True})
        self.assertEqual(captured["context"].verify_mode, ssl.CERT_REQUIRED)

    def test_tls_verification_error_is_never_swallowed(self):
        err = ssl.SSLCertVerificationError(1, "unable to get local issuer certificate")
        with patch("urllib.request.urlopen", side_effect=err):
            with self.assertRaises(ssl.SSLCertVerificationError):
                http_client.http_get_text("https://export.arxiv.org/api/query")

    def test_blocked_status_still_raises_evidence_source_blocked(self):
        import urllib.error
        err = urllib.error.HTTPError("https://x", 403, "Forbidden", {}, None)
        with patch("urllib.request.urlopen", side_effect=err):
            with self.assertRaises(http_client.EvidenceSourceBlocked):
                http_client.http_get_text("https://x")


class TestArxivConnectorUsesTheFixedClient(unittest.TestCase):
    def test_connector_imports_the_shared_client(self):
        import inspect
        from multi_source_intelligence.connectors import arxiv
        src = inspect.getsource(arxiv)
        self.assertIn("http_client.http_get_text", src)

    def test_connector_returns_blocked_on_evidence_source_blocked(self):
        from multi_source_intelligence.connectors import arxiv
        with patch("multi_source_intelligence.connectors.arxiv.http_client.http_get_text",
                   side_effect=http_client.EvidenceSourceBlocked(429, "https://export.arxiv.org")):
            result = arxiv.check("x")
        self.assertEqual(result.verification_status, "BLOCKED")


if __name__ == "__main__":
    unittest.main()
