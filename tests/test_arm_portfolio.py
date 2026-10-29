"""Arm taxonomy reconciliation and registry-derived Digital Products status (2026-10-29).

Pins three things:
  * the ten portfolio activities map onto the eight canonical doctrine arms
    without renumbering, adding or dropping a canonical arm;
  * Digital Products is restated from the product registry, and a sale on the
    registry is the only thing that can make it REVENUE_VERIFIED;
  * the control capabilities are advisory and never carry a business status.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import business_arms as ba  # noqa: E402


def registry(tmp, products):
    p = Path(tmp) / "product_registry.json"
    p.write_text(json.dumps({"generated_at": "2026-10-29T00:00:00Z", "products": products}), encoding="utf-8")
    return p


class Taxonomy(unittest.TestCase):
    def test_canonical_arms_unchanged(self):
        self.assertEqual(
            ["digital_products", "micro_b2b", "research_data_services", "affiliate_intelligence",
             "content_distribution", "ai_operations", "productized_ai_services", "childrens_media_studio"],
            list(ba.ARMS))

    def test_ten_activities_each_map_to_a_canonical_arm_or_say_none(self):
        self.assertEqual(10, len(ba.PORTFOLIO_ACTIVITIES))
        for key, act in ba.PORTFOLIO_ACTIVITIES.items():
            if act["arm"] is None:
                self.assertIn(act.get("nearest_arm"), ba.ARMS, key)
                self.assertTrue(act.get("note"), key)
            else:
                self.assertIn(act["arm"], ba.ARMS, key)

    def test_every_canonical_arm_is_reachable_from_the_portfolio(self):
        used = set()
        for act in ba.PORTFOLIO_ACTIVITIES.values():
            used.add(act.get("arm"))
            used.update(act.get("also") or [])
        self.assertEqual(set(ba.ARMS), used - {None})

    def test_portfolio_status_comes_from_the_arm(self):
        view = ba.portfolio_view()
        arms = ba.arm_status()["arms"]
        for row in view["activities"]:
            if row["arm"]:
                self.assertEqual(arms[row["arm"]]["status"], row["status"])
            else:
                self.assertIn(row["status"], ("PLANNED", "PARTIAL"))

    def test_controls_are_not_business_arms_and_name_their_rule(self):
        c = ba.control_status()
        self.assertEqual({"predictive_intelligence", "treasury_control"}, set(c))
        for cap in c.values():
            self.assertNotIn(cap["status"], ba.STATUSES)
            self.assertTrue(cap["rule"])
        self.assertIn("no module here initiates a payment", c["treasury_control"]["rule"])


class DigitalProductsFromRegistry(unittest.TestCase):
    def test_live_listings_without_sales_are_partial_not_blocked(self):
        with tempfile.TemporaryDirectory() as t:
            ev = ba._registry_evidence(registry(t, [
                {"published": True, "sales_count": 0, "sales_usd_cents": 0},
                {"published": False, "sales_count": 0}]))
        cfg = ba._digital_products_cfg(ba.ARMS["digital_products"], ev)
        arm = ba.evaluate_arm("digital_products", cfg, {"status": "PASS", "gross_usd": 0})
        self.assertEqual("PARTIAL", arm["status"])
        self.assertIn("1 listings live", arm["gap"])
        self.assertIsNone(arm["external_dependency"])

    def test_missing_registry_keeps_the_conservative_static_text(self):
        cfg = ba._digital_products_cfg(ba.ARMS["digital_products"], ba._registry_evidence(Path("/nonexistent.json")))
        self.assertEqual(ba.ARMS["digital_products"]["external_dependency"], cfg["external_dependency"])

    def test_a_registry_sale_alone_does_not_make_revenue_verified(self):
        with tempfile.TemporaryDirectory() as t:
            ev = ba._registry_evidence(registry(t, [{"published": True, "sales_count": 2, "sales_usd_cents": 3800}]))
        cfg = ba._digital_products_cfg(ba.ARMS["digital_products"], ev)
        self.assertIn("$38.00 gross", cfg["gap"])
        # The finance record still says $0: no promotion.
        arm = ba.evaluate_arm("digital_products", cfg, {"status": "PASS", "gross_usd": 0})
        self.assertNotEqual("REVENUE_VERIFIED", arm["status"])

    def test_registry_sale_plus_reconciled_finance_record_is_revenue_verified(self):
        with tempfile.TemporaryDirectory() as t:
            ev = ba._registry_evidence(registry(t, [{"published": True, "sales_count": 1, "sales_usd_cents": 1500}]))
        cfg = ba._digital_products_cfg(ba.ARMS["digital_products"], ev)
        arm = ba.evaluate_arm("digital_products", cfg, {"status": "PASS", "gross_usd": 15.0})
        self.assertEqual("REVENUE_VERIFIED", arm["status"])
        self.assertEqual([], ba.validate_arm_states({"arms": {"digital_products": arm}}))

    def test_other_arms_cannot_claim_revenue_from_company_wide_figures(self):
        arm = ba.evaluate_arm("micro_b2b", ba.ARMS["micro_b2b"], {"status": "PASS", "gross_usd": 500.0})
        self.assertNotEqual("REVENUE_VERIFIED", arm["status"])


class StateFile(unittest.TestCase):
    def test_write_state_is_complete_and_self_validated(self):
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / "state.json"
            doc = ba.write_state(out, now="2026-10-29T00:00:00Z")
            on_disk = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(doc["generated_at"], on_disk["generated_at"])
        self.assertEqual(10, len(on_disk["portfolio"]["activities"]))
        self.assertEqual([], on_disk["problems"])
        self.assertIn("treasury_control", on_disk["controls"])


class RegistryDailyWritesArms(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import registry_daily
        self.rd = registry_daily
        self.summary = {"products": 1, "states": {}, "sales_total": 0, "drift_counts": {}}

    def test_injected_writer_runs_after_the_rebuild(self):
        calls = []
        with tempfile.TemporaryDirectory() as t:
            r = self.rd.run_once(today="2026-10-29", state_path=Path(t) / "s.json",
                                 runner=lambda: (self.summary, {}),
                                 arms_writer=lambda: calls.append(1) or {"problems": ["x"]})
        self.assertEqual([1], calls)
        self.assertIn("arm state problems: 1", r["detail"])

    def test_a_failing_writer_never_hides_the_registry_result(self):
        def boom():
            raise RuntimeError("disk")
        with tempfile.TemporaryDirectory() as t:
            r = self.rd.run_once(today="2026-10-29", state_path=Path(t) / "s.json",
                                 runner=lambda: (self.summary, {}), arms_writer=boom)
        self.assertEqual("ok", r["action"])
        self.assertIn("arm state not written (RuntimeError)", r["detail"])

    def test_injected_runner_without_writer_never_touches_the_live_file(self):
        live = ROOT / "data" / "business_arms_state.json"
        before = live.read_bytes() if live.exists() else None
        with tempfile.TemporaryDirectory() as t:
            with mock.patch.object(self.rd, "_write_arms", side_effect=AssertionError("live write")):
                self.rd.run_once(today="2026-10-29", state_path=Path(t) / "s.json",
                                 runner=lambda: (self.summary, {}))
        self.assertEqual(before, live.read_bytes() if live.exists() else None)


if __name__ == "__main__":
    unittest.main()
