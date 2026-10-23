"""scripts/publish_batch14.py: only reviewed, unchanged bundles are
published, every publish is read back and verified, and the run stops at
the first failure. No network: Gumroad, scopes, ledger and HTTP are fakes."""
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import publish_batch14 as pb  # noqa: E402


def manifest(tmp, ok=True, tamper=False, price=1500):
    b = Path(tmp) / "bundle.zip"
    b.write_bytes(b"bundle-bytes")
    digest = hashlib.sha256(b.read_bytes()).hexdigest()
    if tamper:
        b.write_bytes(b"changed-after-qa")
    return {"id": "B14-099", "slug": "x", "title": "Test Tool", "price_cents": price,
            "files": {"bundle": {"path": str(b), "sha256": digest}},
            "qa": {"ok": ok, "listing": {"description_html": "<p>d</p>"}}}


class FakeGumroad:
    NEW_PRODUCT = "NEW_PRODUCT"

    def __init__(self, readback=None, published=True):
        self.calls, self.readback, self.published = [], readback, published

    def create_product(self, token, spec, upload_scope_id=None):
        self.calls.append(("create", spec["title"], upload_scope_id))
        return {"id": "p1"}

    def get_product(self, token, pid):
        self.calls.append(("get", pid))
        base = {"name": "Test Tool", "price": 1500, "published": self.published, "short_url": "https://x.gumroad.com/l/t", "covers": []}
        return dict(base, **(self.readback or {}))

    def enable_product(self, token, pid):
        self.calls.append(("enable", pid))
        self.published = True

    def add_product_cover(self, token, pid, url, expected_cover_count=None):
        # same contract as channels/gumroad_publisher.add_product_cover: the
        # re-read count must grow past expected_cover_count (the count before)
        self.calls.append(("cover", url))
        if expected_cover_count is not None and 1 <= expected_cover_count:
            raise RuntimeError("VERIFICATION_FAILED: cover count did not grow")


class Fakes:
    def __init__(self):
        self.scopes, self.events = [], []
        self.write_scope = SimpleNamespace(issue_scope=lambda **kw: self.scopes.append(kw) or SimpleNamespace(scope_id="s1"))
        self.ledger = SimpleNamespace(record_publish_attempt=lambda p, r: self.events.append((p, r)))


def page(body="<title>Test Tool</title>", status=200):
    return lambda req, timeout=30: SimpleNamespace(status=status, read=lambda: body.encode())


class TestPreflight(unittest.TestCase):
    def test_unreviewed_or_changed_bundles_are_refused(self):
        t = tempfile.mkdtemp()
        self.assertFalse(pb.preflight(manifest(t, ok=False), root=Path("/"))[0])
        self.assertIn("changed since QA", pb.preflight(manifest(t, tamper=True), root=Path("/"))[1])
        self.assertFalse(pb.preflight(manifest(t, price=50), root=Path("/"))[0])
        self.assertTrue(pb.preflight(manifest(t), root=Path("/"))[0])


class TestPublishOne(unittest.TestCase):
    def run_one(self, gp, opener=page()):
        f = Fakes()
        m = manifest(tempfile.mkdtemp())
        orig = pb.preflight
        pb.preflight = lambda man, root=None: orig(man, root=Path("/"))
        try:
            rec = pb.publish_one(m, "tok", gp=gp, write_scope=f.write_scope, ledger=f.ledger,
                                 cover_url_fn=lambda i: f"https://c/{i}.png", opener=opener)
        finally:
            pb.preflight = orig
        return rec, f

    def test_happy_path_scopes_the_upload_verifies_and_records(self):
        gp = FakeGumroad()
        rec, f = self.run_one(gp)
        self.assertTrue(rec["ok"], rec)
        self.assertEqual(f.scopes[0]["operation"], "upload_file")
        self.assertEqual(set(f.scopes[0]["payload"]), {"file_path"})  # bound to the exact bundle, nothing else
        self.assertTrue(f.scopes[0]["payload"]["file_path"].endswith("bundle.zip"))
        self.assertEqual(gp.calls[0], ("create", "Test Tool", "s1"))
        self.assertIn(("cover", "https://c/B14-099.png"), gp.calls)
        self.assertFalse(f.events[0][1].dry_run)
        self.assertTrue(f.events[0][1].ok)

    def test_price_mismatch_on_read_back_stops_before_cover_and_ledger(self):
        gp = FakeGumroad(readback={"price": 999})
        rec, f = self.run_one(gp)
        self.assertIn("read-back mismatch", rec["error"])
        self.assertNotIn("cover", [c[0] for c in gp.calls])
        self.assertEqual(f.events, [])

    def test_unpublished_create_is_enabled_and_rechecked(self):
        gp = FakeGumroad(published=False)
        rec, _ = self.run_one(gp)
        self.assertIn(("enable", "p1"), gp.calls)
        self.assertTrue(rec["steps"]["published"])

    def test_public_page_must_show_the_title(self):
        rec, f = self.run_one(FakeGumroad(), opener=page(body="<title>Something else</title>"))
        self.assertFalse(rec["ok"])
        self.assertFalse(f.events[0][1].ok)

    def test_html_escaped_title_still_matches(self):
        gp = FakeGumroad(readback={"name": "Test Tool"})
        rec, _ = self.run_one(gp, opener=page(body="<h1>Test Tool &amp; More</h1>"))
        self.assertTrue(rec["steps"]["public_page"])


if __name__ == "__main__":
    unittest.main()
