"""arm_portfolio.py: every doctrine arm has a complete profile, and a declared
stage can never claim more than the arm's evidence status allows."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import arm_portfolio as ap  # noqa: E402
import business_arms as ba  # noqa: E402


def state(**statuses):
    return {"arms": {k: {"status": statuses.get(k, "PARTIAL"), "name": k} for k in ba.ARMS}}


class Profiles(unittest.TestCase):
    def test_every_doctrine_arm_has_exactly_one_profile(self):
        self.assertEqual(set(ap.PROFILES), set(ba.ARMS))
        self.assertEqual(set(ap.DIRECTIVE_LETTERS), set(ba.ARMS))

    def test_directive_arms_a_to_i_are_all_mapped(self):
        letters = {l for ls in ap.DIRECTIVE_LETTERS.values() for l in ls}
        self.assertEqual(letters, set("ABCDEFGHI"))

    def test_live_profiles_are_consistent(self):
        s = state(affiliate_intelligence="BLOCKED", productized_ai_services="PARTIAL")
        self.assertEqual(ap.validate(s), [])

    def test_operating_needs_verified_revenue(self):
        profiles = {k: dict(v) for k, v in ap.PROFILES.items()}
        profiles["digital_products"]["stage"] = "OPERATING"
        problems = ap.validate(state(), profiles)
        self.assertTrue(any("digital_products: stage OPERATING not supported by evidence status PARTIAL" in p
                            for p in problems), problems)
        ok = state(digital_products="REVENUE_VERIFIED", affiliate_intelligence="BLOCKED",
                   productized_ai_services="PARTIAL")
        self.assertEqual(ap.validate(ok, profiles), [])

    def test_a_planned_arm_cannot_claim_a_commercial_test(self):
        profiles = {k: dict(v) for k, v in ap.PROFILES.items()}
        profiles["ai_operations"]["stage"] = "COMMERCIAL_TEST"
        self.assertTrue(any("ai_operations: stage COMMERCIAL_TEST" in p
                            for p in ap.validate(state(ai_operations="PLANNED"), profiles)))

    def test_every_arm_names_its_current_experiment_and_none_claims_to_run(self):
        self.assertEqual(set(ap.EXPERIMENTS), set(ap.PROFILES))
        for key, e in ap.EXPERIMENTS.items():
            self.assertTrue(e["state"] in ("PENDING_APPROVAL", "PREPARED", "NONE") or e["state"].startswith("BLOCKED: "), key)
            self.assertNotIn("RUNNING", e["state"], key)
        rows = ap.summary(state(affiliate_intelligence="BLOCKED"))["arms"]
        self.assertTrue(all("experiment" in r for r in rows))

    def test_every_dependency_is_a_named_shared_capability(self):
        for key, p in ap.PROFILES.items():
            for d in p["depends_on"]:
                self.assertIn(d, ap.SHARED_CAPABILITIES, key)

    def test_summary_names_cross_arm_bottlenecks(self):
        out = ap.summary(state(affiliate_intelligence="BLOCKED", productized_ai_services="PARTIAL"))
        caps = {b["capability"]: b["blocks"] for b in out["bottlenecks"]}
        self.assertIn("visit_measurement", caps)
        self.assertGreaterEqual(len(caps["visit_measurement"]), 3)
        self.assertIn("customer_intake", caps)
        self.assertEqual(out["problems"], [])

    def test_unknown_kpis_are_never_reported_as_measured(self):
        for p in ap.PROFILES.values():
            for k in p["kpis"]:
                self.assertIn(k["available"], ("OBSERVED", "UNKNOWN"))
                if k["source"].startswith("none") or "no " in k["source"][:3]:
                    self.assertEqual(k["available"], "UNKNOWN", k)


class StudioEvidence(unittest.TestCase):
    def test_counts_only_passing_episode_renders(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            r = Path(d) / "kids_studio" / "renders"
            r.mkdir(parents=True)
            for name, verdict in (("ep01_animatic", "PASS"), ("ep02_ball", "PASS"), ("ep01_sc01_poc", "PASS"),
                                  ("ep03_draft", "FAIL")):
                (r / f"{name}.verify.json").write_text(json.dumps({"verdict": verdict}))
            (Path(d) / "kids_studio" / "production_manifest.json").write_text(json.dumps({"finished_film_exists": False}))
            ev = ba._studio_evidence(Path(d))
            self.assertEqual(ev["verified_episode_renders"], ["ep01_animatic", "ep02_ball"])
            cfg = ba._studio_cfg(ba.ARMS["childrens_media_studio"], ev)
            self.assertIn("2 episode animatic(s) verified", cfg["gap"])
            self.assertIn("no finished film exists", cfg["gap"])

    def test_no_records_keeps_the_static_text(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            ev = ba._studio_evidence(Path(d))
            self.assertEqual(ba._studio_cfg(ba.ARMS["childrens_media_studio"], ev), ba.ARMS["childrens_media_studio"])


if __name__ == "__main__":
    unittest.main()
