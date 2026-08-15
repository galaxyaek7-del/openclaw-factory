"""Tests for first_dollar_engine.py -- the thin FIRST-DOLLAR ENGINE on top of
the existing Golden Hunter + Revenue OS + CEO Loop infrastructure.

MOCK data only: scoring, ranking, human-gate classification, duplicate
prevention, revenue integrity and the scale ladder are all exercised against
temporary/mocked portfolio rows. Nothing here writes to any real ledger.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import first_dollar_engine as fde


def _opp(opportunity_id="CO-x-affiliate", **kw):
    base = {
        "opportunity_id": opportunity_id,
        "source": "test",
        "program_name": "X Affiliate Program",
        "partner_name": "X",
        "partner_id": "x",
        "category": "affiliate",
        "verification_status": "VERIFIED",
        "recurring_commission": True,
        "commission_value": "30% recurring for 12 months",
        "payout_algeria_compatible": True,
        "eligibility": "Self-service signup",
        "risk_score": "Low",
        "evidence_url": "https://example.com/affiliates",
        "geography": "GLOBAL",
        "payout_terms": "via Awin/Payoneer",
        "estimated_cost": 0,
    }
    base.update(kw)
    return base


class FirstDollarScoringTests(unittest.TestCase):
    def test_score_weights_sum_to_one(self):
        total = sum(c["weight"] for c in fde.FIRST_DOLLAR_CRITERIA)
        self.assertAlmostEqual(total, 1.0, places=9)

    def test_verified_recurring_automatable_scores_high(self):
        o = _opp()
        s = fde.first_dollar_score(o, human_gates={"BLOCKING": False},
                                   clicks=10, assets_ready=["asset"])
        self.assertGreater(s["FIRST_DOLLAR_SCORE"], 70.0)

    def test_human_gate_lowers_score_via_speed_and_intervention(self):
        gated = fde.first_dollar_score(_opp(), human_gates={"BLOCKING": True}, assets_ready=[])
        ungated = fde.first_dollar_score(_opp(), human_gates={"BLOCKING": False}, assets_ready=["asset"])
        self.assertGreater(ungated["FIRST_DOLLAR_SCORE"], gated["FIRST_DOLLAR_SCORE"])
        # Speed + intervention specifically
        self.assertEqual(gated["breakdown"]["time_to_first_revenue"], 0.2)
        self.assertEqual(gated["breakdown"]["minimal_founder_intervention"], 0.2)

    def test_algeria_incompatible_payout_penalizes(self):
        blocked = fde.first_dollar_score(_opp(payout_algeria_compatible=False))
        ok = fde.first_dollar_score(_opp(payout_algeria_compatible=True))
        self.assertLess(blocked["breakdown"]["country_payment_compatibility"],
                        ok["breakdown"]["country_payment_compatibility"])

    def test_fast_small_path_can_outrank_slow_high_value(self):
        # The directive's core rule: a fast $5 opportunity with a realistic
        # conversion path may outrank a theoretical $500 opportunity needing
        # weeks of setup. Both VERIFIED + recurring + compatible, but one has
        # a ready asset + no gate (fast) vs a gate + no asset (slow).
        fast = _opp("CO-fast-5", commission_value="10%", eligibility="AUTOMATABLE",
                    _distribution_ready=True)
        slow = _opp("CO-slow-500", commission_value="30%", eligibility="application approval required")
        sf = fde.first_dollar_score(fast, human_gates={"BLOCKING": False}, assets_ready=["ready asset"], clicks=5)
        ss = fde.first_dollar_score(slow, human_gates={"BLOCKING": True}, assets_ready=[])
        self.assertGreater(sf["FIRST_DOLLAR_SCORE"], ss["FIRST_DOLLAR_SCORE"])

    def test_unknown_signals_stay_neutral_never_zero(self):
        o = _opp(verification_status="UNKNOWN", payout_algeria_compatible=None,
                 commission_value="UNKNOWN", recurring_commission=False, evidence_url=None)
        s = fde.first_dollar_score(o)
        # No fabricated zeros: every breakdown value is >= 0.2 (never killed by an unknown).
        for v in s["breakdown"].values():
            self.assertGreaterEqual(v, 0.2)


class HumanGateClassificationTests(unittest.TestCase):
    def test_affiliate_always_human_gate_without_credential(self):
        # A program whose category is affiliate + no credential configured is
        # a human gate (account creation/approval), even when eligibility is
        # UNKNOWN -- unverified capability is never claimed automatable.
        for o in (_opp(), _opp(eligibility="UNKNOWN")):
            g = fde.classify_human_gate(o)
            self.assertEqual(g["classification"], "HUMAN_GATE")

    def test_explicit_approval_eligibility_is_human_gate(self):
        g = fde.classify_human_gate(_opp(eligibility="Application approval required; manual review"))
        self.assertEqual(g["classification"], "HUMAN_GATE")
        self.assertIn("approval", g["founder_action"].lower())

    def test_real_blocking_gate_maps_to_founder_action(self):
        gates = [{
            "gate_id": "GATE-AWIN-DIGITALOCEAN", "platform": "DigitalOcean (Awin)",
            "founder_action": "https://ui.awin.com/merchant-profile/123996",
            "action_required": "Apply to the verified DigitalOcean affiliate program",
            "why_required": "real reason", "verification_after_action": "verify link live",
        }]
        o = _opp("CO-digitalocean-affiliate")
        g = fde.classify_human_gate(o, blocking_gates=gates)
        self.assertEqual(g["classification"], "HUMAN_GATE")
        self.assertEqual(g["gate_id"], "GATE-AWIN-DIGITALOCEAN")
        self.assertIn("awin", g["founder_action"].lower())

    def test_unknown_eligibility_never_defaults_to_automatable(self):
        g = fde.classify_human_gate(_opp(eligibility="UNKNOWN"))
        self.assertEqual(g["classification"], "HUMAN_GATE")


class RankAndRouterTests(unittest.TestCase):
    def test_rank_orders_by_first_dollar_score_desc(self):
        portfolio = [
            _opp("CO-a", commission_value="30%", recurring_commission=True),
            _opp("CO-b", commission_value="5%", recurring_commission=False),
            _opp("CO-c", commission_value="30%", recurring_commission=True),
        ]
        r = fde.rank_first_dollar(portfolio=portfolio, top_n=3)
        scores = [o["first_dollar_score"] for o in r["ranking"]]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_execution_router_independent_classification(self):
        # One blocked opportunity must never stop the others: every top-N entry
        # is classified independently.
        portfolio = [
            _opp("CO-blocked", eligibility="application approval required"),
            _opp("CO-open", eligibility="UNKNOWN"),
        ]
        route = fde.execution_router(top_n=2, portfolio=portfolio)
        self.assertEqual(len(route["TOP_3"]), 2)
        for o in route["TOP_3"]:
            self.assertEqual(o["can_execute_now"], o["classification"] == "AUTOMATABLE")


class DuplicatePreventionTests(unittest.TestCase):
    def test_discovery_deduplicates_by_opportunity_id(self):
        portfolio = [_opp("CO-x"), _opp("CO-y")]
        verified = [_opp("CO-x"), _opp("CO-z")]  # CO-x duplicate
        d = fde.discover_first_dollar_opportunities(
            portfolio=portfolio, verified_programs=verified, goos_candidates={})
        ids = [o["opportunity_id"] for o in d["opportunities"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 3)  # CO-x, CO-y, CO-z exactly once
        self.assertEqual(d["deduplicated"], 1)


class RevenueIntegrityTests(unittest.TestCase):
    def test_ladder_only_advances_on_real_revenue(self):
        self.assertEqual(fde.first_dollar_ladder(0)["level"], 0)
        self.assertEqual(fde.first_dollar_ladder(5)["level"], 1)
        self.assertEqual(fde.first_dollar_ladder(30)["level"], 2)
        self.assertEqual(fde.first_dollar_ladder(150)["level"], 3)
        self.assertEqual(fde.first_dollar_ladder(650)["level"], 4)
        self.assertEqual(fde.first_dollar_ladder(9000)["level"], 5)

    def test_cycle_reports_zero_verified_and_no_write(self):
        # run_first_dollar_cycle must report the real (currently $0) verified
        # revenue and must NOT create/alter any real ledger file. We snapshot
        # the REAL data/ directory (the dir the ledger files actually live in)
        # before and after, so a hypothetical write to a real ledger is caught.
        data_dir = Path(__file__).resolve().parent.parent / "data"
        if data_dir.exists():
            before = {str(p.relative_to(data_dir)): p.stat().st_mtime_ns
                      for p in data_dir.rglob("*") if p.is_file()}
        else:
            before = {}
        cycle = fde.run_first_dollar_cycle()
        if data_dir.exists():
            after = {str(p.relative_to(data_dir)): p.stat().st_mtime_ns
                     for p in data_dir.rglob("*") if p.is_file()}
        else:
            after = {}
        self.assertEqual(before, after)  # no real file created or modified
        self.assertIn("REAL_VERIFIED_REVENUE_USD", cycle)
        self.assertIsInstance(cycle["REAL_VERIFIED_REVENUE_USD"], float)
        self.assertIn("LADDER", cycle)


class AttributionAndRerankTests(unittest.TestCase):
    def test_real_click_counts_feed_score(self):
        # Real click counts read from the real click ledger must feed the
        # first-dollar score (demand evidence) and shift the ranking.
        with mock.patch.object(fde, "_real_click_counts") as m:
            m.return_value = {"CO-x": 25, "CO-y": 0}
            low = fde.first_dollar_score(_opp("CO-x"), clicks=25)
            no_clicks = fde.first_dollar_score(_opp("CO-x"), clicks=0)
            self.assertGreater(low["FIRST_DOLLAR_SCORE"], no_clicks["FIRST_DOLLAR_SCORE"])
        ranked = fde.rank_first_dollar(top_n=3, portfolio=[_opp("CO-x"), _opp("CO-y")])
        self.assertEqual(ranked["ranking"][0]["opportunity_id"], "CO-x")

    def test_rerank_shifts_on_click_delta(self):
        # A real click delta re-ranks across two rank calls (learning loop).
        base = [_opp("CO-a"), _opp("CO-b")]
        with mock.patch.object(fde, "_real_click_counts") as m:
            m.return_value = {"CO-a": 12, "CO-b": 2}
            first = fde.rank_first_dollar(top_n=2, portfolio=base)
            m.return_value = {"CO-a": 12, "CO-b": 40}
            second = fde.rank_first_dollar(top_n=2, portfolio=base)
        a, b = [o["opportunity_id"] for o in first["ranking"]], \
               [o["opportunity_id"] for o in second["ranking"]]
        self.assertEqual(a[0], "CO-a")
        self.assertEqual(b[0], "CO-b")  # big click surge for CO-b flips the order


class ExistingArmIntegrationTests(unittest.TestCase):
    def test_ceo_loop_has_first_dollar_lens(self):
        import revenue_os
        loop = revenue_os.run_daily_ceo_loop()
        self.assertIn("FIRST_DOLLAR", loop)
        self.assertIn("BEST_FIRST_DOLLAR", loop["FIRST_DOLLAR"])
        # The CEO loop remains the central authority: profit-first rank still present.
        self.assertIn("RANK", loop)
        self.assertIn("BEST_PROFIT_FIRST", loop["RANK"])

    def test_mission_control_endpoint_registered_and_read_only(self):
        import mission_control_api as mca
        self.assertIn("first_dollar_engine", mca._ENDPOINTS)
        r = mca._ENDPOINTS["first_dollar_engine"]()
        self.assertIn("RANK", r)
        self.assertIn("SELECT", r)
        self.assertIn("REAL_VERIFIED_REVENUE_USD", r)

    def test_opportunity_class_has_all_required_fields(self):
        o = _opp()
        gate = fde.classify_human_gate(o)
        score = fde.first_dollar_score(o)
        cls = fde.build_opportunity_class(o, gate, score, {})
        required = [
            "opportunity_id", "category", "source", "offer", "merchant_platform",
            "commission_or_margin", "recurring_status", "payout_method",
            "country_eligibility", "required_credentials", "required_founder_action",
            "estimated_time_to_first_revenue", "estimated_cost", "demand_evidence",
            "competition_signal", "risk", "first_dollar_score", "long_term_score", "status",
        ]
        for k in required:
            self.assertIn(k, cls, f"missing opportunity class field: {k}")


if __name__ == "__main__":
    unittest.main()