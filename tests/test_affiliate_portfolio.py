import unittest
from datetime import datetime, timezone

from affiliate import portfolio


class TestPortfolioRegister(unittest.TestCase):
    def setUp(self):
        self.register = portfolio.build_register()
        self.rows = self.register["programs"] + self.register["owned_purchase_intent"]

    def test_register_has_at_least_24_distinct_rows(self):
        self.assertGreaterEqual(len(self.rows), 24)
        self.assertGreaterEqual(self.register["affiliate_candidate_count"], 24)
        ids = [row["opportunity_id"] for row in self.rows]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_candidate_has_the_required_research_fields(self):
        for row in self.rows:
            for field in self.register["required_candidate_fields"]:
                self.assertIn(field, row, "%s missing %s" % (
                    row["opportunity_id"], field))
                value = row[field]
                self.assertIsNotNone(value, "%s has empty %s" % (
                    row["opportunity_id"], field))
                if isinstance(value, (str, list, dict)):
                    self.assertTrue(value, "%s has empty %s" % (
                        row["opportunity_id"], field))

    def test_every_row_has_a_valid_disposition(self):
        for row in self.rows:
            self.assertIn(row["disposition"], portfolio.CANDIDATE_DISPOSITIONS)

    def test_all_six_families_are_represented(self):
        summary = portfolio.summary(self.register)
        for family in portfolio.FAMILIES:
            self.assertGreater(summary["by_family"][family], 0, family)

    def test_no_row_is_activation_ready(self):
        self.assertTrue(all(row["activation_status"] == "NOT_ACTIVATION_READY"
                            for row in self.rows))

    def test_every_row_has_an_activation_gate(self):
        for row in self.rows:
            self.assertTrue(row["gates"], row["opportunity_id"])

    def test_no_commissions_are_claimed(self):
        summary = portfolio.summary(self.register)
        self.assertEqual(summary["activation_ready"], 0)
        self.assertNotIn("revenue", summary)

    def test_candidate_missing_facts_stay_unknown(self):
        for row in self.rows:
            self.assertIsInstance(row["evidence_sources"], list)
            self.assertTrue(row["next_action"])
            self.assertIn(row["payout_state"], (
                portfolio.PAYOUT_VERIFIED,
                portfolio.PAYOUT_CONDITIONAL,
                portfolio.PAYOUT_UNKNOWN,
                portfolio.PAYOUT_NOT_APPLICABLE,
            ))


class TestAlgeriaPayoutStatus(unittest.TestCase):
    def _row(self, opportunity_id):
        return next(p for p in portfolio.load_programs()
                    if p["opportunity_id"] == opportunity_id)

    def test_digitalocean_route_is_conditional_on_algeria_capability(self):
        result = portfolio.algeria_payout_status(
            self._row("CO-digitalocean-affiliate"))
        self.assertEqual(result["status"], portfolio.PAYOUT_CONDITIONAL)
        self.assertEqual(result["scope"], "country_rail_unconfirmed")
        self.assertFalse(result["account_level_verified"])
        self.assertTrue(result["official_sources"])
        self.assertIn(
            "Payoneer's Algeria payout capability is not confirmed",
            result["gaps"])
        self.assertIn("account-level eligibility is not confirmed", result["gaps"])

    def test_paypal_primary_program_is_conditional(self):
        result = portfolio.algeria_payout_status(
            self._row("CO-aweber-affiliate"))
        self.assertEqual(result["status"], portfolio.PAYOUT_CONDITIONAL)
        self.assertTrue(result["gaps"])
        self.assertTrue(result["official_sources"])

    def test_missing_algeria_evidence_is_unknown_not_rejected(self):
        result = portfolio.algeria_payout_status(
            self._row("CO-brevo-affiliate"))
        self.assertEqual(result["status"], portfolio.PAYOUT_UNKNOWN)
        self.assertFalse(result["account_level_verified"])
        self.assertIn("no current Algeria-specific payout evidence", result["gaps"])

    def test_paypal_primary_gate_is_named(self):
        row = next(p for p in portfolio.program_rows()
                   if p["opportunity_id"] == "CO-n8n-affiliate")
        self.assertIn("PAYOUT_ALGERIA_CONDITIONAL", row["gates"])
        self.assertIn("PAYOUT_ALGERIA_CONDITIONAL", next(
            p["gates"] for p in portfolio.program_rows()
            if p["opportunity_id"] == "CO-digitalocean-affiliate"))
        self.assertNotIn("PAYPAL_RAIL_RECORDED_ALGERIA_RISK", row["gates"])

    def test_canonical_states_are_not_collapsed(self):
        rows = [p for p in portfolio.program_rows()
                if p["opportunity_id"] in (
                    "CO-brevo-affiliate",
                    "CO-n8n-affiliate",
                    "CO-aweber-affiliate",
                    "CO-siteground-affiliate",
                    "CO-digitalocean-affiliate",
                )]
        statuses = {row["opportunity_id"]: row["algeria"]["status"] for row in rows}
        self.assertEqual(statuses["CO-brevo-affiliate"], portfolio.PAYOUT_UNKNOWN)
        self.assertEqual(statuses["CO-n8n-affiliate"], portfolio.PAYOUT_CONDITIONAL)
        self.assertEqual(statuses["CO-aweber-affiliate"], portfolio.PAYOUT_CONDITIONAL)
        self.assertEqual(statuses["CO-siteground-affiliate"], portfolio.PAYOUT_CONDITIONAL)
        self.assertEqual(statuses["CO-digitalocean-affiliate"], portfolio.PAYOUT_CONDITIONAL)

    def test_no_incompatible_or_blocked_state_exists(self):
        summary = portfolio.summary()
        self.assertFalse(hasattr(portfolio, "ALGERIA_INCOMPATIBLE"))
        self.assertNotIn("INCOMPATIBLE", summary["by_algeria_payout"])
        self.assertNotIn("BLOCKED", summary["by_payout_verdict"])
        for row in portfolio.program_rows():
            self.assertIn(row["algeria"]["status"], portfolio.PAYOUT_STATES)

    def test_summary_reports_all_canonical_states(self):
        summary = portfolio.summary()
        self.assertEqual(summary["by_algeria_payout"][portfolio.PAYOUT_VERIFIED], 0)
        self.assertEqual(summary["by_algeria_payout"][portfolio.PAYOUT_CONDITIONAL], 10)
        self.assertEqual(summary["by_algeria_payout"][portfolio.PAYOUT_UNKNOWN], 19)
        self.assertEqual(summary["by_algeria_payout"][portfolio.PAYOUT_NOT_APPLICABLE], 3)
        self.assertEqual(summary["by_payout_verdict"], {
            "PASS": 0,
            "HOLD": 10,
            "UNKNOWN": 19,
            "N/A": 3,
        })

    def test_payout_transitions_require_current_authoritative_evidence(self):
        current = datetime.now(timezone.utc).date().isoformat()
        base = {"checked_at": current, "official_sources": ["https://example.test"],
                "scope": "route_only"}
        conditional = dict(base, gaps=["program-specific rail is not confirmed"])
        verified = dict(base, gaps=["account-level eligibility is not confirmed"])
        self.assertTrue(portfolio.can_transition_payout(
            portfolio.PAYOUT_UNKNOWN, portfolio.PAYOUT_CONDITIONAL, conditional))
        self.assertTrue(portfolio.can_transition_payout(
            portfolio.PAYOUT_UNKNOWN, portfolio.PAYOUT_VERIFIED, verified))
        self.assertFalse(portfolio.can_transition_payout(
            portfolio.PAYOUT_UNKNOWN, portfolio.PAYOUT_VERIFIED, {}))
        self.assertTrue(portfolio.can_transition_payout(
            portfolio.PAYOUT_CONDITIONAL, portfolio.PAYOUT_VERIFIED, verified))
        self.assertTrue(portfolio.can_transition_payout(
            portfolio.PAYOUT_VERIFIED, portfolio.PAYOUT_UNKNOWN, None))
        self.assertFalse(portfolio.can_transition_payout(
            portfolio.PAYOUT_UNKNOWN, portfolio.PAYOUT_NOT_APPLICABLE, verified))
        self.assertFalse(portfolio.can_transition_payout(
            portfolio.PAYOUT_UNKNOWN, portfolio.PAYOUT_VERIFIED,
            {"checked_at": "2020-01-01", "official_sources": ["x"],
             "scope": "route_only", "gaps": []}))


class TestExistingGuideAudit(unittest.TestCase):
    def test_every_mapped_guide_exists(self):
        for filename in portfolio.GUIDE_BY_PROGRAM.values():
            audit = portfolio.audit_guide(filename)
            self.assertTrue(audit["exists"], filename)
            self.assertGreater(audit["words"], 0, filename)

    def test_guides_without_cta_are_held(self):
        for filename in portfolio.GUIDE_BY_PROGRAM.values():
            audit = portfolio.audit_guide(filename)
            if not audit["cta_present"] or not audit["disclosure"]:
                self.assertEqual(audit["status"], "HOLD", filename)


class TestAssetStateTransitions(unittest.TestCase):
    def test_normal_path_is_allowed(self):
        path = ["IDEA", "RESEARCHED", "ELIGIBILITY_PASS", "DRAFTED",
                "QA_PASS", "LINK_BLOCKED", "AUTH_PENDING", "PUBLISHED",
                "MEASURING", "HELD"]
        for current, next_stage in zip(path, path[1:]):
            self.assertTrue(portfolio.can_transition(current, next_stage),
                            "%s -> %s" % (current, next_stage))

    def test_cannot_skip_quality_gate(self):
        self.assertFalse(portfolio.can_transition("DRAFTED", "AUTH_PENDING"))
        self.assertFalse(portfolio.can_transition("RESEARCHED", "PUBLISHED"))

    def test_hold_cannot_go_straight_to_published(self):
        self.assertFalse(portfolio.can_transition("QA_HOLD", "PUBLISHED"))
        self.assertTrue(portfolio.can_transition("QA_HOLD", "DRAFTED"))

    def test_terminal_states_are_terminal(self):
        self.assertFalse(portfolio.can_transition("HIBERNATED", "PUBLISHED"))
        self.assertFalse(portfolio.can_transition("SCALED", "MEASURING"))


if __name__ == "__main__":
    unittest.main()
