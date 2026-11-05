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
