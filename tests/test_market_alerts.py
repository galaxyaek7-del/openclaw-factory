"""Tests for market_alerts.py (Live Competitive Intelligence Layer,
Market Evidence & Alerting layer, 2026-07-23).

Runs with stdlib unittest. Zero live network calls -- auto-detection
reads only an already-persisted, temp-file-isolated competitor
database/snapshot; manual detection reads only a temp-file-isolated
market_evidence.jsonl.

    python -m unittest tests.test_market_alerts -v
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import competitor_discovery as cd
import market_alerts as ma
import market_evidence as me


def _temp_path(suffix=".jsonl"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


class TestSeverityHelpers(unittest.TestCase):
    def test_percent_growth_computes_a_real_percentage(self):
        self.assertEqual(ma._percent_growth(100, 250), 150.0)

    def test_percent_growth_is_none_when_old_value_is_zero_or_missing(self):
        self.assertIsNone(ma._percent_growth(0, 50))
        self.assertIsNone(ma._percent_growth(None, 50))

    def test_severity_for_new_competitor_by_real_category(self):
        self.assertEqual(ma._severity_for_new_competitor({"category": "Enterprise Leader"}), "Critical")
        self.assertEqual(ma._severity_for_new_competitor({"category": "Direct Competitor"}), "High")
        self.assertEqual(ma._severity_for_new_competitor({"category": "Emerging Startup"}), "Medium")
        self.assertEqual(ma._severity_for_new_competitor({"category": "Alternative Solution"}), "Medium")
        self.assertEqual(ma._severity_for_new_competitor({"category": "Unclassified"}), "Low")
        self.assertEqual(ma._severity_for_new_competitor({}), "Low")

    def test_severity_for_growth_signal_scales_with_real_percentage(self):
        self.assertEqual(ma._severity_for_growth_signal({"from": 100, "to": 250})[0], "High")   # 150%
        self.assertEqual(ma._severity_for_growth_signal({"from": 100, "to": 130})[0], "Medium")  # 30%
        self.assertEqual(ma._severity_for_growth_signal({"from": 100, "to": 110})[0], "Low")      # 10%
        self.assertEqual(ma._severity_for_growth_signal({"from": 0, "to": 50})[0], "Medium")       # not percentage-comparable


class TestDetectAutoAlerts(unittest.TestCase):
    def setUp(self):
        self.db_path = _temp_path(suffix=".json")

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_no_cached_snapshot_yields_no_alerts(self):
        self.assertEqual(ma.detect_auto_alerts("a niche never discovered", db_file=self.db_path), [])

    def test_no_real_history_yet_yields_no_alerts(self):
        db = {cd._normalize_key("n"): {"total_found": 2, "changes": {"has_history": False}}}
        cd.save_database(db, db_file=self.db_path)
        self.assertEqual(ma.detect_auto_alerts("n", db_file=self.db_path), [])

    def test_a_real_new_enterprise_leader_is_a_critical_alert(self):
        db = {cd._normalize_key("n"): {
            "total_found": 3,
            "changes": {
                "has_history": True, "compared_at": "2026-07-23T00:00:00+00:00",
                "new_competitors": [{"name": "BigCo", "category": "Enterprise Leader", "category_reason": "x"}],
                "disappeared_competitors": [], "growth_signals": [],
            },
        }}
        cd.save_database(db, db_file=self.db_path)
        alerts = ma.detect_auto_alerts("n", db_file=self.db_path)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["event_type"], "new_competitor_appeared")
        self.assertEqual(alerts[0]["severity"], "Critical")
        self.assertEqual(alerts[0]["confidence"], 1.0)
        self.assertEqual(alerts[0]["source"], "competitor_discovery")

    def test_a_real_disappeared_competitor_is_a_low_alert(self):
        db = {cd._normalize_key("n"): {
            "total_found": 1,
            "changes": {
                "has_history": True, "compared_at": "2026-07-23T00:00:00+00:00",
                "new_competitors": [], "disappeared_competitors": [{"name": "GoneCo"}], "growth_signals": [],
            },
        }}
        cd.save_database(db, db_file=self.db_path)
        alerts = ma.detect_auto_alerts("n", db_file=self.db_path)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["event_type"], "competitor_disappeared")
        self.assertEqual(alerts[0]["severity"], "Low")

    def test_a_real_growth_signal_carries_its_own_percent_growth_as_evidence(self):
        db = {cd._normalize_key("n"): {
            "total_found": 1,
            "changes": {
                "has_history": True, "compared_at": "2026-07-23T00:00:00+00:00",
                "new_competitors": [], "disappeared_competitors": [],
                "growth_signals": [{"name": "GrowCo", "metric": "github_stars", "from": 100, "to": 300}],
            },
        }}
        cd.save_database(db, db_file=self.db_path)
        alerts = ma.detect_auto_alerts("n", db_file=self.db_path)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["event_type"], "competitor_growth_signal")
        self.assertEqual(alerts[0]["severity"], "High")
        self.assertEqual(alerts[0]["evidence"]["percent_growth"], 200.0)

    def test_dedupe_key_is_stable_and_distinguishes_competitors(self):
        db = {cd._normalize_key("n"): {
            "total_found": 2,
            "changes": {
                "has_history": True, "compared_at": "2026-07-23T00:00:00+00:00",
                "new_competitors": [
                    {"name": "A", "category": "Direct Competitor"},
                    {"name": "B", "category": "Direct Competitor"},
                ],
                "disappeared_competitors": [], "growth_signals": [],
            },
        }}
        cd.save_database(db, db_file=self.db_path)
        alerts = ma.detect_auto_alerts("n", db_file=self.db_path)
        self.assertEqual(len({a["dedupe_key"] for a in alerts}), 2)


class TestDetectManualAlerts(unittest.TestCase):
    def setUp(self):
        self.evidence_path = _temp_path()

    def tearDown(self):
        if os.path.exists(self.evidence_path):
            os.remove(self.evidence_path)

    def test_no_competitor_events_yields_no_alerts(self):
        me.record_evidence("n", "demo_request", {}, evidence_path=self.evidence_path)
        self.assertEqual(ma.detect_manual_alerts("n", evidence_path=self.evidence_path), [])

    def test_a_real_customer_migration_is_a_critical_alert(self):
        me.record_evidence(
            "n", "competitor_customer_migration",
            {"competitor": "Acme", "source_url": "https://example.com/case-study"},
            evidence_path=self.evidence_path,
        )
        alerts = ma.detect_manual_alerts("n", evidence_path=self.evidence_path)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["severity"], "Critical")
        self.assertEqual(alerts[0]["confidence"], 1.0)
        self.assertEqual(alerts[0]["evidence"]["competitor"], "Acme")

    def test_a_real_security_incident_is_a_low_alert(self):
        me.record_evidence(
            "n", "competitor_security_incident",
            {"competitor": "Acme", "source_url": "https://example.com/breach-report"},
            evidence_path=self.evidence_path,
        )
        alerts = ma.detect_manual_alerts("n", evidence_path=self.evidence_path)
        self.assertEqual(alerts[0]["severity"], "Low")

    def test_dedupe_key_is_stable_per_recorded_event(self):
        me.record_evidence(
            "n", "competitor_funding_round",
            {"competitor": "Acme", "source_url": "https://example.com/funding"},
            evidence_path=self.evidence_path,
        )
        alerts = ma.detect_manual_alerts("n", evidence_path=self.evidence_path)
        self.assertEqual(len(alerts), 1)
        self.assertIn("competitor_funding_round", alerts[0]["dedupe_key"])


class TestScanAndGetActiveAlerts(unittest.TestCase):
    def setUp(self):
        self.db_path = _temp_path(suffix=".json")
        self.evidence_path = _temp_path()
        self.alerts_path = _temp_path()

    def tearDown(self):
        for p in (self.db_path, self.evidence_path, self.alerts_path):
            if os.path.exists(p):
                os.remove(p)

    def test_scan_with_nothing_real_to_find_persists_nothing(self):
        result = ma.scan_market_alerts("n", db_file=self.db_path, evidence_path=self.evidence_path, alerts_path=self.alerts_path)
        self.assertEqual(result["new_alert_count"], 0)
        self.assertFalse(os.path.exists(self.alerts_path), "a scan that finds nothing real must never create the alerts file")

    def test_scan_persists_a_real_auto_detected_alert(self):
        db = {cd._normalize_key("n"): {
            "total_found": 1,
            "changes": {
                "has_history": True, "compared_at": "2026-07-23T00:00:00+00:00",
                "new_competitors": [{"name": "BigCo", "category": "Enterprise Leader"}],
                "disappeared_competitors": [], "growth_signals": [],
            },
        }}
        cd.save_database(db, db_file=self.db_path)
        result = ma.scan_market_alerts("n", db_file=self.db_path, evidence_path=self.evidence_path, alerts_path=self.alerts_path)
        self.assertEqual(result["new_alert_count"], 1)
        active = ma.get_active_alerts("n", alerts_path=self.alerts_path)
        self.assertEqual(active["total"], 1)
        self.assertEqual(active["by_severity_counts"]["Critical"], 1)

    def test_rescanning_the_same_unchanged_snapshot_never_re_alerts_no_spam(self):
        db = {cd._normalize_key("n"): {
            "total_found": 1,
            "changes": {
                "has_history": True, "compared_at": "2026-07-23T00:00:00+00:00",
                "new_competitors": [{"name": "BigCo", "category": "Direct Competitor"}],
                "disappeared_competitors": [], "growth_signals": [],
            },
        }}
        cd.save_database(db, db_file=self.db_path)
        first = ma.scan_market_alerts("n", db_file=self.db_path, evidence_path=self.evidence_path, alerts_path=self.alerts_path)
        second = ma.scan_market_alerts("n", db_file=self.db_path, evidence_path=self.evidence_path, alerts_path=self.alerts_path)
        self.assertEqual(first["new_alert_count"], 1)
        self.assertEqual(second["new_alert_count"], 0, "identical underlying event must never alert twice")
        self.assertEqual(ma.get_active_alerts("n", alerts_path=self.alerts_path)["total"], 1)

    def test_scan_persists_a_real_manual_alert(self):
        me.record_evidence(
            "n", "competitor_pricing_change",
            {"competitor": "Acme", "source_url": "https://example.com/pricing"},
            evidence_path=self.evidence_path,
        )
        result = ma.scan_market_alerts("n", db_file=self.db_path, evidence_path=self.evidence_path, alerts_path=self.alerts_path)
        self.assertEqual(result["new_alert_count"], 1)
        self.assertEqual(result["new_alerts"][0]["event_type"], "competitor_pricing_change")

    def test_get_active_alerts_never_triggers_a_scan(self):
        result = ma.get_active_alerts("n", alerts_path=self.alerts_path)
        self.assertEqual(result["total"], 0)
        self.assertFalse(os.path.exists(self.alerts_path), "a read-only lookup must never create the alerts file")

    def test_get_active_alerts_is_scoped_to_the_requested_niche_only(self):
        me.record_evidence(
            "niche a", "competitor_partnership",
            {"competitor": "Acme", "source_url": "https://example.com/partnership"},
            evidence_path=self.evidence_path,
        )
        ma.scan_market_alerts("niche a", db_file=self.db_path, evidence_path=self.evidence_path, alerts_path=self.alerts_path)
        self.assertEqual(ma.get_active_alerts("niche a", alerts_path=self.alerts_path)["total"], 1)
        self.assertEqual(ma.get_active_alerts("a different niche", alerts_path=self.alerts_path)["total"], 0)

    def test_every_alert_carries_all_6_required_fields(self):
        me.record_evidence(
            "n", "competitor_hiring_spike",
            {"competitor": "Acme", "source_url": "https://example.com/jobs"},
            evidence_path=self.evidence_path,
        )
        result = ma.scan_market_alerts("n", db_file=self.db_path, evidence_path=self.evidence_path, alerts_path=self.alerts_path)
        alert = result["new_alerts"][0]
        for field in ("alerted_at", "source", "evidence", "confidence", "recommended_action", "severity"):
            self.assertIn(field, alert)
        self.assertIn(alert["severity"], ma.SEVERITY_LEVELS)


if __name__ == "__main__":
    unittest.main()
