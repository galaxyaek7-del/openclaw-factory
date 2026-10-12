"""C81 — targeted regression tests for the confirmed Paddle webhook
idempotency defect (a transient rejection permanently burned an event_id,
losing a real paid sale).

Covers:
  - the defect itself (recovery now works)
  - the anti-duplicate guarantee is NOT weakened
  - a permanently-invalid event still cannot be smuggled through
  - rejected events are still fully logged
  - a malformed/garbage ledger line cannot break idempotency
"""
import json, hmac, hashlib, tempfile, unittest, sys, os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from channels import paddle_webhook as pw

# Locally generated, clearly-fake secret. Never a real credential.
_FAKE_SECRET = "c81-unit-test-secret-not-real"


def _sign(body_bytes, secret, ts="1760000000"):
    h1 = hmac.new(secret.encode(), (ts + ":").encode() + body_bytes, hashlib.sha256).hexdigest()
    return f"ts={ts};h1={h1}"


def _payload(event_id="evt_1", price_id="pri_c81", amount="15500",
             currency="USD", event_type="transaction.completed"):
    return json.dumps({
        "event_type": event_type,
        "event_id": event_id,
        "data": {
            "id": "txn_c81",
            "items": [{"price": {"id": price_id}}],
            "details": {"totals": {"grand_total": amount, "currency_code": currency}},
        },
    }).encode()


class TestTransientRejectionNoLongerBurnsEventId(unittest.TestCase):
    """The confirmed defect: one transient rejection must not make a real
    paid sale permanently unrecordable."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.led = self.tmp / "events.jsonl"
        self.cat = self.tmp / "catalog.json"
        self._write_catalog()

    def _write_catalog(self):
        self.cat.write_text(json.dumps(
            [{"price_id": "pri_c81", "price": 155.0, "product_id": "pro_c81"}]), encoding="utf-8")

    def _process(self, body):
        return pw.process_paddle_webhook(
            body, _sign(body, _FAKE_SECRET), secret=_FAKE_SECRET,
            processed_events_path=self.led, catalog_path=self.cat)

    def test_retry_after_transient_catalog_failure_is_accepted(self):
        body = _payload(event_id="evt_transient")
        self.cat.unlink()                                  # transient: catalog not synced yet
        first = self._process(body)
        self.assertEqual(first["status"], "REJECTED")
        self.assertEqual(first["reason"], "PRODUCT_MISMATCH")

        self._write_catalog()                              # system self-heals
        retry = self._process(body)                        # Paddle's real retry
        self.assertEqual(retry["status"], "ACCEPTED",
                         "a real paid sale must be recoverable after a transient rejection")

    def test_true_duplicate_of_accepted_event_is_still_rejected(self):
        body = _payload(event_id="evt_true_dup")
        self.assertEqual(self._process(body)["status"], "ACCEPTED")
        dup = self._process(body)
        self.assertEqual(dup["reason"], "DUPLICATE_EVENT",
                         "anti-duplicate guarantee must not be weakened")
        accepted = [json.loads(l) for l in self.led.read_text(encoding="utf-8").splitlines()
                    if json.loads(l)["status"] == "ACCEPTED"]
        self.assertEqual(len(accepted), 1, "never two ACCEPTED records for one event_id")

    def test_repeated_transient_failures_never_produce_a_second_accept(self):
        body = _payload(event_id="evt_flip")
        self.assertEqual(self._process(body)["status"], "ACCEPTED")
        for _ in range(3):
            self._process(body)
        accepted = [json.loads(l) for l in self.led.read_text(encoding="utf-8").splitlines()
                    if json.loads(l)["status"] == "ACCEPTED"]
        self.assertEqual(len(accepted), 1)

    def test_permanently_invalid_event_is_still_rejected_every_time(self):
        """A genuinely bad event (wrong amount) must NOT become acceptable
        just because rejections no longer poison the idempotency set."""
        body = _payload(event_id="evt_bad_amount", amount="1")
        for _ in range(3):
            r = self._process(body)
            self.assertEqual(r["status"], "REJECTED")
            self.assertEqual(r["reason"], "AMOUNT_MISMATCH")
        self.assertFalse(any(
            json.loads(l)["status"] == "ACCEPTED"
            for l in self.led.read_text(encoding="utf-8").splitlines()))

    def test_permanently_wrong_price_is_still_rejected_every_time(self):
        body = _payload(event_id="evt_bad_price", price_id="pri_not_real")
        for _ in range(3):
            self.assertEqual(self._process(body)["reason"], "PRODUCT_MISMATCH")

    def test_rejected_events_are_still_fully_logged(self):
        """Section 6's logging requirement is unchanged by the fix."""
        good = _payload(event_id="evt_ok")
        bad = _payload(event_id="evt_bad", price_id="pri_not_real")
        self._process(good)
        self._process(bad)
        records = [json.loads(l) for l in self.led.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(records), 2)
        self.assertEqual([r["status"] for r in records], ["ACCEPTED", "REJECTED"])
        # the rejected one is still on disk with its event_id, for audit
        self.assertEqual(records[1]["event_id"], "evt_bad")

    def test_corrupt_ledger_line_does_not_break_idempotency(self):
        good = _payload(event_id="evt_after_corruption")
        self.assertEqual(self._process(good)["status"], "ACCEPTED")
        with open(self.led, "a", encoding="utf-8") as f:
            f.write("{this is not json\n")
        dup = self._process(good)
        self.assertEqual(dup["reason"], "DUPLICATE_EVENT")

    def test_never_writes_real_finance_data(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        fin = Path(root) / "finance_data.json"
        before = fin.stat().st_mtime
        self._process(_payload(event_id="evt_nofin"))
        self.assertEqual(fin.stat().st_mtime, before)

    def test_signature_still_required(self):
        body = _payload(event_id="evt_sig")
        r = pw.process_paddle_webhook(body, "ts=1760000000;h1=deadbeef",
                                      secret=_FAKE_SECRET,
                                      processed_events_path=self.led,
                                      catalog_path=self.cat)
        self.assertEqual(r["reason"], "INVALID_SIGNATURE")


if __name__ == "__main__":
    unittest.main(verbosity=2)