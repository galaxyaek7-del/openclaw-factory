"""Trend-to-Product Intelligence Engine (2026-10-29).

Covers provenance, evidence classes, explainable scoring with missing evidence,
rights checks, duplication against the registry, traceability to production/QA
records, and the authorization boundary (nothing here fetches or publishes).
Every test writes to a temporary directory; no live data file is touched.
"""
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from trend_to_product import ideation, linkage, records, rights, scoring  # noqa: E402
from trend_to_product.records import RecordError  # noqa: E402

REGISTRY = [
    {"internal_id": "P-1", "title": "Etsy Seller Pricing & Profit Calculator", "published": True,
     "sales_count": 0, "first_published_at": "2026-08-01T00:00:00+00:00", "manifest": "m/P-1.json",
     "url": "https://example.gumroad.com/l/p1"},
    {"internal_id": "P-2", "title": "Renovation Allowance & Change-Order Control", "published": True,
     "sales_count": 0, "first_published_at": "2026-10-28T00:00:00+00:00"},
]


class Base(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def src(self, url="https://www.etsy.com/listing/1", st="MARKETPLACE_LISTING",
            am="WEB_SEARCH_INDEX", use="CITATION_ONLY", kw="crochet pattern", **kw_):
        return records.record_source(url, "2026-10-29", kw, "crochet", st, am, use,
                                     base_dir=self.d, **kw_)


class SourceRegistry(Base):
    def test_records_full_provenance(self):
        s = self.src()
        for f in ("source_id", "url", "accessed_on", "keyword", "topic", "source_type",
                  "access_method", "permitted_use", "platform", "platform_rule"):
            self.assertIn(f, s)
        self.assertEqual("etsy", s["platform"])

    def test_idempotent(self):
        self.assertEqual(self.src()["source_id"], self.src()["source_id"])
        self.assertEqual(1, len(records.read_jsonl("sources.jsonl", self.d)))

    def test_forbidden_access_refused(self):
        for am in ("SCRAPE", "LOGIN_BYPASS", "AUTOMATED_SCRAPE"):
            with self.assertRaises(RecordError):
                self.src(am=am)

    def test_unconfigured_api_not_assumed(self):
        with self.assertRaises(RecordError):
            self.src(url="https://www.pinterest.com/pin/1", st="OFFICIAL_PLATFORM_DATA",
                     am="OFFICIAL_API_AUTHORIZED", use="SIGNAL_ONLY")

    def test_pinterest_is_signal_only(self):
        s = self.src(url="https://trends.pinterest.com/x", st="OFFICIAL_PLATFORM_DATA",
                     am="MANUAL_SESSION_VIEW", use="SIGNAL_ONLY")
        self.assertEqual("pinterest", s["platform"])
        with self.assertRaises(RecordError):
            self.src(url="https://www.pinterest.com/pin/2", st="UNVERIFIED_SOCIAL",
                     am="MANUAL_SESSION_VIEW", use="LICENSED_ASSET_USE",
                     licence={"commercial_use": True, "reference": "x"})

    def test_attribution_is_not_permission(self):
        with self.assertRaises(RecordError):
            self.src(url="https://example.org/photo", use="LICENSED_ASSET_USE",
                     licence={"attribution_only": True, "reference": "CC BY-NC"})
        ok = self.src(url="https://example.org/photo2", use="LICENSED_ASSET_USE",
                      licence={"commercial_use": True, "reference": "licence #123"})
        self.assertEqual("LICENSED_ASSET_USE", ok["permitted_use"])

    def test_requires_real_date_and_url(self):
        with self.assertRaises(RecordError):
            records.record_source("https://x.org", "yesterday", "k", "t", "ANECDOTAL",
                                  "MANUAL_SESSION_VIEW", base_dir=self.d)
        with self.assertRaises(RecordError):
            records.record_source("file:///c/x", "2026-10-29", "k", "t", "ANECDOTAL",
                                  "MANUAL_SESSION_VIEW", base_dir=self.d)

    def test_own_record_must_be_internal(self):
        with self.assertRaises(RecordError):
            self.src(st="OWN_PLATFORM_RECORD")


class Signals(Base):
    def test_claim_must_cite_registered_source(self):
        with self.assertRaises(RecordError):
            records.record_signal("SEARCH_INTEREST", "crochet", "x", [], "2026-10-29", base_dir=self.d)
        with self.assertRaises(RecordError):
            records.record_signal("SEARCH_INTEREST", "crochet", "x", ["SRC-nope"], "2026-10-29",
                                  base_dir=self.d)

    def test_search_interest_never_counts_as_sales(self):
        s = self.src(url="https://trends.pinterest.com/x", st="OFFICIAL_PLATFORM_DATA",
                     am="MANUAL_SESSION_VIEW", use="SIGNAL_ONLY")
        sig = records.record_signal("SEARCH_INTEREST", "crochet", "index rose", [s["source_id"]],
                                    "2026-10-29", base_dir=self.d)
        self.assertFalse(sig["counts_as_sales_evidence"])

    def test_sale_only_from_own_records(self):
        s = self.src()
        with self.assertRaises(RecordError):
            records.record_signal("OBSERVED_SALE", "crochet", "sold", [s["source_id"]], "2026-10-29",
                                  base_dir=self.d)

    def test_price_observation_shape(self):
        s = self.src()
        with self.assertRaises(RecordError):
            records.record_signal("PRICE_OBSERVATION", "crochet", "p", [s["source_id"]], "2026-10-29",
                                  value={"currency": "USD", "low": 9, "high": 4}, base_dir=self.d)


class Scoring(Base):
    def test_no_evidence_is_insufficient_not_fabricated(self):
        r = scoring.score_opportunity("excel_tool", [], {})
        self.assertEqual("INSUFFICIENT_EVIDENCE", r["band"])
        self.assertIsNone(r["composite"])
        self.assertIsNone(r["dimensions"]["demand_evidence"]["score"])
        self.assertIsNone(r["dimensions"]["differentiation"]["score"])
        self.assertTrue(r["missing_evidence"])
        self.assertTrue(r["advisory"])
        self.assertIsNone(r["publication_decision"])

    def test_assessment_needs_basis_and_label(self):
        r = scoring.score_opportunity("excel_tool", [], {"differentiation": {"score": 5}})
        self.assertIsNone(r["dimensions"]["differentiation"]["score"])
        r = scoring.score_opportunity("excel_tool", [], {"differentiation": {
            "score": 4, "basis": "covers shipping", "label": "OBSERVED"}})
        self.assertIsNone(r["dimensions"]["differentiation"]["score"])

    def _full(self, listings=500, free=False):
        a = self.src()
        b = self.src(url="https://example.org/tracker", st="THIRD_PARTY_ESTIMATE", kw="k2")
        ids = [records.record_signal("CUSTOMER_PROBLEM", "crochet", "sellers underprice", [a["source_id"]],
                                     "2026-10-29", base_dir=self.d)["signal_id"],
               records.record_signal("SEARCH_INTEREST", "crochet", "steady interest", [b["source_id"]],
                                     "2026-10-29", base_dir=self.d)["signal_id"],
               records.record_signal("COMPETITION_DENSITY", "crochet", "listings", [b["source_id"]],
                                     "2026-10-29", value={"listings": listings}, base_dir=self.d)["signal_id"],
               records.record_signal("COMPETING_FORMAT", "crochet", "free sheets", [a["source_id"]],
                                     "2026-10-29", value={"free_alternatives": free}, base_dir=self.d)["signal_id"]]
        return ids

    def test_composite_only_over_scored_dimensions(self):
        ids = self._full()
        sigs = records.signals_for(signal_ids=ids, base_dir=self.d)
        r = scoring.score_opportunity("excel_tool", sigs, {"differentiation": {
            "score": 3, "basis": "includes shipping/overhead", "label": "INFERRED"}})
        self.assertIsNotNone(r["composite"])
        self.assertEqual(1.0, r["coverage"])
        scored = {k: v for k, v in r["dimensions"].items() if v["score"] is not None}
        expect = round(sum(v["score"] * scoring.WEIGHTS[k] for k, v in scored.items())
                       / sum(scoring.WEIGHTS[k] for k in scored), 2)
        self.assertEqual(expect, r["composite"])
        for v in r["dimensions"].values():
            self.assertTrue(v["basis"])

    def test_competition_and_free_alternatives(self):
        ids = self._full(listings=726887, free=True)
        sigs = records.signals_for(signal_ids=ids, base_dir=self.d)
        r = scoring.score_opportunity("excel_tool", sigs)
        self.assertEqual(0, r["dimensions"]["competition"]["score"])

    def test_rights_block_overrides_band(self):
        ids = self._full()
        sigs = records.signals_for(signal_ids=ids, base_dir=self.d)
        rr = rights.check_rights([{"name": "photo", "provenance": "THIRD_PARTY"}])
        self.assertEqual("BLOCKED_RIGHTS", scoring.score_opportunity("excel_tool", sigs, rights_result=rr)["band"])

    def test_record_and_rank(self):
        ids = self._full()
        o = scoring.record_opportunity("Pricing tool", "crochet", "excel_tool", ids, base_dir=self.d)
        self.assertTrue(o["opportunity_id"].startswith("OPP-"))
        scoring.record_opportunity("Empty", "x", "craft_pattern", [], base_dir=self.d)
        ranked = scoring.rank(self.d)
        self.assertEqual("Pricing tool", ranked[0]["name"])
        with self.assertRaises(RecordError):
            scoring.record_opportunity("Bad", "x", "excel_tool", ["SIG-missing"], base_dir=self.d)


class Rights(unittest.TestCase):
    def test_empty_is_review_never_pass(self):
        self.assertEqual("REVIEW", rights.check_rights()["status"])
        self.assertEqual("REVIEW", rights.check_rights(text="a clean original idea")["status"])

    def test_pinterest_asset_blocked(self):
        r = rights.check_rights([{"name": "img", "provenance": "ORIGINAL_FACTORY",
                                  "process_evidence": "x", "source_url": "https://i.pinterest.com/a.jpg"}])
        self.assertEqual("BLOCK", r["status"])

    def test_attribution_only_blocked(self):
        r = rights.check_rights([{"name": "font", "provenance": "LICENSED",
                                  "licence": {"attribution_only": True, "reference": "CC BY"}}])
        self.assertEqual("BLOCK", r["status"])

    def test_original_needs_process_evidence(self):
        self.assertEqual("REVIEW", rights.check_rights([{"name": "pdf", "provenance": "ORIGINAL_FACTORY"}])["status"])
        self.assertEqual("PASS", rights.check_rights([{"name": "pdf", "provenance": "ORIGINAL_FACTORY",
                                                       "process_evidence": "books/x/build.py"}])["status"])

    def test_derivative_wording_and_brand_claims(self):
        a = [{"name": "pdf", "provenance": "ORIGINAL_FACTORY", "process_evidence": "b.py"}]
        self.assertEqual("REVIEW", rights.check_rights(a, "a dupe of the viral pin")["status"])
        self.assertEqual("BLOCK", rights.check_rights(a, "Officially licensed by Disney")["status"])


class Ideation(Base):
    def _opp(self, fmt="excel_tool"):
        s = self.src()
        sig = records.record_signal("PRICE_OBSERVATION", "crochet", "tools sell $2-45", [s["source_id"]],
                                    "2026-10-29", value={"currency": "USD", "low": 2, "high": 45, "median": 10},
                                    base_dir=self.d)
        return scoring.record_opportunity("x", "crochet", fmt, [sig["signal_id"]], base_dir=self.d)

    def _spec(self, opp, fmt="excel_tool", title="Market Stall Float Counter", **kw):
        args = dict(target_customer="makers", problem_statement="underpricing",
                    value_proposition="v", differentiation="d", deliverables=["xlsx"],
                    acceptance_tests=["formulas recomputed"], proposed_price_usd=12, registry=REGISTRY,
                    base_dir=self.d)
        args.update(kw)
        return ideation.build_spec(opp, fmt, title, **args)

    def test_duplication_against_registry(self):
        d = ideation.duplication_check("Etsy Seller Pricing and Profit Calculator", registry=REGISTRY)
        self.assertEqual("DUPLICATE", d["verdict"])
        self.assertEqual("P-1", d["matches"][0]["internal_id"])
        self.assertEqual("NONE_FOUND", ideation.duplication_check("Toddler bedtime story cards",
                                                                  registry=REGISTRY)["verdict"])

    def test_concept_overlap_flags_own_product(self):
        # Regression, 2026-10-29: title words alone missed B14-005.
        reg = [{"internal_id": "B14-005", "title": "Etsy & Shopify Product Profit Calculator"},
               {"internal_id": "B15-002", "title": "Employee True Cost Calculator (US Small Business)"}]
        d = ideation.duplication_check("Handmade Order Costing & Pricing Workbook", registry=reg)
        self.assertEqual("CANNIBALIZATION", d["verdict"])
        self.assertEqual(["B14-005"], [m["internal_id"] for m in d["matches"]])
        sp = self._spec(self._opp(), title="Handmade Order Costing & Pricing Workbook", registry=reg)
        self.assertEqual("SPEC_REVIEW", sp["status"])
        self.assertTrue(sp["reviews"])

    def test_spec_fields_required(self):
        with self.assertRaises(RecordError):
            self._spec(self._opp(), acceptance_tests=[])

    def test_spec_price_from_observations(self):
        sp = self._spec(self._opp())
        self.assertEqual("OBSERVED_RANGE", sp["price_range"]["status"])
        self.assertEqual("within observed competing range", sp["price_basis"])
        self.assertEqual("SPEC_DRAFT", sp["status"])

    def test_unverifiable_format_blocked(self):
        sp = self._spec(self._opp("craft_pattern"), fmt="craft_pattern", title="Granny square blanket pattern")
        self.assertEqual("SPEC_BLOCKED", sp["status"])
        self.assertTrue(any("physical test make" in b for b in sp["blockers"]))

    def test_duplicate_spec_blocked(self):
        sp = self._spec(self._opp(), title="Etsy Seller Pricing Profit Calculator")
        self.assertEqual("SPEC_BLOCKED", sp["status"])

    def test_listing_draft_never_publishable(self):
        sp = self._spec(self._opp())
        ld = ideation.listing_draft(sp, "Price every order. Offer ends in 2 hours!", ["a"], ["xlsx"], "email")
        self.assertFalse(ld["publish_allowed"])
        self.assertEqual("DRAFT_NOT_PUBLISHED", ld["status"])
        self.assertTrue(ld["problems"])


class Linkage(Base):
    def setUp(self):
        super().setUp()
        self.root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.root, "m"))
        Path(self.root, "m", "P-1.json").write_text(json.dumps({"qa": {"ok": True, "gate": {"status": "PASS"},
                                                                       "workbook": {"status": "PASS"}}}))
        self.appr = os.path.join(self.root, "appr.json")
        Path(self.appr).write_text(json.dumps({"approvals": [{"product_id": "P-1", "status": "APPROVED",
                                                              "approval_id": "A1"}]}))
        s = self.src()
        sig = records.record_signal("CUSTOMER_PROBLEM", "crochet", "p", [s["source_id"]], "2026-10-29",
                                    base_dir=self.d)
        self.opp = scoring.record_opportunity("x", "crochet", "excel_tool", [sig["signal_id"]], base_dir=self.d)
        self.spec = ideation.build_spec(self.opp, "excel_tool", "Market day cost sheet", "makers", "p", "v",
                                        "d", ["xlsx"], ["t"], registry=REGISTRY, base_dir=self.d)

    def tearDown(self):
        super().tearDown()
        shutil.rmtree(self.root, ignore_errors=True)

    def test_link_requires_registry_product(self):
        with self.assertRaises(RecordError):
            linkage.link_spec_to_product(self.spec["spec_id"], "NOPE", base_dir=self.d, registry=REGISTRY)
        with self.assertRaises(RecordError):
            linkage.link_spec_to_product("SPEC-x", "P-1", base_dir=self.d, registry=REGISTRY)

    def test_trace_reads_qa_approval_listing_outcome(self):
        linkage.link_spec_to_product(self.spec["spec_id"], "P-1", base_dir=self.d, registry=REGISTRY)
        t = linkage.trace(self.opp["opportunity_id"], base_dir=self.d, registry=REGISTRY,
                          root=self.root, approvals_path=self.appr)
        c = t["chain"][0]
        self.assertEqual("PASS", c["qa"]["status"])
        self.assertEqual("APPROVED", c["approval"]["status"])
        self.assertEqual("OBSERVED", c["outcome"]["label"])
        self.assertTrue(c["outcome"]["traffic"].startswith("UNKNOWN"))
        self.assertIn(self.spec["spec_id"], t["specs"])

    def test_calibration_needs_enough_data(self):
        linkage.link_spec_to_product(self.spec["spec_id"], "P-1", base_dir=self.d, registry=REGISTRY)
        c = linkage.calibration_summary(self.d, REGISTRY, datetime(2026, 10, 29, tzinfo=timezone.utc))
        self.assertEqual("NOT_ENOUGH_DATA", c["status"])
        self.assertEqual(1, c["eligible"])

    def test_state_reflects_stored_evidence_only(self):
        p = os.path.join(self.d, "state.json")
        doc = linkage.write_state(p, base_dir=self.d, registry=REGISTRY,
                                  now=datetime(2026, 10, 31, tzinfo=timezone.utc))
        self.assertEqual(1, doc["counts"]["sources"])
        self.assertEqual(2, doc["evidence_freshness"]["newest_age_days"])
        self.assertEqual(0, doc["signals_counting_as_sales"])
        self.assertFalse(doc["platform_policy"]["pinterest"]["api_configured"])
        self.assertTrue(os.path.exists(p))
        empty = linkage.build_state(base_dir=tempfile.mkdtemp(), registry=[])
        self.assertEqual(0, empty["counts"]["opportunities"])
        self.assertIsNone(empty["evidence_freshness"]["newest_access"])


class AuthorizationBoundary(unittest.TestCase):
    def test_package_has_no_network_or_publish_path(self):
        pkg = ROOT / "trend_to_product"
        banned = re.compile(r"\b(requests|urllib\.request|http\.client|socket|subprocess|distributor|"
                            r"publish_batch|gumroad_api|metricool|smtplib)\b")
        for f in pkg.glob("*.py"):
            code = "\n".join(l for l in f.read_text(encoding="utf-8").splitlines()
                             if not l.strip().startswith("#"))
            code = re.sub(r'"""[\s\S]*?"""', "", code)
            self.assertIsNone(banned.search(code), f"{f.name}: {banned.search(code)}")

    def test_default_paths_are_not_written_by_tests(self):
        # A guard against the B5 class of leak: the tests above pass base_dir/paths.
        self.assertTrue(str(records.DEFAULT_DIR).endswith(os.path.join("data", "trend_to_product")))


if __name__ == "__main__":
    unittest.main()


class OverlapAndApprovals(Base):
    def setUp(self):
        super().setUp()
        s = self.src()
        sig = records.record_signal("CUSTOMER_PROBLEM", "pricing", "p", [s["source_id"]], "2026-10-29",
                                    base_dir=self.d)
        self.opp = scoring.record_opportunity("x", "pricing", "excel_tool", [sig["signal_id"]], base_dir=self.d)
        self.spec = ideation.build_spec(self.opp, "excel_tool", "Etsy Seller Pricing Profit Calculator",
                                        "makers", "p", "v", "d", ["xlsx"], ["t"], registry=REGISTRY,
                                        base_dir=self.d)

    def test_overlap_link_only_for_products_the_check_found(self):
        linkage.link_spec_to_product(self.spec["spec_id"], "P-1", "OVERLAPS_EXISTING",
                                     base_dir=self.d, registry=REGISTRY)
        with self.assertRaises(RecordError):
            linkage.link_spec_to_product(self.spec["spec_id"], "P-2", "OVERLAPS_EXISTING",
                                         base_dir=self.d, registry=REGISTRY)

    def test_batch_authorization_is_found_when_no_per_product_approval(self):
        root = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(root, "data"))
            Path(root, "data", "batch14_publish_results.json").write_text(json.dumps([
                {"at": "2026-10-23T13:22:42Z", "authorization": "founder 2026-10-23: publish batch 14",
                 "results": [{"id": "P-1"}]}]))
            a = linkage._approval_of("P-1", os.path.join(root, "none.json"), root)
            self.assertEqual("BATCH_AUTHORIZATION", a["status"])
            self.assertEqual("data/batch14_publish_results.json", a["source"])
            self.assertEqual("NONE", linkage._approval_of("P-9", os.path.join(root, "none.json"), root)["status"])
        finally:
            shutil.rmtree(root, ignore_errors=True)


class Previews(Base):
    def setUp(self):
        super().setUp()
        self.root = tempfile.mkdtemp()
        Path(self.root, "deliv.xlsx").write_bytes(b"workbook v1")
        Path(self.root, "render.png").write_bytes(b"png of sheet 1")
        Path(self.root, "mock.png").write_bytes(b"device frame")

    def tearDown(self):
        super().tearDown()
        shutil.rmtree(self.root, ignore_errors=True)

    def rec(self, preview="render.png", kind="RENDER"):
        from trend_to_product import previews
        return previews.record_preview("SPEC-1", "deliv.xlsx", preview, kind, "scripts/render_sheet.py",
                                       root=self.root, base_dir=self.d)

    def test_render_verifies_until_the_deliverable_changes(self):
        from trend_to_product import previews
        r = self.rec()
        self.assertEqual("VERIFIED", previews.verify_preview(r, self.root)["status"])
        Path(self.root, "deliv.xlsx").write_bytes(b"workbook v2")
        v = previews.verify_preview(r, self.root)
        self.assertEqual("FAILED", v["status"])
        self.assertIn("deliverable changed", v["problems"][0])

    def test_listing_needs_a_render_and_labelled_mockups(self):
        from trend_to_product import previews
        mock = self.rec("mock.png", "MOCKUP")
        self.assertTrue(any("only mockups" in p for p in previews.check_listing_previews([mock], True, self.root)))
        render = self.rec()
        problems = previews.check_listing_previews([render, mock], False, self.root)
        self.assertEqual(1, len(problems))
        self.assertIn("labelled as an illustration", problems[0])
        self.assertEqual([], previews.check_listing_previews([render, mock], True, self.root))
        self.assertTrue(previews.check_listing_previews([], False, self.root))

    def test_record_requires_files_kind_and_generator(self):
        from trend_to_product import previews
        with self.assertRaises(RecordError):
            previews.record_preview("S", "nope.xlsx", "render.png", "RENDER", "g", root=self.root, base_dir=self.d)
        with self.assertRaises(RecordError):
            previews.record_preview("S", "deliv.xlsx", "render.png", "PHOTO", "g", root=self.root, base_dir=self.d)
        with self.assertRaises(RecordError):
            previews.record_preview("S", "deliv.xlsx", "render.png", "RENDER", " ", root=self.root, base_dir=self.d)


class SpecDecisions(Base):
    def setUp(self):
        super().setUp()
        s = self.src()
        sig = records.record_signal("CUSTOMER_PROBLEM", "pricing", "p", [s["source_id"]], "2026-10-29",
                                    base_dir=self.d)
        opp = scoring.record_opportunity("x", "pricing", "excel_tool", [sig["signal_id"]], base_dir=self.d)
        self.spec = ideation.build_spec(opp, "excel_tool", "Etsy Seller Pricing Profit Calculator",
                                        "makers", "p", "v", "d", ["xlsx"], ["t"], registry=REGISTRY,
                                        base_dir=self.d)

    def test_merge_needs_a_found_target_and_a_reason(self):
        with self.assertRaises(RecordError):
            ideation.record_spec_decision(self.spec["spec_id"], "MERGE_INTO_EXISTING", "r", "founder",
                                          target_product="P-2", base_dir=self.d)
        with self.assertRaises(RecordError):
            ideation.record_spec_decision(self.spec["spec_id"], "DROP", " ", "founder", base_dir=self.d)
        r = ideation.record_spec_decision(self.spec["spec_id"], "MERGE_INTO_EXISTING", "overlaps P-1",
                                          "founder", target_product="P-1", base_dir=self.d)
        self.assertEqual("SPEC_MERGED", r["status"])
        latest = ideation.latest_specs(self.d)[self.spec["spec_id"]]
        self.assertEqual("P-1", latest["decision"]["target_product"])
        self.assertEqual(2, len(records.read_jsonl("specs.jsonl", self.d)))   # history kept

    def test_unknown_decision_refused(self):
        with self.assertRaises(RecordError):
            ideation.record_spec_decision(self.spec["spec_id"], "PUBLISH", "r", "founder", base_dir=self.d)
