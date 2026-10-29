"""scripts/approve_products.py: records exactly what the publication gate
checks, replaces only the named products' approvals, and is never called by
automation. No real approval file is written."""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import approve_products as ap  # noqa: E402

REQUIRED = ("approval_id", "status", "approved_by", "approval_reference", "approved_at", "expires_at",
            "product_id", "price_cents", "currency", "actions", "revision_sha256")


class ApproveProducts(unittest.TestCase):
    def test_record_has_every_field_the_gate_requires(self):
        from channels import publication_authorization as pa
        m = {"id": "B99-001", "price_cents": 1200, "currency": "USD", "title": "T"}
        orig = pa.product_revision
        pa.product_revision = lambda man, **k: "a" * 64
        try:
            r = ap.build_records([m], "approved in chat 2026-10-30", datetime(2026, 10, 30, 9, 0, tzinfo=timezone.utc), 72)[0]
        finally:
            pa.product_revision = orig
        for f in REQUIRED:
            self.assertIn(f, r)
        self.assertEqual(set(pa.REQUIRED_APPROVAL_FIELDS) - set(r), set())
        self.assertEqual(r["expires_at"], "2026-11-02T09:00:00Z")
        self.assertEqual(r["actions"], ["upload", "publish"])

    def test_merge_replaces_only_the_named_products(self):
        doc = {"approvals": [{"product_id": "A"}, {"product_id": "B", "old": True}]}
        out = ap.merge(doc, [{"product_id": "B"}, {"product_id": "C"}])
        self.assertEqual([a["product_id"] for a in out["approvals"]], ["A", "B", "C"])
        self.assertFalse(any(a.get("old") for a in out["approvals"]))

    def test_a_short_reference_is_refused(self):
        with self.assertRaises(SystemExit):
            ap.main(["--batch", "batch16", "--only", "B16-008", "--reference", "ok"])

    def test_no_automation_calls_it(self):
        for rel in ("factory_loop.js", "server.js", "mission_control_api.py", "scripts/publish_approved_daily.py"):
            p = ROOT / rel
            if p.exists():
                self.assertNotIn("approve_products", p.read_text(encoding="utf-8", errors="replace"), rel)


if __name__ == "__main__":
    unittest.main()
