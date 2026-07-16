"""Tests for real_world_mode/ (ADR-056).

Runs with stdlib unittest. All network-calling functions are mocked
throughout — this suite never depends on live API availability, and
execute_production is never True in any test here, so no test ever
spawns a real book_generator.py subprocess or attempts a real publish.

    python -m unittest tests.test_real_world_mode -v
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from real_world_mode import operating_mode, signal_intake


def _temp_path(suffix=".jsonl"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


class TestSignalIntakeFromTier1Candidates(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _write_candidate(self, filename, data):
        with open(os.path.join(self.tmp_dir, filename), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    def test_empty_directory_yields_no_signals(self):
        result = signal_intake.intake_from_tier1_candidates(candidates_dir=self.tmp_dir)
        self.assertEqual(result, [])

    def test_missing_directory_never_throws(self):
        result = signal_intake.intake_from_tier1_candidates(candidates_dir="/no/such/dir")
        self.assertEqual(result, [])

    def test_real_github_source_shape_is_extracted_correctly(self):
        self._write_candidate("a.json", {
            "niche": "a real tier1 test niche",
            "source": {"platform": "github", "stars": 500, "created_at": "2026-01-01T00:00:00Z"},
        })
        result = signal_intake.intake_from_tier1_candidates(candidates_dir=self.tmp_dir)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["niche"], "a real tier1 test niche")
        self.assertEqual(result[0]["external_signal"], {"source": "github", "stars": 500, "created_at": "2026-01-01T00:00:00Z"})

    def test_real_hacker_news_source_shape_is_extracted_correctly(self):
        self._write_candidate("b.json", {
            "niche": "a real hn test niche",
            "source": {"platform": "hacker_news", "points": 150, "created_at": "2026-01-01T00:00:00Z"},
        })
        result = signal_intake.intake_from_tier1_candidates(candidates_dir=self.tmp_dir)
        self.assertEqual(result[0]["external_signal"]["source"], "hacker_news")
        self.assertEqual(result[0]["external_signal"]["points"], 150)

    def test_candidate_with_no_recognizable_source_gets_no_external_signal(self):
        self._write_candidate("c.json", {"niche": "a niche with unknown source", "source": {"platform": "product_hunt"}})
        result = signal_intake.intake_from_tier1_candidates(candidates_dir=self.tmp_dir)
        self.assertIsNone(result[0]["external_signal"])

    def test_malformed_json_file_is_skipped_never_crashes(self):
        with open(os.path.join(self.tmp_dir, "broken.json"), "w", encoding="utf-8") as f:
            f.write("{not valid json")
        result = signal_intake.intake_from_tier1_candidates(candidates_dir=self.tmp_dir)
        self.assertEqual(result, [])

    def test_candidate_missing_niche_field_is_skipped(self):
        self._write_candidate("d.json", {"source": {"platform": "github", "stars": 10}})
        result = signal_intake.intake_from_tier1_candidates(candidates_dir=self.tmp_dir)
        self.assertEqual(result, [])


class TestSignalIntakeFromOpportunitiesMd(unittest.TestCase):
    @patch("profit_oracle._read_opportunities")
    def test_reuses_profit_oracle_reader_directly(self, mock_read):
        mock_read.return_value = ["a real opportunities.md niche"]
        result = signal_intake.intake_from_opportunities_md()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["niche"], "a real opportunities.md niche")
        self.assertIsNone(result[0]["external_signal"])
        self.assertTrue(mock_read.called)


class TestRunRealWorldCycle(unittest.TestCase):
    def setUp(self):
        self.timeline_path = _temp_path()
        self.decisions_path = _temp_path()
        self.analysis_db_path = _temp_path()
        self.competitor_db_path = _temp_path(".json")
        for p in (
            patch("competitor_discovery._query_hn", return_value=[]),
            patch("competitor_discovery._query_github", return_value=[]),
            patch("market_intelligence_engine._query_hn_discussions", return_value=([], 0)),
            patch("market_intelligence_engine._query_github_issues", return_value=([], 0)),
            patch("competitor_discovery.COMPETITOR_DB_FILE", self.competitor_db_path),
        ):
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        for p in (self.timeline_path, self.decisions_path, self.analysis_db_path, self.competitor_db_path):
            if os.path.exists(p):
                os.remove(p)

    def test_no_real_signals_reports_honestly(self):
        with patch("real_world_mode.signal_intake.collect_all_real_signals", return_value=[]):
            result = operating_mode.run_real_world_cycle(timeline_path=self.timeline_path, decisions_path=self.decisions_path)
        self.assertEqual(result["processed"], 0)
        self.assertIn("reason", result)

    def test_each_real_signal_runs_through_the_unchanged_orchestrator(self):
        fake_signals = [
            {"niche": "real world mode test niche one", "external_signal": None, "source": "test"},
            {"niche": "real world mode test niche two", "external_signal": {"source": "github", "stars": 100}, "source": "test"},
        ]
        with patch("real_world_mode.signal_intake.collect_all_real_signals", return_value=fake_signals):
            result = operating_mode.run_real_world_cycle(
                timeline_path=self.timeline_path, decisions_path=self.decisions_path,
                analysis_db_file=self.analysis_db_path,
            )
        self.assertEqual(result["processed"], 2)
        for entry in result["results"]:
            stage_names = [s["engine"] for s in entry["stages"]]
            self.assertEqual(stage_names, ["market_intelligence", "decision", "production", "publishing", "learning"])

    def test_default_never_executes_production_or_publishing(self):
        fake_signals = [{"niche": "safety default test niche", "external_signal": None, "source": "test"}]
        with patch("real_world_mode.signal_intake.collect_all_real_signals", return_value=fake_signals):
            result = operating_mode.run_real_world_cycle(
                timeline_path=self.timeline_path, decisions_path=self.decisions_path,
                analysis_db_file=self.analysis_db_path,
            )
        stages = {s["engine"]: s for s in result["results"][0]["stages"]}
        self.assertEqual(stages["production"]["status"], "SKIPPED_NOT_APPLICABLE")
        self.assertEqual(stages["publishing"]["status"], "SKIPPED_NOT_APPLICABLE")

    def test_production_evidence_history_reflects_the_cycle_automatically(self):
        """The concrete proof of 'every platform outcome must update the
        Production Evidence history' — no special update code exists or
        is needed; production_evidence is a derived view, so it reflects
        new decisions the moment they're persisted."""
        from production_evidence import catalog as evidence_catalog

        fake_signals = [{"niche": "evidence auto update test niche", "external_signal": None, "source": "test"}]
        with patch("real_world_mode.signal_intake.collect_all_real_signals", return_value=fake_signals):
            operating_mode.run_real_world_cycle(
                timeline_path=self.timeline_path, decisions_path=self.decisions_path,
                analysis_db_file=self.analysis_db_path,
            )

        records = evidence_catalog.list_all_evidence_records(timeline_path=self.timeline_path, decisions_path=self.decisions_path)
        niches = {r["niche"] for r in records}
        self.assertIn("evidence auto update test niche", niches)


if __name__ == "__main__":
    unittest.main()
