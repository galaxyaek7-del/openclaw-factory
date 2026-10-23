# -*- coding: utf-8 -*-
"""Cycle 118 -- tests for the first-sale task orchestrator.

All local. Injected callables replace any network page. These tests prove the
orchestrator's *behavior* (dependency handling, bounded retry, reconciliation,
next-action selection), NOT that any real Gumroad operation succeeded.
"""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from unittest import mock
from datetime import datetime, timezone
from pathlib import Path

FACTORY_DIR = Path(__file__).resolve().parent.parent
MOD_PATH = FACTORY_DIR / "scripts" / "first_sale_orchestrator.py"


def _load():
    spec = importlib.util.spec_from_file_location("first_sale_orchestrator", MOD_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["first_sale_orchestrator"] = mod
    spec.loader.exec_module(mod)
    return mod


od = _load()

import sys as _gf_sys  # noqa: E402
_gf_sys.path.insert(0, str(Path(__file__).resolve().parent))
from paid_artifacts import paid_files_absent, require_paid_files  # noqa: E402

# Paid product files are not in the public repository (2026-10-23). The
# graph and persistence tests exercise orchestration, not the files: on CI
# only the package_validate task is replaced by a stub that reports what the
# real task reports on the factory machine. Tests of the files skip instead.
_PAID = sorted({f for prof in od._load_gdo().PROFILES.values() for f in prof.get("files", [])})
if paid_files_absent(*_PAID):
    od.DEFAULT_REGISTRY["package_validate"] = lambda ctx: {"ready": True, "failed": [], "workbook": {"ci_stand_in": True}}

_MISSING_EVIDENCE = Path(tempfile.gettempdir()) / "c118_no_default_draft_evidence.json"


def setUpModule():
    # Keep every test hermetic: a real draft-evidence file must never make an
    # offline test behave as if a live create already happened.
    _MISSING_EVIDENCE.unlink(missing_ok=True)
    os.environ["FIRST_SALE_DRAFT_EVIDENCE_PATH"] = str(_MISSING_EVIDENCE)


def tearDownModule():
    os.environ.pop("FIRST_SALE_DRAFT_EVIDENCE_PATH", None)


def cust_state(taskdefs):
    st = od.default_state()
    st["tasks"] = {t["id"]: t for t in taskdefs}
    st["events"] = []
    return st


class TestCapabilityAndPrice(unittest.TestCase):
    def test_draft_capability_state_is_remote_unverified(self):
        missing = Path(tempfile.gettempdir()) / "c118_no_evidence_here.json"
        missing.unlink(missing_ok=True)
        cap = od.draft_capability_state(missing)
        self.assertEqual(cap["state"], od.CAP_IMPLEMENTED_BUT_REMOTE_BEHAVIOR_UNVERIFIED)
        self.assertEqual(cap["authorization"], od.CAP_BLOCKED_BY_AUTHORIZATION)
        self.assertTrue(cap["documented"])
        self.assertTrue(cap["implemented"])
        self.assertFalse(cap["remote_verified"])

    def test_price_authority_reads_authoritative_manifest(self):
        pa = od.price_authority()
        self.assertTrue(pa["authorized"], pa.get("reason"))
        self.assertEqual(pa["price_usd"], 14.99)
        self.assertEqual(pa["basis"], "FOUNDER_DECISION_BELOW_COMPARABLE")
        self.assertGreaterEqual(len(pa["sources"]), 2)

    def test_price_authority_rejects_unknown_basis(self):
        import json, tempfile
        tmp = Path(tempfile.gettempdir()) / "c118_bad_manifest.json"
        tmp.write_text(json.dumps({"products": [{"id": "B12-001", "price_usd": 14.99,
                                                 "price_basis": "MADE_UP"}]}), encoding="utf-8")
        try:
            pa = od.price_authority(manifest_path=tmp)
            self.assertFalse(pa["authorized"])
        finally:
            tmp.unlink(missing_ok=True)


class TestDefaultGraphOffline(unittest.TestCase):
    def test_runs_independent_tasks_and_blocks_the_rest(self):
        st = od.default_state()
        spy = {"create": 0}
        st = od.run(st, ctx={"create_draft_fn": lambda c: spy.__setitem__("create", spy["create"] + 1)},
                    persist=False)
        t = st["tasks"]
        for tid in ("package_validate", "price_authority", "catalog_duplicate_check",
                    "draft_capability", "sales_ledger_check", "journey_check"):
            self.assertEqual(t[tid]["status"], od.COMPLETED, tid)
        self.assertEqual(t["create_draft"]["status"], od.BLOCKED)
        self.assertEqual(t["create_draft"]["blocker"], od.BLOCKER_EXTERNAL_CAPABILITY)
        self.assertEqual(spy["create"], 0, "external create must never be called")
        for tid in ("verify_remote_draft", "resolve_utm", "publish"):
            self.assertEqual(t[tid]["status"], od.PENDING, tid)
            self.assertEqual(t[tid]["blocker"], od.BLOCKER_DEPENDENCY, tid)
        self.assertEqual(st["next_action"]["kind"], "BLOCKED")
        self.assertIn("create_draft", st["next_action"]["blocked_by"])

    def test_no_network_readers_default_to_unknown(self):
        st = od.run(od.default_state(), persist=False)
        self.assertEqual(st["tasks"]["catalog_duplicate_check"]["result"]["duplicate"], "UNKNOWN")
        self.assertEqual(st["tasks"]["sales_ledger_check"]["result"]["verdict"], "UNKNOWN")


class TestAutonomyScenario(unittest.TestCase):
    """Phase 9 -- the factory must keep moving when one task is blocked."""

    def _scenario(self):
        done = od._task("t_done", "already done", od.WORK_AUTONOMOUS)
        done["status"] = od.COMPLETED
        ext = od._task("t_external", "external capability", od.WORK_EXTERNAL_CAPABILITY,
                       external=True, max_attempts=1)
        ind1 = od._task("t_ind1", "independent 1", od.WORK_AUTONOMOUS)
        ind2 = od._task("t_ind2", "independent 2", od.WORK_AUTONOMOUS)
        founder = od._task("t_founder", "needs founder", od.WORK_FOUNDER_AUTHORITY)
        flaky = od._task("t_flaky", "transient", od.WORK_AUTONOMOUS, max_attempts=2)
        state = cust_state([done, ext, ind1, ind2, founder, flaky])

        called = {"done": 0}

        def done_fn(ctx):
            called["done"] += 1
            raise AssertionError("completed task must not re-run")

        def ext_fn(ctx):
            raise od.CapabilityError("no supported external route")

        def ind_fn(ctx):
            return {"ok": True}

        def founder_fn(ctx):
            raise od.FounderAuthorityError("needs 'APPROVE ...'")

        def flaky_fn(ctx):
            raise od.TransientError("temporary network blip")

        registry = {
            "t_done": done_fn, "t_external": ext_fn, "t_ind1": ind_fn,
            "t_ind2": ind_fn, "t_founder": founder_fn, "t_flaky": flaky_fn,
        }
        return state, registry, called

    def test_scenario(self):
        state, registry, called = self._scenario()
        state = od.run(state, registry, persist=False)
        t = state["tasks"]

        # 1. no unauthorized actions; completed work not re-run
        self.assertEqual(called["done"], 0)
        self.assertEqual(t["t_done"]["status"], od.COMPLETED)
        # 2. independent tasks continued
        self.assertEqual(t["t_ind1"]["status"], od.COMPLETED)
        self.assertEqual(t["t_ind2"]["status"], od.COMPLETED)
        # 3. transient failure retried under a bounded policy, then blocked
        self.assertEqual(t["t_flaky"]["attempts"], 2)
        self.assertEqual(t["t_flaky"]["status"], od.BLOCKED)
        self.assertEqual(t["t_flaky"]["blocker"], od.BLOCKER_TRANSIENT_EXHAUSTED)
        # 5. genuine blockers recorded, distinctly
        self.assertEqual(t["t_external"]["blocker"], od.BLOCKER_EXTERNAL_CAPABILITY)
        self.assertEqual(t["t_founder"]["blocker"], od.BLOCKER_FOUNDER_AUTHORITY)
        # 7. a useful next-action state
        self.assertEqual(state["next_action"]["kind"], "BLOCKED")
        self.assertIn("t_external", state["next_action"]["blocked_by"])

    def test_no_infinite_retry(self):
        state, registry, _ = self._scenario()
        # a single run must terminate (max_steps bound) and exhaust the retry
        state = od.run(state, registry, persist=False, max_steps=200)
        self.assertEqual(state["tasks"]["t_flaky"]["attempts"], 2)


class TestUncertainOutcomeReconciliation(unittest.TestCase):
    def _state(self):
        ext = od._task("t_ext", "create", od.WORK_EXTERNAL_CAPABILITY, external=True, max_attempts=1)
        return cust_state([ext])

    def test_uncertain_outcome_blocks_duplicate_and_is_not_retried(self):
        calls = {"n": 0}

        def fn(ctx):
            calls["n"] += 1
            raise od.UncertainOutcomeError("timeout after the request was sent")

        registry = {"t_ext": fn}
        state = self._state()
        state = od.run(state, registry, persist=False)
        self.assertEqual(state["tasks"]["t_ext"]["status"], od.NEEDS_RECONCILIATION)
        self.assertEqual(calls["n"], 1)
        # a second run must NOT re-issue the create
        state = od.run(state, registry, persist=False)
        self.assertEqual(calls["n"], 1, "must not blindly retry an uncertain external action")

    def test_reconcile_then_completed_never_recalled(self):
        calls = {"n": 0}

        def fn(ctx):
            calls["n"] += 1
            raise od.UncertainOutcomeError("lost response")

        registry = {"t_ext": fn}
        state = od.run(self._state(), registry, persist=False)
        od.reconcile(state, "t_ext", "COMPLETED", note="read-back confirmed it landed")
        self.assertEqual(state["tasks"]["t_ext"]["status"], od.COMPLETED)
        state = od.run(state, registry, persist=False)
        self.assertEqual(calls["n"], 1)

    def test_reconcile_requires_reconciliation_state(self):
        state = self._state()
        with self.assertRaises(od.TaskError):
            od.reconcile(state, "t_ext", "COMPLETED")


class TestResumeAfterInterruption(unittest.TestCase):
    def test_interrupted_internal_retries_external_needs_reconciliation(self):
        internal = od._task("t_internal", "internal", od.WORK_AUTONOMOUS)
        internal["status"] = od.RUNNING
        internal["run_id"] = "old-run"
        ext = od._task("t_external", "ext", od.WORK_EXTERNAL_CAPABILITY, external=True, max_attempts=1)
        ext["status"] = od.RUNNING
        ext["run_id"] = "old-run"
        state = cust_state([internal, ext])
        registry = {"t_internal": lambda ctx: {"ok": True}}
        state = od.run(state, registry, persist=False, run_id="new-run")
        self.assertEqual(state["tasks"]["t_internal"]["status"], od.COMPLETED)
        self.assertEqual(state["tasks"]["t_external"]["status"], od.NEEDS_RECONCILIATION)


class TestNextActionSelection(unittest.TestCase):
    def test_execute_then_blocked(self):
        a = od._task("a", "a", od.WORK_AUTONOMOUS)
        b = od._task("b", "b", od.WORK_EXTERNAL_CAPABILITY, depends=["a"], external=True, max_attempts=1)
        state = cust_state([a, b])
        self.assertEqual(od.next_action(state)["kind"], "EXECUTE")
        self.assertEqual(od.next_action(state)["action"], "a")

    def test_transient_retry_takes_priority(self):
        a = od._task("a", "a", od.WORK_AUTONOMOUS)
        a["status"] = od.FAILED_RETRYABLE
        state = cust_state([a])
        na = od.next_action(state)
        self.assertEqual(na["kind"], "RETRY")
        self.assertEqual(na["action"], "a")


class TestPublishAuthorityAudit(unittest.TestCase):
    def test_read_only_audit_flags_parallel_paths(self):
        out = od.publish_authority_audit()
        by_file = {f["file"]: f for f in out["findings"]}
        # affiliate/publish_queue.py is parallel-owned and untracked, so it is
        # absent from any clean checkout (CI). When present it must be flagged;
        # when absent the audit must say so honestly, never invent a finding.
        queue = by_file["affiliate/publish_queue.py"]
        if (od.FACTORY_DIR / "affiliate" / "publish_queue.py").is_file():
            self.assertTrue(queue["creates_then_publishes"])
        else:
            self.assertEqual(queue, {"file": "affiliate/publish_queue.py", "present": False})
        self.assertTrue(by_file["src/publish/auto_publisher.py"]["checks_live_flag"])


class TestStatePersistence(unittest.TestCase):
    def test_save_and_load_roundtrip(self):
        import tempfile
        tmp = Path(tempfile.gettempdir()) / "c118_state.json"
        tmp.unlink(missing_ok=True)
        try:
            st = od.run(od.default_state(), persist=False)
            od.save_state(st, path=tmp)
            loaded = od.load_state(path=tmp)
            self.assertIn("create_draft", loaded["tasks"])
            self.assertEqual(loaded["tasks"]["create_draft"]["status"], od.BLOCKED)
        finally:
            tmp.unlink(missing_ok=True)

    def test_corrupt_state_falls_back_to_default(self):
        import tempfile
        tmp = Path(tempfile.gettempdir()) / "c118_corrupt.json"
        tmp.write_text("{not json", encoding="utf-8")
        try:
            loaded = od.load_state(path=tmp)
            self.assertEqual(sorted(loaded["tasks"]), sorted(od.default_state()["tasks"]))
        finally:
            tmp.unlink(missing_ok=True)


class TestWorkbookValidation(unittest.TestCase):
    def test_canonical_workbook_structure(self):
        require_paid_files(*_PAID)
        wb = od.workbook_validate()
        self.assertTrue(wb["structural_ok"], wb.get("reason"))
        self.assertEqual(wb["sha256"],
                         "aee8fc0b100345e7abc6e8a41487ddf551b5b7f235c6f4324827d1c6ab8a092d")
        self.assertEqual(wb["sheets"], ["Inputs", "ClientMix", "RaisePlanner", "README"])
        self.assertEqual(wb["formula_cells"], 10)
        # openpyxl cannot calculate; the file stores no cached results.
        self.assertEqual(wb["cached_verification"], "UNVERIFIED_NO_CACHED_VALUES")
        self.assertTrue(all(v is None for v in wb["cached_values"].values()))

    def test_missing_workbook_fails_closed(self):
        wb = od.workbook_validate(workbook=Path("does-not-exist.xlsx"))
        self.assertFalse(wb["structural_ok"])


class TestUtmResolution(unittest.TestCase):
    BASE = "https://galaxyforge.gumroad.com/l/b12-001"

    def test_build_map_resolves_every_placeholder(self):
        out = od.build_utm_map(self.BASE)
        self.assertGreaterEqual(len(out["utm_links"]), 5)
        self.assertEqual(out["unresolved"], [])
        for link in out["utm_links"].values():
            self.assertNotIn("[base_url]", link["url"])
            self.assertTrue(link["url"].startswith(self.BASE))
        self.assertEqual(out["utm_links"]["affiliate"]["url"].count("utm_campaign=B12-001"), 1)

    def test_placeholder_or_empty_base_rejected(self):
        for bad in ("", None, "[base_url]", "not-a-url"):
            with self.assertRaises(od.PermanentError):
                od.build_utm_map(bad)

    def test_resolve_writes_new_file_and_leaves_source_untouched(self):
        import hashlib, tempfile
        src = od.UTM_TEMPLATE_PATH
        before = hashlib.sha256(src.read_bytes()).hexdigest()
        dst = Path(tempfile.gettempdir()) / "c118_utm_resolved.json"
        dst.unlink(missing_ok=True)
        try:
            res = od.resolve_utm_links(self.BASE, out_path=dst)
            self.assertTrue(dst.is_file())
            self.assertGreaterEqual(res["resolved"], 5)
            self.assertEqual(hashlib.sha256(src.read_bytes()).hexdigest(), before,
                             "source template must never be rewritten")
        finally:
            dst.unlink(missing_ok=True)


class TestCreateDefenseInDepth(unittest.TestCase):
    def test_explicit_authorization_required_even_when_capable(self):
        orig = od.draft_capability_state
        orig_ev = od.read_draft_evidence
        od.read_draft_evidence = lambda path=None: {}
        od.draft_capability_state = lambda: {
            "state": od.CAP_SUPPORTED_AND_IMPLEMENTED, "reason": "test"}
        try:
            with self.assertRaises(od.AuthorizationError):
                od._task_create_draft({"create_draft_fn": lambda c: {"created": True}})
            res = od._task_create_draft({
                "create_draft_fn": lambda c: {"created": True}, "draft_authorized": True})
            self.assertEqual(res, {"created": True})
        finally:
            od.draft_capability_state = orig
            od.read_draft_evidence = orig_ev

    def test_first_live_verification_needs_all_three_switches(self):
        orig_ev = od.read_draft_evidence
        orig_authz = od._write_authorized
        od.read_draft_evidence = lambda path=None: {}
        caps = {"state": od.CAP_IMPLEMENTED_BUT_REMOTE_BEHAVIOR_UNVERIFIED,
                "reason": "unverified"}
        orig_cap = od.draft_capability_state
        od.draft_capability_state = lambda: caps
        try:
            fn = {"create_draft_fn": lambda c: {"created": True}}
            with self.assertRaises(od.CapabilityError):
                od._task_create_draft(dict(fn, draft_authorized=True))
            od._write_authorized = lambda op="create_product": False
            with self.assertRaises(od.CapabilityError):
                od._task_create_draft(dict(fn, draft_authorized=True,
                                           first_live_verification=True))
            od._write_authorized = lambda op="create_product": True
            res = od._task_create_draft(dict(fn, draft_authorized=True,
                                             first_live_verification=True))
            self.assertEqual(res, {"created": True})
        finally:
            od.draft_capability_state = orig_cap
            od.read_draft_evidence = orig_ev
            od._write_authorized = orig_authz


class TestRecheckOnNewRun(unittest.TestCase):
    def test_capability_and_authorization_blocks_are_reopened(self):
        st = od.default_state()
        od._set(st, st["tasks"]["create_draft"], od.BLOCKED,
                od.BLOCKER_EXTERNAL_CAPABILITY, "x")
        od._set(st, st["tasks"]["publish"], od.BLOCKED,
                od.BLOCKER_AUTHORIZATION, "x")
        changed = od.reset_recheckable(st)
        self.assertIn("create_draft", changed)
        self.assertIn("publish", changed)
        self.assertEqual(st["tasks"]["create_draft"]["status"], od.PENDING)

    def test_founder_authority_and_permanent_blocks_are_not_reopened(self):
        st = od.default_state()
        od._set(st, st["tasks"]["publish"], od.BLOCKED,
                od.BLOCKER_FOUNDER_AUTHORITY, "x")
        od._set(st, st["tasks"]["package_validate"], od.BLOCKED,
                od.BLOCKER_PERMANENT, "x")
        changed = od.reset_recheckable(st)
        self.assertEqual(changed, [])
        self.assertEqual(st["tasks"]["publish"]["status"], od.BLOCKED)


class TestFounderAuthorityReset(unittest.TestCase):
    """A founder-authority block may be re-opened ONLY by the arrival of the
    exact authorization the task demanded -- never by a routine recheck, and
    never in a way that lets the task act without that authorization."""

    PHRASE = "APPROVE X PUBLISH"

    def _blocked_publish(self, requirement=True):
        t = od._task("publish", "publish", od.WORK_FOUNDER_AUTHORITY)
        t["status"] = od.BLOCKED
        t["blocker"] = od.BLOCKER_FOUNDER_AUTHORITY
        t["last_error"] = "requires phrase"
        t["last_error_kind"] = "BLOCKED"
        if requirement:
            t["authority_requirement"] = {
                "ctx_key": "publish_authorization", "required": self.PHRASE}
        return cust_state([t])

    def test_reopens_only_with_the_exact_required_authorization(self):
        st = self._blocked_publish()
        # wrong / missing authorization: never reopened
        self.assertEqual(od.reset_founder_authority(st, {"publish_authorization": "nope"}), [])
        self.assertEqual(od.reset_founder_authority(st, {}), [])
        self.assertEqual(st["tasks"]["publish"]["status"], od.BLOCKED)
        self.assertEqual(st["tasks"]["publish"]["blocker"], od.BLOCKER_FOUNDER_AUTHORITY)
        # the exact authorization: reopened to PENDING
        changed = od.reset_founder_authority(st, {"publish_authorization": self.PHRASE})
        self.assertEqual(changed, ["publish"])
        self.assertEqual(st["tasks"]["publish"]["status"], od.PENDING)

    def test_block_without_a_recorded_requirement_is_never_reopened(self):
        # A bare/legacy founder block (or a founder error raised without
        # ctx_key/required) must never be cleared by a recheck.
        st = self._blocked_publish(requirement=False)
        self.assertEqual(od.reset_founder_authority(st, {"publish_authorization": self.PHRASE}), [])
        self.assertEqual(st["tasks"]["publish"]["status"], od.BLOCKED)

    def test_other_blocker_kinds_are_untouched(self):
        st = od.default_state()
        od._set(st, st["tasks"]["package_validate"], od.BLOCKED, od.BLOCKER_PERMANENT, "x")
        od._set(st, st["tasks"]["create_draft"], od.BLOCKED, od.BLOCKER_EXTERNAL_CAPABILITY, "x")
        od._set(st, st["tasks"]["sales_ledger_check"], od.BLOCKED, od.BLOCKER_AUTHORIZATION, "x")
        changed = od.reset_founder_authority(st, {"publish_authorization": self.PHRASE})
        self.assertEqual(changed, [])
        self.assertEqual(st["tasks"]["package_validate"]["status"], od.BLOCKED)
        self.assertEqual(st["tasks"]["create_draft"]["status"], od.BLOCKED)
        self.assertEqual(st["tasks"]["sales_ledger_check"]["status"], od.BLOCKED)

    def test_run_records_the_requirement_and_reopens_when_supplied(self):
        calls = {"n": 0}

        def fn(ctx):
            calls["n"] += 1
            if ctx.get("publish_authorization") != self.PHRASE:
                raise od.FounderAuthorityError(
                    f"requires '{self.PHRASE}'",
                    ctx_key="publish_authorization", required=self.PHRASE)
            return {"published": True}

        t = od._task("t_founder", "needs founder", od.WORK_FOUNDER_AUTHORITY)
        state = cust_state([t])
        registry = {"t_founder": fn}

        # run 1: no authorization -> blocked, and the requirement is recorded
        state = od.run(state, registry, ctx={}, persist=False)
        self.assertEqual(state["tasks"]["t_founder"]["status"], od.BLOCKED)
        self.assertEqual(state["tasks"]["t_founder"]["blocker"], od.BLOCKER_FOUNDER_AUTHORITY)
        self.assertEqual(state["tasks"]["t_founder"]["authority_requirement"],
                         {"ctx_key": "publish_authorization", "required": self.PHRASE})

        # run 2: a different value must NOT reopen it
        state = od.run(state, registry, ctx={"publish_authorization": "wrong"}, persist=False)
        self.assertEqual(state["tasks"]["t_founder"]["status"], od.BLOCKED)

        # run 3: the exact authorization reopens it, and it completes
        state = od.run(state, registry, ctx={"publish_authorization": self.PHRASE}, persist=False)
        self.assertEqual(state["tasks"]["t_founder"]["status"], od.COMPLETED)
        self.assertIsNone(state["tasks"]["t_founder"]["authority_requirement"])

    def test_reopening_publish_never_bypasses_the_publish_gate(self):
        # Even with the exact phrase, the real publish task refuses to act
        # without a real publish implementation injected.
        t0 = od._task("publish", "publish", od.WORK_FOUNDER_AUTHORITY)
        t0["status"] = od.BLOCKED
        t0["blocker"] = od.BLOCKER_FOUNDER_AUTHORITY
        t0["authority_requirement"] = {
            "ctx_key": "publish_authorization", "required": od.PUBLISH_PHRASE}
        st = cust_state([t0])
        st = od.run(st, {"publish": od._task_publish},
                    ctx={"publish_authorization": od.PUBLISH_PHRASE}, persist=False)
        t = st["tasks"]["publish"]
        self.assertEqual(t["status"], od.BLOCKED)
        self.assertNotIn(t["status"], (od.COMPLETED, od.EXTERNALLY_VERIFIED))
        self.assertNotEqual(t.get("result"), {"published": True})
        self.assertEqual(t["blocker"], od.BLOCKER_EXTERNAL_CAPABILITY)


class TestDraftEvidenceAndLivePath(unittest.TestCase):
    """Evidence is what permanently unlocks the normal live path."""
    def _product(self, published=False, price=1499):
        return {"id": "prod_1", "name": "B12-001 Freelancer Rate Raise Calculator",
                "price": price, "published": published,
                "short_url": "https://example.invalid/p/prod_1"}

    def test_evidence_roundtrip_and_atomic_write(self):
        tmp = Path(tempfile.gettempdir()) / "c118_draft_evidence.json"
        tmp.unlink(missing_ok=True)
        try:
            ev = od.record_draft_evidence(self._product(), path=tmp)
            self.assertEqual(ev["product_id"], "prod_1")
            self.assertEqual(ev["price_cents"], 1499)
            self.assertIs(ev["published"], False)
            loaded = od.read_draft_evidence(tmp)
            self.assertEqual(loaded["product_id"], "prod_1")
        finally:
            tmp.unlink(missing_ok=True)

    def test_evidence_rejects_published_or_wrong_price(self):
        tmp = Path(tempfile.gettempdir()) / "c118_draft_evidence_bad.json"
        try:
            od.record_draft_evidence(self._product(published=True), path=tmp)
            self.assertEqual(od.read_draft_evidence(tmp), {})
            od.record_draft_evidence(self._product(price=2900), path=tmp)
            self.assertEqual(od.read_draft_evidence(tmp), {})
        finally:
            tmp.unlink(missing_ok=True)

    def test_evidence_blocks_recreation(self):
        tmp = Path(tempfile.gettempdir()) / "c118_draft_evidence_idem.json"
        tmp.unlink(missing_ok=True)
        orig = od.read_draft_evidence
        od.read_draft_evidence = lambda path=None: json.loads(tmp.read_text(encoding="utf-8"))
        try:
            od.record_draft_evidence(self._product(), path=tmp)
            called = {"n": 0}
            res = od._task_create_draft(
                {"create_draft_fn": lambda c: called.__setitem__("n", called["n"] + 1),
                 "draft_authorized": True})
            self.assertTrue(res["already_exists"])
            self.assertEqual(called["n"], 0, "must never re-create an existing draft")
        finally:
            od.read_draft_evidence = orig
            tmp.unlink(missing_ok=True)

    def test_capability_unlocks_only_with_evidence(self):
        tmp = Path(tempfile.gettempdir()) / "c118_draft_evidence_cap.json"
        tmp.unlink(missing_ok=True)
        try:
            real = od.draft_capability_state(tmp)
            self.assertEqual(real["state"], od.CAP_IMPLEMENTED_BUT_REMOTE_BEHAVIOR_UNVERIFIED)
            od.record_draft_evidence(self._product(), path=tmp)
            unlocked = od.draft_capability_state(tmp)
            self.assertTrue(unlocked["remote_verified"])
            self.assertIn(unlocked["state"],
                          (od.CAP_BLOCKED_BY_AUTHORIZATION, od.CAP_SUPPORTED_AND_IMPLEMENTED))
        finally:
            tmp.unlink(missing_ok=True)

    def test_real_create_fn_refuses_ambiguous_authorization(self):
        with self.assertRaises(od.PermanentError):
            od._real_create_draft_fn({"dry_run": True})

    def test_resolve_utm_falls_back_to_recorded_evidence(self):
        orig = od.read_draft_evidence
        od.read_draft_evidence = lambda path=None: {"url": "https://ex.invalid/l/x"}
        seen = {}
        try:
            res = od._task_resolve_utm(
                {"utm_fn": lambda base: seen.setdefault("base", base) and {"resolved": 5}})
            self.assertEqual(seen["base"], "https://ex.invalid/l/x")
            self.assertEqual(res, {"resolved": 5})
        finally:
            od.read_draft_evidence = orig

    def test_publish_requires_exact_phrase(self):
        with self.assertRaises(od.FounderAuthorityError):
            od._task_publish({"publish_authorization": "approve b12-001 publish"})
        with self.assertRaises(od.FounderAuthorityError):
            od._task_publish({})
        with self.assertRaises(od.CapabilityError):
            od._task_publish({"publish_authorization": od.PUBLISH_PHRASE})


class TestApplyListingCopy(unittest.TestCase):
    """The listing copy write: gated, verified by read-back, never publishes."""

    def setUp(self):
        import channels.gumroad_publisher as gp
        import channels.write_scope as ws
        self.gp = gp
        self.ws = ws
        self._orig = (od.read_draft_evidence, od.live_flag_enabled, od._write_authorized)
        od.read_draft_evidence = lambda path=None: {"product_id": "pid"}

    def tearDown(self):
        od.read_draft_evidence, od.live_flag_enabled, od._write_authorized = self._orig

    def _allow_gate(self):
        od.live_flag_enabled = lambda: True
        od._write_authorized = lambda op: True

    def test_prepared_description_clears_the_300_word_gate(self):
        desc = od._prepared_description()
        self.assertGreaterEqual(len(desc.split()), 300)
        self.assertEqual(len(od.LISTING_TAGS), 8)

    def test_dry_run_never_touches_the_network_or_the_gate(self):
        od.live_flag_enabled = lambda: False
        od._write_authorized = lambda op: False
        res = od.apply_listing_copy()  # dry_run default
        self.assertFalse(res["applied"])
        self.assertEqual(res["reason"], "dry_run")

    def test_real_apply_requires_the_write_gate(self):
        od.live_flag_enabled = lambda: False
        od._write_authorized = lambda op: False
        with self.assertRaises(od.AuthorizationError):
            od.apply_listing_copy(dry_run=True if False else False, evidence_path="x")

    def test_silent_noop_is_reported_not_swallowed(self):
        self._allow_gate()
        desc = od._prepared_description()
        with mock.patch.object(self.ws, "issue_scope",
                               return_value=mock.Mock(scope_id="s")), \
                mock.patch.object(self.gp, "load_token", return_value="tok"), \
                mock.patch.object(self.gp, "update_product_description_scoped"), \
                mock.patch.object(self.gp, "update_product"), \
                mock.patch.object(self.gp, "get_product",
                                  return_value={"id": "pid", "published": False,
                                                "price": 1499,
                                                "description": "short unchanged",
                                                "tags": []}):
            with self.assertRaises(od.UncertainOutcomeError):
                od.apply_listing_copy(dry_run=False, evidence_path="unused.json")
        self.assertTrue(desc)

    def test_never_publishes(self):
        self._allow_gate()
        desc = od._prepared_description()
        with mock.patch.object(self.ws, "issue_scope",
                               return_value=mock.Mock(scope_id="s")), \
                mock.patch.object(self.gp, "load_token", return_value="tok"), \
                mock.patch.object(self.gp, "update_product_description_scoped"), \
                mock.patch.object(self.gp, "update_product"), \
                mock.patch.object(self.gp, "get_product",
                                  return_value={"id": "pid", "published": True,
                                                "price": 1499, "description": desc,
                                                "tags": list(od.LISTING_TAGS)}):
            with self.assertRaises(od.UncertainOutcomeError):
                od.apply_listing_copy(dry_run=False, evidence_path="unused.json")

    def test_library_verification_failed_is_not_a_write_failure(self):
        """Gumroad returned the same tags in a different order on 2026-10-18;
        update_product()'s order-sensitive comparison called that a failure.
        The independent read-back must decide, not the library's verdict."""
        self._allow_gate()
        desc = od._prepared_description()
        with mock.patch.object(self.ws, "issue_scope",
                               return_value=mock.Mock(scope_id="s")), \
                mock.patch.object(self.gp, "load_token", return_value="tok"), \
                mock.patch.object(self.gp, "update_product_description_scoped"), \
                mock.patch.object(self.gp, "update_product",
                                  side_effect=RuntimeError("VERIFICATION_FAILED: tags reordered")), \
                mock.patch.object(self.gp, "get_product",
                                  return_value={"id": "pid", "published": False,
                                                "price": 1499, "description": desc,
                                                "tags": list(reversed(od.LISTING_TAGS))}):
            res = od.apply_listing_copy(dry_run=False, evidence_path="unused.json")
        self.assertTrue(res["applied"])
        self.assertFalse(res["published"])
        self.assertIn("tags", res["library_unproven"])

    def test_library_verification_unknown_fails_closed(self):
        """A library read-back it could not complete leaves the final state
        unestablished -- the orchestrator must not guess success."""
        self._allow_gate()
        with mock.patch.object(self.ws, "issue_scope",
                               return_value=mock.Mock(scope_id="s")), \
                mock.patch.object(self.gp, "load_token", return_value="tok"), \
                mock.patch.object(self.gp, "update_product_description_scoped",
                                  side_effect=RuntimeError("VERIFICATION_UNKNOWN: re-read failed")), \
                mock.patch.object(self.gp, "update_product"):
            with self.assertRaises(od.UncertainOutcomeError):
                od.apply_listing_copy(dry_run=False, evidence_path="unused.json")

    def test_a_real_write_failure_still_raises(self):
        self._allow_gate()
        with mock.patch.object(self.ws, "issue_scope",
                               return_value=mock.Mock(scope_id="s")), \
                mock.patch.object(self.gp, "load_token", return_value="tok"), \
                mock.patch.object(self.gp, "update_product_description_scoped",
                                  side_effect=RuntimeError("Gumroad update_product failed: nope")), \
                mock.patch.object(self.gp, "update_product"):
            with self.assertRaises(RuntimeError):
                od.apply_listing_copy(dry_run=False, evidence_path="unused.json")

    def test_success_writes_evidence(self):
        self._allow_gate()
        desc = od._prepared_description()
        with tempfile.TemporaryDirectory() as d:
            target = os.path.join(d, "listing_evidence.json")
            with mock.patch.object(self.ws, "issue_scope",
                                   return_value=mock.Mock(scope_id="s")), \
                    mock.patch.object(self.gp, "load_token", return_value="tok"), \
                    mock.patch.object(self.gp, "update_product_description_scoped"), \
                    mock.patch.object(self.gp, "update_product"), \
                    mock.patch.object(self.gp, "get_product",
                                      return_value={"id": "pid", "published": False,
                                                    "price": 1499,
                                                    "description": desc,
                                                    "tags": list(od.LISTING_TAGS)}):
                res = od.apply_listing_copy(dry_run=False, evidence_path=target)
            self.assertTrue(res["description_words"] >= 300)
            self.assertFalse(res["published"])
            self.assertTrue(os.path.exists(target))


class TestAttachCover(unittest.TestCase):
    """The cover path: public-URL based, gate enforced, read-back proven,
    and never allowed to change price or publication state."""

    def setUp(self):
        import channels.gumroad_publisher as gp
        self.gp = gp
        self._orig = (od.read_draft_evidence, od.live_flag_enabled, od._write_authorized,
                      od.verify_cover_source)
        od.read_draft_evidence = lambda path=None: {"product_id": "pid"}

    def tearDown(self):
        (od.read_draft_evidence, od.live_flag_enabled, od._write_authorized,
         od.verify_cover_source) = self._orig

    def test_dry_run_touches_nothing(self):
        od.verify_cover_source = lambda *a, **k: self.fail("must not verify on a dry run")
        res = od.attach_cover()
        self.assertFalse(res["attached"])
        self.assertEqual(res["reason"], "dry_run")

    def test_requires_the_write_gate(self):
        od.live_flag_enabled = lambda: False
        od._write_authorized = lambda op: False
        with self.assertRaises(od.AuthorizationError):
            od.attach_cover(dry_run=False, evidence_path="unused.json")

    def test_refuses_a_public_url_that_is_not_our_cover(self):
        od.live_flag_enabled = lambda: True
        od._write_authorized = lambda op: True
        od.verify_cover_source = lambda *a, **k: {"identical": False, "public_status": 404}
        with self.assertRaises(od.PermanentError):
            od.attach_cover(dry_run=False, evidence_path="unused.json")

    def test_refuses_to_attach_while_published(self):
        od.live_flag_enabled = lambda: True
        od._write_authorized = lambda op: True
        od.verify_cover_source = lambda *a, **k: {"identical": True, "local_sha256": "x"}
        with mock.patch.object(self.gp, "load_token", return_value="tok"), \
                mock.patch.object(self.gp, "get_product",
                                  return_value={"published": True, "price": 1499, "covers": []}):
            with self.assertRaises(od.PermanentError):
                od.attach_cover(dry_run=False, evidence_path="unused.json")

    def test_success_writes_evidence_and_keeps_the_listing_unchanged(self):
        od.live_flag_enabled = lambda: True
        od._write_authorized = lambda op: True
        od.verify_cover_source = lambda *a, **k: {"identical": True, "local_sha256": "sha"}
        fresh = {"published": False, "price": 1499, "covers": [{"id": "c1"}], "main_cover_id": "c1"}
        with tempfile.TemporaryDirectory() as d:
            target = os.path.join(d, "cover_evidence.json")
            with mock.patch.object(self.gp, "load_token", return_value="tok"), \
                    mock.patch.object(self.gp, "get_product",
                                      side_effect=[{"published": False, "price": 1499, "covers": []},
                                                   fresh]), \
                    mock.patch.object(self.gp, "add_product_cover", return_value=fresh) as add:
                res = od.attach_cover(dry_run=False, evidence_path=target)
            self.assertTrue(res["attached"])
            self.assertFalse(res["published"])
            self.assertEqual(res["covers_count"], 1)
            self.assertEqual(add.call_args[0][2], od.COVER_PUBLIC_URL)
            self.assertTrue(os.path.exists(target))

    def test_cover_that_did_not_attach_is_not_reported_as_success(self):
        od.live_flag_enabled = lambda: True
        od._write_authorized = lambda op: True
        od.verify_cover_source = lambda *a, **k: {"identical": True, "local_sha256": "sha"}
        with mock.patch.object(self.gp, "load_token", return_value="tok"), \
                mock.patch.object(self.gp, "get_product",
                                  side_effect=[{"published": False, "price": 1499, "covers": []},
                                               {"published": False, "price": 1499, "covers": []}]), \
                mock.patch.object(self.gp, "add_product_cover",
                                  return_value={"published": False, "price": 1499, "covers": []}):
            with self.assertRaises(od.UncertainOutcomeError):
                od.attach_cover(dry_run=False, evidence_path="unused.json")

    def test_an_existing_cover_is_never_duplicated(self):
        od.live_flag_enabled = lambda: True
        od._write_authorized = lambda op: True
        od.verify_cover_source = lambda *a, **k: {"identical": True, "local_sha256": "sha"}
        with mock.patch.object(self.gp, "load_token", return_value="tok"), \
                mock.patch.object(self.gp, "add_product_cover") as add, \
                mock.patch.object(self.gp, "get_product",
                                  return_value={"published": False, "price": 1499,
                                                "covers": [{"id": "c1"}], "main_cover_id": "c1"}):
            res = od.attach_cover(dry_run=False, evidence_path="unused.json")
        add.assert_not_called()
        self.assertTrue(res["already_attached"])

    def test_cover_source_proves_the_real_file_when_available(self):
        """Integration-ish: the canonical cover exists and is a real PNG; the
        public check is exercised only if the network answers."""
        res = od.verify_cover_source()
        self.assertTrue(Path(res["local_path"]).exists())
        self.assertEqual(res["local_bytes"], 30643)


class TestRollbackPath(unittest.TestCase):
    """The revert-to-unpublished path uses the documented PUT .../disable."""

    def setUp(self):
        import channels.gumroad_publisher as gp
        self.gp = gp
        self.mock = mock

    def test_disable_uses_documented_route_and_reads_back(self):
        resp = self.mock.Mock(status_code=200)
        resp.json.return_value = {"success": True}
        with self.mock.patch.object(self.gp, "_request_with_retry",
                                    return_value=resp) as req, \
                self.mock.patch.object(self.gp, "get_product",
                                       return_value={"id": "x", "published": False}):
            res = od._real_disable_fn("tok", "x")
        self.assertTrue(res["disabled"])
        self.assertEqual(req.call_args[0][0], "PUT")
        self.assertIn("/products/x/disable", req.call_args[0][1])

    def test_disable_not_confirmed_by_readback_is_uncertain(self):
        resp = self.mock.Mock(status_code=200)
        resp.json.return_value = {"success": True}
        with self.mock.patch.object(self.gp, "_request_with_retry", return_value=resp), \
                self.mock.patch.object(self.gp, "get_product",
                                       return_value={"id": "x", "published": True}):
            with self.assertRaises(od.UncertainOutcomeError):
                od._real_disable_fn("tok", "x")

    def test_disable_non_success_is_permanent(self):
        resp = self.mock.Mock(status_code=404)
        resp.json.return_value = {"success": False}
        with self.mock.patch.object(self.gp, "_request_with_retry", return_value=resp):
            with self.assertRaises(od.PermanentError):
                od._real_disable_fn("tok", "x")

    def test_rollback_requires_the_write_gate(self):
        orig = od.read_draft_evidence
        od.read_draft_evidence = lambda path=None: {"product_id": "x"}
        try:
            with self.assertRaises(od.AuthorizationError):
                od._rollback()
        finally:
            od.read_draft_evidence = orig

    def test_rollback_needs_recorded_evidence(self):
        orig = od.read_draft_evidence
        od.read_draft_evidence = lambda path=None: {}
        try:
            with self.assertRaises(od.PermanentError):
                od._rollback()
        finally:
            od.read_draft_evidence = orig


class TestB12004Profile(unittest.TestCase):
    """Cycle 98 -- the parameterized second-product (B12-004) path.

    These prove the profile plumbing resolves per product while every default
    (no `product`) stays byte-for-byte B12-001."""

    def test_b12004_price_authority_is_authorized_at_1199(self):
        pa = od.price_authority(product="B12-004")
        self.assertTrue(pa["authorized"], pa.get("reason"))
        self.assertEqual(pa["price_usd"], 11.99)
        self.assertEqual(pa["basis"], "FOUNDER_APPROVED_BELOW_COMPARABLE_2026-10-18")

    def test_default_price_authority_unchanged(self):
        self.assertEqual(od.price_authority()["price_usd"], 14.99)
        self.assertEqual(od.price_authority(product="B12-001")["price_usd"], 14.99)

    def test_publish_phrase_per_product(self):
        self.assertEqual(od.publish_phrase(), "APPROVE B12-001 PUBLISH")
        self.assertEqual(od.publish_phrase("B12-004"), "APPROVE B12-004 PUBLISH")

    def test_task_graph_titles_use_product(self):
        titles = [t["title"] for t in od.build_task_graph("B12-004")]
        self.assertTrue(any("B12-004" in t for t in titles))
        self.assertFalse(any("B12-001" in t for t in titles))

    def test_default_task_graph_is_b12001(self):
        titles = [t["title"] for t in od.build_task_graph()]
        self.assertTrue(any("B12-001" in t for t in titles))

    def test_b12004_build_spec_has_two_pinned_files(self):
        gdo = od._load_gdo()
        spec = gdo.build_spec("B12-004")
        self.assertEqual(spec["product"], "B12-004")
        self.assertEqual(spec["price_cents"], 1199)
        self.assertEqual(len(spec["files"]), 2)
        self.assertIsNotNone(spec["expected_sha256"])

    def test_b12004_validate_spec_ready(self):
        require_paid_files(*_PAID)
        gdo = od._load_gdo()
        rep = gdo.validate_spec(gdo.build_spec("B12-004"))
        self.assertTrue(rep["ready"], [c for c in rep["checks"] if c["status"] != "PASS"])

    def test_default_build_spec_is_single_file_b12001(self):
        gdo = od._load_gdo()
        spec = gdo.build_spec()
        self.assertEqual(spec["product"], "B12-001")
        self.assertEqual(spec["price_cents"], 1499)
        self.assertEqual(len(spec["files"]), 1)

    def test_expected_price_for_path_resolves_per_product(self):
        self.assertEqual(
            od._expected_price_for_path(od.product_config("B12-004")["evidence"]), 1199)
        self.assertEqual(
            od._expected_price_for_path(od.product_config("B12-001")["evidence"]), 1499)
        unknown = Path(tempfile.gettempdir()) / "c98_unknown_evidence.json"
        self.assertEqual(od._expected_price_for_path(unknown), 1499)

    def test_verify_draft_expected_price_per_product(self):
        self.assertEqual(int(od.product_config("B12-004")["price_cents"]), 1199)
        self.assertEqual(int(od.product_config()["price_cents"]), 1499)

    def test_publish_task_requires_the_product_phrase(self):
        with self.assertRaises(od.FounderAuthorityError):
            od._task_publish({"product": "B12-004",
                              "publish_authorization": "APPROVE B12-001 PUBLISH"})
        with self.assertRaises(od.CapabilityError):
            od._task_publish({"product": "B12-004",
                              "publish_authorization": "APPROVE B12-004 PUBLISH"})

    def test_unknown_product_fails_closed(self):
        with self.assertRaises(Exception):
            od.product_config("B12-999")

    def test_b12004_listing_copy_parser(self):
        desc, tags = od._prepared_listing_copy("B12-004")
        self.assertEqual(len(tags), 8)
        self.assertIn("meetings", tags)
        self.assertGreaterEqual(len(desc.split()), 200)
        self.assertEqual(od._prepared_listing_copy("B12-004"),
                         od._prepared_listing_copy("B12-004"))

    def test_default_listing_copy_is_b12001(self):
        desc, tags = od._prepared_listing_copy()
        self.assertGreaterEqual(len(desc.split()), 300)
        self.assertEqual(tags, list(od.LISTING_TAGS))

    def test_b12004_apply_listing_copy_dry_run(self):
        out = od.apply_listing_copy(dry_run=True, product="B12-004")
        self.assertFalse(out["applied"])
        self.assertEqual(out["reason"], "dry_run")
        self.assertEqual(len(out["tags"]), 8)


class TestCycle99B12003Publish(unittest.TestCase):
    """Cycle 99: B12-003 is fully parameterized and its authorization is
    strictly product-scoped -- one product's phrase can never publish another,
    and the gate record must carry a real top-level APPROVED verdict."""

    def test_config_resolves_every_layer(self):
        cfg = od.product_config("B12-003")
        self.assertEqual(cfg["id"], "B12-003")
        self.assertEqual(int(cfg["price_cents"]), 800)
        self.assertEqual(cfg["phrase"], "APPROVE B12-003 PUBLISH")
        # `evidence` is created by the real draft create, so it is a forward
        # path; every pre-existing artifact must resolve on disk.
        for key in ("gate", "listing_copy", "customer_page", "cover_local_path"):
            self.assertTrue(Path(cfg[key]).exists(), f"{key} missing: {cfg[key]}")
        self.assertTrue(str(cfg["evidence"]).endswith("first_sale_draft_evidence_b12_003.json"))

    def test_price_authority_is_authorized_at_8_00(self):
        pa = od.price_authority(product="B12-003")
        self.assertTrue(pa["authorized"], pa.get("reason"))
        self.assertEqual(pa["price_usd"], 8.0)
        self.assertEqual(pa["basis"], "FOUNDER_DECISION_BELOW_COMPARABLE")
        self.assertGreaterEqual(len(pa["sources"]), 2)

    def test_manifest_price_matches_the_profile_price(self):
        # No layer may silently disagree on the price.
        import json
        man = json.loads((FACTORY_DIR / "data" / "product_batch_12.json").read_text(encoding="utf-8"))
        entry = next(p for p in man["products"] if p["id"] == "B12-003")
        profile = od.product_config("B12-003")
        self.assertEqual(int(entry["price_usd"] * 100), int(profile["price_cents"]))
        self.assertEqual(int(profile["price_cents"]), 800)

    def test_gate_must_carry_a_top_level_approved_verdict(self):
        # The real Cycle 99 blocker: GATE_FINAL for B12-003/B12-002 had verdicts
        # only nested, so price_authority read '' and refused. A gate without a
        # top-level APPROVED verdict must fail closed.
        b12_002_gate = FACTORY_DIR / "reports" / "B12-002" / "GATE_FINAL_2026-10-18.json"
        pa = od.price_authority(product="B12-003", gate_path=b12_002_gate)
        self.assertFalse(pa["authorized"])
        self.assertIn("not APPROVED", pa.get("reason", ""))

    def test_publish_requires_its_own_phrase(self):
        with self.assertRaises(od.FounderAuthorityError):
            od._task_publish({"product": "B12-003",
                              "publish_authorization": "APPROVE B12-001 PUBLISH"})
        with self.assertRaises(od.CapabilityError):
            od._task_publish({"product": "B12-003",
                              "publish_authorization": "APPROVE B12-003 PUBLISH"})

    def test_phrases_are_distinct_per_product(self):
        self.assertNotEqual(od.publish_phrase("B12-003"), od.publish_phrase("B12-001"))
        self.assertNotEqual(od.publish_phrase("B12-003"), od.publish_phrase("B12-004"))

    def test_b12003_phrase_does_not_unlock_b12001(self):
        with self.assertRaises(od.FounderAuthorityError):
            od._task_publish({"product": "B12-001",
                              "publish_authorization": "APPROVE B12-003 PUBLISH"})

    def test_b12003_listing_copy_parses_plain_format(self):
        desc, tags = od._prepared_listing_copy("B12-003")
        self.assertEqual(len(tags), 8)
        self.assertIn("business continuity", tags)
        self.assertGreaterEqual(len(desc.split()), 300)

    def test_b12003_apply_listing_copy_dry_run(self):
        out = od.apply_listing_copy(dry_run=True, product="B12-003")
        self.assertFalse(out["applied"])
        self.assertEqual(out["reason"], "dry_run")
        self.assertEqual(len(out["tags"]), 8)

    def test_publish_block_reopens_only_with_the_b12003_phrase(self):
        # A stale B12-003 publish block must stay BLOCKED until the exact
        # B12-003 phrase arrives -- and never be reopened by B12-001's.
        st = od.default_state()
        t = st["tasks"]["publish"]
        t["status"] = od.BLOCKED
        t["blocker"] = od.BLOCKER_FOUNDER_AUTHORITY
        t["authority_requirement"] = {"ctx_key": "publish_authorization",
                                      "required": "APPROVE B12-003 PUBLISH"}
        self.assertEqual(od.reset_founder_authority(st, {"publish_authorization": "APPROVE B12-001 PUBLISH"}), [])
        self.assertEqual(t["status"], od.BLOCKED)
        self.assertEqual(od.reset_founder_authority(st, {"publish_authorization": "APPROVE B12-003 PUBLISH"}), ["publish"])
        # Re-opened to PENDING only; the task function still enforces the phrase.
        self.assertEqual(t["status"], od.PENDING)

    def test_publish_guard_refuses_until_listing_copy_is_live(self):
        # The real Cycle 99 defect: a run published the listing before
        # --apply-listing, leaving zero tags live. The guard must now refuse.
        import channels.gumroad_publisher as gp
        orig_ev = od.read_draft_evidence
        od.read_draft_evidence = lambda path=None: {"product_id": "pid"}
        try:
            with mock.patch.object(gp, "load_token", return_value="tok"), \
                    mock.patch.object(gp, "enable_product") as en, \
                    mock.patch.object(gp, "get_product",
                                      return_value={"id": "pid", "published": False,
                                                    "tags": [], "description": "word " * 400}):
                with self.assertRaises(od.CapabilityError):
                    od._real_publish_fn({"product": "B12-003",
                                         "publish_authorization": "APPROVE B12-003 PUBLISH"})
                en.assert_not_called()
        finally:
            od.read_draft_evidence = orig_ev

    def test_publish_guard_allows_publish_once_listing_copy_is_live(self):
        import channels.gumroad_publisher as gp
        _, tags = od._prepared_listing_copy("B12-003")
        live_pre = {"id": "pid", "published": False, "tags": list(tags),
                    "description": "word " * 320}
        live_post = {"id": "pid", "published": True, "tags": list(tags),
                     "description": "word " * 320, "short_url": "https://x/l/abc"}
        orig_ev = od.read_draft_evidence
        od.read_draft_evidence = lambda path=None: {"product_id": "pid"}
        try:
            with mock.patch.object(gp, "load_token", return_value="tok"), \
                    mock.patch.object(gp, "enable_product") as en, \
                    mock.patch.object(gp, "get_product", side_effect=[live_pre, live_post]):
                out = od._real_publish_fn({"product": "B12-003",
                                           "publish_authorization": "APPROVE B12-003 PUBLISH"})
            en.assert_called_once()
            self.assertTrue(out["published"])
        finally:
            od.read_draft_evidence = orig_ev

    def test_republish_requires_gate_and_phrase(self):
        orig = (od.live_flag_enabled, od._write_authorized, od._real_publish_fn)
        try:
            od.live_flag_enabled = lambda: False
            od._write_authorized = lambda op="create_product": False
            with self.assertRaises(od.FounderAuthorityError):
                od.republish(product="B12-003", publish_authorization="nope")
            with self.assertRaises(od.AuthorizationError):
                od.republish(product="B12-003",
                             publish_authorization="APPROVE B12-003 PUBLISH")
            calls = []
            od.live_flag_enabled = lambda: True
            od._write_authorized = lambda op="create_product": True
            od._real_publish_fn = lambda ctx: calls.append(ctx) or {"published": True}
            out = od.republish(product="B12-003",
                               publish_authorization="APPROVE B12-003 PUBLISH")
            self.assertTrue(out["published"])
            self.assertEqual(calls[0]["product"], "B12-003")
        finally:
            od.live_flag_enabled, od._write_authorized, od._real_publish_fn = orig


if __name__ == "__main__":
    unittest.main()
