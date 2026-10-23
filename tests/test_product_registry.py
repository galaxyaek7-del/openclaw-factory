"""product_registry.py: stable internal ids, evidence-only states, drift.
Pure functions on fixtures; no network."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import product_registry as pr  # noqa: E402

LIVE = [
    {"id": "g1", "name": "Tool A", "price": 1900, "published": True, "short_url": "u1", "sales_count": 0},
    {"id": "g2", "name": "Old Guide", "price": 2900, "published": True, "short_url": "u2", "sales_count": 0},
    {"id": "g3", "name": "Old Guide", "price": 2900, "published": True, "short_url": "u3", "sales_count": 2},
    {"id": "g4", "name": "Hidden", "price": 900, "published": False, "short_url": "u4", "sales_count": 0},
]
CATALOG = [{"id": "g2", "channel": "Gumroad"}, {"id": "g3", "channel": "Gumroad"}, {"id": "g4", "channel": "Gumroad"},
           {"id": "gone", "channel": "Gumroad"}, {"id": "kdp1", "channel": "KDP (pending)"}]
MANIFESTS = [
    {"id": "B14-001", "title": "Tool A", "price_cents": 1900, "qa": {"ok": True}, "_path": "books/batch14/B14-001/manifest.json"},
    {"id": "B14-002", "title": "Tool B", "price_cents": 2400, "qa": {"ok": True}, "_path": "books/batch14/B14-002/manifest.json"},
]
PUBLISHED = {"g1": {"internal_id": "B14-001", "public_page": True}}


def build(previous=None, live=LIVE):
    return pr.build(live, CATALOG, MANIFESTS, PUBLISHED, previous)


class TestIdentity(unittest.TestCase):
    def test_factory_id_kept_and_others_derived_deterministically(self):
        reg = build()
        ids = {r["external_ids"].get("gumroad"): r["internal_id"] for r in reg["products"]}
        self.assertEqual(ids["g1"], "B14-001")
        self.assertEqual(ids["g2"], pr.derived_id("g2"))
        self.assertEqual(build()["products"], reg["products"], "same inputs, same registry")

    def test_ids_survive_a_rename_and_are_never_reused(self):
        reg = build()
        renamed = [dict(p, name="Tool A v2") if p["id"] == "g1" else p for p in LIVE]
        reg2 = build(previous=reg, live=renamed)
        self.assertEqual(next(r for r in reg2["products"] if r["external_ids"].get("gumroad") == "g1")["internal_id"], "B14-001")
        ids = [r["internal_id"] for r in reg2["products"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_duplicate_listing_cannot_take_a_factory_id_twice(self):
        live = LIVE + [{"id": "g5", "name": "Tool A", "price": 1900, "published": True, "short_url": "u5", "sales_count": 0}]
        ids = [r["internal_id"] for r in build(live=live)["products"]]
        self.assertEqual(ids.count("B14-001"), 1)


class TestStates(unittest.TestCase):
    def state(self, gid, reg=None):
        reg = reg or build()
        return next(r for r in reg["products"] if r["external_ids"].get("gumroad") == gid)["primary_state"]

    def test_states_come_from_evidence_only(self):
        self.assertEqual(self.state("g1"), "PUBLIC_LISTING_VERIFIED")   # published + public page checked
        self.assertEqual(self.state("g2"), "UPLOAD_COMPLETED")          # published, no page check on record
        self.assertEqual(self.state("g3"), "FIRST_SALE_VERIFIED")       # platform sales_count > 0
        self.assertEqual(self.state("g4"), "UPLOAD_COMPLETED")
        unlisted = next(r for r in build()["products"] if r["internal_id"] == "B14-002")
        self.assertEqual(unlisted["primary_state"], "READY_FOR_AUTHORIZATION")
        self.assertEqual(unlisted["external_ids"], {})

    def test_failed_qa_manifest_is_only_build_complete(self):
        mans = MANIFESTS[:1] + [dict(MANIFESTS[1], qa={"ok": False})]
        reg = pr.build(LIVE, CATALOG, mans, PUBLISHED, None)
        self.assertEqual(next(r for r in reg["products"] if r["internal_id"] == "B14-002")["primary_state"], "BUILD_COMPLETE")


class TestDrift(unittest.TestCase):
    def test_drift_lists_every_difference(self):
        reg = build()
        d = pr.drift(reg, LIVE, CATALOG, MANIFESTS)
        self.assertEqual(d["live_missing_from_catalog"], ["B14-001"])
        self.assertEqual(d["catalog_rows_not_live"], ["gone"])          # KDP row is not a Gumroad listing
        self.assertEqual(d["duplicate_live_titles"], ["Old Guide"])
        self.assertEqual(d["qa_passed_not_listed"], ["B14-002"])
        self.assertEqual(d["unpublished_on_platform"], [pr.derived_id("g4")])
        self.assertEqual(d["manifest_live_mismatch"], [])

    def test_price_changed_on_platform_is_reported(self):
        live = [dict(p, price=2500) if p["id"] == "g1" else p for p in LIVE]
        reg = pr.build(live, CATALOG, MANIFESTS, PUBLISHED, None)
        d = pr.drift(reg, live, CATALOG, MANIFESTS)
        self.assertEqual(d["manifest_live_mismatch"][0]["internal_id"], "B14-001")


if __name__ == "__main__":
    unittest.main()


class TestPageEvidence(unittest.TestCase):
    def test_fresh_passing_page_check_upgrades_state_and_stale_one_does_not(self):
        from datetime import datetime, timedelta, timezone
        now = datetime(2026, 10, 23, tzinfo=timezone.utc)
        checks = {"g2": {"checked_at": (now - timedelta(days=1)).isoformat(), "ok": True},
                  "g4": {"checked_at": (now - timedelta(days=1)).isoformat(), "ok": True},
                  "g3": {"checked_at": (now - timedelta(days=30)).isoformat(), "ok": True}}
        fresh = pr.fresh_page_checks(checks, now)
        self.assertEqual(set(fresh), {"g2", "g4"})
        reg = pr.build(LIVE, CATALOG, MANIFESTS, PUBLISHED, None, fresh)
        st = {r["external_ids"].get("gumroad"): r["primary_state"] for r in reg["products"]}
        self.assertEqual(st["g2"], "PUBLIC_LISTING_VERIFIED")
        self.assertEqual(st["g4"], "UPLOAD_COMPLETED", "an unpublished listing is never verified by a page check")

    def test_verify_pages_requires_200_and_title(self):
        from types import SimpleNamespace
        pages = {"https://x.test/u1": (200, "<title>Tool A</title>"), "https://x.test/u2": (200, "<title>Not it</title>"),
                 "https://x.test/u3": (404, "")}
        live = [dict(p, short_url="https://x.test/" + p["short_url"]) for p in LIVE]

        def opener(req, timeout=20):
            st, body = pages[req.full_url]
            return SimpleNamespace(status=st, read=lambda: body.encode())
        res = pr.verify_pages(live, opener=opener)
        self.assertTrue(res["g1"]["ok"])
        self.assertFalse(res["g2"]["ok"])
        self.assertFalse(res["g3"]["ok"])
        self.assertNotIn("g4", res, "unpublished listings are not checked")


class TestTransientErrors(unittest.TestCase):
    def test_throttling_is_retried_and_never_replaces_an_earlier_result(self):
        import json
        import tempfile
        import urllib.error
        from types import SimpleNamespace
        calls = []

        def opener(req, timeout=20):
            calls.append(req.full_url)
            raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", None, None)
        live = [{"id": "g1", "name": "Tool A", "price": 1900, "published": True, "short_url": "https://x.test/u1", "sales_count": 0}]
        res = pr.verify_pages(live, opener=opener, retry_wait=0)
        self.assertEqual(len(calls), 2, "one retry after a 429")
        self.assertTrue(res["g1"]["transient"])
        d = tempfile.mkdtemp()
        checks = Path(d) / "checks.json"
        checks.write_text(json.dumps({"g1": {"checked_at": "2026-10-23T00:00:00+00:00", "ok": True}}))
        orig = pr.verify_pages
        pr.verify_pages = lambda live, opener=None: {"g1": {"checked_at": "x", "ok": False, "transient": True}}
        try:
            pr.run(write=True, live=live, registry_path=Path(d) / "reg.json", catalog_path=Path(d) / "none.json",
                   check_pages=True, page_checks_path=checks)
        finally:
            pr.verify_pages = orig
        self.assertTrue(json.loads(checks.read_text())["g1"]["ok"])
