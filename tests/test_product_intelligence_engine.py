"""Digital Product Intelligence engine: invariance and honesty tests.

The point of these tests is not that the catalog is large. It is that no
number can be manufactured: no demand without a recorded source, no PURSUE
without observed willingness to pay, no composite below the coverage floor,
no ranking that effort can buy, and no file written anywhere.
"""
import hashlib
import os
import unittest

import product_intelligence_engine as pie

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REQUIRED_FIELDS = (
    "idea_id", "category", "title", "target_customer", "geography", "problem",
    "job_to_be_done", "format", "deliverable", "demand_evidence",
    "competitor_examples", "competition_indicators", "differentiation",
    "production", "distribution", "unit_economics", "licensing_risks",
    "research_confidence", "unknowns", "recommended_next_action", "status",
    "evidence_refs", "scores", "composite",
)

ALLOWED_ACTIONS = {"PURSUE", "TEST", "RESEARCH_DEMAND", "HOLD", "REJECT"}

PROTECTED = [
    os.path.join(ROOT, "data", "catalog.json"),
    os.path.join(ROOT, "data", "market_evidence.jsonl"),
    os.path.join(ROOT, "data", "product_registry.json"),
    os.path.join(ROOT, "config", "reality.json"),
    os.path.join(ROOT, "finance_data.json"),
]


def _digest(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _idea(**over):
    """Test helper: `over` uses the catalog's own public field names, so an
    override of `licensing_risks` or `proposed_price_usd` actually lands."""
    kwargs = {
        "idea_id": "TEST-01",
        "category": "budgeting_financial",
        "title": "Test idea",
        "customer": "Test buyer",
        "geography": "Global",
        "problem": "Buyers cannot see the cost",
        "job": "See the cost",
        "fmt": "excel_tool",
        "deliverable": "A workbook",
        "keywords": ["unlikely keyword phrase"],
        "price": 29.0,
        "risks": (),
        "differentiation": "UNKNOWN",
    }
    if "licensing_risks" in over:
        kwargs["risks"] = over.pop("licensing_risks")
    if "proposed_price_usd" in over:
        kwargs["price"] = over.pop("proposed_price_usd")
    if "format" in over:
        kwargs["fmt"] = over.pop("format")
    base = pie._idea(**kwargs)
    base.update(over)
    return base


class TestCatalogShape(unittest.TestCase):
    def test_fifty_ideas_five_per_category(self):
        self.assertEqual(len(pie.IDEA_CATALOG), 50)
        counts = {}
        for idea in pie.IDEA_CATALOG:
            counts[idea["category"]] = counts.get(idea["category"], 0) + 1
        self.assertEqual(len(counts), 10)
        self.assertEqual(set(counts), set(pie.CATEGORIES))
        self.assertEqual(set(counts.values()), {5})

    def test_ids_are_unique(self):
        ids = [i["idea_id"] for i in pie.IDEA_CATALOG]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_format_is_real(self):
        from trend_to_product.ideation import FORMATS
        for idea in pie.IDEA_CATALOG:
            self.assertIn(idea["format"], FORMATS, idea["idea_id"])
            self.assertIn(idea["format"], pie.FORMAT_TO_PRODUCT_TYPE)

    def test_resolved_records_carry_required_fields(self):
        for item in pie.catalog():
            for field in REQUIRED_FIELDS:
                self.assertIn(field, item, "%s missing %s" % (item.get("idea_id"), field))
            self.assertIn(item["recommended_next_action"], ALLOWED_ACTIONS)
            self.assertIn("ADVISORY_ONLY", item["status"])

    def test_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(pie.WEIGHTS.values()), 1.0, places=9)


class TestDemandHonesty(unittest.TestCase):
    def test_observed_requires_a_cited_source(self):
        row = {
            "event_type": "freelancer_agency_pricing",
            "niche": "x",
            "payload": {"source_url": "https://example.test/a", "quote": "we pay $50"},
        }
        idea = _idea(keywords=["freelancer agency pricing"])
        demand = pie.resolve_demand(idea, evidence=[row], products=[])
        self.assertEqual(demand["status"], "OBSERVED")
        self.assertEqual(demand["sources"], ["https://example.test/a"])

    def test_listing_with_zero_sales_is_not_demand(self):
        product = {"name": "an unlikely keyword phrase workbook", "price_usd": 19,
                   "sales": 0, "revenue_usd": 0.0}
        demand = pie.resolve_demand(_idea(), evidence=[], products=[product])
        self.assertEqual(demand["status"], "UNKNOWN")
        self.assertIn("not demand", demand["reason"])

    def test_listing_with_a_real_sale_is_derived(self):
        product = {"name": "an unlikely keyword phrase workbook", "price_usd": 19,
                   "sales": 1, "revenue_usd": 19.0}
        demand = pie.resolve_demand(_idea(), evidence=[], products=[product])
        self.assertEqual(demand["status"], "DERIVED")

    def test_no_idea_can_be_pursued_with_unknown_demand(self):
        for item in pie.catalog():
            if item["demand_evidence"]["status"] == "UNKNOWN":
                self.assertNotEqual(item["recommended_next_action"], "PURSUE", item["idea_id"])

    def test_supporting_keyword_is_not_enough(self):
        row = {
            "event_type": "complaining_review",
            "payload": {"source_url": "https://example.test/b",
                        "quote": "customer reviews say it is thin"},
        }
        # primary phrase does not appear; only a supporting concept does
        idea = _idea(keywords=["testimonial request", "customer review"])
        demand = pie.resolve_demand(idea, evidence=[row], products=[])
        self.assertEqual(demand["status"], "UNKNOWN")


class TestCompositesAndGates(unittest.TestCase):
    def test_coverage_floor_withholds_composite(self):
        sparse = {
            "demand_evidence": None,
            "problem_severity": {"score": 80.0, "basis": "INFERRED"},
            "competition_intensity": None,
            "differentiation": None,
            "willingness_to_pay": None,
            "production_cost_complexity": {"score": 80.0, "basis": "DERIVED"},
            "distribution_feasibility": None,
            "contribution_margin": None,
            "expansion_potential": {"score": 60.0, "basis": "DERIVED"},
            "risk": None,
        }
        result = pie._composite(sparse, pie.WEIGHTS)
        self.assertIsNone(result["value"])
        self.assertEqual(result["band"], "INSUFFICIENT_EVIDENCE")
        self.assertGreater(len(result["missing"]), 0)

    def test_effort_cannot_buy_a_pursue(self):
        heavy = _idea(idea_id="TEST-HEAVY", format="craft_pattern")
        light = _idea(idea_id="TEST-LIGHT", format="guide_printable")
        for idea in (heavy, light):
            item = pie.resolve(idea, evidence=[], products=[], db={})
            self.assertNotEqual(item["recommended_next_action"], "PURSUE")
            self.assertEqual(item["demand_evidence"]["status"], "UNKNOWN")
        heavy_score = pie._score_production(heavy)["score"]
        light_score = pie._score_production(light)["score"]
        self.assertGreater(light_score, heavy_score)

    def test_high_licensing_risk_holds(self):
        idea = _idea(licensing_risks=[{"level": "high", "note": "regulated"}])
        item = pie.resolve(idea, evidence=[], products=[], db={})
        self.assertEqual(item["recommended_next_action"], "HOLD")

    def test_high_risk_holds_even_with_observed_demand(self):
        row = {"event_type": "freelancer_agency_pricing",
               "payload": {"source_url": "https://example.test/c", "quote": "$99"}}
        idea = _idea(keywords=["freelancer agency pricing"],
                     licensing_risks=[{"level": "high", "note": "regulated"}])
        item = pie.resolve(idea, evidence=[row], products=[], db={})
        self.assertEqual(item["demand_evidence"]["status"], "OBSERVED")
        self.assertEqual(item["recommended_next_action"], "HOLD")

    def test_unit_economics_derived_from_real_table(self):
        import economics
        idea = _idea(proposed_price_usd=29.0)
        econ = pie.resolve_unit_economics(idea)
        self.assertEqual(econ["status"], "DERIVED")
        expected = economics.net_profit(29.0, econ["platform"],
                                        economics.load_config(pie.ECONOMICS_CONFIG_PATH))
        self.assertAlmostEqual(econ["net_per_unit_usd"], expected)

    def test_unit_economics_unknown_without_price(self):
        econ = pie.resolve_unit_economics(_idea(proposed_price_usd=None))
        self.assertEqual(econ["status"], "UNKNOWN")
        self.assertIsNone(econ.get("net_per_unit_usd"))


class TestSensitivity(unittest.TestCase):
    def test_only_scoreable_ideas_are_perturbed(self):
        items = pie.catalog()
        result = pie.sensitivity(items)
        scoreable = {i["idea_id"] for i in items if i["composite"]["value"] is not None}
        self.assertEqual({r["idea_id"] for r in result["per_item"]}, scoreable)

    def test_perturbations_are_deterministic(self):
        items = pie.catalog()
        first = pie.sensitivity(items)
        second = pie.sensitivity(items)
        self.assertEqual(first, second)

    def test_weights_stay_normalised_under_perturbation(self):
        result = pie.sensitivity(pie.catalog())
        self.assertEqual(len(result["samples"]), result["perturbations"])
        for weights in result["samples"]:
            self.assertAlmostEqual(sum(weights.values()), 1.0, places=3)

    def test_ranks_are_one_based(self):
        for row in pie.sensitivity(pie.catalog())["per_item"]:
            self.assertGreaterEqual(row["base_rank"], 1)
            self.assertGreaterEqual(row["min_rank"], 1)

    def test_insufficient_data_reports_honestly(self):
        result = pie.sensitivity([{"composite": {"value": None}, "scores": {}, "idea_id": "X"}])
        self.assertEqual(result["per_item"], [])
        self.assertIn("no ordering", result["note"])


class TestProductionAndDistribution(unittest.TestCase):
    def test_production_path_is_unbuilt_and_cites_real_files(self):
        path = pie.production_path(pie.IDEA_CATALOG[0]["idea_id"])
        self.assertEqual(path["status"], "NOT_BUILT")
        self.assertTrue(path["steps"])
        for step in path["steps"]:
            self.assertTrue(step["exists_on_disk"], step["module"])
            self.assertFalse(step["verified_for_this_idea"], step["module"])

    def test_distribution_plan_cites_the_publish_gate(self):
        plan = pie.distribution_plan(pie.IDEA_CATALOG[0]["idea_id"])
        self.assertTrue(plan["channels"])
        self.assertIn("check_publish_allowed", plan["publish_gate"])
        self.assertIn("no listing is created", plan["note"])

    def test_best_channel_is_not_blocked_for_a_real_format(self):
        plan = pie.distribution_plan("PI-IND-02")
        self.assertEqual(plan["best_channel"], "gumroad")
        self.assertEqual(plan["blocked_by"], [])


class TestNoWrites(unittest.TestCase):
    def test_report_does_not_touch_protected_files(self):
        before = {p: _digest(p) for p in PROTECTED if os.path.exists(p)}
        pie.report()
        after = {p: _digest(p) for p in PROTECTED if os.path.exists(p)}
        self.assertEqual(before, after)

    def test_report_is_stable_except_for_the_timestamp(self):
        first = pie.report()
        second = pie.report()
        first["revenue_truth"].pop("generated_at", None)
        second["revenue_truth"].pop("generated_at", None)
        self.assertEqual(first, second)


class TestLiveCatalogSignals(unittest.TestCase):
    def test_ranking_only_contains_scored_ideas(self):
        report = pie.report()
        self.assertEqual(len(report["ranking"]), report["scoreable"])
        for row in report["ranking"]:
            self.assertIsNotNone(row["composite"])

    def test_research_queue_is_the_complement(self):
        report = pie.report()
        self.assertEqual(len(report["ranking"]) + len(report["research_queue"]),
                         report["catalog_size"])

    def test_observed_demand_ideas_cite_http_sources(self):
        for idea in pie.report()["observed_demand_ideas"]:
            self.assertTrue(idea["sources"], idea["idea_id"])
            for src in idea["sources"]:
                self.assertTrue(str(src).startswith("http"), src)

    def test_revenue_truth_is_reported(self):
        truth = pie.report()["revenue_truth"]
        self.assertEqual(truth["source"], "revenue_os.revenue_read_model()")
        self.assertIsNotNone(truth["verified_revenue_usd"])


if __name__ == "__main__":
    unittest.main()
