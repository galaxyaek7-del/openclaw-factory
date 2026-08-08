import hashlib
import hmac
import json
import os
import tempfile
import time
import unittest

from channels import paddle_webhook as pw

_FAKE_SECRET = "test_only_fake_secret_never_a_real_paddle_secret"
_CATALOG = [{"title": "Test Product", "product_id": "pro_test1", "price_id": "pri_test1", "price": 100.0}]


def _sign(body_bytes, secret, ts=None):
    ts = ts or str(int(time.time()))
    signed_payload = f"{ts}:".encode("utf-8") + body_bytes
    h1 = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"ts={ts};h1={h1}"


def _valid_payload(event_id="evt_1", event_type="transaction.completed", amount_cents=10000, currency="USD", price_id="pri_test1"):
    return json.dumps({
        "event_id": event_id, "event_type": event_type,
        "data": {
            "id": "txn_1", "custom_data": {"request_id": "req_1"},
            "items": [{"price": {"id": price_id}}],
            "details": {"totals": {"grand_total": str(amount_cents), "currency_code": currency}},
        },
    }).encode("utf-8")


class TestSignatureVerification(unittest.TestCase):
    def test_valid_signature_verifies(self):
        body = b'{"a":1}'
        header = _sign(body, _FAKE_SECRET)
        self.assertTrue(pw.verify_signature(body, header, _FAKE_SECRET))

    def test_wrong_secret_fails(self):
        body = b'{"a":1}'
        header = _sign(body, _FAKE_SECRET)
        self.assertFalse(pw.verify_signature(body, header, "a_different_secret"))

    def test_tampered_body_fails(self):
        body = b'{"a":1}'
        header = _sign(body, _FAKE_SECRET)
        self.assertFalse(pw.verify_signature(b'{"a":2}', header, _FAKE_SECRET))

    def test_missing_header_fails(self):
        self.assertFalse(pw.verify_signature(b"{}", None, _FAKE_SECRET))

    def test_malformed_header_fails(self):
        self.assertFalse(pw.verify_signature(b"{}", "not-a-real-header", _FAKE_SECRET))

    def test_no_secret_fails(self):
        body = b'{"a":1}'
        header = _sign(body, _FAKE_SECRET)
        self.assertFalse(pw.verify_signature(body, header, None))


class TestProcessPaddleWebhook(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.events_path = os.path.join(self._tmpdir.name, "events.jsonl")
        self.catalog_path = os.path.join(self._tmpdir.name, "catalog.json")
        with open(self.catalog_path, "w", encoding="utf-8") as f:
            json.dump(_CATALOG, f)

    def tearDown(self):
        self._tmpdir.cleanup()

    def _run(self, body, header=None, secret=_FAKE_SECRET):
        header = header if header is not None else _sign(body, secret or _FAKE_SECRET)
        return pw.process_paddle_webhook(body, header, secret=secret,
                                          processed_events_path=self.events_path,
                                          catalog_path=self.catalog_path)

    def test_valid_event_is_accepted(self):
        result = self._run(_valid_payload())
        self.assertEqual(result["status"], "ACCEPTED")

    def test_missing_secret_is_rejected(self):
        result = self._run(_valid_payload(), secret=None)
        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["reason"], "MISSING_SECRET")

    def test_invalid_signature_is_rejected(self):
        result = self._run(_valid_payload(), header="ts=1;h1=deadbeef")
        self.assertEqual(result["reason"], "INVALID_SIGNATURE")

    def test_duplicate_event_is_rejected(self):
        first = self._run(_valid_payload(event_id="evt_dup"))
        self.assertEqual(first["status"], "ACCEPTED")
        second = self._run(_valid_payload(event_id="evt_dup"))
        self.assertEqual(second["reason"], "DUPLICATE_EVENT")

    def test_wrong_product_is_rejected(self):
        result = self._run(_valid_payload(price_id="pri_unknown"))
        self.assertEqual(result["reason"], "PRODUCT_MISMATCH")

    def test_wrong_amount_is_rejected(self):
        result = self._run(_valid_payload(amount_cents=1))
        self.assertEqual(result["reason"], "AMOUNT_MISMATCH")

    def test_wrong_currency_is_rejected(self):
        result = self._run(_valid_payload(currency="EUR"))
        self.assertEqual(result["reason"], "CURRENCY_MISMATCH")

    def test_unknown_event_type_is_rejected(self):
        result = self._run(_valid_payload(event_type="subscription.created"))
        self.assertEqual(result["reason"], "UNKNOWN_EVENT_TYPE")

    def test_replayed_event_is_rejected(self):
        # A "replay" is the same real event_id sent again -- same as duplicate.
        first = self._run(_valid_payload(event_id="evt_replay"))
        self.assertEqual(first["status"], "ACCEPTED")
        replay = self._run(_valid_payload(event_id="evt_replay"))
        self.assertEqual(replay["reason"], "DUPLICATE_EVENT")

    def test_malformed_payload_is_rejected(self):
        body = b"not json at all"
        result = self._run(body)
        self.assertEqual(result["reason"], "MALFORMED_PAYLOAD")

    def test_every_outcome_is_logged(self):
        self._run(_valid_payload(event_id="evt_a"))
        self._run(_valid_payload(event_id="evt_b", price_id="pri_unknown"))
        with open(self.events_path, encoding="utf-8") as f:
            lines = [json.loads(l) for l in f if l.strip()]
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]["status"], "ACCEPTED")
        self.assertEqual(lines[1]["status"], "REJECTED")

    def test_never_writes_to_real_finance_data(self):
        import os as _os
        finance_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "finance_data.json")
        before = _os.path.getmtime(finance_path)
        self._run(_valid_payload())
        after = _os.path.getmtime(finance_path)
        self.assertEqual(before, after)

    def test_accepted_event_never_creates_an_order_itself(self):
        result = self._run(_valid_payload())
        self.assertNotIn("order_id", result)
        self.assertNotIn("customer_id", result)


if __name__ == "__main__":
    unittest.main()
