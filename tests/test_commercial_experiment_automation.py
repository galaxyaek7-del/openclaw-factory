"""Tests for commercial_experiment_automation.py — the LEARN->SCALE/ITERATE/
KILL loop closure (Autonomous Enterprise Directive, 2026-08-15, gap #3).

Uses temp directories for every ledger (never touches the real data/ or the
real commercial_experiments.jsonl)."""

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import commercial_experiment_automation as cea
import commercial_experiments as ce


def _write(path, records):
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _defn(exp_id="EXP-SEO-001", created=None, duration_days=30, metric="page_views of guide-digitalocean-affiliate-program.html"):
    return {
        "record_type": "experiment_definition",
        "experiment_id": exp_id,
        "experiment_type": "affiliate_channel",
        "hypothesis": "SEO guide pages generate page views",
        "baseline": "0 page views before",
        "change": "publish guide pages",
        "metric": metric,
        "planned_duration_days": duration_days,
        "status": "RUNNING",
        "created_at": created or datetime.now(timezone.utc).isoformat(),
    }


def _view(page_id="guide-digitalocean-affiliate-program", day="2026-08-15", count=1):
    out = []
    for _ in range(count):
        out.append({"page_id": page_id, "timestamp": f"{day}T10:00:00+00:00", "referrer": None})
    return out


class ExperimentAutomationTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._root = Path(self._tmp.name)
        self._exp = self._root / "commercial_experiments.jsonl"
        self._views = self._root / "affiliate_page_views.jsonl"

    def tearDown(self):
        self._tmp.cleanup()

    def test_records_one_observation_per_experiment_per_day_from_real_views(self):
        _write(self._exp, [_defn()])
        _write(self._views, _view(count=3))
        r = cea.record_observations_from_real_ledgers(
            experiments_path=self._exp, page_views_path=self._views)
        self.assertEqual(r["recorded_observations"], 1, "3 views same day = exactly 1 observation")
        self.assertEqual(r["running_experiments"], 1)

    def test_record_is_idempotent_second_run_records_nothing_new(self):
        _write(self._exp, [_defn()])
        _write(self._views, _view(count=1))
        cea.record_observations_from_real_ledgers(experiments_path=self._exp, page_views_path=self._views)
        r2 = cea.record_observations_from_real_ledgers(experiments_path=self._exp, page_views_path=self._views)
        self.assertEqual(r2["recorded_observations"], 0)
        lines = [json.loads(l) for l in self._exp.read_text(encoding="utf-8").strip().splitlines() if l.strip()]
        obs = [l for l in lines if l.get("record_type") == "observation"]
        self.assertEqual(len(obs), 1)

    def test_no_observations_without_real_views(self):
        _write(self._exp, [_defn()])
        _write(self._views, [])
        r = cea.record_observations_from_real_ledgers(experiments_path=self._exp, page_views_path=self._views)
        self.assertEqual(r["recorded_observations"], 0)

    def test_evaluate_due_experiment_returns_iterate_when_insufficient_data(self):
        created = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
        _write(self._exp, [_defn(created=created, duration_days=30)])
        r = cea.evaluate_due_experiments(experiments_path=self._exp)
        self.assertEqual(r["evaluated"], 1)
        self.assertEqual(r["decisions"][0]["decision"], "ITERATE")

    def test_evaluate_skips_experiments_within_planned_window(self):
        _write(self._exp, [_defn(created=datetime.now(timezone.utc).isoformat(), duration_days=30)])
        r = cea.evaluate_due_experiments(experiments_path=self._exp)
        self.assertEqual(r["evaluated"], 0)

    def test_adopt_maps_to_scale_with_real_sample(self):
        created = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
        records = [_defn(created=created, duration_days=30)]
        for _ in range(30):
            records.append({"record_type": "observation", "experiment_id": "EXP-SEO-001", "arm": "baseline", "value": 10.0, "observed_at": "2026-08-01T00:00:00+00:00"})
        for _ in range(30):
            records.append({"record_type": "observation", "experiment_id": "EXP-SEO-001", "arm": "variant", "value": 15.0, "observed_at": "2026-08-01T00:00:00+00:00"})
        _write(self._exp, records)
        r = cea.evaluate_due_experiments(experiments_path=self._exp)
        self.assertEqual(r["decisions"][0]["decision"], "SCALE")
        self.assertEqual(r["decisions"][0]["status"], "SCALING")

    def test_retire_stale_no_observations_to_watch(self):
        # 33 days = within grace (30 planned + 7) but past window, 0 obs.
        created = (datetime.now(timezone.utc) - timedelta(days=33)).isoformat()
        _write(self._exp, [_defn(created=created, duration_days=30)])
        r = cea.retire_stale_experiments(experiments_path=self._exp)
        self.assertEqual(r["count"], 1)
        self.assertEqual(r["retired"][0]["decision"], "WATCH")

    def test_retire_grace_period_to_iterate(self):
        created = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
        records = [_defn(created=created, duration_days=30)]
        records.append({"record_type": "observation", "experiment_id": "EXP-SEO-001", "arm": "variant", "value": 1.0, "observed_at": "2026-08-01T00:00:00+00:00"})
        _write(self._exp, records)
        r = cea.retire_stale_experiments(experiments_path=self._exp)
        self.assertEqual(r["count"], 1)
        self.assertEqual(r["retired"][0]["decision"], "ITERATE")

    def test_list_experiments_surfaces_latest_status(self):
        created = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
        records = [_defn(created=created, duration_days=30)]
        records.append({"record_type": "status_update", "experiment_id": "EXP-SEO-001", "status": "KILLED", "decision": "KILL", "reason": "x", "updated_at": "2026-08-10T00:00:00+00:00"})
        _write(self._exp, records)
        listing = ce.list_experiments(experiments_path=self._exp)
        self.assertEqual(listing["experiments"][0]["status"], "KILLED")
        self.assertEqual(listing["experiments"][0]["decision"], "KILL")


if __name__ == "__main__":
    unittest.main()