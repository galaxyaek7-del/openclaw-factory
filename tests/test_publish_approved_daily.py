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

    def test_already_published_products_are_not_candidates(self):
        groups = pad.candidates(self.registry, self.batches)
        self.assertEqual(groups, {"batch16": ["B16-008", "B16-009", "B16-010"]})


if __name__ == "__main__":
    unittest.main()
