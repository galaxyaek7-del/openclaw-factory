"""Intake-gate regression tests (Cycle 107 repair, 2026-10-20).

The defect these tests exist for: three discovery rounds in a row (EUDR 19/25,
CBAM 15/25, EmpCo 16/25) were scored first and rejected afterwards, all on the
same hard gate -- "materially duplicated by an adequate free alternative".
Scoring a product that cannot be built wastes the cycle and makes the score
something to argue with. These tests pin the gate that now runs first, and pin
the retrieval classification that Cycle 107 proved was being assumed wrongly
(a 200 is not proof of content; a 202 with 0 bytes is not "served"; 403/404/DNS
are not evidence).
"""
import ast
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import market_discovery_engine as mde

ROOT = Path(__file__).resolve().parent.parent


def _candidate(**over):
    base = {
        "name": "fixture candidate",
        "cited_urls": [
            {"url": "https://authority.example/obligation", "source_type": "official"},
            {"url": "https://vendor.example/free-template", "source_type": "vendor_free"},
        ],
        "free_alternative": {
            "urls": ["https://vendor.example/free-template"],
            "materially_duplicates": False,
            "demonstrated_advantage": "a branching determination the free template leaves to counsel",
        },
        "paid_comparison": {
            "competitors": ["Paid Kit $99"],
            "differentiator": "handles the role determination the paid kit treats as out of scope",
        },
        "buyer_channel": {"buyer": "EU importers", "channel": "direct download"},
        "build_cost_usd": 0,
        "claimed_score": 19,
    }
    base.update(over)
    return base


def _ok_retrievals():
    return {
        "https://authority.example/obligation": {
            "url": "https://authority.example/obligation", "status": "FETCHED_OK",
            "detail": "HTTP 200 with 1000 bytes", "counts_as_evidence": True,
            "source_type": "official"},
        "https://vendor.example/free-template": {
            "url": "https://vendor.example/free-template", "status": "FETCHED_OK",
            "detail": "HTTP 200 with 1000 bytes", "counts_as_evidence": True,
            "source_type": "vendor_free"},
    }


class ClassifierTests(unittest.TestCase):
    def test_served_with_body_is_evidence(self):
        got = mde.classify_source(status_code=200, body_bytes=1200)
        self.assertEqual(got["status"], "FETCHED_OK")
        self.assertTrue(got["counts_as_evidence"])

    def test_202_with_empty_body_is_not_served(self):
        # The real EUR-Lex behaviour: 202, zero bytes. Cycle 107 was close to
        # citing this as a fetch.
        got = mde.classify_source(status_code=202, body_bytes=0)
        self.assertEqual(got["status"], "UNVERIFIED")
        self.assertFalse(got["counts_as_evidence"])

    def test_bot_protection_is_blocked_not_missing(self):
        for code in (401, 403, 429):
            got = mde.classify_source(status_code=code)
            self.assertEqual(got["status"], "BLOCKED", code)
            self.assertFalse(got["counts_as_evidence"])

    def test_gone_is_dead(self):
        for code in (404, 410):
            self.assertEqual(mde.classify_source(status_code=code)["status"], "DEAD")

    def test_dns_failure_is_dead(self):
        got = mde.classify_source(error="dns getaddrinfo failed")
        self.assertEqual(got["status"], "DEAD")
        self.assertFalse(got["counts_as_evidence"])

    def test_tls_or_connection_failure_is_unverified(self):
        for err in ("tls certificate verify failed", "connection closed"):
            self.assertEqual(mde.classify_source(error=err)["status"], "UNVERIFIED")

    def test_redirect_needs_an_observed_destination(self):
        same = mde.classify_source(status_code=302, requested_url="https://a.example",
                                   final_url="https://a.example")
        moved = mde.classify_source(status_code=302, requested_url="https://a.example",
                                    final_url="https://b.example")
        self.assertEqual(same["status"], "UNVERIFIED")
        self.assertEqual(moved["status"], "REDIRECTED")
        self.assertTrue(moved["counts_as_evidence"])

    def test_no_status_is_unverified(self):
        self.assertEqual(mde.classify_source()["status"], "UNVERIFIED")


class LedgerTests(unittest.TestCase):
    def test_records_append_and_keep_history(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "retrievals.jsonl"
            first = mde.record_retrieval("https://a.example", status_code=403, path=path)
            second = mde.record_retrieval("https://a.example", status_code=200,
                                          body_bytes=10, path=path)
            self.assertTrue(first["recorded"])
            self.assertTrue(second["recorded"])
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([r["status"] for r in rows], ["BLOCKED", "FETCHED_OK"])
            self.assertEqual(mde.latest_retrievals(path)["https://a.example"]["status"],
                             "FETCHED_OK")

    def test_non_http_urls_are_refused(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "retrievals.jsonl"
            out = mde.record_retrieval("javascript:alert(1)", status_code=200, path=path)
            self.assertFalse(out["recorded"])
            self.assertFalse(path.exists())


class IntegrityTests(unittest.TestCase):
    def test_a_url_with_no_record_is_unverified(self):
        got = mde.evidence_integrity(["https://authority.example/obligation"], {})
        self.assertFalse(got["ok"])
        self.assertEqual(got["urls"][0]["status"], "UNVERIFIED")

    def test_blocked_url_fails_the_whole_claim(self):
        retrievals = _ok_retrievals()
        retrievals["https://authority.example/obligation"].update(
            {"status": "BLOCKED", "counts_as_evidence": False})
        got = mde.evidence_integrity(list(retrievals), retrievals)
        self.assertFalse(got["ok"])
        self.assertTrue(any("BLOCKED/DEAD" in p for p in got["problems"]))

    def test_one_served_url_is_not_enough(self):
        retrievals = {"https://authority.example/obligation": _ok_retrievals()[
            "https://authority.example/obligation"]}
        got = mde.evidence_integrity(["https://authority.example/obligation"], retrievals)
        self.assertFalse(got["ok"])
        self.assertTrue(any("2 required" in p for p in got["problems"]))


class IntakeGateTests(unittest.TestCase):
    def test_complete_candidate_is_only_qualified_for_scoring(self):
        got = mde.evaluate_intake(_candidate(), _ok_retrievals())
        self.assertEqual(got["verdict"], "QUALIFIED_FOR_SCORING")
        self.assertEqual(got["failed_gates"], [])
        self.assertTrue(got["score_consulted"] is False)
        # Passing intake is not acceptance: no other verdict exists here.
        self.assertNotIn(got["verdict"], ("ACCEPTED", "APPROVED"))

    def test_materially_duplicated_by_free_alternative_is_rejected(self):
        cand = _candidate(free_alternative={
            "urls": ["https://vendor.example/free-template"],
            "materially_duplicates": True,
            "demonstrated_advantage": "none found"})
        got = mde.evaluate_intake(cand, _ok_retrievals())
        self.assertEqual(got["verdict"], "REJECTED")
        self.assertIn("G3", got["failed_gates"])
        self.assertTrue(got["scoring_skipped"])

    def test_unknown_advantage_is_not_an_advantage(self):
        cand = _candidate(free_alternative={
            "urls": ["https://vendor.example/free-template"],
            "materially_duplicates": False,
            "demonstrated_advantage": "UNKNOWN"})
        got = mde.evaluate_intake(cand, _ok_retrievals())
        self.assertEqual(got["verdict"], "REJECTED")
        self.assertIn("G3", got["failed_gates"])

    def test_not_asking_the_free_alternative_question_fails(self):
        # The Cycle 107 omission, made an explicit failure.
        got = mde.evaluate_intake(_candidate(free_alternative={}), _ok_retrievals())
        self.assertEqual(got["verdict"], "REJECTED")
        self.assertIn("G3", got["failed_gates"])

    def test_single_source_type_fails_g2(self):
        cand = _candidate(cited_urls=[
            {"url": "https://authority.example/obligation", "source_type": "official"},
            {"url": "https://vendor.example/free-template", "source_type": "official"},
        ])
        got = mde.evaluate_intake(cand, _ok_retrievals())
        self.assertIn("G2", got["failed_gates"])

    def test_missing_differentiator_fails_g4(self):
        got = mde.evaluate_intake(
            _candidate(paid_comparison={"competitors": ["Paid Kit $99"], "differentiator": ""}),
            _ok_retrievals())
        self.assertIn("G4", got["failed_gates"])

    def test_unnamed_buyer_or_channel_fails_g5(self):
        got = mde.evaluate_intake(
            _candidate(buyer_channel={"buyer": "EU importers", "channel": ""}),
            _ok_retrievals())
        self.assertIn("G5", got["failed_gates"])

    def test_any_spend_fails_g6(self):
        got = mde.evaluate_intake(_candidate(build_cost_usd=1), _ok_retrievals())
        self.assertIn("G6", got["failed_gates"])

    def test_a_high_score_cannot_rescue_a_failed_gate(self):
        # The exact Cycle 107 shape: EUDR scored 19/25 and was still rejected.
        cand = _candidate(claimed_score=19, free_alternative={
            "urls": ["https://vendor.example/free-template"],
            "materially_duplicates": True,
            "demonstrated_advantage": "a worked example already published free"})
        got = mde.evaluate_intake(cand, _ok_retrievals())
        self.assertEqual(got["claimed_score"], 19)
        self.assertEqual(got["verdict"], "REJECTED")
        self.assertFalse(got["score_consulted"])

    def test_screen_intake_rolls_up_honestly(self):
        out = mde.screen_intake([
            _candidate(),
            _candidate(name="duplicate", free_alternative={
                "urls": ["https://vendor.example/free-template"],
                "materially_duplicates": True,
                "demonstrated_advantage": "none"}),
        ], _ok_retrievals())
        self.assertEqual(out["screened"], 2)
        self.assertEqual(out["qualified"], 1)
        self.assertEqual(out["rejected_at_intake"], 1)


class NoNetworkTests(unittest.TestCase):
    def test_module_imports_no_network_client(self):
        tree = ast.parse((ROOT / "market_discovery_engine.py").read_text(encoding="utf-8"))
        banned = {"urllib", "requests", "httpx", "socket", "aiohttp", "http.client"}
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertEqual(imported & banned, set())


if __name__ == "__main__":
    unittest.main()
