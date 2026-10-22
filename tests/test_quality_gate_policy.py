"""Tests for the policy-wide Quality Gate enforcement (QUALITY GATE —
POLICY-WIDE ENFORCEMENT directive, 2026-09-02).

Covers:
  * Gate-1 strict PASS interpretation (only clean all-pass = PASS; any
    REVIEW / FAIL / UNKNOWN / MISSING tool -> BLOCK).
  * Gate 2 founder sign-off ledger (only APPROVED = PASS; MISSING /
    REJECTED / NEEDS_FURTHER_WORK / REVOKED = BLOCK).
  * quality_gate_allowed() combinations (G1/G2/circuit-breaker).
  * distributor.py wiring: a product that fails the central gate is blocked
    on every arm, never reaches arm.publish(), and its gate result is
    recorded in the ledger BEFORE any real publish.

No test touches the real data/quality_gate_approvals.jsonl,
data/sales_ledger.jsonl, or data/circuit_breaker_state.json — every test
passes explicit temp paths or injects its gate inputs.

    python tests/test_quality_gate_policy.py
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import distributor
import quality_gate_policy as qgp
from channels import registry
from channels import ledger
from channels.base_arm import PublishResult
from schemas.product import Product
from quality_toolchain import runner as qtc_runner


def _temp_file(suffix=".jsonl"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


def _fake_product(source_id="PROD-qa-1"):
    return Product(
        title="t", subtitle="", description="d", price_usd=19.0, file_path="/fake/path.pdf",
        cover_path=None, tags=[], language="ar", source_id=source_id, raw_price_hint=19.0,
        needs_pricing=False, price_source="profit_raw",
    )


def _gate1_result(results, verdict="PASS", blocked=False):
    return {"results": results, "verdict": verdict, "blocked": blocked}


class TestGate1Strict(unittest.TestCase):
    def test_clean_all_pass_is_gate1_pass(self):
        rep = _gate1_result({
            "t1": {"status": "ok", "passed": True},
            "t2": {"status": "ok", "passed": True},
        })
        self.assertTrue(qgp._gate1_verdict(rep)["passed"])

    def test_any_failed_tool_is_review_block(self):
        rep = _gate1_result({
            "t1": {"status": "ok", "passed": True},
            "t2": {"status": "ok", "passed": False},  # honest REVIEW/FAIL
        })
        verdict = qgp._gate1_verdict(rep)
        self.assertFalse(verdict["passed"])
        self.assertEqual(verdict["code"], "FAIL")

    def test_unknown_tool_is_block(self):
        rep = _gate1_result({"t1": {"status": "unknown", "passed": False}})
        verdict = qgp._gate1_verdict(rep)
        self.assertFalse(verdict["passed"])
        self.assertEqual(verdict["code"], "UNKNOWN")

    def test_disabled_or_not_available_tool_is_block(self):
        for status in ("disabled", "not_available"):
            rep = _gate1_result({"t1": {"status": status, "passed": False}})
            self.assertFalse(qgp._gate1_verdict(rep)["passed"], status)

    def test_thin_no_result_at_all_is_missing_block(self):
        rep = _gate1_result({})
        verdict = qgp._gate1_verdict(rep)
        self.assertFalse(verdict["passed"])
        self.assertEqual(verdict["code"], "MISSING")

    def test_runner_review_verdict_never_passes(self):
        rep = _gate1_result(
            {"t1": {"status": "ok", "passed": True}}, verdict="REVIEW")
        self.assertFalse(qgp._gate1_verdict(rep)["passed"])


class TestGate2Ledger(unittest.TestCase):
    def setUp(self):
        self.ledger = _temp_file(".jsonl")

    def tearDown(self):
        if os.path.exists(self.ledger):
            os.remove(self.ledger)

    def test_missing_sign_off_is_not_passed(self):
        st = qgp.gate2_status("away-product", ledger_path=self.ledger)
        self.assertFalse(st["passed"])
        self.assertEqual(st["status"], "MISSING")

    def test_approved_is_the_only_pass(self):
        for decision, expected in (("APPROVED", True),
                                   ("REJECTED", False),
                                   ("NEEDS_FURTHER_WORK", False),
                                   ("REVOKED", False)):
            self.ledger = _temp_file(".jsonl")
            qgp.founder_sign_off("p", "founder", decision, ledger_path=Path(self.ledger))
            st = qgp.gate2_status("p", ledger_path=self.ledger)
            self.assertEqual(st["passed"], expected, decision)

    def test_newest_record_governs(self):
        qgp.founder_sign_off("p", "founder", "APPROVED", ledger_path=Path(self.ledger))
        qgp.founder_sign_off("p", "founder", "REVOKED", ledger_path=Path(self.ledger))
        st = qgp.gate2_status("p", ledger_path=self.ledger)
        self.assertFalse(st["passed"])
        self.assertEqual(st["decision"], "REVOKED")


class TestQualityGateAllowed(unittest.TestCase):
    def setUp(self):
        self.g2 = _temp_file(".jsonl")

    def tearDown(self):
        if os.path.exists(self.g2):
            os.remove(self.g2)

    def _pass_report(self):
        return _gate1_result({"t": {"status": "ok", "passed": True}})

    def test_both_gates_pass_is_allowed(self):
        # An APPROVED sign-off must be bound to the specific artifact version
        # being published (POLICY-WIDE ENFORCEMENT directive, 2026-09-02): a
        # version-less query is bound to "<no-artifact>" and a matching sign-off
        # must also carry that version.
        qgp.founder_sign_off("p", "founder", "APPROVED", artifact_version="<no-artifact>",
                             ledger_path=Path(self.g2))
        result = qgp.quality_gate_allowed(
            "p", gate1_report=self._pass_report(),
            gate2_ledger_path=Path(self.g2))
        self.assertTrue(result["allowed"])
        self.assertEqual(result["blocked_by"], None)

    def test_gate1_fail_blocks_even_with_founder_approval(self):
        qgp.founder_sign_off("p", "founder", "APPROVED", ledger_path=Path(self.g2))
        result = qgp.quality_gate_allowed(
            "p", gate1_report=_gate1_result({
                "t": {"status": "ok", "passed": False}}),
            gate2_ledger_path=Path(self.g2))
        self.assertFalse(result["allowed"])
        self.assertEqual(result["blocked_by"], "gate1")

    def test_gate2_missing_blocks_even_with_gate1_pass(self):
        result = qgp.quality_gate_allowed(
            "p", gate1_report=self._pass_report(),
            gate2_ledger_path=Path(self.g2))
        self.assertFalse(result["allowed"])
        self.assertEqual(result["blocked_by"], "gate2")
        self.assertEqual(result["gate2"]["status"], "MISSING")

    def test_any_block_state_short_circuits_to_block(self):
        # Gate 2 present-but-not-APPROVED must BLOCK, not pass.
        qgp.founder_sign_off("p", "founder", "NEEDS_FURTHER_WORK", ledger_path=Path(self.g2))
        result = qgp.quality_gate_allowed(
            "p", gate1_report=self._pass_report(),
            gate2_ledger_path=Path(self.g2))
        self.assertFalse(result["allowed"])


class TestGate2ArtifactAndVersionBinding(unittest.TestCase):
    """POLICY-WIDE ENFORCEMENT directive: Gate-2 sign-off must be tied to the
    specific product/artifact + version/revision. Missing, stale, invalid, or
    mismatched sign-off = BLOCK; a previous/unrelated review is never current
    authorization."""

    def setUp(self):
        self.g2 = _temp_file(".jsonl")
        for p in (self.g2,):
            if os.path.exists(p):
                os.remove(p)

    def tearDown(self):
        if os.path.exists(self.g2):
            os.remove(self.g2)

    def _pass_report(self):
        return _gate1_result({"t": {"status": "ok", "passed": True}})

    def _write(self, source_id="p", decision="APPROVED", version="v3", age_days=0):
        rec = {
            "source_id": source_id,
            "artifact_version": version,
            "reviewer": "founder",
            "decision": decision,
            "timestamp": (Path(__file__) and __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
                          - __import__("datetime").timedelta(days=age_days)).isoformat(),
        }
        with open(self.g2, "a", encoding="utf-8") as f:
            f.write(__import__("json").dumps(rec, ensure_ascii=False) + "\n")

    def test_correct_version_sign_off_is_recognized(self):
        self._write(source_id="p", decision="APPROVED", version="v3")
        result = qgp.quality_gate_allowed(
            "p", gate1_report=self._pass_report(),
            gate2_ledger_path=Path(self.g2), artifact_version="v3")
        self.assertTrue(result["allowed"])
        self.assertEqual(result["gate2"]["status"], "ok")

    def test_wrong_version_mismatch_blocks(self):
        self._write(source_id="p", decision="APPROVED", version="v2")
        result = qgp.quality_gate_allowed(
            "p", gate1_report=self._pass_report(),
            gate2_ledger_path=Path(self.g2), artifact_version="v3")
        self.assertFalse(result["allowed"])
        self.assertEqual(result["blocked_by"], "gate2")
        self.assertEqual(result["gate2"]["status"], "MISMATCH")

    def test_previous_review_is_not_current_authorization(self):
        # An APPROVED bound to an OLD version must not authorize the current one.
        self._write(source_id="p", decision="APPROVED", version="v1")
        self._write(source_id="p", decision="APPROVED", version="v2")
        result = qgp.quality_gate_allowed(
            "p", gate1_report=self._pass_report(),
            gate2_ledger_path=Path(self.g2), artifact_version="v3")
        self.assertFalse(result["allowed"])
        self.assertEqual(result["gate2"]["status"], "MISMATCH")

    def test_absent_revision_in_sign_off_is_unbound_and_blocks(self):
        # Version-less sign-off can never authorize a version-carrying publish.
        rec = {
            "source_id": "p", "reviewer": "founder", "decision": "APPROVED",
            "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        }
        with open(self.g2, "a", encoding="utf-8") as f:
            f.write(__import__("json").dumps(rec, ensure_ascii=False) + "\n")
        result = qgp.quality_gate_allowed(
            "p", gate1_report=self._pass_report(),
            gate2_ledger_path=Path(self.g2), artifact_version="v3")
        self.assertFalse(result["allowed"])
        self.assertEqual(result["gate2"]["status"], "MISMATCH")

    def test_stale_sign_off_blocks(self):
        # APPROVED but older than GATE2_MAX_AGE_DAYS -> STALE, not a pass.
        self._write(source_id="p", decision="APPROVED", version="v3",
                    age_days=qgp.GATE2_MAX_AGE_DAYS + 1)
        result = qgp.quality_gate_allowed(
            "p", gate1_report=self._pass_report(),
            gate2_ledger_path=Path(self.g2), artifact_version="v3")
        self.assertFalse(result["allowed"])
        self.assertEqual(result["gate2"]["status"], "STALE")

    def test_unparseable_timestamp_is_stale_and_blocks(self):
        rec = {
            "source_id": "p", "artifact_version": "v3", "reviewer": "founder",
            "decision": "APPROVED", "timestamp": "not-a-timestamp",
        }
        with open(self.g2, "a", encoding="utf-8") as f:
            f.write(__import__("json").dumps(rec, ensure_ascii=False) + "\n")
        result = qgp.quality_gate_allowed(
            "p", gate1_report=self._pass_report(),
            gate2_ledger_path=Path(self.g2), artifact_version="v3")
        self.assertFalse(result["allowed"])
        self.assertEqual(result["gate2"]["status"], "STALE")

    def test_missing_sign_off_still_blocks_with_version(self):
        result = qgp.quality_gate_allowed(
            "p", gate1_report=self._pass_report(),
            gate2_ledger_path=Path(self.g2), artifact_version="v9")
        self.assertFalse(result["allowed"])
        self.assertEqual(result["gate2"]["status"], "MISSING")


class TestDefaultArtifactVersion(unittest.TestCase):
    def test_no_artifact_yields_placeholder(self):
        self.assertEqual(qgp._default_artifact_version(None), "<no-artifact>")

    def test_missing_file_derives_from_basename(self):
        prod = _fake_product("PROD-x")
        prod.file_path = os.path.join(tempfile.gettempdir(), "nonexistent_pdf_xy.pdf")
        v = qgp._default_artifact_version(prod)
        self.assertTrue(v.startswith("nonexistent_pdf_xy.pdf::"))

    def test_real_file_version_changes_when_artifact_changes(self):
        import time as _time
        path = _temp_file(".pdf")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("A")
            v1 = qgp._default_artifact_version(type("P", (), {"file_path": path})())
            _time.sleep(0.05)
            with open(path, "w", encoding="utf-8") as f:
                f.write("BBBB")
            v2 = qgp._default_artifact_version(type("P", (), {"file_path": path})())
            self.assertNotEqual(v1, v2)
        finally:
            if os.path.exists(path):
                os.remove(path)


import os as _gf_os  # noqa: E402  (2026-10-22 live-path opt-in)
from unittest import mock as _gf_mock  # noqa: E402
_gf_patch = _gf_mock.patch


# 2026-10-22: exercises the mocked live distribution path; distributor.py
# and channels/write_gate.py fail closed by default, so it opts in explicitly.
@_gf_patch.dict(_gf_os.environ, {"FACTORY_LIVE_PUBLISH": "true"})
class TestDistributorQualityGateWiring(unittest.TestCase):
    def setUp(self):
        self._saved_arms = registry.all_arms()
        registry.clear()
        self.ledger_path = _temp_file(".jsonl")
        self.gate2_path = _temp_file(".jsonl")

    def tearDown(self):
        registry.clear()
        for a in self._saved_arms:
            registry.register(a)
        for p in (self.ledger_path, self.gate2_path):
            if os.path.exists(p):
                os.remove(p)

    def _register_fake_arm(self, name, publish_result):
        fake_arm = MagicMock()
        fake_arm.name = name
        fake_arm.supports.return_value = True
        fake_arm.publish.return_value = publish_result
        registry.register(fake_arm)
        return fake_arm

    def _gate_deny(self, product, arm_name=None, **kwargs):
        return {
            "allowed": False, "source_id": product.source_id,
            "gate1": {"passed": False, "code": "REVIEW"},
            "gate2": {"passed": False, "decision": None, "status": "MISSING"},
            "reason": "central Quality Gate NOT_PASSED (G1 REVIEW / G2 MISSING)",
        }

    def test_denied_product_never_reaches_any_arm_publish(self):
        fake_arm = self._register_fake_arm("gumroad", PublishResult(
            ok=True, platform="gumroad", product_id="p1", url="http://x", error=None, dry_run=False,
        ))
        outcomes = distributor.distribute(
            _fake_product(), dry_run=False, ledger_path=self.ledger_path,
            quality_gate=self._gate_deny,
            gate2_ledger_path=Path(self.gate2_path),
        )
        fake_arm.publish.assert_not_called()
        self.assertFalse(outcomes[0]["attempted"])
        self.assertIn("Quality Gate", outcomes[0]["skip_reason"])
        # failure from an unbound gate -> outcome.ok is None (blocked before publish)
        self.assertIsNone(outcomes[0]["ok"])

    def test_denied_product_gate_is_recorded_in_ledger_before_publish(self):
        self._register_fake_arm("gumroad", PublishResult(
            ok=True, platform="gumroad", product_id="p1", url="http://x", error=None, dry_run=False,
        ))
        distributor.distribute(
            _fake_product(), dry_run=False, ledger_path=self.ledger_path,
            quality_gate=self._gate_deny,
            gate2_ledger_path=Path(self.gate2_path),
        )
        events = list(ledger.read_events(event_type="publish_attempt", ledger_path=self.ledger_path))
        self.assertEqual(len(events), 1)
        self.assertFalse(events[0]["ok"])
        self.assertEqual(events[0]["protection_decision"], "quality_gate_blocked")
        qg = events[0].get("quality_gate")
        self.assertIsNotNone(qg)
        self.assertFalse(qg["allowed"])
        self.assertIn("Quality Gate", qg["reason"])

    def test_mandatory_default_gate_applies_block_to_unapproved_product(self):
        """The REAL (non-injected) resolver must run by default: a product
        with no founder sign-off is BLOCKED on real publish even though its
        code is callable — proving no production unit bypasses the gate."""
        fake_arm = self._register_fake_arm("gumroad", PublishResult(
            ok=True, platform="gumroad", product_id="p1", url="http://x", error=None, dry_run=False,
        ))
        evidence_path = _temp_file(".jsonl")
        try:
            outcomes = distributor.distribute(
                _fake_product(), dry_run=False, ledger_path=self.ledger_path,
                gate2_ledger_path=Path(self.gate2_path),
                quality_evidence_path=Path(evidence_path),
            )
        finally:
            if os.path.exists(evidence_path):
                os.remove(evidence_path)
        fake_arm.publish.assert_not_called()
        self.assertFalse(outcomes[0]["attempted"])
        self.assertIn("Quality Gate", outcomes[0]["skip_reason"])


class TestGate1RunnerContract(unittest.TestCase):
    """FULL INTEGRATION RECOVERY PLAN Phase 1 (2026-09-02): the repaired
    contract between quality_toolchain.runner.run_stack() and
    quality_gate_policy._gate1_verdict.

    run_stack now emits a top-level `verdict`/`blocked` (strict contract,
    quality_toolchain.runner.overall_verdict). These tests prove a legitimate
    Gate-1 PASS is reachable through the default resolver AND that every
    missing/invalid/non-PASS state remains fail-closed. No verdict is
    manufactured or hard-coded to make a test pass.

    python tests/test_quality_gate_policy.py
    """

    def setUp(self):
        self.g2 = _temp_file(".jsonl")
        self.ev = _temp_file(".jsonl")

    def tearDown(self):
        for p in (self.g2, self.ev):
            if os.path.exists(p):
                os.remove(p)

    # -- 1. A legitimate, valid Gate-1 result produces PASS -------------------
    def test_legitimate_clean_pass_is_reachable(self):
        # A report structurally identical to a clean run_stack output (its
        # strict overall_verdict agrees with _gate1_verdict; see the runner
        # contract test in test_quality_toolchain.py).
        clean = {
            "results": {
                "t1": {"status": "ok", "passed": True, "lcs_unavailable": False},
                "t2": {"status": "ok", "passed": True},
            },
            "verdict": "PASS",
            "blocked": False,
        }
        self.assertEqual(qgp._gate1_verdict(clean)["code"], "PASS")
        # Through the default resolver decision path, a matching Gate-2
        # APPROVED makes the full publish gate allowed.
        qgp.founder_sign_off("p", "founder", "APPROVED",
                             artifact_version="<no-artifact>", ledger_path=Path(self.g2))
        result = qgp.quality_gate_allowed(
            "p", gate1_report=clean, gate2_ledger_path=Path(self.g2))
        self.assertTrue(result["allowed"])
        self.assertIsNone(result["blocked_by"])

    def test_runner_emits_verdict_contract_keys(self):
        # The actual runner always emits the contract keys (not advisory-only).
        rep = qtc_runner.run_stack(
            "arabic_book", {"product_type": "arabic_book"},
            product_name="probe", record_evidence=False,
        )
        self.assertIn("verdict", rep)
        self.assertIn("blocked", rep)
        self.assertIsInstance(rep["verdict"], str)
        self.assertIsInstance(rep["blocked"], bool)
        # blocked is True exactly when verdict != PASS.
        self.assertEqual(rep["blocked"], rep["verdict"] != "PASS")

    # -- run_stack strict overall_verdict: PASS only on clean all-pass --------
    def test_runner_strict_verdict_is_pass_only_for_clean_all_pass(self):
        from quality_toolchain import runner as r
        pass_rep = {"results": {"a": {"status": "ok", "passed": True},
                                "b": {"status": "ok", "passed": True}}}
        self.assertEqual(r.overall_verdict(pass_rep),
                         {"verdict": "PASS", "blocked": False})

    def test_runner_strict_verdict_blocks_on_any_fail(self):
        from quality_toolchain import runner as r
        for results in (
            {"a": {"status": "ok", "passed": False}},
            {"a": {"status": "error", "passed": False}},
            {"a": {"status": "ok", "passed": True},
             "b": {"status": "ok", "passed": False}},
            {"a": {"status": "ok", "passed": True},
             "b": {"status": "ok", "passed": True, "lcs_unavailable": True}},
            {"a": {"status": "not_available", "passed": False}},
            {"a": {"status": "disabled", "passed": False}},
        ):
            self.assertEqual(r.overall_verdict({"results": results}),
                             {"verdict": "REVIEW", "blocked": True}, results)

    def test_runner_strict_verdict_missing_on_empty_results(self):
        from quality_toolchain import runner as r
        self.assertEqual(r.overall_verdict({"results": {}}),
                         {"verdict": "MISSING", "blocked": True})

    # -- 2. Missing verdict -> BLOCK ------------------------------------------
    def test_missing_verdict_key_is_block(self):
        for rep in ({}, {"results": {"t": {"status": "ok", "passed": True}}}):
            self.assertFalse(qgp._gate1_verdict(rep)["passed"])

    # -- 3. REVIEW -> BLOCK ---------------------------------------------------
    def test_review_verdict_is_block(self):
        rep = _gate1_result({"t": {"status": "ok", "passed": True}},
                            verdict="REVIEW")
        v = qgp._gate1_verdict(rep)
        self.assertFalse(v["passed"])
        self.assertEqual(v["code"], "REVIEW")

    # -- 4. FAIL -> BLOCK -----------------------------------------------------
    def test_fail_verdict_is_block(self):
        rep = _gate1_result({"t": {"status": "ok", "passed": False}})
        v = qgp._gate1_verdict(rep)
        self.assertFalse(v["passed"])
        self.assertEqual(v["code"], "FAIL")

    # -- 5. UNKNOWN -> BLOCK --------------------------------------------------
    def test_unknown_verdict_is_block(self):
        rep = _gate1_result({"t": {"status": "unknown", "passed": False}})
        v = qgp._gate1_verdict(rep)
        self.assertFalse(v["passed"])
        self.assertEqual(v["code"], "UNKNOWN")

    # -- 6. Malformed verdict -> BLOCK ----------------------------------------
    def test_malformed_verdict_is_block(self):
        # A non-string or non-exact-"PASS" verdict is not a valid explicit PASS.
        for verdict in ("pass", "Pass", "PASS ", "yes", 1, None, ("PASS",)):
            rep = _gate1_result({"t": {"status": "ok", "passed": True}}, verdict=verdict)
            self.assertFalse(qgp._gate1_verdict(rep)["passed"], repr(verdict))

    def test_malformed_tool_result_is_block(self):
        # A per-tool result lacking status/passed can never be a PASS.
        rep = _gate1_result({"t": {"passed": True}})  # status missing
        self.assertFalse(qgp._gate1_verdict(rep)["passed"])

    # -- 7. Insufficient evidence -> BLOCK ------------------------------------
    def test_insufficient_evidence_missing_results_is_block(self):
        v = qgp._gate1_verdict(_gate1_result({}))
        self.assertFalse(v["passed"])
        self.assertEqual(v["code"], "MISSING")

    def test_insufficient_evidence_partial_or_unavailable_is_block(self):
        for results in (
            {"t": {"status": "ok", "passed": True},
             "u": {"status": "not_available", "passed": False}},
            {"t": {"status": "ok", "passed": True},
             "u": {"status": "disabled", "passed": False}},
        ):
            self.assertFalse(qgp._gate1_verdict(
                _gate1_result(results, verdict="REVIEW", blocked=True))["passed"])

    # -- 8. Existing publish protection remains effective ---------------------
    def test_publish_protection_still_blocks_emergency_stop(self):
        import channels.publish_protection as pp
        prot = _temp_file(".jsonl")
        cb = _temp_file(".jsonl")
        try:
            pp.trigger_emergency_stop("founder order", triggered_by="founder",
                                      state_path=prot)
            res = pp.check_publish_allowed(
                "gumroad", state_path=prot,
                circuit_breaker_state_path=cb,
            )
            self.assertFalse(res["allowed"])
            self.assertIn("global publish emergency stop", res["reason"])
        finally:
            for p in (prot, cb):
                if os.path.exists(p):
                    os.remove(p)

    # -- 9. CircuitBreakerState remains effective -----------------------------
    def test_isolated_circuit_breaker_blocks_gate_despite_pass(self):
        import circuit_breaker as cb_mod
        from circuit_breaker import CircuitBreakerState
        cb_path = _temp_file(".jsonl")
        try:
            cb = CircuitBreakerState(state_path=cb_path)
            for _ in range(3):
                cb.record_failure("marketplace_publishing", "f")
            # Gate-1 PASS + Gate-2 APPROVED still blocked by ISOLATED breaker.
            qgp.founder_sign_off("p", "founder", "APPROVED",
                                 artifact_version="<no-artifact>",
                                 ledger_path=Path(self.g2))
            result = qgp.quality_gate_allowed(
                "p", gate1_report=_gate1_result(
                    {"t": {"status": "ok", "passed": True}}),
                gate2_ledger_path=Path(self.g2),
                circuit_breaker_state_path=Path(cb_path),
            )
            self.assertFalse(result["allowed"])
            self.assertEqual(result["blocked_by"], "circuit_breaker")
            self.assertEqual(result["circuit_breaker"]["state"],
                             cb_mod.ISOLATED)
        finally:
            if os.path.exists(cb_path):
                os.remove(cb_path)


if __name__ == "__main__":
    unittest.main()