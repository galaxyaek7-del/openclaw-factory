"""scripts/tool_pages_daily.py: once-a-day gate around the tool-page generator.
The real generator, state file and site are never touched: temp state and an
injected runner only."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import tool_pages_daily as tpd  # noqa: E402


class DailyGate(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.state = Path(self.dir.name) / "state.json"

    def tearDown(self):
        self.dir.cleanup()

    def test_new_pages_report_updated_and_set_the_gate(self):
        out = tpd.run_once(today="2026-10-29", state_path=self.state,
                           runner=lambda: {"pages": 30, "sitemap_added": 3, "skipped_unpublished": []})
        self.assertEqual(out["action"], "updated")
        self.assertIn("3 new in sitemap", out["detail"])
        again = tpd.run_once(today="2026-10-29", state_path=self.state, runner=lambda: self.fail("ran twice"))
        self.assertEqual(again["action"], "none")

    def test_nothing_new_is_none(self):
        out = tpd.run_once(today="2026-10-30", state_path=self.state,
                           runner=lambda: {"pages": 30, "sitemap_added": 0, "skipped_unpublished": ["B16-008"]})
        self.assertEqual(out["action"], "none")
        self.assertIn("1 unpublished skipped", out["detail"])

    def test_missing_generator_is_reported_not_failed(self):
        out = tpd.run_once(today="2026-10-29", state_path=self.state, generator=Path(self.dir.name) / "absent.py")
        self.assertEqual(out["action"], "none")
        self.assertIn("generator not present", out["detail"])
        self.assertFalse(self.state.exists())

    def test_generator_error_is_reported_and_retried_next_tick(self):
        def boom():
            raise RuntimeError("bad page")
        out = tpd.run_once(today="2026-10-29", state_path=self.state, runner=boom)
        self.assertEqual(out["action"], "failed")
        self.assertFalse(self.state.exists())

    def test_without_once_flag_it_does_nothing(self):
        self.assertEqual(tpd.main([]), 2)


if __name__ == "__main__":
    unittest.main()
