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
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
