"""GF-22: review runner is deadline-gated, validates input, idempotent."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from run_campaign_review import check_deadline, decide, load_snapshot, run
import datetime

SNAP = json.loads((ROOT / "data" / "review_snapshot_10-11.json").read_text(encoding="utf-8"))


def test_snapshot_validates():
    loaded, err = load_snapshot(str(ROOT / "data" / "review_snapshot_10-11.json"))
    assert err is None and loaded["deadline"].isoformat().startswith("2026-10-11")


def test_malformed_snapshot_rejected(tmp_path):
    bad = tmp_path / "s.json"
    bad.write_text(json.dumps({"campaigns": []}), encoding="utf-8")
    loaded, err = load_snapshot(str(bad))
    assert loaded is None and "missing" in err
    bad.write_text("not json", encoding="utf-8")
    loaded, err = load_snapshot(str(bad))
    assert loaded is None and "unreadable" in err


def test_future_deadline_refuses_real_run():
    res = run(str(ROOT / "data" / "review_snapshot_10-11.json"), str(ROOT / "data"))
    assert res["exit"] == 3 and "premature" in res["error"]


def test_dry_run_past_deadline_writes_temp_only(tmp_path):
    snap = copy.deepcopy(SNAP)
    snap["review_deadline"] = "2026-01-01T00:00:00+00:00"
    fx = tmp_path / "snap.json"
    fx.write_text(json.dumps(snap), encoding="utf-8")
    before = {p.name for p in (ROOT / "data").glob("review_result_*.json")}
    res = run(str(fx), str(tmp_path), dry_run=True)
    assert res["exit"] == 0 and "dry_run_path" in res
    assert "tmp" in res["dry_run_path"].lower() or "Temp" in res["dry_run_path"]
    after = {p.name for p in (ROOT / "data").glob("review_result_*.json")}
    assert after == before, "dry-run must never write the production artifact"


def test_idempotency(tmp_path):
    snap = copy.deepcopy(SNAP)
    snap["review_deadline"] = "2026-01-02T00:00:00+00:00"
    fx = tmp_path / "snap.json"
    fx.write_text(json.dumps(snap), encoding="utf-8")
    first = run(str(fx), str(tmp_path))
    assert first["exit"] == 0
    second = run(str(fx), str(tmp_path))
    assert second["exit"] == 4 and "already-decided" in second["error"]
    third = run(str(fx), str(tmp_path), force=True, force_reason="test override")
    assert third["exit"] == 0 and True


def test_verdict_mapping():
    v, _ = decide("EXP-X", "live", "")
    assert v == "CONTINUE"
    v, _ = decide("EXP-X", "UNKNOWN(timeout)", "")
    assert v == "INCONCLUSIVE"
    v, _ = decide("EXP-X", "live", "dead destination link evidenced")
    assert v == "IMPROVE"


def test_check_deadline():
    dl = datetime.datetime(2026, 10, 11, 23, 59, tzinfo=datetime.timezone.utc)
    ok, _ = check_deadline(dl, datetime.datetime(2026, 10, 12, tzinfo=datetime.timezone.utc))
    assert ok
    ok, why = check_deadline(dl, datetime.datetime(2026, 10, 9, tzinfo=datetime.timezone.utc))
    assert not ok and "premature" in why
