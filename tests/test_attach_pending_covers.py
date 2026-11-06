import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import attach_pending_covers as a  # noqa: E402


def _results(tmp_path, runs):
    (tmp_path / "data").mkdir(exist_ok=True)
    (tmp_path / "data" / "batch9_publish_results.json").write_text(json.dumps(runs), encoding="utf-8")
    return str(tmp_path / "data" / "batch*_publish_results.json")


def test_pending_lists_only_live_created_listings_with_a_failed_cover(tmp_path):
    g = _results(tmp_path, [
        {"mode": "LIVE", "results": [{"id": "B9-001", "product_id": "p1", "steps": {"cover": "FAILED: x"}},
                                     {"id": "B9-002", "product_id": "p2", "steps": {"cover": "ok"}},
                                     {"id": "B9-003", "steps": {"cover": "FAILED: y"}}]},
        {"mode": "DRY", "results": [{"id": "B9-004", "product_id": "p4", "steps": {"cover": "FAILED: z"}}]}])
    assert a.pending(g, root=tmp_path) == [("B9-001", "p1")]


def test_a_cover_already_attached_is_no_longer_pending(tmp_path):
    g = _results(tmp_path, [{"mode": "LIVE", "results": [{"id": "B9-001", "product_id": "p1", "steps": {"cover": "FAILED: x"}}]}])
    (tmp_path / "data" / "gumroad_cover_results.json").write_text(
        json.dumps([{"results": [{"id": "p1", "name": "B9-001", "result": "ATTACHED"}]}]), encoding="utf-8")
    assert a.pending(g, root=tmp_path) == []


def test_nothing_pending_is_none():
    assert a.run_once(pending_fn=lambda: [])["action"] == "none"


def test_waits_for_the_public_url_and_never_calls_gumroad_before():
    r = a.run_once(pending_fn=lambda: [("B9-001", "p1")], stage_fn=lambda i: "committed", ok_fn=lambda u: False, gp=object(), auth=object())
    assert r["action"] == "waiting" and "waiting for the site publish" in r["detail"]


class GP:
    def __init__(self, covers):
        self.covers, self.calls = covers, []

    def load_token(self):
        return "t"

    def get_product(self, token, pid):
        return {"published": True, "covers": self.covers}

    def add_product_cover(self, token, pid, url, expected_cover_count=0):
        self.calls.append((pid, url))
        return {"covers": ["c"]}


class Auth:
    def __init__(self, status):
        self.s = status

    def poll(self):
        return {"status": self.s}


def test_attaches_with_safeguards(tmp_path, monkeypatch):
    monkeypatch.setattr(a, "RESULTS", tmp_path / "res.json")
    gp = GP([])
    r = a.run_once(pending_fn=lambda: [("B9-001", "p1")], stage_fn=lambda i: "ready", ok_fn=lambda u: True, gp=gp, auth=Auth("VERIFIED"))
    assert r["action"] == "attached" and gp.calls == [("p1", a.PUBLIC.format(id="B9-001"))]
    assert json.loads((tmp_path / "res.json").read_text(encoding="utf-8"))[0]["results"][0]["result"] == "ATTACHED"


def test_a_product_that_already_has_a_cover_is_never_touched(tmp_path, monkeypatch):
    monkeypatch.setattr(a, "RESULTS", tmp_path / "res.json")
    gp = GP(["existing"])
    a.run_once(pending_fn=lambda: [("B9-001", "p1")], stage_fn=lambda i: "ready", ok_fn=lambda u: True, gp=gp, auth=Auth("VERIFIED"))
    assert gp.calls == []


def test_unverified_auth_blocks_every_write(tmp_path, monkeypatch):
    monkeypatch.setattr(a, "RESULTS", tmp_path / "res.json")
    gp = GP([])
    r = a.run_once(pending_fn=lambda: [("B9-001", "p1")], stage_fn=lambda i: "ready", ok_fn=lambda u: True, gp=gp, auth=Auth("NEEDS_AUTH"))
    assert r["action"] == "blocked" and gp.calls == []
