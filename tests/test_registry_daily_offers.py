"""scripts/registry_daily.py restates the distribution offers after the registry
rebuild (2026-10-31), and a failure there never hides the registry result.
Injected runner and writers only; nothing live is read or written."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import registry_daily as rd  # noqa: E402

SUMMARY = {"products": 1, "states": {"PUBLIC_LISTING_VERIFIED": 1}, "sales_total": 0,
           "drift_counts": {"duplicate_live_titles": 0}}


class RegistryDailyOffers(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.state = Path(self.dir.name) / "state.json"

    def tearDown(self):
        self.dir.cleanup()

    def run_(self, offers_writer):
        return rd.run_once(today="2026-10-31", state_path=self.state, runner=lambda: (SUMMARY, {}),
                           arms_writer=lambda: None, trends_writer=lambda: None, offers_writer=offers_writer)

    def test_offers_are_restated_after_the_rebuild(self):
        calls = []
        out = self.run_(lambda: calls.append(json.loads(self.state.read_text(encoding="utf-8"))["last_day"]))
        self.assertEqual(calls, ["2026-10-31"])  # runs after the registry state is written
        self.assertEqual(out["action"], "ok")

    def test_an_offers_failure_is_reported_not_raised(self):
        def boom():
            raise OSError("offline")
        out = self.run_(boom)
        self.assertEqual(out["action"], "ok")
        self.assertIn("distribution offers not written (OSError)", out["detail"])

    def test_the_live_writer_never_drafts(self):
        import inspect
        src = inspect.getsource(rd._write_offers)
        self.assertNotIn("add_draft", src)
        self.assertNotIn("distribution_cycle", src)


if __name__ == "__main__":
    unittest.main()
