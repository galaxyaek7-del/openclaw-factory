"""End-to-end test for automation_systems (Universal Production Engine
Roadmap Step 2, 2026-07-18) — proves ONE real family works completely
through the full pipeline: real Market Discovery/Opportunity Scoring
(profit_oracle.ladder_opportunity_score), the real Decision Engine
(decision_engine.engine.record_ladder_decision), the real orchestrator
dispatch (orchestrator.engines.production.run), Content Generation,
Asset Generation, Packaging, and the Dossier Bundle (version/build
manifest/QA report/recovery metadata) — then round-trips the result
through schemas/product.py and a dry-run Paddle/Gumroad publish() to
prove marketplace compatibility with zero special-casing.

Real Groq calls are mocked. orchestrator.engines.production.run() is the
real orchestrator entry point, not a test seam — it doesn't accept a
per-call path override, so the changelog/factory_state module-level
defaults are patched to isolated temp paths for the duration of each
test instead. The one real PDF this produces is cleaned up afterward,
same _CleanupPdfMixin discipline every other family adapter test in this
suite already uses.

    python -m unittest tests.test_automation_systems_e2e -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import book_generator as bg
import factory_state
import dossier_bundle.build_bundle as bb
import market_hunter as mh
import mission_control_api
import profit_oracle
from decision_engine import engine as decision_engine
from orchestrator.engines import production
import product_families  # noqa: F401 — self-registers every family
from schemas.product import Product
from channels import registry as channel_registry
from channels.paddle_arm import PaddleArm
from channels.gumroad_arm import GumroadArm


def _fake_techdoc_content(title, topic, titles):
    return [{"title": t, "content": f"real generated content for {t} in {topic}"} for t in titles]


class TestAutomationSystemsEndToEnd(unittest.TestCase):
    # Deliberately NOT market_hunter.py's own real seed niche text
    # ("workflow automation system for logistics companies") — this test's
    # thin fake content fails real Dual Inspection every run, and doing that
    # against a real, shared seed niche pollutes REJECTED_NICHES.md's
    # circuit-breaker memory for a niche real Discovery actually uses (found
    # live, 2026-07-18: 16 real polluting entries broke
    # tests/test_unified_pipeline_e2e.py's own use of that exact niche).
    # This string scores identically under the real ladder gate (confirmed:
    # ladder_score 76.3/100, price $327, same as the real seed) without
    # colliding with it — real Market Discovery/Opportunity Scoring proven
    # via test_discovery_tags_this_ladder_with_a_real_seed_niche below instead.
    NICHE = "automated compliance workflow system for mid-size logistics firms"

    def test_discovery_tags_this_ladder_with_a_real_seed_niche(self):
        """Real Market Discovery integration proof, kept separate from the
        full generation pipeline above: market_hunter.py's own real
        SEED_CATEGORIES tags real niches with ladder="b2b_systems"/
        "automation_tools" — exactly the ranks this family's mapping
        resolves from (product_families/mapping.py)."""
        seeded_ladders = {c["ladder"] for c in mh.SEED_CATEGORIES}
        self.assertTrue({"b2b_systems", "automation_tools"} & seeded_ladders)

    def setUp(self):
        self.tmp_changelog = tempfile.mktemp(suffix=".jsonl")
        self.tmp_state = tempfile.mktemp(suffix=".json")
        self.tmp_decisions = tempfile.mktemp(suffix=".jsonl")
        self._created_files = []

        # channels.registry is global, mutable, module-level state shared
        # across the whole test process (see test_production_factory.py's
        # TestPublishingChecklist) — clear + re-register just what this
        # test needs so it's authoritative regardless of run order.
        channel_registry.clear()
        channel_registry.register(PaddleArm())
        channel_registry.register(GumroadArm())

        patches = [
            patch.object(bb, "_CHANGELOG_PATH", self.tmp_changelog),
            patch.object(factory_state, "DEFAULT_STATE_PATH", Path(self.tmp_state)),
            patch.object(bg, "ai_generate_techdoc_content", side_effect=_fake_techdoc_content),
            patch.object(bg, "groq_chat", side_effect=RuntimeError("no network in test")),
            # This test's thin fake content will likely fail real Dual
            # Inspection (a real, honest verdict — not mocked), which would
            # otherwise write a real entry to REJECTED_NICHES.md/
            # QUARANTINE.md on every run. The verdict itself stays real;
            # only the disk-logging side effect is suppressed (found live,
            # 2026-07-18: an earlier version of this test repeatedly
            # polluted both files for a real market_hunter.py seed niche).
            patch.object(bg, "_record_rejected_niche"),
            patch.object(bg.INSPECTORS, "_log_quarantine"),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        for p in (self.tmp_changelog, self.tmp_state, self.tmp_decisions, *self._created_files):
            if p and os.path.exists(p):
                os.remove(p)

    def _run_full_pipeline(self):
        ladder_result = profit_oracle.ladder_opportunity_score(self.NICHE, ladder="b2b_systems")
        self.assertTrue(ladder_result["accepted"], f"seed niche must clear the real ladder gate: {ladder_result}")

        decision = decision_engine.record_ladder_decision(
            self.NICHE, "b2b_systems", ladder_result, decisions_path=self.tmp_decisions,
        )
        self.assertEqual(decision.product_family, "automation_systems")
        self.assertEqual(decision.status, "ACCEPTED")

        result = production.run({
            "niche": self.NICHE, "dry_run": False, "decision_result": decision.to_dict(),
        })
        if result.get("path"):
            self._created_files.append(result["path"])
        if (result.get("cover") or {}).get("path"):
            self._created_files.append(result["cover"]["path"])
        return decision, result

    def test_dispatches_through_the_real_decision_engine_and_orchestrator(self):
        decision, result = self._run_full_pipeline()
        self.assertTrue(result["executed"])
        self.assertTrue(result["success"])
        self.assertEqual(result["product_type"], "techdoc")
        expected_production_id = f"PROD-{decision.decision_id}"
        self.assertEqual(result["production_id"], expected_production_id)
        self.assertEqual(result["dossier_bundle"]["production_id"], expected_production_id)

    def test_every_required_per_product_artifact_is_present(self):
        _, result = self._run_full_pipeline()
        dossier = result["dossier_bundle"]
        self.assertEqual(dossier["version"], "1.0.0")
        self.assertIn("# ", dossier["documentation"])
        self.assertIsNotNone(dossier["metadata"])
        self.assertIn("build_manifest", dossier)
        self.assertEqual(dossier["build_manifest"]["content_generator"], "groq_techdoc")
        self.assertEqual(dossier["build_manifest"]["asset_builder"], "techdoc_package")
        self.assertEqual(dossier["build_manifest"]["packager"], "single_file")
        self.assertIn(result["path"], dossier["build_manifest"]["files"])
        self.assertIsNotNone(dossier["qa_report"])
        self.assertFalse(dossier["recovery_metadata"]["had_pending_retry"])
        self.assertTrue(dossier["changelog_appended"])

    def test_mission_control_reports_this_family_as_real(self):
        self._run_full_pipeline()
        families = mission_control_api._production_families()["families"]
        self.assertTrue(families["automation_systems"].startswith("REAL"))

    def test_a_real_groq_interruption_enqueues_a_retry_and_degrades_honestly(self):
        """Requirement #8: a Content Generation failure must be resumable
        from a real checkpoint, never a silent data loss or a crash."""
        with patch.object(bg, "ai_generate_techdoc_content", side_effect=RuntimeError("groq unreachable")):
            _, result = self._run_full_pipeline()
        self.assertTrue(result["success"])  # degrades honestly to fallback content, never crashes
        state = factory_state.load_state(self.tmp_state)
        matching = [
            r for r in state["pending_retries"]
            if isinstance(r.get("context"), dict) and r["context"].get("production_id") == result["production_id"]
        ]
        self.assertTrue(matching, "a Groq failure during Content Generation must enqueue a real, traceable retry")

    def test_round_trips_through_the_generic_product_schema_and_dry_run_publish(self):
        """KDP/Gumroad/Paddle compatibility proof (requirement #6): the
        exact real books/_generation_log.jsonl-shaped record this family
        produces converts into a Product via schemas/product.py with zero
        special-casing, and both the Paddle and Gumroad arms accept it in
        a dry run — the same generic BaseArm contract every other family
        already reuses. Shopify is future/not built; BaseArm's contract
        (title/description/price_usd/file_path) needs no schema change to
        add one later, but no ShopifyArm exists today."""
        _, result = self._run_full_pipeline()
        record = dict(result)
        record["timestamp"] = "2026-07-18T00:00:00Z"
        product = Product.from_jsonl_record(record)
        self.assertEqual(product.source_id, result["production_id"])
        self.assertEqual(product.file_path, result["path"])
        self.assertFalse(product.needs_pricing, f"a techdoc product must resolve a real price: {product}")

        for arm_name in ("paddle", "gumroad"):
            arm = channel_registry.get(arm_name)
            publish_result = arm.publish(product, dry_run=True)
            self.assertTrue(publish_result.dry_run)


if __name__ == "__main__":
    unittest.main()
