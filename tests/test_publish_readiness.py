"""The readiness report is the only thing that will notice a silent blocker.

If it ever reports ready_to_publish=true while the session is stale, the loop
says nothing and the factory looks healthy while refusing every publish -- which
is exactly the failure that lasted eleven days. These tests pin the verdict
logic, not the wording.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import publish_readiness_daily as prd  # noqa: E402


@pytest.fixture()
def env(tmp_path, monkeypatch):
    data = tmp_path / "data"
    reports = tmp_path / "reports"
    data.mkdir()
    monkeypatch.setattr(prd, "DATA", data)
    monkeypatch.setattr(prd, "REPORTS", reports)

    def write(name, payload):
        (data / name).write_text(json.dumps(payload), encoding="utf-8")

    return write


def _check(verdict, name):
    return next(c for c in verdict["checks"] if c["check"] == name)


def test_stale_session_blocks_and_names_the_command(env, monkeypatch):
    env("gumroad_auth_state.json", {"recorded_at": "2026-11-08T16:13:11+00:00"})
    env("publication_approvals.json", {"approvals": []})
    env("product_registry.json", {"products": []})
    env("pinterest_queue.json", {"items": []})
    monkeypatch.setattr(sys, "argv", ["x"])
    assert prd.main() == 0

    verdict = json.loads((prd.REPORTS / "publish_readiness_2026-11-20.json").read_text(encoding="utf-8")) \
        if (prd.REPORTS / "publish_readiness_2026-11-20.json").exists() else None
    assert verdict is not None
    assert verdict["ready_to_publish"] is False
    assert "gumroad_session" in verdict["blocking"]
    assert "gumroad_auth_watch" in _check(verdict, "gumroad_session")["clears_with"]


def test_approvals_are_append_only_and_the_latest_record_wins(env):
    env("publication_approvals.json", {"approvals": [
        {"product_id": "B19-001", "status": "APPROVED", "approved_at": "2026-11-01T00:00:00Z",
         "expires_at": "2026-11-02T00:00:00Z"},
        {"product_id": "B19-001", "status": "APPROVED", "approved_at": "2026-11-19T00:00:00Z",
         "expires_at": "2099-01-01T00:00:00Z"},
        {"product_id": "B19-002", "status": "REVOKED", "approved_at": "2026-11-19T00:00:00Z",
         "expires_at": "2099-01-01T00:00:00Z"},
    ]})
    result = prd.approval_blocker()
    assert result["approved"] == ["B19-001"]
    assert result["not_approved"] == ["B19-002"]
    assert result["status"] == "OK"


def test_pins_already_scheduled_in_the_past_are_named(env):
    env("pinterest_queue.json", {"items": [
        {"id": "p1", "status": "READY", "scheduled_at": "2026-10-27T10:00:00Z"},
        {"id": "p2", "status": "READY", "scheduled_at": "2099-01-01T10:00:00Z"},
    ]})
    result = prd.pinterest_blocker()
    assert result["scheduled_in_past"] == 1
    assert result["status"] == "SCHEDULED_IN_PAST"


def test_nothing_ready_is_not_reported_as_ready(env):
    env("publication_approvals.json", {"approvals": []})
    env("product_registry.json", {"products": [{"primary_state": "PUBLIC_LISTING_VERIFIED"}]})
    result = prd.registry_blocker()
    assert result["status"] == "NOTHING_READY"
    assert result["clears_with"] == "python product_registry.py --rebuild"
