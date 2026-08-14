"""Tests for affiliate_content_factory.py — honest, deterministic, zero-fabrication
affiliate content generation (directive section 5).

    python -m unittest tests.test_affiliate_content_factory -v
"""

import os
import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from affiliate_content_factory import (
    AffiliateContentInput,
    build_affiliate_content,
    from_portfolio_opportunity,
)
from commission_engine import load_opportunity_portfolio


def _inp(**kwargs):
    defaults = dict(
        opportunity_id="CO-test-affiliate",
        program_name="Test Program",
        product_category="test category",
        solves_problem="choosing the right tool",
        target_audience="small businesses",
        verified_usage=False,
    )
    defaults.update(kwargs)
    return AffiliateContentInput(**defaults)


class TestContentChain(unittest.TestCase):
    def test_full_chain_has_all_five_formats(self):
        pieces = build_affiliate_content(_inp())
        formats = [p.format for p in pieces]
        self.assertEqual(formats, ["educational", "comparison", "usecase", "tutorial", "recommendation"])

    def test_every_piece_has_disclosure(self):
        for p in build_affiliate_content(_inp()):
            self.assertIn("إفصاح", p.disclosure)
            self.assertIn("Affiliate", p.disclosure)

    def test_deterministic_same_input_same_output(self):
        a = build_affiliate_content(_inp())
        b = build_affiliate_content(_inp())
        self.assertEqual([p.body for p in a], [p.body for p in b])

    def test_no_usage_claim_when_not_verified(self):
        pieces = build_affiliate_content(_inp(verified_usage=False))
        for p in pieces:
            self.assertNotIn("استخدمنا", p.body)
        usecase = next(p for p in pieces if p.format == "usecase")
        self.assertIn("لم نختبر", usecase.body)
        self.assertIn("لا ندّعي تجربة", usecase.body)

    def test_usage_claim_only_when_verified(self):
        pieces = build_affiliate_content(_inp(verified_usage=True))
        usecase = next(p for p in pieces if p.format == "usecase")
        self.assertIn("استخدمنا", usecase.body)


class TestPortfolioAdapter(unittest.TestCase):
    def test_adapter_uses_only_real_portfolio_fields(self):
        portfolio = load_opportunity_portfolio()
        aweber = next(o for o in portfolio if o.get("opportunity_id") == "CO-aweber-affiliate")
        pieces = from_portfolio_opportunity(aweber, verified_usage=False)
        self.assertEqual(len(pieces), 5)
        for p in pieces:
            self.assertIn("AWeber", p.title + p.body)
        # Disclosure must carry the real commission value.
        disc = pieces[0].disclosure
        self.assertIn("30% recurring", disc)


if __name__ == "__main__":
    unittest.main()