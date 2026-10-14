"""Cycle 77 section 2: mirrors scripts/run_python_group.py's network
block for ad-hoc `pytest` runs (the real CI entrypoint is unittest-based
and does not load this file at all -- see that script for the
authoritative enforcement point). Session-scoped and autouse so every
test, in every file, is covered with no per-file opt-in needed.

Phase 5 (2026-10-14): write-gate authorisation for the test suite.

channels/write_gate.py makes every Gumroad mutation begin with a fail-closed
authorisation check. That is correct, and it correctly broke 63 existing unit
tests across 11 files that exercise write logic against a mocked HTTP layer --
they were reaching their mocks, and now hit WriteNotAuthorized first.

The fix below grants those tests an authorised gate state. It is SAFE because
of what is already in place in this very file: network_guard.block()
monkeypatches socket.socket.connect/connect_ex, the single chokepoint every
Python HTTP client ultimately goes through, to raise for any non-loopback
destination. A test that tries to perform a REAL mutation cannot reach
Gumroad even with the gate open -- it dies at the socket layer.

This fixture therefore authorises the DECISION, never the NETWORK. It also
cannot weaken the rules: the gate still requires the state to be exactly
VERIFIED, fresh, and fingerprint-matched. tests/test_write_gate.py pins every
one of those denial branches and is unaffected, because it passes its own
explicit state_path and patches the environment itself.
"""
import json
import os
from datetime import datetime, timezone

import network_guard
import pytest


def pytest_configure(config):
    network_guard.block()


@pytest.fixture(autouse=True)
def _authorize_write_gate_for_tests(tmp_path_factory):
    """
    Provide a VALID, FRESH, FINGERPRINT-MATCHED auth state so write-logic unit
    tests can reach their mocks. Restores the previous environment afterwards.

    The fingerprint written here is the live credential's own fingerprint,
    read through the same helper the gate uses -- so this grants nothing the
    gate would not also require in production.
    """
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    saved_flag = os.environ.get("FACTORY_LIVE_PUBLISH")
    saved_path = os.environ.get("FACTORY_WRITE_GATE_STATE_PATH")
    state_file = tmp_path_factory.mktemp("write_gate") / "auth_state.json"

    fp = ""
    try:
        import gumroad_auth_watch as auth
        fp = auth.credential_fingerprint() or ""
    except Exception:  # noqa: BLE001 -- a test suite must still run
        fp = ""

    state_file.write_text(json.dumps({
        "status": "VERIFIED",
        "reason": "test fixture: unit tests only, network is blocked",
        "fingerprint_prefix": fp[:16] if fp else "",
        "at": datetime.now(timezone.utc).isoformat(),
    }), encoding="utf-8")

    os.environ["FACTORY_LIVE_PUBLISH"] = "true"
    os.environ["FACTORY_WRITE_GATE_STATE_PATH"] = str(state_file)
    try:
        yield
    finally:
        if saved_flag is None:
            os.environ.pop("FACTORY_LIVE_PUBLISH", None)
        else:
            os.environ["FACTORY_LIVE_PUBLISH"] = saved_flag
        if saved_path is None:
            os.environ.pop("FACTORY_WRITE_GATE_STATE_PATH", None)
        else:
            os.environ["FACTORY_WRITE_GATE_STATE_PATH"] = saved_path