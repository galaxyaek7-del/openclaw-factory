import pytest
"""G7 — fsync durability for factory_state and publish_protection."""
import unittest
from pathlib import Path
import tempfile
import inspect

# Cycle 84: this module exercises Gumroad write logic against a mocked
# HTTP layer, so it explicitly opts in to write authorization. It was
# previously getting this from an AUTOUSE fixture that set
# FACTORY_LIVE_PUBLISH=true for the whole suite -- a hidden broad
# permission. The opt-in is now visible here, in the file that needs it.
pytestmark = pytest.mark.usefixtures("authorize_live_writes")

class TestG7FactoryState(unittest.TestCase):
    def test_save_uses_fsync(self):
        import factory_state
        src = inspect.getsource(factory_state.save_state)
        self.assertIn("fsync", src)
        self.assertIn("flush", src)

    def test_save_and_load_roundtrip(self):
        import factory_state
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "factory_state.json"
            state = {"current_task": {"name": "test"}, "pending_retries": []}
            factory_state.save_state(state, path=p)
            loaded = factory_state.load_state(path=p)
            self.assertEqual(loaded["current_task"]["name"], "test")

    def test_corrupt_returns_default(self):
        import factory_state
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "factory_state.json"
            p.write_text("not json {{{", encoding="utf-8")
            loaded = factory_state.load_state(path=p)
            self.assertIsNone(loaded["current_task"])

class TestG7PublishProtection(unittest.TestCase):
    def test_save_uses_fsync(self):
        import channels.publish_protection as pp
        src = inspect.getsource(pp._save_state)
        self.assertIn("fsync", src)

    def test_save_and_load_roundtrip(self):
        import channels.publish_protection as pp
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "publish_protection_state.json"
            state = {"global": {"emergency_stopped": False}, "arms": {}}
            pp._save_state(state, state_path=p)
            # load via _load_state if exists, else just check file exists and is valid json
            import json
            self.assertTrue(p.exists())
            data = json.loads(p.read_text(encoding="utf-8"))
            self.assertIn("global", data)

    def test_d7_g2_still_verified(self):
        self.assertIn("abs(rate - t) < 1e-9", Path("economics.py").read_text(encoding="utf-8"))
        # D8's platform-param form was consolidated: economics.net_profit()
        # takes the platform explicitly and profit_oracle passes
        # "gumroad_digital" at the real call site (same note as
        # tests/test_d16_d19.py::test_d8_still_verified).
        self.assertIn('ECONOMICS.net_profit(price, "gumroad_digital", config)', Path("profit_oracle.py").read_text(encoding="utf-8"))

    def test_d10_still_verified(self):
        self.assertIn("astimezone(timezone.utc)", Path("profit_oracle.py").read_text(encoding="utf-8"))
