"""Phase 37C, Section 5 — corroboration_check() regression tests
(ADR-232). Confirms real, mechanical corroboration never manufactured."""

import unittest

from scripts.phase37c_fresh_evidence import corroboration_check


class TestCorroborationCheck(unittest.TestCase):
    def test_no_corroboration_for_a_single_isolated_candidate(self):
        candidates = [{"lead_id": "L1", "website": None, "company_name": "UNKNOWN"}]
        result = corroboration_check(candidates[0], candidates)
        self.assertFalse(result["has_corroboration"])

    def test_shared_canonical_domain_corroborates(self):
        candidates = [
            {"lead_id": "L1", "website": "https://github.com/acme", "company_name": "acme"},
            {"lead_id": "L2", "website": "https://github.com/acme", "company_name": "acme"},
        ]
        result = corroboration_check(candidates[0], candidates)
        self.assertTrue(result["has_corroboration"])
        self.assertIn("L2", result["corroborating_lead_ids"])

    def test_shared_company_name_corroborates_even_without_website(self):
        candidates = [
            {"lead_id": "L1", "website": None, "company_name": "Automattic"},
            {"lead_id": "L2", "website": None, "company_name": "Automattic"},
        ]
        result = corroboration_check(candidates[0], candidates)
        self.assertTrue(result["has_corroboration"])

    def test_unknown_company_name_never_corroborates_with_another_unknown(self):
        """Two different UNKNOWN-company individual posters must never be
        treated as corroborating each other -- that would manufacture
        corroboration out of two unrelated anonymous signals."""
        candidates = [
            {"lead_id": "L1", "website": None, "company_name": "UNKNOWN -- individual poster"},
            {"lead_id": "L2", "website": None, "company_name": "UNKNOWN -- individual poster"},
        ]
        result = corroboration_check(candidates[0], candidates)
        self.assertFalse(result["has_corroboration"])

    def test_different_companies_do_not_corroborate(self):
        candidates = [
            {"lead_id": "L1", "website": "https://github.com/acme", "company_name": "acme"},
            {"lead_id": "L2", "website": "https://github.com/other", "company_name": "other"},
        ]
        result = corroboration_check(candidates[0], candidates)
        self.assertFalse(result["has_corroboration"])


if __name__ == "__main__":
    unittest.main()
