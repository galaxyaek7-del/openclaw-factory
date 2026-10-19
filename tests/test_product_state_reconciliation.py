"""Cycle 105 -- canonical product-state reconciliation tests.

These lock the two things Cycle 105 was asked to fix:
  1. exactly one primary state per product (no double counting across axes);
  2. a product is never reported as purchasable without a real checkout.

They run entirely on injected fixtures -- no network, no git, no real state.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import operational_history as oh              # noqa: E402
import product_state_reconciliation as psr    # noqa: E402


def _catalog(products):
    return {"generated_at": "2026-10-19T00:00:00+00:00",
            "total_products": len(products), "products": products}


def _gumroad_entry(pid, title, files, status="PUBLISHED"):
    return {
        "internal_product_id": pid, "product_name": title,
        "product_type": "gumroad_digital_product",
        "source_files": files, "pricing_usd": 14.99,
        "platforms": {"gumroad": {"status": status, "product_id": pid}},
        "publication_status": status, "revenue_usd": 0,
    }


def _history(product_id, title, highest):
    """A minimal operational-history snapshot whose milestones exactly match
    the requested highest state."""
    index = oh.MILESTONES.index(highest)
    milestones = {}
    for i, name in enumerate(oh.MILESTONES):
        milestones[name] = {
            "status": "VERIFIED" if i <= index else "NOT_VERIFIED",
            "label": "OBSERVED", "at": None,
            "source": "reports/%s/GATE_FINAL.json" % product_id,
            "evidence": ["fixture"], "note": None,
        }
    return {"product_id": product_id, "title": title, "milestones": milestones}


def _clean(products, history=None, verification=None, tracked=()):
    return psr.reconcile(
        catalog=_catalog(products),
        history=history or {"products": [], "generated_at": "t"},
        approvals=[],
        listing_verification=verification or {},
        asset_registry={"assets": []},
        authorization_fn=lambda op: type("D", (), {"allowed": False,
                                                   "reason": "flag off",
                                                   "live_publish_flag": False})(),
        tracked=set(tracked),
    )


class TestExclusivity(unittest.TestCase):
    def test_one_primary_state_per_product(self):
        r = _clean([_gumroad_entry("G1", "Alpha Kit", ["books/a.xlsx"]),
                    _gumroad_entry("G2", "Beta Kit", ["books/b.xlsx"],
                                   status="NOT_PUBLISHED")])
        for product in r["products"]:
            self.assertIn(product["primary_state"], psr.PRIMARY_STATES)

    def test_primary_state_sum_equals_product_count(self):
        r = _clean([_gumroad_entry("G1", "Alpha Kit", ["books/a.xlsx"]),
                    _gumroad_entry("G2", "Beta Kit", [])])
        counts = r["counts"]
        self.assertEqual(counts["primary_state_sum"], counts["logical_products"])
        self.assertEqual(counts["logical_products"], 2)

    def test_publication_is_a_flag_not_a_second_state(self):
        """The whole point of Cycle 105: a published product must not be
        counted twice -- once on the milestone axis, once on the platform
        axis. It appears once, with a publication flag."""
        products = [_gumroad_entry("G1", "Alpha Kit", [])]
        history = {"products": [_history("G1", "Alpha Kit", "CHECKOUT_VERIFIED")],
                   "generated_at": "t"}
        verification = {"verified_at": "2026-10-19T00:00:00+00:00",
                        "results": [{"product": "G1", "state": "PUBLISHED_VERIFIED_WITH_REVIEW_ITEMS",
                                     "review_items": []}]}
        r = _clean(products, history=history, verification=verification)
        self.assertEqual(r["counts"]["logical_products"], 1)
        self.assertEqual(r["counts"]["primary_state_sum"], 1)
        self.assertEqual(r["products"][0]["primary_state"], "CHECKOUT_VERIFIED")
        self.assertEqual(r["products"][0]["flags"]["publication"]["status"],
                         "PUBLISHED_VERIFIED_WITH_REVIEW_ITEMS")

    def test_axis_overlap_reproduces_the_reported_24(self):
        """21 products + 3 published == 24, computed rather than asserted."""
        products = [_gumroad_entry("G%d" % i, "Product %d" % i, []) for i in range(21)]
        for entry in products[:3]:
            entry["platforms"]["gumroad"]["status"] = "PUBLISHED"
        for entry in products[3:]:
            entry["platforms"]["gumroad"]["status"] = "NOT_PUBLISHED"
        verification = {"results": [{"product": "G%d" % i, "state": "PUBLISHED_VERIFIED"}
                                    for i in range(3)]}
        r = _clean(products, verification=verification)
        counts = r["counts"]
        self.assertEqual(counts["logical_products"], 21)
        self.assertEqual(counts["axis_overlap"], 3)
        self.assertEqual(counts["products_plus_axis_overlap"], 24)
        self.assertEqual(r["invariant_violations"], [])


class TestJoinsAndIdentity(unittest.TestCase):
    def test_joins_history_by_declared_registry_id_from_artifact_path(self):
        """The catalog keys Gumroad products by their live platform id, but
        operational history keys them by B12-NNN -- the join must still work."""
        products = [_gumroad_entry("LIVEID==", "Freelancer Rate & Raise Calculator",
                                   ["books/batch12/B12-001_freelancer_rate_raise_calculator.xlsx"])]
        history = {"products": [_history("B12-001", "Freelancer Rate & Raise Calculator",
                                         "BUILD_COMPLETE")], "generated_at": "t"}
        r = _clean(products, history=history)
        self.assertEqual(r["products"][0]["primary_state"], "BUILD_COMPLETE")
        self.assertEqual(r["products"][0]["declared_product_id"], "B12-001")
        self.assertEqual(r["products"][0]["primary_state_basis"]["history_join"],
                         "declared_registry_id")

    def test_status_is_never_promoted_without_evidence(self):
        """A platform record alone must not become a milestone."""
        entry = {"internal_product_id": "PRO1", "product_name": "Thing",
                 "product_type": "ai_saas_or_b2b_ladder_product", "source_files": [],
                 "platforms": {"paddle": {"status": "PRODUCT_CREATED"}},
                 "publication_status": "PRODUCT_CREATED_NOT_CONFIRMED_LIVE",
                 "revenue_usd": 0}
        r = _clean([entry])
        self.assertEqual(r["products"][0]["primary_state"], "PLATFORM_RECORD_ONLY")

    def test_affiliate_asset_is_external_not_owned(self):
        entry = {"internal_product_id": "B0X", "product_name": "Desk Converter",
                 "product_type": "affiliate_asset", "source_files": [],
                 "platforms": {"amazon_associates": {"status": "REAL_LISTING_CITED"}},
                 "publication_status": "EXTERNAL_PRODUCT_NOT_OWNED", "revenue_usd": 0}
        r = _clean([entry])
        self.assertEqual(r["products"][0]["primary_state"], "EXTERNAL_NOT_OWNED")


class TestInvariants(unittest.TestCase):
    def test_purchasability_is_always_unknown(self):
        r = _clean([_gumroad_entry("G1", "Alpha Kit", [])])
        self.assertEqual(r["products"][0]["flags"]["purchasability"]["status"], "UNKNOWN")
        self.assertEqual(r["invariant_violations"], [])

    def test_invariant_fires_if_purchasability_asserted(self):
        r = _clean([_gumroad_entry("G1", "Alpha Kit", [])])
        r["products"][0]["flags"]["purchasability"]["status"] = "YES"
        self.assertTrue(any("purchasability" in p for p in psr.assert_invariants(r)))

    def test_invariant_fires_on_duplicate_explicit_id(self):
        r = _clean([_gumroad_entry("SAME", "Alpha", []), _gumroad_entry("SAME", "Beta", [])])
        self.assertTrue(any("duplicate explicit ids" in p for p in psr.assert_invariants(r)))

    def test_stale_snapshot_timestamps_are_carried(self):
        r = _clean([_gumroad_entry("G1", "Alpha Kit", [])])
        self.assertIn("gumroad_live_snapshot", r["snapshots"])
        self.assertIn("listing_verification", r["snapshots"])


class TestIdentityNotes(unittest.TestCase):
    def test_unmatched_asset_is_never_merged_and_alias_uses_running_token_overlap(self):
        products = [_gumroad_entry("P1", "AI Customer Support Automation Platform for E-Commerce Businesses", [])]
        assets = {"assets": [{"asset_id": "GF-003",
                              "product_name": "AI Customer Support Automation for E-Commerce",
                              "production_status": "PRODUCED",
                              "product_genome": {"file": "books/x.pdf"}}]}
        r = psr.reconcile(catalog=_catalog(products),
                          history={"products": [], "generated_at": "t"}, approvals=[],
                          listing_verification={}, asset_registry=assets,
                          authorization_fn=None, tracked=set())
        note = r["identity_notes"]["asset_registry"]
        self.assertEqual(note["matched"], [])
        self.assertEqual(len(note["unmatched"]), 1)
        alias = note["unmatched"][0]["probable_alias"]
        self.assertEqual(alias["catalog_id"], "P1")
        self.assertEqual(alias["label"], "INFERRED")

    def test_exact_normalized_title_counts_as_a_real_match(self):
        products = [_gumroad_entry("P1", "EU AI Act Compliance Toolkit", [])]
        assets = {"assets": [{"asset_id": "GF-001",
                              "product_name": "EU AI Act Compliance Toolkit",
                              "production_status": "PRODUCED",
                              "product_genome": {"file": "books/eu.pdf"}}]}
        r = psr.reconcile(catalog=_catalog(products),
                          history={"products": [], "generated_at": "t"}, approvals=[],
                          listing_verification={}, asset_registry=assets,
                          authorization_fn=None, tracked=set())
        self.assertEqual(len(r["identity_notes"]["asset_registry"]["matched"]), 1)
        self.assertEqual(r["identity_notes"]["asset_registry"]["unmatched"], [])


class TestGitTracking(unittest.TestCase):
    def test_tracking_uses_injected_git_output(self):
        class FakeProc:
            returncode = 0
            stdout = "books/a.xlsx\n"
        tracked = psr.git_tracked_paths(root=Path.cwd(),
                                        runner=lambda args: FakeProc())
        self.assertEqual(tracked, {"books/a.xlsx"})

    def test_tracking_unknown_when_git_unavailable(self):
        def boom(args):
            raise OSError("no git")
        self.assertIsNone(psr.git_tracked_paths(root=Path.cwd(), runner=boom))

    def test_untracked_artifact_is_reported(self):
        r = psr.reconcile(catalog=_catalog([_gumroad_entry("G1", "Alpha Kit", ["books/a.xlsx"])]),
                          history={"products": [], "generated_at": "t"}, approvals=[],
                          listing_verification={}, asset_registry={"assets": []},
                          authorization_fn=None, tracked=set())
        self.assertEqual(r["products"][0]["flags"]["git_tracking"]["status"],
                         "ARTIFACTS_MISSING")


class TestRealRepository(unittest.TestCase):
    """One integration test against the real repository: the invariants must
    hold on the real fleet, not only on fixtures."""

    def test_real_reconciliation_has_no_invariant_violations(self):
        r = psr.reconcile(tracked=None)
        self.assertEqual(r["invariant_violations"], [])
        counts = r["counts"]
        self.assertEqual(counts["primary_state_sum"], counts["logical_products"])
        self.assertGreaterEqual(counts["logical_products"], 21)

    def test_real_published_products_are_checkout_verified(self):
        r = psr.reconcile()
        published = [p for p in r["products"]
                     if (p["flags"]["publication"].get("status") or "").startswith("PUBLISHED")]
        self.assertTrue(published, "the three live B12 listings must be recognised")
        for product in published:
            self.assertIn(product["primary_state"],
                          ("CHECKOUT_VERIFIED", "PUBLIC_LISTING_VERIFIED"))


if __name__ == "__main__":
    unittest.main()
