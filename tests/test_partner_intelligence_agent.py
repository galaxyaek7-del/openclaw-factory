import unittest

import commission_engine as ce
import partner_intelligence_agent as pia


class TestCategorizeEvidenceSource(unittest.TestCase):
    def test_no_url_is_unknown(self):
        result = pia.categorize_evidence_source(None)
        self.assertEqual(result["category"], "UNKNOWN")

    def test_off_domain_url_never_elevated(self):
        result = pia.categorize_evidence_source("https://some-random-blog.com/amazon-review", partner_domain="amazon")
        self.assertEqual(result["category"], "TRUSTED_SECONDARY_SOURCE")

    def test_partner_domain_terms_path_is_official_terms(self):
        result = pia.categorize_evidence_source("https://affiliate-program.amazon.com/help/operating/agreement", partner_domain="amazon")
        self.assertEqual(result["category"], "OFFICIAL_TERMS")

    def test_partner_domain_affiliate_path_is_official_partner_page(self):
        result = pia.categorize_evidence_source("https://amazon.com/affiliate/signup", partner_domain="amazon")
        self.assertEqual(result["category"], "OFFICIAL_PARTNER_PAGE")

    def test_partner_domain_api_subdomain_is_official_api(self):
        result = pia.categorize_evidence_source("https://api.amazon.com/v1/products", partner_domain="amazon")
        self.assertEqual(result["category"], "OFFICIAL_API")

    def test_never_treats_arbitrary_webpage_as_authoritative(self):
        result = pia.categorize_evidence_source("https://randomblog.net/i-heard-amazon-pays-90-percent", partner_domain="amazon")
        self.assertNotIn(result["category"], ("OFFICIAL_PARTNER_PAGE", "OFFICIAL_TERMS", "OFFICIAL_API", "OFFICIAL_PROGRAM_DOCUMENTATION"))


class TestCategorizeOpportunityEvidence(unittest.TestCase):
    def test_real_portfolio_opportunity_categorized(self):
        opp = ce.load_opportunity_portfolio()[0]
        result = pia.categorize_opportunity_evidence(opp)
        self.assertGreater(len(result["sources"]), 0)


class TestDetectPartnerChanges(unittest.TestCase):
    def test_no_change_reports_false(self):
        snap = {"opportunity_id": "X", "commission_value": "10%", "status": "DISCOVERED"}
        result = pia.detect_partner_changes(snap, dict(snap))
        self.assertFalse(result["changed"])

    def test_commission_change_detected(self):
        old = {"opportunity_id": "X", "commission_value": "10%"}
        new = {"opportunity_id": "X", "commission_value": "20%"}
        result = pia.detect_partner_changes(old, new)
        self.assertTrue(result["changed"])
        self.assertEqual(result["changes"][0]["field"], "commission_value")

    def test_program_closed_detected(self):
        old = {"opportunity_id": "X", "status": "DISCOVERED"}
        new = {"opportunity_id": "X", "status": "REJECTED"}
        result = pia.detect_partner_changes(old, new)
        self.assertTrue(result["program_closed"])

    def test_different_opportunity_ids_not_comparable(self):
        result = pia.detect_partner_changes({"opportunity_id": "A"}, {"opportunity_id": "B"})
        self.assertFalse(result["comparable"])


class TestPartnerFreshnessStatus(unittest.TestCase):
    def test_stale_never_presented_as_fresh(self):
        opp = {"opportunity_id": "X", "last_verified": "2020-01-01"}
        result = pia.partner_freshness_status(opp)
        self.assertEqual(result["freshness_status"], "STALE")
        self.assertFalse(result["presented_as_fresh_recommendation"])


class TestComparePartners(unittest.TestCase):
    def test_never_ranks_by_raw_commission_percentage_alone(self):
        portfolio = ce.load_opportunity_portfolio()
        result = pia.compare_partners(portfolio)
        self.assertIn("real_dimensions_count", result["ranked"][0])
        self.assertNotIn("ranked_by_commission_pct", result)

    def test_returns_every_opportunity(self):
        portfolio = ce.load_opportunity_portfolio()
        result = pia.compare_partners(portfolio)
        self.assertEqual(len(result["ranked"]), len(portfolio))


class TestAgentHealth(unittest.TestCase):
    def test_returns_all_named_health_fields(self):
        health = pia.agent_health()
        for field in ("status", "last_run", "last_success", "last_failure", "error_rate",
                      "queue_size", "current_task", "blocked_reason"):
            self.assertIn(field, health)

    def test_empty_portfolio_reports_idle(self):
        health = pia.agent_health(portfolio_path="/nonexistent/path.jsonl")
        self.assertEqual(health["status"], "IDLE")


if __name__ == "__main__":
    unittest.main()
