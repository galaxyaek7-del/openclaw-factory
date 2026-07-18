"""End-to-end verification (ADR-076, Decision Surface Reconciliation):
proves one real, discovered opportunity flows through every stage of the
pipeline — Golden Hunter -> Decision Engine (single source of truth) ->
Mission Control's real read-path -> factory_loop's automatic gate -> the
n8n/Telegram notification payload -> the production brief Paddle
ultimately receives its price from — with the SAME score/price/ladder at
every stage. No mocking of the scoring itself: every number below is a
real, live computation.

    python -m unittest tests.test_unified_pipeline_e2e -v
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import market_hunter as mh
import profit_oracle as po
from decision_engine import ranking, store
from decision_engine.engine import record_ladder_decision

REAL_NICHE = "workflow automation system for logistics companies"
REAL_LADDER = "b2b_systems"


def _temp_path(suffix=".jsonl"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


class TestOneOpportunityFlowsThroughEveryStageWithNoDivergence(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()
        self.opps_path = _temp_path(suffix=".md")

    def tearDown(self):
        for p in (self.decisions_path, self.opps_path):
            if os.path.exists(p):
                os.remove(p)

    def test_stage_1_golden_hunter_discovers_and_scores_it(self):
        """Golden Hunter (market_hunter.py) — the real seed list already
        tags this exact niche ai_saas; confirms it's still there and still
        a real, live ACCEPT under ladder_opportunity_score()."""
        seeded = [c for c in mh.SEED_CATEGORIES if c["niche"] == REAL_NICHE]
        self.assertEqual(len(seeded), 1, "the proven real niche must still be seeded")
        self.assertEqual(seeded[0]["ladder"], REAL_LADDER)

        direct = po.ladder_opportunity_score(REAL_NICHE, ladder=REAL_LADDER)
        self.assertTrue(direct["accepted"])
        self.stage1_score = direct["ladder_score"]
        self.stage1_price = direct["price"]

    def test_stage_2_decision_engine_is_the_single_source_of_truth(self):
        """market_hunter.hunt_market() -> decision_engine.record_ladder_decision()
        -> data/decisions.jsonl (a temp copy here) — the SAME real score,
        never recomputed, never diverging."""
        with patch.object(
            mh, "RECORD_LADDER_DECISION",
            lambda niche, ladder, scored: record_ladder_decision(niche, ladder, scored, decisions_path=self.decisions_path),
        ):
            mh.hunt_market(limit=len(mh.SEED_CATEGORIES), write_opportunities=False)

        history = store.find_decisions_by_niche(REAL_NICHE, path=self.decisions_path)
        self.assertEqual(len(history), 1)
        recorded = history[0]
        self.assertEqual(recorded["status"], "ACCEPTED")
        self.assertEqual(recorded["ladder"], REAL_LADDER)
        self.assertEqual(recorded["decision_path"], "ladder_fast_gate")

        # The exact same real score as a direct, independent call —
        # ladder_opportunity_score() is deterministic, so this is a real
        # equality check, not a tautology: it proves market_hunter recorded
        # what it actually computed, not a stale or re-derived number.
        direct = po.ladder_opportunity_score(REAL_NICHE, ladder=REAL_LADDER)
        self.assertEqual(recorded["opportunity_score"], direct["ladder_score"])
        self.assertEqual(recorded["evaluation_snapshot"]["price"], direct["price"])

        self.recorded_score = recorded["opportunity_score"]
        self.recorded_price = recorded["evaluation_snapshot"]["price"]

    def test_stage_3_mission_control_read_path_reflects_the_same_decision(self):
        """decision_engine.ranking.rank_queue() is the exact function
        mission_control_api.py calls for the Decision Queue — proving
        Mission Control would show this real opportunity, not a stale one."""
        record_ladder_decision(
            REAL_NICHE, REAL_LADDER, po.ladder_opportunity_score(REAL_NICHE, ladder=REAL_LADDER),
            decisions_path=self.decisions_path,
        )
        queue = ranking.rank_queue(decisions_path=self.decisions_path, outcomes_path=_temp_path())
        matches = [d for d in queue if d["niche"] == REAL_NICHE]
        self.assertEqual(len(matches), 1)
        direct = po.ladder_opportunity_score(REAL_NICHE, ladder=REAL_LADDER)
        self.assertEqual(matches[0]["opportunity_score"], direct["ladder_score"], "Mission Control's queue must show the same real score, not a different one")

    def test_stage_4_factory_loop_gate_agrees_with_the_recorded_decision(self):
        """factory_loop.js's getLadderOpportunityScore() (the real
        automatic-tick gate) is a thin JS wrapper around profit_oracle.py
        --ladder-score — the literal same Python function decision_engine
        and market_hunter call. Verified via a real subprocess call (no
        mocking) that it returns the identical score/accepted/price."""
        script = f"""
        const fl = require({json.dumps(str(_FACTORY_ROOT / 'factory_loop.js'))});
        fl.getLadderOpportunityScore({json.dumps(REAL_NICHE)}, {json.dumps(REAL_LADDER)}).then(r => {{
          process.stdout.write(JSON.stringify(r));
        }});
        """
        result = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=30, cwd=str(_FACTORY_ROOT))
        self.assertEqual(result.returncode, 0, result.stderr)
        gate_result = json.loads(result.stdout.strip())
        self.assertTrue(gate_result["ok"])
        self.assertTrue(gate_result["accepted"])

        direct = po.ladder_opportunity_score(REAL_NICHE, ladder=REAL_LADDER)
        self.assertEqual(gate_result["score"], direct["ladder_score"], "the automatic tick's gate must agree exactly with the single source of truth")
        self.assertEqual(gate_result["price"], direct["price"])

    def test_stage_5_notification_and_production_brief_carry_the_same_numbers(self):
        """n8n/Telegram's payload (buildGoldenHunterNotifyPayload) and the
        production brief Paddle's price ultimately comes from
        (briefFromGoldenOpportunity) both derive from the SAME real
        opportunity object — no separate re-scoring, no separate price
        source, verified via real subprocess calls."""
        direct = po.ladder_opportunity_score(REAL_NICHE, ladder=REAL_LADDER)
        opportunity = {
            "niche": REAL_NICHE, "profit_score": 69, "verdict": "GOOD",
            "ladder": REAL_LADDER, "ladder_score": direct["ladder_score"],
            "ladder_accepted": True, "ladder_price": direct["price"],
        }
        script = f"""
        const fl = require({json.dumps(str(_FACTORY_ROOT / 'factory_loop.js'))});
        const {{ buildGoldenHunterNotifyPayload }} = require({json.dumps(str(_FACTORY_ROOT / 'lib' / 'n8n_notify.js'))});
        const opportunity = {json.dumps(opportunity)};
        const payload = buildGoldenHunterNotifyPayload(opportunity.niche, {{ score: opportunity.ladder_score, price: opportunity.ladder_price, reason: 'test' }});
        fl.briefFromGoldenOpportunity(opportunity).then(brief => {{
          process.stdout.write(JSON.stringify({{ payload, brief }}));
        }});
        """
        result = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=30, cwd=str(_FACTORY_ROOT))
        self.assertEqual(result.returncode, 0, result.stderr)
        out = json.loads(result.stdout.strip())

        self.assertEqual(out["payload"]["opportunity_score"], direct["ladder_score"])
        self.assertEqual(out["payload"]["price"], direct["price"])
        self.assertEqual(out["brief"]["price"], direct["price"], "the production brief Paddle's arm ultimately prices from must match the single source of truth, not a separately-derived number")
        self.assertEqual(out["brief"]["product_type"], "techdoc")


class TestFullProductGenerationPipelineEndToEnd(unittest.TestCase):
    """ADR-077 (Product Generation Pipeline) Requirement #7: one real,
    connected proof that every stage — Market Intelligence -> Opportunity
    Selection -> Product Specification -> AI Content Generation ->
    Packaging -> QA -> Metadata -> Paddle Product Creation -> Publishing
    Queue -> Finance Ledger -> Telegram Founder Report — actually wires
    together, carrying the SAME real production_id (Requirement #5) end
    to end. Real Groq content generation is not repeated here (already
    proven live by tests/test_product_package.py's
    TestCliDispatchAutoFillsSectionsForTechdoc) — book_generator.py's own
    subprocess is mocked so this test proves wiring, not content quality.
    Paddle is called with dry_run=True (this repo's standing convention:
    never spend real money in a test) but IS the real, registered
    PaddleArm — not a stub.

    python -m unittest tests.test_unified_pipeline_e2e.TestFullProductGenerationPipelineEndToEnd -v
    """

    def setUp(self):
        self.decisions_path = _temp_path()
        self.ledger_path = _temp_path(suffix=".jsonl")
        self.finance_path = _temp_path(suffix=".json")

        from channels import registry as channel_registry
        from channels.paddle_arm import PaddleArm
        channel_registry.register(PaddleArm())  # idempotent — a real, live arm, not a stub

    def tearDown(self):
        for p in (self.decisions_path, self.ledger_path, self.finance_path):
            if os.path.exists(p):
                os.remove(p)

    def test_full_pipeline_carries_one_real_production_id_through_every_stage(self):
        from production_factory import dossier as dossier_module
        from schemas.product import Product
        from channels import ledger
        from channels import registry as channel_registry
        from orchestrator.engines import production as production_engine

        # Stage 1+2: Market Intelligence -> Opportunity Selection. Reuses
        # the exact real scoring/recording path stages 1-2 above already
        # proved live (profit_oracle.ladder_opportunity_score() + the
        # ADR-076 single-source-of-truth recorder).
        scored = po.ladder_opportunity_score(REAL_NICHE, ladder=REAL_LADDER)
        self.assertTrue(scored["accepted"])
        record_ladder_decision(REAL_NICHE, REAL_LADDER, scored, decisions_path=self.decisions_path)
        decision = store.find_decisions_by_niche(REAL_NICHE, path=self.decisions_path)[0]
        self.assertEqual(decision["status"], "ACCEPTED")

        # Stage 3: Product Specification / Metadata — the real dossier,
        # production_factory/dossier.py's own structured-JSON contract
        # (Requirement #2/#6).
        dossier = dossier_module.build_production_dossier(decision)
        production_id = dossier["production_id"]
        self.assertEqual(production_id, f"PROD-{decision['decision_id']}")
        for key in ("product_specification", "pricing_strategy", "publishing_checklist"):
            self.assertIn(key, dossier)

        # Stage 4: AI Content Generation + Packaging + QA — the real
        # orchestrator production engine, with only the Groq-costly
        # book_generator.py subprocess mocked. Proves the SAME production_id
        # computed above is the one actually sent to generation.
        context = {"niche": REAL_NICHE, "dry_run": False, "decision_result": decision}
        fake_stdout = json.dumps({
            "success": True, "path": "/fake/path.pdf", "pages": 8,
            "product_type": "techdoc", "price": scored["price"],
        })
        fake_proc = MagicMock(stdout=fake_stdout)
        with patch.object(production_engine.subprocess, "run", return_value=fake_proc) as mock_run:
            production_result = production_engine.run(context)
        sent_payload = json.loads(mock_run.call_args.kwargs["input"])
        self.assertEqual(sent_payload["production_id"], production_id)
        self.assertTrue(production_result["success"])

        # Stage 5: Metadata carried into a real Product (schemas/product.py) —
        # proves source_id (the ledger's own product identity) resolves to
        # the SAME production_id, not the fallback timestamp.
        generated_record = {**production_result, "production_id": production_id}
        product = Product.from_jsonl_record(generated_record)
        self.assertEqual(product.source_id, production_id)
        self.assertFalse(product.needs_pricing)

        # Stage 6: Paddle Product Creation — the real, registered PaddleArm.
        # dry_run=True: validates real product shape, makes zero live API
        # calls (this repo's standing "never spend real money in a test" rule).
        paddle_arm = channel_registry.get("paddle")
        publish_result = paddle_arm.publish(product, dry_run=True)
        self.assertTrue(publish_result.ok)

        # Stage 7: Publishing Queue — the real ledger, proving the SAME
        # production_id is the recorded event's product identity.
        publish_event = ledger.record_publish_attempt(product, publish_result, ledger_path=self.ledger_path)
        self.assertEqual(publish_event["product_source_id"], production_id)

        # Stage 8: Finance Ledger — a real Paddle-shaped sale event
        # reconciled into finance_data.json via the real, already-unit-
        # tested reconciliation function (channels/ledger.py, ADR-077).
        ledger.record_sale("paddle", {"id": "txn_e2e_1", "details": {"totals": {"grand_total": "38800"}}}, ledger_path=self.ledger_path)
        reconciliation = ledger.reconcile_ledger_to_finance(ledger_path=self.ledger_path, finance_path=self.finance_path)
        self.assertEqual(reconciliation["reconciled"], 1)
        with open(self.finance_path, encoding="utf-8") as f:
            finance_data = json.load(f)
        self.assertEqual(finance_data["totalPaddle"], 388.0)

        # Stage 9: Telegram Founder Report — the real JS payload builder
        # (lib/n8n_notify.js, called via a real subprocess, no mocking),
        # proving the SAME production_id would reach the founder's Telegram
        # message (03_Production_Notify.prepared.json's "Build Telegram
        # Message" node reads body.production_id directly).
        script = f"""
        const {{ buildProductionNotifyPayload }} = require({json.dumps(str(_FACTORY_ROOT / 'lib' / 'n8n_notify.js'))});
        const dossier = {json.dumps(dossier, default=str)};
        process.stdout.write(JSON.stringify(buildProductionNotifyPayload(dossier)));
        """
        result = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=30, cwd=str(_FACTORY_ROOT))
        self.assertEqual(result.returncode, 0, result.stderr)
        telegram_payload = json.loads(result.stdout.strip())
        self.assertEqual(telegram_payload["production_id"], production_id)


if __name__ == "__main__":
    unittest.main()
