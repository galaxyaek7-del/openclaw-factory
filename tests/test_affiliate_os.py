#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the affiliate/ OS layer (read-only joins + pure functions).

All I/O targets temp paths. No network (check_link_status is NOT called
here — it is explicitly opt-in per call). No revenue, no secrets.
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from affiliate import intelligence as intel
from affiliate import links
from affiliate import content_qa
from affiliate import control_center as cc

_NOW = datetime(2026, 9, 20, tzinfo=timezone.utc)


def _opp(**kw):
    base = {"opportunity_id": "CO-t", "verification_status": "VERIFIED",
            "commission_value": "10%", "last_verified": "2026-09-20",
            "evidence_url": ["https://example.com/p"]}
    base.update(kw)
    return base


class TestIntelligence(unittest.TestCase):
    def test_record_marks_present_vs_absent(self):
        rec = intel.program_record(_opp(cookie_duration=None), now=_NOW)
        self.assertEqual(rec["fields"]["commission_value"]["evidence"], "OBSERVED")
        self.assertEqual(rec["fields"]["cookie_duration"]["evidence"], "UNKNOWN")
        self.assertEqual(rec["freshness"]["status"], "FRESH")

    def test_score_promising_without_conversions(self):
        rec = intel.program_record(_opp(), now=_NOW)
        out = intel.score_category(rec, {})
        self.assertEqual(out["category"], "PROMISING")
        self.assertTrue(out["reasons"])

    def test_score_strong_requires_conversion(self):
        rec = intel.program_record(_opp(), now=_NOW)
        out = intel.score_category(rec, {"conversions": 2})
        self.assertEqual(out["category"], "STRONG_EVIDENCE")

    def test_score_hold_and_high_risk(self):
        rec = intel.program_record(_opp(), now=_NOW)
        self.assertEqual(intel.score_category(rec, {"hold": True})["category"], "HOLD")
        out = intel.score_category(rec, {"adverse": ["terms cut 50%"]})
        self.assertEqual(out["category"], "HIGH_RISK")

    def test_score_insufficient_for_unknown_heavy(self):
        rec = intel.program_record(
            {"opportunity_id": "CO-u", "verification_status": "THIRD_PARTY_ONLY",
             "last_verified": "2020-01-01"}, now=_NOW)
        out = intel.score_category(rec, {})
        self.assertIn(out["category"], ("INSUFFICIENT_EVIDENCE", "HOLD"))

    def test_kill_routing(self):
        self.assertEqual(intel.kill_decision("CLOSED")["state"], "HIBERNATE")
        self.assertEqual(intel.kill_decision("TERMS_CHANGED")["state"], "HIBERNATE")
        d = intel.kill_decision("VERIFIED", {"window_complete": True, "conversions": 0})
        self.assertEqual(d["state"], "HOLD")
        self.assertIn("clone", d["reason"].lower())
        self.assertEqual(
            intel.kill_decision("VERIFIED", {"conversions": 1})["state"], "ACTIVE")
        self.assertEqual(intel.kill_decision("VERIFIED", {})["state"], "MONITORING")
        self.assertEqual(
            intel.kill_decision("VERIFIED", {"compliance_risk": True})["state"], "HOLD")


class TestLinks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.reg = os.path.join(self.tmp, "links.jsonl")

    def test_register_and_list(self):
        r = links.register_link("Acme", "guide-1", "blog", "Q3", "Try it",
                                "example.com", registry_path=self.reg)
        self.assertTrue(r["ok"])
        rows = links.list_links(registry_path=self.reg)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["merchant_domain"], "example.com")

    def test_rejects_tokenized_urls_and_empties(self):
        bad = [("A", "c", "ch", "camp", "Try", "example.com/?sa=SECRET123"),
               ("A", "c", "ch", "camp", "Try", ""),
               ("", "c", "ch", "camp", "Try", "example.com")]
        for args in bad:
            self.assertFalse(links.register_link(*args, registry_path=self.reg)["ok"])
        self.assertEqual(links.list_links(registry_path=self.reg), [])

    def test_empty_registry_reads_empty(self):
        self.assertEqual(links.list_links(registry_path=os.path.join(self.tmp, "no.jsonl")), [])


class TestContentQA(unittest.TestCase):
    def test_pass_clean_asset(self):
        out = content_qa.qa_content({
            "title": "Guide", "body": "Do X, then Y. Takes an hour.",
            "disclosure": True, "cta_present": True,
            "pricing_claims": [{"text": "$10/mo", "evidence_date": "2026-09-20"}],
            "commission_claims": [], "thumbnail_claims": []}, now=_NOW)
        self.assertEqual(out["status"], "PASS")

    def test_hold_reasons(self):
        out = content_qa.qa_content({
            "title": "Get rich", "body": "Guaranteed income with no risk!",
            "disclosure": False, "cta_present": False,
            "pricing_claims": [{"text": "$10", "evidence_date": "2020-01-01"}],
            "thumbnail_claims": ["10x overnight"]}, now=_NOW)
        self.assertEqual(out["status"], "HOLD")
        self.assertGreaterEqual(len(out["failures"]), 4)


class TestControlCenter(unittest.TestCase):
    def test_build_writes_report_only(self):
        tmp = tempfile.mkdtemp()
        out = os.path.join(tmp, "cc.md")
        res = cc.build(report_path=out)
        self.assertTrue(res["ok"])
        text = Path(out).read_text(encoding="utf-8")
        self.assertIn("AFFILIATE CONTROL CENTER", text)
        self.assertIn("COMMERCIAL_TRUTH", text)
        self.assertIn("$0", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
