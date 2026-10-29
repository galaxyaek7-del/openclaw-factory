"""Fail-closed publication authorization tests (no network, no writes to data/)."""
import hashlib
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from channels import publication_authorization as pa  # noqa: E402


def make_product(tmp, *, product_id="B15-001", price=1500, currency="USD",
                 tags=None, category="Finance", description="<p>Useful tool. Not financial advice.</p>"):
    base = Path(tmp)
    files = {}
    for key, filename, payload in (
        ("bundle", "bundle.zip", b"bundle-bytes"),
        ("workbook", "workbook.xlsx", b"workbook-bytes"),
        ("guide", "guide.pdf", b"%PDF-guide"),
        ("cover", "cover.png", b"\x89PNG\r\n\x1a\ncover"),
    ):
        path = base / filename
        path.write_bytes(payload)
        files[key] = {"path": str(path), "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}
    return {
        "id": product_id,
        "slug": "test-product",
        "title": "Test Product",
        "price_cents": price,
        "currency": currency,
        "tags": tags if tags is not None else ["finance"],
        "category": category,
        "files": files,
        "qa": {"listing": {"description_html": description}},
    }


def make_approval(product, *, revision=None, **overrides):
    now = datetime.now(timezone.utc)
    record = {
        "approval_id": "GF-B15-001-01",
        "status": "APPROVED",
        "approved_by": "founder",
        "approval_reference": "founder message 2026-10-25",
        "approved_at": (now - timedelta(minutes=5)).isoformat(),
        "expires_at": (now + timedelta(days=1)).isoformat(),
        "product_id": product["id"],
        "price_cents": product["price_cents"],
        "currency": product["currency"],
        "actions": ["upload", "publish"],
        "revision_sha256": revision or pa.product_revision(product),
    }
    record.update(overrides)
    return record


class TestRevision(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.product = make_product(self.tmp)

    def test_revision_is_stable(self):
        self.assertEqual(pa.product_revision(self.product), pa.product_revision(self.product))

    def test_file_change_changes_revision(self):
        before = pa.product_revision(self.product)
        Path(self.product["files"]["bundle"]["path"]).write_bytes(b"changed")
        self.assertNotEqual(before, pa.product_revision(self.product))

    def test_description_change_changes_revision(self):
        before = pa.product_revision(self.product)
        self.product["qa"]["listing"]["description_html"] = "<p>different</p>"
        self.assertNotEqual(before, pa.product_revision(self.product))

    def test_missing_currency_cannot_be_bound(self):
        self.product["currency"] = ""
        with self.assertRaises(pa.ProductRevisionError):
            pa.product_revision(self.product)

    def test_missing_file_cannot_be_bound(self):
        Path(self.product["files"]["bundle"]["path"]).unlink()
        with self.assertRaises(pa.ProductRevisionError):
            pa.product_revision(self.product)


class TestValidate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.product = make_product(self.tmp)
        self.revision = pa.product_revision(self.product)

    def test_valid_approval(self):
        record = make_approval(self.product, revision=self.revision)
        accepted = pa.validate_approval(record, self.product, required_actions=("upload", "publish"))
        self.assertEqual(accepted["approval_id"], record["approval_id"])
        self.assertEqual(accepted["actions"], ["upload", "publish"])
        self.assertEqual(accepted["revision_sha256"], self.revision)

    def test_missing_record(self):
        with self.assertRaises(pa.MissingApprovalRecord):
            pa.require_approval([], self.product)

    def test_wrong_product(self):
        record = make_approval(self.product, revision=self.revision, product_id="B15-002")
        with self.assertRaises(pa.ApprovalRefused):
            pa.validate_approval(record, self.product)

    def test_wildcard_product_is_refused(self):
        record = make_approval(self.product, revision=self.revision, product_id="*")
        with self.assertRaises(pa.ApprovalRefused):
            pa.validate_approval(record, self.product)

    def test_wrong_price(self):
        record = make_approval(self.product, revision=self.revision, price_cents=999)
        with self.assertRaises(pa.ApprovalRefused):
            pa.validate_approval(record, self.product)

    def test_wrong_currency(self):
        record = make_approval(self.product, revision=self.revision, currency="EUR")
        with self.assertRaises(pa.ApprovalRefused):
            pa.validate_approval(record, self.product)

    def test_missing_required_action(self):
        record = make_approval(self.product, revision=self.revision, actions=["upload"])
        with self.assertRaises(pa.ApprovalRefused):
            pa.validate_approval(record, self.product, required_actions=("upload", "publish"))

    def test_unknown_action(self):
        record = make_approval(self.product, revision=self.revision, actions=["upload", "delete"])
        with self.assertRaises(pa.MalformedApproval):
            pa.validate_approval(record, self.product)

    def test_both_shorthand(self):
        record = make_approval(self.product, revision=self.revision, actions="both")
        accepted = pa.validate_approval(record, self.product, required_actions="both")
        self.assertEqual(accepted["actions"], ["upload", "publish"])

    def test_expired(self):
        now = datetime.now(timezone.utc)
        record = make_approval(
            self.product,
            revision=self.revision,
            approved_at=(now - timedelta(hours=2)).isoformat(),
            expires_at=(now - timedelta(hours=1)).isoformat(),
        )
        with self.assertRaises(pa.ApprovalRefused):
            pa.validate_approval(record, self.product)

    def test_future_dated(self):
        now = datetime.now(timezone.utc)
        record = make_approval(
            self.product,
            revision=self.revision,
            approved_at=(now + timedelta(hours=1)).isoformat(),
            expires_at=(now + timedelta(hours=2)).isoformat(),
        )
        with self.assertRaises(pa.ApprovalRefused):
            pa.validate_approval(record, self.product)

    def test_stale(self):
        now = datetime.now(timezone.utc)
        record = make_approval(
            self.product,
            revision=self.revision,
            approved_at=(now - timedelta(hours=2)).isoformat(),
            expires_at=(now + timedelta(hours=1)).isoformat(),
        )
        with self.assertRaises(pa.ApprovalRefused):
            pa.validate_approval(record, self.product, max_age_seconds=60)

    def test_revision_mismatch(self):
        record = make_approval(self.product, revision="0" * 64)
        with self.assertRaises(pa.ApprovalRefused):
            pa.validate_approval(record, self.product)

    def test_malformed_revision(self):
        record = make_approval(self.product, revision="not-a-digest")
        with self.assertRaises(pa.MalformedApproval):
            pa.validate_approval(record, self.product)

    def test_revoked(self):
        record = make_approval(self.product, revision=self.revision, revoked_at="2026-10-25T00:00:00Z")
        with self.assertRaises(pa.ApprovalRefused):
            pa.validate_approval(record, self.product)

    def test_not_approved(self):
        record = make_approval(self.product, revision=self.revision, status="PENDING")
        with self.assertRaises(pa.ApprovalRefused):
            pa.validate_approval(record, self.product)

    def test_non_founder(self):
        record = make_approval(self.product, revision=self.revision, approved_by="agent")
        with self.assertRaises(pa.ApprovalRefused):
            pa.validate_approval(record, self.product)

    def test_missing_field(self):
        record = make_approval(self.product, revision=self.revision)
        del record["approval_reference"]
        with self.assertRaises(pa.MalformedApproval):
            pa.validate_approval(record, self.product)

    def test_amendments_do_not_change_founder_approval(self):
        record = make_approval(self.product, revision=self.revision)
        self.assertNotIn("approved_by", pa.validate_approval(record, self.product))


class TestFilesAndSessions(unittest.TestCase):
    def test_missing_file(self):
        with self.assertRaises(pa.MissingApproval):
            pa.load_approvals("/definitely/not/here.json")

    def test_malformed_json(self):
        path = Path(tempfile.mkdtemp()) / "approvals.json"
        path.write_text("{not json", encoding="utf-8")
        with self.assertRaises(pa.MalformedApproval):
            pa.load_approvals(path)

    def test_duplicate_json_keys(self):
        path = Path(tempfile.mkdtemp()) / "approvals.json"
        path.write_text('{"approvals": [], "approvals": []}', encoding="utf-8")
        with self.assertRaises(pa.MalformedApproval):
            pa.load_approvals(path)

    def test_ambiguous_product(self):
        product = {"id": "B15-001"}
        records = [{"product_id": "B15-001"}, {"product_id": "B15-001"}]
        with self.assertRaises(pa.AmbiguousApproval):
            pa.select_approval(records, product["id"])

    def test_session_fresh(self):
        state = {"status": "VERIFIED", "at": datetime.now(timezone.utc).isoformat()}
        self.assertEqual(pa.assert_session_fresh(state)["status"], "VERIFIED")

    def test_session_stale(self):
        old = datetime.now(timezone.utc) - timedelta(hours=2)
        with self.assertRaises(pa.StaleSession):
            pa.assert_session_fresh({"status": "VERIFIED", "at": old.isoformat()})

    def test_session_not_verified(self):
        with self.assertRaises(pa.StaleSession):
            pa.assert_session_fresh({"status": "EXPIRED", "at": datetime.now(timezone.utc).isoformat()})

    def test_approval_file_round_trip(self):
        product = make_product(tempfile.mkdtemp())
        path = Path(tempfile.mkdtemp()) / "approvals.json"
        path.write_text(json.dumps({"approvals": [make_approval(product)]}), encoding="utf-8")
        approvals = pa.load_approvals(path)
        accepted = pa.require_approval(approvals, product)
        self.assertEqual(accepted["product_id"], product["id"])


if __name__ == "__main__":
    unittest.main()
