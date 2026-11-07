import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import doctor_round as dr  # noqa: E402

NOW = datetime(2026, 11, 6, 15, 0, tzinfo=timezone.utc)


def log(tmp_path, rows):
    p = tmp_path / "l.log"
    p.write_text("\n".join(json.dumps({"timestamp": ts, "actions": [{"step": s, "action": a, "detail": "d"}]}) for ts, s, a in rows) + "\n")
    return p


def test_a_step_that_failed_then_recovered_is_not_failing_now(tmp_path):
    p = log(tmp_path, [("2026-11-06T03:00:00Z", "a", "failed"), ("2026-11-06T04:00:00Z", "a", "none"), ("2026-11-06T05:00:00Z", "b", "failed")])
    r = {f["step"]: f for f in dr.failed_steps(p, NOW)}
    assert r["a"]["failing_now"] is False and r["b"]["failing_now"] is True


def test_old_failures_outside_the_window_are_ignored(tmp_path):
    p = log(tmp_path, [("2026-11-01T03:00:00Z", "a", "failed")])
    assert dr.failed_steps(p, NOW) == []


def test_approval_expiry_window(tmp_path):
    f = tmp_path / "a.json"
    f.write_text(json.dumps({"approvals": {"P1": {"expires_at": "2026-11-07T01:00:00+00:00"}, "P2": {"expires_at": "2026-11-06T20:00:00+00:00"}, "P3": {"expires_at": "2026-12-01T00:00:00+00:00"}}}))
    got = {a["product"]: a["hours_left"] for a in dr.expiring_approvals(f, NOW)}
    assert set(got) == {"P1", "P2"} and got["P2"] == 5.0


def test_diagnose_recovers_when_a_later_tick_carries_diagnosis_checks(tmp_path):
    rows = [
        {"timestamp": "2026-11-06T10:00:00Z", "actions": [{"step": "diagnose", "action": "failed", "detail": "health timed out"}]},
        {"timestamp": "2026-11-06T11:00:00Z", "diagnosis": {"status": "warning", "checks": {"x": {"ok": True}}}, "actions": [{"step": "other", "action": "none"}]},
    ]
    p = tmp_path / "l.log"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    assert {f["step"]: f for f in dr.failed_steps(p, NOW)}["diagnose"]["failing_now"] is False
    # but with no later healthy diagnosis it still counts as failing
    p.write_text(json.dumps(rows[0]) + "\n")
    assert {f["step"]: f for f in dr.failed_steps(p, NOW)}["diagnose"]["failing_now"] is True


def test_an_approval_for_a_product_already_live_is_not_a_problem(tmp_path):
    from datetime import timedelta
    ap = tmp_path / "a.json"
    exp = (NOW + timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ap.write_text(json.dumps([{"product_id": "B1-001", "expires_at": exp}, {"product_id": "B1-002", "expires_at": exp}]), encoding="utf-8")
    assert {a["product"] for a in dr.expiring_approvals(ap, NOW)} == {"B1-001", "B1-002"}
    assert {a["product"] for a in dr.expiring_approvals(ap, NOW, spent={"B1-001"})} == {"B1-002"}


def test_published_product_ids_reads_live_results_that_created_a_listing(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "batch1_publish_results.json").write_text(json.dumps([
        {"mode": "LIVE", "results": [{"id": "B1-001", "status": "PASS", "product_id": "p"}, {"id": "B1-002", "status": "BLOCKED"},
                                     {"id": "B1-003", "status": "BLOCKED", "product_id": "q"}]},
        {"mode": "DRY", "results": [{"id": "B1-004", "status": "PASS", "product_id": "z"}]}]), encoding="utf-8")
    assert dr.published_product_ids(tmp_path) == {"B1-001", "B1-003"}
