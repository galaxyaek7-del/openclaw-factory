"""scripts/publish_approved_daily.py: publishes only what the publisher's own
audit passes, only when switched on, and never beyond Gumroad's window.
The publisher is replaced by a fake; nothing touches Gumroad or real files."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import publish_approved_daily as pad  # noqa: E402


class FakePublisher:
    def __init__(self, passing):
        self.passing, self.calls = set(passing), []

    def __call__(self, args, timeout_s):
        self.calls.append(args)
        ids = args[args.index("--only") + 1:]
        if "--live" in args:
            return {"results": [{"id": i, "status": "PASS"} for i in ids]}
        return {"products": [{"id": i, "status": "PASS" if i in self.passing else "HOLD"} for i in ids]}


class PublishApproved(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        folder = Path(self.dir.name) / "batch16"
        (folder / "B16-008").mkdir(parents=True)
        self.batches = {"batch16": (folder, Path(self.dir.name) / "results.json")}
        rel = lambda i: str(folder / i / "manifest.json")
        self.registry = {"products": [
            {"internal_id": i, "primary_state": "READY_FOR_AUTHORIZATION", "manifest": rel(i)} for i in ("B16-008", "B16-009", "B16-010")
        ] + [{"internal_id": "B16-001", "primary_state": "PUBLIC_LISTING_VERIFIED", "manifest": rel("B16-001")}]}

    def tearDown(self):
        self.dir.cleanup()

    def go(self, env, passing=("B16-008", "B16-009"), used=0, limit=10):
        pub = FakePublisher(passing)
        out = pad.run_once(env=env, registry=self.registry, batches=self.batches, window_used=used, run=pub, limit=limit)
        return out, pub

    def test_off_by_default_reports_without_publishing(self):
        out, pub = self.go({})
        self.assertEqual(out["action"], "none")
        self.assertIn("2 approved product(s) ready; auto-publish is off", out["detail"])
        self.assertFalse(any("--live" in c for c in pub.calls))

    def test_publishes_only_products_the_audit_passes(self):
        out, pub = self.go({pad.SWITCH: "true"})
        live = [c for c in pub.calls if "--live" in c]
        self.assertEqual(len(live), 1)
        self.assertEqual(live[0][live[0].index("--only") + 1:], ["B16-008", "B16-009"])
        self.assertEqual(out["action"], "published")

    def test_never_exceeds_the_gumroad_window(self):
        out, pub = self.go({pad.SWITCH: "true"}, used=9)
        live = [c for c in pub.calls if "--live" in c]
        self.assertEqual(live[0][live[0].index("--only") + 1:], ["B16-008"])
        out, pub = self.go({pad.SWITCH: "true"}, used=10)
        self.assertIn("window full", out["detail"])
        self.assertFalse(any("--live" in c for c in pub.calls))

    def test_no_valid_approval_means_nothing_to_publish(self):
        out, pub = self.go({pad.SWITCH: "true"}, passing=())
        self.assertIn("none has a valid approval", out["detail"])
        self.assertFalse(any("--live" in c for c in pub.calls))

    def test_freeze_wins_over_the_publish_switch_and_calls_nothing(self):
        out, pub = self.go({pad.SWITCH: "true", pad.FREEZE: "true"})
        self.assertEqual(out["action"], "none")
        self.assertIn("frozen", out["detail"])
        self.assertEqual(pub.calls, [], "a frozen run must not even run the publisher dry run")

    def test_freeze_off_or_other_value_changes_nothing(self):
        for v in ("", "false", "0"):
            out, pub = self.go({pad.SWITCH: "true", pad.FREEZE: v})
            self.assertEqual(out["action"], "published", v)

    def test_loop_source_gates_every_automatic_producer(self):
        src = (Path(__file__).resolve().parent.parent / "factory_loop.js").read_text(encoding="utf-8")
        self.assertIn("GF_FREEZE_NEW_PRODUCTS", src)
        # demand-gated design (founder, second order 2026-11-05): one isProductFrozen() decides
        for needle in ("process.env.FACTORY_LIVE_PUBLISH === 'true' && !isProductFrozen()",
                       "process.env.FACTORY_AUTO_PRODUCE === 'true' && !isProductFrozen()"):
            self.assertIn(needle, src)
        for fn in ("async function triggerGenerateBook(", "async function runAgentProductChain("):
            body = src[src.index(fn):]
            first_lines = body.split(chr(10))[:3]
            self.assertTrue(any("if (isProductFrozen())" in l for l in first_lines), fn)

    def test_gated_freeze_lifts_only_while_the_gate_is_open_and_caps_the_day(self):
        env = {pad.SWITCH: "true", pad.FREEZE: "true", pad.GATED: "true"}
        from unittest import mock
        closed = {"open": False, "daily_cap": 0, "why": "WAITING FOR REAL DATA"}
        with mock.patch.object(pad, "_demand_gate", return_value=closed):
            out, pub = self.go(env)
        self.assertEqual(out["action"], "none")
        self.assertIn("WAITING FOR REAL DATA", out["detail"])
        self.assertEqual(pub.calls, [])
        with mock.patch.object(pad, "_demand_gate", return_value=None):  # gate cannot run: fail closed
            out, pub = self.go(env)
        self.assertEqual(out["action"], "none")
        self.assertEqual(pub.calls, [])
        opened = {"open": True, "daily_cap": 1, "why": "real demand recorded: SALE"}
        with mock.patch.object(pad, "_demand_gate", return_value=opened):
            out, pub = self.go(env)
        self.assertEqual(out["action"], "published")
        live = [c for c in pub.calls if "--live" in c]
        self.assertEqual(len(live), 1)
        self.assertEqual(len(live[0][live[0].index("--only") + 1:]), 1, "the daily cap limits the batch")

    def test_founder_approved_products_may_go_out_when_frozen_only_with_the_explicit_flag(self):
        from unittest import mock
        closed = {"open": False, "daily_cap": 0, "why": "WAITING FOR REAL DATA"}
        base = {pad.SWITCH: "true", pad.FREEZE: "true", pad.GATED: "true"}
        with mock.patch.object(pad, "_demand_gate", return_value=closed):
            out, pub = self.go(base)  # flag absent: still frozen
        self.assertEqual(out["action"], "none")
        self.assertEqual(pub.calls, [])
        with mock.patch.object(pad, "_demand_gate", return_value=closed):
            out, pub = self.go(dict(base, **{pad.FOUNDER_APPROVED: "true"}))
        self.assertEqual(out["action"], "published")
        live = [c for c in pub.calls if "--live" in c]
        self.assertEqual(live[0][live[0].index("--only") + 1:], ["B16-008", "B16-009"], "only audit-passing, approved products go out")

    def test_with_the_flag_a_product_without_a_valid_approval_still_does_not_go_out(self):
        from unittest import mock
        closed = {"open": False, "daily_cap": 0, "why": "x"}
        with mock.patch.object(pad, "_demand_gate", return_value=closed):
            out, pub = self.go({pad.SWITCH: "true", pad.FREEZE: "true", pad.FOUNDER_APPROVED: "true"}, passing=())
        self.assertIn("none has a valid approval", out["detail"])
        self.assertFalse(any("--live" in c for c in pub.calls))

    def test_gate_switch_off_keeps_the_freeze_absolute(self):
        from unittest import mock
        opened = {"open": True, "daily_cap": 5, "why": "x"}
        with mock.patch.object(pad, "_demand_gate", return_value=opened):
            out, pub = self.go({pad.SWITCH: "true", pad.FREEZE: "true"})
        self.assertEqual(out["action"], "none")
        self.assertEqual(pub.calls, [])

    def test_already_published_products_are_not_candidates(self):
        groups = pad.candidates(self.registry, self.batches)
        self.assertEqual(groups, {"batch16": ["B16-008", "B16-009", "B16-010"]})


if __name__ == "__main__":
    unittest.main()


def test_reopen_daily_followups_clears_only_the_day_marker(tmp_path):
    import json
    import publish_approved_daily as pad
    for n, doc in (("registry_daily_state.json", {"last_day": "2026-11-06", "summary": {}}),
                   ("tool_pages_daily_state.json", {"last_day": "2026-11-06", "result": {"pages": 3}}),
                   ("indexnow_auto.json", {"submitted": {"a": 1}, "last_day": "2026-11-06"}),
                   ("listing_health_state.json", {"last_day": "2026-11-06"})):
        (tmp_path / n).write_text(json.dumps(doc), encoding="utf-8")
    assert sorted(pad.reopen_daily_followups(tmp_path)) == sorted(pad.FOLLOWUP_STATES)
    d = json.loads((tmp_path / "indexnow_auto.json").read_text(encoding="utf-8"))
    assert d["last_day"] is None and d["submitted"] == {"a": 1}
    assert pad.reopen_daily_followups(tmp_path) == []


def test_a_product_already_live_pass_is_not_a_candidate_again(tmp_path):
    import json
    import publish_approved_daily as pad
    res = tmp_path / "res.json"
    res.write_text(json.dumps([{"mode": "LIVE", "results": [{"id": "B1-001", "status": "PASS", "product_id": "abc"}]},
                               {"mode": "LIVE", "results": [{"id": "B1-002", "status": "BLOCKED"}, {"id": "B1-004", "status": "BLOCKED", "product_id": "made-but-cover-failed"}]},
                               {"mode": "DRY", "results": [{"id": "B1-003", "status": "PASS", "product_id": "zzz"}]}]), encoding="utf-8")
    folder = tmp_path / "b1"
    (folder / "x").mkdir(parents=True)
    reg = {"products": [{"internal_id": i, "primary_state": "READY_FOR_AUTHORIZATION", "manifest": str(folder / "x" / "m.json")}
                        for i in ("B1-001", "B1-002", "B1-003", "B1-004")]}
    out = pad.candidates(reg, {"b1": (str(folder), str(res))})
    assert out == {"b1": ["B1-002", "B1-003"]}
    assert pad.candidates(reg, {"b1": (str(folder), str(tmp_path / "missing.json"))}) == {"b1": ["B1-001", "B1-002", "B1-003", "B1-004"]}
