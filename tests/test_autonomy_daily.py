import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import autonomy_daily as ad  # noqa: E402


def row(n, status, name=None, detail="d"):
    return {"stage": n, "name": name or f"s{n}", "status": status, "detail": detail, "owner": "x"}


def paths(tmp_path):
    return dict(state_path=tmp_path / "s.json", history_path=tmp_path / "h.jsonl", latest_path=tmp_path / "l.json")


def test_regressions_only_ok_to_not_ok():
    prev = [row(1, "OK"), row(2, "BLOCKED"), row(3, "OK"), row(4, "WAITING")]
    now = [row(1, "BLOCKED"), row(2, "BLOCKED"), row(3, "OK"), row(4, "OK"), row(5, "BLOCKED")]
    assert [g["stage"] for g in ad.regressions(prev, now)] == [1]


def test_first_run_has_no_regression_and_no_alert(tmp_path):
    calls = []
    r = ad.run_once("2026-11-06", collector=lambda: [row(1, "OK"), row(2, "BLOCKED")],
                    alerter=lambda **k: calls.append(k), **paths(tmp_path))
    assert r["action"] == "ok" and not calls
    assert json.loads((tmp_path / "l.json").read_text())["counts"] == {"OK": 1, "BLOCKED": 1}


def test_once_per_day(tmp_path):
    p = paths(tmp_path)
    ad.run_once("2026-11-06", collector=lambda: [row(1, "OK")], alerter=lambda **k: None, **p)
    r = ad.run_once("2026-11-06", collector=lambda: 1 / 0, alerter=lambda **k: None, **p)
    assert r["action"] == "none"
    assert len((tmp_path / "h.jsonl").read_text().splitlines()) == 1


def test_regression_alerts_once_and_not_again_next_day_if_still_down(tmp_path):
    p = paths(tmp_path)
    calls = []
    ad.run_once("2026-11-06", collector=lambda: [row(1, "OK")], alerter=lambda **k: calls.append(k), **p)
    r = ad.run_once("2026-11-07", collector=lambda: [row(1, "BLOCKED", detail="loop dead")], alerter=lambda **k: calls.append(k), **p)
    assert r["action"] == "regressed" and len(calls) == 1 and "loop dead" in calls[0]["body"]
    r2 = ad.run_once("2026-11-08", collector=lambda: [row(1, "BLOCKED")], alerter=lambda **k: calls.append(k), **p)
    assert r2["action"] == "ok" and len(calls) == 1


def test_alert_goes_to_fallback_ledger_without_telegram(tmp_path):
    from gf_ops import alerts
    ledger = tmp_path / "fb.jsonl"
    r = alerts.send_alert(subject="x", body="y", category="OPS", sender=lambda t: {"sent": False, "error": "no chat"},
                          dedupe_path=str(tmp_path / "d.json"), fallback_path=str(ledger))
    assert r["channel"] == "local_fallback" and ledger.exists()


def test_tool_rows_map_statuses_and_skip_conditional(tmp_path):
    fake = lambda: {"rows": [  # noqa: E731
        {"name": "gumroad", "status": "VERIFIED", "evidence": "ok"},
        {"name": "agent:qa", "status": "VERIFIED_CONNECTED", "evidence": "ok"},
        {"name": "paddle", "status": "FAILED", "evidence": "403"},
        {"name": "loop:low_disk_mode", "status": "DEGRADED", "evidence": "active"}]}
    rows = ad.tool_rows(fake)
    assert [(r["stage"], r["status"]) for r in rows] == [("T:gumroad", "OK"), ("T:agent:qa", "OK"), ("T:paddle", "FAILED")]


def test_tool_regression_alerts_and_verifier_crash_is_recorded(tmp_path):
    p = paths(tmp_path)
    calls = []
    up = lambda: [row("T:gumroad", "OK", "gumroad")]  # noqa: E731
    down = lambda: [row("T:gumroad", "DEGRADED", "gumroad", "refused")]  # noqa: E731
    ad.run_once("2026-11-06", collector=lambda: [], tools=up, alerter=lambda **k: calls.append(k), **p)
    r = ad.run_once("2026-11-07", collector=lambda: [], tools=down, alerter=lambda **k: calls.append(k), **p)
    assert r["action"] == "regressed" and "T:gumroad" in calls[0]["body"]
    boom = lambda: 1 / 0  # noqa: E731
    r = ad.run_once("2026-11-08", collector=lambda: [row(1, "OK")], tools=boom, alerter=lambda **k: None, **p)
    assert json.loads((tmp_path / "l.json").read_text())["rows"][-1]["stage"] == "T:verifier"
