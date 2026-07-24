"""Operational simulation (2026-07-23 audit): proves what nothing else
tests -- that factory_orchestrator.run_master_cycle(execute=True), the
real single entry point a human or Mission Control action invokes for
"governance + production in one call," actually drives a real
production + real publishing attempt through orchestrator.run_cycle(),
not just the Quality Gate/Board stages (already proven live in
ADR-091). tests/test_unified_pipeline_e2e.py already proves each later
stage (production, Paddle publish, ledger, finance) works when invoked
directly -- this proves run_master_cycle's own real wiring reaches them.

Same isolation discipline as test_unified_pipeline_e2e.py's
TestFullProductGenerationPipelineEndToEnd: every path parameter
run_master_cycle exposes is redirected to a temp file; the handful of
internal writes it does NOT expose a path override for (generation log,
dossier changelog, rejected-niche/quarantine logging, factory_state) are
suppressed via the same patches that file already established as this
repo's real seam for them.

    python -m unittest tests.test_master_cycle_production_e2e -v
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
import dossier_bundle.build_bundle as bb
import factory_state
import profit_oracle as po
from decision_engine import store
from decision_engine.engine import record_ladder_decision

import factory_orchestrator as orch

SYNTHETIC_NICHE = "synthetic test fixture automation toolkit zzz-do-not-produce"
SYNTHETIC_LADDER = "automation_tools"
# Founder-directed fix (2026-07-24): previously used a REAL SEED_CATEGORIES
# niche ("automated invoice processing toolkit for small businesses") --
# a founder-requested live full-cycle verification then actually produced
# it for real outside this test process, and dual inspection's real
# duplicate/quarantine checks (correctly reading real global production
# history) started failing this test. A synthetic niche name no real
# product will ever be named removes the collision permanently rather
# than deferring it to the next real niche this file happens to reuse.
# Unlike tests/test_unified_pipeline_e2e.py, this file never checks
# SEED_CATEGORIES membership -- ladder_opportunity_score() and
# run_master_cycle() both work on any niche string -- so no seed-list
# patch is needed here.


def _temp_path(suffix=".jsonl"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


class TestRunMasterCycleExecuteTrueDrivesRealProductionAndPublishing(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()
        self.board_path = _temp_path()
        self.timeline_path = _temp_path()
        self.outcomes_path = _temp_path()
        self.state_path = _temp_path(suffix=".json")
        self.changelog_path = _temp_path()
        self.competitor_db_file = _temp_path(suffix=".json")
        self.competitor_history_file = _temp_path()
        self.ledger_path = _temp_path()
        self.alerts_path = _temp_path()
        self.reopen_log_path = _temp_path()
        self._generated_files = []

        scored = po.ladder_opportunity_score(SYNTHETIC_NICHE, ladder=SYNTHETIC_LADDER)
        self.assertTrue(scored["accepted"], "fixture niche must still be a real ACCEPT")
        record_ladder_decision(SYNTHETIC_NICHE, SYNTHETIC_LADDER, scored, decisions_path=self.decisions_path)

        from channels import registry as channel_registry
        from channels.paddle_arm import PaddleArm
        channel_registry.register(PaddleArm())  # idempotent — real, registered arm, not a stub

    def tearDown(self):
        for p in (self.decisions_path, self.board_path, self.timeline_path, self.outcomes_path,
                  self.state_path, self.changelog_path, self.competitor_db_file, self.ledger_path,
                  self.competitor_history_file, self.alerts_path, self.reopen_log_path, *self._generated_files):
            if p and os.path.exists(p):
                os.remove(p)

    def _run(self):
        def _fake_generated(title, topic, titles):
            return [{"title": t, "content": f"real content for {t}"} for t in titles]

        # Directory-snapshot diff for cleanup, not path-parsing: the real
        # generated PDF/cover path is buried inside
        # production_result.business_lifecycle.execution_status[i].output
        # (a real, deeply-nested, timeline-derived shape) — far too
        # fragile to parse reliably here. A before/after listing of
        # books/ and books/covers/ is robust regardless of that shape,
        # and is exactly how this exact gap was actually caught during
        # the audit that wrote this test (a real generated PDF/cover pair
        # was silently missed by naive prod.get("path") cleanup and had
        # to be found and removed by hand).
        books_dir = _FACTORY_ROOT / "books"
        covers_dir = books_dir / "covers"
        before = set(books_dir.glob("*.pdf")) | set(covers_dir.glob("*"))

        # FACTORY_LIVE_PUBLISH deliberately left unset/false: this test
        # proves the real wiring reaches the publishing stage, not that
        # it can make it go live — orchestrator/engines/publishing.py's
        # own third-barrier check (dry_run = ... or not
        # FACTORY_LIVE_PUBLISH-enabled) must force dry_run=True
        # regardless, so no real external API call happens either way.
        with patch.object(bg, "ai_generate_techdoc_content", side_effect=_fake_generated), \
             patch.object(bg, "groq_chat", side_effect=RuntimeError("no network in test")), \
             patch.object(bb, "_CHANGELOG_PATH", self.changelog_path), \
             patch.object(factory_state, "DEFAULT_STATE_PATH", Path(self.state_path)), \
             patch.object(bg, "_record_rejected_niche"), \
             patch.object(bg, "_log_generation"), \
             patch.object(bg.INSPECTORS, "_log_quarantine"), \
             patch.dict(os.environ, {"FACTORY_LIVE_PUBLISH": ""}, clear=False):
            result = orch.run_master_cycle(
                SYNTHETIC_NICHE, execute=True, decisions_path=self.decisions_path,
                board_path=self.board_path, timeline_path=self.timeline_path,
                outcomes_path=self.outcomes_path, state_path=self.state_path,
                competitor_db_file=self.competitor_db_file, ledger_path=self.ledger_path,
                competitor_history_file=self.competitor_history_file, alerts_path=self.alerts_path,
                reopen_log_path=self.reopen_log_path,
            )

        after = set(books_dir.glob("*.pdf")) | set(covers_dir.glob("*"))
        self._generated_files.extend(str(p) for p in (after - before))
        return result

    def test_production_actually_executes_and_succeeds(self):
        result = self._run()
        prod = result["production_result"]
        self.assertIsNotNone(prod, "execute=True with a real ACCEPTED decision must produce a real production_result, not None")
        self.assertTrue(prod["executed"])
        self.assertTrue(prod["quality_validation"]["passed"], prod["quality_validation"])

    def test_publishing_result_reaches_the_top_level_caller(self):
        """revenue_pipeline.pipeline.process_opportunity() only ever
        extracts the 'production' stage from orch.run_cycle()'s
        stage_results -- the 'publishing' stage's result (dry-run or
        real, which arms were tried, whether Paddle/Gumroad/Etsy
        accepted it) is never read from there. It still reaches the top
        level caller, but indirectly: business_lifecycle is built
        separately, by re-reading the same real timeline log every stage
        (including publishing) appends to. This test locks in that the
        information genuinely arrives, not that it arrives via the path
        an audit might naively assume (production_result.publishing)."""
        result = self._run()
        prod = result["production_result"]
        lifecycle = prod["business_lifecycle"]
        self.assertIn("publishing_status", lifecycle)
        self.assertTrue(lifecycle["publishing_status"], "a real execute=True run must have a non-empty real publishing_status")
        attempted = lifecycle["platform"]["attempted"]
        self.assertIn("paddle", attempted, "the real, registered PaddleArm must have been attempted")


if __name__ == "__main__":
    unittest.main()
