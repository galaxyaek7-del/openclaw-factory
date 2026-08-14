"""Tests for affiliate_router.py — the Golden Hunter <-> Affiliate bridge.

The router must be deterministic, never fabricate a program match, and
only produce a positive "affiliate" route from real VERIFIED affiliate
programs in the on-disk portfolio.

    python -m unittest tests.test_affiliate_router -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from affiliate_router import route_niche, route_many, routing_summary
from commission_engine import load_opportunity_portfolio


def _temp_routing_path():
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(path)
    return path


class TestNicheMatching(unittest.TestCase):
    def test_automation_niche_routes_to_zapier_or_n8n(self):
        # Use the REAL on-disk portfolio so the match must be against real
        # VERIFIED programs (no synthetic fixture that could mask a bug).
        d = route_niche(
            "AI agent workflow automation for small businesses",
            record=False,
        )
        self.assertEqual(d.route, "affiliate")
        self.assertIn("CO-zapier-affiliate", d.matched_programs)
        self.assertIn("CO-n8n-affiliate", d.matched_programs)
        self.assertIn("اختبر مسار Affiliate", d.reason)

    def test_design_niche_routes_to_canva_or_adobe_only_if_verified(self):
        d = route_niche("graphic design templates for social media", record=False)
        # The route must only include programs that are VERIFIED in the real
        # portfolio — a THIRD_PARTY_ONLY program (CO-canva-affiliate) must
        # never appear as a positive match.
        self.assertNotIn("CO-canva-affiliate", d.matched_programs)

    def test_unrelated_niche_returns_unknown_not_fabricated(self):
        d = route_niche("industrial robotic arm calibration", record=False)
        self.assertEqual(d.route, "unknown")
        self.assertNotIn("fabricate", d.reason.lower())

    def test_record_optional_logs_append_only(self):
        path = _temp_routing_path()
        try:
            d = route_niche("workflow automation for agencies", record=True, routing_path=path)
            self.assertEqual(d.route, "affiliate")
            rows = [l for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
            self.assertEqual(len(rows), 1)
            self.assertIn("workflow automation for agencies", rows[0])
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_unverified_program_never_produces_positive_route(self):
        # Canva is THIRD_PARTY_ONLY in the real portfolio: a design niche
        # matching Canva keywords must still not route to Canva positively.
        d = route_niche("design assets and mockups for branding", record=False)
        if "CO-canva-affiliate" in d.matched_programs:
            self.fail("unverified program leaked into matched_programs")
        self.assertIn(d.route, ("unknown", "affiliate"))


class TestRouteMany(unittest.TestCase):
    def test_batch_routing_preserves_order_and_counts(self):
        niches = [
            "workflow automation for logistics",
            "industrial machine calibration",
            "social media graphic templates",
        ]
        decisions = route_many(niches, record=False)
        self.assertEqual(len(decisions), 3)
        self.assertEqual([d.niche for d in decisions], niches)
        summary = routing_summary(decisions)
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["by_route"]["unknown"], 1)
        self.assertIn("affiliate", summary["by_route"])
        # Every 'affiliate' route must carry real matched programs.
        for d in decisions:
            if d.route == "affiliate":
                self.assertTrue(d.matched_programs)


class TestRouterAgainstRealPortfolio(unittest.TestCase):
    def test_portfolio_has_verified_affiliate_programs_to_route_to(self):
        # The router is only useful if the real portfolio actually contains
        # VERIFIED affiliate programs — a regression guard.
        portfolio = load_opportunity_portfolio()
        verified_aff = [
            o for o in portfolio
            if o.get("verification_status") == "VERIFIED" and o.get("category") == "affiliate"
        ]
        self.assertGreater(len(verified_aff), 0,
                           "no VERIFIED affiliate program exists — router can never route")


if __name__ == "__main__":
    unittest.main()
