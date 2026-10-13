# -*- coding: utf-8 -*-
"""Evidence-integrity guard for the market-evidence checkout signals (c105).

Root cause this guards against
------------------------------
`market_evidence_loop.py` emits two events from OUR OWN server-side HTTP GET
of a public product URL:

    checkout_observed / CHECKOUT_STARTED
    checkout_failure  / CHECKOUT_BLOCKED

Both used to carry evidence_class="OBSERVED", verification_status="VERIFIED",
confidence="high". Nothing in the row said that the only actor was this
factory's poller, so a ledger reader (dashboard, report, or agent) saw

    50 x checkout_observed  CHECKOUT_STARTED  VERIFIED
    75 x checkout_failure   CHECKOUT_BLOCKED  VERIFIED

and could conclude 50 buyers started a checkout and 75 were blocked at it.
Both readings are false, and the batch timestamps prove no human is involved
(every batch spans 6-56 milliseconds -- a poll, not a person).

What is asserted here
---------------------
1. Every emitted event declares its actor, so it can never be read as demand.
2. No emitted event may claim a human initiated it.
3. The word "BLOCKED" is not used as an event status any more, because that
   name asserts a proven commercial obstacle for a signal that only says our
   own fetch missed the URL.
4. The financial stages stay unreachable from these factory signals.
"""
import ast
import os
import unittest

FACTORY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = os.path.join(FACTORY_DIR, "market_evidence_loop.py")


class TestFetchSignalDisambiguation(unittest.TestCase):
    def setUp(self):
        import market_evidence_loop as mel
        self.mel = mel

    def test_signal_declares_its_actor_and_humility(self):
        sig = self.mel.FACTORY_FETCH_SIGNAL
        self.assertEqual(sig["actor"], "FACTORY_MONITOR")
        self.assertIs(sig["human_initiated"], False)
        self.assertEqual(sig["signal_kind"], "SERVER_SIDE_HTTP_REACHABILITY")
        self.assertIn("does_not_prove", sig)
        # The disclaimer must actually deny demand, not just exist.
        self.assertIn("Demand is UNPROVEN", sig["does_not_prove"])

    def test_new_status_never_asserts_a_proven_blocker(self):
        self.assertNotIn("BLOCK", self.mel.CHECKOUT_UNREACHABLE_STATUS)
        self.assertEqual(
            self.mel.CHECKOUT_UNREACHABLE_STATUS,
            "CHECKOUT_PAGE_UNREACHABLE_ON_FETCH")

    def test_no_emitted_event_literals_leave_a_fetch_unguarded(self):
        """Every dict literal carrying a checkout_* event_type must spread
        FACTORY_FETCH_SIGNAL, so a future edit cannot drop the disambiguation."""
        tree = ast.parse(open(MODULE_PATH, encoding="utf-8").read())

        checked = 0
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            keys = [k.value for k in node.keys
                    if isinstance(k, ast.Constant) and isinstance(k.value, str)]
            if "event_type" not in keys:
                continue
            # find the event_type value
            et = None
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and k.value == "event_type" \
                        and isinstance(v, ast.Constant):
                    et = v.value
            if et not in ("checkout_observed", "checkout_failure"):
                continue
            checked += 1
            # `{**FACTORY_FETCH_SIGNAL}` unpacks as a None key in the AST.
            has_spread = any(
                k is None and isinstance(v, ast.Name)
                and v.id == "FACTORY_FETCH_SIGNAL"
                for k, v in zip(node.keys, node.values))
            self.assertTrue(
                has_spread,
                "%s event literal at line %d does not spread "
                "FACTORY_FETCH_SIGNAL" % (et, node.lineno))
        self.assertGreaterEqual(checked, 2,
                                "expected both checkout event literals to be found")

    def test_factory_signals_cannot_reach_financial_stages(self):
        """A reachability fetch must never advance to money stages."""
        for stage in ("TRANSACTION_COMPLETED", "REVENUE_VERIFIED",
                      "PAYOUT_VERIFIED"):
            self.assertNotEqual(stage, self.mel.CHECKOUT_STAGE)
            self.assertNotEqual(stage, self.mel.CHECKOUT_UNREACHABLE_STATUS)
        # Money only ever arrives through the payment ledger.
        self.assertIn("sale", self.mel.PAYMENT_EVENT_TYPES)


if __name__ == "__main__":
    unittest.main()
