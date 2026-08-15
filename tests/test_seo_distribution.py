"""Tests for seo_distribution.py — the autonomous SEO distribution engine.

Validates: real-opportunity-driven pages, honest disclosure, idempotency,
no duplicate registry entries, and resilience to missing data. Uses a temp
directory (never touches the real data/ or customer_site/)."""

import json
import tempfile
import unittest
from pathlib import Path

import seo_distribution as sd


def _make_opp(opp_id="CO-digitalocean-affiliate", program="DigitalOcean Affiliate Program",
              problem="Needs cheap cloud infrastructure", audience="Developers"):
    return {
        "opportunity_id": opp_id,
        "program_name": program,
        "partner_name": "DigitalOcean",
        "target_customer": audience,
        "customer_problem": problem,
        "product_or_service": "cloud infrastructure",
        "commission_value": "10 percent recurring",
        "recurring_commission": True,
        "minimum_conditions": "Apply via Awin",
        "verification": "VERIFIED",
        "founder_action": "Complete Awin application",
    }


class SeoDistributionTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._root = Path(self._tmp.name)
        (self._root / "data").mkdir()
        (self._root / "customer_site").mkdir()
        self._orig_root = sd._FACTORY_ROOT
        sd._FACTORY_ROOT = self._root
        sd._COMMISSION_OPPORTUNITIES = self._root / "data" / "commission_opportunities.jsonl"
        sd._SEO_PAGES_REGISTRY = self._root / "data" / "seo_pages.json"
        sd._CUSTOMER_SITE_DIR = self._root / "customer_site"

    def tearDown(self):
        sd._FACTORY_ROOT = self._orig_root
        sd._COMMISSION_OPPORTUNITIES = self._orig_root / "data" / "commission_opportunities.jsonl"
        sd._SEO_PAGES_REGISTRY = self._orig_root / "data" / "seo_pages.json"
        sd._CUSTOMER_SITE_DIR = self._orig_root / "customer_site"
        self._tmp.cleanup()

    def _write_opps(self, opps):
        with open(sd._COMMISSION_OPPORTUNITIES, "w", encoding="utf-8") as f:
            for o in opps:
                f.write(json.dumps(o) + "\n")

    def test_publishes_real_opportunity_pages(self):
        self._write_opps([_make_opp()])
        r = sd.publish_seo_pages()
        self.assertEqual(r["published_count"], 1)
        self.assertEqual(r["failed_count"], 0)
        page = sd._CUSTOMER_SITE_DIR / "guide-digitalocean-affiliate-program.html"
        self.assertTrue(page.exists())
        content = page.read_text(encoding="utf-8")
        self.assertIn("DigitalOcean", content)
        self.assertIn("awaiting founder approval", content.lower())

    def test_idempotent_no_duplicate_registry(self):
        self._write_opps([_make_opp()])
        sd.publish_seo_pages()
        sd.publish_seo_pages()
        registry = json.loads(sd._SEO_PAGES_REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(len(registry), 1)
        self.assertEqual(registry[0]["page"], "/site/guide-digitalocean-affiliate-program.html")

    def test_skips_opportunity_without_problem(self):
        self._write_opps([_make_opp(problem="")])
        r = sd.publish_seo_pages()
        self.assertEqual(r["published_count"], 0)

    def test_multiple_opportunities(self):
        self._write_opps([_make_opp(), _make_opp("CO-n8n-affiliate", "n8n affiliate", "Needs workflow automation", "Teams")])
        r = sd.publish_seo_pages()
        self.assertEqual(r["published_count"], 2)
        self.assertEqual(r["registry_count"], 2)

    def test_empty_opportunities_is_safe(self):
        self._write_opps([])
        r = sd.publish_seo_pages()
        self.assertEqual(r["published_count"], 0)
        self.assertEqual(r["failed_count"], 0)

    def test_disclosure_honest_when_no_founder_action(self):
        opp = _make_opp()
        opp["founder_action"] = ""
        self._write_opps([opp])
        sd.publish_seo_pages()
        content = (sd._CUSTOMER_SITE_DIR / "guide-digitalocean-affiliate-program.html").read_text(encoding="utf-8")
        self.assertIn("no commission is collected from this page today", content.lower())


if __name__ == "__main__":
    unittest.main()