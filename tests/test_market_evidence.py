"""Isolated tests for market_evidence.py -- temp state/ledger only, never the
real data/ files and never any network."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import market_evidence_loop as me


def _write(path, rows):
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


class TestBaseline(unittest.TestCase):
    def test_baseline_stage_is_not_discovered(self):
        with tempfile.TemporaryDirectory() as d:
            lp = os.path.join(d, "ledger.jsonl")
            _write(lp, [{"event_type": "publish_attempt", "ok": True, "dry_run": False,
                         "product_source_id": "X-V1", "product_title": "X",
                         "url": "https://example.com/x", "platform": "gumroad"}])
            sp = os.path.join(d, "state.json")
            ep = os.path.join(d, "events.jsonl")
            out = me.run_cycle(state_path=sp, events_path=ep, ledger_path=lp,
                               live_urls=set(), day="2026-09-25")
            st = json.load(open(sp, encoding="utf-8"))
            self.assertEqual(st["X-V1"]["stage"], "NOT_DISCOVERED")
            self.assertEqual(out["material_changes"], [])

    def test_dry_run_and_failed_publishes_never_seed(self):
        with tempfile.TemporaryDirectory() as d:
            lp = os.path.join(d, "ledger.jsonl")
            _write(lp, [{"event_type": "publish_attempt", "ok": True, "dry_run": True,
                         "product_source_id": "D-V1"},
                        {"event_type": "publish_attempt", "ok": False, "dry_run": False,
                         "product_source_id": "F-V1"}])
            sp = os.path.join(d, "state.json")
            ep = os.path.join(d, "events.jsonl")
            out = me.run_cycle(state_path=sp, events_path=ep, ledger_path=lp,
                               live_urls=set(), day="2026-09-25")
            self.assertEqual(out["summary"]["products"], 0)


class TestPromotion(unittest.TestCase):
    def _base(self, d):
        lp = os.path.join(d, "ledger.jsonl")
        _write(lp, [{"event_type": "publish_attempt", "ok": True, "dry_run": False,
                     "product_source_id": "X-V1", "product_title": "X",
                     "url": "https://example.com/x", "platform": "gumroad"}])
        return lp

    def test_checkout_promotion_only_on_direct_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            lp = self._base(d)
            sp = os.path.join(d, "state.json")
            ep = os.path.join(d, "events.jsonl")
            me.run_cycle(state_path=sp, events_path=ep, ledger_path=lp,
                         live_urls=set(), day="2026-09-25")
            out = me.run_cycle(state_path=sp, events_path=ep, ledger_path=lp,
                               live_urls={"https://example.com/x"}, day="2026-09-25")
            self.assertEqual(len(out["material_changes"]), 1)
            self.assertEqual(out["material_changes"][0]["new_state"], "CHECKOUT_STARTED")
            self.assertEqual(out["material_changes"][0]["evidence_class"], "OBSERVED")

    def test_idempotent_second_run_appends_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            lp = self._base(d)
            sp = os.path.join(d, "state.json")
            ep = os.path.join(d, "events.jsonl")
            me.run_cycle(state_path=sp, events_path=ep, ledger_path=lp,
                         live_urls={"https://example.com/x"}, day="2026-09-25")
            out = me.run_cycle(state_path=sp, events_path=ep, ledger_path=lp,
                               live_urls={"https://example.com/x"}, day="2026-09-25")
            self.assertEqual(out["material_changes"], [])

    def test_checkout_failure_is_material(self):
        with tempfile.TemporaryDirectory() as d:
            lp = self._base(d)
            sp = os.path.join(d, "state.json")
            ep = os.path.join(d, "events.jsonl")
            me.run_cycle(state_path=sp, events_path=ep, ledger_path=lp,
                         live_urls={"https://example.com/x"}, day="2026-09-25")
            out = me.run_cycle(state_path=sp, events_path=ep, ledger_path=lp,
                               live_urls=set(), day="2026-09-25")
            kinds = [e["event_type"] for e in out["material_changes"]]
            self.assertIn("checkout_failure", kinds)


class TestPayments(unittest.TestCase):
    def test_only_real_payment_events_promote(self):
        with tempfile.TemporaryDirectory() as d:
            lp = os.path.join(d, "ledger.jsonl")
            _write(lp, [
                {"event_type": "publish_attempt", "ok": True, "dry_run": False,
                 "product_source_id": "X-V1", "url": "https://example.com/x", "platform": "gumroad"},
                {"event_type": "page_view", "ok": True, "product_source_id": "X-V1"},
                {"event_type": "sale", "ok": True, "test": True, "product_source_id": "X-V1"},
            ])
            sp = os.path.join(d, "state.json")
            ep = os.path.join(d, "events.jsonl")
            out = me.run_cycle(state_path=sp, events_path=ep, ledger_path=lp,
                               live_urls={"https://example.com/x"}, day="2026-09-25")
            kinds = [e["event_type"] for e in out["material_changes"]]
            self.assertNotIn("transaction_completed", kinds)

    def test_real_payment_promotes_exact_product_only(self):
        with tempfile.TemporaryDirectory() as d:
            lp = os.path.join(d, "ledger.jsonl")
            _write(lp, [
                {"event_type": "publish_attempt", "ok": True, "dry_run": False,
                 "product_source_id": "X-V1", "url": "https://example.com/x", "platform": "gumroad"},
                {"event_type": "publish_attempt", "ok": True, "dry_run": False,
                 "product_source_id": "Y-V1", "url": "https://example.com/y", "platform": "gumroad"},
                {"event_type": "sale", "ok": True, "product_source_id": "X-V1",
                 "transaction_id": "txn_1", "amount": 29.0},
            ])
            sp = os.path.join(d, "state.json")
            ep = os.path.join(d, "events.jsonl")
            out = me.run_cycle(state_path=sp, events_path=ep, ledger_path=lp,
                               live_urls={"https://example.com/x", "https://example.com/y"},
                               day="2026-09-25")
            by_product = {e["product"]: e["new_state"] for e in out["material_changes"]
                          if e["event_type"] == "transaction_completed"}
            self.assertEqual(by_product, {"X-V1": "TRANSACTION_COMPLETED"})
            st = json.load(open(sp, encoding="utf-8"))
            self.assertEqual(st["Y-V1"]["stage"], "CHECKOUT_STARTED")


if __name__ == "__main__":
    unittest.main()


class TestAttribution(unittest.TestCase):
    def _ledgers(self, d, views, clicks):
        vp = os.path.join(d, "views.jsonl")
        cp = os.path.join(d, "clicks.jsonl")
        with open(vp, "w", encoding="utf-8") as fh:
            for r in views:
                fh.write(json.dumps(r) + "\n")
        with open(cp, "w", encoding="utf-8") as fh:
            for r in clicks:
                fh.write(json.dumps(r) + "\n")
        return vp, cp

    def test_clean_external_requires_referrer_plus_browser(self):
        with tempfile.TemporaryDirectory() as d:
            vp, cp = self._ledgers(
                d,
                [{"page_id": "p1", "timestamp": "2026-09-25T10:00:00+00:00",
                  "referrer": "https://www.google.com/", "ua_category": "browser"},
                 {"page_id": "p2", "timestamp": "2026-09-25T10:00:00+00:00",
                  "referrer": "https://www.google.com/", "ua_category": "unknown"},
                 {"page_id": "p3", "timestamp": "2026-09-25T10:00:00+00:00",
                  "referrer": None, "ua_category": "browser"}],
                [])
            out = me.traffic_attribution(clicks_path=cp, views_path=vp)
            self.assertEqual(out["views"]["counters"]["CLEAN_EXTERNAL"], 1)
            self.assertEqual(out["views"]["counters"]["UNKNOWN"], 2)

    def test_bot_and_test_classes(self):
        with tempfile.TemporaryDirectory() as d:
            vp, cp = self._ledgers(
                d, [],
                [{"product_id": "CO-x", "timestamp": "2026-09-25T10:00:00+00:00",
                  "referrer": None, "ua_category": "bot"},
                 {"product_id": "qa-probe", "timestamp": "2026-09-25T10:00:00+00:00",
                  "referrer": "https://x/", "ua_category": "browser"}])
            out = me.traffic_attribution(clicks_path=cp, views_path=vp)
            self.assertEqual(out["clicks"]["counters"]["BOT"], 1)
            self.assertEqual(out["clicks"]["counters"]["TEST"], 1)

    def test_future_timestamp_is_anomaly_not_silently_fixed(self):
        with tempfile.TemporaryDirectory() as d:
            vp, cp = self._ledgers(
                d,
                [{"page_id": "p1", "timestamp": "2999-01-01T00:00:00+00:00",
                  "referrer": None}],
                [])
            out = me.traffic_attribution(clicks_path=cp, views_path=vp)
            self.assertEqual(len(out["anomalies"]), 1)
            self.assertEqual(out["anomalies"][0]["issue"], "future_timestamp")


class TestTrustLevels(unittest.TestCase):
    def test_ladder_never_exceeds_l2_without_corroboration(self):
        self.assertEqual(me.trust_level({})["level"], 0)
        self.assertEqual(me.trust_level(
            {"page_id": "x", "timestamp": "2026-09-25T00:00:00+00:00"})["level"], 0)
        self.assertEqual(me.trust_level(
            {"page_id": "qa-x", "timestamp": "2026-09-25T00:00:00+00:00",
             "referrer": "https://x/", "ua_category": "browser"})["level"], 1)
        self.assertEqual(me.trust_level(
            {"page_id": "x", "timestamp": "2026-09-25T00:00:00+00:00",
             "referrer": "https://x/", "ua_category": "browser"})["level"], 2)

    def test_historical_19_views_max_level(self):
        lv = [me.trust_level(
            {"page_id": ("mindfulness-test" if "mindfulness" in (r.get("page_id") or "") else r.get("page_id")),
             "timestamp": r.get("timestamp"), "referrer": r.get("referrer")})
            for r in ({"page_id": "solutions", "timestamp": "2026-08-09T10:35:37+00:00", "referrer": None},
                      {"page_id": "mindfulness-test", "timestamp": "2026-09-14T12:34:21+00:00", "referrer": None},
                      {"page_id": "guide-mindfulness-focus-for-founders", "timestamp": "2026-09-14T12:39:26+00:00", "referrer": None})]
        self.assertTrue(all(t["level"] <= 1 for t in lv))
        self.assertTrue(any(t["level"] == 1 for t in lv))  # test-marked row


class TestInvariants(unittest.TestCase):
    def test_revenue_requires_transaction(self):
        # Invariant: VERIFIED_REVENUE > 0 requires VERIFIED_TRANSACTION > 0.
        # The module has no revenue path except payment_events(); with zero
        # payment rows, no revenue figure can exist anywhere downstream.
        with tempfile.TemporaryDirectory() as d:
            lp = os.path.join(d, "ledger.jsonl")
            with open(lp, "w", encoding="utf-8") as fh:
                fh.write(json.dumps({"event_type": "publish_attempt", "ok": True,
                                     "dry_run": False, "product_source_id": "X"}) + "\n")
            self.assertEqual(me.payment_events(lp), [])
            st = me.status(ledger_path=lp,
                           state_path=os.path.join(d, "s.json"),
                           events_path=os.path.join(d, "e.jsonl"))
            self.assertEqual(st["payments"], 0)

    def test_test_fixture_cannot_be_financial(self):
        with tempfile.TemporaryDirectory() as d:
            lp = os.path.join(d, "ledger.jsonl")
            with open(lp, "w", encoding="utf-8") as fh:
                fh.write(json.dumps({"event_type": "sale", "ok": True, "test": True,
                                     "is_test": True, "amount": 9999.0}) + "\n")
            self.assertEqual(me.payment_events(lp), [])


class TestExternalProof(unittest.TestCase):
    def test_ledger_classes_sum_and_no_financial(self):
        with tempfile.TemporaryDirectory() as d:
            lp = os.path.join(d, "ledger.jsonl")
            rows = ([{"event_type": "publish_attempt", "ok": True, "dry_run": False}]
                    + [{"event_type": "publish_attempt", "ok": True, "dry_run": True}]
                    + [{"event_type": "publish_attempt", "ok": False, "dry_run": False}])
            with open(lp, "w", encoding="utf-8") as fh:
                for r in rows:
                    fh.write(json.dumps(r) + "\n")
            out = me.reconcile_ledgers(lp)
            self.assertEqual(out["classes"],
                             {"OPERATIONAL": 1, "TEST": 1, "ERROR": 1})
            self.assertEqual(out["financial_payments"], 0)

    def test_factory_telemetry_caps_at_technical_proof(self):
        with tempfile.TemporaryDirectory() as d:
            lp = os.path.join(d, "ledger.jsonl")
            with open(lp, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(
                    {"event_type": "publish_attempt", "ok": True, "dry_run": False,
                     "product_source_id": "X-V1", "url": "https://example.com/x",
                     "platform": "gumroad"}) + "\n")
            sp = os.path.join(d, "s.json")
            ep = os.path.join(d, "e.jsonl")
            me.run_cycle(state_path=sp, events_path=ep, ledger_path=lp,
                         live_urls={"https://example.com/x"}, day="2026-09-25")
            proof = me.commercial_proof_state(state_path=sp)
            self.assertEqual(proof["proof_state"], "EXTERNAL_TECHNICAL_PROOF")
            self.assertFalse(proof["independently_confirmed"])

    def test_matrix_never_claims_beyond_evidence(self):
        m = me.build_external_matrix(
            matrix_path=os.path.join(tempfile.mkdtemp(), "m.json"))
        for name, ms in m["milestones"].items():
            if ms["status"] == "UNKNOWN":
                self.assertFalse(ms["independently_confirmed"], name)
                self.assertEqual(ms["level"], "E0", name)
