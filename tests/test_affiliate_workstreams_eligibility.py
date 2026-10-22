"""Affiliate mandate 2026-10-22: eligibility/payout matrix, first-commission
ranking, the 24 workstreams, and two registry/scoring defects.

Fixtures only (plus read-only checks of the real registry's integrity).
No network, no writes.

    python -m pytest tests/test_affiliate_workstreams_eligibility.py -q
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from affiliate import eligibility_matrix as em  # noqa: E402
from affiliate import opportunity_rank, priority, registry, workstreams  # noqa: E402

RAILS = {
    "paypal": {"algeria_receive": "CONDITIONAL", "basis": "VERIFIED"},
    "stripe": {"algeria_receive": "UNAVAILABLE", "basis": "VERIFIED"},
    "payoneer": {"algeria_receive": "UNKNOWN", "basis": "UNKNOWN"},
}


def opp(oid, **kw):
    base = {"opportunity_id": oid, "program_name": oid, "partner_id": oid, "category": "affiliate",
            "verification_status": "VERIFIED", "commission_value": "30% recurring",
            "recurring_commission": True, "cookie_or_tracking_window": "60-day cookie",
            "last_verified": "2026-10-22", "geography": "Global"}
    base.update(kw)
    return base


class TestEligibilityMatrix(unittest.TestCase):
    def test_no_evidence_is_unknown_never_eligible(self):
        rows = em.matrix([opp("A")], {"rails": RAILS, "programs": {}})
        self.assertEqual(rows[0]["eligibility_state"], "ELIGIBILITY_UNKNOWN")
        self.assertEqual(rows[0]["payout_state"], "PAYOUT_UNVERIFIED")

    def test_eligibility_and_payout_are_independent(self):
        ev = {"rails": RAILS, "programs": {"A": {
            "publisher_eligibility_algeria": "NO_COUNTRY_RESTRICTION_STATED",
            "eligibility_basis": "VERIFIED", "payout_routes": ["payoneer"]}}}
        r = em.matrix([opp("A")], ev)[0]
        self.assertEqual(r["eligibility_state"], "ELIGIBLE_EVIDENCE_FOUND")
        self.assertEqual(r["payout_state"], "PAYOUT_UNVERIFIED")

    def test_stripe_only_route_is_blocked_paypal_is_conditional(self):
        ev = {"rails": RAILS, "programs": {
            "S": {"payout_routes": ["stripe"]},
            "P": {"payout_routes": ["stripe", "paypal"]}}}
        rows = {r["opportunity_id"]: r for r in em.matrix([opp("S"), opp("P")], ev)}
        self.assertEqual(rows["S"]["payout_state"], "PAYOUT_ROUTE_BLOCKED")
        self.assertEqual(rows["P"]["payout_state"], "PAYOUT_ROUTE_CONDITIONAL")

    def test_payout_verified_needs_explicit_flag(self):
        ev = {"rails": RAILS, "programs": {"A": {"payout_routes": ["paypal"], "payout_verified": True}}}
        self.assertEqual(em.matrix([opp("A")], ev)[0]["payout_state"], "PAYOUT_VERIFIED")

    def test_discontinued_is_closed(self):
        r = em.matrix([opp("A", verification_status="DISCONTINUED")], {"rails": {}, "programs": {}})[0]
        self.assertEqual(r["eligibility_state"], "CLOSED")


class TestRanking(unittest.TestCase):
    def test_evidenced_modest_program_beats_unknown_high_commission(self):
        programs = [opp("HIGH", commission_value="80% recurring"),
                    opp("MODEST", commission_value="20% recurring")]
        ev = {"rails": RAILS, "programs": {"MODEST": {
            "publisher_eligibility_algeria": "NO_COUNTRY_RESTRICTION_STATED",
            "eligibility_basis": "VERIFIED", "payout_routes": ["paypal"]}}}
        order = [r["opportunity_id"] for r in opportunity_rank.rank(programs, ev)]
        self.assertEqual(order[0], "MODEST")

    def test_components_are_exposed(self):
        r = opportunity_rank.rank([opp("A")], {"rails": {}, "programs": {}})[0]
        for k in ("economics_score", "eligibility_factor", "payout_factor", "account_bonus"):
            self.assertIn(k, r["components"])
        self.assertTrue(r["not_a_revenue_forecast"])

    def test_closed_program_is_not_rankable(self):
        r = opportunity_rank.rank([opp("A", verification_status="DISCONTINUED")],
                                  {"rails": {}, "programs": {}})[0]
        self.assertFalse(r["rankable"])


class TestDefectFixes(unittest.TestCase):
    def test_registry_reads_the_field_names_the_data_uses(self):
        rec = registry.program_record({"opportunity_id": "X", "geography": "Global",
                                       "payout_minimum": "USD 30", "payout_methods": ["PayPal"]}, [], [])
        self.assertEqual(rec["geographic_restrictions"], "Global")
        self.assertEqual(rec["payout_threshold"], "USD 30")
        self.assertEqual(rec["payout_method"], ["PayPal"])

    def test_global_or_algeria_mention_is_not_algeria_eligibility(self):
        for geo in ("Global", "Global; PayPal receiving in Algeria is conditional"):
            s = priority.score_program({"geographic_restrictions": geo})
            geo_c = [c for c in s["components"] if c["axis"] == "geographic_fit"][0]
            self.assertLess(geo_c["points"], priority.WEIGHTS["geographic_fit"], geo)
            self.assertNotEqual(geo_c["basis"], "VERIFIED")


class TestWorkstreams(unittest.TestCase):
    def setUp(self):
        self.ev = {"rails": RAILS, "programs": {"CO-n8n-affiliate": {
            "publisher_eligibility_algeria": "NO_COUNTRY_RESTRICTION_STATED",
            "eligibility_basis": "OBSERVED", "payout_routes": ["paypal"]}}}
        self.rows = workstreams.workstream_registry([opp("CO-n8n-affiliate")], self.ev)

    def test_exactly_24_stable_unique_ids(self):
        ids = [r["workstream_id"] for r in self.rows]
        self.assertEqual(ids, [f"WS-{i:02d}" for i in range(1, 25)])

    def test_states_follow_evidence(self):
        by = {r["workstream_id"]: r for r in self.rows}
        self.assertEqual(by["WS-06"]["state"], "PAYOUT_HOLD")
        self.assertEqual(by["WS-01"]["state"], "NO_CANDIDATE")
        self.assertIn("CO-zapier-affiliate", by["WS-06"]["missing_from_registry"])
        self.assertTrue(by["WS-22"]["cross_cutting_format"])
        for r in self.rows:
            self.assertEqual(r["demand_evidence"], "UNKNOWN")


class TestRealRegistryIntegrity(unittest.TestCase):
    def test_opportunity_ids_unique_and_workstream_refs_resolve(self):
        ids = [o["opportunity_id"] for o in registry.load_opportunities()]
        self.assertEqual(len(ids), len(set(ids)))
        # A reference must be in the registry, or at least carry sourced
        # evidence (systeme.io: pending reconciliation, see affiliate_discovery).
        evidenced = set(json.loads(em.EVIDENCE.read_text(encoding="utf-8"))["programs"])
        known = set(ids) | evidenced
        for wid, *_rest in workstreams._WS:
            cands = _rest[4]
            for c in cands or []:
                self.assertIn(c, known, f"{wid} references unknown {c}")

    def test_evidence_file_has_sources_and_no_unflagged_payout_verification(self):
        data = json.loads(em.EVIDENCE.read_text(encoding="utf-8"))
        for oid, ev in data["programs"].items():
            self.assertTrue(ev.get("sources"), oid)
            self.assertIn("checked", ev, oid)
            self.assertFalse(ev.get("payout_verified"), f"{oid}: no payout has been received")


if __name__ == "__main__":
    unittest.main()
