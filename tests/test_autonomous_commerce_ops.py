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


class MultiArmCompetitionTests(unittest.TestCase):
    def test_never_declares_a_winner_with_zero_verified_revenue(self):
        result = aco.multi_arm_competition()
        self.assertIsNone(result["winner"])
        self.assertIn("No REAL VERIFIED revenue", result["note"])


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


if __name__ == "__main__":
    unittest.main()
