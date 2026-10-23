"""Affiliate end-to-end simulation (scripts/affiliate_e2e_simulation.py) and
the repairs it drove (2026-10-23): commission status changes, latest-state
and per-currency revenue, unique commission ids, destination validation,
evidence-backed program approvals. Temp files only; no network."""
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import affiliate_e2e_simulation as sim  # noqa: E402
import commission_ledger as cl  # noqa: E402
from affiliate import links, registry  # noqa: E402

NOW = datetime(2026, 10, 23, tzinfo=timezone.utc)


def tmp(name="l.jsonl"):
    return Path(tempfile.mkdtemp()) / name


class TestSimulation(unittest.TestCase):
    def test_every_scenario_passes_and_touches_only_temp_files(self):
        before = (ROOT / "data" / "commission_ledger.jsonl").read_bytes() if (ROOT / "data" / "commission_ledger.jsonl").exists() else None
        r = sim.run(Path(tempfile.mkdtemp()))
        fails = [s for s in r.scenarios if s["result"] == "FAIL"]
        self.assertEqual(fails, [])
        self.assertEqual({s["scenario"] for s in r.scenarios}, set("ABCDEFGHIJ"))
        after = (ROOT / "data" / "commission_ledger.jsonl").read_bytes() if (ROOT / "data" / "commission_ledger.jsonl").exists() else None
        self.assertEqual(before, after, "production ledger untouched")


class TestCommissionStates(unittest.TestCase):
    def rec(self, led, tx, status="PENDING", amt=10.0, env="REAL", cur="USD"):
        return cl.record_commission("p", "o", status, amt, env, evidence="network event ref 1",
                                    external_transaction_id=tx, currency=cur, ledger_path=led, now=NOW)

    def test_status_changes_live_beside_the_ledger_and_load_ledger_is_unchanged(self):
        led = tmp()
        self.rec(led, "tx-001")
        cl.record_status_change("tx-001", "CONFIRMED", "REAL", evidence="approval notice 1", ledger_path=led, now=NOW)
        self.assertEqual(len(cl.load_ledger(led)), 1)
        self.assertTrue(cl.status_path(led).exists())
        self.assertEqual(cl.transaction_states(led, "REAL")["tx-001"]["status"], "CONFIRMED")

    def test_real_change_needs_evidence_and_a_known_transaction_and_a_legal_transition(self):
        led = tmp()
        self.rec(led, "tx1")
        with self.assertRaises(cl.AntiFabricationError):
            cl.record_status_change("tx1", "CONFIRMED", "REAL", evidence="", ledger_path=led)
        with self.assertRaises(ValueError):
            cl.record_status_change("nope", "CONFIRMED", "REAL", evidence="approval notice 1", ledger_path=led)
        with self.assertRaises(ValueError):
            cl.record_status_change("tx1", "SETTLED", "REAL", evidence="approval notice 1", ledger_path=led)
        cl.record_status_change("tx1", "REFUNDED", "REAL", evidence="refund notice 1", ledger_path=led)
        with self.assertRaises(ValueError):
            cl.record_status_change("tx1", "PAID", "REAL", evidence="payout notice 1", ledger_path=led)

    def test_revenue_uses_latest_state_and_separates_currencies(self):
        led = tmp()
        self.rec(led, "tx-a", "CONFIRMED", 20.0)
        self.rec(led, "tx-b", "PAID", 40.0)
        self.rec(led, "tx-c", "CONFIRMED", 15.0, cur="EUR")
        self.rec(led, "tx-d", "CONFIRMED", 99.0)
        cl.record_status_change("tx-d", "REVERSED", "REAL", evidence="reversal notice 1", ledger_path=led)
        s = cl.real_commission_summary(led)
        self.assertEqual(s["real_confirmed_or_paid_commission_usd"], 60.0)
        self.assertEqual(s["real_paid_commission_usd"], 40.0)
        self.assertEqual(s["real_confirmed_or_paid_by_currency"], {"USD": 60.0, "EUR": 15.0})
        self.assertEqual(s["real_reversed_or_refunded_records"], 1)
        self.assertTrue(cl.first_real_dollar_status(led)["FIRST_REAL_DOLLAR"])

    def test_a_reversed_only_ledger_has_no_first_dollar(self):
        led = tmp()
        self.rec(led, "tx-a", "CONFIRMED", 20.0)
        cl.record_status_change("tx-a", "REVERSED", "REAL", evidence="reversal notice 1", ledger_path=led)
        self.assertFalse(cl.first_real_dollar_status(led)["FIRST_REAL_DOLLAR"])

    def test_pending_without_transaction_id_cannot_be_confirmed_by_a_status_change(self):
        led = tmp()
        r = cl.record_commission("p", "o", "PENDING", 10.0, "REAL", evidence="referral note 1", ledger_path=led, now=NOW)
        with self.assertRaises(cl.AntiFabricationError):
            cl.record_status_change(r["commission_id"], "CONFIRMED", "REAL", evidence="approval notice 1", ledger_path=led)
        self.assertEqual(cl.real_commission_summary(led)["real_confirmed_or_paid_commission_usd"], 0)

    def test_simulation_never_reaches_real_totals(self):
        led = tmp()
        self.rec(led, "s", "PAID", 500.0, env="SIMULATION")
        self.assertEqual(cl.real_commission_summary(led)["real_confirmed_or_paid_commission_usd"], 0)

    def test_ids_unique_within_one_second(self):
        led = tmp()
        for i in range(5):
            cl.record_commission("p", "o", "PENDING", 1.0, "SIMULATION", ledger_path=led, now=NOW)
        ids = [r["commission_id"] for r in cl.load_ledger(led)]
        self.assertEqual(len(set(ids)), 5)


class TestDestinations(unittest.TestCase):
    def test_subdomain_allowed_lookalikes_refused(self):
        self.assertTrue(links.validate_destination("https://www.acme.example/x?ref=1", "acme.example")["ok"])
        for bad in ("https://acmeexample.com/", "https://acme.example@evil.example/", "ftp://acme.example/",
                    "https://acme.example/?next=//evil.example/", "https://acme.example/?url=https%3A%2F%2Fevil.example"):
            self.assertFalse(links.validate_destination(bad, "acme.example")["ok"], bad)

    def test_same_domain_redirect_parameter_allowed(self):
        self.assertTrue(links.validate_destination("https://acme.example/login?next=https://app.acme.example/", "acme.example")["ok"])


class TestApprovals(unittest.TestCase):
    def test_latest_approval_wins_and_rejection_overrides(self):
        p = tmp()
        opp = {"opportunity_id": "CO-x", "partner_id": "x", "verification_status": "VERIFIED", "evidence_url": "https://x.example"}
        registry.record_approval("CO-x", "APPLIED", None, approvals_path=p)
        self.assertEqual(registry.program_record(opp, [], [], registry.latest_approvals(p))["affiliate_status"], "APPLIED")
        registry.record_approval("CO-x", "REJECTED", "rejection email 2026-10-24", approvals_path=p)
        self.assertEqual(registry.program_record(opp, [], [], registry.latest_approvals(p))["affiliate_status"], "REJECTED")

    def test_invalid_state_refused(self):
        self.assertFalse(registry.record_approval("CO-x", "ACTIVE", "x" * 20, approvals_path=tmp())["ok"])


if __name__ == "__main__":
    unittest.main()
