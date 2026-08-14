"""Tests for golden_hunter/evidence_identity.py — the Evidence Identity
Analyzer (founder priority, 2026-08-14).

The bug this locks in: real evidence is keyed by the OPPORTUNITY NAME, not
the stable decision ID. When an opportunity is renamed/repositioned, its
real evidence stays under the OLD name and is unreachable under the NEW
decision's name — gates report "PAIN NOT ESTABLISHED" and confidence drops
even though real evidence exists.

These tests prove the analyzer:
  - resolves the identity name-set of a decision_id ONLY from real recorded
    facts (own record + recorded RepositioningAttempt lineage),
  - recovers real evidence across every proven identity name,
  - NEVER attributes evidence without a recorded lineage link,
  - NEVER fabricates/duplicates pain or payment evidence,
  - recomputes confidence from evidence_completeness machinery only, with
    the acceptance gate never re-run.

All tests use temp files only — nothing here ever writes to the real
data/ ledger or evidence stores (same isolation discipline as
tests/test_repositioning.py).

    python -m unittest tests.test_evidence_identity -v
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

from golden_hunter import evidence_identity as ei
from golden_hunter import repositioning

ORIGINAL_NICHE = "AI Agent Blueprint for Legal Case Research Automation for Solo Attorneys"
RENAMED_NICHE = "Legal Case Research Automation System for Solo Attorneys"
ORIGINAL_ID = "13ab500d184b6dd4"
ACCEPTED_ID = "5214fb83a464299d"


def _temp_path(suffix=".jsonl"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


def _write_jsonl(records):
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return path


def _write_json(obj):
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    return path


def _original_decision(**overrides):
    base = {
        "decision_id": ORIGINAL_ID,
        "niche": ORIGINAL_NICHE,
        "status": "REJECTED",
        "opportunity_score": 55.8,
        "ladder": "automation_tools",
        "reasoning": ["price $66 below the $97 floor"],
        "evaluation_snapshot": {},
    }
    base.update(overrides)
    return base


def _accepted_decision(**overrides):
    """Mirrors the REAL accepted legal decision's recorded snapshot fields
    (components, defensibility, ai_leverage, payment_evidence, price)."""
    base = {
        "decision_id": ACCEPTED_ID,
        "niche": RENAMED_NICHE,
        "status": "ACCEPTED",
        "opportunity_score": 68.7,
        "ladder": "automation_tools",
        "reasoning": ["accepted: all 8 gates satisfied"],
        "evaluation_snapshot": {
            "price": 194,
            "components": {
                "payment_evidence_score": 70.0,
                "market_demand": 54,
                "competition_favorability": 70,
                "profit_potential": 75,
                "recurring_revenue_potential": 55,
                "reusability": 80,
                "automation_potential": 90,
            },
            "defensibility": {"score": 70, "level": "متوسطة-عالية"},
            "ai_leverage": {"score": 70, "level": "عالية"},
            "payment_evidence": [
                {"event_type": "freelancer_agency_pricing",
                 "source_url": "https://owlesq.com/x",
                 "quote": "Harvey requires a 20-seat minimum",
                 "recorded_at": "2026-08-14T00:15:32+00:00"},
            ],
        },
    }
    base.update(overrides)
    return base


def _repositioning_attempt(**overrides):
    base = {
        "attempt_id": "attempt-test-1",
        "original_decision_id": ORIGINAL_ID,
        "original_niche": ORIGINAL_NICHE,
        "rejection_reason": "rejected: price $66 below $97 profit floor",
        "original_score": 55.8,
        "original_positioning": ORIGINAL_NICHE,
        "proposed_positioning": RENAMED_NICHE,
        "changed_pricing": 194,
        "resulting_score": 68.7,
        "final_outcome": "ACCEPTED",
        "recorded_at": "2026-08-14T00:16:53+00:00",
        "ladder": "automation_tools",
    }
    base.update(overrides)
    return base


def _real_pain_under_original_name():
    return {
        "pain_score": 20,
        "confidence": "medium",
        "reason": "10 GitHub issue, 4 إشارة ألم لغوية",
        "real_evidence": {
            "github_issues_found": 10,
            "github_issues_total": 276,
            "pain_language_hits": 4,
            "willingness_to_pay_hits": 0,
        },
        "cached_at": "2026-07-31T14:11:09+00:00",
    }


def _empty_pain_under_renamed_name():
    return {
        "pain_score": None,
        "confidence": "low",
        "reason": "لا نتائج حقيقية",
        "real_evidence": {
            "github_issues_found": 0,
            "pain_language_hits": 0,
            "willingness_to_pay_hits": 0,
        },
        "cached_at": "2026-08-14T00:15:35+00:00",
    }


def _write_pain_cache(pain_cache_path, extra=None):
    cache = {ei._normalize(ORIGINAL_NICHE): _real_pain_under_original_name()}
    cache[ei._normalize(RENAMED_NICHE)] = _empty_pain_under_renamed_name()
    if extra:
        cache.update(extra)
    with open(pain_cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)


def _write_evidence(evidence_path, extra=None):
    records = [
        {"niche": ORIGINAL_NICHE, "event_type": "freelancer_agency_pricing",
         "payload": {"source_url": "https://owlesq.com/x", "quote": "Harvey requires a 20-seat minimum"},
         "source": "test", "recorded_at": "2026-08-14T00:15:32+00:00"},
        {"niche": RENAMED_NICHE, "event_type": "freelancer_agency_pricing",
         "payload": {"source_url": "https://costbench.com/x", "quote": "CoCounsel $104-$639/user/month"},
         "source": "test", "recorded_at": "2026-08-14T00:16:44+00:00"},
    ]
    if extra:
        records.extend(extra)
    with open(evidence_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


class TestEvidenceIdentity(unittest.TestCase):
    def setUp(self):
        self._paths = []
        self.decisions_path = _write_jsonl([_original_decision(), _accepted_decision()])
        self.pain_cache_path = _write_json({})
        self.evidence_path = _write_jsonl([])
        self.attempts_path = _temp_path(".jsonl")
        self._paths += [self.decisions_path, self.pain_cache_path,
                        self.evidence_path, self.attempts_path]

    def tearDown(self):
        for p in self._paths:
            if os.path.exists(p):
                os.remove(p)

    def _attempts(self, records=None):
        if records is None:
            records = [_repositioning_attempt()]
        self.attempts_path = _write_jsonl(records)
        self._paths.append(self.attempts_path)

    def _pipeline(self, with_lineage=True):
        _write_pain_cache(self.pain_cache_path)
        _write_evidence(self.evidence_path)
        if with_lineage:
            self._attempts()
        return ei.recompute_confidence(
            ACCEPTED_ID,
            decisions_path=self.decisions_path,
            attempts_path=self.attempts_path,
            pain_cache_path=self.pain_cache_path,
            evidence_path=self.evidence_path,
        )

    # ---- identity resolution ----

    def test_identity_without_lineage_is_only_own_niche(self):
        identity = ei.resolve_identity_names(
            ACCEPTED_ID, decisions_path=self.decisions_path, attempts_path=self.attempts_path)
        self.assertEqual(identity["identity_names"], [RENAMED_NICHE])
        self.assertNotIn(ORIGINAL_NICHE, identity["identity_names"])

    def test_identity_resolves_original_name_via_recorded_rename(self):
        self._attempts()
        identity = ei.resolve_identity_names(
            ACCEPTED_ID, decisions_path=self.decisions_path, attempts_path=self.attempts_path)
        self.assertEqual(identity["identity_names"], [RENAMED_NICHE, ORIGINAL_NICHE])
        # provenance must cite the real recorded attempt, never a guess
        self.assertIn("attempt-test-1", json.dumps(identity["provenance"]))

    def test_forward_lineage_from_original_decision_id(self):
        self._attempts()
        identity = ei.resolve_identity_names(
            ORIGINAL_ID, decisions_path=self.decisions_path, attempts_path=self.attempts_path)
        self.assertIn(RENAMED_NICHE, identity["identity_names"])

    def test_unknown_decision_returns_error_dict(self):
        self._attempts()
        result = ei.recompute_confidence(
            "no-such-decision",
            decisions_path=self.decisions_path,
            attempts_path=self.attempts_path,
            pain_cache_path=self.pain_cache_path,
            evidence_path=self.evidence_path,
        )
        self.assertIn("error", result)

    # ---- evidence recovery (rename survival) ----

    def test_real_pain_evidence_survives_rename_with_lineage(self):
        result = self._pipeline(with_lineage=True)
        self.assertIsNotNone(result["recovered_pain"])
        self.assertEqual(result["recovered_pain"]["proven_under"], ORIGINAL_NICHE)
        self.assertEqual(result["recovered_pain"]["real_evidence"]["pain_language_hits"], 4)

    def test_evidence_not_claimed_without_recorded_lineage(self):
        """No lineage record -> the analyzer must NOT attribute the original
        name's evidence to the accepted decision ID (no guessing)."""
        result = self._pipeline(with_lineage=False)
        self.assertIsNone(result["recovered_pain"])
        self.assertEqual(result["old_coverage_pct"], result["new_coverage_pct"])

    def test_no_pain_evidence_never_fabricates(self):
        empty = {ei._normalize(ORIGINAL_NICHE): _empty_pain_under_renamed_name()}
        _write_pain_cache(self.pain_cache_path, extra={})
        with open(self.pain_cache_path, "w", encoding="utf-8") as f:
            json.dump(empty, f, ensure_ascii=False)
        self._attempts()
        result = ei.recompute_confidence(
            ACCEPTED_ID,
            decisions_path=self.decisions_path,
            attempts_path=self.attempts_path,
            pain_cache_path=self.pain_cache_path,
            evidence_path=self.evidence_path,
        )
        self.assertIsNone(result["recovered_pain"])
        self.assertEqual(result["old_coverage_pct"], result["new_coverage_pct"])
        self.assertIn("pain_severity", result["new_missing"])

    # ---- confidence recompute (evidence_completeness only, never re-gates) ----

    def test_confidence_rises_only_by_proven_evidence(self):
        result = self._pipeline(with_lineage=True)
        self.assertEqual(result["old_coverage_pct"], 72.7)
        self.assertIn("pain_severity", result["old_missing"])
        self.assertEqual(result["new_coverage_pct"], 81.8)
        self.assertNotIn("pain_severity", result["new_missing"])
        self.assertEqual(result["new_confidence"], result["new_coverage_pct"])

    def test_payment_evidence_deduplicated_across_names(self):
        """The same real record appearing under both names is counted once."""
        self._attempts()
        _write_evidence(self.evidence_path, extra=[
            {"niche": ORIGINAL_NICHE, "event_type": "freelancer_agency_pricing",
             "payload": {"source_url": "https://owlesq.com/x", "quote": "Harvey requires a 20-seat minimum"},
             "source": "test", "recorded_at": "2026-08-14T00:15:32+00:00"},
        ])
        result = ei.recompute_confidence(
            ACCEPTED_ID,
            decisions_path=self.decisions_path,
            attempts_path=self.attempts_path,
            pain_cache_path=self.pain_cache_path,
            evidence_path=self.evidence_path,
        )
        urls = [e["source_url"] for e in result["recovered_payment_evidence"]]
        self.assertEqual(len(urls), 2)
        self.assertEqual(len(set(urls)), 2)
        self.assertEqual(urls.count("https://owlesq.com/x"), 1)

    def test_confidence_mapping_is_identity(self):
        result = self._pipeline(with_lineage=True)
        self.assertEqual(result["new_confidence"], result["new_coverage_pct"])

    def test_module_docstring_discloses_no_regate(self):
        self.assertIn("never", ei.__doc__)


class TestResolveIdentityEdgeCases(unittest.TestCase):
    def setUp(self):
        self._paths = []

    def tearDown(self):
        for p in self._paths:
            if os.path.exists(p):
                os.remove(p)

    def test_missing_decisions_file_returns_empty_identity(self):
        identity = ei.resolve_identity_names(ACCEPTED_ID, decisions_path=_temp_path())
        self.assertEqual(identity["identity_names"], [])


if __name__ == "__main__":
    unittest.main()
