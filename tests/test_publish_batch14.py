"""scripts/publish_batch14.py: a live write needs its own founder approval,
every binding is re-checked, and a failure never retries or stops later
products. No network: Gumroad, scopes, ledger and HTTP are fakes."""
import hashlib
import json
import os
import sys
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import publish_batch14 as pb  # noqa: E402
from channels import publication_authorization as pa  # noqa: E402


def _write_xlsx(path):
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("xl/workbook.xml", "<workbook/>")


def _write_guide(path, title="Test Tool", disclaimer="This is not financial advice."):
    from reportlab.pdfgen import canvas
    pdf = canvas.Canvas(str(path))
    pdf.drawString(72, 720, title)
    pdf.drawString(72, 700, disclaimer)
    pdf.save()


def _write_cover(path):
    from PIL import Image
    Image.new("RGB", (1280, 720), (30, 80, 120)).save(path, format="PNG")


def manifest(tmp, ok=True, tamper=False, price=1500, currency="USD",
             description=None, tags=None, category="Finance", pricing_evidence=True):
    base = Path(tmp)
    slug = "test-tool"
    workbook = base / "tool.xlsx"
    guide = base / "guide.pdf"
    cover = base / "cover.png"
    bundle = base / "bundle.zip"
    _write_xlsx(workbook)
    _write_guide(guide)
    _write_cover(cover)
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.write(workbook, f"{slug}/{workbook.name}")
        archive.write(guide, f"{slug}/{guide.name}")
        archive.writestr(f"{slug}/README.txt", "read me")

    def entry(path):
        return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "bytes": path.stat().st_size}

    files = {
        "workbook": entry(workbook),
        "guide": entry(guide),
        "cover": entry(cover),
        "bundle": entry(bundle),
    }
    if tamper:
        bundle.write_bytes(b"changed-after-qa")
    if description is None:
        description = (
            "<p>This tool helps a small business compare two real options and see the "
            "break-even point clearly. It explains every input and every output so the "
            "result can be checked by hand. It is a decision aid, not a promise of a "
            "particular outcome.</p>"
            "<p><strong>What's included</strong></p><ul><li>A calculator workbook</li>"
            "<li>A worked example</li><li>A PDF guide</li></ul>"
            "<p><strong>Who it's for</strong></p><ul><li>Small business owners</li>"
            "<li>Operators comparing two offers</li></ul>"
            "<p>Use Excel 2016 or later, Excel for Mac, Excel on the web, Google Sheets "
            "or LibreOffice. The workbook uses standard formulas and no macros.</p>"
            "<p><em>This workbook is a comparison tool, not financial, lending or tax "
            "advice. Check any decision against your own documents and a qualified "
            "adviser.</em></p>"
        )
    return {
        "id": "B14-099",
        "slug": slug,
        "title": "Test Tool",
        "price_cents": price,
        "currency": currency,
        "tags": tags if tags is not None else ["small-business", "calculator"],
        "category": category,
        "pricing_evidence": {"basis": "reviewed comparable products"} if pricing_evidence else None,
        "files": files,
        "qa": {
            "ok": ok,
            "file_test": {"status": "PASS", "problems": []},
            "recalc": {"checked": 10, "failed": []},
            "guide": {"pages": 1, "title_found": True, "disclaimer_found": True},
            "cover": {"size": [1280, 720]},
            "brand": {"passed": True, "failed_checks": [], "listing_chars": len(description)},
            "bundle": {"files": [f"{slug}/{workbook.name}", f"{slug}/{guide.name}", f"{slug}/README.txt"],
                       "corrupt_member": None},
            "listing": {"description_html": description},
        },
    }


def approval_for(man, **overrides):
    now = datetime.now(timezone.utc)
    record = {
        "approval_id": "GF-TEST-01",
        "status": "APPROVED",
        "approved_by": "founder",
        "approval_reference": "test approval",
        "approved_at": (now - timedelta(minutes=5)).isoformat(),
        "expires_at": (now + timedelta(days=1)).isoformat(),
        "product_id": man["id"],
        "price_cents": man["price_cents"],
        "currency": man["currency"],
        "actions": ["upload", "publish"],
        "revision_sha256": pa.product_revision(man),
    }
    record.update(overrides)
    return record


class FakeGumroad:
    NEW_PRODUCT = "NEW_PRODUCT"

    def __init__(self, readback=None, published=True, create_error=None, fail_first=False):
        self.calls = []
        self.readback = readback
        self.published = published
        self.create_error = create_error
        self.fail_first = fail_first
        self.create_count = 0

    def create_product(self, token, spec, upload_scope_id=None):
        self.calls.append(("create", spec["title"], upload_scope_id))
        self.create_count += 1
        if self.create_error and (not self.fail_first or self.create_count == 1):
            raise RuntimeError(self.create_error)
        return {"id": "p1"}

    def get_product(self, token, pid):
        self.calls.append(("get", pid))
        base = {"name": "Test Tool", "price": 1500, "published": self.published,
                "short_url": "https://x.gumroad.com/l/t", "covers": []}
        return dict(base, **(self.readback or {}))

    def enable_product(self, token, pid):
        self.calls.append(("enable", pid))
        self.published = True

    def add_product_cover(self, token, pid, url, expected_cover_count=None):
        self.calls.append(("cover", url))


class Fakes:
    def __init__(self):
        self.scopes, self.events = [], []
        self.write_scope = SimpleNamespace(
            issue_scope=lambda **kw: self.scopes.append(kw) or SimpleNamespace(scope_id="s1")
        )
        self.ledger = SimpleNamespace(
            record_publish_attempt=lambda p, r: self.events.append((p, r))
        )


def page(body="<title>Test Tool</title>", status=200):
    return lambda req, timeout=30: SimpleNamespace(status=status, read=lambda: body.encode())


def registry_ready():
    return {"internal_id": "B14-099", "published": False, "external_ids": {}}


class TestPreflight(unittest.TestCase):
    def test_unreviewed_or_changed_bundles_are_refused(self):
        t = tempfile.mkdtemp()
        self.assertFalse(pb.preflight(manifest(t, ok=False), root=Path("/"))[0])
        self.assertIn("changed since QA", pb.preflight(manifest(t, tamper=True), root=Path("/"))[1])
        self.assertFalse(pb.preflight(manifest(t, price=50), root=Path("/"))[0])
        self.assertTrue(pb.preflight(manifest(t), root=Path("/"))[0])

    def test_audit_holds_on_missing_metadata_and_disclaimer(self):
        m = manifest(tempfile.mkdtemp(), tags=[], description="<p>Too short, no disclaimer.</p>")
        audit = pb.audit_product(m, registry_entry=registry_ready())
        self.assertEqual(audit["status"], "HOLD")
        self.assertEqual(audit["checks"]["metadata"]["status"], "UNKNOWN")
        self.assertEqual(audit["checks"]["listing"]["status"], "HOLD")
        self.assertEqual(audit["checks"]["authorization"]["status"], "HOLD")

    def test_audit_passes_complete_product_with_approval(self):
        m = manifest(tempfile.mkdtemp())
        audit = pb.audit_product(
            m,
            registry_entry=registry_ready(),
            approvals=[approval_for(m)],
        )
        self.assertEqual(audit["status"], "PASS", audit)
        self.assertEqual(audit["authorization"]["status"], "VALID")

    def test_malformed_approval_record_is_blocked_not_held(self):
        m = manifest(tempfile.mkdtemp())
        record = dict(approval_for(m))
        record.pop("expires_at")
        audit = pb.audit_product(m, registry_entry=registry_ready(), approvals=[record])
        self.assertEqual(audit["status"], "BLOCKED")
        self.assertEqual(audit["checks"]["authorization"]["status"], "FAIL")
        self.assertEqual(audit["authorization"]["status"], "INVALID")
        self.assertTrue(audit["status_reason"].startswith("authorization:"))

    def test_duplicate_approval_records_are_blocked(self):
        m = manifest(tempfile.mkdtemp())
        rec = approval_for(m)
        audit = pb.audit_product(m, registry_entry=registry_ready(), approvals=[rec, rec])
        self.assertEqual(audit["status"], "BLOCKED")
        self.assertEqual(audit["authorization"]["status"], "AMBIGUOUS")


class TestPublishOne(unittest.TestCase):
    def run_one(self, gp, opener=page(), approvals=None):
        f = Fakes()
        m = manifest(tempfile.mkdtemp())
        rec = pb.publish_one(
            m,
            "tok",
            gp=gp,
            write_scope=f.write_scope,
            ledger=f.ledger,
            cover_url_fn=lambda i: f"https://c/{i}.png",
            approvals=approvals if approvals is not None else [approval_for(m)],
            registry_entry=registry_ready(),
            opener=opener,
            sleep=lambda _seconds: None,
        )
        return rec, f, m

    def test_happy_path_scopes_the_upload_verifies_and_records(self):
        gp = FakeGumroad()
        rec, f, _m = self.run_one(gp)
        self.assertEqual(rec["status"], "PASS", rec)
        self.assertEqual(f.scopes[0]["operation"], "upload_file")
        self.assertEqual(set(f.scopes[0]["payload"]), {"file_path"})
        self.assertTrue(f.scopes[0]["payload"]["file_path"].endswith("bundle.zip"))
        self.assertIn("GF-TEST-01", f.scopes[0]["note"])
        self.assertEqual(gp.calls[0], ("create", "Test Tool", "s1"))
        self.assertIn(("cover", "https://c/B14-099.png"), gp.calls)
        self.assertFalse(f.events[0][1].dry_run)
        self.assertTrue(f.events[0][1].ok)

    def test_missing_approval_blocks_before_any_write(self):
        gp = FakeGumroad()
        with self.assertRaises(pb.PublicationBlocked) as caught:
            self.run_one(gp, approvals=[])
        self.assertIn("HOLD", str(caught.exception))
        self.assertEqual(gp.calls, [])

    def test_wrong_price_blocks_before_any_write(self):
        gp = FakeGumroad()
        f = Fakes()
        m = manifest(tempfile.mkdtemp())
        with self.assertRaises(pb.PublicationBlocked):
            pb.publish_one(
                m, "tok", gp=gp, write_scope=f.write_scope, ledger=f.ledger,
                cover_url_fn=lambda i: "https://c/x.png",
                approvals=[approval_for(m, price_cents=999)],
                registry_entry=registry_ready(), sleep=lambda _seconds: None,
            )
        self.assertEqual(gp.calls, [])

    def test_cross_product_approval_blocks_before_any_write(self):
        gp = FakeGumroad()
        f = Fakes()
        m = manifest(tempfile.mkdtemp())
        other = manifest(tempfile.mkdtemp())
        with self.assertRaises(pb.PublicationBlocked):
            pb.publish_one(
                m, "tok", gp=gp, write_scope=f.write_scope, ledger=f.ledger,
                cover_url_fn=lambda i: "https://c/x.png",
                approvals=[approval_for(other)],
                registry_entry=registry_ready(), sleep=lambda _seconds: None,
            )
        self.assertEqual(gp.calls, [])

    def test_dry_run_never_reaches_a_write(self):
        gp = FakeGumroad()
        f = Fakes()
        m = manifest(tempfile.mkdtemp())
        with self.assertRaises(pb.PublicationBlocked):
            pb.publish_one(
                m, "tok", gp=gp, write_scope=f.write_scope, ledger=f.ledger,
                cover_url_fn=lambda i: "https://c/x.png",
                approvals=[approval_for(m)], registry_entry=registry_ready(),
                live=False,
            )
        self.assertEqual(gp.calls, [])

    def test_metadata_gap_blocks_even_with_a_valid_approval(self):
        gp = FakeGumroad()
        f = Fakes()
        m = manifest(tempfile.mkdtemp(), tags=[])
        with self.assertRaises(pb.PublicationBlocked) as caught:
            pb.publish_one(
                m, "tok", gp=gp, write_scope=f.write_scope, ledger=f.ledger,
                cover_url_fn=lambda i: "https://c/x.png",
                approvals=[approval_for(m)], registry_entry=registry_ready(),
                sleep=lambda _seconds: None,
            )
        self.assertIn("HOLD", str(caught.exception))
        self.assertEqual(gp.calls, [])

    def test_price_mismatch_on_read_back_stops_before_cover_and_ledger(self):
        gp = FakeGumroad(readback={"price": 999})
        rec, f, _m = self.run_one(gp)
        self.assertEqual(rec["status"], "BLOCKED")
        self.assertIn("read-back mismatch", rec["error"])
        self.assertNotIn("cover", [c[0] for c in gp.calls])
        self.assertEqual(f.events, [])

    def test_unpublished_create_is_enabled_and_rechecked(self):
        gp = FakeGumroad(published=False)
        rec, _f, _m = self.run_one(gp)
        self.assertIn(("enable", "p1"), gp.calls)
        self.assertTrue(rec["steps"]["published"])

    def test_public_page_must_show_the_title(self):
        rec, f, _m = self.run_one(FakeGumroad(), opener=page(body="<title>Something else</title>"))
        self.assertEqual(rec["status"], "BLOCKED")
        self.assertFalse(f.events[0][1].ok)

    def test_html_escaped_title_still_matches(self):
        rec, _f, _m = self.run_one(
            FakeGumroad(readback={"name": "Test Tool"}),
            opener=page(body="<h1>Test Tool &amp; More</h1>"),
        )
        self.assertTrue(rec["steps"]["public_page"])


class TestRunBatch(unittest.TestCase):
    def test_failure_does_not_stop_later_products_and_is_not_retried(self):
        first = manifest(tempfile.mkdtemp())
        second = manifest(tempfile.mkdtemp())
        second["id"] = "B14-100"
        second["slug"] = "second"
        first["id"], first["slug"] = "B14-099", "first"
        approvals = [approval_for(first), approval_for(second)]
        gp = FakeGumroad(create_error="Sorry, you can only create 10 products per day.",
                         fail_first=True)
        f = Fakes()
        registry = {
            "B14-099": registry_ready(),
            "B14-100": dict(registry_ready(), internal_id="B14-100"),
        }
        results = pb.run_batch(
            [first, second],
            live=True,
            approvals=approvals,
            registry=registry,
            gp=gp,
            write_scope=f.write_scope,
            ledger=f.ledger,
            token="tok",
            auth_poll=lambda: {"status": "VERIFIED", "at": datetime.now(timezone.utc).isoformat()},
            cover_url_fn=lambda i: f"https://c/{i}.png",
            opener=page(),
            sleep=lambda _seconds: None,
        )
        self.assertEqual(len(results), 2)
        self.assertEqual([r["status"] for r in results], ["BLOCKED", "PASS"])
        self.assertIn("10 products per day", results[0]["status_reason"])
        self.assertEqual(len(gp.calls), 4)
        self.assertEqual([c[0] for c in gp.calls].count("create"), 2)
        self.assertEqual(len(f.events), 1)

    def test_dry_run_never_calls_gumroad_even_with_live_flag(self):
        m = manifest(tempfile.mkdtemp())
        gp = FakeGumroad()
        f = Fakes()
        old = os.environ.get("FACTORY_LIVE_PUBLISH")
        os.environ["FACTORY_LIVE_PUBLISH"] = "true"
        try:
            results = pb.run_batch(
                [m], live=False, approvals=[approval_for(m)], registry={"B14-099": registry_ready()},
                gp=gp, write_scope=f.write_scope, ledger=f.ledger, token="tok",
            )
        finally:
            if old is None:
                os.environ.pop("FACTORY_LIVE_PUBLISH", None)
            else:
                os.environ["FACTORY_LIVE_PUBLISH"] = old
        self.assertEqual(results[0]["status"], "PASS")
        self.assertEqual(gp.calls, [])
        self.assertEqual(f.scopes, [])
        self.assertEqual(f.events, [])

    def test_malformed_approval_file_produces_no_writes(self):
        m = manifest(tempfile.mkdtemp())
        gp = FakeGumroad()
        f = Fakes()
        results = pb.run_batch(
            [m], live=True, approvals=None,
            approvals_error=pa.MalformedApproval("duplicate key"),
            gp=gp, write_scope=f.write_scope, ledger=f.ledger, token="tok",
        )
        self.assertEqual(results[0]["status"], "BLOCKED")
        self.assertEqual(gp.calls, [])

    def test_missing_approval_file_produces_no_writes(self):
        m = manifest(tempfile.mkdtemp())
        gp = FakeGumroad()
        f = Fakes()
        results = pb.run_batch(
            [m], live=True, approvals=None,
            approvals_error=pa.MissingApproval("no file"),
            gp=gp, write_scope=f.write_scope, ledger=f.ledger, token="tok",
        )
        self.assertEqual(results[0]["status"], "BLOCKED")
        self.assertEqual(gp.calls, [])

    def test_stale_auth_produces_no_writes(self):
        m = manifest(tempfile.mkdtemp())
        gp = FakeGumroad()
        f = Fakes()
        old = datetime.now(timezone.utc) - timedelta(hours=2)
        results = pb.run_batch(
            [m], live=True, approvals=[approval_for(m)], registry={"B14-099": registry_ready()},
            gp=gp, write_scope=f.write_scope, ledger=f.ledger, token="tok",
            auth_poll=lambda: {"status": "VERIFIED", "at": old.isoformat()},
        )
        self.assertEqual(results[0]["status"], "BLOCKED")
        self.assertEqual(gp.calls, [])

class CreationBudgetTests(unittest.TestCase):
    """Gumroad's real 10-per-day cap, measured live on 2026-10-28.

    The window is rolling 24 hours: ten creations recorded on 2026-10-27 at
    12:41-12:46Z were still blocking an attempt at 06:29Z the next morning.
    """

    def _results(self, records):
        directory = tempfile.mkdtemp()
        path = Path(directory) / "results.json"
        path.write_text(json.dumps(records), encoding="utf-8")
        return [path]

    def _live(self, at, ids, create="ok"):
        return {
            "at": at,
            "mode": "LIVE",
            "results": [{"id": i, "steps": {"create": create, "published": True}} for i in ids],
        }

    def test_counts_only_real_creations_inside_the_window(self):
        paths = self._results([
            self._live("2026-10-27T12:41:16Z", ["B15-001", "B15-003"]),
            self._live("2026-10-27T12:46:19Z", ["B15-002"]),
            self._live("2026-10-27T13:00:00Z", ["B15-011"], create="FAILED"),
            {"at": "2026-10-27T13:10:00Z", "mode": "DRY_RUN", "results": [{"id": "X", "steps": {"create": "ok"}}]},
            self._live("not-a-timestamp", ["B15-012"]),
        ])
        blocked_moment = pb._record_epoch("2026-10-27T14:00:00Z")
        self.assertEqual(pb.creations_in_window(paths, now_ts=blocked_moment), 3)
        after_window = pb._record_epoch("2026-10-28T13:00:00Z")
        self.assertEqual(pb.creations_in_window(paths, now_ts=after_window), 0)

    def test_the_real_blocked_moment_is_reproduced(self):
        paths = self._results([
            self._live("2026-10-27T12:41:16Z", ["B15-001", "B15-003", "B15-004", "B15-005",
                                                "B15-006", "B15-007", "B15-008", "B15-009",
                                                "B15-010"]),
            self._live("2026-10-27T12:46:19Z", ["B15-002"]),
        ])
        real_blocked_at = pb._record_epoch("2026-10-28T06:29:02Z")
        self.assertEqual(pb.creations_in_window(paths, now_ts=real_blocked_at), 10,
                         "the ten creations were still inside the rolling 24h window")
        later = pb._record_epoch("2026-10-28T16:02:18Z")
        self.assertEqual(pb.creations_in_window(paths, now_ts=later), 0,
                         "27.3 hours later the window has cleared")


if __name__ == "__main__":
    unittest.main()
