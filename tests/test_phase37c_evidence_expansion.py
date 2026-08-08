"""Phase 37C, Sections 1-8 — fresh evidence expansion tests (ADR-232).
Covers the Stack Overflow source, source-tier hierarchy, the explicit
FRESH/STALE/UNKNOWN freshness classifier, and the new 3-way
QUALIFICATION_STATUS. Zero live network calls -- every query function
injected."""

import unittest
from datetime import datetime, timezone

import lead_discovery as ld

OPPORTUNITY = {"opportunity_id": "CO-n8n-affiliate", "verification_status": "VERIFIED"}
KEYWORDS = ["workflow", "automation", "n8n"]


def _so_hit(display_name="dev1", title="how to automate n8n workflow tasks", link="https://stackoverflow.com/q/1",
            question_id=1, creation_date=None, profile_link="https://stackoverflow.com/users/1/dev1", tags=None):
    return {"owner": {"display_name": display_name, "link": profile_link}, "title": title, "link": link,
            "question_id": question_id, "creation_date": creation_date, "tags": tags or ["n8n"]}


class TestStackOverflowAdapter(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 8, tzinfo=timezone.utc)

    def test_fresh_stack_overflow_hit_is_correctly_shaped(self):
        recent_ts = int(datetime(2026, 8, 1, tzinfo=timezone.utc).timestamp())
        hit = _so_hit(creation_date=recent_ts)
        lead = ld._lead_from_stack_overflow_hit(hit, opportunity_id="CO-n8n-affiliate", now=self.now)
        self.assertEqual(lead["source_type"], "stack_overflow")
        self.assertEqual(lead["contact_channel"], "https://stackoverflow.com/users/1/dev1")
        self.assertIn("2026-08-01", lead["source_timestamp"])
        self.assertIn("n8n", lead["problem_signal"])

    def test_missing_creation_date_is_honestly_none_not_guessed(self):
        hit = _so_hit(creation_date=None)
        lead = ld._lead_from_stack_overflow_hit(hit, now=self.now)
        self.assertIsNone(lead["source_timestamp"])

    def test_discover_raw_candidates_dispatches_to_stack_overflow(self):
        def fake_so(q, limit=10):
            return [_so_hit(creation_date=int(self.now.timestamp()))], 1
        result = ld.discover_raw_candidates("n8n", source="stack_overflow", stack_overflow_query_fn=fake_so, now=self.now)
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["candidates"]), 1)
        self.assertEqual(result["candidates"][0]["source_type"], "stack_overflow")


class TestSourceTierHierarchy(unittest.TestCase):
    def test_all_six_tiers_named(self):
        self.assertEqual(len(ld.EVIDENCE_HIERARCHY), 6)

    def test_source_tier_never_elevates_hacker_news_above_official_sources(self):
        self.assertGreater(ld.SOURCE_TIER["hacker_news"], ld.SOURCE_TIER["github_issues"])

    def test_stack_overflow_between_github_and_hacker_news(self):
        self.assertGreater(ld.SOURCE_TIER["stack_overflow"], ld.SOURCE_TIER["github_issues"])
        self.assertLess(ld.SOURCE_TIER["stack_overflow"], ld.SOURCE_TIER["hacker_news"])


class TestClassifyFreshness(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 8, tzinfo=timezone.utc)

    def test_fresh_within_45_days(self):
        result = ld.classify_freshness("2026-07-25T00:00:00+00:00", now=self.now)
        self.assertEqual(result["freshness_status"], "FRESH")
        self.assertLessEqual(result["age_days"], 45)

    def test_stale_beyond_45_days(self):
        result = ld.classify_freshness("2026-01-01T00:00:00+00:00", now=self.now)
        self.assertEqual(result["freshness_status"], "STALE")

    def test_missing_timestamp_is_unknown_never_fresh(self):
        result = ld.classify_freshness(None, now=self.now)
        self.assertEqual(result["freshness_status"], "UNKNOWN")

    def test_unparseable_timestamp_is_unknown_never_guessed(self):
        result = ld.classify_freshness("not-a-real-date", now=self.now)
        self.assertEqual(result["freshness_status"], "UNKNOWN")

    def test_stale_days_constant_is_still_45_never_weakened(self):
        """Phase 37C's own explicit, non-negotiable rule."""
        self.assertEqual(ld._STALE_DAYS, 45)

    def test_result_always_includes_retrieved_at(self):
        result = ld.classify_freshness("2026-07-25T00:00:00+00:00", now=self.now)
        self.assertIsNotNone(result["retrieved_at"])


class TestQualificationStatusThreeWay(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 8, tzinfo=timezone.utc)

    def _candidate(self, source_timestamp, contact_channel="https://github.com/dev1", company_name="RealCo"):
        return {
            "company_name": company_name, "contact_channel": contact_channel,
            "problem_signal": "we need n8n workflow automation badly", "source_url": "https://example.com/p",
            "source_timestamp": source_timestamp, "source_type": "github_issues",
        }

    def test_fresh_strong_candidate_is_qualified(self):
        c = self._candidate(source_timestamp="2026-08-01T00:00:00+00:00")
        q = ld.qualify_lead(c, opportunity=OPPORTUNITY, problem_keywords=KEYWORDS, now=self.now)
        self.assertEqual(q["QUALIFICATION_STATUS"], "QUALIFIED")
        self.assertTrue(q["qualifies"])

    def test_stale_but_otherwise_strong_candidate_is_provisional_not_rejected(self):
        c = self._candidate(source_timestamp="2026-01-01T00:00:00+00:00")
        q = ld.qualify_lead(c, opportunity=OPPORTUNITY, problem_keywords=KEYWORDS, now=self.now)
        self.assertEqual(q["QUALIFICATION_STATUS"], "PROVISIONAL")
        self.assertFalse(q["qualifies"])  # PROVISIONAL is still not QUALIFIED

    def test_weak_candidate_with_no_keyword_match_is_rejected_not_provisional(self):
        c = self._candidate(source_timestamp="2026-01-01T00:00:00+00:00")
        c["problem_signal"] = "totally unrelated topic"
        q = ld.qualify_lead(c, opportunity=OPPORTUNITY, problem_keywords=KEYWORDS, now=self.now)
        self.assertEqual(q["QUALIFICATION_STATUS"], "REJECTED")

    def test_provisional_never_bypasses_outreach_gates(self):
        """A PROVISIONAL candidate is not silently treated as sendable --
        outreach_adapter.py's own send() only checks draft state/approval,
        never QUALIFICATION_STATUS, so PROVISIONAL carries no special
        send-eligibility of its own."""
        import inspect
        import outreach_adapter as oa
        source = inspect.getsource(oa.SMTPOutreachAdapter.send)
        self.assertNotIn("PROVISIONAL", source)
        self.assertNotIn("QUALIFICATION_STATUS", source)


if __name__ == "__main__":
    unittest.main()
