"""Phase 37A, Sections 24-26 -- integration tests (ADR-230). Golden
Hunter -> Partner Intelligence -> Commercial Deal Agent -> Lead
Discovery, and Lead Outreach Agent -> Outreach Adapter (draft only,
never send). Every test is isolated, zero live network calls."""

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import commercial_deal_agent as cda
import lead_outreach_agent as loa

OPPORTUNITY = {
    "opportunity_id": "CO-n8n-affiliate", "partner_id": "n8n", "product_or_service": "n8n",
    "program_name": "n8n affiliate", "partner_name": "n8n", "verification_status": "VERIFIED",
    "commission_value": "30%", "recurring_commission": True,
}
CUSTOMER_PROFILE = {"industry": "agency", "budget": "UNKNOWN"}


def _fake_hn_with_hit(q, limit=10):
    return [{"author": "dev1", "title": "manual workflow pain", "url": "https://example.com/p", "objectID": "1",
             "created_at": "2026-08-01T00:00:00.000Z", "story_text": "connecting apps by hand is a nightmare"}], 1


def _fake_hn_empty(q, limit=10):
    return [], 0


def _fake_gh_empty(q, limit=10):
    return [], 0


class TestGoldenHunterToCommercialDealAgentChain(unittest.TestCase):
    """Section 24: Golden Hunter -> Partner Intelligence -> Commercial
    Deal Agent -> Lead Discovery. Golden Hunter itself never appears in
    this chain (it only ever produces the opportunity/niche input,
    confirmed by direct grep this session) -- this test proves the
    downstream half: a real opportunity (as Partner Intelligence would
    verify it) flows into Commercial Deal Agent -> Lead Discovery
    without any function in the chain sending outreach."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.now = datetime(2026, 8, 8, tzinfo=timezone.utc)

    def test_recommend_prospect_chains_match_deal_and_discovery(self):
        result = cda.recommend_prospect(
            OPPORTUNITY, CUSTOMER_PROFILE, problem_keywords=["workflow", "manual", "connecting apps"],
            leads_path=self.tmp / "leads.jsonl", dnc_path=self.tmp / "dnc.jsonl", events_path=self.tmp / "events.jsonl",
            hn_query_fn=_fake_hn_with_hit, github_query_fn=_fake_gh_empty, now=self.now,
        )
        self.assertIsNotNone(result["RECOMMENDED_PROSPECT"])
        self.assertIn("deal", result)
        self.assertIn("discovery", result)
        # An HN-sourced lead is an individual poster with an honestly
        # UNKNOWN company_name -- this correctly, honestly triggers a
        # real disclosed risk (unconfirmed business entity) rather than
        # an over-eager PROCEED_TO_OUTREACH_DRAFT.
        self.assertEqual(result["RECOMMENDED_ACTION"], "GATHER_MORE_EVIDENCE_BEFORE_OUTREACH")
        self.assertTrue(any("company identity is unconfirmed" in r for r in result["RISKS"]))

    def test_recommend_prospect_never_sends_anything(self):
        import inspect
        source = inspect.getsource(cda.recommend_prospect)
        self.assertNotIn(".send(", source)
        self.assertNotIn("smtplib", source)

    def test_proceed_to_outreach_draft_when_a_real_company_signal_exists(self):
        def _fake_gh_with_org_hit(q, limit=10):
            return [{"user": {"login": "alice"}, "title": "manual workflow pain point",
                      "body": "connecting apps by hand is a nightmare", "html_url": "https://github.com/acme/repo/issues/1",
                      "created_at": "2026-08-01T00:00:00.000Z", "repository_url": "https://api.github.com/repos/acme/repo", "id": 111}], 1

        result = cda.recommend_prospect(
            OPPORTUNITY, CUSTOMER_PROFILE, problem_keywords=["workflow", "manual", "connecting apps"],
            leads_path=self.tmp / "leads3.jsonl", dnc_path=self.tmp / "dnc3.jsonl", events_path=self.tmp / "events3.jsonl",
            hn_query_fn=_fake_hn_empty, github_query_fn=_fake_gh_with_org_hit, now=self.now,
        )
        self.assertEqual(result["RECOMMENDED_ACTION"], "PROCEED_TO_OUTREACH_DRAFT")
        self.assertEqual(result["RISKS"], ["no additional real risk identified beyond standard evidence limitations"])

    def test_no_qualified_candidate_returns_honest_no_prospect(self):
        result = cda.recommend_prospect(
            OPPORTUNITY, CUSTOMER_PROFILE, problem_keywords=["workflow"],
            leads_path=self.tmp / "leads2.jsonl", dnc_path=self.tmp / "dnc2.jsonl", events_path=self.tmp / "events2.jsonl",
            hn_query_fn=_fake_hn_empty, github_query_fn=_fake_gh_empty, now=self.now,
        )
        self.assertIsNone(result["RECOMMENDED_PROSPECT"])
        self.assertEqual(result["RECOMMENDED_ACTION"], "RETRY_DISCOVERY_LATER_OR_EXPAND_SOURCES")


class TestGoldenHunterNeverSendsOutreachItself(unittest.TestCase):
    def test_market_hunter_module_has_no_outreach_import(self):
        import inspect
        import market_hunter as mh
        source = inspect.getsource(mh)
        self.assertNotIn("import outreach_engine", source)
        self.assertNotIn("import outreach_adapter", source)
        self.assertNotIn("import lead_discovery", source)


class TestLeadOutreachAgentPreparesButNeverSends(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.now = datetime(2026, 8, 8, tzinfo=timezone.utc)
        self.lead = {"lead_id": "LEAD-abc123", "industry": "agency", "problem_signal": "manual workflow pain"}

    def test_prepare_outreach_for_lead_returns_a_draft_not_a_sent_message(self):
        result = loa.prepare_outreach_for_lead(OPPORTUNITY, self.lead, channel="email",
                                                log_path=self.tmp / "drafts.jsonl", now=self.now)
        self.assertEqual(result["state"], "DRAFT")
        self.assertIn("REQUIRES real CEO approval", result["next_step"])

    def test_prepare_outreach_for_lead_never_calls_send(self):
        import inspect
        source = inspect.getsource(loa.prepare_outreach_for_lead)
        self.assertNotIn(".send(", source)


if __name__ == "__main__":
    unittest.main()
