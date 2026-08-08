"""Phase 37A, Section 10 — Lead Discovery test suite (ADR-230).

Every test uses injected fake query functions -- zero live network
calls, matching this factory's established testing discipline. Every
test uses an isolated tempfile path -- never the real default
data/leads.jsonl.
"""

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import lead_discovery as ld

OPPORTUNITY = {"opportunity_id": "CO-n8n-affiliate", "product_or_service": "n8n", "verification_status": "VERIFIED"}


def _hn_hit(author="dev1", title="manual workflow pain", url="https://example.com/post", oid="1", created_at="2026-08-01T00:00:00.000Z", text="hate connecting apps by hand"):
    return {"author": author, "title": title, "url": url, "objectID": oid, "created_at": created_at, "story_text": text}


class LeadDiscoveryTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.leads_path = self.tmp / "leads.jsonl"
        self.dnc_path = self.tmp / "dnc.jsonl"
        self.events_path = self.tmp / "events.jsonl"
        self.now = datetime(2026, 8, 8, tzinfo=timezone.utc)

    def _discover(self, hn_hits=None, gh_hits=None, **kwargs):
        hn_hits = hn_hits if hn_hits is not None else [_hn_hit()]
        gh_hits = gh_hits if gh_hits is not None else []
        return ld.discover_lead_for_opportunity(
            OPPORTUNITY, problem_keywords=["workflow", "manual", "connecting apps"],
            leads_path=self.leads_path, dnc_path=self.dnc_path, events_path=self.events_path,
            hn_query_fn=lambda q, limit=10: (hn_hits, len(hn_hits)),
            github_query_fn=lambda q, limit=10: (gh_hits, len(gh_hits)),
            now=self.now, **kwargs,
        )


class TestValidLead(LeadDiscoveryTestCase):
    def test_valid_lead_is_qualified_and_persisted(self):
        result = self._discover()
        self.assertEqual(result["qualified_count"], 1)
        self.assertIsNotNone(result["best_candidate"])
        self.assertEqual(result["best_candidate"]["status"], "QUALIFIED")
        self.assertTrue(self.leads_path.exists())


class TestInvalidLead(LeadDiscoveryTestCase):
    def test_no_problem_keyword_match_is_rejected(self):
        result = self._discover(hn_hits=[_hn_hit(title="my new open source project", text="check it out")])
        self.assertEqual(result["qualified_count"], 0)
        self.assertIsNone(result["best_candidate"])
        self.assertEqual(result["all_candidates"][0]["status"], "REJECTED")


class TestDuplicateLead(LeadDiscoveryTestCase):
    def test_second_discovery_of_same_source_ref_is_flagged_duplicate(self):
        first = self._discover()
        self.assertEqual(first["qualified_count"], 1)
        second = self._discover()
        self.assertEqual(second["all_candidates"][0]["status"], "DUPLICATE")
        self.assertIsNone(second["best_candidate"])


class TestMissingSource(LeadDiscoveryTestCase):
    def test_unknown_source_name_returns_source_unavailable(self):
        result = ld.discover_raw_candidates("n8n", source="carrier_pigeon")
        self.assertFalse(result["ok"])
        self.assertIn("SOURCE_UNAVAILABLE", result["reason"])

    def test_zero_hits_is_honestly_disclosed_as_ambiguous(self):
        result = ld.discover_raw_candidates("n8n", source="hacker_news", hn_query_fn=lambda q, limit=10: ([], 0))
        self.assertTrue(result["ok"])
        self.assertEqual(result["candidates"], [])
        self.assertIn("indistinguishable", result["note"])


class TestStaleEvidence(LeadDiscoveryTestCase):
    def test_old_evidence_is_marked_stale_not_supported(self):
        old_hit = _hn_hit(created_at="2025-01-01T00:00:00.000Z")
        result = self._discover(hn_hits=[old_hit])
        cand = result["all_candidates"][0]
        self.assertEqual(cand["qualification"]["evidence_status"], "STALE")
        # Staleness alone doesn't earn the evidence-freshness qualification point
        self.assertLess(cand["qualification"]["qualification_score_numeric"],
                         self._discover()["all_candidates"][0]["qualification"]["qualification_score_numeric"])


class TestConflictingEvidenceNeverFabricated(LeadDiscoveryTestCase):
    def test_module_never_assigns_conflicting_or_verified_status(self):
        """Real, disclosed scope boundary: a single public post can never
        honestly earn VERIFIED (no independent corroboration) or
        CONFLICTING (no second disagreeing source exists in this module's
        design) -- confirmed here as a real invariant, not an oversight."""
        result = self._discover()
        status = result["all_candidates"][0]["qualification"]["evidence_status"]
        self.assertNotIn(status, ("VERIFIED", "CONFLICTING"))
        self.assertIn(status, ld.EVIDENCE_STATES)


class TestBlockedProspect(LeadDiscoveryTestCase):
    def test_do_not_contact_entry_blocks_the_lead(self):
        ld.add_to_do_not_contact(contact_channel="https://news.ycombinator.com/user?id=dev1",
                                  reason="test block", dnc_path=self.dnc_path, now=self.now)
        result = self._discover()
        self.assertEqual(result["qualified_count"], 0)
        cand = result["all_candidates"][0]
        self.assertEqual(cand["status"], "BLOCKED")
        self.assertTrue(cand["do_not_contact"])


class TestMissingCompany(LeadDiscoveryTestCase):
    def test_unknown_company_name_does_not_block_qualification(self):
        result = self._discover()
        cand = result["best_candidate"]
        self.assertTrue(str(cand["company_name"]).startswith("UNKNOWN"))
        self.assertEqual(cand["status"], "QUALIFIED")


class TestMissingContactChannel(LeadDiscoveryTestCase):
    def test_no_author_means_no_contact_channel_and_lead_is_rejected(self):
        result = self._discover(hn_hits=[_hn_hit(author=None)])
        cand = result["all_candidates"][0]
        self.assertIsNone(cand["contact_channel"])
        self.assertEqual(cand["status"], "REJECTED")


class TestQualificationLevels(LeadDiscoveryTestCase):
    def test_low_qualification_below_threshold(self):
        # No keyword match -> never qualifies, regardless of other real
        # signals present (evidence + opportunity verification still
        # score points, but relevance is the hard gate, Section 5).
        result = self._discover(hn_hits=[_hn_hit(title="random", text="nothing relevant", author=None)])
        cand = result["all_candidates"][0]
        self.assertEqual(cand["qualification"]["qualification_score_numeric"], 2)
        self.assertFalse(cand["qualification"]["qualifies"])

    def test_high_qualification_meets_threshold(self):
        result = self._discover()
        cand = result["best_candidate"]
        self.assertGreaterEqual(int(cand["qualification_score"].split("/")[0]), 3)


class TestSimulationLeakage(LeadDiscoveryTestCase):
    def test_simulation_only_flag_is_persisted_and_never_silently_dropped(self):
        result = self._discover(simulation_only=True)
        self.assertTrue(result["simulation_only"])
        self.assertTrue(result["best_candidate"]["simulation_only"])
        persisted = ld.load_leads(self.leads_path)
        self.assertTrue(persisted[0]["simulation_only"])

    def test_reality_firewall_module_has_no_ledger_import(self):
        import inspect
        source = inspect.getsource(ld)
        self.assertNotIn("import commission_ledger", source)
        self.assertNotIn("from commission_ledger", source)
        self.assertNotIn("open(\"finance_data.json\"", source)


class TestDedupCanonicalDomain(LeadDiscoveryTestCase):
    def test_same_github_org_domain_is_deduped_across_different_issues(self):
        gh_hit_1 = {"user": {"login": "alice"}, "title": "manual workflow pain point", "body": "connecting apps by hand is painful",
                    "html_url": "https://github.com/acme/repo/issues/1", "created_at": "2026-08-01T00:00:00.000Z",
                    "repository_url": "https://api.github.com/repos/acme/repo", "id": 111}
        gh_hit_2 = dict(gh_hit_1, id=222, html_url="https://github.com/acme/repo/issues/2", user={"login": "bob"})

        first = self._discover(hn_hits=[], gh_hits=[gh_hit_1])
        self.assertEqual(first["qualified_count"], 1)
        second = self._discover(hn_hits=[], gh_hits=[gh_hit_2])
        # Different contact_channel (bob vs alice) and different _raw_source_ref,
        # but the SAME canonical company website (github.com/acme) -- must dedup.
        self.assertEqual(second["all_candidates"][0]["status"], "DUPLICATE")


class TestNoQueryDerivable(LeadDiscoveryTestCase):
    def test_empty_opportunity_returns_honest_failure(self):
        result = ld.discover_lead_for_opportunity({}, hn_query_fn=lambda q, limit=10: ([], 0),
                                                    github_query_fn=lambda q, limit=10: ([], 0))
        self.assertFalse(result["ok"])


class TestAgentHealth(LeadDiscoveryTestCase):
    def test_idle_before_any_discovery(self):
        health = ld.agent_health(leads_path=self.leads_path, now=self.now)
        self.assertEqual(health["status"], "IDLE")

    def test_active_after_a_real_discovery(self):
        self._discover()
        health = ld.agent_health(leads_path=self.leads_path, now=self.now)
        self.assertEqual(health["status"], "ACTIVE")


if __name__ == "__main__":
    unittest.main()
