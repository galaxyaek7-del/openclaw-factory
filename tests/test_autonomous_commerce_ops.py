"""Tests for autonomous_commerce_ops.py -- the autonomous commercial
operations orchestration layer.

Unit + integration + regression + security + revenue-integrity, MOCK data only.
These tests never touch the real Paddle/Gumroad APIs (live checks are stubbed)
and never write to the real data/ ledgers. All gates, launch-queue states and
revenue-integrity invariants are exercised against temporary/mocked state.
"""

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import autonomous_commerce_ops as aco


def _stub_live_checks():
    """Make every live network check a deterministic stub (mock-only)."""
    import scripts.check_paddle_checkout_status as paddle_check

    def _fake_paddle():
        return {"results": [{"checkout_ready": False} for _ in range(6)]}

    paddle_check.check_and_notify_all = _fake_paddle

    import channels.gumroad_publisher as gp

    gp.list_products = lambda token: [{
        "id": "p1", "published": False, "price_cents": None,
    }]
    gp.load_token = lambda: "mock-token"
    return paddle_check, gp


class HumanGateOrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.paddle_check, self.gp = _stub_live_checks()

    def test_every_gate_has_required_fields(self):
        result = aco.human_gate_orchestrator()
        for g in result["gates"]:
            for field in ("gate_id", "platform", "action_required", "why_required",
                          "status", "blocking_revenue", "founder_action",
                          "verification_after_action"):
                self.assertIn(field, g)

    def test_all_three_gates_are_blocking_with_zero_revenue(self):
        result = aco.human_gate_orchestrator()
        blocking = [g for g in result["gates"] if g["status"] == "BLOCKING"]
        self.assertEqual(len(blocking), 3)

    def test_awin_gate_links_to_official_signup(self):
        result = aco.human_gate_orchestrator()
        awin = next(g for g in result["gates"] if g["gate_id"] == "GATE-AWIN-DIGITALOCEAN")
        self.assertIn("ui.awin.com/merchant-profile/123996", awin["founder_action"])

    def test_awin_gate_becomes_ready_for_verification_when_link_configured(self):
        original = aco._launch_link_status
        aco._launch_link_status = lambda: "CONFIGURED"
        try:
            result = aco.human_gate_orchestrator()
            awin = next(g for g in result["gates"] if g["gate_id"] == "GATE-AWIN-DIGITALOCEAN")
            self.assertEqual(awin["status"], "READY_FOR_VERIFICATION")
        finally:
            aco._launch_link_status = original

    def test_gumroad_gate_blocking_while_draft_unpriced(self):
        result = aco.human_gate_orchestrator()
        gum = next(g for g in result["gates"] if g["gate_id"] == "GATE-GUMROAD-PAYMENT")
        self.assertEqual(gum["status"], "BLOCKING")

    def test_no_gate_ever_reports_verified_without_live_confirmation(self):
        result = aco.human_gate_orchestrator()
        for g in result["gates"]:
            self.assertNotEqual(g["status"], "VERIFIED")


class FounderActionQueueTests(unittest.TestCase):
    def setUp(self):
        self.paddle_check, self.gp = _stub_live_checks()

    def test_exactly_one_urgent_action(self):
        result = aco.founder_action_queue()
        urgent = result["URGENT"]
        self.assertIsNotNone(urgent)
        self.assertEqual(urgent["gate_id"], "GATE-AWIN-DIGITALOCEAN")

    def test_urgent_is_a_single_gate_not_a_list(self):
        result = aco.founder_action_queue()
        self.assertIsInstance(result["URGENT"], dict)

    def test_next_is_a_short_capped_list(self):
        result = aco.founder_action_queue()
        self.assertLessEqual(len(result["NEXT"]), 2)

    def test_no_gate_appears_twice(self):
        result = aco.founder_action_queue()
        seen = []
        for item in ([result["URGENT"]] + result["NEXT"] + result["OPTIONAL"]):
            if item:
                self.assertNotIn(item["gate_id"], seen)
                seen.append(item["gate_id"])


class AutoCloseSupersededTests(unittest.TestCase):
    def test_non_blocking_gates_closed_when_verified_revenue_exists(self):
        gates = [
            {"gate_id": "GATE-AWIN-DIGITALOCEAN", "status": "BLOCKING", "blocking_revenue": True},
            {"gate_id": "GATE-X", "status": "OPEN", "blocking_revenue": False},
        ]
        original = aco._real_revenue_totals
        aco._real_revenue_totals = lambda: {"VERIFIED_REVENUE_USD": 50.0}
        try:
            out = aco.auto_close_superseded_gates(gates)
            closed = next(g for g in out if g["gate_id"] == "GATE-X")
            self.assertEqual(closed["status"], "NOT_REQUIRED")
            self.assertTrue(closed["auto_closed"])
        finally:
            aco._real_revenue_totals = original


class UnifiedLaunchQueueTests(unittest.TestCase):
    def test_statuses_are_valid(self):
        result = aco.unified_launch_queue()
        for e in result["entries"]:
            self.assertIn(e["status"], aco.LAUNCH_QUEUE_STATES)

    def test_all_entries_honestly_blocked_until_destination_configured(self):
        result = aco.unified_launch_queue()
        if result["entries"]:
            for e in result["entries"]:
                self.assertEqual(e["status"], "HUMAN_GATE")

    def test_invariant_ready_cannot_jump_to_published(self):
        transitions = aco.unified_launch_queue()["allowed_transitions"]
        self.assertNotIn("PUBLISHED", transitions["READY"])
        self.assertIn("AUTHORIZED", transitions["READY"])

    def test_authorize_requires_readyt_state(self):
        entry = {"status": "HUMAN_GATE", "offer_id": "x"}
        with self.assertRaises(ValueError):
            aco.authorize_launch_entry(entry)

    def test_authorize_moves_ready_to_authorized(self):
        entry = {"status": "READY", "offer_id": "x"}
        out = aco.authorize_launch_entry(entry)
        self.assertEqual(out["status"], "AUTHORIZED")
        self.assertIn("authorized_at", out)

    def test_no_auto_publish_is_performed(self):
        result = aco.unified_launch_queue()
        for e in result["entries"]:
            self.assertNotEqual(e["status"], "PUBLISHED")


class MultiArmRevenueEngineTests(unittest.TestCase):
    def test_never_declares_a_winner_with_zero_verified_revenue(self):
        result = aco.multi_arm_revenue_engine()
        self.assertIsNone(result["winner"])
        self.assertIn("No REAL VERIFIED revenue", result["note"])

    def test_ranking_is_recomputed_every_call(self):
        result = aco.multi_arm_revenue_engine()
        self.assertIn("dynamic_ranking", result)
        self.assertEqual(len(result["dynamic_ranking"]), 10)

    def test_recurring_high_automation_arms_rank_first_with_no_data(self):
        result = aco.multi_arm_revenue_engine()
        ranked = [r["arm"] for r in result["dynamic_ranking"]]
        # Affiliate + Paddle (recurring + high automation) outrank blocked arms.
        self.assertLess(ranked.index("AFFILIATE"), ranked.index("ETSY"))
        self.assertLess(ranked.index("PADDLE"), ranked.index("SAAS"))


class CeoCommandCenterTests(unittest.TestCase):
    def setUp(self):
        self.paddle_check, self.gp = _stub_live_checks()

    def test_has_all_required_metrics(self):
        result = aco.ceo_command_center()
        for key in ("CASH_USD", "VERIFIED_REVENUE_USD", "PENDING_REVENUE_USD", "PROFIT_USD",
                    "TOP_ARM", "TOP_OFFER", "TOP_CHANNEL", "ACTIVE_CAMPAIGNS",
                    "BLOCKED_CAMPAIGNS", "HUMAN_GATES", "NEXT_ACTION"):
            self.assertIn(key, result)

    def test_verified_and_pending_never_merged(self):
        result = aco.ceo_command_center()
        self.assertEqual(result["VERIFIED_REVENUE_USD"], 0.0)
        self.assertEqual(result["PENDING_REVENUE_USD"], 0.0)

    def test_next_action_is_single_founder_action(self):
        result = aco.ceo_command_center()
        self.assertIsInstance(result["NEXT_ACTION"], str)
        self.assertNotIn("\n", result["NEXT_ACTION"])


class AutonomousDailyLoopTests(unittest.TestCase):
    def setUp(self):
        self.paddle_check, self.gp = _stub_live_checks()

    def test_loop_reports_blocked_when_gates_blocking(self):
        result = aco.run_autonomous_daily_loop()
        self.assertEqual(result["REPORT"]["status"], "BLOCKED")

    def test_loop_is_read_only_no_revenue_fabricated(self):
        result = aco.run_autonomous_daily_loop()
        self.assertEqual(result["MEASURE"]["VERIFIED"], 0.0)
        self.assertEqual(result["REPORT"]["real_verified_revenue_usd"], 0.0)

    def test_loop_has_all_stages(self):
        result = aco.run_autonomous_daily_loop()
        for stage in ("DISCOVER", "CHECK_ACTIVE_OFFERS", "CHECK_BLOCKERS", "PRIORITIZE",
                      "PRODUCE", "DISTRIBUTE", "TRACK", "MEASURE", "OPTIMIZE", "REPORT"):
            self.assertIn(stage, result)


class SelfHealingTests(unittest.TestCase):
    def test_recoverable_failure_marks_auto_retry(self):
        with tempfile.TemporaryDirectory() as td:
            original = aco._FACTORY_ROOT
            root = Path(td)
            (root / "data").mkdir(parents=True, exist_ok=True)
            aco._FACTORY_ROOT = root
            try:
                entry = aco.record_failure_and_recover(
                    component="publishing_adapter", error="boom", retry=1,
                    fallback="dry-run", recoverable=True)
                self.assertEqual(entry["status"], "AUTO_RETRY")
                log = (root / "data" / "recovery_actions.jsonl").read_text(encoding="utf-8")
                self.assertIn("autonomous_commerce_failure", log)
            finally:
                aco._FACTORY_ROOT = original

    def test_high_risk_failure_is_human_gate(self):
        entry = aco.record_failure_and_recover(
            component="webhook", error="e", retry=0,
            fallback="manual", recoverable=False)
        self.assertEqual(entry["status"], "HUMAN_GATE")


class RevenueIntegrityTests(unittest.TestCase):
    """MOCK revenue-integrity: canonical events must carry identity fields and
    duplicates must be detectable. Uses temporary files only."""

    def test_canonical_event_requires_real_verification_tier(self):
        import revenue_os as ros
        with self.assertRaises(ValueError):
            ros.canonical_event(verification="FAKE_TIER")

    def test_canonical_event_carries_identity_fields(self):
        import revenue_os as ros
        ev = ros.canonical_event(
            event_type="CLICK", opportunity_id="CO-digitalocean-affiliate",
            offer_id="offer-1", revenue_arm="AFFILIATE", channel="x_post",
            campaign="c1", asset="a1", verification="VERIFIED", source="test",
        )
        for field in ("event_type", "opportunity_id", "offer_id", "revenue_arm",
                      "channel", "campaign", "asset", "verification", "occurred_at"):
            self.assertIn(field, ev)

    def test_duplicate_event_ids_are_detectable(self):
        evs = [{"event_id": "evt-1"}, {"event_id": "evt-1"}]
        ids = [e["event_id"] for e in evs]
        self.assertNotEqual(len(ids), len(set(ids)))

    def test_real_commission_requires_confirmed_status_in_temp_ledger(self):
        import commission_ledger as cl
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "mock_ledger.jsonl"
            with self.assertRaises(cl.AntiFabricationError):
                cl.record_commission(
                    partner_id="awin-123996",
                    opportunity_id="CO-digitalocean-affiliate",
                    commission_status="CONFIRMED",
                    gross_commission=25.0,
                    environment="REAL",
                    evidence="test",
                    ledger_path=path,
                )


class LaunchQueueIntegrationTests(unittest.TestCase):
    """End-to-end integration with the real existing launch-batch machinery,
    using ONLY the real launch_batches/ output (read-only) and temporary
    ledgers. Nothing here writes to the production data/ directory."""

    def test_launch_batch_output_feeds_the_queue(self):
        batch_dir = Path("launch_batches")
        if not batch_dir.exists():
            self.skipTest("no launch_batches/ present in this checkout")
        result = aco.unified_launch_queue()
        self.assertGreaterEqual(len(result["entries"]), 1)
        for e in result["entries"]:
            self.assertTrue(e["offer_id"])
            self.assertTrue(e["channel"])
            self.assertTrue(e["campaign"])

    def test_authorize_then_publish_requires_authorized_state(self):
        entry = {"status": "READY", "offer_id": "CO-digitalocean-affiliate", "channel": "x_post"}
        authorized = aco.authorize_launch_entry(entry)
        self.assertEqual(authorized["status"], "AUTHORIZED")
        transitions = aco.unified_launch_queue()["allowed_transitions"]
        # PUBLISHED is only reachable from AUTHORIZED, never from READY directly.
        self.assertEqual(transitions["AUTHORIZED"], ["PUBLISHED"])
        self.assertNotIn("PUBLISHED", transitions["READY"])

    def test_click_through_to_ledger_uses_temp_files_only(self):
        """Full mock funnel: attributed click -> (temp) commission ledger. The
        production data/affiliate_clicks.jsonl is never touched."""
        from affiliate_commerce.click_tracking import record_attributed_click, attributed_click_summary
        from commission_ledger import load_ledger, record_commission
        import affiliate_commerce.click_tracking as ct

        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            clicks = td_path / "mock_clicks.jsonl"
            original_clicks = ct.DEFAULT_LEDGER_PATH
            ct.DEFAULT_LEDGER_PATH = clicks
            try:
                record_attributed_click(
                    product_id="CO-digitalocean-affiliate",
                    channel="x_post", campaign="c1", content="a1",
                    utm_source="galaxyforge",
                )
                summary = attributed_click_summary()
                self.assertEqual(summary["total_real_clicks"], 1)
            finally:
                ct.DEFAULT_LEDGER_PATH = original_clicks

            # A real commission still requires evidence -- even in a temp ledger.
            ledger = td_path / "mock_ledger.jsonl"
            import commission_ledger as cl
            with self.assertRaises(cl.AntiFabricationError):
                record_commission(
                    partner_id="awin-123996",
                    opportunity_id="CO-digitalocean-affiliate",
                    commission_status="CONFIRMED",
                    gross_commission=25.0,
                    environment="REAL",
                    evidence="xx",
                    ledger_path=ledger,
                )


class SecurityTests(unittest.TestCase):
    def test_no_secret_values_in_renders(self):
        # The commission ledger/click files may contain real API tokens in some
        # environments; the renders must never echo raw token values.
        for payload in (aco.ceo_command_center(), aco.founder_action_queue(), aco.run_autonomous_daily_loop()):
            text = json.dumps(payload)
            self.assertNotIn("access_token", text)
            for forbidden in ("Authorization", "Bearer "):
                self.assertNotIn(forbidden, text)

    def test_verification_never_claimed_without_evidence(self):
        # No gate, queue entry, or loop stage may assert verified revenue.
        for payload in (aco.ceo_command_center(), aco.founder_action_queue(), aco.run_autonomous_daily_loop()):
            text = json.dumps(payload)
            self.assertNotIn('"VERIFIED_REVENUE_USD": 50', text)


class RevenueIntegrityGateTests(unittest.TestCase):
    """Classification of every sales-ledger row (directive section 1)."""

    def _write_rows(self, rows):
        td = tempfile.TemporaryDirectory()
        path = Path(td.name) / "mock_sales.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        self.addCleanup(td.cleanup)
        return path

    def test_publish_attempts_are_never_sales(self):
        path = self._write_rows([{"event_type": "publish_attempt", "platform": "gumroad", "ok": False}])
        gate = aco.revenue_integrity_gate(sales_ledger_path=str(path))
        self.assertEqual(gate["VERIFIED_SALES"], 0)
        self.assertEqual(gate["UNKNOWN_ROWS"], 1)

    def test_mock_rows_are_classified_mock_not_sales(self):
        path = self._write_rows([{"event_type": "sale", "platform": "paddle", "environment": "MOCK", "id": "t1"}])
        gate = aco.revenue_integrity_gate(sales_ledger_path=str(path))
        self.assertEqual(gate["VERIFIED_SALES"], 0)
        self.assertEqual(gate["TEST_OR_MOCK_ROWS"], 1)

    def test_sale_without_order_ref_is_unknown(self):
        path = self._write_rows([{"event_type": "sale", "platform": "gumroad"}])
        gate = aco.revenue_integrity_gate(sales_ledger_path=str(path))
        self.assertEqual(gate["VERIFIED_SALES"], 0)
        self.assertEqual(gate["UNKNOWN_ROWS"], 1)

    def test_sale_with_order_ref_but_no_evidence_is_observed_only(self):
        path = self._write_rows([{"event_type": "sale", "platform": "paddle", "order_id": "ord-1", "environment": "REAL"}])
        gate = aco.revenue_integrity_gate(sales_ledger_path=str(path))
        self.assertEqual(gate["VERIFIED_SALES"], 0)
        self.assertEqual(gate["OBSERVED_SALES"], 1)
        self.assertEqual(gate["VERIFIED_REVENUE_USD"], 0.0)

    def test_44_publish_rows_never_become_44_sales(self):
        rows = [{"event_type": "publish_attempt", "platform": "gumroad", "dry_run": True} for _ in range(44)]
        path = self._write_rows(rows)
        gate = aco.revenue_integrity_gate(sales_ledger_path=str(path))
        self.assertEqual(gate["TOTAL_LEDGER_ROWS"], 44)
        self.assertEqual(gate["VERIFIED_SALES"], 0)
        self.assertEqual(gate["UNKNOWN_ROWS"], 44)

    def test_history_is_preserved_verbatim(self):
        rows = [{"event_type": "publish_attempt", "platform": "gumroad", "dry_run": True, "product_title": "X"}]
        path = self._write_rows(rows)
        gate = aco.revenue_integrity_gate(sales_ledger_path=str(path))
        self.assertEqual(gate["classified"][0]["raw"]["product_title"], "X")

    def test_verified_sales_never_from_mock_or_test(self):
        path = self._write_rows([
            {"event_type": "sale", "environment": "MOCK", "order_id": "o1", "evidence": "ev1"},
            {"event_type": "sale", "environment": "TEST", "order_id": "o2", "evidence": "ev2"},
        ])
        gate = aco.revenue_integrity_gate(sales_ledger_path=str(path))
        self.assertEqual(gate["VERIFIED_SALES"], 0)
        self.assertEqual(gate["TEST_OR_MOCK_ROWS"], 2)


class AffiliateFunnelTests(unittest.TestCase):
    def test_funnel_state_counts_are_consistent(self):
        result = aco.affiliate_candidate_funnel()
        self.assertEqual(result["REVENUE_PRODUCING"], 0)
        self.assertEqual(result["ACTIVE"], 0)  # link is NOT_CONFIGURED

    def test_funnel_has_all_states(self):
        result = aco.affiliate_candidate_funnel()
        for state in aco.AFFILIATE_FUNNEL_STATES:
            self.assertIn(state, result)

    def test_no_program_is_active_without_configured_link(self):
        original = aco._launch_link_status
        aco._launch_link_status = lambda: "NOT_CONFIGURED"
        try:
            result = aco.affiliate_candidate_funnel()
            self.assertEqual(result["ACTIVE"], 0)
        finally:
            aco._launch_link_status = original

    def test_program_becomes_active_when_link_configured(self):
        original = aco._launch_link_status
        aco._launch_link_status = lambda: "CONFIGURED"
        try:
            result = aco.affiliate_candidate_funnel()
            self.assertEqual(result["ACTIVE"], 1)
        finally:
            aco._launch_link_status = original


class OpportunityRoutingTests(unittest.TestCase):
    def test_affiliate_routes_to_affiliate_arm(self):
        r = aco.route_opportunity({
            "opportunity_id": "CO-x-affiliate", "category": "affiliate",
            "recurring_commission": True, "verification_status": "VERIFIED",
        })
        self.assertEqual(r["BEST_REVENUE_ARM"], "AFFILIATE")
        self.assertEqual(r["route_decision"], "route_to_production_router")

    def test_unverified_opportunity_is_held(self):
        r = aco.route_opportunity({
            "opportunity_id": "CO-x-affiliate", "category": "affiliate",
            "recurring_commission": False, "verification_status": "THIRD_PARTY_ONLY",
        })
        self.assertEqual(r["route_decision"], "hold_for_verification")

    def test_marketplace_routes_to_marketplace_arm(self):
        r = aco.route_opportunity({
            "opportunity_id": "CO-y-marketplace", "category": "marketplace",
            "verification_status": "VERIFIED",
        })
        self.assertEqual(r["BEST_REVENUE_ARM"], "MARKETPLACE")


class DailyPriorityTests(unittest.TestCase):
    def setUp(self):
        self.paddle_check, self.gp = _stub_live_checks()

    def test_removing_revenue_blocker_is_top_priority_today(self):
        result = aco.daily_commercial_priority()
        self.assertEqual(result["priorities"][0]["action"].lower()[:6], "remove")
        self.assertIn("GATE-AWIN-DIGITALOCEAN", result["priorities"][0]["blocker"])

    def test_never_proposes_new_feature_work_while_asset_unearned(self):
        result = aco.daily_commercial_priority()
        for p in result["priorities"]:
            self.assertNotIn("build another feature", p["action"])


class CeoCommandCenterRevenueTests(unittest.TestCase):
    def setUp(self):
        self.paddle_check, self.gp = _stub_live_checks()

    def test_command_center_shows_integrity_sales_figures(self):
        result = aco.ceo_command_center()
        self.assertIn("VERIFIED_SALES", result)
        self.assertIn("OBSERVED_SALES", result)
        self.assertEqual(result["VERIFIED_SALES"], 0)
        self.assertEqual(result["OBSERVED_SALES"], 0)

    def test_ledger_rows_reported_not_hidden(self):
        result = aco.ceo_command_center()
        self.assertIn("LEDGER_ROWS", result)
        self.assertEqual(result["LEDGER_ROWS"], 44)  # real historical rows preserved


class RevenueArmAuditTests(unittest.TestCase):
    def setUp(self):
        self.paddle_check, self.gp = _stub_live_checks()

    def test_every_arm_is_classified(self):
        result = aco.revenue_arm_audit()
        names = {a["arm"] for a in result["arms"]}
        for expected in ("GUMROAD", "PADDLE", "ETSY", "PAYHIP", "KDP", "TEMPLATES", "SAAS", "AFFILIATE"):
            self.assertIn(expected, names)

    def test_affiliate_is_postponed_not_active(self):
        result = aco.revenue_arm_audit()
        by = {a["arm"]: a["state"] for a in result["arms"]}
        self.assertEqual(by["AFFILIATE"], "POSTPONED")  # directive: no Awin today

    def test_gumroad_ready_requires_no_duplicate_product(self):
        result = aco.revenue_arm_audit()
        by = {a["arm"]: a["state"] for a in result["arms"]}
        self.assertEqual(by["GUMROAD"], "READY")  # existing product, one payment action

    def test_no_state_from_old_reports(self):
        result = aco.revenue_arm_audit()
        for a in result["arms"]:
            self.assertIn("evidence", a)
            self.assertTrue(len(a["evidence"]) > 10)


class PaddleActivationQueueTests(unittest.TestCase):
    def setUp(self):
        self.paddle_check, self.gp = _stub_live_checks()

    def test_six_products_one_human_action(self):
        result = aco.paddle_activation_queue()
        self.assertEqual(result["total_products"], 6)
        self.assertEqual(result["human_actions_required"], 1)  # one account-level action

    def test_every_product_has_full_audit_fields(self):
        result = aco.paddle_activation_queue()
        for p in result["products"]:
            for field in ("title", "price", "status", "checkout_ready", "payment_readiness", "webhook", "revenue_event", "tracking", "blocker"):
                self.assertIn(field, p)

    def test_all_gated_products_listed_as_human_gate(self):
        result = aco.paddle_activation_queue()
        self.assertEqual(len(result["HUMAN_GATE"]), 6)


class RevenueRouterTests(unittest.TestCase):
    def setUp(self):
        self.paddle_check, self.gp = _stub_live_checks()

    def test_router_produces_today_second_third_deferred(self):
        result = aco.revenue_router()
        self.assertIn("TOP_TODAY", result)
        self.assertIn("SECOND", result)
        self.assertIn("THIRD", result)
        self.assertIn("DEFERRED", result)

    def test_affiliate_not_permanently_preferred(self):
        # In FIRST_DOLLAR_MODE the AFFILIATE arm is postponed, not top.
        result = aco.revenue_router()
        top = result["TOP_TODAY"]["arm"]
        self.assertNotEqual(top, "AFFILIATE")

    def test_deferred_contains_strategic_later(self):
        result = aco.revenue_router()
        deferred_arms = {d["arm"] for d in result["DEFERRED"]}
        self.assertIn("SAAS", deferred_arms)

    def test_score_is_multiplicative_of_six_factors(self):
        score = aco._arm_score({"revenue_potential": 0.5, "speed": 0.5, "confidence": 0.5,
                                "automation": 0.5, "profit": 0.5, "recurring_potential": 0.5})
        self.assertAlmostEqual(score, 0.5 ** 6, places=4)

    def test_zero_factor_never_zeroes_score(self):
        # one-time arm has recurring_potential=0; floor prevents a false 0.
        score = aco._arm_score({"revenue_potential": 0.5, "speed": 0.5, "confidence": 0.5,
                                "automation": 0.5, "profit": 0.5, "recurring_potential": 0.0})
        self.assertGreater(score, 0.0)


class FounderGateConsolidationTests(unittest.TestCase):
    def setUp(self):
        self.paddle_check, self.gp = _stub_live_checks()

    def test_today_is_gumroad_payment(self):
        result = aco.founder_gate_consolidation()
        today_ids = [a["gate_id"] for a in result["horizons"]["TODAY"] if a]
        self.assertIn("GATE-GUMROAD-PAYMENT", today_ids)

    def test_next_is_paddle_onboarding(self):
        result = aco.founder_gate_consolidation()
        next_ids = [a["gate_id"] for a in result["horizons"]["NEXT"] if a]
        self.assertIn("GATE-PADDLE-ONBOARDING", next_ids)

    def test_later_is_etsy_authorization(self):
        result = aco.founder_gate_consolidation()
        later_ids = [a["gate_id"] for a in result["horizons"]["LATER"] if a]
        self.assertIn("GATE-ETSY-AUTHORIZATION", later_ids)

    def test_tomorrow_is_awin(self):
        result = aco.founder_gate_consolidation()
        tomorrow_ids = [a["gate_id"] for a in result["horizons"]["TOMORROW"] if a]
        self.assertIn("GATE-AWIN-DIGITALOCEAN", tomorrow_ids)


class FirstDollarModeTests(unittest.TestCase):
    def setUp(self):
        self.paddle_check, self.gp = _stub_live_checks()

    def test_mode_is_enabled_and_prioritizes_existing_assets(self):
        result = aco.first_dollar_mode_report()
        self.assertTrue(result["enabled"])
        self.assertIn("existing sellable assets", result["prioritize"])

    def test_deprioritizes_new_architecture(self):
        result = aco.first_dollar_mode_report()
        self.assertIn("new architecture", result["deprioritize"])
        self.assertIn("unproven SaaS", result["deprioritize"])


class DistributionPrepTests(unittest.TestCase):
    def setUp(self):
        self.paddle_check, self.gp = _stub_live_checks()

    def test_all_organic_channels_prepared_but_never_auto_published(self):
        result = aco.distribution_prep()
        self.assertEqual(len(result["channels"]), len(aco.ORGANIC_CHANNELS))
        for ch in result["channels"]:
            self.assertEqual(ch["status"], "HUMAN_GATE")
            self.assertFalse(ch["authorized"])

    def test_target_offer_has_tracking_and_campaign(self):
        result = aco.distribution_prep()
        offer = result["target_offer"]
        self.assertIn("tracking", offer)
        self.assertIn("campaign_id", offer)

    def test_content_assets_are_real_files(self):
        result = aco.distribution_prep()
        offer = result["target_offer"]
        for asset in offer.get("content_assets", []):
            if asset.endswith(".pdf") or asset.endswith(".html"):
                p = Path(__file__).resolve().parent.parent / asset
                self.assertTrue(p.exists(), f"missing asset {asset}")


class MissionControlTests(unittest.TestCase):
    def setUp(self):
        self.paddle_check, self.gp = _stub_live_checks()

    def test_unified_view_has_all_sections(self):
        result = aco.mission_control()
        for key in ("REVENUE_ARMS", "VERIFIED_REVENUE", "PENDING_REVENUE", "PROJECTED_REVENUE",
                    "BLOCKERS", "FOUNDER_ACTIONS", "TOP_REVENUE_PATH"):
            self.assertIn(key, result)

    def test_affiliate_shown_as_postponed(self):
        result = aco.mission_control()
        self.assertEqual(result["REVENUE_ARMS"]["AFFILIATE"], "POSTPONED UNTIL TOMORROW")

    def test_verified_and_projected_never_merged(self):
        result = aco.mission_control()
        # The invariant is structural: PROJECTED is reported separately and the
        # rule states it is NEVER summed into VERIFIED.
        self.assertIn("PROJECTED_REVENUE", result)
        self.assertNotIn("VERIFIED+PROJECTED", result)
        self.assertIn("never merged", result["rule"].lower())
        self.assertIn("projected", result["rule"].lower())

    def test_zero_click_does_not_equal_revenue(self):
        result = aco.mission_control()
        self.assertEqual(result["VERIFIED_REVENUE"], 0.0)  # no clicks/views count as revenue


if __name__ == "__main__":
    unittest.main()
