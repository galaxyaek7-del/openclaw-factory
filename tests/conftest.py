"""Cycle 77 section 2: mirrors scripts/run_python_group.py's network
block for ad-hoc `pytest` runs (the real CI entrypoint is unittest-based
and does not load this file at all -- see that script for the
authoritative enforcement point). Session-scoped and autouse so every
test, in every file, is covered with no per-file opt-in needed.

Phase 5 (2026-10-14): write-gate authorisation for the test suite.

channels/write_gate.py makes every Gumroad mutation begin with a fail-closed
authorisation check.

CYCLE 84 CORRECTION -- THIS FIXTURE WAS ITSELF THE DEFECT. The original
version set FACTORY_LIVE_PUBLISH=true for every test in the suite. That is
exactly the "broad hidden permission inside a test fixture" the founder's
directive forbids: a green suite was relying on a factory-wide live-publishing
flag being on. It also silently defeated tests that assert the gate DENIES --
they passed only because this fixture flipped the switch first.

What is provided here now is deliberately NARROWER than before:

  * the auth STATE (a fresh, fingerprint-matched VERIFIED record) via
    FACTORY_WRITE_GATE_STATE_PATH, and
  * an OPT-IN `authorize_live_writes` fixture, which a test must request by
    name. Nothing is authorised implicitly.

Safety is unchanged: network_guard.block() monkeypatches
socket.socket.connect/connect_ex, the single chokepoint urllib, requests and
http.client all go through, so a test cannot reach Gumroad even with an
authorization in hand. The fixture grants the DECISION, never the NETWORK.
"""
import json
import os
from datetime import datetime, timezone

import network_guard
import pytest


def pytest_configure(config):
    network_guard.block()
    # Backlog B5: same write overlay as scripts/run_python_group.py.
    import write_guard
    write_guard.install()


def _write_state(state_file) -> str:
    """A fresh, fingerprint-matched VERIFIED state, scoped to this run."""
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
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
    return str(state_file)


@pytest.fixture
def authorize_live_writes(tmp_path_factory):
    """
    OPT-IN. A test that exercises write logic against a mocked HTTP layer
    must request this fixture by name. It sets FACTORY_LIVE_PUBLISH only for
    the duration of that one test.

    It is deliberately not autouse. Cycle 84 removed an autouse version
    because a suite-wide live-publishing flag is a hidden broad permission,
    and because it made every "the gate denies" assertion untestable.
    """
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    state = tmp_path_factory.mktemp("write_gate") / "auth_state.json"
    saved_flag = os.environ.get("FACTORY_LIVE_PUBLISH")
    saved_path = os.environ.get("FACTORY_WRITE_GATE_STATE_PATH")
    os.environ["FACTORY_LIVE_PUBLISH"] = "true"
    os.environ["FACTORY_WRITE_GATE_STATE_PATH"] = _write_state(state)
    try:
        yield
    finally:
        for k, v in (("FACTORY_LIVE_PUBLISH", saved_flag),
                     ("FACTORY_WRITE_GATE_STATE_PATH", saved_path)):
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v