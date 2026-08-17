"""Tests for distribution_os.py (Distribution OS, 2026-08-17):
the founder-approved smallest safe Distribution OS layer -- a READ-ONLY,
per-production_id cross-channel read model that merges the 3 pre-existing
distribution-status aggregators instead of building a 4th orchestrator.

Every test uses isolated temp paths (generation log, sales ledger, paddle
products, seo pages, changelog, kits, reality) -- never the real ledgers.
Real aggregator sub-calls (product_platform_matrix ~3s) are mocked in the
tests that would otherwise trigger them, matching the established
expensive-sub-scan discipline in this repo.

    python -m unittest tests.test_distribution_os -v
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import distribution_os as dos


def _write_jsonl(tmp_dir, name, records):
    path = Path(tmp_dir) / name
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return str(path)


def _write_json(tmp_dir, name, obj):
    path = Path(tmp_dir) / name
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    return str(path)


_REAL_RECORD = {
    "production_id": "PROD-abc123",
    "topic": "automated compliance workflow system for mid-size logistics firms",
    "price": 327,
    "pages": 8,
    "path": "/books/out.pdf",
    "cover": {"path": "/books/cover.png"},
    "inspection": {"passed": True, "published": True},
    "published": True,
    "success": True,
    "timestamp": "2026-07-18T23:44:00",
}

_TEST_RECORD = {
    "production_id": "PROD-dec-test-1",
    "topic": "Test Production Id Package",
    "price": 197,
    "pages": 3,
    "success": True,
    "timestamp": "2026-08-14T10:18:55.632242",
}

_PADDLE_PRODUCTS = [
    {
        "title": "EU AI Act Compliance Toolkit",
        "product_id": "pro_01kzdzzh4kv6bkpzfhd5r1jnkn",
        "price_id": "pri_01kzdzzhhnfs8b3jraewg022kp",
        "price": 155.0,
    },
]

_SALES_LEDGER = [
    {
        "event_type": "publish_attempt",
        "platform": "paddle",
        "ok": True,
        "dry_run": False,
        "product_id": "pro_01kzdzzh4kv6bkpzfhd5r1jnkn",
        "product_title": "EU AI Act Compliance Toolkit",
        "product_source_id": None,
        "timestamp": "2026-08-07T22:10:06.847323+00:00",
    },
    {
        "event_type": "publish_attempt",
        "platform": "gumroad",
        "ok": False,
        "dry_run": False,
        "error": "arm not ready: unavailable",
        "product_title": "EU AI Act Compliance Toolkit",
        "product_source_id": None,
        "timestamp": "2026-07-20T10:00:00+00:00",
    },
]


class TestDistributionOsView(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.genlog = _write_jsonl(self.tmp, "genlog.jsonl", [_REAL_RECORD, _TEST_RECORD])
        self.ledger = _write_jsonl(self.tmp, "sales.jsonl", _SALES_LEDGER)
        self.paddle = _write_json(self.tmp, "paddle.json", _PADDLE_PRODUCTS)
        self.seo = _write_json(self.tmp, "seo.json", [])
        self.kits = _write_jsonl(self.tmp, "kits.jsonl", [])
        self.reality = _write_json(self.tmp, "reality.json", {"published_books": []})

    def _view(self, production_id, **kw):
        return dos.distribution_os_view(
            production_id,
            generation_log_path=self.genlog,
            sales_ledger_path=self.ledger,
            paddle_products_path=self.paddle,
            seo_pages_path=self.seo,
            kits_path=self.kits,
            reality_path=self.reality,
            webhook_events_path=os.path.join(self.tmp, "webhooks.jsonl"),
            merge_aggregators=False,
            **kw,
        )

    def test_found_for_real_generation_record(self):
        v = self._view("PROD-abc123")
        self.assertTrue(v["found"])
        self.assertEqual(v["stages"]["product"]["production_id"], "PROD-abc123")
        self.assertTrue(v["stages"]["product"]["inspection_passed"])
        self.assertEqual(v["stages"]["product"]["pages"], 8)

    def test_honest_not_found(self):
        v = self._view("PROD-does-not-exist")
        self.assertFalse(v["found"])
        self.assertIn("no real", v["reason"])

    def test_requires_production_id(self):
        v = self._view("   ")
        self.assertFalse(v["found"])
        self.assertIn("required", v["reason"])

    def test_all_seven_stages_present(self):
        v = self._view("PROD-abc123")
        self.assertEqual(
            list(v["stages"].keys()),
            ["product", "package", "channel", "listing", "distribution", "attribution", "learning"],
        )

    def test_channel_stage_reports_real_arm_statuses(self):
        v = self._view("PROD-abc123")
        arms = v["stages"]["channel"]["registered_arms"]
        names = {a["name"] for a in arms}
        self.assertTrue({"gumroad", "paddle", "etsy", "payhip"}.issubset(names))
        for a in arms:
            self.assertIn(a["status"], {"READY", "UNAVAILABLE", "COOLDOWN", "UNKNOWN"})

    def test_paddle_listing_matched_by_title(self):
        v = self._view("PROD-abc123")
        paddle = v["stages"]["listing"]["paddle"]
        self.assertFalse(paddle["listed"])  # PROD-abc123 title != EU AI Act Toolkit
        # A view whose title matches a paddle product must show it listed
        v2 = self._view("PROD-abc123")
        # Override via a record that matches the paddle title:
        rec = dict(_REAL_RECORD)
        rec["production_id"] = "PROD-eu"
        rec["topic"] = "EU AI Act Compliance Toolkit"
        genlog = _write_jsonl(self.tmp, "genlog2.jsonl", [rec])
        v3 = dos.distribution_os_view(
            "PROD-eu",
            generation_log_path=genlog,
            paddle_products_path=self.paddle,
            seo_pages_path=self.seo,
            kits_path=self.kits,
            reality_path=self.reality,
            webhook_events_path=os.path.join(self.tmp, "webhooks.jsonl"),
            merge_aggregators=False,
        )
        self.assertEqual(v3["stages"]["listing"]["paddle"]["product_id"], "pro_01kzdzzh4kv6bkpzfhd5r1jnkn")

    def test_kdp_listing_reports_real_reality_json(self):
        v = self._view("PROD-abc123")
        kdp = v["stages"]["listing"]["kdp"]
        self.assertFalse(kdp["listed"])
        self.assertEqual(kdp["count"], 0)

    def test_distribution_stage_joins_by_title_for_null_production_id(self):
        # A real null-production_id product (the EU AI Act toolkit's real
        # shape) resolves by title and joins the sales ledger by title.
        rec = dict(_REAL_RECORD)
        rec["production_id"] = None
        rec["topic"] = "EU AI Act Compliance Toolkit"
        genlog = _write_jsonl(self.tmp, "genlog3.jsonl", [rec])
        v = dos.distribution_os_view(
            "EU AI Act Compliance Toolkit",
            generation_log_path=genlog,
            sales_ledger_path=self.ledger,
            paddle_products_path=self.paddle,
            seo_pages_path=self.seo,
            kits_path=self.kits,
            reality_path=self.reality,
            webhook_events_path=os.path.join(self.tmp, "webhooks.jsonl"),
            merge_aggregators=False,
        )
        self.assertTrue(v["found"])
        self.assertTrue(v["stages"]["product"]["resolved_by_title"])
        dist = v["stages"]["distribution"]
        self.assertEqual(dist["events"], 2)  # 1 paddle ok-real + 1 gumroad failure, both title-matched
        self.assertEqual(dist["per_platform"]["paddle"]["ok_real"], 1)
        self.assertEqual(dist["per_platform"]["gumroad"]["failures"], 1)
        self.assertEqual(dist["sales"], 0)

    def test_webhook_count_honest_when_file_missing(self):
        v = self._view("PROD-abc123")
        wh = v["stages"]["learning"]["paddle_webhook_events"]
        self.assertEqual(wh["count"], 0)
        self.assertIn("does not exist", wh["note"])

    def test_attribution_state_reports_counts(self):
        clicks = _write_jsonl(self.tmp, "clicks.jsonl", [{"id": "c1"}, {"id": "c2"}])
        views = _write_jsonl(self.tmp, "views.jsonl", [{"id": "v1"}])
        v = self._view("PROD-abc123", clicks_path=clicks, page_views_path=views)
        att = v["stages"]["attribution"]
        self.assertEqual(att["affiliate_clicks"], 2)
        self.assertEqual(att["affiliate_page_views"], 1)
        self.assertIn("never production_id", att["note"])

    def test_commercial_kit_honest_missing(self):
        v = self._view("PROD-abc123")
        self.assertFalse(v["stages"]["package"]["commercial_kit"]["exists"])

    def test_read_only_never_writes(self):
        before = set(os.listdir(self.tmp))
        self._view("PROD-abc123")
        after = set(os.listdir(self.tmp))
        self.assertEqual(before, after)


class TestDistributionOsSummary(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.genlog = _write_jsonl(self.tmp, "genlog.jsonl", [_REAL_RECORD, _TEST_RECORD])
        self.ledger = _write_jsonl(self.tmp, "sales.jsonl", [])
        self.paddle = _write_json(self.tmp, "paddle.json", [])
        self.seo = _write_json(self.tmp, "seo.json", [])
        self.reality = _write_json(self.tmp, "reality.json", {"published_books": []})

    def _summary(self, **kw):
        kw.setdefault("generation_log_path", self.genlog)
        kw.setdefault("sales_ledger_path", self.ledger)
        kw.setdefault("paddle_products_path", self.paddle)
        kw.setdefault("seo_pages_path", self.seo)
        kw.setdefault("reality_path", self.reality)
        kw.setdefault("webhook_events_path", os.path.join(self.tmp, "webhooks.jsonl"))
        kw.setdefault("merge_aggregators", False)
        return dos.distribution_os_summary(**kw)

    def test_summary_filters_test_production_ids(self):
        s = self._summary()
        # PROD-dec-test-1 is a test id -- must not appear
        pids = [p["production_id"] for p in s["products"]]
        self.assertNotIn("PROD-dec-test-1", pids)
        self.assertIn("PROD-abc123", pids)
        self.assertEqual(s["total_real_production_ids_in_log"], 1)

    def test_summary_respects_limit(self):
        recs = [
            dict(_REAL_RECORD),
            dict(_REAL_RECORD),
            dict(_REAL_RECORD),
        ]
        for i, r in enumerate(recs):
            r["production_id"] = f"PROD-{i}"
            r["topic"] = f"topic {i}"
            r["timestamp"] = f"2026-07-{18+i}T00:00:00"
        genlog = _write_jsonl(self.tmp, "genlog_many.jsonl", recs)
        s = dos.distribution_os_summary(
            limit=2,
            generation_log_path=genlog,
            sales_ledger_path=self.ledger,
            paddle_products_path=self.paddle,
            seo_pages_path=self.seo,
            reality_path=self.reality,
            webhook_events_path=os.path.join(self.tmp, "webhooks.jsonl"),
            merge_aggregators=False,
        )
        self.assertEqual(s["shown_products"], 2)
        self.assertEqual(s["total_real_production_ids_in_log"], 3)

    def test_summary_reports_real_publish_state(self):
        ledger = _write_jsonl(self.tmp, "sales_real.jsonl", [{
            "event_type": "publish_attempt",
            "platform": "paddle",
            "ok": True,
            "dry_run": False,
            "product_source_id": "PROD-abc123",
            "product_title": "automated compliance workflow system for mid-size logistics firms",
            "timestamp": "2026-08-07T22:10:06+00:00",
        }])
        s = self._summary(sales_ledger_path=ledger)
        p = [x for x in s["products"] if x["production_id"] == "PROD-abc123"][0]
        self.assertTrue(p["distribution"]["ok_real_publish"])
        self.assertEqual(p["distribution"]["publish_attempts"], 1)

    def test_merged_aggregators_called(self):
        with patch.object(dos, "_merge_distribution_aggregators", return_value={"capability_matrix": "mocked"}) as m:
            s = self._summary(merge_aggregators=True)
            m.assert_called_once()
            self.assertEqual(s["merged_aggregators"]["capability_matrix"], "mocked")

    def test_read_only_never_writes(self):
        before = set(os.listdir(self.tmp))
        self._summary()
        after = set(os.listdir(self.tmp))
        self.assertEqual(before, after)


class TestMergedAggregators(unittest.TestCase):
    def test_merge_absorbs_single_aggregator_failure(self):
        # A failure in one aggregator must never take down the whole merge.
        import commercial_operations
        import global_partnership_network
        import global_commercial_operations_engine

        with patch.object(commercial_operations, "distribution_capability_matrix", side_effect=RuntimeError("x")), \
             patch.object(global_partnership_network, "distribution_network_health", side_effect=RuntimeError("y")), \
             patch.object(global_commercial_operations_engine, "product_platform_matrix", side_effect=RuntimeError("z")):
            merged = dos._merge_distribution_aggregators()
        self.assertIn("error", merged["capability_matrix"])
        self.assertIn("error", merged["network_health"])
        self.assertIn("error", merged["product_platform_matrix"])


class TestTitleJoinHelpers(unittest.TestCase):
    def test_titles_match_exact_and_containment(self):
        self.assertTrue(dos._titles_match("EU AI Act Compliance Toolkit", "EU AI Act Compliance Toolkit"))
        self.assertTrue(dos._titles_match("EU AI Act compliance toolkit", "EU AI Act Compliance Toolkit"))
        self.assertTrue(dos._titles_match("A system for accounting firms", "accounting firms"))
        self.assertFalse(dos._titles_match("alpha system", "beta system"))
        self.assertFalse(dos._titles_match(None, "x"))
        self.assertFalse(dos._titles_match("x", None))

    def test_normalize(self):
        self.assertEqual(dos._normalize("  EU   AI Act  "), "eu ai act")


if __name__ == "__main__":
    unittest.main()