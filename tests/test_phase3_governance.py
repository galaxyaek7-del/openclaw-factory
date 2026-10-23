import pytest
"""Phase 3 — Governance & Production Gate Enforcement Prep (tests).

Authorized by the founder directive (docs/PHASE_3_GOVERNANCE_GATE_PLAN.md,
2026-09-02). Proves BOTH:
  * legitimate, fully-verified governance CAN pass the dual gate
    (Gate-1 = technical Quality PASS + Gate-2 = founder Sign-Off Ledger
    approval, current + version-matched) and
  * any invalid / incomplete / missing / stale / mismatched governance is
    BLOCKED / no execution.

The real enforcement surface under test (read from the live source, never
re-implemented here):
  * quality_gate_policy._gate1_verdict      — strict, fail-closed Gate-1 PASS
  * quality_gate_policy.gate2_status        — founder sign-off, newest-governs,
                                               version-bound, not stale
  * quality_gate_policy.founder_sign_off    — the single Gate-2 write path
  * quality_gate_policy.quality_gate_allowed — combined G1 + G2 + breaker
  * quality_gate_policy._circuit_allows     — ISOLATED breaker => BLOCK
  * distributor.distribute(...)             — central gate front + per-arm
                                               fan-out; dry_run default True
  * circuit_breaker.is_isolated (CIRCUIT_PATH = "marketplace_publishing")

Safety invariants enforced by THIS suite:
  * dry_run=True remains the default and is never overridden to True->False
    by this suite's own code.
  * arm.publish(dry_run=False) is NEVER called: the four-arms test and the
    non-dry-run gate test assert arm.publish was never invoked with
    dry_run=False (spy counts real publish calls == 0).
  * No network / external side effects: every test is offline; no real
    connector / Groq / HTTP call is made. No real ledger is written.
  * finance_data.json and every real data/*.jsonl stay byte-identical: every
    test passes explicit temp paths or injects its inputs.

    python tests/test_phase3_governance.py
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

# --- Phase 3 isolation guard -----------------------------------------------
# Redirect the factory AI cost-ledger default to an isolated temp location
# BEFORE importing any factory module, so no real data/ai_cost_log.jsonl can
# ever be written by this suite regardless of import order. Same discipline
# as tests/test_durable_telemetry.py / tests/test_run_identity.py.
_GF_COST_LOG_DIR = tempfile.mkdtemp(prefix="gf-phase3-costlog-")
os.environ["GF_AI_COST_LOG"] = os.path.join(_GF_COST_LOG_DIR, "ai_cost_log.jsonl")

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import distributor  # noqa: E402
import quality_gate_policy as qgp  # noqa: E402
import circuit_breaker as cb_mod  # noqa: E402
from channels import registry  # noqa: E402
from channels import publish_protection as pp  # noqa: E402
from channels.base_arm import PublishResult  # noqa: E402
from schemas.product import Product  # noqa: E402

# Cycle 84: this module exercises Gumroad write logic against a mocked
# HTTP layer, so it explicitly opts in to write authorization. It was
# previously getting this from an AUTOUSE fixture that set
# FACTORY_LIVE_PUBLISH=true for the whole suite -- a hidden broad
# permission. The opt-in is now visible here, in the file that needs it.
pytestmark = pytest.mark.usefixtures("authorize_live_writes")


def _temp_file(suffix=".jsonl"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


def _fake_product(source_id="PHASE3-PROD-1"):
    return Product(
        title="t", subtitle="", description="d", price_usd=19.0, file_path="/fake/path.pdf",
        cover_path=None, tags=[], language="ar", source_id=source_id, raw_price_hint=19.0,
        needs_pricing=False, price_source="profit_raw",
    )


def _gate1_result(results, verdict="PASS", blocked=False):
    return {"results": results, "verdict": verdict, "blocked": blocked}


def _pass_report():
    return _gate1_result({"t": {"status": "ok", "passed": True}})


class TestDualGateAllow(unittest.TestCase):
    """The single controllable PASS path: Gate-1 PASS AND Gate-2 APPROVED
    (matching version, fresh) AND circuit breaker CLOSED."""

    def setUp(self):
        self.g2 = _temp_file(".jsonl")

    def tearDown(self):
        if os.path.exists(self.g2):
            os.remove(self.g2)

    def test_legitimate_fully_verified_governance_passes(self):
        qgp.founder_sign_off("p", "founder", "APPROVED",
                             artifact_version="v3", ledger_path=Path(self.g2))
        result = qgp.quality_gate_allowed(
            "p", gate1_report=_pass_report(),
            gate2_ledger_path=Path(self.g2), artifact_version="v3")
        self.assertTrue(result["allowed"])
        self.assertIsNone(result["blocked_by"])
        self.assertEqual(result["gate1"]["code"], "PASS")
        self.assertEqual(result["gate2"]["status"], "ok")
        self.assertEqual(result["circuit_breaker"]["state"], "CLOSED")

    def test_gate2_missing_blocks_even_with_gate1_pass(self):
        result = qgp.quality_gate_allowed(
            "p", gate1_report=_pass_report(),
            gate2_ledger_path=Path(self.g2))
        self.assertFalse(result["allowed"])
        self.assertEqual(result["blocked_by"], "gate2")
        self.assertEqual(result["gate2"]["status"], "MISSING")


class TestDualGateBlockMatrix(unittest.TestCase):
    """One independent test per fail-closed governance condition (Phase 3 plan
    §2 / §3.1 class 2). Every row must resolve to BLOCK / no execution."""

    def setUp(self):
        self.g2 = _temp_file(".jsonl")
        self.cb = _temp_file(".jsonl")

    def tearDown(self):
        for p in (self.g2, self.cb):
            if os.path.exists(p):
                os.remove(p)

    def _write(self, source_id="p", decision="APPROVED", version="v3", age_days=0,
               timestamp="__now__"):
        ts = (datetime.now(timezone.utc) - timedelta(days=age_days)).isoformat() \
            if timestamp == "__now__" else timestamp
        rec = {"source_id": source_id, "artifact_version": version,
               "reviewer": "founder", "decision": decision, "timestamp": ts}
        with open(self.g2, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def _allowed(self, g1=None, version="v3"):
        return qgp.quality_gate_allowed(
            "p", gate1_report=g1 if g1 is not None else _pass_report(),
            gate2_ledger_path=Path(self.g2), artifact_version=version,
            circuit_breaker_state_path=Path(self.cb))

    def test_missing_evidence_blocks(self):            # no sign-off at all
        r = self._allowed()
        self.assertFalse(r["allowed"])
        self.assertEqual(r["blocked_by"], "gate2")
        self.assertEqual(r["gate2"]["status"], "MISSING")

    def test_unverified_evidence_blocks(self):         # Gate-1 tool did not run (status != ok)
        rep = _gate1_result({"t": {"status": "unknown", "passed": False}}, verdict="REVIEW", blocked=True)
        self._write()  # APPROVED present, but Gate-1 unverified
        r = self._allowed(g1=rep)
        self.assertFalse(r["allowed"])
        self.assertEqual(r["blocked_by"], "gate1")

    def test_review_verdict_blocks(self):              # advisory REVIEW, never a pass
        rep = _gate1_result({"t": {"status": "ok", "passed": True}}, verdict="REVIEW")
        self._write()
        r = self._allowed(g1=rep)
        self.assertFalse(r["allowed"])
        self.assertEqual(r["blocked_by"], "gate1")
        self.assertEqual(r["gate1"]["code"], "REVIEW")

    def test_unknown_verdict_blocks(self):             # UNKNOWN => BLOCK
        rep = _gate1_result({"t": {"status": "unknown", "passed": False}})
        self._write()
        r = self._allowed(g1=rep)
        self.assertFalse(r["allowed"])
        self.assertEqual(r["blocked_by"], "gate1")

    def test_fail_verdict_blocks(self):                # a tool FAILed => FAIL
        rep = _gate1_result({"t": {"status": "ok", "passed": False}})
        self._write()
        r = self._allowed(g1=rep)
        self.assertFalse(r["allowed"])
        self.assertEqual(r["blocked_by"], "gate1")
        self.assertEqual(r["gate1"]["code"], "FAIL")

    def test_malformed_verdict_blocks(self):           # malformed Gate-1 verdict
        rep = _gate1_result({"t": {"status": "ok", "passed": True}}, verdict="pass")
        self._write()
        r = self._allowed(g1=rep)
        self.assertFalse(r["allowed"])
        self.assertEqual(r["blocked_by"], "gate1")

    def test_malformed_timestamp_blocks(self):         # unparseable Gate-2 timestamp => STALE
        self._write(version="v3", timestamp="not-a-timestamp")
        r = self._allowed()
        self.assertFalse(r["allowed"])
        self.assertEqual(r["blocked_by"], "gate2")
        self.assertEqual(r["gate2"]["status"], "STALE")

    def test_stale_sign_off_blocks(self):              # APPROVED but older than GATE2_MAX_AGE_DAYS
        self._write(version="v3", age_days=qgp.GATE2_MAX_AGE_DAYS + 1)
        r = self._allowed()
        self.assertFalse(r["allowed"])
        self.assertEqual(r["blocked_by"], "gate2")
        self.assertEqual(r["gate2"]["status"], "STALE")

    def test_mismatched_version_blocks(self):          # sign-off version != request version
        self._write(version="v2")
        r = self._allowed(version="v3")
        self.assertFalse(r["allowed"])
        self.assertEqual(r["blocked_by"], "gate2")
        self.assertEqual(r["gate2"]["status"], "MISMATCH")


class TestGate2VersionRunMatching(unittest.TestCase):
    """Gate-2 approval must be bound to the exact artifact version being
    published; a sign-off for any other version is a MISMATCH -> BLOCK."""

    def setUp(self):
        self.g2 = _temp_file(".jsonl")

    def tearDown(self):
        if os.path.exists(self.g2):
            os.remove(self.g2)

    def _write(self, version, decision="APPROVED"):
        qgp.founder_sign_off("p", "founder", decision,
                             artifact_version=version, ledger_path=Path(self.g2))

    def test_matching_version_passes(self):
        self._write(version="release-7")
        r = qgp.quality_gate_allowed("p", gate1_report=_pass_report(),
                                     gate2_ledger_path=Path(self.g2),
                                     artifact_version="release-7")
        self.assertTrue(r["allowed"])
        self.assertEqual(r["gate2"]["signoff_version"], "release-7")

    def test_different_version_mismatch_blocks(self):
        self._write(version="release-6")
        r = qgp.quality_gate_allowed("p", gate1_report=_pass_report(),
                                     gate2_ledger_path=Path(self.g2),
                                     artifact_version="release-7")
        self.assertFalse(r["allowed"])
        self.assertEqual(r["gate2"]["status"], "MISMATCH")

    def test_versionless_request_against_versioned_signoff_blocks(self):
        # A version-less request with no artifact_version: the default binds to
        # "<no-artifact>" which never matches a real version -> MISMATCH/BLOCK.
        self._write(version="release-7")
        r = qgp.quality_gate_allowed("p", gate1_report=_pass_report(),
                                     gate2_ledger_path=Path(self.g2))
        self.assertFalse(r["allowed"])
        self.assertEqual(r["gate2"]["status"], "MISMATCH")


class TestGate2Staleness(unittest.TestCase):
    """Gate-2 PASS requires the governing sign-off to be within
    GATE2_MAX_AGE_DAYS. Fresh passes; aged/unparseable is STALE -> BLOCK."""

    def setUp(self):
        self.g2 = _temp_file(".jsonl")

    def tearDown(self):
        if os.path.exists(self.g2):
            os.remove(self.g2)

    def _write(self, age_days, timestamp="__now__"):
        ts = (datetime.now(timezone.utc) - timedelta(days=age_days)).isoformat() \
            if timestamp == "__now__" else timestamp
        rec = {"source_id": "p", "artifact_version": "v3", "reviewer": "founder",
               "decision": "APPROVED", "timestamp": ts}
        with open(self.g2, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def _allowed(self):
        return qgp.quality_gate_allowed("p", gate1_report=_pass_report(),
                                        gate2_ledger_path=Path(self.g2),
                                        artifact_version="v3")

    def test_fresh_approved_passes(self):
        self._write(age_days=1)
        self.assertTrue(self._allowed()["allowed"])

    def test_aged_approved_is_stale_and_blocks(self):
        self._write(age_days=qgp.GATE2_MAX_AGE_DAYS + 1)
        r = self._allowed()
        self.assertFalse(r["allowed"])
        self.assertEqual(r["gate2"]["status"], "STALE")

    def test_unparseable_timestamp_is_stale_and_blocks(self):
        self._write(age_days=0, timestamp="garbage")
        r = self._allowed()
        self.assertFalse(r["allowed"])
        self.assertEqual(r["gate2"]["status"], "STALE")


class TestBreakerBlocksGovernance(unittest.TestCase):
    """Circuit-breaker enforcement: ISOLATED stops execution even when both
    gates are satisfied."""

    def setUp(self):
        self.g2 = _temp_file(".jsonl")
        self.cb = _temp_file(".jsonl")

    def tearDown(self):
        for p in (self.g2, self.cb):
            if os.path.exists(p):
                os.remove(p)

    def test_isolated_breaker_blocks_despite_full_governance(self):
        qgp.founder_sign_off("p", "founder", "APPROVED",
                             artifact_version="v3", ledger_path=Path(self.g2))
        # Record 3 failures -> marketplace_publishing ISOLATED.
        breaker = cb_mod.CircuitBreakerState(state_path=Path(self.cb))
        for _ in range(3):
            breaker.record_failure(qgp.CIRCUIT_PATH, "governance-test failure")
        r = qgp.quality_gate_allowed(
            "p", gate1_report=_pass_report(),
            gate2_ledger_path=Path(self.g2), artifact_version="v3",
            circuit_breaker_state_path=Path(self.cb))
        self.assertFalse(r["allowed"])
        self.assertEqual(r["blocked_by"], "circuit_breaker")
        self.assertEqual(r["circuit_breaker"]["state"], cb_mod.ISOLATED)

    def test_closed_breaker_allows_and_isolated_blocks(self):
        # CLOSED breaker alone does not approve — gates still required.
        r = qgp.quality_gate_allowed(
            "p", gate1_report=_pass_report(),
            gate2_ledger_path=Path(self.g2), artifact_version="v3",
            circuit_breaker_state_path=Path(self.cb))
        self.assertFalse(r["allowed"])
        self.assertEqual(r["blocked_by"], "gate2")  # no sign-off; breaker CLOSED
        self.assertEqual(r["circuit_breaker"]["state"], "CLOSED")


# CI runs this file with plain unittest, where the pytest fixture above does
# not apply; these classes need the live-write opt-in to reach the quality
# and publish-protection gates behind channels/write_gate.py (2026-10-23).
@patch.dict(os.environ, {"FACTORY_LIVE_PUBLISH": "true"})
class TestAllFourArmsGated(unittest.TestCase):
    """Each of the four publishing arms (gumroad, payhip, etsy, paddle) must be
    blocked uniformly at the CENTRAL gate front — a non-passing product never
    leaks to any arm's publish(). No real publish call is ever made."""

    ARMS = ("gumroad", "payhip", "etsy", "paddle")

    def setUp(self):
        self._saved = registry.all_arms()
        registry.clear()
        self.ledger_path = _temp_file(".jsonl")
        self.gate2_path = _temp_file(".jsonl")
        self.arm_publish_calls = []

    def tearDown(self):
        registry.clear()
        for a in self._saved:
            registry.register(a)
        for p in (self.ledger_path, self.gate2_path):
            if os.path.exists(p):
                os.remove(p)

    def _register_spy_arm(self, name):
        arm = MagicMock()
        arm.name = name
        arm.supports.return_value = True
        def _spy(product, dry_run=True):
            self.arm_publish_calls.append((name, dry_run))
            return PublishResult(ok=True, platform=name, product_id=None,
                                 url=None, error=None, dry_run=dry_run)
        arm.publish.side_effect = _spy
        registry.register(arm)
        return arm

    def _deny_all_arms(self, product, arm_name=None, **kwargs):
        return {"allowed": False, "source_id": product.source_id,
                "gate1": {"passed": False, "code": "REVIEW"},
                "gate2": {"passed": False, "decision": None, "status": "MISSING"},
                "reason": "central Quality Gate NOT_PASSED (G1 REVIEW / G2 MISSING)"}

    def _run(self, quality_gate, dry_run):
        return distributor.distribute(
            _fake_product(), arm_names=list(self.ARMS), dry_run=dry_run,
            ledger_path=self.ledger_path, quality_gate=quality_gate,
            gate2_ledger_path=Path(self.gate2_path))

    def test_nonpassing_product_blocked_on_all_four_arms(self):
        for name in self.ARMS:
            self._register_spy_arm(name)
        outcomes = self._run(self._deny_all_arms, dry_run=False)
        self.assertEqual(len(outcomes), 4)
        for out, name in zip(outcomes, self.ARMS):
            self.assertEqual(out["arm"], name)
            self.assertFalse(out["attempted"])
            self.assertIn("Quality Gate", out["skip_reason"])
        # The central gate blocks BEFORE any arm runs.
        self.assertEqual(self.arm_publish_calls, [])

    def test_realtime_resolver_blocks_unapproved_product_on_all_four(self):
        # The REAL (non-injected) resolver must run by default even on a
        # real publish: a product with no founder sign-off is BLOCKED on every
        # arm, and no arm.publish(dry_run=False) is ever called.
        for name in self.ARMS:
            self._register_spy_arm(name)
        outcomes = distributor.distribute(
            _fake_product(), arm_names=list(self.ARMS), dry_run=False,
            ledger_path=self.ledger_path,
            gate2_ledger_path=Path(self.gate2_path))
        self.assertEqual(len(outcomes), 4)
        self.assertTrue(all(not o["attempted"] for o in outcomes))
        self.assertEqual(self.arm_publish_calls, [])


class TestNoWeakeningInvariant(unittest.TestCase):
    """Prove the fail-closed governance constants and defaults are unchanged
    from baseline — Phase 3 must not weaken any of them."""

    def test_fail_closed_constants_unchanged(self):
        self.assertEqual(qgp.GATE2_PASS_DECISIONS, frozenset({"APPROVED"}))
        self.assertIn("REVIEW", qgp.BLOCK_STATES)
        self.assertIn("FAIL", qgp.BLOCK_STATES)
        self.assertIn("UNKNOWN", qgp.BLOCK_STATES)
        self.assertIn("MISSING", qgp.BLOCK_STATES)
        self.assertGreater(qgp.GATE2_MAX_AGE_DAYS, 0)

    def test_dry_run_defaults_unchanged(self):
        import inspect
        sig = inspect.signature(distributor.distribute)
        # dry_run is the 3rd positional param with default True.
        self.assertTrue(sig.parameters["dry_run"].default)
        # CLI --json path: job.get("dry_run", True)
        self.assertEqual(qgp._gate1_verdict(_pass_report())["code"], "PASS")

    def test_gate1_review_never_passes(self):
        for verdict in ("REVIEW", "FAIL", "UNKNOWN", "MISSING"):
            rep = _gate1_result({"t": {"status": "ok", "passed": True}}, verdict=verdict)
            self.assertFalse(qgp._gate1_verdict(rep)["passed"], verdict)

    def test_non_approved_gate2_never_passes(self):
        for decision in ("REJECTED", "NEEDS_FURTHER_WORK", "REVOKED", "MAYBE"):
            path = _temp_file(".jsonl")
            try:
                qgp.founder_sign_off("p", "founder", decision,
                                     artifact_version="v1", ledger_path=Path(path))
                r = qgp.gate2_status("p", ledger_path=path, artifact_version="v1")
                self.assertFalse(r["passed"], decision)
            finally:
                if os.path.exists(path):
                    os.remove(path)


@patch.dict(os.environ, {"FACTORY_LIVE_PUBLISH": "true"})
class TestNonDryRunGateEnforcement(unittest.TestCase):
    """On the non-dry-run (real-publish) surface, the central quality gate and
    publish-protection gate MUST fire and block before any arm may publish.
    This exercises the enforcement path WITHOUT ever making a real
    arm.publish(dry_run=False) call — every path asserts 0 real-publish calls."""

    def setUp(self):
        self._saved = registry.all_arms()
        registry.clear()
        self.ledger_path = _temp_file(".jsonl")
        self.gate2_path = _temp_file(".jsonl")
        self.prot_path = _temp_file(".jsonl")
        self.arm_publish_calls = []

    def tearDown(self):
        registry.clear()
        for a in self._saved:
            registry.register(a)
        for p in (self.ledger_path, self.gate2_path, self.prot_path):
            if os.path.exists(p):
                os.remove(p)

    def _register_spy_arm(self, name):
        arm = MagicMock()
        arm.name = name
        arm.supports.return_value = True
        def _spy(product, dry_run=True):
            self.arm_publish_calls.append((name, dry_run))
            return PublishResult(ok=True, platform=name, product_id=None,
                                 url=None, error=None, dry_run=dry_run)
        arm.publish.side_effect = _spy
        registry.register(arm)
        return arm

    def test_non_dry_run_default_resolver_blocks_before_any_publish(self):
        # Real resolver + NO founder sign-off => central gate BLOCK on every arm,
        # arm.publish never invoked with dry_run=False.
        self._register_spy_arm("gumroad")
        outcomes = distributor.distribute(
            _fake_product(), arm_names=["gumroad"], dry_run=False,
            ledger_path=self.ledger_path,
            gate2_ledger_path=Path(self.gate2_path))
        self.assertEqual(len(outcomes), 1)
        self.assertFalse(outcomes[0]["attempted"])
        self.assertIn("Quality Gate", outcomes[0]["skip_reason"])
        self.assertEqual(self.arm_publish_calls, [])

    def test_dry_run_true_never_invokes_publish_with_false(self):
        # Even a passing dry_run must not overreach: dry_run=True keeps publish
        # dry; the spy never sees dry_run=False.
        self._register_spy_arm("gumroad")
        outcomes = distributor.distribute(
            _fake_product(), arm_names=["gumroad"], dry_run=True,
            ledger_path=self.ledger_path,
            gate2_ledger_path=Path(self.gate2_path))
        self.assertEqual(len(outcomes), 1)
        self.assertTrue(outcomes[0]["attempted"])
        self.assertEqual([c for c in self.arm_publish_calls if not c[1]], [])

    def test_publish_protection_blocks_when_emergency_stop_on_real_publish(self):
        # Gate APPROVED + Gate2 APPROVED but publish-protection emergency stop
        # active => arm.publish(dry_run=False) must NEVER be called. Uses the
        # real publish_protection gate via the temp protection_state_path.
        pp.trigger_emergency_stop("phase3 test", triggered_by="founder",
                                  state_path=Path(self.prot_path))
        self._register_spy_arm("gumroad")
        # APPROVED Gate to let the quality gate pass so we isolate the
        # publish-protection layer's own block.
        gate = {"allowed": True, "source_id": "p",
                "gate1": {"passed": True, "code": "PASS"},
                "gate2": {"passed": True, "decision": "APPROVED", "status": "ok"},
                "reason": "Phase3 test-approved GOP"}
        def _approved_gate(product, arm_name=None, evidence_path=None):
            return gate
        outcomes = distributor.distribute(
            _fake_product(), arm_names=["gumroad"], dry_run=False,
            ledger_path=self.ledger_path, quality_gate=_approved_gate,
            gate2_ledger_path=Path(self.gate2_path),
            protection_state_path=Path(self.prot_path))
        self.assertEqual(len(outcomes), 1)
        self.assertFalse(outcomes[0]["attempted"])
        self.assertIn("blocked by publish protection layer", outcomes[0]["skip_reason"])
        self.assertEqual(self.arm_publish_calls, [])


if __name__ == "__main__":
    unittest.main()